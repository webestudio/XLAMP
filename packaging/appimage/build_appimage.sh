#!/bin/bash
# Script para construir AppImage de XLAMP

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Construyendo AppImage de XLAMP${NC}"
echo -e "${GREEN}========================================${NC}"

# Verificar que estamos en el directorio correcto
PROJECT_ROOT="$(cd ../.. && pwd)"
cd "$PROJECT_ROOT"

# Crear directorio AppDir
echo -e "\n${YELLOW}Creando estructura AppDir...${NC}"
APPDIR="packaging/appimage/XLAMP.AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/lib"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$APPDIR/usr/share/xlamp"

# Copiar aplicación
echo -e "\n${YELLOW}Copiando archivos de la aplicación...${NC}"
cp -r src "$APPDIR/usr/share/xlamp/"
cp -r data "$APPDIR/usr/share/xlamp/"
cp -r resources "$APPDIR/usr/share/xlamp/" 2>/dev/null || true
cp requirements.txt "$APPDIR/usr/share/xlamp/"
cp icon.png "$APPDIR/usr/share/icons/hicolor/256x256/apps/xlamp.png"

# Crear script de ejecución
cat > "$APPDIR/usr/bin/xlamp" << 'EOF'
#!/bin/bash
APPDIR="$(dirname "$(readlink -f "$0")")/.."
export PYTHONPATH="$APPDIR/usr/share/xlamp:$PYTHONPATH"
export LD_LIBRARY_PATH="$APPDIR/usr/lib:$LD_LIBRARY_PATH"
cd "$APPDIR/usr/share/xlamp"
exec python3 -m src.main "$@"
EOF
chmod +x "$APPDIR/usr/bin/xlamp"

# AppRun
cat > "$APPDIR/AppRun" << 'EOF'
#!/bin/bash
APPDIR="$(dirname "$(readlink -f "$0")")"
export PATH="$APPDIR/usr/bin:$PATH"
export LD_LIBRARY_PATH="$APPDIR/usr/lib:$LD_LIBRARY_PATH"
export PYTHONPATH="$APPDIR/usr/share/xlamp:$PYTHONPATH"
exec "$APPDIR/usr/bin/xlamp" "$@"
EOF
chmod +x "$APPDIR/AppRun"

# Desktop file
cp packaging/xlamp.desktop "$APPDIR/usr/share/applications/"
cp packaging/xlamp.desktop "$APPDIR/"
cp icon.png "$APPDIR/xlamp.png"
ln -sf usr/share/icons/hicolor/256x256/apps/xlamp.png "$APPDIR/.DirIcon"

# Verificar Python dependencies
echo -e "\n${YELLOW}Verificando dependencias de Python...${NC}"
python3 -m pip install --target="$APPDIR/usr/lib/python3/dist-packages" -r requirements.txt

# Descargar appimagetool si no existe
APPIMAGETOOL="packaging/appimage/appimagetool-x86_64.AppImage"
if [ ! -f "$APPIMAGETOOL" ]; then
    echo -e "\n${YELLOW}Descargando appimagetool...${NC}"
    wget -O "$APPIMAGETOOL" \
        "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "$APPIMAGETOOL"
fi

# Construir AppImage
echo -e "\n${YELLOW}Construyendo AppImage...${NC}"
ARCH=x86_64 "$APPIMAGETOOL" "$APPDIR" "packaging/appimage/XLAMP-x86_64.AppImage"

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}   ¡AppImage construido exitosamente!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "\nArchivo creado: ${GREEN}packaging/appimage/XLAMP-x86_64.AppImage${NC}"
    echo -e "\nPara ejecutar:"
    echo -e "  ${YELLOW}./packaging/appimage/XLAMP-x86_64.AppImage${NC}"
    echo -e "\nPara instalar:"
    echo -e "  ${YELLOW}chmod +x packaging/appimage/XLAMP-x86_64.AppImage${NC}"
    echo -e "  ${YELLOW}mv packaging/appimage/XLAMP-x86_64.AppImage ~/bin/xlamp${NC}"
else
    echo -e "\n${RED}Error al construir AppImage${NC}"
    exit 1
fi

echo -e "\n${GREEN}¡Listo!${NC}"
