# 📦 Instrucciones para Construir el Paquete .deb

## ⚠️ IMPORTANTE: Ejecutar desde Terminal del Sistema

**NO ejecutes este script desde la terminal integrada de VSCode** si VSCode está instalado como Flatpak.

### ✅ Método Correcto

Abre una **terminal del sistema** (Aplicaciones → Terminal) y ejecuta:

```bash
cd /home/jorge/Documentos/XLAMP
./packaging/build_deb.sh
```

### 📋 Pasos Detallados

1. **Abrir Terminal del Sistema**
   - Presiona `Super` (tecla Windows)
   - Busca "Terminal" o "Consola"
   - Abre la aplicación de terminal nativa

2. **Navegar al Proyecto**
   ```bash
   cd /home/jorge/Documentos/XLAMP
   ```

3. **Ejecutar el Script de Construcción**
   ```bash
   ./packaging/build_deb.sh
   ```

4. **Instalar Dependencias** (si es la primera vez)
   
   El script te pedirá contraseña para instalar:
   - debhelper
   - dh-python
   - python3-all
   - python3-setuptools
   - devscripts
   - build-essential

5. **Esperar la Construcción**
   
   El proceso tomará unos minutos y generará:
   - `../xlamp_1.0.0_all.deb` - El paquete instalable
   - Varios archivos auxiliares

6. **Instalar el Paquete**
   ```bash
   sudo dpkg -i ../xlamp_1.0.0_all.deb
   sudo apt-get install -f  # Resolver dependencias si es necesario
   ```

### 🐛 Solución de Problemas

#### Error: "dpkg: orden no encontrada"
**Causa:** Estás ejecutando desde VSCode Flatpak  
**Solución:** Usa la terminal del sistema nativa

#### Error: "Unmet build dependencies"
**Causa:** Faltan dependencias de construcción  
**Solución:** El script las instalará automáticamente

#### Error: "debian/rules no es ejecutable"
**Causa:** Permisos incorrectos  
**Solución:** Ya corregido automáticamente

### 📍 Ubicación del Paquete

Después de construir exitosamente:

```
/home/jorge/Documentos/
├── XLAMP/                    # Tu proyecto
└── xlamp_1.0.0_all.deb      # Paquete generado (un nivel arriba)
```

### 🚀 Uso Rápido (Copy-Paste)

```bash
# Abrir terminal del sistema y ejecutar todo de una vez:
cd /home/jorge/Documentos/XLAMP && \
./packaging/build_deb.sh && \
sudo dpkg -i ../xlamp_1.0.0_all.deb && \
sudo apt-get install -f
```

### 📦 Alternativa: Instalación desde Código Fuente

Si tienes problemas con el paquete .deb, puedes instalar directamente:

```bash
cd /home/jorge/Documentos/XLAMP
sudo pip3 install .
```

Esto instalará XLAMP sin crear el paquete .deb.

### 🔧 Reconstruir (después de cambios)

Para reconstruir el paquete después de hacer cambios:

```bash
cd /home/jorge/Documentos/XLAMP
rm -rf debian/  # Limpiar
./packaging/build_deb.sh
```

---

**Nota:** Este proceso crea un paquete nativo de Elementary OS/Ubuntu que se integra completamente con el sistema de paquetes apt.
