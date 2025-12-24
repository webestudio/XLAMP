#!/bin/bash
# Script de inicio rápido para desarrollo

echo "Iniciando LAMP Manager..."

# Verificar que estemos en el directorio correcto
if [ ! -f "src/main.py" ]; then
    echo "Error: Ejecuta este script desde el directorio raíz del proyecto"
    exit 1
fi

# Definir ruta del entorno virtual
VENV_DIR=".venv"

# Verificar dependencias críticas
echo "Verificando dependencias..."
python3 -c "import gi; import psutil" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Faltan dependencias de Python"
    
    # Crear entorno virtual si no existe
    if [ ! -d "$VENV_DIR" ]; then
        echo "Creando entorno virtual..."
        python3 -m venv "$VENV_DIR"
        if [ $? -ne 0 ]; then
            echo ""
            echo "❌ No se pudo crear el entorno virtual"
            echo ""
            echo "Por favor, instala python3-venv:"
            echo "  sudo apt install python3-venv python3-psutil python3-dotenv python3-jinja2 python3-gi"
            echo ""
            exit 1
        fi
        echo "✓ Entorno virtual creado"
    fi
    
    # Activar entorno virtual e instalar dependencias
    echo "Instalando dependencias en entorno virtual..."
    source "$VENV_DIR/bin/activate"
    
    # Instalar PyGObject desde sistema (no puede instalarse con pip fácilmente)
    # Las demás dependencias se instalan con pip
    pip install --quiet psutil python-dotenv Jinja2
    
    if [ $? -ne 0 ]; then
        echo ""
        echo "❌ Error al instalar dependencias"
        echo ""
        echo "Instala las dependencias del sistema:"
        echo "  sudo apt install python3-venv python3-psutil python3-dotenv python3-jinja2 python3-gi"
        echo ""
        exit 1
    fi
    
    echo "✓ Dependencias instaladas"
fi

# Crear directorios necesarios
mkdir -p data logs backups

# Ejecutar aplicación (usando venv si existe)
cd src
if [ -d "../$VENV_DIR" ] && [ -f "../$VENV_DIR/bin/python3" ]; then
    exec "../$VENV_DIR/bin/python3" main.py
else
    exec python3 main.py
fi
