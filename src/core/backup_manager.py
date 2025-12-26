"""
LAMP Manager - Backup Manager
Gestión de copias de seguridad de bases de datos y configuraciones.
"""

import os
import logging
import subprocess
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
import json

logger = logging.getLogger(__name__)


class BackupManager:
    """Gestiona copias de seguridad de bases de datos y configuraciones."""
    
    def __init__(self, backup_dir: str = "backups", use_flatpak: bool = False):
        """
        Inicializa el gestor de backups.
        
        Args:
            backup_dir: Directorio donde guardar los backups
            use_flatpak: Si está ejecutándose en Flatpak
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.use_flatpak = use_flatpak
        
        # Subdirectorios por tipo
        self.db_backup_dir = self.backup_dir / "databases"
        self.config_backup_dir = self.backup_dir / "configs"
        self.vhost_backup_dir = self.backup_dir / "vhosts"
        
        for dir_path in [self.db_backup_dir, self.config_backup_dir, self.vhost_backup_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"BackupManager inicializado: {self.backup_dir}")
    
    def _run_command(self, cmd: List[str], timeout: int = 60) -> Tuple[bool, str]:
        """
        Ejecuta un comando con soporte para Flatpak.
        
        Args:
            cmd: Lista con el comando y argumentos
            timeout: Timeout en segundos
            
        Returns:
            Tupla (éxito, mensaje/salida)
        """
        try:
            if self.use_flatpak and cmd[0] not in ['cp', 'mv', 'rm', 'mkdir']:
                cmd = ['flatpak-spawn', '--host'] + cmd
            
            logger.info(f"Ejecutando: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                return True, result.stdout
            else:
                error_msg = result.stderr or result.stdout or "Error desconocido"
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            return False, f"Timeout ejecutando comando ({timeout}s)"
        except FileNotFoundError:
            return False, f"Comando no encontrado: {cmd[0]}"
        except Exception as e:
            return False, str(e)
    
    def backup_mysql_database(self, db_name: str, user: str = "root", password: Optional[str] = None) -> Tuple[bool, str]:
        """
        Crea backup de una base de datos MySQL/MariaDB.
        
        Args:
            db_name: Nombre de la base de datos
            user: Usuario de MySQL
            password: Contraseña (opcional, solicitará interactivamente si no se proporciona)
            
        Returns:
            Tupla (éxito, mensaje)
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = self.db_backup_dir / f"{db_name}_{timestamp}.sql"
            
            # Construir comando mysqldump
            cmd = ['mysqldump']
            if user:
                cmd.extend(['-u', user])
            if password:
                cmd.append(f'-p{password}')
            else:
                cmd.append('-p')  # Solicitará contraseña interactivamente
            
            cmd.append(db_name)
            
            # Ejecutar mysqldump y guardar en archivo
            logger.info(f"Creando backup de MySQL: {db_name}")
            success, output = self._run_command(cmd, timeout=300)  # 5 minutos
            
            if success:
                # Guardar output en archivo
                backup_file.write_text(output)
                
                # Crear metadata
                metadata = {
                    'database': db_name,
                    'type': 'mysql',
                    'timestamp': timestamp,
                    'date': datetime.now().isoformat(),
                    'size_bytes': backup_file.stat().st_size
                }
                metadata_file = self.db_backup_dir / f"{db_name}_{timestamp}.json"
                metadata_file.write_text(json.dumps(metadata, indent=2))
                
                size_mb = backup_file.stat().st_size / (1024 * 1024)
                logger.info(f"✓ Backup creado: {backup_file} ({size_mb:.2f} MB)")
                return True, f"Backup creado: {backup_file.name} ({size_mb:.2f} MB)"
            else:
                return False, f"Error ejecutando mysqldump: {output}"
                
        except Exception as e:
            logger.error(f"Error creando backup de MySQL: {e}", exc_info=True)
            return False, str(e)
    
    def backup_all_mysql_databases(self, user: str = "root", password: Optional[str] = None) -> Tuple[bool, str]:
        """
        Crea backup de todas las bases de datos MySQL/MariaDB.
        
        Args:
            user: Usuario de MySQL
            password: Contraseña
            
        Returns:
            Tupla (éxito, mensaje)
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = self.db_backup_dir / f"all_databases_{timestamp}.sql"
            
            # Construir comando para todas las bases de datos
            cmd = ['mysqldump']
            if user:
                cmd.extend(['-u', user])
            if password:
                cmd.append(f'-p{password}')
            else:
                cmd.append('-p')
            
            cmd.append('--all-databases')
            
            logger.info("Creando backup de todas las bases de datos MySQL")
            success, output = self._run_command(cmd, timeout=600)  # 10 minutos
            
            if success:
                backup_file.write_text(output)
                
                metadata = {
                    'database': 'all',
                    'type': 'mysql',
                    'timestamp': timestamp,
                    'date': datetime.now().isoformat(),
                    'size_bytes': backup_file.stat().st_size
                }
                metadata_file = self.db_backup_dir / f"all_databases_{timestamp}.json"
                metadata_file.write_text(json.dumps(metadata, indent=2))
                
                size_mb = backup_file.stat().st_size / (1024 * 1024)
                logger.info(f"✓ Backup completo creado: {backup_file} ({size_mb:.2f} MB)")
                return True, f"Backup completo creado ({size_mb:.2f} MB)"
            else:
                return False, f"Error ejecutando mysqldump: {output}"
                
        except Exception as e:
            logger.error(f"Error creando backup completo: {e}", exc_info=True)
            return False, str(e)
    
    def backup_apache_config(self) -> Tuple[bool, str]:
        """
        Crea backup de la configuración de Apache.
        
        Returns:
            Tupla (éxito, mensaje)
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = self.config_backup_dir / f"apache_config_{timestamp}.tar.gz"
            
            apache_config_paths = [
                '/etc/apache2/apache2.conf',
                '/etc/apache2/sites-available',
                '/etc/apache2/sites-enabled',
                '/etc/apache2/mods-enabled',
                '/etc/apache2/conf-enabled',
                '/etc/hosts'
            ]
            
            # Construir comando tar
            cmd = ['tar', '-czf', str(backup_file)]
            for path in apache_config_paths:
                if Path(path).exists():
                    cmd.append(path)
            
            logger.info("Creando backup de configuración Apache")
            success, output = self._run_command(cmd, timeout=60)
            
            if success and backup_file.exists():
                metadata = {
                    'type': 'apache_config',
                    'timestamp': timestamp,
                    'date': datetime.now().isoformat(),
                    'size_bytes': backup_file.stat().st_size,
                    'paths': apache_config_paths
                }
                metadata_file = self.config_backup_dir / f"apache_config_{timestamp}.json"
                metadata_file.write_text(json.dumps(metadata, indent=2))
                
                size_mb = backup_file.stat().st_size / (1024 * 1024)
                logger.info(f"✓ Backup de Apache creado: {backup_file} ({size_mb:.2f} MB)")
                return True, f"Backup de Apache creado ({size_mb:.2f} MB)"
            else:
                return False, f"Error creando backup: {output}"
                
        except Exception as e:
            logger.error(f"Error creando backup de Apache: {e}", exc_info=True)
            return False, str(e)
    
    def backup_vhost(self, vhost_name: str, document_root: str, config_path: str) -> Tuple[bool, str]:
        """
        Crea backup de un virtual host específico.
        
        Args:
            vhost_name: Nombre del vhost
            document_root: Directorio raíz del vhost
            config_path: Ruta al archivo de configuración
            
        Returns:
            Tupla (éxito, mensaje)
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = self.vhost_backup_dir / f"{vhost_name}_{timestamp}.tar.gz"
            
            # Construir comando tar
            cmd = ['tar', '-czf', str(backup_file)]
            
            if Path(document_root).exists():
                cmd.append(document_root)
            
            if Path(config_path).exists():
                cmd.append(config_path)
            
            logger.info(f"Creando backup de vhost: {vhost_name}")
            success, output = self._run_command(cmd, timeout=300)
            
            if success and backup_file.exists():
                metadata = {
                    'vhost_name': vhost_name,
                    'document_root': document_root,
                    'config_path': config_path,
                    'timestamp': timestamp,
                    'date': datetime.now().isoformat(),
                    'size_bytes': backup_file.stat().st_size
                }
                metadata_file = self.vhost_backup_dir / f"{vhost_name}_{timestamp}.json"
                metadata_file.write_text(json.dumps(metadata, indent=2))
                
                size_mb = backup_file.stat().st_size / (1024 * 1024)
                logger.info(f"✓ Backup de vhost creado: {backup_file} ({size_mb:.2f} MB)")
                return True, f"Backup de {vhost_name} creado ({size_mb:.2f} MB)"
            else:
                return False, f"Error creando backup: {output}"
                
        except Exception as e:
            logger.error(f"Error creando backup de vhost: {e}", exc_info=True)
            return False, str(e)
    
    def list_backups(self, backup_type: Optional[str] = None) -> List[dict]:
        """
        Lista todos los backups disponibles.
        
        Args:
            backup_type: Tipo de backup ('database', 'config', 'vhost') o None para todos
            
        Returns:
            Lista de diccionarios con información de backups
        """
        backups = []
        
        try:
            if backup_type is None or backup_type == 'database':
                for metadata_file in self.db_backup_dir.glob("*.json"):
                    try:
                        metadata = json.loads(metadata_file.read_text())
                        metadata['backup_type'] = 'database'
                        metadata['metadata_file'] = str(metadata_file)
                        backups.append(metadata)
                    except Exception as e:
                        logger.warning(f"Error leyendo metadata {metadata_file}: {e}")
            
            if backup_type is None or backup_type == 'config':
                for metadata_file in self.config_backup_dir.glob("*.json"):
                    try:
                        metadata = json.loads(metadata_file.read_text())
                        metadata['backup_type'] = 'config'
                        metadata['metadata_file'] = str(metadata_file)
                        backups.append(metadata)
                    except Exception as e:
                        logger.warning(f"Error leyendo metadata {metadata_file}: {e}")
            
            if backup_type is None or backup_type == 'vhost':
                for metadata_file in self.vhost_backup_dir.glob("*.json"):
                    try:
                        metadata = json.loads(metadata_file.read_text())
                        metadata['backup_type'] = 'vhost'
                        metadata['metadata_file'] = str(metadata_file)
                        backups.append(metadata)
                    except Exception as e:
                        logger.warning(f"Error leyendo metadata {metadata_file}: {e}")
            
            # Ordenar por fecha (más reciente primero)
            backups.sort(key=lambda x: x.get('date', ''), reverse=True)
            
        except Exception as e:
            logger.error(f"Error listando backups: {e}", exc_info=True)
        
        return backups
    
    def clean_old_backups(self, days_to_keep: int = 7, max_backups: int = 10) -> Tuple[int, str]:
        """
        Limpia backups antiguos según retención.
        
        Args:
            days_to_keep: Días a mantener
            max_backups: Máximo número de backups a mantener por tipo
            
        Returns:
            Tupla (cantidad eliminada, mensaje)
        """
        try:
            deleted_count = 0
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Procesar cada subdirectorio
            for backup_subdir in [self.db_backup_dir, self.config_backup_dir, self.vhost_backup_dir]:
                # Obtener todos los archivos con metadata
                backups_info = []
                for metadata_file in backup_subdir.glob("*.json"):
                    try:
                        metadata = json.loads(metadata_file.read_text())
                        backup_date = datetime.fromisoformat(metadata.get('date', ''))
                        
                        # Obtener archivo de backup correspondiente
                        backup_filename = metadata_file.stem  # Sin .json
                        possible_exts = ['.sql', '.tar.gz', '.sql.gz']
                        backup_file = None
                        
                        for ext in possible_exts:
                            candidate = backup_subdir / f"{backup_filename}{ext}"
                            if candidate.exists():
                                backup_file = candidate
                                break
                        
                        if backup_file:
                            backups_info.append({
                                'date': backup_date,
                                'metadata_file': metadata_file,
                                'backup_file': backup_file
                            })
                    except Exception as e:
                        logger.warning(f"Error procesando {metadata_file}: {e}")
                
                # Ordenar por fecha (más antiguos primero)
                backups_info.sort(key=lambda x: x['date'])
                
                # Eliminar por antigüedad
                for info in backups_info:
                    if info['date'] < cutoff_date:
                        try:
                            info['metadata_file'].unlink()
                            info['backup_file'].unlink()
                            deleted_count += 1
                            logger.info(f"Eliminado backup antiguo: {info['backup_file'].name}")
                        except Exception as e:
                            logger.warning(f"Error eliminando backup: {e}")
                
                # Mantener solo max_backups más recientes
                if len(backups_info) > max_backups:
                    to_delete = backups_info[:(len(backups_info) - max_backups)]
                    for info in to_delete:
                        try:
                            if info['date'] < cutoff_date:  # Ya contado arriba
                                continue
                            info['metadata_file'].unlink()
                            info['backup_file'].unlink()
                            deleted_count += 1
                            logger.info(f"Eliminado backup excedente: {info['backup_file'].name}")
                        except Exception as e:
                            logger.warning(f"Error eliminando backup: {e}")
            
            if deleted_count > 0:
                msg = f"Eliminados {deleted_count} backups antiguos"
                logger.info(msg)
            else:
                msg = "No hay backups antiguos para eliminar"
            
            return deleted_count, msg
            
        except Exception as e:
            logger.error(f"Error limpiando backups: {e}", exc_info=True)
            return 0, str(e)
    
    def get_backup_stats(self) -> dict:
        """
        Obtiene estadísticas de backups.
        
        Returns:
            Diccionario con estadísticas
        """
        try:
            stats = {
                'total_backups': 0,
                'database_backups': 0,
                'config_backups': 0,
                'vhost_backups': 0,
                'total_size_bytes': 0,
                'total_size_mb': 0.0
            }
            
            # Contar backups de bases de datos
            for file in self.db_backup_dir.glob("*.sql"):
                stats['database_backups'] += 1
                stats['total_size_bytes'] += file.stat().st_size
            
            # Contar backups de configuración
            for file in self.config_backup_dir.glob("*.tar.gz"):
                stats['config_backups'] += 1
                stats['total_size_bytes'] += file.stat().st_size
            
            # Contar backups de vhosts
            for file in self.vhost_backup_dir.glob("*.tar.gz"):
                stats['vhost_backups'] += 1
                stats['total_size_bytes'] += file.stat().st_size
            
            stats['total_backups'] = (
                stats['database_backups'] + 
                stats['config_backups'] + 
                stats['vhost_backups']
            )
            stats['total_size_mb'] = stats['total_size_bytes'] / (1024 * 1024)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}", exc_info=True)
            return {}
