"""
LAMP Manager - Database module
Gestión de la base de datos SQLite para configuraciones.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class Database:
    """Gestor de la base de datos SQLite."""
    
    def __init__(self, db_path: str = "data/lamp_manager.db"):
        """
        Inicializa la conexión a la base de datos.
        
        Args:
            db_path: Ruta al archivo de base de datos
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None
        self._initialize()
    
    def _initialize(self) -> None:
        """Inicializa la base de datos y crea las tablas necesarias."""
        try:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
            self._create_tables()
            logger.info(f"Base de datos inicializada: {self.db_path}")
        except Exception as e:
            logger.error(f"Error al inicializar la base de datos: {e}")
            raise
    
    def _create_tables(self) -> None:
        """Crea todas las tablas necesarias."""
        cursor = self.conn.cursor()
        
        # Tabla de hosts virtuales
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vhosts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                document_root TEXT NOT NULL,
                server_name TEXT NOT NULL,
                port INTEGER DEFAULT 80,
                php_version TEXT,
                enabled INTEGER DEFAULT 1,
                ssl_enabled INTEGER DEFAULT 0,
                ssl_cert_path TEXT,
                ssl_key_path TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla de versiones PHP
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS php_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL UNIQUE,
                path TEXT NOT NULL,
                is_active INTEGER DEFAULT 0,
                is_installed INTEGER DEFAULT 1,
                detected_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla de configuración de la aplicación
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_config (
                key TEXT PRIMARY KEY,
                value TEXT,
                description TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla de componentes del stack
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stack_components (
                name TEXT PRIMARY KEY,
                installed INTEGER DEFAULT 0,
                version TEXT,
                service_name TEXT,
                package_name TEXT,
                install_date TEXT,
                last_check TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla de logs de operaciones
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation TEXT NOT NULL,
                component TEXT,
                status TEXT,
                message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insertar componentes por defecto si no existen
        components = [
            ('apache2', 'Apache2', 'apache2', 'apache2'),
            ('mysql', 'MySQL', 'mysql', 'mysql-server'),
            ('php', 'PHP', None, 'php'),
        ]
        
        for name, _, service, package in components:
            cursor.execute("""
                INSERT OR IGNORE INTO stack_components (name, service_name, package_name)
                VALUES (?, ?, ?)
            """, (name, service, package))
        
        # Configuración por defecto
        default_config = [
            ('backup_enabled', '1', 'Realizar backups automáticos'),
            ('backup_path', 'backups/', 'Ruta para backups'),
            ('apache_config_path', '/etc/apache2', 'Ruta de configuración de Apache'),
            ('apache_sites_available', '/etc/apache2/sites-available', 'Directorio sites-available'),
            ('apache_sites_enabled', '/etc/apache2/sites-enabled', 'Directorio sites-enabled'),
            ('hosts_file', '/etc/hosts', 'Archivo hosts del sistema'),
            ('default_document_root', '/var/www', 'Raíz por defecto para documentos'),
        ]
        
        for key, value, desc in default_config:
            cursor.execute("""
                INSERT OR IGNORE INTO app_config (key, value, description)
                VALUES (?, ?, ?)
            """, (key, value, desc))
        
        self.conn.commit()
        logger.info("Tablas creadas correctamente")
    
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Ejecuta una consulta SQL.
        
        Args:
            query: Consulta SQL
            params: Parámetros de la consulta
            
        Returns:
            Cursor con los resultados
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            self.conn.commit()
            return cursor
        except Exception as e:
            logger.error(f"Error ejecutando consulta: {e}")
            raise
    
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Ejecuta una consulta y retorna un resultado."""
        cursor = self.execute(query, params)
        return cursor.fetchone()
    
    def fetch_all(self, query: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Ejecuta una consulta y retorna todos los resultados."""
        cursor = self.execute(query, params)
        return cursor.fetchall()
    
    def log_operation(self, operation: str, component: str, status: str, message: str = "") -> None:
        """Registra una operación en el log."""
        self.execute("""
            INSERT INTO operation_logs (operation, component, status, message)
            VALUES (?, ?, ?, ?)
        """, (operation, component, status, message))
    
    def get_config(self, key: str) -> Optional[str]:
        """Obtiene un valor de configuración."""
        result = self.fetch_one("SELECT value FROM app_config WHERE key = ?", (key,))
        return result['value'] if result else None
    
    def set_config(self, key: str, value: str) -> None:
        """Establece un valor de configuración."""
        self.execute("""
            INSERT OR REPLACE INTO app_config (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (key, value))
    
    def add_vhost(self, vhost: 'VirtualHost') -> int:
        """
        Agrega un host virtual a la base de datos.
        
        Args:
            vhost: Objeto VirtualHost
            
        Returns:
            ID del vhost insertado
        """
        cursor = self.execute("""
            INSERT INTO vhosts (name, document_root, server_name, port, php_version, enabled, ssl_enabled, ssl_cert_path, ssl_key_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vhost.name,
            vhost.document_root,
            vhost.server_name,
            vhost.port,
            vhost.php_version,
            int(vhost.enabled),
            int(vhost.ssl_enabled),
            vhost.ssl_cert_path,
            vhost.ssl_key_path
        ))
        return cursor.lastrowid
    
    def get_all_vhosts(self) -> list['VirtualHost']:
        """
        Obtiene todos los hosts virtuales.
        
        Returns:
            Lista de objetos VirtualHost
        """
        from .models import VirtualHost
        from datetime import datetime
        
        rows = self.fetch_all("SELECT * FROM vhosts ORDER BY name")
        vhosts = []
        
        for row in rows:
            vhost = VirtualHost(
                id=row['id'],
                name=row['name'],
                document_root=row['document_root'],
                server_name=row['server_name'],
                port=row['port'],
                php_version=row['php_version'],
                enabled=bool(row['enabled']),
                ssl_enabled=bool(row['ssl_enabled']),
                ssl_cert_path=row['ssl_cert_path'],
                ssl_key_path=row['ssl_key_path'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
            )
            vhosts.append(vhost)
        
        return vhosts
    
    def get_vhost(self, vhost_id: int) -> Optional['VirtualHost']:
        """
        Obtiene un host virtual por ID.
        
        Args:
            vhost_id: ID del vhost
            
        Returns:
            Objeto VirtualHost o None
        """
        from .models import VirtualHost
        from datetime import datetime
        
        row = self.fetch_one("SELECT * FROM vhosts WHERE id = ?", (vhost_id,))
        
        if not row:
            return None
        
        return VirtualHost(
            id=row['id'],
            name=row['name'],
            document_root=row['document_root'],
            server_name=row['server_name'],
            port=row['port'],
            php_version=row['php_version'],
            enabled=bool(row['enabled']),
            ssl_enabled=bool(row['ssl_enabled']),
            ssl_cert_path=row['ssl_cert_path'],
            ssl_key_path=row['ssl_key_path'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )
    
    def update_vhost(self, vhost: 'VirtualHost') -> None:
        """
        Actualiza un host virtual.
        
        Args:
            vhost: Objeto VirtualHost con datos actualizados
        """
        self.execute("""
            UPDATE vhosts
            SET name = ?, document_root = ?, server_name = ?, port = ?, php_version = ?,
                enabled = ?, ssl_enabled = ?, ssl_cert_path = ?, ssl_key_path = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            vhost.name,
            vhost.document_root,
            vhost.server_name,
            vhost.port,
            vhost.php_version,
            int(vhost.enabled),
            int(vhost.ssl_enabled),
            vhost.ssl_cert_path,
            vhost.ssl_key_path,
            vhost.id
        ))
    
    def delete_vhost(self, vhost_id: int) -> None:
        """
        Elimina un host virtual.
        
        Args:
            vhost_id: ID del vhost a eliminar
        """
        self.execute("DELETE FROM vhosts WHERE id = ?", (vhost_id,))
    
    def close(self) -> None:
        """Cierra la conexión a la base de datos."""
        if self.conn:
            self.conn.close()
            logger.info("Conexión a la base de datos cerrada")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
