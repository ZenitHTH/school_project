#!/usr/bin/env bash
set -euo pipefail

APP_NAME="${1:-StudentManagement}"
APP_BIN_NAME="${2:-StudentManagement}"
PKG_NAME=$(echo "$APP_NAME" | tr '[:upper:]' '[:lower:]' | tr '_' '-')
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_VERSION_FILE="$SCRIPT_DIR/../../../VERSION"
DEFAULT_VERSION=$( [ -f "$REPO_VERSION_FILE" ] && tr -d '[:space:]' < "$REPO_VERSION_FILE" || echo "0.0.0" )
VERSION="${3:-$DEFAULT_VERSION}"
RPM_VERSION="${VERSION//-/~}"
DIST_BIN_PATH="${4:-dist/$APP_BIN_NAME}"
OUTPUT_DIR="${5:-dist/installers}"

if [ ! -f "$DIST_BIN_PATH" ]; then
    echo "Error: Binary not found at $DIST_BIN_PATH"
    exit 1
fi
ABS_DIST_BIN_PATH="$(cd "$(dirname "$DIST_BIN_PATH")" && pwd)/$(basename "$DIST_BIN_PATH")"

ARCH="${6:-$(uname -m)}"
case "$ARCH" in
    x86_64|amd64) ARCH="x86_64" ;;
    aarch64|arm64) ARCH="aarch64" ;;
esac

mkdir -p "$OUTPUT_DIR"

RPM_TOPDIR=$(mktemp -d -t rpm-build-XXXXXX)
trap 'rm -rf "$RPM_TOPDIR"' EXIT

mkdir -p "$RPM_TOPDIR"/{BUILD,RPMS,SOURCES,SPECS,SRPMS,BUILDROOT}

SPEC_FILE="$RPM_TOPDIR/SPECS/$PKG_NAME.spec"
ICON_SRC="$SCRIPT_DIR/../../../assets/icons/$PKG_NAME.png"
ABS_ICON_PATH=""
ICON_DESKTOP_LINE=""
ICON_FILE_ENTRY=""
if [ -f "$ICON_SRC" ]; then
    ABS_ICON_PATH="$(cd "$(dirname "$ICON_SRC")" && pwd)/$(basename "$ICON_SRC")"
    ICON_DESKTOP_LINE="Icon=$PKG_NAME"
    ICON_FILE_ENTRY="/usr/share/icons/hicolor/256x256/apps/$PKG_NAME.png"
fi

cat <<EOF > "$SPEC_FILE"
Name:           $PKG_NAME
Version:        $RPM_VERSION
Release:        1%{?dist}
Summary:        $APP_NAME desktop application for SMTE School System
License:        Proprietary
BuildArch:      $ARCH

%description
$APP_NAME desktop application for SMTE School System.

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/usr/lib/$PKG_NAME
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/usr/share/applications

cp "$ABS_DIST_BIN_PATH" %{buildroot}/usr/lib/$PKG_NAME/$APP_BIN_NAME
chmod 755 %{buildroot}/usr/lib/$PKG_NAME/$APP_BIN_NAME
ln -sf /usr/lib/$PKG_NAME/$APP_BIN_NAME %{buildroot}/usr/bin/$PKG_NAME

cat <<DESKTOP > %{buildroot}/usr/share/applications/$PKG_NAME.desktop
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_NAME
Comment=School Management System - $APP_NAME
Exec=/usr/bin/$PKG_NAME
Terminal=false
Categories=Education;Office;
$ICON_DESKTOP_LINE
DESKTOP
chmod 644 %{buildroot}/usr/share/applications/$PKG_NAME.desktop
EOF

if [ -n "$ABS_ICON_PATH" ]; then
    cat <<EOF >> "$SPEC_FILE"
mkdir -p %{buildroot}/usr/share/icons/hicolor/256x256/apps
cp "$ABS_ICON_PATH" %{buildroot}/usr/share/icons/hicolor/256x256/apps/$PKG_NAME.png
chmod 644 %{buildroot}/usr/share/icons/hicolor/256x256/apps/$PKG_NAME.png
EOF
fi

cat <<EOF >> "$SPEC_FILE"

%files
/usr/lib/$PKG_NAME/$APP_BIN_NAME
/usr/bin/$PKG_NAME
/usr/share/applications/$PKG_NAME.desktop
$ICON_FILE_ENTRY
EOF

if [ "$PKG_NAME" = "librarianmanagement" ]; then
    cat <<'EOF' >> "$SPEC_FILE"

%post
if command -v firewall-cmd >/dev/null 2>&1; then
    firewall-cmd --permanent --add-port=8765/tcp --add-port=8766/udp >/dev/null 2>&1 || true
    firewall-cmd --reload >/dev/null 2>&1 || true
fi
if command -v ufw >/dev/null 2>&1; then
    ufw allow 8765/tcp >/dev/null 2>&1 || true
    ufw allow 8766/udp >/dev/null 2>&1 || true
fi

%postun
if [ "$1" -eq 0 ]; then
    if command -v firewall-cmd >/dev/null 2>&1; then
        firewall-cmd --permanent --remove-port=8765/tcp --remove-port=8766/udp >/dev/null 2>&1 || true
        firewall-cmd --reload >/dev/null 2>&1 || true
    fi
    if command -v ufw >/dev/null 2>&1; then
        ufw delete allow 8765/tcp >/dev/null 2>&1 || true
        ufw delete allow 8766/udp >/dev/null 2>&1 || true
    fi
fi
EOF
fi

cat <<EOF >> "$SPEC_FILE"

%changelog
* Fri Oct 02 2026 Admin <admin@school.local> - $RPM_VERSION-1
- Package built for $APP_NAME
EOF

rpmbuild --define "_topdir $RPM_TOPDIR" -bb "$SPEC_FILE"

RPM_RESULT=$(find "$RPM_TOPDIR/RPMS" -type f -name "*.rpm" | head -n 1)
if [ -n "$RPM_RESULT" ]; then
    cp "$RPM_RESULT" "$OUTPUT_DIR/"
    echo "Created RPM: $OUTPUT_DIR/$(basename "$RPM_RESULT")"
else
    echo "Error: RPM build failed to produce file."
    exit 1
fi
