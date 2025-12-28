"""
XLAMP Manager - Virtual Host Manager
Gestión de hosts virtuales con terminación .test
"""

import os
import logging
import subprocess
import pwd
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
    
    def _get_temp_dir(self) -> str:
        """
        Obtiene un directorio temporal accesible tanto por el host como por Flatpak.
        """
        # Usar un directorio en el home del usuario que sea accesible
        temp_dir = os.path.join(os.path.expanduser('~'), '.xlamp_temp')
        os.makedirs(temp_dir, exist_ok=True)
        return temp_dir
    
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
            username = pwd.getpwuid(os.getuid()).pw_name
            domain = vhost.server_name
            if not domain.endswith(self.DEFAULT_DOMAIN_SUFFIX):
                domain = f"{domain}{self.DEFAULT_DOMAIN_SUFFIX}"
            
            vhost.server_name = domain
            vhost.document_root = os.path.abspath(document_root)
            # Crear directorio del sitio si no existe
            if not os.path.exists(vhost.document_root):
                logger.info(f"Creando directorio: {vhost.document_root}")
                
                # Preparar contenido de index.php
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
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; background-color: #f8fafc; color: #434B4D; min-height: 100vh; padding: 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; border-radius: 8px; border: 1px solid #e2e8f0; overflow: hidden; }}
        .header {{ background-color: #20B2AA; color: white; padding: 30px; text-align: center; }}
        .header h1 {{ font-size: 2em; margin-bottom: 10px; font-weight: 600; }}
        .header p {{ opacity: 0.9; font-size: 1.1em; }}
        .content {{ padding: 30px; }}
        .section {{ margin-bottom: 30px; }}
        .section h2 {{ color: #20B2AA; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #e5e7eb; font-size: 1.5em; }}
        .info-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin: 20px 0; }}
        .info-card {{ background: #f9fafb; padding: 15px; border-radius: 6px; border: 1px solid #e5e7eb; border-left: 4px solid #20B2AA; }}
        .info-card strong {{ color: #434B4D; display: block; margin-bottom: 5px; }}
        .info-card span {{ color: #6b7280; font-family: 'Courier New', monospace; font-size: 0.9em; }}
        .path-list {{ background: #f9fafb; padding: 20px; border-radius: 6px; border: 1px solid #e5e7eb; margin: 15px 0; }}
        .path-list li {{ margin: 8px 0; padding: 8px; background: white; border: 1px solid #e5e7eb; border-radius: 4px; font-family: 'Courier New', monospace; font-size: 0.9em; }}
        .path-list li strong {{ color: #20B2AA; }}
        .tips {{ background: #f0fdfa; border-left: 4px solid #20B2AA; padding: 20px; border-radius: 6px; margin: 20px 0; }}
        .tips h3 {{ color: #20B2AA; margin-bottom: 10px; }}
        .tips ul {{ margin-left: 20px; }}
        .tips li {{ margin: 8px 0; color: #434B4D; }}
        code {{ background: #e5e7eb; padding: 2px 6px; border-radius: 3px; font-family: 'Courier New', monospace; color: #be123c; }}
        .success {{ color: #20B2AA; }}
        .footer {{ text-align: center; padding: 20px; color: #6b7280; border-top: 1px solid #e5e7eb; font-size: 0.9em; }}
        .tools-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px; }}
        .tool-card {{ background: white; border: 1px solid #e2e8f0; padding: 15px; border-radius: 6px; text-align: center; }}
        .tool-card h4 {{ color: #20B2AA; margin-bottom: 5px; }}
        .tool-card p {{ font-size: 0.9em; color: #64748b; }}
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
                <h2>🛠️ Herramientas Disponibles</h2>
                <p>Gestiona tu entorno desde XLAMP Manager:</p>
                <div class="tools-grid">
                    <div class="tool-card">
                        <h4>Apache</h4>
                        <p>Servidor Web</p>
                    </div>
                    <div class="tool-card">
                        <h4>PHP-FPM</h4>
                        <p>Procesador PHP</p>
                    </div>
                    <div class="tool-card">
                        <h4>MariaDB / MySQL</h4>
                        <p>Base de Datos</p>
                    </div>
                    <div class="tool-card">
                        <h4>VHost Manager</h4>
                        <p>Gestión de Dominios</p>
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
            <p>Creado con XLAMP Manager • {domain}</p>
        </div>
    </div>
</body>
</html>
"""
                
                import tempfile
                # Escribir contenido a archivo temporal
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.php', dir=self._get_temp_dir()) as tmp_index:
                    tmp_index.write(index_content)
                    tmp_index_path = tmp_index.name

                # Crear script temporal que agrupa todas las operaciones administrativas
                script_content = f"""#!/bin/bash
set -e

# Crear directorio
mkdir -p "{vhost.document_root}"

# Copiar index.php desde temporal
cp "{tmp_index_path}" "{vhost.document_root}/index.php"

# Propietario www-data (lo usa PHP-FPM), grupo del usuario para poder editar
chown -R www-data:{username} "{vhost.document_root}"

# Permisos: directorios 755, archivos 644 (lectura para todos)
find "{vhost.document_root}" -type d -exec chmod 755 {{}} \;
find "{vhost.document_root}" -type f -exec chmod 644 {{}} \;

echo "Directorio y archivo index.php creados correctamente"
"""
                
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh', dir=self._get_temp_dir()) as script_file:
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
                    
                    logger.info(f"Directorio {vhost.document_root} creado con permisos correctos (www-data:{username} dirs 775 / files 664)")
                    
                finally:
                    # Limpiar archivos temporales
                    try:
                        os.unlink(script_path)
                        os.unlink(tmp_index_path)
                    except:
                        pass
            
            # Generar configuración Apache
            config_content = self._generate_apache_config(vhost)
            
            # Guardar configuración
            # Sanitizar nombre: reemplazar espacios y caracteres problemáticos
            safe_name = vhost.name.replace(' ', '_').replace('/', '_').replace('\\', '_')
            config_filename = f"{safe_name}.conf"
            config_path = os.path.join(self.VHOST_DIR, config_filename)
            
            # Crear archivo temporal con la configuración
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.conf', dir=self._get_temp_dir()) as tmp:
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

# Habilitar sitio (sin extensión .conf)
SITE_NAME="{safe_name}"
a2ensite "$SITE_NAME" 2>&1 || true

# Agregar a /etc/hosts si no existe
if ! grep -q "{hosts_entry}" /etc/hosts; then
    echo "" >> /etc/hosts
    echo "# XLAMP Manager - {domain}" >> /etc/hosts
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
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh', dir=self._get_temp_dir()) as script_file:
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
            
            # Iniciar PHP-FPM usando ServiceManager si se especificó versión
            if vhost.php_version:
                try:
                    from core.service_manager import ServiceManager
                    service_mgr = ServiceManager()
                    php_service = f"php{vhost.php_version}-fpm"
                    
                    # Verificar si el servicio está corriendo
                    status = service_mgr.get_status(php_service)
                    if not status.is_active:
                        logger.info(f"Iniciando {php_service}...")
                        success, msg = service_mgr.start(php_service)
                        if success:
                            logger.info(f"✓ {php_service} iniciado correctamente")
                        else:
                            logger.warning(f"No se pudo iniciar {php_service}: {msg}")
                    else:
                        logger.info(f"✓ {php_service} ya está activo")
                except Exception as e:
                    logger.warning(f"No se pudo verificar/iniciar PHP-FPM: {e}")
            
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
            # Usar socket genérico php-fpm.sock (apunta al FPM activo)
            socket_path = "/run/php/php-fpm.sock"
            # Configuración híbrida: intenta PHP-FPM primero, fallback a mod_php
            php_config = f"""
    # PHP {vhost.php_version} - Configuración híbrida
    <IfModule mod_proxy_fcgi.c>
        # PHP-FPM (preferido)
        <FilesMatch \\.php$>
            SetHandler "proxy:unix:{socket_path}|fcgi://localhost"
        </FilesMatch>
    </IfModule>
    
    <IfModule !mod_proxy_fcgi.c>
        # Fallback a mod_php si PHP-FPM no está disponible
        <FilesMatch \\.php$>
            SetHandler application/x-httpd-php
        </FilesMatch>
    </IfModule>
"""
        
        config = f"""<VirtualHost *:{vhost.port}>
    ServerName {vhost.server_name}
    ServerAdmin webmaster@{vhost.server_name}
    DocumentRoot {vhost.document_root}
    
    # DirectoryIndex debe estar SIEMPRE, priorizando PHP
    DirectoryIndex index.php index.html index.htm
    
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
    
    # DirectoryIndex debe estar SIEMPRE, priorizando PHP
    DirectoryIndex index.php index.html index.htm
    
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
            new_entry = f"\n# XLAMP Manager - {domain}\n127.0.0.1\t{domain}\n"
            new_content = hosts_content + new_entry
            
            # Escribir con pkexec
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, dir=self._get_temp_dir()) as tmp:
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
    
    def delete_vhosts(self, vhosts: List[Tuple[str, str]]) -> Tuple[bool, str]:
        """
        Elimina múltiples hosts virtuales.
        
        Args:
            vhosts: Lista de tuplas (vhost_name, domain)
            
        Returns:
            Tupla (éxito, mensaje)
        """
        try:
            if not vhosts:
                return True, "No hay hosts para eliminar"
                
            logger.info(f"Eliminando {len(vhosts)} hosts virtuales")
            
            domains = [v[1] for v in vhosts]
            
            # Preparar nuevo archivo hosts (sin los dominios)
            tmp_hosts_path = self._prepare_hosts_file_for_multiple_removal(domains)
            
            # Construir script unificado
            script_content = "#!/bin/bash\nset -e\n"
            
            for vhost_name, _ in vhosts:
                # 1. Deshabilitar sitio
                script_content += f"a2dissite {vhost_name}.conf || true\n"
                
                # 2. Eliminar configuración
                config_path = os.path.join(self.VHOST_DIR, f"{vhost_name}.conf")
                script_content += f"rm -f {config_path}\n"
            
            # 3. Actualizar hosts si se pudo preparar
            if tmp_hosts_path:
                script_content += f"cp {tmp_hosts_path} {self.HOSTS_FILE}\n"
                script_content += f"chmod 644 {self.HOSTS_FILE}\n"
            
            # 4. Recargar Apache
            script_content += "systemctl reload apache2 || true\n"
            
            # Crear archivo de script temporal
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh', dir=self._get_temp_dir()) as script_file:
                script_file.write(script_content)
                script_path = script_file.name
            
            os.chmod(script_path, 0o755)
            
            try:
                # Ejecutar script con una sola llamada a pkexec
                cmd = self._build_command(['pkexec', 'bash', script_path])
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode != 0:
                    return False, f"Error eliminando vhosts: {result.stderr}"
                
                logger.info(f"✓ {len(vhosts)} hosts virtuales eliminados")
                return True, f"{len(vhosts)} hosts virtuales eliminados correctamente"
                
            finally:
                # Limpiar archivos temporales
                if os.path.exists(script_path):
                    os.unlink(script_path)
                if tmp_hosts_path and os.path.exists(tmp_hosts_path):
                    os.unlink(tmp_hosts_path)
            
        except Exception as e:
            msg = f"Error eliminando hosts virtuales: {str(e)}"
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
        return self.delete_vhosts([(vhost_name, domain)])
    
    def _prepare_hosts_file_for_multiple_removal(self, domains: List[str]) -> Optional[str]:
        """
        Prepara un archivo temporal con el contenido de /etc/hosts sin los dominios indicados.
        
        Args:
            domains: Lista de dominios a eliminar
            
        Returns:
            Ruta al archivo temporal o None si falla
        """
        try:
            # Leer archivo hosts
            read_cmd = self._build_command(['cat', self.HOSTS_FILE])
            result = subprocess.run(read_cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logger.warning("No se pudo leer /etc/hosts")
                return None
            
            lines = result.stdout.split('\n')
            new_lines = []
            skip_next = False
            
            # Convertir a set para búsqueda rápida
            domains_set = set(domains)
            
            for line in lines:
                # Verificar si es una línea de comentario de XLAMP para alguno de los dominios
                is_xlamp_comment = False
                for domain in domains_set:
                    if f"# XLAMP Manager - {domain}" in line:
                        is_xlamp_comment = True
                        break
                
                if is_xlamp_comment:
                    skip_next = True
                    continue
                
                # Verificar si es la línea del dominio
                is_domain_line = False
                if skip_next:
                    for domain in domains_set:
                        if domain in line:
                            is_domain_line = True
                            break
                
                if is_domain_line:
                    skip_next = False
                    continue
                    
                new_lines.append(line)
            
            # Escribir nuevo contenido
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, dir=self._get_temp_dir()) as tmp:
                tmp.write('\n'.join(new_lines))
                return tmp.name
                
        except Exception as e:
            logger.error(f"Error preparando hosts file: {e}")
            return None

    def _prepare_hosts_file_for_removal(self, domain: str) -> Optional[str]:
        """
        Prepara un archivo temporal con el contenido de /etc/hosts sin el dominio.
        Deprecated: Use _prepare_hosts_file_for_multiple_removal instead.
        """
        return self._prepare_hosts_file_for_multiple_removal([domain])

    
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
