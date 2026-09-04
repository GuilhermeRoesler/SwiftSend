#!/usr/bin/env bash
# Gera AppImage a partir do binário PyInstaller (python/dist/SwiftSend).
# Uso:
#   ./installer/linux/build_appimage.sh [VERSION] [--skip-build]
# Saída:
#   installer/output/SwiftSend-VERSION-x86_64.AppImage
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY_DIR="$ROOT/python"
BIN="$PY_DIR/dist/SwiftSend"
OUT_DIR="$ROOT/installer/output"
APPDIR="$OUT_DIR/SwiftSend.AppDir"
DESKTOP_SRC="$ROOT/installer/linux/SwiftSend.desktop"
ICON_SRC="$ROOT/shared/static/icon.png"
VERSION="0.0.0-dev"
SKIP_BUILD=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-build) SKIP_BUILD=1 ;;
    *) VERSION="${1#v}" ;;
  esac
  shift
done

echo "=== SwiftSend AppImage ==="
echo "Repo:    $ROOT"
echo "Version: $VERSION"

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
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/256x256/apps"
cp "$BIN" "$APPDIR/usr/bin/SwiftSend"
chmod +x "$APPDIR/usr/bin/SwiftSend"

cp "$DESKTOP_SRC" "$APPDIR/SwiftSend.desktop"
cp "$DESKTOP_SRC" "$APPDIR/usr/share/applications/SwiftSend.desktop"

if [[ -f "$ICON_SRC" ]]; then
  cp "$ICON_SRC" "$APPDIR/SwiftSend.png"
  cp "$ICON_SRC" "$APPDIR/usr/share/icons/hicolor/256x256/apps/SwiftSend.png"
fi

cat > "$APPDIR/AppRun" <<'EOF'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/SwiftSend" "$@"
EOF
chmod +x "$APPDIR/AppRun"

mkdir -p "$OUT_DIR"
ARCH="$(uname -m)"
case "$ARCH" in
  x86_64|amd64) APPIMAGE_ARCH=x86_64 ;;
  aarch64|arm64) APPIMAGE_ARCH=aarch64 ;;
  *) APPIMAGE_ARCH="$ARCH" ;;
esac

TOOL="$OUT_DIR/appimagetool-$APPIMAGE_ARCH.AppImage"
if [[ ! -x "$TOOL" ]]; then
  echo
  echo "--- Baixando appimagetool ---"
  URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${APPIMAGE_ARCH}.AppImage"
  curl -fsSL -o "$TOOL" "$URL"
  chmod +x "$TOOL"
fi

APPIMAGE_OUT="$OUT_DIR/SwiftSend-${VERSION}-${APPIMAGE_ARCH}.AppImage"
rm -f "$APPIMAGE_OUT"

echo
echo "--- appimagetool ---"
# Em CI (sem FUSE): --appimage-extract-and-run
export APPIMAGE_EXTRACT_AND_RUN=1
"$TOOL" "$APPDIR" "$APPIMAGE_OUT"

chmod +x "$APPIMAGE_OUT"
echo
echo "SUCESSO: $APPIMAGE_OUT"
echo "Requisito runtime: GTK 3 + WebKitGTK (ex.: libgtk-3-0, libwebkit2gtk-4.1-0)."
echo "Dados do usuário: ~/Documents/SwiftSend"
