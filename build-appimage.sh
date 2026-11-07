#!/usr/bin/env bash
set -euo pipefail

# Build script to package R-Quran into a standalone AppImage

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Preparing AppDir directory structure..."

# Synchronize python modules from src into AppDir
mkdir -p AppDir/usr/src/r_quran
cp -f src/r_quran/*.py AppDir/usr/src/r_quran/

# Ensure entrypoint scripts have execute permissions
chmod +x AppDir/AppRun
chmod +x AppDir/usr/bin/r-quran

# Locate or download appimagetool
APPIMAGETOOL="/tmp/appimagetool"
if ! command -v appimagetool &>/dev/null; then
    if [ ! -x "$APPIMAGETOOL" ]; then
        echo "==> Downloading official appimagetool..."
        curl -fsSL -o "$APPIMAGETOOL" \
            https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
        chmod +x "$APPIMAGETOOL"
    fi
else
    APPIMAGETOOL="$(command -v appimagetool)"
fi

echo "==> Building AppImage..."
export ARCH=x86_64
export APPIMAGE_EXTRACT_AND_RUN=1

"$APPIMAGETOOL" --no-appstream AppDir R-Quran-x86_64.AppImage

chmod +x R-Quran-x86_64.AppImage
echo "==> Successfully generated R-Quran-x86_64.AppImage"
