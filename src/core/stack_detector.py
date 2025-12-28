"""
XLAMP Manager - Stack Detector
Detección automática de componentes del stack LAMP instalados.
"""

import subprocess
import logging
import re
import os
from typing import Optional, Dict, List
from pathlib import Path

from data.models import StackComponent, PHPVersion

logger = logging.getLogger(__name__)


class StackDetector:
    """Detector de componentes del stack LAMP."""
    
    def __init__(self):
        """Inicializa el detector."""
        self.components: Dict[str, StackComponent] = {}
        self.php_versions: List[PHPVersion] = []
        self.use_flatpak = os.path.exists('/.flatpak-info')
        
        # Detectar sistema de gestión de paquetes disponible
        self.pkg_manager = self._detect_package_manager()
        
        if self.use_flatpak:
            logger.info("Detectando desde Flatpak - usando flatpak-spawn --host")
        logger.info(f"Sistema de paquetes detectado: {self.pkg_manager or 'ninguno (usando solo which)'}")
    
    def _build_command(self, cmd: list) -> list:
        """Construye el comando con flatpak-spawn si es necesario."""
        if self.use_flatpak and cmd[0] not in ['flatpak-spawn']:
            return ['flatpak-spawn', '--host'] + cmd
        return cmd
    
    def _detect_package_manager(self) -> Optional[str]:
        """Detecta qué sistema de gestión de paquetes está disponible."""
        managers = {
            'dpkg': ['dpkg', '--version'],
            'rpm': ['rpm', '--version'],
            'pacman': ['pacman', '--version']
        }
        
        for name, cmd in managers.items():
            try:
                # Intentar directamente
                result = subprocess.run(cmd, capture_output=True, timeout=2)
                if result.returncode == 0:
                    logger.info(f"Sistema de paquetes {name} disponible")
                    return name
            except FileNotFoundError:
                # Si no se encuentra, intentar con flatpak-spawn
                try:
                    result = subprocess.run(['flatpak-spawn', '--host'] + cmd, 
                                          capture_output=True, timeout=2)
                    if result.returncode == 0:
                        logger.info(f"Sistema de paquetes {name} disponible (vía flatpak-spawn)")
                        return name
                except:
                    pass
            except:
                pass
        
        logger.warning("No se detectó sistema de paquetes (dpkg/rpm/pacman) - usando solo 'which'")
        return None
    
    def _check_package_installed(self, package: str) -> Optional[bool]:
        """
        Verifica si un paquete está instalado usando el gestor de paquetes disponible.
        Intenta primero directamente, luego con flatpak-spawn si es necesario.
        
        Returns:
            True: paquete instalado
            False: paquete NO instalado (verificado)
            None: no se pudo verificar (gestor no disponible)
        """
        if not self.pkg_manager or not package:
            return None
        
        try:
            if self.pkg_manager == 'dpkg':
                # Intentar ambos métodos: directo y con flatpak-spawn
                for cmd in [['dpkg', '-l', package], 
                           ['flatpak-spawn', '--host', 'dpkg', '-l', package]]:
                    try:
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                        
                        if result.returncode == 0:
                            # Buscar líneas que empiecen con 'ii' (instalado)
                            # Formato dpkg: "ii  nombre-paquete  version..."
                            is_installed = any(line.startswith('ii ') for line in result.stdout.split('\n'))
                            logger.info(f"dpkg ({cmd[0]}): {package} = {'instalado' if is_installed else 'no instalado'}")
                            return is_installed
                    except FileNotFoundError:
                        logger.info(f"Comando {cmd[0]} no encontrado, probando siguiente método...")
                        continue  # Intentar siguiente método
                    except Exception as e:
                        logger.info(f"Error con {cmd[0]}: {e}")
                        continue
                
                return False  # Ningún método funcionó
                
            elif self.pkg_manager == 'rpm':
                for cmd in [['rpm', '-q', package],
                           ['flatpak-spawn', '--host', 'rpm', '-q', package]]:
                    try:
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            return True
                    except FileNotFoundError:
                        continue
                    except:
                        continue
                return False
                
            elif self.pkg_manager == 'pacman':
                for cmd in [['pacman', '-Q', package],
                           ['flatpak-spawn', '--host', 'pacman', '-Q', package]]:
                    try:
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            return True
                    except FileNotFoundError:
                        continue
                    except:
                        continue
                return False
                
        except Exception as e:
            logger.debug(f"Error verificando paquete {package}: {e}")
        
        return None
    
    def detect_all(self) -> Dict[str, StackComponent]:
        """
        Detecta todos los componentes del stack.
        
        Returns:
            Diccionario con componentes detectados
        """
        logger.info("Iniciando detección del stack LAMP...")
        
        # Componentes principales
        self.components = {
            'apache2': self.detect_apache(),
            'mysql': self.detect_mysql(),
            'php': self.detect_php(),
        }
        
        # Componentes adicionales con detección genérica
        additional_components = {
            'mariadb': ('mariadb', 'mariadb-server', 'mariadb'),
            'composer': ('composer', 'composer', None),
            'phpmyadmin': ('phpmyadmin', 'phpmyadmin', None),
            'adminer': ('adminer', 'adminer', None),
            'git': ('git', 'git', None),
            'nodejs': ('node', 'nodejs', None),
            'yarn': ('yarn', 'yarn', None),
            'redis': ('redis-server', 'redis-server', 'redis-server'),
            'memcached': ('memcached', 'memcached', 'memcached'),
            'varnish': ('varnishd', 'varnish', 'varnish'),
            'xdebug': ('php-xdebug', 'php-xdebug', None),
            'phpunit': ('phpunit', 'phpunit', None),
            'wpcli': ('wp', 'wp-cli', None)
        }
        
        for comp_id, (binary, package, service) in additional_components.items():
            self.components[comp_id] = self._detect_generic(
                comp_id, binary, package, service
            )
        
        # Detectar versiones PHP disponibles
        self.php_versions = self.detect_php_versions()
        
        return self.components
    
    def detect_apache(self) -> StackComponent:
        """Detecta Apache."""
        component = StackComponent(
            name='apache2',
            service_name='apache2',
            package_name='apache2'
        )
        
        try:
            # Verificar con gestor de paquetes si está disponible
            pkg_installed = self._check_package_installed('apache2')
            
            # Si el gestor dice definitivamente que NO está instalado
            if pkg_installed is False:
                logger.info("Apache no está instalado (verificado con gestor de paquetes)")
                return component
            
            # Verificar si apache2 está disponible
            which_cmd = self._build_command(['which', 'apache2'])
            result = subprocess.run(
                which_cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Está instalado si: pkg_manager dice SÍ OR which lo encuentra
            if result.returncode == 0 or pkg_installed is True:
                component.installed = True
                
                # Obtener versión
                version_cmd = self._build_command(['apache2', '-v'])
                version_result = subprocess.run(
                    version_cmd,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if version_result.returncode == 0:
                    match = re.search(r'Apache/(\d+\.\d+\.\d+)', version_result.stdout)
                    if match:
                        component.version = match.group(1)
                
                logger.info(f"Apache detectado: {component.version}")
            else:
                logger.info("Apache no está instalado")
                
        except Exception as e:
            logger.error(f"Error detectando Apache: {e}")
        
        return component
    
    def detect_mysql(self) -> StackComponent:
        """Detecta MySQL/MariaDB."""
        component = StackComponent(
            name='mysql',
            service_name='mysql',
            package_name='mysql-server'
        )
        
        try:
            # Verificar con gestor de paquetes si está disponible
            pkg_installed = None
            for pkg in ['mysql-server', 'mariadb-server']:
                result = self._check_package_installed(pkg)
                if result is True:
                    pkg_installed = True
                    component.package_name = pkg
                    break
                elif result is False:
                    pkg_installed = False
            
            # Si el gestor dice definitivamente que NO está instalado
            if pkg_installed is False:
                logger.info("MySQL no está instalado (verificado con gestor de paquetes)")
                return component
            
            # Intentar detectar MySQL
            which_cmd = self._build_command(['which', 'mysql'])
            result = subprocess.run(
                which_cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Está instalado si: pkg_manager dice SÍ OR which lo encuentra
            if result.returncode == 0 or pkg_installed is True:
                component.installed = True
                
                # Obtener versión
                version_cmd = self._build_command(['mysql', '--version'])
                version_result = subprocess.run(
                    version_cmd,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if version_result.returncode == 0:
                    # Buscar versión en el output
                    match = re.search(r'(\d+\.\d+\.\d+)', version_result.stdout)
                    if match:
                        component.version = match.group(1)
                    
                    # Detectar si es MariaDB
                    if 'MariaDB' in version_result.stdout:
                        component.package_name = 'mariadb-server'
                
                logger.info(f"MySQL/MariaDB detectado: {component.version}")
            else:
                logger.info("MySQL no está instalado")
                
        except Exception as e:
            logger.error(f"Error detectando MySQL: {e}")
        
        return component
    
    def detect_php(self) -> StackComponent:
        """Detecta PHP."""
        component = StackComponent(
            name='php',
            service_name=None,  # PHP no es un servicio directo
            package_name='php'
        )
        
        try:
            # Verificar si PHP está instalado
            which_cmd = self._build_command(['which', 'php'])
            result = subprocess.run(
                which_cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                component.installed = True
                
                # Obtener versión
                version_cmd = self._build_command(['php', '-v'])
                version_result = subprocess.run(
                    version_cmd,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if version_result.returncode == 0:
                    match = re.search(r'PHP (\d+\.\d+\.\d+)', version_result.stdout)
                    if match:
                        component.version = match.group(1)
                
                logger.info(f"PHP detectado: {component.version}")
            else:
                logger.info("PHP no está instalado")
                
        except Exception as e:
            logger.error(f"Error detectando PHP: {e}")
        
        return component
    
    def detect_php_versions(self) -> List[PHPVersion]:
        """
        Detecta todas las versiones de PHP instaladas.
        
        Returns:
            Lista de versiones PHP detectadas
        """
        versions = []
        
        # Buscar versiones en /usr/bin
        try:
            bin_path = Path('/usr/bin')
            if bin_path.exists():
                # Buscar ejecutables php*
                for php_bin in bin_path.glob('php*'):
                    if php_bin.is_file() and php_bin.name.startswith('php'):
                        # Extraer versión del nombre
                        match = re.match(r'php(\d+\.\d+)', php_bin.name)
                        if match:
                            version_num = match.group(1)
                            
                            # Verificar que sea ejecutable
                            try:
                                version_cmd = self._build_command([str(php_bin), '-v'])
                                result = subprocess.run(
                                    version_cmd,
                                    capture_output=True,
                                    text=True,
                                    timeout=5
                                )
                                
                                if result.returncode == 0:
                                    # Extraer versión completa
                                    version_match = re.search(
                                        r'PHP (\d+\.\d+\.\d+)',
                                        result.stdout
                                    )
                                    full_version = version_match.group(1) if version_match else version_num
                                    
                                    # Verificar si es la versión activa
                                    is_active = php_bin.name == 'php'
                                    
                                    php_version = PHPVersion(
                                        version=full_version,
                                        path=str(php_bin),
                                        is_active=is_active,
                                        is_installed=True
                                    )
                                    versions.append(php_version)
                                    logger.info(f"PHP {full_version} detectado en {php_bin}")
                                    
                            except Exception as e:
                                logger.debug(f"Error verificando {php_bin}: {e}")
            
            # Si no se encontró ninguna versión pero PHP está instalado
            if not versions and self.components.get('php', {}).installed:
                default_php = self.components['php']
                if default_php.version:
                    versions.append(PHPVersion(
                        version=default_php.version,
                        path='/usr/bin/php',
                        is_active=True,
                        is_installed=True
                    ))
                    
        except Exception as e:
            logger.error(f"Error detectando versiones PHP: {e}")
        
        return versions
    
    def _detect_generic(self, comp_id: str, binary: str, package: str, service: Optional[str]) -> StackComponent:
        """
        Detección genérica de componentes por binario y paquete.
        
        Args:
            comp_id: ID del componente
            binary: Nombre del binario a buscar
            package: Nombre del paquete
            service: Nombre del servicio (opcional)
            
        Returns:
            StackComponent con información de detección
        """
        component = StackComponent(
            name=comp_id,
            service_name=service,
            package_name=package
        )
        
        try:
            # Verificar con gestor de paquetes si está disponible
            pkg_installed = self._check_package_installed(package)
            
            # Si el gestor dice definitivamente que NO está instalado
            if pkg_installed is False:
                logger.debug(f"{comp_id} no instalado (verificado con gestor de paquetes)")
                return component
            
            # Verificar si el binario está disponible
            binary_found = False
            binary_path = None
            try:
                which_cmd = self._build_command(['which', binary])
                result = subprocess.run(
                    which_cmd,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    binary_found = True
                    binary_path = result.stdout.strip()
            except:
                pass
            
            # Componente instalado si: pkg_manager dice SÍ OR which lo encuentra
            if pkg_installed is True or binary_found:
                component.installed = True
                component.path = binary_path
                
                # Intentar obtener versión con --version
                if binary_found:
                    try:
                        version_cmd = self._build_command([binary, '--version'])
                        version_result = subprocess.run(
                            version_cmd,
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        
                        if version_result.returncode == 0:
                            # Buscar patrones comunes de versión
                            version_match = re.search(
                                r'(\d+\.\d+(?:\.\d+)?)',
                                version_result.stdout
                            )
                            if version_match:
                                component.version = version_match.group(1)
                    except:
                        pass
                
                logger.debug(f"{comp_id} detectado: pkg_manager={pkg_installed}, binary={binary_found}, version={component.version or 'desconocida'}")
            else:
                logger.debug(f"{comp_id} no instalado")
            
        except Exception as e:
            logger.debug(f"Error detectando {comp_id}: {e}")
        
        return component
    
    def is_service_running(self, service_name: str) -> bool:
        """
        Verifica si un servicio está ejecutándose.
        
        Args:
            service_name: Nombre del servicio
            
        Returns:
            True si el servicio está activo
        """
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error verificando servicio {service_name}: {e}")
            return False
    
    def get_package_info(self, package_name: str) -> Optional[Dict[str, str]]:
        """
        Obtiene información de un paquete instalado.
        
        Args:
            package_name: Nombre del paquete
            
        Returns:
            Diccionario con información del paquete o None
        """
        try:
            result = subprocess.run(
                ['dpkg', '-s', package_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                info = {}
                for line in result.stdout.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        info[key.strip()] = value.strip()
                return info
                
        except Exception as e:
            logger.debug(f"No se pudo obtener info de {package_name}: {e}")
        
        return None
