# OpenTripPlanner Startup Script for Windows (Cached Version)
# This script builds the graph only when input files change using hash verification

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AssetsDir = Join-Path $ScriptDir "assets"
$OtpJar = Join-Path $AssetsDir "otp.jar"
$GraphFile = Join-Path $AssetsDir "graph.obj"
$ManifestFile = Join-Path $AssetsDir "graph_manifest.json"
$BuildLog = Join-Path $AssetsDir "build.log"
$JavaVersionCheckTmp = Join-Path $ScriptDir "java_version_check.tmp"

$ForceRebuild = $false
foreach ($arg in $args) {
    switch ($arg) {
        "--rebuild" { $ForceRebuild = $true }
        "-r" { $ForceRebuild = $true }
    }
}

# Function to compute SHA256 hash of a file
function Get-LocalFileHash {
    param([string]$FilePath)
    if (Test-Path $FilePath) {
        $hasher = [System.Security.Cryptography.SHA256]::Create()
        $stream = [System.IO.File]::OpenRead($FilePath)
        $hash = [System.BitConverter]::ToString($hasher.ComputeHash($stream)).Replace("-", "").ToLower()
        $stream.Close()
        return $hash
    }
    return $null
}

# Function to compute hash of all files in a directory
function Get-DirectoryHash {
    param([string]$DirPath, [string]$Pattern)
    $hashes = @()
    if (Test-Path $DirPath) {
        Get-ChildItem -Path $DirPath -Filter $Pattern | Sort-Object Name | ForEach-Object {
            $hash = Get-LocalFileHash -FilePath $_.FullName
            if ($hash) {
                $hashes += @{
                    name = $_.Name
                    hash = $hash
                    size = $_.Length
                    modified = $_.LastWriteTimeUtc.ToString("o")
                }
            }
        }
    }
    return $hashes
}

# Validate GTFS zip integrity (skip files that fail)
function Test-GtfsFileValid {
    param([string]$FilePath)
    try {
        Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction SilentlyContinue | Out-Null
        $zip = [System.IO.Compression.ZipFile]::OpenRead($FilePath)
        $zip.Dispose()
        return $true
    } catch {
        return $false
    }
}

# ==========================================
# ROBUST JAVA DETECTION
# ==========================================
Write-Host "Searching for a valid Java 21 installation..." -ForegroundColor Cyan

# 1. Define a list of places to look for Java
$PotentialJavaPaths = @(
    # Look specifically for JDK 21 in standard locations (Highest Priority)
    "C:\Program Files\Java\jdk-21*\bin\java.exe",
    "C:\Program Files\Eclipse Adoptium\jdk-21*\bin\java.exe",
    "C:\Program Files\Microsoft\jdk-21*\bin\java.exe",
    "C:\Program Files\Zulu\zulu-21*\bin\java.exe",
    
    # Look at JAVA_HOME if set
    "$env:JAVA_HOME\bin\java.exe",
    
    # Fallback to whatever is in the System PATH
    "java"
)

$SelectedJava = $null

foreach ($pathPattern in $PotentialJavaPaths) {
    # Resolve wildcards (like jdk-21*)
    $foundPaths = Get-ChildItem -Path $pathPattern -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
    
    # Handle the case where "java" (system path) is passed directly without wildcards
    if (-not $foundPaths -and $pathPattern -eq "java") { $foundPaths = @("java") }

    foreach ($exePath in $foundPaths) {
        try {
            # Run java -version to see if this executable actually works
            Start-Process -FilePath $exePath -ArgumentList "-version" -NoNewWindow -PassThru -RedirectStandardError $JavaVersionCheckTmp -Wait | Out-Null
            $output = Get-Content $JavaVersionCheckTmp -ErrorAction SilentlyContinue

            if ($output -match "version") {
                # Check if it is version 21 (Preferred)
                if ($output -match '"21') {
                    Write-Host "SUCCESS: Found Java 21 at: $exePath" -ForegroundColor Green
                    $SelectedJava = $exePath
                    break
                }
                # If we haven't found a preferred one yet, keep this as a backup
                if (-not $SelectedJava) {
                    $SelectedJava = $exePath
                }
            }
        } catch {
            # Continue looking
        } finally {
            Remove-Item $JavaVersionCheckTmp -ErrorAction SilentlyContinue
        }
    }
    if ($SelectedJava -and ($SelectedJava -match "jdk-21")) { break }
}

