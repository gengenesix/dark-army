#!/bin/bash
set -e

VERSION="2.0.0"
PKG="echelon_${VERSION}_amd64"
echo "=== Building Echelon .deb package ==="

rm -rf "$PKG"
mkdir -p "${PKG}/DEBIAN"
mkdir -p "${PKG}/opt/echelon"
mkdir -p "${PKG}/usr/local/bin"
mkdir -p "${PKG}/usr/share/applications"
mkdir -p "${PKG}/usr/share/icons/hicolor/256x256/apps"
mkdir -p "${PKG}/usr/share/icons/hicolor/48x48/apps"

cat > "${PKG}/DEBIAN/control" << EOF
Package: echelon
Version: ${VERSION}
Section: video
Priority: optional
Architecture: amd64
Depends: libgl1, libglib2.0-0, libxcb-xinerama0, libxcb-icccm4, libxcb-cursor0
Maintainer: Zero <zero@echelon.app>
Description: Real-time face swap for video calls
 Echelon lets you swap your face in real-time during video calls.
 Works with Zoom, Google Meet, Discord, WhatsApp, and Teams.
 Created by Zero.
EOF

cat > "${PKG}/DEBIAN/postinst" << 'EOF'
#!/bin/bash
modprobe v4l2loopback devices=1 video_nr=10 card_label="Echelon Camera" exclusive_caps=1 2>/dev/null || true
update-desktop-database /usr/share/applications 2>/dev/null || true
gtk-update-icon-cache -f /usr/share/icons/hicolor/ 2>/dev/null || true
echo ""
echo "✅ Echelon installed successfully!"
echo "   Find it in your app menu, or run: echelon"
echo ""
EOF
chmod 755 "${PKG}/DEBIAN/postinst"

cat > "${PKG}/DEBIAN/prerm" << 'EOF'
#!/bin/bash
pkill -f "Echelon" 2>/dev/null || true
EOF
chmod 755 "${PKG}/DEBIAN/prerm"

# Copy binary
cp -r dist/Echelon/* "${PKG}/opt/echelon/"

# Launcher
cat > "${PKG}/usr/local/bin/echelon" << 'EOF'
#!/bin/bash
export ALBUMENTATIONS_DISABLE_VERSION_CHECK=1
export NO_ALBUMENTATIONS_UPDATE=1
export MPLBACKEND=Agg
export MPLCONFIGDIR="${HOME}/.cache/matplotlib"
cd /opt/echelon
exec ./Echelon "$@"
EOF
chmod +x "${PKG}/usr/local/bin/echelon"

# Desktop file
cat > "${PKG}/usr/share/applications/echelon.desktop" << 'EOF'
[Desktop Entry]
Name=Echelon
GenericName=Face Swap
Comment=Real-time face swap for video calls — by Zero
Exec=/usr/local/bin/echelon
Icon=echelon
Terminal=false
Type=Application
Categories=Video;AudioVideo;Graphics;
StartupNotify=false
EOF

# Icons
cp assets/icons/icon_256.png "${PKG}/usr/share/icons/hicolor/256x256/apps/echelon.png"
cp assets/icons/icon_48.png  "${PKG}/usr/share/icons/hicolor/48x48/apps/echelon.png"

# Build
dpkg-deb --build "$PKG"
echo "Deb built: $(du -sh ${PKG}.deb)"
