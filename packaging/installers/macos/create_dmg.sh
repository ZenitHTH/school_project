#!/usr/bin/env bash
set -euo pipefail

APP_NAME="${1:-StudentManagement}"
APP_BUNDLE="${2:-dist/$APP_NAME.app}"
VERSION="${3:-1.0.0}"
OUTPUT_DIR="${4:-dist/installers}"

if [ ! -d "$APP_BUNDLE" ]; then
    echo "Error: App bundle not found at $APP_BUNDLE"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

DMG_TMP=$(mktemp -d -t dmg-build-XXXXXX)
trap 'rm -rf "$DMG_TMP"' EXIT

DMG_SOURCE="$DMG_TMP/dmg_root"
mkdir -p "$DMG_SOURCE"

# Copy .app bundle
cp -R "$APP_BUNDLE" "$DMG_SOURCE/"

# Create symlink to /Applications
ln -s /Applications "$DMG_SOURCE/Applications"

DMG_OUTPUT="$OUTPUT_DIR/${APP_NAME}-${VERSION}.dmg"
rm -f "$DMG_OUTPUT"

# Create compressed DMG image using native macOS hdiutil
hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$DMG_SOURCE" \
  -ov \
  -format UDZO \
  "$DMG_OUTPUT"

echo "Created DMG: $DMG_OUTPUT"
