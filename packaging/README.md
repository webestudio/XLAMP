# Empaquetado de XLAMP

Este directorio contiene los archivos y scripts necesarios para crear diferentes tipos de instaladores para XLAMP.

## Tipos de Paquetes Disponibles

### 1. Paquete Debian (.deb)
**Recomendado para**: Elementary OS, Ubuntu, Debian y derivados

#### Construir:
```bash
cd /home/jorge/Documentos/XLAMP
chmod +x packaging/build_deb.sh
./packaging/build_deb.sh
```

#### Instalar:
```bash
sudo dpkg -i ../xlamp_1.0.0_all.deb
sudo apt-get install -f  # Resolver dependencias
```

#### Desinstalar:
```bash
sudo apt remove xlamp
```

---

### 2. Flatpak
**Recomendado para**: Cualquier distribución Linux moderna

#### Requisitos previos:
```bash
sudo apt install flatpak flatpak-builder
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
```

#### Construir:
```bash
cd /home/jorge/Documentos/XLAMP/packaging/flatpak
chmod +x build_flatpak.sh
./build_flatpak.sh
```

#### Instalar:
```bash
flatpak install --user xlamp.flatpak
```

#### Ejecutar:
```bash
flatpak run io.github.xlamp
```

#### Desinstalar:
```bash
flatpak uninstall io.github.xlamp
```

---

### 3. AppImage
**Recomendado para**: Ejecución portable sin instalación

#### Construir:
```bash
cd /home/jorge/Documentos/XLAMP
chmod +x packaging/appimage/build_appimage.sh
./packaging/appimage/build_appimage.sh
```

#### Ejecutar:
```bash
chmod +x packaging/appimage/XLAMP-x86_64.AppImage
./packaging/appimage/XLAMP-x86_64.AppImage
```

#### "Instalar" (opcional - solo mover a PATH):
```bash
mkdir -p ~/bin
mv packaging/appimage/XLAMP-x86_64.AppImage ~/bin/xlamp
# Agregar ~/bin a PATH si no está
```

---

### 4. Instalación desde Código Fuente (setup.py)
**Recomendado para**: Desarrollo y testing

#### Instalar en modo desarrollo:
```bash
cd /home/jorge/Documentos/XLAMP
pip3 install -e .
```

#### Instalar sistema-wide:
```bash
cd /home/jorge/Documentos/XLAMP
sudo pip3 install .
```

#### Desinstalar:
```bash
sudo pip3 uninstall xlamp
```

---

## Comparación de Métodos

| Método | Ventajas | Desventajas |
|--------|----------|-------------|
| **DEB** | ✅ Nativo para tu sistema<br>✅ Integración completa<br>✅ Actualizaciones automáticas | ❌ Solo Debian/Ubuntu<br>❌ Requiere dependencias |
| **Flatpak** | ✅ Multi-distro<br>✅ Sandbox seguro<br>✅ Dependencias incluidas | ❌ Tamaño grande<br>❌ Requiere Flatpak runtime |
| **AppImage** | ✅ Portable<br>✅ Sin instalación<br>✅ Multi-distro | ❌ No auto-actualiza<br>❌ Sin integración sistema |
| **Source** | ✅ Siempre actualizado<br>✅ Modificable | ❌ Requiere Python<br>❌ Gestión manual |

---

## Estructura de Archivos

```
packaging/
├── README.md                      # Este archivo
├── build_deb.sh                   # Script para construir .deb
├── xlamp.desktop                  # Entrada del menú de aplicaciones
├── xlamp.policy                   # Reglas de PolicyKit
│
├── debian/                        # Paquete Debian
│   ├── control                    # Metadatos y dependencias
│   ├── rules                      # Reglas de construcción
│   ├── changelog                  # Historial de cambios
│   ├── compat                     # Versión de debhelper
│   └── copyright                  # Licencia
│
├── flatpak/                       # Paquete Flatpak
│   ├── io.github.xlamp.yml        # Manifiesto Flatpak
│   ├── io.github.xlamp.metainfo.xml  # Metadata AppStream
│   └── build_flatpak.sh           # Script de construcción
│
└── appimage/                      # AppImage portable
    └── build_appimage.sh          # Script de construcción
```

---

## Notas Importantes

### Permisos del Sistema
XLAMP requiere permisos elevados para:
- Instalar/desinstalar paquetes del sistema (Apache, MySQL, PHP)
- Crear/modificar hosts virtuales en `/var/www` y `/etc/apache2`
- Gestionar servicios del sistema (start/stop/restart)
- Modificar `/etc/hosts` para dominios .test

Todos los métodos de instalación configuran PolicyKit para solicitar contraseña cuando sea necesario.

### Dependencias
La aplicación requiere:
- Python 3.8+
- GTK 3.0
- PyGObject
- psutil
- Jinja2
- python-dotenv

Los paquetes .deb y Flatpak gestionan dependencias automáticamente.
AppImage las incluye en el bundle.
Source requiere instalación manual.

---

## Recomendaciones

**Para usuarios de Elementary OS/Ubuntu**: Usa el paquete **.deb**
- Mayor integración con el sistema
- Actualizaciones fáciles
- Gestión de dependencias automática

**Para otras distribuciones**: Usa **Flatpak**
- Compatible con cualquier distro moderna
- Sandbox seguro
- Actualizaciones automáticas

**Para testing/desarrollo**: Usa **Source** (setup.py)
- Cambios inmediatos
- Sin reconstruir paquetes

**Para portabilidad**: Usa **AppImage**
- Lleva XLAMP en USB
- Sin instalación requerida
- Funciona en cualquier Linux

---

## Soporte

Si encuentras problemas durante el empaquetado:

1. Verifica que todas las dependencias de construcción estén instaladas
2. Revisa los logs de construcción
3. Asegúrate de ejecutar los scripts desde los directorios correctos
4. Consulta la documentación específica de cada formato

Para reportar bugs: https://github.com/tu-usuario/xlamp/issues
