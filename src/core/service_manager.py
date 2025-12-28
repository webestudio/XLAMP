"""
XLAMP Manager - Service Manager
Gestión de servicios del sistema con pkexec.
"""

import subprocess
import logging
import psutil
import shutil
from typing import Optional, List
from pathlib import Path
from datetime import datetime, timedelta

from data.models import ServiceStatus

logger = logging.getLogger(__name__)


class ServiceManager:
    """Gestor de servicios del sistema."""
    
    SERVICES = {
        'apache2': 'Apache',
        'mysql': 'MySQL',
        'php-fpm': 'PHP-FPM',
    }
    
    def __init__(self):
        """Inicializa el gestor de servicios."""
        # Buscar systemctl en múltiples ubicaciones
        self.systemctl = self._find_systemctl()
        
        # Buscar alternativas si systemctl no está disponible
        self.service_cmd = self._find_service()
        self.invoke_rc = self._find_invoke_rc()
        
        # Determinar qué método usar
        if self.systemctl:
            self.method = 'systemctl'
            logger.info(f"✓ Usando systemctl: {self.systemctl}")
        elif self.service_cmd:
            self.method = 'service'
            logger.info(f"✓ Usando service (fallback): {self.service_cmd}")
        elif self.invoke_rc:
            self.method = 'invoke-rc.d'
            logger.info(f"✓ Usando invoke-rc.d (fallback): {self.invoke_rc}")
        else:
            self.method = None
            logger.warning("⚠️ No se encontró systemctl, service ni invoke-rc.d - gestión de servicios no disponible")
    
    def _find_systemctl(self) -> Optional[str]:
        """Busca el ejecutable systemctl en el sistema."""
        possible_paths = [
            '/usr/bin/systemctl',
            '/bin/systemctl',
            shutil.which('systemctl'),
        ]
        
        for path in possible_paths:
            if path and Path(path).exists():
                return path
        
        return None
    
    def _find_service(self) -> Optional[str]:
        """Busca el comando service (SysV init)."""
        possible_paths = [
            '/usr/sbin/service',
            '/sbin/service',
            shutil.which('service'),
        ]
        
        for path in possible_paths:
            if path and Path(path).exists():
                return path
        
        return None
    
    def _find_invoke_rc(self) -> Optional[str]:
        """Busca invoke-rc.d (Debian/Ubuntu)."""
        possible_paths = [
            '/usr/sbin/invoke-rc.d',
            '/sbin/invoke-rc.d',
            shutil.which('invoke-rc.d'),
        ]
        
        for path in possible_paths:
            if path and Path(path).exists():
                return path
        
        return None
    
    def get_status(self, service_name: str) -> ServiceStatus:
        """
        Obtiene el estado de un servicio.
        
        Args:
            service_name: Nombre del servicio
            
        Returns:
            Estado del servicio
        """
        status = ServiceStatus(name=service_name)
        
        if not self.systemctl:
            logger.debug(f"systemctl no disponible, no se puede verificar {service_name}")
            return status
        
        try:
            # Verificar si está ejecutándose
            result = subprocess.run(
                [self.systemctl, 'is-active', service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            status.running = (result.returncode == 0)
            
            # Verificar si está habilitado
            result = subprocess.run(
                [self.systemctl, 'is-enabled', service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            status.enabled = (result.returncode == 0)
            
            # Si está ejecutándose, obtener información adicional
            if status.running:
                status_result = subprocess.run(
                    [self.systemctl, 'status', service_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                # Extraer PID
                for line in status_result.stdout.split('\n'):
                    if 'Main PID' in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'PID:' and i + 1 < len(parts):
                                try:
                                    status.pid = int(parts[i + 1])
                                except ValueError:
                                    pass
                
                # Obtener uso de recursos si tenemos el PID
                if status.pid:
                    try:
                        process = psutil.Process(status.pid)
                        status.memory_usage = process.memory_info().rss / (1024 * 1024)  # MB
                        status.cpu_percent = process.cpu_percent(interval=0.1)
                        
                        # Calcular uptime
                        create_time = datetime.fromtimestamp(process.create_time())
                        uptime_delta = datetime.now() - create_time
                        status.uptime = self._format_uptime(uptime_delta)
                        
                    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                        logger.debug(f"No se pudo obtener info del proceso: {e}")
            
            logger.debug(f"Estado de {service_name}: {status.status_text}")
            
        except Exception as e:
            logger.error(f"Error obteniendo estado de {service_name}: {e}")
        
        return status
    
    def get_all_status(self, installed_components: dict = None) -> List[ServiceStatus]:
        """
        Obtiene el estado de todos los servicios LAMP.
        
        Args:
            installed_components: Diccionario de componentes instalados
        
        Returns:
            Lista de estados de servicios
        """
        if not self.method:
            logger.warning("No hay método disponible para obtener estado de servicios")
            return []
        
        statuses = []
        services_added = set()
        
        # Servicios principales siempre verificados
        core_services = ['apache2', 'mysql', 'mariadb']
        
        for service_name in core_services:
            if service_name not in services_added:
                status = self.get_status(service_name)
                # Solo agregar si el servicio existe (tiene información válida)
                if status.running or self._service_exists(service_name):
                    statuses.append(status)
                    services_added.add(service_name)
        
        # Detectar todas las versiones de PHP-FPM realmente instaladas
        php_versions_detected = []
        
        # Buscar versiones de PHP instaladas en el sistema
        import glob
        import os
        for php_bin in glob.glob('/usr/bin/php[0-9]*'):
            if php_bin == '/usr/bin/php':
                continue
            # Extraer versión (ej: /usr/bin/php8.3 -> 8.3)
            version = php_bin.replace('/usr/bin/php', '')
            if '.' in version:
                # Verificar que el socket de FPM exista o el binario de FPM
                fpm_socket = f'/run/php/php{version}-fpm.sock'
                fpm_bin = f'/usr/sbin/php-fpm{version}'
                fpm_bin_alt = f'/usr/sbin/php{version}-fpm'
                
                # Solo agregar si tiene FPM instalado
                if os.path.exists(fpm_socket) or os.path.exists(fpm_bin) or os.path.exists(fpm_bin_alt):
                    php_versions_detected.append(version)
                    logger.info(f"PHP {version} con FPM detectado")
                else:
                    logger.debug(f"PHP {version} encontrado pero sin FPM instalado")
        
        logger.info(f"Versiones de PHP con FPM instaladas: {php_versions_detected}")
        
        # Solo agregar servicios FPM para versiones realmente instaladas
        for version in php_versions_detected:
            service_name = f'php{version}-fpm'
            if service_name not in services_added:
                logger.info(f"Agregando servicio {service_name}...")
                status = self.get_status(service_name)
                statuses.append(status)
                services_added.add(service_name)
        
        logger.info(f"Total de servicios detectados: {len(statuses)}")
        return statuses
    
    def _service_exists(self, service_name: str) -> bool:
        """
        Verifica si un servicio existe en el sistema.
        
        Args:
            service_name: Nombre del servicio
            
        Returns:
            True si el servicio existe
        """
        try:
            if self.method == 'systemctl' and self.systemctl:
                cmd = [self.systemctl, 'list-unit-files', f'{service_name}.service']
                logger.debug(f"Verificando existencia de {service_name}: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                exists = f'{service_name}.service' in result.stdout
                logger.debug(f"{service_name} existe: {exists}")
                return exists
            elif self.method == 'service' and self.service_cmd:
                cmd = [self.service_cmd, '--status-all']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                return service_name in result.stdout
            elif self.method == 'invoke-rc.d' and self.invoke_rc:
                cmd = [self.invoke_rc, service_name, 'status']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                return result.returncode != 127  # 127 = command not found
            else:
                logger.debug(f"No hay método disponible para verificar {service_name}")
        except Exception as e:
            logger.debug(f"Error verificando existencia de {service_name}: {e}")
        return False
    
    def manage_all_services(self, action: str, services: List[str]) -> tuple[bool, str]:
        """
        Ejecuta una acción (start/stop/restart) en múltiples servicios con una sola llamada a pkexec.
        
        Args:
            action: Acción a realizar ('start', 'stop', 'restart')
            services: Lista de nombres de servicios
            
        Returns:
            Tupla (éxito, mensaje)
        """
        if not self.method:
            return False, "No hay gestor de servicios disponible"
            
        if not services:
            return False, "No hay servicios seleccionados"
            
        try:
            # Construir comando compuesto
            commands = []
            
            if self.method == 'systemctl':
                # systemctl permite múltiples servicios en un comando: systemctl start s1 s2 s3
                cmd = ['pkexec', self.systemctl, action] + services
                
            elif self.method == 'service':
                # service requiere un comando por servicio: service s1 start && service s2 start
                shell_cmd = " && ".join([f"{self.service_cmd} {svc} {action}" for svc in services])
                cmd = ['pkexec', 'sh', '-c', shell_cmd]
                
            elif self.method == 'invoke-rc.d':
                shell_cmd = " && ".join([f"{self.invoke_rc} {svc} {action}" for svc in services])
                cmd = ['pkexec', 'sh', '-c', shell_cmd]
            
            logger.info(f"Ejecutando acción masiva '{action}': {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info(f"✓ Acción '{action}' completada para todos los servicios")
                return True, f"Acción '{action}' completada correctamente"
            else:
                error_msg = result.stderr.strip() or "Error desconocido"
                if "Authentication cancelled" in error_msg or "not authorized" in error_msg:
                    return False, "Autenticación cancelada"
                return False, f"Error: {error_msg}"
                
        except Exception as e:
            logger.error(f"Error en acción masiva '{action}': {e}")
            return False, str(e)

    def start_service(self, service_name: str) -> tuple[bool, str]:
        """
        Inicia un servicio usando pkexec.
        
        Args:
            service_name: Nombre del servicio
            
        Returns:
            Tupla (éxito, mensaje)
        """
        if not self.method:
            return False, "No hay gestor de servicios disponible (systemctl/service/invoke-rc.d)"
        
        try:
            if self.method == 'systemctl':
                cmd = ['pkexec', self.systemctl, 'start', service_name]
            elif self.method == 'service':
                cmd = ['pkexec', self.service_cmd, service_name, 'start']
            elif self.method == 'invoke-rc.d':
                cmd = ['pkexec', self.invoke_rc, service_name, 'start']
            
            logger.info(f"Ejecutando: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"✓ Servicio {service_name} iniciado correctamente")
                return True, f"Servicio {service_name} iniciado"
            else:
                error_msg = result.stderr or result.stdout or "Error desconocido"
                logger.error(f"✗ Error iniciando {service_name}: {error_msg}")
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            msg = f"Timeout iniciando {service_name}"
            logger.error(msg)
            return False, msg
        except Exception as e:
            msg = f"Error iniciando {service_name}: {str(e)}"
            logger.error(msg, exc_info=True)
            return False, msg
    
    def stop_service(self, service_name: str) -> tuple[bool, str]:
        """
        Detiene un servicio usando pkexec.
        
        Args:
            service_name: Nombre del servicio
            
        Returns:
            Tupla (éxito, mensaje)
        """
        if not self.method:
            return False, "No hay gestor de servicios disponible (systemctl/service/invoke-rc.d)"
        
        try:
            if self.method == 'systemctl':
                cmd = ['pkexec', self.systemctl, 'stop', service_name]
            elif self.method == 'service':
                cmd = ['pkexec', self.service_cmd, service_name, 'stop']
            elif self.method == 'invoke-rc.d':
                cmd = ['pkexec', self.invoke_rc, service_name, 'stop']
            
            logger.info(f"Ejecutando: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"✓ Servicio {service_name} detenido correctamente")
                return True, f"Servicio {service_name} detenido"
            else:
                error_msg = result.stderr or result.stdout or "Error desconocido"
                logger.error(f"✗ Error deteniendo {service_name}: {error_msg}")
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            msg = f"Timeout deteniendo {service_name}"
            logger.error(msg)
            return False, msg
        except Exception as e:
            msg = f"Error deteniendo {service_name}: {str(e)}"
            logger.error(msg, exc_info=True)
            return False, msg
    
    def restart_service(self, service_name: str) -> tuple[bool, str]:
        """
        Reinicia un servicio usando pkexec.
        
        Args:
            service_name: Nombre del servicio
            
        Returns:
            Tupla (éxito, mensaje)
        """
        if not self.method:
            return False, "No hay gestor de servicios disponible (systemctl/service/invoke-rc.d)"
        
        try:
            if self.method == 'systemctl':
                cmd = ['pkexec', self.systemctl, 'restart', service_name]
            elif self.method == 'service':
                cmd = ['pkexec', self.service_cmd, service_name, 'restart']
            elif self.method == 'invoke-rc.d':
                cmd = ['pkexec', self.invoke_rc, service_name, 'restart']
            else:
                return False, f"Método desconocido: {self.method}"
            
            logger.info(f"Ejecutando: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"✓ Servicio {service_name} reiniciado correctamente")
                return True, f"Servicio {service_name} reiniciado correctamente"
            else:
                error_msg = result.stderr or result.stdout or "Error desconocido"
                logger.error(f"✗ Error reiniciando {service_name}: {error_msg}")
                return False, f"Error reiniciando servicio: {error_msg}"
                
        except subprocess.TimeoutExpired:
            msg = f"Timeout reiniciando {service_name} (operación tardó más de 30 segundos)"
            logger.error(msg)
            return False, msg
        except FileNotFoundError as e:
            msg = f"Comando no encontrado: {e.filename}"
            logger.error(msg)
            return False, msg
        except Exception as e:
            msg = f"Error reiniciando {service_name}: {str(e)}"
            logger.error(msg, exc_info=True)
            return False, msg
    
    def enable_service(self, service_name: str) -> tuple[bool, str]:
        """
        Habilita un servicio para inicio automático.
        
        Args:
            service_name: Nombre del servicio
            
        Returns:
            Tupla (éxito, mensaje)
        """
        if not self.systemctl:
            return False, "systemctl no está disponible en este sistema"
        
        try:
            result = subprocess.run(
                ['pkexec', self.systemctl, 'enable', service_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"Servicio {service_name} habilitado")
                return True, f"Servicio {service_name} habilitado para inicio automático"
            else:
                error_msg = result.stderr or "Error desconocido"
                logger.error(f"Error habilitando {service_name}: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            msg = f"Error habilitando {service_name}: {str(e)}"
            logger.error(msg)
            return False, msg
    
    def disable_service(self, service_name: str) -> tuple[bool, str]:
        """
        Deshabilita un servicio del inicio automático.
        
        Args:
            service_name: Nombre del servicio
            
        Returns:
            Tupla (éxito, mensaje)
        """
        if not self.systemctl:
            return False, "systemctl no está disponible en este sistema"
        
        try:
            result = subprocess.run(
                ['pkexec', self.systemctl, 'disable', service_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"Servicio {service_name} deshabilitado")
                return True, f"Servicio {service_name} deshabilitado del inicio automático"
            else:
                error_msg = result.stderr or "Error desconocido"
                logger.error(f"Error deshabilitando {service_name}: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            msg = f"Error deshabilitando {service_name}: {str(e)}"
            logger.error(msg)
            return False, msg
    
    def _format_uptime(self, delta: timedelta) -> str:
        """
        Formatea el tiempo de actividad.
        
        Args:
            delta: Diferencia de tiempo
            
        Returns:
            Tiempo formateado
        """
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if not parts:  # Menos de un minuto
            parts.append(f"{seconds}s")
        
        return " ".join(parts)
