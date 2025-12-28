"""
XLAMP Manager - Data models
Modelos de datos para vhosts, PHP, y componentes del stack.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
from .base_model import Model


@dataclass
class VirtualHost(Model):
    """Modelo de host virtual."""
    _table = "vhosts"
    
    id: Optional[int] = None
    name: str = ""
    document_root: str = ""
    server_name: str = ""
    port: int = 80
    php_version: Optional[str] = None
    enabled: bool = True
    ssl_enabled: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convierte el modelo a diccionario."""
        return {
            'id': self.id,
            'name': self.name,
            'document_root': self.document_root,
            'server_name': self.server_name,
            'port': self.port,
            'php_version': self.php_version,
            'enabled': 1 if self.enabled else 0,
            'ssl_enabled': 1 if self.ssl_enabled else 0,
            'ssl_cert_path': self.ssl_cert_path,
            'ssl_key_path': self.ssl_key_path,
        }
    
    @classmethod
    def from_row(cls, row: Any) -> 'VirtualHost':
        """Crea instancia desde fila de BD."""
        data = dict(row)
        # Convertir enteros a booleanos
        data['enabled'] = bool(data.get('enabled', 1))
        data['ssl_enabled'] = bool(data.get('ssl_enabled', 0))
        return cls(**data)


@dataclass
class PHPVersion(Model):
    """Modelo de versión PHP."""
    _table = "php_versions"
    
    id: Optional[int] = None
    version: str = ""
    path: str = ""
    is_active: bool = False
    is_installed: bool = True
    detected_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'version': self.version,
            'path': self.path,
            'is_active': 1 if self.is_active else 0,
            'is_installed': 1 if self.is_installed else 0
        }

    @classmethod
    def from_row(cls, row: Any) -> 'PHPVersion':
        data = dict(row)
        data['is_active'] = bool(data.get('is_active', 0))
        data['is_installed'] = bool(data.get('is_installed', 1))
        return cls(**data)

    detected_at: Optional[datetime] = None
    
    def __str__(self) -> str:
        return f"PHP {self.version} ({'activa' if self.is_active else 'instalada'})"


@dataclass
class StackComponent:
    """Modelo de componente del stack LAMP."""
    name: str = ""
    installed: bool = False
    version: Optional[str] = None
    service_name: Optional[str] = None
    package_name: Optional[str] = None
    install_date: Optional[datetime] = None
    last_check: Optional[datetime] = None
    
    @property
    def display_name(self) -> str:
        """Nombre para mostrar."""
        names = {
            'apache2': 'Apache',
            'mysql': 'MySQL',
            'php': 'PHP',
        }
        return names.get(self.name, self.name.title())
    
    def __str__(self) -> str:
        status = "✓ Instalado" if self.installed else "✗ No instalado"
        version = f" ({self.version})" if self.version else ""
        return f"{self.display_name}: {status}{version}"


@dataclass
class ServiceStatus:
    """Estado de un servicio."""
    name: str
    running: bool = False
    enabled: bool = False
    pid: Optional[int] = None
    memory_usage: float = 0.0
    cpu_percent: float = 0.0
    uptime: Optional[str] = None
    
    @property
    def status_text(self) -> str:
        """Texto de estado."""
        if self.running:
            return "Ejecutando"
        return "Detenido"
    
    @property
    def status_color(self) -> str:
        """Color del estado."""
        return "green" if self.running else "red"


@dataclass
class OperationLog:
    """Registro de operación."""
    id: Optional[int] = None
    operation: str = ""
    component: str = ""
    status: str = ""
    message: str = ""
    created_at: Optional[datetime] = None


@dataclass
class Config(Model):
    """Modelo de configuración."""
    _table = "app_config"
    _pk = "key"
    
    key: str = ""
    value: str = ""
    description: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'key': self.key,
            'value': self.value,
            'description': self.description
        }
    
    @classmethod
    def from_row(cls, row: Any) -> 'Config':
        return cls(**dict(row))
    
    @classmethod
    def get_value(cls, key: str, default: str = None) -> str:
        """Helper para obtener valor directamente."""
        config = cls.find(key)
        return config.value if config else default

    @classmethod
    def set_value(cls, key: str, value: str, description: str = None) -> None:
        """Helper para guardar valor directamente."""
        config = cls.find(key)
        if config:
            config.value = value
            if description:
                config.description = description
            config.save()
        else:
            config = cls(key=key, value=value, description=description)
            config.save()
