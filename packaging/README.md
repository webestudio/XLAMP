# Empaquetado de XLAMP

Este directorio contiene los archivos necesarios para crear el instalador de XLAMP para Elementary OS/Ubuntu.

## 📦 Paquete Debian (.deb)
**Recomendado para**: Elementary OS, Ubuntu, Debian y derivados

### Requisitos Previos

Instalar herramientas de construcción (solo la primera vez):
```bash
sudo apt-get update
sudo apt-get install -y debhelper dh-python python3-all python3-setuptools devscripts build-essential
```

### Construir el Paquete

**Importante**: Ejecuta desde una terminal del sistema (NO desde VSCode):

```bash
cd /home/jorge/Documentos/XLAMP
./packaging/build_deb.sh
```

El script:
1. Verifica e instala dependencias de construcción
2. Construye el paquete .deb
3. Crea el archivo `../xlamp_1.0.0_all.deb`

### Instalar

```bash
sudo dpkg -i ../xlamp_1.0.0_all.deb
sudo apt-get install -f  # Resolver dependencias
```

### Desinstalar

```bash
sudo apt remove xlamp
```

### Ejecutar

Después de instalar:
- Busca "XLAMP" en el menú de aplicaciones
- O ejecuta desde terminal: `xlamp`

---

## 🐍 Instalación desde Código Fuente

Para desarrollo o si prefieres no usar el paquete .deb:

### Instalar en modo desarrollo:
```bash
cd /home/jorge/Documentos/XLAMP
pip3 install -e .
```

### Instalar sistema-wide:
```bash
cd /home/jorge/Documentos/XLAMP
sudo pip3 install .
```

### Desinstalar:
```bash
sudo pip3 uninstall xlamp
```

### Ejecutar (sin instalar):
```bash
cd /home/jorge/Documentos/XLAMP
python3 -m src.main
# o
./run.sh
```

---

## 📋 Comparación de Métodos

| Método | Ventajas | Desventajas | Recomendado Para |
|--------|----------|-------------|------------------|
| **DEB** | ✅ Integración completa con el sistema<br>✅ Actualizaciones con apt<br>✅ Gestión automática de dependencias<br>✅ Entrada en el menú de aplicaciones | ❌ Solo Debian/Ubuntu | **Usuarios finales de Elementary OS** |
| **Source** | ✅ Siempre actualizado<br>✅ Fácil de modificar<br>✅ Sin reconstruir paquetes | ❌ Sin integración con el sistema<br>❌ Gestión manual de dependencias | **Desarrollo y testing** |

---

## 📁 Estructura de Archivos

```
packaging/
├── README.md                      # Este archivo
├── INSTRUCCIONES.md              # Guía detallada paso a paso
├── build_deb.sh                  # Script para construir .deb
├── xlamp.desktop                 # Entrada del menú de aplicaciones
├── xlamp.policy                  # Reglas de PolicyKit
│
└── debian/                       # Paquete Debian
    ├── control                   # Metadatos y dependencias
    ├── rules                     # Reglas de construcción
    ├── changelog                 # Historial de cambios
    ├── compat                    # Versión de debhelper
    └── copyright                 # Licencia
```

---

## 🔒 Permisos del Sistema

XLAMP requiere permisos elevados para:
- Instalar/desinstalar paquetes del sistema (Apache, MySQL, PHP)
- Crear/modificar hosts virtuales en `/var/www` y `/etc/apache2`
- Gestionar servicios del sistema (start/stop/restart)
- Modificar `/etc/hosts` para dominios .test

El paquete .deb configura PolicyKit automáticamente para solicitar contraseña cuando sea necesario.

---

## 📦 Dependencias

La aplicación requiere:
- Python 3.8+
- GTK 3.0
- PyGObject
- psutil
- Jinja2
- python-dotenv

**El paquete .deb instala todas las dependencias automáticamente.**

---

## 🚀 Recomendación Final

**Para usuarios de Elementary OS (tu caso):**
```bash
# Construir e instalar de una vez:
cd /home/jorge/Documentos/XLAMP
./packaging/build_deb.sh
sudo dpkg -i ../xlamp_1.0.0_all.deb
sudo apt-get install -f
```

Esto te dará la mejor experiencia con integración completa del sistema.

---

## 🐛 Solución de Problemas

### Error: "dpkg: orden no encontrada"
**Solución**: Ejecuta desde una terminal del sistema (no desde VSCode Flatpak)

### Error: "Unmet build dependencies"
**Solución**: El script las instalará automáticamente, solo confirma con tu contraseña

### Error durante la construcción
**Solución**: Limpia y reconstruye:
```bash
cd /home/jorge/Documentos/XLAMP
rm -rf debian/ .pybuild/
./packaging/build_deb.sh
```

---

## 📞 Soporte

Para reportar problemas: https://github.com/tu-usuario/xlamp/issues
