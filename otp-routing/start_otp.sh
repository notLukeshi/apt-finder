#!/bin/bash
# OpenTripPlanner Startup Script for Linux/macOS (Cached Version)
# Builds only when inputs change and reports problematic GTFS with a recap

set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSETS_DIR="$SCRIPT_DIR/assets"
OTP_JAR="$ASSETS_DIR/otp.jar"
GRAPH_FILE="$ASSETS_DIR/graph.obj"
MANIFEST_FILE="$ASSETS_DIR/graph_manifest.json"
BUILD_LOG="$ASSETS_DIR/build.log"

FORCE_REBUILD=false
for arg in "$@"; do
    case "$arg" in
        --rebuild|-r)
            FORCE_REBUILD=true
            ;;
    esac
done

# Function to compute SHA256 hash of a file
get_file_hash() {
    local file="$1"
    if [ -f "$file" ]; then
        sha256sum "$file" | cut -d' ' -f1
    else
        echo ""
    fi
}

# Validate GTFS zip integrity (skip files that fail)
validate_gtfs_file() {
    local file="$1"
    if command -v unzip >/dev/null 2>&1; then
        unzip -t "$file" >/dev/null 2>&1
    else
        python3 - << 'PY'
import sys, zipfile
path = sys.argv[1]
try:
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
    if bad:
        sys.exit(1)
except Exception:
    sys.exit(1)
PY
        [ $? -eq 0 ] || return 1
    fi
}

# Function to compute hash of all files in a directory
get_directory_hashes() {
    local dir="$1"
    local pattern="$2"
    local result="["
    local first=true
    
    if [ -d "$dir" ]; then
        for file in "$dir"/$pattern; do
            if [ -f "$file" ]; then
                if [ "$first" = true ]; then
                    first=false
                else
                    result+=","
                fi
                local filename=$(basename "$file")
                local filesize=$(stat -c%s "$file" 2>/dev/null || stat -f%z "$file" 2>/dev/null)
                local modified=$(date -r "$file" -u +"%Y-%m-%dT%H:%M:%S.000Z" 2>/dev/null || stat -f%Sm -t%Y-%m-%dT%H:%M:%S.000Z "$file" 2>/dev/null)
                local hash=$(get_file_hash "$file")
                
                result+=$(cat <<EOF
{
  "name": "$filename",
  "hash": "$hash",
  "size": $filesize,
  "modified": "$modified"
}
EOF
)
            fi
        done
    fi
    result+="]"
    echo "$result"
}

# Check Java
echo -e "\033[36mChecking Java installation...\033[0m"
if ! command -v java &> /dev/null; then
    echo -e "\033[31mERROR: Java is not installed or not in PATH\033[0m"
    echo -e "\033[33mPlease install Java 21 (LTS) and try again\033[0m"
    exit 1
fi
java -version

# Check OTP jar exists
if [ ! -f "$OTP_JAR" ]; then
    echo -e "\033[31mERROR: otp.jar not found at $OTP_JAR\033[0m"
    echo -e "\033[33mDownload a shaded OpenTripPlanner release from https://github.com/opentripplanner/OpenTripPlanner/releases\033[0m"
    echo -e "\033[33mRename the JAR to otp.jar and place it at $OTP_JAR\033[0m"
    echo -e "\033[33mSee docs/otp-routing/route_setup.md for the full OTP asset checklist\033[0m"
    exit 1
fi

# Check for OSM file
OSM_FILES=$(find "$ASSETS_DIR" -maxdepth 1 -name "*.osm.pbf" 2>/dev/null)
if [ -z "$OSM_FILES" ]; then
    echo -e "\033[31mERROR: No .osm.pbf file found in $ASSETS_DIR\033[0m"
    echo -e "\033[33mDownload a .osm.pbf extract from https://download.geofabrik.de/asia/japan/kanto.html (or another region)\033[0m"
    echo -e "\033[33mSave it in $ASSETS_DIR with any filename ending in .osm.pbf, for example kanto.osm.pbf\033[0m"
    echo -e "\033[33mSee docs/otp-routing/route_setup.md for the full OTP asset checklist\033[0m"
    exit 1
