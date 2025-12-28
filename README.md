# XLAMP Manager

Aplicación GUI para gestionar el stack LAMP en Linux con soporte Flatpak.

## Características

- ✅ 16 componentes: Apache, MySQL, MariaDB, PHP, Node.js, Redis, Git, Composer, etc.
- ✅ Instalación/desinstalación con pkexec y flatpak-spawn
- ✅ Control de servicios (iniciar, detener, reiniciar)
- ✅ Selector de 4 versiones PHP (8.3, 8.2, 8.1, 8.0)
- ✅ Gestión automática de PATH
- ✅ Logs con rotación (2 MB máx, 3 backups)
- ✅ Diseño Flat moderno inspirado en Tailwind CSS

## Requisitos

- Python 3.10+
- GTK 3 (PyGObject)
- pkexec (PolicyKit)
- psutil

## Ejecución

```bash
./run.sh
# o
python3 src/main.py
```

## Configuración Opcional

### Evitar solicitudes repetidas de contraseña

Para evitar que PolicyKit solicite contraseña en cada operación de Apache:

```bash
# Instalar reglas de PolicyKit
./install_polkit_rules.sh

# Reiniciar PolicyKit (opcional)
sudo systemctl restart polkit
```

Esto permite que usuarios del grupo `sudo` gestionen Apache sin solicitudes repetidas de contraseña.

## Componentes Disponibles

**Servidores:** Apache, MySQL, MariaDB  
**Lenguajes:** PHP, Node.js  
**Caché:** Redis, Memcached, Varnish  
**Herramientas:** Git, Composer, Yarn, WP-CLI, PHPUnit  
**Interfaces Web:** phpMyAdmin, Adminer  
**Desarrollo:** Xdebug

## Estructura

```
XLAMP/
├── src/
│   ├── main.py           # Entrada principal
│   ├── ui/               # Interfaces GTK + CSS
│   ├── core/             # Instalador, detector, servicios
│   ├── data/             # SQLite + modelos
│   └── utils/            # Helpers + logging
├── logs/                 # Logs rotativos
├── resources/            # Iconos
└── run.sh                # Script de inicio
```

## Desarrollo

```bash
# Limpiar caché
find . -name "__pycache__" -exec rm -rf {} +

# Ver logs
tail -f logs/lamp_manager.log
```
