#!/usr/bin/env bash
set -euo pipefail

APP_NAME="${1:-StudentManagement}"
APP_BIN_NAME="${2:-StudentManagement}"
PKG_NAME=$(echo "$APP_NAME" | tr '[:upper:]' '[:lower:]' | tr '_' '-')
VERSION="${3:-1.0.0}"
DIST_BIN_PATH="${4:-dist/$APP_BIN_NAME}"
OUTPUT_DIR="${5:-dist/installers}"

if [ ! -f "$DIST_BIN_PATH" ]; then
    echo "Error: Binary not found at $DIST_BIN_PATH"
    exit 1
fi

ARCH="${6:-$(dpkg --print-architecture 2>/dev/null || uname -m)}"
case "$ARCH" in
    x86_64) ARCH="amd64" ;;
    aarch64) ARCH="arm64" ;;
esac

mkdir -p "$OUTPUT_DIR"

BUILD_ROOT=$(mktemp -d -t deb-build-XXXXXX)
trap 'rm -rf "$BUILD_ROOT"' EXIT

# Package directories
INSTALL_DIR="$BUILD_ROOT/usr/lib/$PKG_NAME"
BIN_DIR="$BUILD_ROOT/usr/bin"
DESKTOP_DIR="$BUILD_ROOT/usr/share/applications"
CONTROL_DIR="$BUILD_ROOT/DEBIAN"

mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$CONTROL_DIR"

# Copy binary
cp "$DIST_BIN_PATH" "$INSTALL_DIR/$APP_BIN_NAME"
chmod 755 "$INSTALL_DIR/$APP_BIN_NAME"

# Create symlink in /usr/bin
ln -sf "/usr/lib/$PKG_NAME/$APP_BIN_NAME" "$BIN_DIR/$PKG_NAME"

# Create .desktop file
cat <<EOF > "$DESKTOP_DIR/$PKG_NAME.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_NAME
Comment=School Management System - $APP_NAME
Exec=/usr/bin/$PKG_NAME
Terminal=false
Categories=Education;Office;
EOF
chmod 644 "$DESKTOP_DIR/$PKG_NAME.desktop"

# Create control file
cat <<EOF > "$CONTROL_DIR/control"
Package: $PKG_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: School Management System <admin@school.local>
Description: $APP_NAME desktop application for SMTE School System.
EOF

# Calculate size in KB
INSTALLED_SIZE=$(du -sk "$BUILD_ROOT" | cut -f1)
echo "Installed-Size: $INSTALLED_SIZE" >> "$CONTROL_DIR/control"

DEB_FILE="$OUTPUT_DIR/${PKG_NAME}_${VERSION}_${ARCH}.deb"
dpkg-deb --build --root-owner-group "$BUILD_ROOT" "$DEB_FILE"

echo "Created DEB: $DEB_FILE"
