"""
LAMP Manager - Virtual Host Manager
Gestión de hosts virtuales con terminación .test
"""

import os
import logging
import subprocess
from typing import List, Tuple, Optional
from pathlib import Path
from data.models import VirtualHost

logger = logging.getLogger(__name__)


class VHostManager:
    """Gestor de hosts virtuales Apache."""
    
    VHOST_DIR = "/etc/apache2/sites-available"
    VHOST_ENABLED_DIR = "/etc/apache2/sites-enabled"
    HOSTS_FILE = "/etc/hosts"
    DEFAULT_DOMAIN_SUFFIX = ".test"
    
    def __init__(self, use_flatpak: bool = False):
        """
        Inicializa el gestor de vhosts.
        
        Args:
            use_flatpak: Si está ejecutándose en Flatpak
        """
        # Auto-detectar si estamos en Flatpak
        if os.path.exists('/.flatpak-info'):
            self.use_flatpak = True
            logger.info("Detectado entorno Flatpak, usando flatpak-spawn")
        else:
            self.use_flatpak = use_flatpak
            
        logger.info(f"VHostManager inicializado (Flatpak: {self.use_flatpak})")
    
    def _build_command(self, cmd: List[str]) -> List[str]:
        """
        Construye comando con flatpak-spawn si es necesario.
        
        Args:
            cmd: Comando a ejecutar
            
        Returns:
            Comando completo
        """
        if self.use_flatpak:
            return ['flatpak-spawn', '--host'] + cmd
        return cmd
    
    def create_vhost(self, vhost: VirtualHost, document_root: str) -> Tuple[bool, str]:
        """
        Crea un nuevo host virtual con configuración Apache.
        
        Args:
            vhost: Datos del host virtual
            document_root: Ruta del directorio raíz
            
        Returns:
            Tupla (éxito, mensaje)
        """
        try:
            # Normalizar nombre de dominio
            domain = vhost.server_name
            if not domain.endswith(self.DEFAULT_DOMAIN_SUFFIX):
                domain = f"{domain}{self.DEFAULT_DOMAIN_SUFFIX}"
            
            vhost.server_name = domain
            vhost.document_root = os.path.abspath(document_root)
            
            # Crear directorio del sitio si no existe
            if not os.path.exists(vhost.document_root):
                logger.info(f"Creando directorio: {vhost.document_root}")
                
                # Obtener usuario actual
                import pwd
                username = pwd.getpwuid(os.getuid()).pw_name
                
                # Crear script temporal que agrupa todas las operaciones administrativas
                import tempfile
                script_content = f"""#!/bin/bash
set -e

# Crear directorio
mkdir -p "{vhost.document_root}"

# Cambiar propietario
chown -R {username}:{username} "{vhost.document_root}"

# Permisos
chmod -R 755 "{vhost.document_root}"

echo "Directorio creado correctamente"
"""
                
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh') as script_file:
                    script_file.write(script_content)
                    script_path = script_file.name
                
                # Dar permisos de ejecución al script
                os.chmod(script_path, 0o755)
                
                try:
                    # Ejecutar script con una sola solicitud de pkexec
                    create_cmd = self._build_command(['pkexec', 'bash', script_path])
                    result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=60)
                    
                    if result.returncode != 0:
                        return False, f"Error creando directorio: {result.stderr}"
                    
                    logger.info(f"Directorio {vhost.document_root} creado con permisos correctos")
                    
                finally:
                    # Limpiar script temporal
                    try:
                        os.unlink(script_path)
                    except:
                        pass
                
                # Crear index.php de prueba (ahora tenemos permisos)
                index_file = os.path.join(vhost.document_root, 'index.php')
                index_content = f"""<?php
/**
 * {domain} - Entorno de Desarrollo
 * Creado: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 */
?>
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>✓ {domain} - Funcionando</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; text-align: center; }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; font-size: 1.1em; }}
        .content {{ padding: 40px; }}
        .section {{ margin-bottom: 30px; }}
        .section h2 {{ color: #667eea; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #e5e7eb; }}
        .info-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin: 20px 0; }}
        .info-card {{ background: #f9fafb; padding: 20px; border-radius: 8px; border-left: 4px solid #667eea; }}
        .info-card strong {{ color: #374151; display: block; margin-bottom: 5px; }}
        .info-card span {{ color: #6b7280; font-family: 'Courier New', monospace; font-size: 0.9em; }}
        .path-list {{ background: #f9fafb; padding: 20px; border-radius: 8px; margin: 15px 0; }}
        .path-list li {{ margin: 10px 0; padding: 10px; background: white; border-radius: 4px; font-family: 'Courier New', monospace; font-size: 0.9em; }}
        .path-list li strong {{ color: #667eea; }}
        .tips {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .tips h3 {{ color: #f59e0b; margin-bottom: 10px; }}
        .tips ul {{ margin-left: 20px; }}
        .tips li {{ margin: 8px 0; color: #78350f; }}
        code {{ background: #e5e7eb; padding: 2px 6px; border-radius: 3px; font-family: 'Courier New', monospace; color: #be123c; }}
        .success {{ color: #10b981; }}
        .footer {{ text-align: center; padding: 20px; color: #6b7280; border-top: 1px solid #e5e7eb; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 ¡{domain} está funcionando!</h1>
            <p>Tu entorno de desarrollo LAMP está listo</p>
        </div>
        
        <div class="content">
            <div class="section">
                <h2>📊 Información del Sistema</h2>
                <div class="info-grid">
                    <div class="info-card">
                        <strong>Versión PHP</strong>
                        <span><?php echo PHP_VERSION; ?></span>
                    </div>
                    <div class="info-card">
                        <strong>Servidor Web</strong>
                        <span><?php echo $_SERVER['SERVER_SOFTWARE'] ?? 'Apache'; ?></span>
                    </div>
                    <div class="info-card">
                        <strong>Document Root</strong>
                        <span>{vhost.document_root}</span>
                    </div>
                    <div class="info-card">
                        <strong>Dominio</strong>
                        <span>{domain}</span>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>📁 Rutas Importantes de PHP</h2>
                <div class="path-list">
                    <ul style="list-style: none;">
                        <li><strong>php.ini principal:</strong> <?php echo php_ini_loaded_file(); ?></li>
                        <li><strong>Archivos .ini adicionales:</strong> <?php echo php_ini_scanned_files() ?: 'Ninguno'; ?></li>
                        <li><strong>Directorio de extensiones:</strong> <?php echo ini_get('extension_dir'); ?></li>
                        <li><strong>Directorio temporal:</strong> <?php echo sys_get_temp_dir(); ?></li>
                        <li><strong>Upload max size:</strong> <?php echo ini_get('upload_max_filesize'); ?></li>
                        <li><strong>Post max size:</strong> <?php echo ini_get('post_max_size'); ?></li>
                        <li><strong>Memory limit:</strong> <?php echo ini_get('memory_limit'); ?></li>
                        <li><strong>Max execution time:</strong> <?php echo ini_get('max_execution_time'); ?>s</li>
                    </ul>
                </div>
            </div>
            
            <div class="section">
                <h2>🔧 Rutas Comunes del Sistema</h2>
                <div class="path-list">
                    <ul style="list-style: none;">
                        <li><strong>Apache sites-available:</strong> <code>/etc/apache2/sites-available/</code></li>
                        <li><strong>Apache sites-enabled:</strong> <code>/etc/apache2/sites-enabled/</code></li>
                        <li><strong>Apache logs:</strong> <code>/var/log/apache2/</code></li>
                        <li><strong>PHP-FPM config:</strong> <code>/etc/php/<?php echo PHP_MAJOR_VERSION . '.' . PHP_MINOR_VERSION; ?>/fpm/</code></li>
                        <li><strong>PHP-FPM logs:</strong> <code>/var/log/php<?php echo PHP_MAJOR_VERSION . '.' . PHP_MINOR_VERSION; ?>-fpm.log</code></li>
                        <li><strong>MySQL/MariaDB config:</strong> <code>/etc/mysql/</code></li>
                    </ul>
                </div>
            </div>
            
            <div class="section">
                <div class="tips">
                    <h3>💡 Recomendaciones para Desarrollo</h3>
                    <ul>
                        <li><strong>Habilita error reporting:</strong> Edita <code>php.ini</code> y configura: <code>display_errors = On</code> y <code>error_reporting = E_ALL</code></li>
                        <li><strong>Instala Xdebug:</strong> Ejecuta <code>sudo apt install php-xdebug</code> para debugging avanzado</li>
                        <li><strong>Usa Composer:</strong> Gestor de dependencias PHP - <code>sudo apt install composer</code></li>
                        <li><strong>Revisa logs:</strong> <code>tail -f /var/log/apache2/error.log</code> para ver errores en tiempo real</li>
                        <li><strong>phpMyAdmin:</strong> Instala para gestionar MySQL visualmente - <code>sudo apt install phpmyadmin</code></li>
                        <li><strong>Reinicia servicios:</strong> Después de cambios en php.ini: <code>sudo systemctl restart php<?php echo PHP_MAJOR_VERSION . '.' . PHP_MINOR_VERSION; ?>-fpm apache2</code></li>
                        <li><strong>Permisos:</strong> Asegúrate que tu usuario tenga permisos en <code>{vhost.document_root}</code></li>
                        <li><strong>.htaccess:</strong> Verifica que <code>AllowOverride All</code> esté habilitado en la config de Apache</li>
                    </ul>
                </div>
            </div>
            
            <div class="section">
                <h2>🎯 Próximos Pasos</h2>
                <ol>
                    <li>Reemplaza este archivo: <code>{index_file}</code></li>
                    <li>Crea tu estructura de proyecto (MVC, por ejemplo)</li>
                    <li>Configura tu base de datos MySQL/MariaDB</li>
                    <li>Instala dependencias con Composer si usas frameworks</li>
                    <li>¡Comienza a desarrollar! 🚀</li>
                </ol>
            </div>
        </div>
        
        <div class="footer">
            <p>Creado con LAMP Manager • {domain}</p>
        </div>
    </div>
</body>
</html>
"""
                
                # Escribir index.php (ahora tenemos permisos)
                try:
                    with open(index_file, 'w') as f:
                        f.write(index_content)
                    logger.info(f"Creado index.php en {index_file}")
                except Exception as e:
                    logger.warning(f"No se pudo crear index.php: {e}")
            
            # Generar configuración Apache
            config_content = self._generate_apache_config(vhost)
            
            # Guardar configuración
            config_filename = f"{vhost.name}.conf"
            config_path = os.path.join(self.VHOST_DIR, config_filename)
            
            # Crear archivo temporal con la configuración
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.conf') as tmp:
                tmp.write(config_content)
                tmp_config_path = tmp.name
            
            # Preparar entrada para /etc/hosts
            hosts_entry = f"127.0.0.1\t{domain}"
            
            # Crear script que agrupa todas las operaciones administrativas de Apache
            script_content = f"""#!/bin/bash
set -e

# Copiar configuración de Apache
cp "{tmp_config_path}" "{config_path}"
chmod 644 "{config_path}"

# Habilitar módulos necesarios para PHP-FPM
echo "Habilitando módulos de Apache..."
a2enmod proxy 2>&1 || true
a2enmod proxy_fcgi 2>&1 || true
a2enmod rewrite 2>&1 || true

# Habilitar sitio
a2ensite "{config_filename}" 2>&1 || true

# Iniciar PHP-FPM si está instalado
if [ -f /lib/systemd/system/php{vhost.php_version}-fpm.service ]; then
    echo "Iniciando PHP {vhost.php_version} FPM..."
    systemctl enable php{vhost.php_version}-fpm 2>&1 || true
    systemctl start php{vhost.php_version}-fpm 2>&1 || systemctl restart php{vhost.php_version}-fpm 2>&1 || true
    echo "✓ PHP {vhost.php_version} FPM iniciado"
fi

# Agregar a /etc/hosts si no existe
if ! grep -q "{hosts_entry}" /etc/hosts; then
    echo "" >> /etc/hosts
    echo "# LAMP Manager - {domain}" >> /etc/hosts
    echo "{hosts_entry}" >> /etc/hosts
    echo "✓ Agregado {domain} a /etc/hosts"
fi

# Verificar configuración de Apache
apache2ctl configtest 2>&1 || echo "Advertencia: Configuración de Apache tiene advertencias"

# Recargar Apache solo si está activo
if systemctl is-active --quiet apache2 2>/dev/null; then
    systemctl reload apache2 2>&1 || echo "No se pudo recargar Apache"
    echo "✓ Apache recargado"
else
    echo "ℹ Apache no está activo, inicia el servicio para aplicar cambios"
fi

echo "✓ Host virtual configurado correctamente"
"""
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh') as script_file:
                script_file.write(script_content)
                script_path = script_file.name
            
            os.chmod(script_path, 0o755)
            
            try:
                # Ejecutar script con una sola solicitud de pkexec
                apache_cmd = self._build_command(['pkexec', 'bash', script_path])
                result = subprocess.run(apache_cmd, capture_output=True, text=True, timeout=60)
                
                logger.info(f"Salida de configuración Apache:\n{result.stdout}")
                
                if result.returncode != 0:
                    error_msg = result.stderr or "Error desconocido"
                    logger.error(f"Error configurando Apache: {error_msg}")
                    return False, f"Error configurando Apache: {error_msg}"
                
            finally:
                # Limpiar archivos temporales
                try:
                    os.unlink(tmp_config_path)
                    os.unlink(script_path)
                except:
                    pass
            
            logger.info(f"✓ Host virtual '{domain}' creado correctamente")
            return True, f"Host virtual '{domain}' creado correctamente"
            
        except Exception as e:
            msg = f"Error creando host virtual: {str(e)}"
            logger.error(msg, exc_info=True)
            return False, msg
    
    def _generate_apache_config(self, vhost: VirtualHost) -> str:
        """
        Genera la configuración de Apache para el vhost.
        
        Args:
            vhost: Datos del host virtual
            
        Returns:
            Contenido del archivo de configuración
        """
        php_config = ""
        if vhost.php_version:
            # Configuración híbrida: intenta PHP-FPM primero, fallback a mod_php
            php_config = f"""
    # PHP {vhost.php_version} - Configuración híbrida
    <IfModule mod_proxy_fcgi.c>
        # PHP-FPM (preferido)
        <FilesMatch \\.php$>
            SetHandler "proxy:unix:/run/php/php{vhost.php_version}-fpm.sock|fcgi://localhost"
        </FilesMatch>
    </IfModule>
    
    <IfModule !mod_proxy_fcgi.c>
        # Fallback a mod_php si PHP-FPM no está disponible
        <FilesMatch \\.php$>
            SetHandler application/x-httpd-php
        </FilesMatch>
    </IfModule>
    
    # Índices
    DirectoryIndex index.php index.html index.htm
"""
        
        config = f"""<VirtualHost *:{vhost.port}>
    ServerName {vhost.server_name}
    ServerAdmin webmaster@{vhost.server_name}
    DocumentRoot {vhost.document_root}
    
    <Directory {vhost.document_root}>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>
{php_config}
    ErrorLog ${{APACHE_LOG_DIR}}/{vhost.name}-error.log
    CustomLog ${{APACHE_LOG_DIR}}/{vhost.name}-access.log combined
</VirtualHost>
"""
        
        if vhost.ssl_enabled and vhost.ssl_cert_path and vhost.ssl_key_path:
            config += f"""
<VirtualHost *:443>
    ServerName {vhost.server_name}
    ServerAdmin webmaster@{vhost.server_name}
    DocumentRoot {vhost.document_root}
    
    SSLEngine on
    SSLCertificateFile {vhost.ssl_cert_path}
    SSLCertificateKeyFile {vhost.ssl_key_path}
    
    <Directory {vhost.document_root}>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>
{php_config}
    ErrorLog ${{APACHE_LOG_DIR}}/{vhost.name}-ssl-error.log
    CustomLog ${{APACHE_LOG_DIR}}/{vhost.name}-ssl-access.log combined
</VirtualHost>
"""
        
        return config
    
    def _add_to_hosts(self, domain: str) -> Tuple[bool, str]:
        """
        Agrega entrada al archivo /etc/hosts.
        
        Args:
            domain: Dominio a agregar
            
        Returns:
            Tupla (éxito, mensaje)
        """
        try:
            # Leer archivo hosts actual
            read_cmd = self._build_command(['cat', self.HOSTS_FILE])
            result = subprocess.run(read_cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return False, "No se pudo leer /etc/hosts"
            
            hosts_content = result.stdout
            
            # Verificar si ya existe
            if f"127.0.0.1\t{domain}" in hosts_content or f"127.0.0.1 {domain}" in hosts_content:
                logger.info(f"Dominio {domain} ya existe en /etc/hosts")
                return True, "Dominio ya existe en /etc/hosts"
            
            # Agregar nueva entrada
            new_entry = f"\n# LAMP Manager - {domain}\n127.0.0.1\t{domain}\n"
            new_content = hosts_content + new_entry
            
            # Escribir con pkexec
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
                tmp.write(new_content)
                tmp_path = tmp.name
            
            try:
                copy_cmd = self._build_command([
                    'pkexec', 'cp', tmp_path, self.HOSTS_FILE
                ])
                result = subprocess.run(copy_cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode != 0:
                    return False, f"Error actualizando /etc/hosts: {result.stderr}"
                
                logger.info(f"✓ Dominio {domain} agregado a /etc/hosts")
                return True, "Dominio agregado a /etc/hosts"
                
            finally:
                os.unlink(tmp_path)
                
        except Exception as e:
            msg = f"Error agregando a /etc/hosts: {str(e)}"
            logger.error(msg)
            return False, msg
    
    def delete_vhost(self, vhost_name: str, domain: str) -> Tuple[bool, str]:
        """
        Elimina un host virtual.
        
        Args:
            vhost_name: Nombre interno del vhost
            domain: Dominio (server_name)
            
        Returns:
            Tupla (éxito, mensaje)
        """
        try:
            logger.info(f"Eliminando host virtual: {vhost_name}")
            
            # Deshabilitar sitio
            disable_cmd = self._build_command([
                'pkexec', 'a2dissite', f"{vhost_name}.conf"
            ])
            subprocess.run(disable_cmd, capture_output=True, timeout=30)
            
            # Eliminar configuración
            config_path = os.path.join(self.VHOST_DIR, f"{vhost_name}.conf")
            remove_cmd = self._build_command([
                'pkexec', 'rm', '-f', config_path
            ])
            result = subprocess.run(remove_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.warning(f"Error eliminando configuración: {result.stderr}")
            
            # Remover de /etc/hosts
            self._remove_from_hosts(domain)
            
            # Verificar que Apache esté corriendo antes de recargar
            check_cmd = self._build_command(['systemctl', 'is-active', 'apache2'])
            try:
                check_result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=10)
                apache_active = check_result.returncode == 0 and 'active' in check_result.stdout
            except Exception as e:
                logger.warning(f"No se pudo verificar estado de Apache: {e}")
                apache_active = False
            
            if apache_active:
                # Apache está activo, intentar recargar
                reload_cmd = self._build_command([
                    'pkexec', 'systemctl', 'reload', 'apache2'
                ])
                try:
                    subprocess.run(reload_cmd, capture_output=True, text=True, timeout=30)
                except Exception as e:
                    logger.warning(f"Error recargando Apache: {e}")
            
            logger.info(f"✓ Host virtual '{vhost_name}' eliminado")
            return True, f"Host virtual eliminado correctamente"
            
        except Exception as e:
            msg = f"Error eliminando host virtual: {str(e)}"
            logger.error(msg)
            return False, msg
    
    def _remove_from_hosts(self, domain: str) -> None:
        """
        Elimina entrada del archivo /etc/hosts.
        
        Args:
            domain: Dominio a eliminar
        """
        try:
            # Leer archivo hosts
            read_cmd = self._build_command(['cat', self.HOSTS_FILE])
            result = subprocess.run(read_cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logger.warning("No se pudo leer /etc/hosts")
                return
            
            lines = result.stdout.split('\n')
            new_lines = []
            skip_next = False
            
            for line in lines:
                # Saltar comentario LAMP Manager y línea del dominio
                if f"# LAMP Manager - {domain}" in line:
                    skip_next = True
                    continue
                if skip_next and domain in line:
                    skip_next = False
                    continue
                new_lines.append(line)
            
            # Escribir nuevo contenido
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
                tmp.write('\n'.join(new_lines))
                tmp_path = tmp.name
            
            try:
                copy_cmd = self._build_command([
                    'pkexec', 'cp', tmp_path, self.HOSTS_FILE
                ])
                subprocess.run(copy_cmd, capture_output=True, timeout=30)
                logger.info(f"✓ Dominio {domain} eliminado de /etc/hosts")
            finally:
                os.unlink(tmp_path)
                
        except Exception as e:
            logger.error(f"Error eliminando de /etc/hosts: {e}")
    
    def list_vhosts(self) -> List[str]:
        """
        Lista los archivos de configuración disponibles.
        
        Returns:
            Lista de nombres de vhosts
        """
        try:
            if not os.path.exists(self.VHOST_DIR):
                return []
            
            vhosts = []
            for filename in os.listdir(self.VHOST_DIR):
                if filename.endswith('.conf') and filename not in ['000-default.conf', 'default-ssl.conf']:
                    vhosts.append(filename.replace('.conf', ''))
            
            return sorted(vhosts)
        except Exception as e:
            logger.error(f"Error listando vhosts: {e}")
            return []
