"""
LAMP Manager - PHP Manager
Gestión específica de versiones PHP.
"""

import os
import logging
import subprocess
from typing import List, Tuple, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class PHPManager:
    """Gestiona instalación y configuración de versiones PHP."""
    
    SUPPORTED_VERSIONS = ['8.0', '8.1', '8.2', '8.3']
    
    def __init__(self, use_flatpak: bool = False):
        """
        Inicializa el gestor de PHP.
        
        Args:
            use_flatpak: Si está ejecutándose en Flatpak
        """
        self.use_flatpak = use_flatpak
        logger.info(f"PHPManager inicializado (flatpak: {use_flatpak})")
    
    def _build_command(self, cmd: List[str]) -> List[str]:
        """
        Construye comando con soporte para Flatpak.
        
        Args:
            cmd: Comando base
            
        Returns:
            Comando adaptado para el entorno
        """
        if self.use_flatpak:
            return ['flatpak-spawn', '--host'] + cmd
        return cmd
    
    def detect_installed_versions(self) -> Dict[str, dict]:
        """
        Detecta versiones de PHP instaladas.
        
        Returns:
            Diccionario con información de versiones instaladas
        """
        installed = {}
        
        for version in self.SUPPORTED_VERSIONS:
            try:
                # Verificar si el binario existe
                cmd = self._build_command(['which', f'php{version}'])
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0 and result.stdout.strip():
                    php_path = result.stdout.strip()
                    
                    # Obtener información detallada
                    cmd_version = self._build_command([f'php{version}', '-v'])
                    version_result = subprocess.run(cmd_version, capture_output=True, text=True, timeout=5)
                    
                    # Verificar módulos instalados
                    cmd_modules = self._build_command([f'php{version}', '-m'])
                    modules_result = subprocess.run(cmd_modules, capture_output=True, text=True, timeout=5)
                    modules = modules_result.stdout.strip().split('\n') if modules_result.returncode == 0 else []
                    
                    # Verificar FPM
                    fpm_installed = self._check_fpm_installed(version)
                    fpm_running = self._check_fpm_running(version) if fpm_installed else False
                    
                    installed[version] = {
                        'path': php_path,
                        'version_info': version_result.stdout.split('\n')[0] if version_result.returncode == 0 else '',
                        'modules': modules,
                        'fpm_installed': fpm_installed,
                        'fpm_running': fpm_running,
                        'is_default': self._is_default_version(version)
                    }
                    
                    logger.info(f"PHP {version} detectado: {php_path}")
            except Exception as e:
                logger.debug(f"PHP {version} no encontrado: {e}")
        
        return installed
    
    def _check_fpm_installed(self, version: str) -> bool:
        """Verifica si PHP-FPM está instalado para una versión."""
        try:
            cmd = self._build_command(['dpkg', '-l', f'php{version}-fpm'])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return result.returncode == 0 and 'ii' in result.stdout
        except:
            return False
    
    def _check_fpm_running(self, version: str) -> bool:
        """Verifica si PHP-FPM está corriendo."""
        try:
            cmd = self._build_command(['systemctl', 'is-active', f'php{version}-fpm'])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return result.returncode == 0 and result.stdout.strip() == 'active'
        except:
            return False
    
    def _is_default_version(self, version: str) -> bool:
        """Verifica si es la versión por defecto del sistema."""
        try:
            cmd = self._build_command(['php', '--version'])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return version in result.stdout
        except:
            return False
    
    def install_php_version(self, version: str, with_fpm: bool = True, 
                          progress_callback: Optional[callable] = None) -> Tuple[bool, str]:
        """
        Instala una versión específica de PHP.
        
        Args:
            version: Versión a instalar (ej: '8.3')
            with_fpm: Si instalar PHP-FPM
            progress_callback: Función para reportar progreso
            
        Returns:
            Tupla (éxito, mensaje)
        """
        logger.info(f"=== Iniciando instalación de PHP {version} ===")
        logger.info(f"Modo: {'FPM' if with_fpm else 'mod_php'}")
        logger.info(f"Flatpak: {self.use_flatpak}")
        
        if version not in self.SUPPORTED_VERSIONS:
            logger.error(f"Versión {version} no soportada")
            return False, f"Versión {version} no soportada"
        
        try:
            # Verificar y reparar sistema antes de instalar
            if progress_callback:
                progress_callback(0.05, "Verificando sistema...")
            
            logger.info("Reparando sistema antes de instalar...")
            repair_success, repair_msg = self._repair_system()
            logger.info(f"Resultado de reparación: {repair_success} - {repair_msg}")
            if not repair_success:
                logger.warning(f"Advertencia al reparar sistema: {repair_msg}")
            
            # Agregar repositorio PPA de Ondrej si no está
            if progress_callback:
                progress_callback(0.1, "Verificando repositorio PHP...")
            
            if not self._check_php_ppa():
                if progress_callback:
                    progress_callback(0.15, "Agregando repositorio PPA de Ondrej...")
                
                success, msg = self._add_php_ppa()
                if not success:
                    return False, f"Error agregando repositorio PHP: {msg}"
            
            if progress_callback:
                progress_callback(0.25, "Actualizando lista de paquetes...")
            
            # Paquetes base a instalar
            packages = [
                f'php{version}',
                f'php{version}-cli',
                f'php{version}-common',
                f'php{version}-mysql',
                f'php{version}-xml',
                f'php{version}-curl',
                f'php{version}-mbstring',
                f'php{version}-zip',
                f'php{version}-gd',
                f'php{version}-intl',
            ]
            
            if with_fpm:
                packages.append(f'php{version}-fpm')
            else:
                packages.append(f'libapache2-mod-php{version}')
            
            # Actualizar repositorio
            if progress_callback:
                progress_callback(0.35, "Actualizando repositorio...")
            
            update_cmd = self._build_command(['pkexec', 'apt-get', 'update'])
            result = subprocess.run(update_cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                logger.warning(f"apt-get update retornó {result.returncode}: {result.stderr}")
            
            # Instalar paquetes
            if progress_callback:
                progress_callback(0.45, f"Instalando PHP {version} y módulos...")
            
            install_cmd = self._build_command([
                'pkexec', 'apt-get', 'install', '-y', '--fix-broken'
            ] + packages)
            
            logger.info(f"Comando de instalación: {' '.join(install_cmd)}")
            logger.info(f"Paquetes a instalar: {', '.join(packages)}")
            logger.info("Ejecutando instalación...")
            
            result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=600)
            
            logger.info(f"Código de retorno: {result.returncode}")
            logger.info(f"STDOUT ({len(result.stdout)} chars): {result.stdout[:500]}")
            if result.stderr:
                logger.error(f"STDERR ({len(result.stderr)} chars): {result.stderr[:500]}")
            
            if result.returncode != 0:
                error_output = result.stderr or result.stdout or "Error desconocido"
                logger.error(f"Error instalando PHP {version}: {error_output}")
                
                # Detectar tipo de error específico
                if "dpkg" in error_output and "error code" in error_output:
                    return False, (
                        f"Error de dependencias al instalar PHP {version}.\n\n"
                        "Solución recomendada:\n"
                        "1. Abre una terminal y ejecuta:\n"
                        "   sudo dpkg --configure -a\n"
                        "   sudo apt-get install -f\n"
                        "   sudo apt-get clean\n"
                        "   sudo apt-get update\n\n"
                        "2. Luego vuelve a intentar desde LAMP Manager.\n\n"
                        "Detalles del error:\n"
                        f"{error_output[:300]}"
                    )
                elif "Unable to locate package" in error_output or "No se ha podido localizar el paquete" in error_output:
                    return False, (
                        f"No se encontraron los paquetes de PHP {version}.\n\n"
                        "Ejecuta desde terminal:\n"
                        "  sudo add-apt-repository ppa:ondrej/php\n"
                        "  sudo apt update\n"
                        "  sudo apt install php{version}\n\n"
                        "Luego reinicia LAMP Manager."
                    )
                
                return False, f"Error instalando PHP {version}.\n\nDetalles:\n{error_output[:400]}"
            
            # Configurar Apache si es necesario
            if with_fpm:
                if progress_callback:
                    progress_callback(0.8, "Configurando Apache para PHP-FPM...")
                
                self._configure_apache_fpm(version)
                
                # Iniciar PHP-FPM
                start_cmd = self._build_command([
                    'pkexec', 'systemctl', 'enable', '--now', f'php{version}-fpm'
                ])
                subprocess.run(start_cmd, capture_output=True, timeout=30)
            else:
                if progress_callback:
                    progress_callback(0.8, "Configurando Apache para mod_php...")
                
                self._configure_apache_modphp(version)
            
            # Reiniciar Apache
            if progress_callback:
                progress_callback(0.9, "Reiniciando Apache...")
            
            restart_cmd = self._build_command(['pkexec', 'systemctl', 'restart', 'apache2'])
            subprocess.run(restart_cmd, capture_output=True, timeout=30)
            
            if progress_callback:
                progress_callback(1.0, "Instalación completada")
            
            logger.info(f"✓ PHP {version} instalado correctamente")
            return True, f"PHP {version} instalado correctamente"
            
        except subprocess.TimeoutExpired:
            return False, "Timeout durante la instalación (operación tardó más de 10 minutos)"
        except Exception as e:
            logger.error(f"Error instalando PHP {version}: {e}", exc_info=True)
            return False, f"Error inesperado: {str(e)}"
    
    def _repair_system(self) -> Tuple[bool, str]:
        """Repara dependencias rotas antes de instalar."""
        try:
            # Configurar paquetes pendientes
            configure_cmd = self._build_command(['pkexec', 'dpkg', '--configure', '-a'])
            subprocess.run(configure_cmd, capture_output=True, timeout=60)
            
            # Reparar dependencias rotas
            fix_cmd = self._build_command(['pkexec', 'apt-get', 'install', '-f', '-y'])
            result = subprocess.run(fix_cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                logger.info("✓ Sistema reparado correctamente")
                return True, "Sistema reparado"
            else:
                return False, "No se pudo reparar automáticamente"
                
        except Exception as e:
            logger.warning(f"Error reparando sistema: {e}")
            return False, str(e)
    
    def _check_php_ppa(self) -> bool:
        """Verifica si el PPA de Ondrej está agregado."""
        try:
            cmd = self._build_command(['grep', '-r', 'ondrej/php', '/etc/apt/sources.list.d/'])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _add_php_ppa(self) -> Tuple[bool, str]:
        """Agrega el repositorio PPA de Ondrej para PHP."""
        try:
            # Instalar software-properties-common si no está
            install_props_cmd = self._build_command([
                'pkexec', 'apt-get', 'install', '-y', 'software-properties-common'
            ])
            subprocess.run(install_props_cmd, capture_output=True, timeout=60)
            
            # Agregar PPA
            add_ppa_cmd = self._build_command([
                'pkexec', 'add-apt-repository', '-y', 'ppa:ondrej/php'
            ])
            result = subprocess.run(add_ppa_cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                logger.info("✓ Repositorio PPA de Ondrej agregado")
                return True, "Repositorio agregado correctamente"
            else:
                error_msg = result.stderr or result.stdout
                logger.error(f"Error agregando PPA: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"Error agregando PPA: {e}", exc_info=True)
            return False, str(e)
    
    def uninstall_php_version(self, version: str, 
                            progress_callback: Optional[callable] = None) -> Tuple[bool, str]:
        """
        Desinstala una versión de PHP.
        
        Args:
            version: Versión a desinstalar
            progress_callback: Función para reportar progreso
            
        Returns:
            Tupla (éxito, mensaje)
        """
        try:
            if progress_callback:
                progress_callback(0.2, f"Desinstalando PHP {version}...")
            
            # Desinstalar todos los paquetes relacionados
            purge_cmd = self._build_command([
                'pkexec', 'apt-get', 'purge', '-y', f'php{version}*'
            ])
            
            result = subprocess.run(purge_cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                return False, f"Error desinstalando PHP {version}"
            
            if progress_callback:
                progress_callback(0.8, "Limpiando dependencias...")
            
            # Autoremove
            autoremove_cmd = self._build_command(['pkexec', 'apt-get', 'autoremove', '-y'])
            subprocess.run(autoremove_cmd, capture_output=True, timeout=120)
            
            if progress_callback:
                progress_callback(1.0, "Desinstalación completada")
            
            logger.info(f"✓ PHP {version} desinstalado")
            return True, f"PHP {version} desinstalado correctamente"
            
        except Exception as e:
            logger.error(f"Error desinstalando PHP {version}: {e}", exc_info=True)
            return False, str(e)
    
    def _configure_apache_fpm(self, version: str) -> None:
        """Configura Apache para usar PHP-FPM."""
        try:
            # Habilitar módulos necesarios
            cmd = self._build_command([
                'pkexec', 'bash', '-c',
                'a2enmod proxy proxy_fcgi rewrite && a2dismod php* mpm_prefork && a2enmod mpm_event'
            ])
            subprocess.run(cmd, capture_output=True, timeout=30)
            
            logger.info(f"Apache configurado para PHP-FPM {version}")
        except Exception as e:
            logger.warning(f"Error configurando Apache para FPM: {e}")
    
    def _configure_apache_modphp(self, version: str) -> None:
        """Configura Apache para usar mod_php."""
        try:
            # Habilitar mod_php
            cmd = self._build_command([
                'pkexec', 'bash', '-c',
                f'a2enmod php{version} && a2dismod mpm_event && a2enmod mpm_prefork'
            ])
            subprocess.run(cmd, capture_output=True, timeout=30)
            
            logger.info(f"Apache configurado para mod_php {version}")
        except Exception as e:
            logger.warning(f"Error configurando Apache para mod_php: {e}")
    
    def set_default_version(self, version: str) -> Tuple[bool, str]:
        """
        Establece una versión de PHP como predeterminada del sistema.
        
        Args:
            version: Versión a establecer como predeterminada
            
        Returns:
            Tupla (éxito, mensaje)
        """
        try:
            cmd = self._build_command([
                'pkexec', 'update-alternatives', '--set', 'php', f'/usr/bin/php{version}'
            ])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                logger.info(f"PHP {version} establecido como predeterminado")
                return True, f"PHP {version} es ahora la versión predeterminada"
            else:
                return False, "Error estableciendo versión predeterminada"
                
        except Exception as e:
            logger.error(f"Error estableciendo versión predeterminada: {e}", exc_info=True)
            return False, str(e)