fi
OSM_FILE=$(echo "$OSM_FILES" | head -n1)
echo -e "\033[32mFound OSM file: $(basename "$OSM_FILE")\033[0m"

# Check for GTFS files in gtfs_backup and validate them
GTFS_BACKUP_DIR="$SCRIPT_DIR/gtfs_backup"
GTFS_COUNT=$(find "$GTFS_BACKUP_DIR" -name "*.zip" 2>/dev/null | wc -l)

VALID_GTFS_ENTRIES="["
INVALID_GTFS_ENTRIES="["
FIRST_VALID=true
FIRST_INVALID=true

if [ "$GTFS_COUNT" -eq 0 ]; then
    echo -e "\033[33mWARNING: No GTFS .zip files found in gtfs_backup\033[0m"
    echo -e "\033[33mTransit routing will not work without GTFS data\033[0m"
    echo -e "\033[33mRegister at https://developer.odpt.org/ and copy your access token from https://developer.odpt.org/editkeys\033[0m"
    echo -e "\033[33mDownload GTFS .zip files from https://ckan.odpt.org/dataset and save them in $GTFS_BACKUP_DIR\033[0m"
    echo -e "\033[33mKeep the original filenames exactly as downloaded, and do not unzip them\033[0m"
else
    echo -e "\033[32mFound $GTFS_COUNT GTFS files in backup\033[0m"
fi

# Copy router-config.json to assets if exists
ROUTER_CONFIG="$SCRIPT_DIR/router-config.json"
ROUTER_CONFIG_DEST="$ASSETS_DIR/router-config.json"
if [ -f "$ROUTER_CONFIG" ]; then
    cp "$ROUTER_CONFIG" "$ROUTER_CONFIG_DEST"
    echo -e "\033[32mCopied router-config.json to assets folder\033[0m"
fi

# Copy build-config.json to assets if exists (required for graph saving)
BUILD_CONFIG="$SCRIPT_DIR/build-config.json"
BUILD_CONFIG_DEST="$ASSETS_DIR/build-config.json"
if [ -f "$BUILD_CONFIG" ]; then
    cp "$BUILD_CONFIG" "$BUILD_CONFIG_DEST"
    echo -e "\033[32mCopied build-config.json to assets folder\033[0m"
fi

