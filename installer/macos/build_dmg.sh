#!/usr/bin/env bash
# Gera .app + DMG a partir do binário PyInstaller (python/dist/SwiftSend).
# Uso:
#   ./installer/macos/build_dmg.sh [VERSION] [--skip-build]
# Saída:
#   installer/output/SwiftSend-VERSION-macos-ARCH.dmg
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY_DIR="$ROOT/python"
BIN="$PY_DIR/dist/SwiftSend"
OUT_DIR="$ROOT/installer/output"
STAGE="$OUT_DIR/dmg-stage"
APP_NAME="SwiftSend.app"
ICON_PNG="$ROOT/shared/static/icon.png"
VERSION="0.0.0-dev"
SKIP_BUILD=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-build) SKIP_BUILD=1 ;;
    *) VERSION="${1#v}" ;;
  esac
  shift
done

ARCH="$(uname -m)"
case "$ARCH" in
  arm64|aarch64) ARCH_LABEL=arm64 ;;
  x86_64) ARCH_LABEL=amd64 ;;
  *) ARCH_LABEL="$ARCH" ;;
esac

echo "=== SwiftSend DMG (macOS) ==="
echo "Repo:    $ROOT"
echo "Version: $VERSION"
echo "Arch:    $ARCH_LABEL"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Este script só roda no macOS." >&2
  exit 1
fi

if [[ "$SKIP_BUILD" -eq 0 ]]; then
  echo
  echo "--- PyInstaller (python/build.py) ---"
  (cd "$PY_DIR" && python3 build.py || python build.py)
fi

if [[ ! -f "$BIN" ]]; then
  echo "Executável não encontrado: $BIN" >&2
  echo "Rode sem --skip-build ou gere o PyInstaller antes." >&2
  exit 1
fi

chmod +x "$BIN"
rm -rf "$STAGE"
mkdir -p "$STAGE/$APP_NAME/Contents/MacOS" "$STAGE/$APP_NAME/Contents/Resources"

cp "$BIN" "$STAGE/$APP_NAME/Contents/MacOS/SwiftSend"
chmod +x "$STAGE/$APP_NAME/Contents/MacOS/SwiftSend"

# Ícone .icns a partir do PNG (opcional)
ICNS="$STAGE/$APP_NAME/Contents/Resources/SwiftSend.icns"
ICON_NAME=""
if [[ -f "$ICON_PNG" ]] && command -v sips >/dev/null && command -v iconutil >/dev/null; then
  ICONSET="$OUT_DIR/SwiftSend.iconset"
  rm -rf "$ICONSET"
  mkdir -p "$ICONSET"
  for size in 16 32 64 128 256 512; do
    sips -z "$size" "$size" "$ICON_PNG" --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
    sips -z $((size * 2)) $((size * 2)) "$ICON_PNG" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
  done
  iconutil -c icns "$ICONSET" -o "$ICNS"
  rm -rf "$ICONSET"
  ICON_NAME="SwiftSend"
fi

cat > "$STAGE/$APP_NAME/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>
  <string>SwiftSend</string>
  <key>CFBundleDisplayName</key>
  <string>SwiftSend</string>
  <key>CFBundleIdentifier</key>
  <string>com.swiftsend.app</string>
  <key>CFBundleVersion</key>
  <string>${VERSION}</string>
  <key>CFBundleShortVersionString</key>
  <string>${VERSION}</string>
  <key>CFBundleExecutable</key>
  <string>SwiftSend</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>LSMinimumSystemVersion</key>
  <string>11.0</string>
  <key>NSHighResolutionCapable</key>
  <true/>
EOF

if [[ -n "$ICON_NAME" ]]; then
  cat >> "$STAGE/$APP_NAME/Contents/Info.plist" <<EOF
  <key>CFBundleIconFile</key>
  <string>${ICON_NAME}</string>
EOF
fi

cat >> "$STAGE/$APP_NAME/Contents/Info.plist" <<'EOF'
</dict>
</plist>
EOF

mkdir -p "$OUT_DIR"
DMG_OUT="$OUT_DIR/SwiftSend-${VERSION}-macos-${ARCH_LABEL}.dmg"
rm -f "$DMG_OUT"

echo
echo "--- hdiutil ---"
hdiutil create \
  -volname "SwiftSend" \
  -srcfolder "$STAGE" \
  -ov \
  -format UDZO \
  "$DMG_OUT"

echo
echo "SUCESSO: $DMG_OUT"
echo "Arraste SwiftSend.app para /Applications. Dados do usuário: ~/Documents/SwiftSend"
