#!/usr/bin/env bash
set -euo pipefail

APP_NAME="${1:-StudentManagement}"
APP_BIN_NAME="${2:-StudentManagement}"
if [[ ! "$APP_NAME" =~ ^[A-Za-z0-9_-]+$ ]] || [[ ! "$APP_BIN_NAME" =~ ^[A-Za-z0-9_-]+$ ]]; then
    echo "Error: Invalid APP_NAME or APP_BIN_NAME" >&2
    exit 1
fi
PKG_NAME=$(echo "$APP_NAME" | tr '[:upper:]' '[:lower:]' | tr '_' '-')
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_VERSION_FILE="$SCRIPT_DIR/../../../VERSION"
DEFAULT_VERSION=$( [ -f "$REPO_VERSION_FILE" ] && tr -d '[:space:]' < "$REPO_VERSION_FILE" || echo "0.0.0" )
VERSION="${3:-$DEFAULT_VERSION}"
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.~+-][A-Za-z0-9._-]+)?$ ]]; then
    echo "Error: Invalid VERSION '$VERSION'" >&2
    exit 1
fi
DEB_VERSION="${VERSION//-/~}"
DIST_BIN_PATH="${4:-dist/$APP_BIN_NAME}"
OUTPUT_DIR="${5:-dist/installers}"

if [ ! -e "$DIST_BIN_PATH" ]; then
    echo "Error: Binary or bundle directory not found at $DIST_BIN_PATH"
    exit 1
fi

ARCH="${6:-$(dpkg --print-architecture 2>/dev/null || uname -m)}"
case "$ARCH" in
    x86_64) ARCH="amd64" ;;
    aarch64) ARCH="arm64" ;;
esac
if [[ ! "$ARCH" =~ ^[A-Za-z0-9._-]+$ ]]; then
    echo "Error: Invalid ARCH '$ARCH'" >&2
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

BUILD_ROOT=$(mktemp -d -t deb-build-XXXXXX)
trap 'rm -rf "$BUILD_ROOT"' EXIT

# Package directories
INSTALL_DIR="$BUILD_ROOT/usr/lib/$PKG_NAME"
BIN_DIR="$BUILD_ROOT/usr/bin"
DESKTOP_DIR="$BUILD_ROOT/usr/share/applications"
CONTROL_DIR="$BUILD_ROOT/DEBIAN"

mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$CONTROL_DIR"

# Copy binary or onedir bundle
if [ -d "$DIST_BIN_PATH" ]; then
    cp -a "$DIST_BIN_PATH/." "$INSTALL_DIR/"
else
    cp "$DIST_BIN_PATH" "$INSTALL_DIR/$APP_BIN_NAME"
fi
chmod -R a+rX,go-w "$INSTALL_DIR"
chmod 755 "$INSTALL_DIR/$APP_BIN_NAME"

# Create symlink in /usr/bin
ln -sf "/usr/lib/$PKG_NAME/$APP_BIN_NAME" "$BIN_DIR/$PKG_NAME"

# Create .desktop file
ICON_SRC="$SCRIPT_DIR/../../../assets/icons/$PKG_NAME.png"
ICON_LINE=""
if [ -f "$ICON_SRC" ]; then
    ICON_DIR="$BUILD_ROOT/usr/share/icons/hicolor/256x256/apps"
    mkdir -p "$ICON_DIR"
    cp "$ICON_SRC" "$ICON_DIR/$PKG_NAME.png"
    chmod 644 "$ICON_DIR/$PKG_NAME.png"
    ICON_LINE="Icon=$PKG_NAME"
fi

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
if [ -n "$ICON_LINE" ]; then
    echo "$ICON_LINE" >> "$DESKTOP_DIR/$PKG_NAME.desktop"
fi
chmod 644 "$DESKTOP_DIR/$PKG_NAME.desktop"

# Create control file
cat <<EOF > "$CONTROL_DIR/control"
Package: $PKG_NAME
Version: $DEB_VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: School Management System <admin@school.local>
Description: $APP_NAME desktop application for SMTE School System.
EOF

# Calculate size in KB
INSTALLED_SIZE=$(du -sk "$BUILD_ROOT" | cut -f1)
echo "Installed-Size: $INSTALLED_SIZE" >> "$CONTROL_DIR/control"

if [ "$PKG_NAME" = "librarianmanagement" ]; then
    cat <<'EOF' > "$CONTROL_DIR/postinst"
#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
    if command -v ufw >/dev/null 2>&1; then
        ufw allow 8765/tcp >/dev/null 2>&1 || true
        ufw allow 8766/udp >/dev/null 2>&1 || true
    fi
    if command -v firewall-cmd >/dev/null 2>&1; then
        firewall-cmd --permanent --add-port=8765/tcp --add-port=8766/udp >/dev/null 2>&1 || true
        firewall-cmd --reload >/dev/null 2>&1 || true
    fi
fi
exit 0
EOF
    cat <<'EOF' > "$CONTROL_DIR/prerm"
#!/bin/sh
set -e
case "$1" in
    remove|purge)
        if command -v ufw >/dev/null 2>&1; then
            ufw delete allow 8765/tcp >/dev/null 2>&1 || true
            ufw delete allow 8766/udp >/dev/null 2>&1 || true
        fi
        if command -v firewall-cmd >/dev/null 2>&1; then
            firewall-cmd --permanent --remove-port=8765/tcp --remove-port=8766/udp >/dev/null 2>&1 || true
            firewall-cmd --reload >/dev/null 2>&1 || true
        fi
        ;;
esac
exit 0
EOF
    chmod 755 "$CONTROL_DIR/postinst" "$CONTROL_DIR/prerm"
fi

DEB_FILE="$OUTPUT_DIR/${PKG_NAME}_${DEB_VERSION}_${ARCH}.deb"
dpkg-deb --build --root-owner-group "$BUILD_ROOT" "$DEB_FILE"

echo "Created DEB: $DEB_FILE"