if (-not $SelectedJava) {
    Write-Host "CRITICAL ERROR: Could not find a working Java installation." -ForegroundColor Red
    Write-Host "We looked in Program Files and your PATH." -ForegroundColor Red
    Write-Host "Please install JDK 21 from https://adoptium.net/" -ForegroundColor Yellow
    exit 1
}

# If we found a Java but it wasn't 21, warn the user but try anyway
Write-Host "Using Java executable: $SelectedJava" -ForegroundColor Cyan

# ==========================================
# END JAVA DETECTION
# ==========================================

# Check OTP jar exists
if (-not (Test-Path $OtpJar)) {
    Write-Host "ERROR: otp.jar not found at $OtpJar" -ForegroundColor Red
    Write-Host "Download a shaded OpenTripPlanner release from https://github.com/opentripplanner/OpenTripPlanner/releases" -ForegroundColor Yellow
    Write-Host "Rename the JAR to otp.jar and place it at $OtpJar" -ForegroundColor Yellow
    Write-Host "See docs/otp-routing/route_setup.md for the full OTP asset checklist" -ForegroundColor Yellow
    exit 1
}

# Check for OSM file
$OsmFiles = Get-ChildItem -Path $AssetsDir -Filter "*.osm.pbf"
if ($OsmFiles.Count -eq 0) {
    Write-Host "ERROR: No .osm.pbf file found in $AssetsDir" -ForegroundColor Red
    Write-Host "Download a .osm.pbf extract from https://download.geofabrik.de/asia/japan/kanto.html (or another region)" -ForegroundColor Yellow
    Write-Host "Save it in $AssetsDir with any filename ending in .osm.pbf, for example kanto.osm.pbf" -ForegroundColor Yellow
    Write-Host "See docs/otp-routing/route_setup.md for the full OTP asset checklist" -ForegroundColor Yellow
    exit 1
}
Write-Host "Found OSM file: $($OsmFiles[0].Name)" -ForegroundColor Green

# Check for GTFS files in gtfs_backup (where they should be after first run)
$GtfsBackupDir = Join-Path $ScriptDir "gtfs_backup"
$GtfsFiles = Get-ChildItem -Path $GtfsBackupDir -Filter "*.zip" -ErrorAction SilentlyContinue | Sort-Object Name

$ValidGtfs = @()
$InvalidGtfs = @()

if ($GtfsFiles.Count -eq 0) {
    Write-Host "WARNING: No GTFS .zip files found in gtfs_backup" -ForegroundColor Yellow
    Write-Host "Transit routing will not work without GTFS data" -ForegroundColor Yellow
    Write-Host "Register at https://developer.odpt.org/ and copy your access token from https://developer.odpt.org/editkeys" -ForegroundColor Yellow
    Write-Host "Download GTFS .zip files from https://ckan.odpt.org/dataset and save them in $GtfsBackupDir" -ForegroundColor Yellow
    Write-Host "Keep the original filenames exactly as downloaded, and do not unzip them" -ForegroundColor Yellow
} else {
    Write-Host "Found $($GtfsFiles.Count) GTFS files in backup:" -ForegroundColor Green
    foreach ($file in $GtfsFiles) {
        Write-Host "  - $($file.Name)" -ForegroundColor Gray
    }
}

# Copy router-config.json to assets if exists
$RouterConfig = Join-Path $ScriptDir "router-config.json"
$RouterConfigDest = Join-Path $AssetsDir "router-config.json"
if (Test-Path $RouterConfig) {
    Copy-Item $RouterConfig $RouterConfigDest -Force
    Write-Host "Copied router-config.json to assets folder" -ForegroundColor Green
}

# Copy build-config.json to assets if exists (required for graph saving)
$BuildConfig = Join-Path $ScriptDir "build-config.json"
$BuildConfigDest = Join-Path $AssetsDir "build-config.json"
if (Test-Path $BuildConfig) {
    Copy-Item $BuildConfig $BuildConfigDest -Force
    Write-Host "Copied build-config.json to assets folder" -ForegroundColor Green
}

