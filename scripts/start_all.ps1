#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir '..')).Path
$WebDir = Join-Path $ProjectRoot 'web'
$OtpScript = Join-Path $ProjectRoot 'otp-routing\start_otp.ps1'
$VenvDir = Join-Path $ProjectRoot '.venv'
$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
$VenvActivate = Join-Path $VenvDir 'Scripts\Activate.ps1'
$ApiPort = if ([string]::IsNullOrWhiteSpace($env:APT_FINDER_API_PORT)) { '8000' } else { $env:APT_FINDER_API_PORT }
$WebPort = if ([string]::IsNullOrWhiteSpace($env:APT_FINDER_WEB_PORT)) { '5173' } else { $env:APT_FINDER_WEB_PORT }
$ApiBindHost = if ([string]::IsNullOrWhiteSpace($env:APT_FINDER_API_HOST)) { '0.0.0.0' } else { $env:APT_FINDER_API_HOST }
$NpmCommand = 'npm.cmd'
$env:npm_config_legacy_peer_deps = 'true'

function Write-Section {
    param([string]$Message)
    Write-Host ''
    Write-Host '============================================================' -ForegroundColor Magenta
    Write-Host $Message -ForegroundColor Magenta
    Write-Host '============================================================' -ForegroundColor Magenta
}

function Write-Step {
    param(
        [string]$Label,
        [string]$Message
    )
    Write-Host "[$Label] $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-ErrorLine {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Get-LaunchHost {
    if (-not [string]::IsNullOrWhiteSpace($env:APT_FINDER_HOST)) {
        return $env:APT_FINDER_HOST
    }

    try {
        $candidate = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
            Where-Object {
                $_.IPAddress -notmatch '^127\.' -and
                $_.IPAddress -notlike '169.254.*' -and
                $_.IPAddress -ne '0.0.0.0'
            } |
            Select-Object -ExpandProperty IPAddress -First 1

        if (-not [string]::IsNullOrWhiteSpace($candidate)) {
            return $candidate
        }
    } catch {
        # Fall through to localhost.
    }

    return '127.0.0.1'
}

function Test-BackendDependencies {
    & python -c "import importlib.util, sys; modules = ['fastapi', 'uvicorn', 'requests', 'bs4', 'yaml', 'googlemaps', 'dotenv', 'tenacity', 'pydantic']; missing = [name for name in modules if importlib.util.find_spec(name) is None]; sys.exit(1 if missing else 0)" *> $null
    return ($LASTEXITCODE -eq 0)
}

function Test-FrontendDependencies {
    $viteCandidates = @(
        (Join-Path $WebDir 'node_modules\.bin\vite.cmd'),
        (Join-Path $WebDir 'node_modules\.bin\vite.ps1'),
        (Join-Path $WebDir 'node_modules\.bin\vite')
    )

    foreach ($candidate in $viteCandidates) {
        if (Test-Path $candidate) {
            return $true
        }
    }

    return $false
}

function Wait-ForHttp {
    param(
        [string]$Url,
        [string]$Label,
        [int]$TimeoutSeconds = 60,
        [System.Diagnostics.Process]$ProcessToWatch = $null
    )

    $elapsed = 0
    while ($true) {
        & python -c "import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=2)" $Url *> $null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "$Label is ready at $Url"
            return
        }

        if ($ProcessToWatch -and $ProcessToWatch.HasExited) {
            throw "$Label exited before it became ready."
        }

        if ($elapsed -ge $TimeoutSeconds) {
            throw "Timed out waiting for $Label at $Url"
        }

        Start-Sleep -Seconds 1
        $elapsed++
    }
}

function Stop-ProcessSafely {
    param([System.Diagnostics.Process]$Process)

    if ($null -ne $Process) {
        try {
            if (-not $Process.HasExited) {
                Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
            }
        } catch {
            # Ignore cleanup errors.
        }
    }
}

function Invoke-NpmCommand {
    param(
        [string[]]$Arguments,
        [string]$Description
    )

    & $NpmCommand @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE"
    }
}

$ApiProcess = $null
$OtpProcess = $null
$WebProcess = $null
$CompletedNormally = $false

