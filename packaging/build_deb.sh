#!/bin/bash
# Script para construir el paquete .deb de XLAMP

set -e

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Construyendo paquete .deb XLAMP${NC}"
echo -e "${GREEN}========================================${NC}"

# Verificar que estamos en el directorio correcto
if [ ! -f "setup.py" ]; then
    echo -e "${RED}Error: Ejecuta este script desde el directorio raíz del proyecto${NC}"
    exit 1
fi

# Detectar si estamos en flatpak y usar flatpak-spawn
if [ -f "/.flatpak-info" ]; then
    echo -e "${YELLOW}Detectado entorno Flatpak, usando flatpak-spawn...${NC}"
    CMD_PREFIX="flatpak-spawn --host"
else
    CMD_PREFIX=""
fi

# Verificar dependencias de construcción
echo -e "\n${YELLOW}Verificando dependencias de construcción...${NC}"
DEPS=(debhelper dh-python python3-all python3-setuptools devscripts build-essential)
MISSING=()

for dep in "${DEPS[@]}"; do
    if ! $CMD_PREFIX dpkg -l 2>/dev/null | grep -q "^ii  $dep"; then
        MISSING+=("$dep")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    echo -e "${YELLOW}Instalando dependencias faltantes: ${MISSING[*]}${NC}"
    $CMD_PREFIX sudo apt-get update
    $CMD_PREFIX sudo apt-get install -y "${MISSING[@]}"
fi

# Limpiar construcciones anteriores
echo -e "\n${YELLOW}Limpiando construcciones anteriores...${NC}"
rm -rf debian/
rm -f ../xlamp_*.deb ../xlamp_*.dsc ../xlamp_*.tar.* ../xlamp_*.changes ../xlamp_*.buildinfo

# Copiar archivos de debian
echo -e "\n${YELLOW}Preparando estructura debian/...${NC}"
cp -r packaging/debian .

# Construir el paquete
echo -e "\n${YELLOW}Construyendo paquete .deb...${NC}"
$CMD_PREFIX dpkg-buildpackage -us -uc -b

# Verificar resultado
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}   ¡Paquete .deb construido exitosamente!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "\nPaquete creado en: ${GREEN}../xlamp_*.deb${NC}"
    echo -e "\nPara instalar:"
    echo -e "  ${YELLOW}$CMD_PREFIX sudo dpkg -i ../xlamp_*.deb${NC}"
    echo -e "  ${YELLOW}$CMD_PREFIX sudo apt-get install -f${NC}  # Para resolver dependencias"
else
    echo -e "\n${RED}Error al construir el paquete${NC}"
    exit 1
fi

# Limpiar
echo -e "\n${YELLOW}Limpiando archivos temporales...${NC}"
rm -rf debian/

echo -e "\n${GREEN}¡Listo!${NC}"
