"""
LAMP Manager - Stack Installer
Sistema de instalación de componentes del stack LAMP.
"""

import subprocess
import logging
from typing import List, Tuple, Optional
import threading
import os
import shutil

logger = logging.getLogger(__name__)


class StackInstaller:
    """Instalador de componentes del stack LAMP."""
    
    COMPONENTS = {
        # === SERVIDORES ===
        'apache2': {
            'name': 'Apache',
            'packages': ['apache2'],
            'description': 'Servidor web Apache HTTP Server',
            'service': 'apache2',
            'post_install': None,
            'category': 'servidores'
        },
        'mysql': {
            'name': 'MySQL',
            'packages': ['mysql-server'],
            'description': 'Sistema de gestión de bases de datos MySQL',
            'service': 'mysql',
            'post_install': None,
            'category': 'servidores'
        },
        'mariadb': {
            'name': 'MariaDB',
            'packages': ['mariadb-server', 'mariadb-client'],
            'description': 'Sistema de BD alternativo a MySQL, más moderno',
            'service': 'mariadb',
            'post_install': None,
            'category': 'servidores'
        },
        
        # === LENGUAJES ===
        'php': {
            'name': 'PHP',
            'packages': [
                'php',
                'libapache2-mod-php',
                'php-mysql',
                'php-cli',
                'php-curl',
                'php-gd',
                'php-mbstring',
                'php-xml',
                'php-zip'
            ],
            'description': 'Lenguaje de programación PHP con módulos comunes',
            'service': 'apache2',
            'post_install': 'apache2',
            'category': 'lenguajes'
        },
        'nodejs': {
            'name': 'Node.js',
            'packages': ['nodejs', 'npm'],
            'description': 'JavaScript runtime y gestor de paquetes NPM',
            'service': None,
            'post_install': None,
            'add_to_path': True,
            'category': 'lenguajes'
        },
        
        # === GESTIÓN DE DEPENDENCIAS ===
        'composer': {
            'name': 'Composer',
            'packages': ['composer'],
            'description': 'Gestor de dependencias para PHP',
            'service': None,
            'post_install': None,
            'category': 'dependencias'
        },
        'yarn': {
            'name': 'Yarn',
            'packages': ['yarn'],
            'description': 'Gestor de paquetes alternativo a NPM',
            'service': None,
            'post_install': None,
            'add_to_path': True,
            'category': 'dependencias'
        },
        
        # === CONTROL DE VERSIONES ===
        'git': {
            'name': 'Git',
            'packages': ['git'],
            'description': 'Sistema de control de versiones distribuido',
            'service': None,
            'post_install': None,
            'add_to_path': True,
            'category': 'versionado'
        },
        
        # === CACHÉ Y RENDIMIENTO ===
        'redis': {
            'name': 'Redis',
            'packages': ['redis-server', 'php-redis'],
            'description': 'Base de datos en memoria para caché de alto rendimiento',
            'service': 'redis-server',
            'post_install': 'apache2',
            'category': 'cache'
        },
        'memcached': {
            'name': 'Memcached',
            'packages': ['memcached', 'php-memcached'],
            'description': 'Sistema de caché distribuida en memoria',
            'service': 'memcached',
            'post_install': 'apache2',
            'category': 'cache'
        },
        'varnish': {
            'name': 'Varnish Cache',
            'packages': ['varnish'],
            'description': 'HTTP accelerator y proxy reverso de alto rendimiento',
            'service': 'varnish',
            'post_install': None,
            'category': 'cache'
        },
        
        # === DESARROLLO Y DEBUGGING ===
        'xdebug': {
            'name': 'Xdebug',
            'packages': ['php-xdebug'],
            'description': 'Debugger y profiler para PHP',
            'service': None,
            'post_install': 'apache2',
            'category': 'desarrollo'
        },
        'phpmyadmin': {
            'name': 'phpMyAdmin',
            'packages': ['phpmyadmin'],
            'description': 'Interfaz web para administración de MySQL/MariaDB',
            'service': None,
            'post_install': 'apache2',
            'category': 'desarrollo'
        },
        'adminer': {
            'name': 'Adminer',
            'packages': ['adminer'],
            'description': 'Gestor de BD ligero, alternativa a phpMyAdmin',
            'service': None,
            'post_install': 'apache2',
            'category': 'desarrollo'
        },
        
        # === TESTING ===
        'phpunit': {
            'name': 'PHPUnit',
            'packages': ['phpunit'],
            'description': 'Framework de testing para PHP',
            'service': None,
            'post_install': None,
            'add_to_path': True,
            'category': 'testing'
        },
        
        # === CMS Y FRAMEWORKS ===
        'wpcli': {
            'name': 'WP-CLI',
            'packages': [],
            'description': 'Herramienta de línea de comandos para WordPress',
            'service': None,
            'post_install': None,
            'add_to_path': True,
            'custom_install': True,
            'category': 'cms'
        }
    }
    
    def __init__(self):
        """Inicializa el instalador."""
        self.is_installing = False
        self.current_progress = 0
        self.in_flatpak = self._detect_flatpak()
        self.flatpak_spawn = self._check_flatpak_spawn()
        self.pkexec_available = self._check_pkexec()
        
        # Log del entorno
        if self.in_flatpak:
            logger.info("🔒 Ejecutando dentro de Flatpak")
            if self.flatpak_spawn:
                logger.info(f"✓ flatpak-spawn disponible: {self.flatpak_spawn}")
            else:
                logger.warning("✗ flatpak-spawn no disponible")
        else:
            logger.info("✓ Ejecutando en sistema nativo")
        
        if self.pkexec_available:
            logger.info("✓ pkexec disponible para elevar privilegios")
        else:
            logger.warning("✗ pkexec no disponible")
    
    def _detect_flatpak(self) -> bool:
        """Detecta si estamos ejecutando dentro de Flatpak."""
        # Método 1: Variable de entorno
        if os.environ.get('FLATPAK_ID'):
            return True
        
        # Método 2: Archivo .flatpak-info
        if os.path.exists('/.flatpak-info'):
            return True
        
        # Método 3: Verificar si estamos en /app
        if os.path.exists('/app'):
            return True
        
        return False
    
    def _check_flatpak_spawn(self) -> Optional[str]:
        """Verifica si flatpak-spawn está disponible."""
        spawn_path = shutil.which('flatpak-spawn')
        if spawn_path:
            logger.info(f"flatpak-spawn encontrado en: {spawn_path}")
            return spawn_path
        return None
    
    def _check_pkexec(self) -> bool:
        """Verifica si pkexec está disponible."""
        try:
            # Si estamos en Flatpak, verificar en el host
            if self.in_flatpak and self.flatpak_spawn:
                result = subprocess.run(
                    [self.flatpak_spawn, '--host', 'which', 'pkexec'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            else:
                result = subprocess.run(
                    ['which', 'pkexec'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            
            if result.returncode == 0:
                logger.info("✓ pkexec disponible")
                return True
            else:
                logger.warning("✗ pkexec no disponible - instalación no funcionará")
                return False
        except Exception as e:
            logger.error(f"Error verificando pkexec: {e}")
            return False
    
    def _build_command(self, base_cmd: List[str]) -> List[str]:
        """
        Construye el comando apropiado según el entorno.
        
        Args:
            base_cmd: Comando base a ejecutar
            
        Returns:
            Comando completo con flatpak-spawn si es necesario
        """
        if self.in_flatpak and self.flatpak_spawn:
            # Ejecutar en el host con flatpak-spawn
            return [self.flatpak_spawn, '--host'] + base_cmd
        else:
            # Ejecución normal
            return base_cmd
    
    def install_component(self, component_id: str, progress_callback=None) -> Tuple[bool, str]:
        """
        Instala un componente del stack.
        
        Args:
            component_id: ID del componente (apache2, mysql, php)
            progress_callback: Función para reportar progreso
            
        Returns:
            Tupla (éxito, mensaje)
        """
        if component_id not in self.COMPONENTS:
            return False, f"Componente desconocido: {component_id}"
        
        if not self.pkexec_available:
            return False, "pkexec no está disponible. Instala policykit-1 en el sistema host."
        
        component = self.COMPONENTS[component_id]
        packages = component['packages']
        
        try:
            self.is_installing = True
            logger.info(f"Iniciando instalación de {component['name']}...")
            
            # Instalación personalizada para componentes especiales
            if component.get('custom_install'):
                return self._custom_install(component_id, component, progress_callback)
            
            if self.in_flatpak:
                logger.info("Ejecutando desde Flatpak - usando flatpak-spawn para acceder al host")
            
            if progress_callback:
                progress_callback(10, f"Actualizando repositorios...")
            
            # Construir comando para actualizar repositorios
            update_cmd = self._build_command(['pkexec', 'apt-get', 'update'])
            logger.info(f"Ejecutando: {' '.join(update_cmd)}")
            
            result = subprocess.run(
                update_cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Error desconocido"
                logger.error(f"Error actualizando repositorios (código {result.returncode}): {error_msg}")
                
                # Mensajes más específicos según el error
                if "denied" in error_msg.lower() or "cancelled" in error_msg.lower():
                    return False, "Autenticación cancelada por el usuario"
                elif "not authorized" in error_msg.lower():
                    return False, "No tienes permisos de administrador"
                else:
                    return False, f"Error actualizando repositorios: {error_msg[:200]}"
            
            logger.info("✓ Repositorios actualizados")
            
            if progress_callback:
                progress_callback(30, f"Descargando e instalando {component['name']}...")
            
            # Construir comando de instalación
            # Usar DEBIAN_FRONTEND=noninteractive para evitar prompts
            packages_str = " ".join(packages)
            install_cmd = self._build_command([
                'pkexec', 'sh', '-c',
                f'DEBIAN_FRONTEND=noninteractive apt-get install -y {packages_str}'
            ])
            
            logger.info(f"Instalando paquetes: {packages_str}")
            logger.info(f"Comando: {' '.join(install_cmd)}")
            
            result = subprocess.run(
                install_cmd,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Error desconocido"
                logger.error(f"Error instalando {component['name']} (código {result.returncode}): {error_msg}")
                
                # Mensajes más específicos
                if "denied" in error_msg.lower() or "cancelled" in error_msg.lower():
                    return False, "Autenticación cancelada por el usuario"
                elif "Unable to locate package" in error_msg:
                    return False, f"Algunos paquetes no fueron encontrados. Verifica tu conexión."
                elif "dpkg was interrupted" in error_msg:
                    return False, f"Instalación interrumpida. Ejecuta: sudo dpkg --configure -a"
                else:
                    return False, f"Error: {error_msg[:200]}"
            
            logger.info(f"✓ {component['name']} instalado correctamente")
            logger.debug(f"Salida: {result.stdout}")
            
            if progress_callback:
                progress_callback(80, f"Configurando {component['name']}...")
            
            # Habilitar y arrancar servicio si existe
            if component['service']:
                logger.info(f"Habilitando servicio {component['service']}...")
                self._enable_service(component['service'])
                logger.info(f"Iniciando servicio {component['service']}...")
                self._start_service(component['service'])
            
            # Post-instalación: reiniciar servicios relacionados
            if component.get('post_install'):
                post_service = component['post_install']
                logger.info(f"Post-instalación: reiniciando {post_service}...")
                self._restart_service(post_service)
            
            # Añadir al PATH si es necesario
            if component.get('add_to_path'):
                logger.info(f"Añadiendo {component['name']} al PATH del sistema...")
                self._add_to_path(component_id, component['name'])
            
            if progress_callback:
                progress_callback(100, f"{component['name']} instalado correctamente")
            
            logger.info(f"✓ {component['name']} instalado y configurado exitosamente")
            return True, f"{component['name']} instalado correctamente"
            
        except subprocess.TimeoutExpired:
            msg = f"⏱️ Timeout: La instalación de {component['name']} tardó demasiado"
            logger.error(msg)
            return False, msg
        except FileNotFoundError as e:
            msg = f"❌ Comando no encontrado: {e.filename}"
            logger.error(msg)
            return False, msg
        except Exception as e:
            msg = f"❌ Error instalando {component['name']}: {str(e)}"
            logger.error(msg, exc_info=True)
            return False, msg
        finally:
            self.is_installing = False
    
    def install_components(self, component_ids: List[str], progress_callback=None) -> Tuple[bool, str]:
        """
        Instala múltiples componentes.
        
        Args:
            component_ids: Lista de IDs de componentes
            progress_callback: Función para reportar progreso
            
        Returns:
            Tupla (éxito, mensaje)
        """
        total = len(component_ids)
        installed = []
        failed = []
        
        for i, component_id in enumerate(component_ids):
            if progress_callback:
                overall_progress = int((i / total) * 100)
                progress_callback(overall_progress, f"Instalando componente {i+1} de {total}...")
            
            success, msg = self.install_component(component_id, None)
            
            if success:
                installed.append(component_id)
            else:
                failed.append((component_id, msg))
        
        if progress_callback:
            progress_callback(100, "Instalación completada")
        
        # Generar mensaje de resultado
        if not failed:
            return True, f"Todos los componentes instalados correctamente"
        elif not installed:
            return False, f"Error: No se pudo instalar ningún componente"
        else:
            return True, f"Instalados: {len(installed)}, Fallidos: {len(failed)}"
    
    def uninstall_component(self, component_id: str) -> Tuple[bool, str]:
        """
        Desinstala un componente del stack.
        
        Args:
            component_id: ID del componente
            
        Returns:
            Tupla (éxito, mensaje)
        """
        if component_id not in self.COMPONENTS:
            return False, f"Componente desconocido: {component_id}"
        
        component = self.COMPONENTS[component_id]
        packages = component['packages']
        
        try:
            logger.info(f"Desinstalando {component['name']}...")
            
            # Detener servicio si existe
            if component['service']:
                logger.info(f"Deteniendo servicio {component['service']}...")
                self._stop_service(component['service'])
            
            # Desinstalar paquetes con flatpak-spawn si es necesario
            uninstall_cmd = self._build_command([
                'pkexec', 'apt-get', 'remove', '--purge', '-y'
            ] + packages)
            
            logger.info(f"Ejecutando: {' '.join(uninstall_cmd)}")
            
            result = subprocess.run(
                uninstall_cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or "Error desconocido"
                logger.error(f"Error desinstalando {component['name']}: {error_msg}")
                return False, f"Error al desinstalar: {error_msg[:200]}"
            
            # Limpiar dependencias huérfanas
            logger.info("Limpiando dependencias...")
            autoremove_cmd = self._build_command([
                'pkexec', 'apt-get', 'autoremove', '-y'
            ])
            subprocess.run(autoremove_cmd, capture_output=True, timeout=60)
            
            logger.info(f"{component['name']} desinstalado correctamente")
            return True, f"{component['name']} desinstalado correctamente"
            
        except subprocess.TimeoutExpired:
            msg = f"Timeout desinstalando {component['name']}"
            logger.error(msg)
            return False, msg
        except Exception as e:
            msg = f"Error desinstalando {component['name']}: {str(e)}"
            logger.error(msg)
            return False, msg
    
    def _enable_service(self, service_name: str) -> None:
        """Habilita un servicio."""
        try:
            cmd = self._build_command(['pkexec', 'systemctl', 'enable', service_name])
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30
            )
            if result.returncode == 0:
                logger.info(f"✓ Servicio {service_name} habilitado")
            else:
                logger.warning(f"No se pudo habilitar {service_name}: {result.stderr}")
        except Exception as e:
            logger.warning(f"No se pudo habilitar {service_name}: {e}")
    
    def _start_service(self, service_name: str) -> None:
        """Inicia un servicio."""
        try:
            cmd = self._build_command(['pkexec', 'systemctl', 'start', service_name])
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30
            )
            if result.returncode == 0:
                logger.info(f"✓ Servicio {service_name} iniciado")
            else:
                logger.warning(f"No se pudo iniciar {service_name}: {result.stderr}")
        except Exception as e:
            logger.warning(f"No se pudo iniciar {service_name}: {e}")
    
    def _stop_service(self, service_name: str) -> None:
        """Detiene un servicio."""
        try:
            cmd = self._build_command(['pkexec', 'systemctl', 'stop', service_name])
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30
            )
            if result.returncode == 0:
                logger.info(f"✓ Servicio {service_name} detenido")
            else:
                logger.warning(f"No se pudo detener {service_name}: {result.stderr}")
        except Exception as e:
            logger.warning(f"No se pudo detener {service_name}: {e}")
    
    def _restart_service(self, service_name: str) -> None:
        """Reinicia un servicio."""
        try:
            cmd = self._build_command(['pkexec', 'systemctl', 'restart', service_name])
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30
            )
            if result.returncode == 0:
                logger.info(f"✓ Servicio {service_name} reiniciado")
            else:
                logger.warning(f"No se pudo reiniciar {service_name}: {result.stderr}")
        except Exception as e:
            logger.warning(f"No se pudo reiniciar {service_name}: {e}")
    
    def _add_to_path(self, component_id: str, component_name: str) -> None:
        """
        Añade un componente al PATH del usuario.
        
        Args:
            component_id: ID del componente
            component_name: Nombre del componente
        """
        try:
            # Detectar ruta del binario
            binary_paths = {
                'git': '/usr/bin/git',
                'nodejs': '/usr/bin/node',
                'yarn': '/usr/bin/yarn',
                'phpunit': '/usr/bin/phpunit',
                'composer': '/usr/bin/composer',
                'wpcli': '/usr/local/bin/wp'
            }
            
            binary_path = binary_paths.get(component_id)
            if not binary_path:
                logger.info(f"{component_name} no requiere configuración adicional de PATH")
                return
            
            # Verificar que el binario existe
            if not os.path.exists(binary_path):
                logger.warning(f"Binario no encontrado en {binary_path}")
                return
            
            # El PATH ya se configura automáticamente al instalar desde apt
            # Solo verificamos que esté disponible
            bin_name = os.path.basename(binary_path)
            if shutil.which(bin_name):
                logger.info(f"✓ {component_name} está disponible en PATH")
            else:
                logger.warning(f"⚠ {component_name} instalado pero no encontrado en PATH")
                logger.info("Puede ser necesario cerrar sesión y volver a entrar")
                
        except Exception as e:
            logger.error(f"Error configurando PATH para {component_name}: {e}")
    
    def _custom_install(self, component_id: str, component: dict, progress_callback=None) -> Tuple[bool, str]:
        """
        Instalación personalizada para componentes que no están en apt.
        
        Args:
            component_id: ID del componente
            component: Diccionario de configuración del componente
            progress_callback: Función para reportar progreso
            
        Returns:
            Tupla (éxito, mensaje)
        """
        if component_id == 'wpcli':
            return self._install_wpcli(progress_callback)
        
        return False, f"Instalación personalizada no implementada para {component_id}"
    
    def _install_wpcli(self, progress_callback=None) -> Tuple[bool, str]:
        """
        Instala WP-CLI descargándolo desde GitHub.
        
        Returns:
            Tupla (éxito, mensaje)
        """
        try:
            logger.info("Instalando WP-CLI desde GitHub...")
            
            if progress_callback:
                progress_callback(20, "Descargando WP-CLI...")
            
            # Descargar WP-CLI
            download_cmd = self._build_command([
                'pkexec', 'curl', '-o', '/tmp/wp-cli.phar',
                'https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar'
            ])
            
            result = subprocess.run(download_cmd, capture_output=True, timeout=120)
            if result.returncode != 0:
                return False, "Error descargando WP-CLI"
            
            if progress_callback:
                progress_callback(50, "Instalando WP-CLI...")
            
            # Dar permisos de ejecución
            chmod_cmd = self._build_command(['pkexec', 'chmod', '+x', '/tmp/wp-cli.phar'])
            subprocess.run(chmod_cmd, capture_output=True, timeout=30)
            
            # Mover a /usr/local/bin
            move_cmd = self._build_command([
                'pkexec', 'mv', '/tmp/wp-cli.phar', '/usr/local/bin/wp'
            ])
            
            result = subprocess.run(move_cmd, capture_output=True, timeout=30)
            if result.returncode != 0:
                return False, "Error instalando WP-CLI"
            
            if progress_callback:
                progress_callback(80, "Verificando instalación...")
            
            # Verificar instalación
            verify_cmd = self._build_command(['wp', '--version'])
            result = subprocess.run(verify_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"✓ WP-CLI instalado: {result.stdout.strip()}")
                
                if progress_callback:
                    progress_callback(100, "WP-CLI instalado correctamente")
                
                return True, "WP-CLI instalado correctamente"
            else:
                return False, "WP-CLI instalado pero no se pudo verificar"
                
        except subprocess.TimeoutExpired:
            return False, "Timeout instalando WP-CLI"
        except Exception as e:
            logger.error(f"Error instalando WP-CLI: {e}", exc_info=True)
            return False, f"Error: {str(e)}"