# Copy/validate GTFS files from gtfs_backup to assets/ (OTP reads zip files directly from assets)
if (Test-Path $GtfsBackupDir) {
    Write-Host "Copying GTFS files to assets folder (invalid files will be skipped)..." -ForegroundColor Cyan
    # Remove stale GTFS files in assets to avoid mixing
    Get-ChildItem -Path $AssetsDir -Filter "*.zip" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

    foreach ($file in $GtfsFiles) {
        $destPath = Join-Path $AssetsDir $file.Name
        $meta = [ordered]@{
            name = $file.Name
            hash = Get-LocalFileHash -FilePath $file.FullName
            size = $file.Length
            modified = $file.LastWriteTimeUtc.ToString("o")
        }

        if (-not (Test-GtfsFileValid -FilePath $file.FullName)) {
            Write-Host "  Skipping invalid GTFS: $($file.Name)" -ForegroundColor Yellow
            $meta.reason = "invalid_zip"
            $InvalidGtfs += $meta
            continue
        }

        Copy-Item $file.FullName $destPath -Force
        Write-Host "  Copied: $($file.Name)" -ForegroundColor Gray
        $ValidGtfs += $meta
    }
}

# Determine if we need to rebuild based on hashes
$NeedRebuild = $ForceRebuild
$CurrentManifest = $null

# Compute current hashes (always) for consistent manifest writes
$CurrentHashes = @{
    otp_jar = Get-LocalFileHash -FilePath $OtpJar
    osm_pbf = Get-LocalFileHash -FilePath $OsmFiles[0].FullName
    gtfs_files = $ValidGtfs
    gtfs_invalid = $InvalidGtfs
    router_config = if (Test-Path $RouterConfigDest) { Get-LocalFileHash -FilePath $RouterConfigDest } else { $null }
}

if (-not $ForceRebuild -and (Test-Path $GraphFile) -and (Test-Path $ManifestFile)) {
    Write-Host "Checking if rebuild is needed..." -ForegroundColor Cyan
    
    try {
        $CurrentManifest = Get-Content $ManifestFile -Raw | ConvertFrom-Json
        
        # Compare hashes (using JSON for array/object equality)
        $HashesMatch = $true
        
        if ($CurrentManifest.otp_jar -ne $CurrentHashes.otp_jar) {
            Write-Host "OTP JAR has changed" -ForegroundColor Yellow
            $HashesMatch = $false
        }
        
        if ($CurrentManifest.osm_pbf -ne $CurrentHashes.osm_pbf) {
            Write-Host "OSM PBF file has changed" -ForegroundColor Yellow
            $HashesMatch = $false
        }
        
        if ($CurrentManifest.router_config -ne $CurrentHashes.router_config) {
            Write-Host "Router config has changed" -ForegroundColor Yellow
            $HashesMatch = $false
        }

        $ManifestGtfsJson = ($CurrentManifest.gtfs_files | ConvertTo-Json -Depth 10)
        $CurrentGtfsJson = ($CurrentHashes.gtfs_files | ConvertTo-Json -Depth 10)
        if ($ManifestGtfsJson -ne $CurrentGtfsJson) {
            Write-Host "GTFS files have changed" -ForegroundColor Yellow
            $HashesMatch = $false
        }

        $ManifestGtfsInvalidJson = ($CurrentManifest.gtfs_invalid | ConvertTo-Json -Depth 10)
        $CurrentGtfsInvalidJson = ($CurrentHashes.gtfs_invalid | ConvertTo-Json -Depth 10)
        if ($ManifestGtfsInvalidJson -ne $CurrentGtfsInvalidJson) {
            Write-Host "GTFS invalid/skip list has changed" -ForegroundColor Yellow
            $HashesMatch = $false
        }
        
        if ($HashesMatch) {
            Write-Host "All input files unchanged - can load existing graph" -ForegroundColor Green
            $NeedRebuild = $false
        } else {
            Write-Host "Input files have changed - rebuild required" -ForegroundColor Yellow
            $NeedRebuild = $true
        }
    } catch {
        Write-Host "Error reading manifest - rebuild required" -ForegroundColor Yellow
        $NeedRebuild = $true
    }
} else {
    if (-not $ForceRebuild) {
        Write-Host "No existing graph or manifest found - build required" -ForegroundColor Yellow
    }
    $NeedRebuild = $true
}

