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

cat <<EOF > "$SPEC_FILE"
Name:           $PKG_NAME
Version:        $VERSION
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

cp "$DIST_BIN_PATH" %{buildroot}/usr/lib/$PKG_NAME/$APP_BIN_NAME
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
DESKTOP
chmod 644 %{buildroot}/usr/share/applications/$PKG_NAME.desktop

%files
/usr/lib/$PKG_NAME/$APP_BIN_NAME
/usr/bin/$PKG_NAME
/usr/share/applications/$PKG_NAME.desktop

%changelog
* Fri Oct 02 2026 Admin <admin@school.local> - $VERSION-1
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
