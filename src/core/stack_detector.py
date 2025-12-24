"""
LAMP Manager - Stack Detector
Detección automática de componentes del stack LAMP instalados.
"""

import subprocess
import logging
import re
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
            # Verificar si apache2 está instalado
            result = subprocess.run(
                ['which', 'apache2'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                component.installed = True
                
                # Obtener versión
                version_result = subprocess.run(
                    ['apache2', '-v'],
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
            # Intentar detectar MySQL
            result = subprocess.run(
                ['which', 'mysql'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                component.installed = True
                
                # Obtener versión
                version_result = subprocess.run(
                    ['mysql', '--version'],
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
            result = subprocess.run(
                ['which', 'php'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                component.installed = True
                
                # Obtener versión
                version_result = subprocess.run(
                    ['php', '-v'],
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
                                result = subprocess.run(
                                    [str(php_bin), '-v'],
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
        Detección genérica de componentes por binario.
        
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
            # Verificar si el binario está disponible
            result = subprocess.run(
                ['which', binary],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                component.installed = True
                component.path = result.stdout.strip()
                
                # Intentar obtener versión con --version
                try:
                    version_result = subprocess.run(
                        [binary, '--version'],
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
                
                logger.debug(f"{comp_id} detectado: {component.version or 'instalado'}")
            
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
