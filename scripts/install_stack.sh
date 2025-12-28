#!/bin/bash
# Script de instalación del stack LAMP completo

set -e

echo "==================================="
echo "XLAMP Manager - Instalador del Stack"
echo "==================================="
echo

# Verificar que se ejecute como root
if [ "$EUID" -ne 0 ]; then 
    echo "Este script debe ejecutarse como root (sudo)"
    exit 1
fi

# Actualizar repositorios
echo "Actualizando repositorios..."
apt-get update

# Instalar Apache
echo
echo "Instalando Apache..."
apt-get install -y apache2
systemctl enable apache2
systemctl start apache2
echo "✓ Apache instalado"

# Instalar MySQL
echo
echo "Instalando MySQL..."
apt-get install -y mysql-server
systemctl enable mysql
systemctl start mysql
echo "✓ MySQL instalado"

# Configuración básica de MySQL
echo
echo "Configurando MySQL..."
mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'root';"
mysql -e "FLUSH PRIVILEGES;"
echo "✓ MySQL configurado (usuario root, contraseña: root)"

# Instalar PHP y módulos comunes
echo
echo "Instalando PHP y módulos..."
apt-get install -y php libapache2-mod-php php-mysql php-cli php-curl php-gd php-mbstring php-xml php-zip php-fpm apparmor-utils

# Asegurar instalación de módulos para la versión activa de PHP (fix para repositorios PPA)
CURRENT_PHP_VER=$(php -r 'echo PHP_MAJOR_VERSION.".".PHP_MINOR_VERSION;' 2>/dev/null || echo "8.3")
echo "Asegurando módulos para PHP $CURRENT_PHP_VER..."
apt-get install -y "php${CURRENT_PHP_VER}-mysql" "php${CURRENT_PHP_VER}-mbstring" "php${CURRENT_PHP_VER}-xml" "php${CURRENT_PHP_VER}-curl" "php${CURRENT_PHP_VER}-gd" "php${CURRENT_PHP_VER}-zip" "php${CURRENT_PHP_VER}-fpm"

echo "✓ PHP y utilidades instalados"

# Habilitar módulos de Apache
echo
echo "Habilitando módulos de Apache..."
a2enmod rewrite
a2enmod ssl
systemctl restart apache2
echo "✓ Módulos habilitados"

# Crear directorio por defecto
echo
echo "Configurando directorio www..."
mkdir -p /var/www/html
chown -R www-data:www-data /var/www/html
echo "✓ Directorio configurado"

# Crear archivo de prueba PHP
echo "<?php phpinfo(); ?>" > /var/www/html/info.php
chown www-data:www-data /var/www/html/info.php

echo
echo "==================================="
echo "Instalación completada con éxito!"
echo "==================================="
echo
echo "Servicios instalados:"
echo "  - Apache: http://localhost"
echo "  - MySQL: usuario root, contraseña root"
echo "  - PHP: http://localhost/info.php"
echo
echo "Para gestionar los servicios, usa XLAMP Manager"
