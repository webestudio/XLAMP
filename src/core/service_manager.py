"""
LAMP Manager - Service Manager
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
        if not self.systemctl:
            return []
        
        statuses = []
        
        # Mapeo de componentes a servicios
        component_service_map = {
            'apache2': ['apache2'],
            'mysql': ['mysql'],
            'php': ['php-fpm', 'php7.4-fpm', 'php8.0-fpm', 'php8.1-fpm', 'php8.2-fpm', 'php8.3-fpm'],
        }
        
        # Si se proporcionan componentes instalados, filtrar
        if installed_components:
            for component_name, component in installed_components.items():
                if component.installed and component_name in component_service_map:
                    for service_name in component_service_map[component_name]:
                        # Para PHP, verificar qué servicio existe realmente
                        if 'php' in service_name:
                            # Verificar si el servicio existe
                            result = subprocess.run(
                                [self.systemctl, 'list-unit-files', service_name + '.service'],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            if service_name + '.service' in result.stdout:
                                status = self.get_status(service_name)
                                statuses.append(status)
                                break  # Solo agregar el primer servicio PHP encontrado
                        else:
                            status = self.get_status(service_name)
                            statuses.append(status)
        else:
            # Sin filtro, obtener todos
            for service_name in self.SERVICES.keys():
                status = self.get_status(service_name)
                statuses.append(status)
        
        return statuses
    
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
