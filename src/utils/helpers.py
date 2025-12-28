"""
XLAMP Manager - Utilities
Funciones de utilidad general.
"""

import logging
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional


def setup_logging(log_file: str = "logs/lamp_manager.log", level: int = logging.INFO) -> None:
    """
    Configura el sistema de logging con rotación de archivos.
    
    Args:
        log_file: Ruta del archivo de log
        level: Nivel de logging
    """
    from logging.handlers import RotatingFileHandler
    
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Formato
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Handler con rotación: máximo 2 MB, mantener 3 backups
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=2 * 1024 * 1024,  # 2 MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # Configurar logging raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Limpiar handlers existentes para evitar duplicados
    root_logger.handlers.clear()
    
    # Añadir handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    logging.info(f"Logging configurado: {log_file} (max 2 MB, 3 backups)")


def create_backup(file_path: str, backup_dir: str = "backups") -> Optional[str]:
    """
    Crea un backup de un archivo.
    
    Args:
        file_path: Ruta del archivo a respaldar
        backup_dir: Directorio de backups
        
    Returns:
        Ruta del backup o None si falla
    """
    try:
        source = Path(file_path)
        if not source.exists():
            return None
        
        # Crear directorio de backups
        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # Nombre del backup con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{source.stem}_{timestamp}{source.suffix}"
        backup_file = backup_path / backup_name
        
        # Copiar archivo
        shutil.copy2(source, backup_file)
        logging.info(f"Backup creado: {backup_file}")
        
        return str(backup_file)
        
    except Exception as e:
        logging.error(f"Error creando backup de {file_path}: {e}")
        return None


def validate_domain(domain: str) -> bool:
    """
    Valida un nombre de dominio.
    
    Args:
        domain: Dominio a validar
        
    Returns:
        True si es válido
    """
    import re
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
    return bool(re.match(pattern, domain))


def validate_path(path: str, must_exist: bool = False) -> bool:
    """
    Valida una ruta de archivo/directorio.
    
    Args:
        path: Ruta a validar
        must_exist: Si debe existir
        
    Returns:
        True si es válida
    """
    try:
        p = Path(path)
        if must_exist:
            return p.exists()
        # Verificar que la ruta sea válida (no vacía, sin caracteres inválidos)
        return bool(path and path.strip())
    except Exception:
        return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitiza un nombre de archivo.
    
    Args:
        filename: Nombre a sanitizar
        
    Returns:
        Nombre sanitizado
    """
    import re
    # Eliminar caracteres no permitidos
    filename = re.sub(r'[^\w\s-]', '', filename)
    # Reemplazar espacios por guiones
    filename = re.sub(r'[-\s]+', '-', filename)
    return filename.strip('-').lower()


def format_bytes(bytes_value: float) -> str:
    """
    Formatea bytes a unidades legibles.
    
    Args:
        bytes_value: Valor en bytes
        
    Returns:
        String formateado
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def is_root() -> bool:
    """
    Verifica si el proceso se ejecuta como root.
    
    Returns:
        True si es root
    """
    return os.geteuid() == 0


def check_command_exists(command: str) -> bool:
    """
    Verifica si un comando existe en el sistema.
    
    Args:
        command: Nombre del comando
        
    Returns:
        True si existe
    """
    return shutil.which(command) is not None
