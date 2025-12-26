#!/bin/bash
# Script para construir Flatpak de XLAMP

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Construyendo Flatpak de XLAMP${NC}"
echo -e "${GREEN}========================================${NC}"

# Verificar flatpak-builder
if ! command -v flatpak-builder &> /dev/null; then
    echo -e "${RED}Error: flatpak-builder no está instalado${NC}"
    echo -e "Instálalo con: ${YELLOW}sudo apt install flatpak-builder${NC}"
    exit 1
fi

# Verificar runtime
echo -e "\n${YELLOW}Verificando runtime de GNOME...${NC}"
if ! flatpak list --runtime | grep -q "org.gnome.Platform.*45"; then
    echo -e "${YELLOW}Instalando runtime de GNOME 45...${NC}"
    flatpak install -y flathub org.gnome.Platform//45 org.gnome.Sdk//45
fi

# Limpiar construcciones anteriores
echo -e "\n${YELLOW}Limpiando construcciones anteriores...${NC}"
rm -rf build-dir .flatpak-builder

# Construir
echo -e "\n${YELLOW}Construyendo Flatpak...${NC}"
flatpak-builder --force-clean build-dir io.github.xlamp.yml

# Crear repositorio local
echo -e "\n${YELLOW}Creando repositorio local...${NC}"
flatpak-builder --repo=repo --force-clean build-dir io.github.xlamp.yml

# Crear bundle (archivo .flatpak)
echo -e "\n${YELLOW}Creando bundle flatpak...${NC}"
flatpak build-bundle repo xlamp.flatpak io.github.xlamp

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}   ¡Flatpak construido exitosamente!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\nArchivo creado: ${GREEN}xlamp.flatpak${NC}"
echo -e "\nPara instalar:"
echo -e "  ${YELLOW}flatpak install --user xlamp.flatpak${NC}"
echo -e "\nPara ejecutar:"
echo -e "  ${YELLOW}flatpak run io.github.xlamp${NC}"

echo -e "\n${GREEN}¡Listo!${NC}"