# Determine memory allocation (use 70% of available RAM, max 16GB)
$TotalMemoryGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
$AllocatedMemory = [math]::Min([math]::Floor($TotalMemoryGB * 0.7), 16)
Write-Host "Allocating ${AllocatedMemory}GB RAM to OTP" -ForegroundColor Cyan

# Start OTP with build and serve
Write-Host "" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Magenta
Write-Host "  Starting OpenTripPlanner Server" -ForegroundColor Magenta
Write-Host "============================================" -ForegroundColor Magenta
Write-Host ""

Write-Host "Preparing OTP startup..." -ForegroundColor Cyan
Write-Host "API will be available at: http://localhost:8080/otp/" -ForegroundColor Yellow

# Run OTP using the specifically found Java path
Set-Location $AssetsDir
Remove-Item $BuildLog -Force -ErrorAction SilentlyContinue

$RebuiltAfterLoadFailure = $false

while ($true) {
    if ($NeedRebuild) {
        # Save manifest before building
        $NewManifest = @{
            otp_jar = Get-LocalFileHash -FilePath $OtpJar
            osm_pbf = Get-LocalFileHash -FilePath $OsmFiles[0].FullName
            gtfs_files = $ValidGtfs
            gtfs_invalid = $InvalidGtfs
            router_config = if (Test-Path $RouterConfigDest) { Get-LocalFileHash -FilePath $RouterConfigDest } else { $null }
            build_time = (Get-Date).ToString("o")
        }

        $NewManifest | ConvertTo-Json -Depth 10 | Set-Content $ManifestFile
        Write-Host "Saved input file manifest" -ForegroundColor Green

        $OtpArgs = "--build", "--save", "--serve"
        Write-Host "Building graph, saving to disk, and starting server..." -ForegroundColor Cyan
    } else {
        $OtpArgs = "--load", "--serve"
        Write-Host "Loading existing graph and starting server..." -ForegroundColor Cyan
    }

    # Run OTP and capture output for recap
    $PreviousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $SelectedJava "-Xmx${AllocatedMemory}G" -jar $OtpJar @OtpArgs . 2>&1 |
            ForEach-Object { $_.ToString() } |
            Tee-Object -FilePath $BuildLog -Append
        $OtpExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $PreviousErrorActionPreference
    }

    if ($OtpExitCode -ne 0 -and -not $NeedRebuild -and -not $RebuiltAfterLoadFailure) {
        Write-Host "Existing graph failed to load. Deleting graph.obj and retrying with a full rebuild..." -ForegroundColor Yellow
        Remove-Item $GraphFile -Force -ErrorAction SilentlyContinue
        Remove-Item $ManifestFile -Force -ErrorAction SilentlyContinue
        $NeedRebuild = $true
        $RebuiltAfterLoadFailure = $true
        continue
    }

    break
}

# Update manifest with last run metadata (if manifest exists)
if (Test-Path $ManifestFile) {
    try {
        $ManifestObj = Get-Content $ManifestFile -Raw | ConvertFrom-Json
        $ManifestObj.last_run_completed_at = (Get-Date).ToString("o")
        $ManifestObj.last_run_exit = $OtpExitCode
        $ManifestObj | ConvertTo-Json -Depth 10 | Set-Content $ManifestFile
    } catch {}
}

Write-Host "" -ForegroundColor White
Write-Host "Build/Load recap" -ForegroundColor Cyan
Write-Host "  GTFS accepted : $($ValidGtfs.Count)" -ForegroundColor White
Write-Host "  GTFS skipped  : $($InvalidGtfs.Count)" -ForegroundColor White
if ($InvalidGtfs.Count -gt 0) {
    Write-Host "  Skipped files:" -ForegroundColor Yellow
    foreach ($item in $InvalidGtfs) {
        Write-Host "    - $($item.name) (reason: $($item.reason))" -ForegroundColor Yellow
    }
}
Write-Host "  OTP exit code : $OtpExitCode" -ForegroundColor White

if ($OtpExitCode -ne 0) {
    Write-Host "OTP exited with errors. See $BuildLog" -ForegroundColor Red
} else {
    Write-Host "OTP completed successfully" -ForegroundColor Green
}

Write-Host "OTP server stopped" -ForegroundColor Yellow