# Copy/validate GTFS files from gtfs_backup to assets/ (OTP reads zip files directly from assets)
if [ -d "$GTFS_BACKUP_DIR" ]; then
    echo -e "\033[36mCopying GTFS files to assets folder (invalid files will be skipped)...\033[0m"
    # Remove any previously copied GTFS to avoid stale files
    find "$ASSETS_DIR" -maxdepth 1 -name "*.zip" -type f -delete 2>/dev/null || true

    for gtfs in "$GTFS_BACKUP_DIR"/*.zip; do
        if [ -f "$gtfs" ]; then
            filename=$(basename "$gtfs")
            filesize=$(stat -c%s "$gtfs" 2>/dev/null || stat -f%z "$gtfs" 2>/dev/null)
            modified=$(date -r "$gtfs" -u +"%Y-%m-%dT%H:%M:%S.000Z" 2>/dev/null || stat -f%Sm -t%Y-%m-%dT%H:%M:%S.000Z "$gtfs" 2>/dev/null)
            filehash=$(get_file_hash "$gtfs")

            if ! validate_gtfs_file "$gtfs"; then
                echo -e "\033[33mSkipping invalid GTFS: $filename\033[0m"
                if [ "$FIRST_INVALID" = true ]; then FIRST_INVALID=false; else INVALID_GTFS_ENTRIES+=","; fi
                INVALID_GTFS_ENTRIES+=$(cat <<EOF
{ "name": "$filename", "hash": "$filehash", "size": $filesize, "modified": "$modified", "reason": "invalid_zip" }
EOF
)
                continue
            fi

            cp "$gtfs" "$ASSETS_DIR/$filename"
            echo "  Copied: $filename"

            if [ "$FIRST_VALID" = true ]; then FIRST_VALID=false; else VALID_GTFS_ENTRIES+=","; fi
            VALID_GTFS_ENTRIES+=$(cat <<EOF
{ "name": "$filename", "hash": "$filehash", "size": $filesize, "modified": "$modified" }
EOF
)
        fi
    done
fi
VALID_GTFS_ENTRIES+="]"
INVALID_GTFS_ENTRIES+="]"

# Compute current hashes (always, so manifest writes are consistent)
CURRENT_OTP_HASH=$(get_file_hash "$OTP_JAR")
CURRENT_OSM_HASH=$(get_file_hash "$OSM_FILE")
CURRENT_ROUTER_HASH=""
if [ -f "$ROUTER_CONFIG_DEST" ]; then
    CURRENT_ROUTER_HASH=$(get_file_hash "$ROUTER_CONFIG_DEST")
fi
CURRENT_GTFS_HASHES="$VALID_GTFS_ENTRIES"
CURRENT_GTFS_INVALID="$INVALID_GTFS_ENTRIES"

# Determine if we need to rebuild based on hashes
NEED_REBUILD=$FORCE_REBUILD

if [ "$FORCE_REBUILD" = false ] && [ -f "$GRAPH_FILE" ] && [ -f "$MANIFEST_FILE" ]; then
    echo -e "\033[36mChecking if rebuild is needed...\033[0m"
    
    # Read existing manifest
    EXISTING_OTP_HASH=$(jq -r '.otp_jar // empty' "$MANIFEST_FILE" 2>/dev/null)
    EXISTING_OSM_HASH=$(jq -r '.osm_pbf // empty' "$MANIFEST_FILE" 2>/dev/null)
    EXISTING_ROUTER_HASH=$(jq -r '.router_config // empty' "$MANIFEST_FILE" 2>/dev/null)
    EXISTING_GTFS_HASHES=$(jq -c '.gtfs_files // []' "$MANIFEST_FILE" 2>/dev/null)
    EXISTING_GTFS_INVALID=$(jq -c '.gtfs_invalid // []' "$MANIFEST_FILE" 2>/dev/null)
    
    # Compare hashes
    HASHES_MATCH=true
    
    if [ "$CURRENT_OTP_HASH" != "$EXISTING_OTP_HASH" ]; then
        echo -e "\033[33mOTP JAR has changed\033[0m"
        HASHES_MATCH=false
    fi
    
    if [ "$CURRENT_OSM_HASH" != "$EXISTING_OSM_HASH" ]; then
        echo -e "\033[33mOSM PBF file has changed\033[0m"
        HASHES_MATCH=false
    fi
    
    if [ "$CURRENT_ROUTER_HASH" != "$EXISTING_ROUTER_HASH" ]; then
        echo -e "\033[33mRouter config has changed\033[0m"
        HASHES_MATCH=false
    fi
    
    # Compare GTFS files (including invalids)
    if [ "$CURRENT_GTFS_HASHES" != "$EXISTING_GTFS_HASHES" ]; then
        echo -e "\033[33mGTFS files have changed\033[0m"
        HASHES_MATCH=false
    fi
    if [ "$CURRENT_GTFS_INVALID" != "$EXISTING_GTFS_INVALID" ]; then
        echo -e "\033[33mGTFS invalid/skip list has changed\033[0m"
        HASHES_MATCH=false
    fi
    
    if [ "$HASHES_MATCH" = true ]; then
        echo -e "\033[32mAll input files unchanged - can load existing graph\033[0m"
        NEED_REBUILD=false
    else
        echo -e "\033[33mInput files have changed - rebuild required\033[0m"
        NEED_REBUILD=true
    fi
else
    if [ "$FORCE_REBUILD" = false ]; then
        echo -e "\033[33mNo existing graph or manifest found - build required\033[0m"
    fi
    NEED_REBUILD=true
fi

# Determine memory allocation
if [[ "$OSTYPE" == "darwin"* ]]; then
    TOTAL_MEM_GB=$(( $(sysctl -n hw.memsize) / 1024 / 1024 / 1024 ))
else
    TOTAL_MEM_GB=$(( $(grep MemTotal /proc/meminfo | awk '{print $2}') / 1024 / 1024 ))
fi
ALLOCATED_MEM=$(( TOTAL_MEM_GB * 70 / 100 ))
[ $ALLOCATED_MEM -gt 16 ] && ALLOCATED_MEM=16
echo -e "\033[36mAllocating ${ALLOCATED_MEM}GB RAM to OTP\033[0m"

# Start OTP
echo ""
echo -e "\033[35m============================================\033[0m"
echo -e "\033[35m  Starting OpenTripPlanner Server\033[0m"
echo -e "\033[35m============================================\033[0m"
echo ""
echo -e "\033[36mPreparing OTP startup...\033[0m"
echo -e "\033[33mAPI will be available at: http://localhost:8080/otp/\033[0m"
echo ""

cd "$ASSETS_DIR"

: > "$BUILD_LOG"
REBUILT_AFTER_LOAD_FAILURE=false

while true; do
    if [ "$NEED_REBUILD" = true ]; then
        # Save manifest before building
        cat > "$MANIFEST_FILE" << EOF
{
  "otp_jar": "$CURRENT_OTP_HASH",
  "osm_pbf": "$CURRENT_OSM_HASH",
  "router_config": $( [ -n "$CURRENT_ROUTER_HASH" ] && echo "\"$CURRENT_ROUTER_HASH\"" || echo null ),
  "gtfs_files": $CURRENT_GTFS_HASHES,
  "gtfs_invalid": $CURRENT_GTFS_INVALID,
  "build_time": "$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")"
}
EOF
        echo -e "\033[32mSaved input file manifest\033[0m"

        OTP_ARGS="--build --save --serve"
        START_MESSAGE="Building graph, saving to disk, and starting server..."
    else
        OTP_ARGS="--load --serve"
        START_MESSAGE="Loading existing graph and starting server..."
    fi

    echo -e "\033[36m$START_MESSAGE\033[0m"

    # Run OTP and capture output for recap
    set +e
    { java -Xmx${ALLOCATED_MEM}G -jar "$OTP_JAR" $OTP_ARGS .; } 2>&1 | tee -a "$BUILD_LOG"
    OTP_EXIT=${PIPESTATUS[0]}
    set -e

    if [ "$OTP_EXIT" -ne 0 ] && [ "$NEED_REBUILD" = false ] && [ "$REBUILT_AFTER_LOAD_FAILURE" = false ]; then
        echo -e "\033[33mExisting graph failed to load. Deleting graph.obj and retrying with a full rebuild...\033[0m"
        rm -f "$GRAPH_FILE" "$MANIFEST_FILE"
        NEED_REBUILD=true
        REBUILT_AFTER_LOAD_FAILURE=true
        continue
    fi

    break
done

# Update manifest with the last build/load result (if jq is available)
if command -v jq >/dev/null 2>&1; then
    TMP_MANIFEST=$(mktemp)
    jq --arg time "$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")" --argjson code "$OTP_EXIT" \
       '.last_run_completed_at = $time | .last_run_exit = $code' "$MANIFEST_FILE" > "$TMP_MANIFEST" && mv "$TMP_MANIFEST" "$MANIFEST_FILE"
fi

echo ""
echo -e "\033[36mBuild/Load recap\033[0m"
VALID_COUNT=$(echo "$CURRENT_GTFS_HASHES" | jq 'length' 2>/dev/null || echo 0)
INVALID_COUNT=$(echo "$CURRENT_GTFS_INVALID" | jq 'length' 2>/dev/null || echo 0)
echo "  GTFS accepted : $VALID_COUNT"
echo "  GTFS skipped  : $INVALID_COUNT"
if [ "$INVALID_COUNT" -gt 0 ]; then
    echo "  Skipped files:"
    echo "$CURRENT_GTFS_INVALID" | jq -r '.[] | "    - \(.name) (reason: \(.reason))"' 2>/dev/null || true
fi
echo "  OTP exit code : $OTP_EXIT"

if [ $OTP_EXIT -ne 0 ]; then
    echo -e "\033[31mOTP exited with errors. See $BUILD_LOG\033[0m"
else
    echo -e "\033[32mOTP completed successfully\033[0m"
fi

echo "OTP server stopped"