try {
    $LaunchHost = Get-LaunchHost
    $WebOrigin = "http://$($LaunchHost):$WebPort"
    $ApiBaseUrl = if ([string]::IsNullOrWhiteSpace($env:VITE_API_BASE_URL)) { "http://$($LaunchHost):$ApiPort/api" } else { $env:VITE_API_BASE_URL }

    if ([string]::IsNullOrWhiteSpace($env:CORS_ORIGINS)) {
        $corsOrigins = @(
            "http://localhost:$WebPort"
            "http://127.0.0.1:$WebPort"
            $WebOrigin
        ) | Select-Object -Unique
        $env:CORS_ORIGINS = ($corsOrigins -join ',')
    }

    $env:API_HOST = $ApiBindHost
    $env:API_PORT = $ApiPort
    $env:API_RELOAD = 'false'
    $env:VITE_API_BASE_URL = $ApiBaseUrl

    Write-Section 'APT-Finder all-in-one launcher'
    Write-Step 'INFO' "Project root: $ProjectRoot"
    Write-Step 'INFO' "Selected host: $LaunchHost"
    Write-Step 'INFO' "API URL: $ApiBaseUrl"
    Write-Step 'INFO' "Web origin: $WebOrigin"
    Write-Step 'INFO' "Backend port: $ApiPort"
    Write-Step 'INFO' "Web port: $WebPort"

    if (-not (Test-Path $VenvPython)) {
        Write-Step 'SETUP' "Creating virtual environment at $VenvDir"
        $pythonBootstrap = $null
        $pythonArgs = @()
        if (Get-Command py -ErrorAction SilentlyContinue) {
            $pythonBootstrap = 'py'
            $pythonArgs = @('-3')
        } elseif (Get-Command python -ErrorAction SilentlyContinue) {
            $pythonBootstrap = 'python'
        } elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
            $pythonBootstrap = 'python3'
        }

        if ($null -eq $pythonBootstrap) {
            throw 'Python was not found in PATH. Please install Python 3 before running the launcher.'
        }

        & $pythonBootstrap @pythonArgs -m venv $VenvDir
        Write-Success 'Virtual environment created'
    } else {
        Write-Success 'Virtual environment already exists'
    }

    if (-not (Test-Path $VenvActivate)) {
        throw "Virtual environment activation script is missing: $VenvActivate"
    }

    . $VenvActivate
    Write-Success 'Virtual environment activated'

    Write-Step 'CHECK' 'Verifying backend Python dependencies'
    if (-not (Test-BackendDependencies)) {
        Write-Warn 'Backend dependencies are missing; installing them now'
        & python -m pip install --upgrade pip
        & python -m pip install -e '.[dev]'
        Write-Success 'Backend dependencies installed'
    } else {
        Write-Success 'Backend dependencies are already installed'
    }

    if (-not (Get-Command $NpmCommand -ErrorAction SilentlyContinue)) {
        throw 'npm was not found in PATH. Install Node.js before starting the web app.'
    }

    if (-not (Test-FrontendDependencies)) {
        Write-Step 'SETUP' 'Installing frontend dependencies with legacy peer resolution'
        Push-Location $WebDir
        try {
            Invoke-NpmCommand -Arguments @('ci') -Description 'Frontend dependency installation'
        } finally {
            Pop-Location
        }
        Write-Success 'Frontend dependencies installed'
    } else {
        Write-Success 'Frontend dependencies are already installed'
    }

    Write-Step 'START' 'Launching API server'
    $ApiProcess = Start-Process -FilePath 'python' -ArgumentList @('run_api.py') -WorkingDirectory $ProjectRoot -NoNewWindow -PassThru
    Write-Success "API server process started (PID $($ApiProcess.Id))"

    Wait-ForHttp -Url "http://127.0.0.1:$ApiPort/health" -Label 'API server' -TimeoutSeconds 60 -ProcessToWatch $ApiProcess

    if (-not (Test-Path $OtpScript)) {
        throw "OTP launcher not found: $OtpScript"
    }

    Write-Step 'START' 'Launching OpenTripPlanner routing'
    $OtpProcess = Start-Process -FilePath 'powershell.exe' -ArgumentList @(
        '-NoLogo',
        '-NoProfile',
        '-ExecutionPolicy',
        'Bypass',
        '-File',
        $OtpScript
    ) -WorkingDirectory $ProjectRoot -NoNewWindow -PassThru
    Write-Success "OTP process started (PID $($OtpProcess.Id))"

    Start-Sleep -Seconds 5
    $OtpProcess.Refresh()
    if ($OtpProcess.HasExited) {
        throw "OTP launcher exited during startup with code $($OtpProcess.ExitCode). Check Java 21 installation and OTP logs."
    }

    Write-Step 'BUILD' 'Creating the production frontend bundle'
    Push-Location $WebDir
    try {
        Invoke-NpmCommand -Arguments @('run', 'build') -Description 'Frontend build'
    } finally {
        Pop-Location
    }
    Write-Success 'Frontend bundle built'

    Write-Step 'START' 'Serving the production web build'
    Write-Success "Open the dashboard at $WebOrigin"
    Write-Warn 'Press Ctrl+C to stop the web server, OTP, and API launcher together.'

    Push-Location $WebDir
    try {
        $WebProcess = Start-Process -FilePath $NpmCommand -ArgumentList @('run', 'preview', '--', '--host', '0.0.0.0', '--port', $WebPort, '--strictPort') -NoNewWindow -PassThru
        Wait-Process -Id $WebProcess.Id
        $WebProcess.Refresh()
        if ($WebProcess.ExitCode -eq 0) {
            $CompletedNormally = $true
        } else {
            throw "Vite preview exited with code $($WebProcess.ExitCode)"
        }
    } finally {
        Pop-Location
    }
} finally {
    Stop-ProcessSafely -Process $WebProcess
    Stop-ProcessSafely -Process $OtpProcess
    Stop-ProcessSafely -Process $ApiProcess
    Remove-Item (Join-Path $ProjectRoot 'otp-routing\java_version_check.tmp') -ErrorAction SilentlyContinue
    if ($CompletedNormally) {
        Write-Success 'Launcher finished cleanly. Background services were asked to shut down.'
    } else {
        Write-Warn 'Launcher stopped. Background services were asked to shut down.'
    }
}
