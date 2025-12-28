"""
XLAMP Manager - Base Model
Clase base para modelos con patrón ActiveRecord.
"""

import logging
from typing import List, Optional, Any, Dict, Type, TypeVar
from .database import Database

logger = logging.getLogger(__name__)

T = TypeVar('T', bound='Model')

class Model:
    """Clase base para modelos de datos."""
    
    _db: Optional[Database] = None
    _table: str = ""
    _pk: str = "id"
    
    @classmethod
    def set_db(cls, db: Database) -> None:
        """Establece la instancia de base de datos."""
        cls._db = db
    
    @classmethod
    def get_db(cls) -> Database:
        """Obtiene la instancia de base de datos."""
        if cls._db is None:
            # Si no se ha establecido, intentar crear una nueva instancia
            # Esto asume que Database es un Singleton o se puede instanciar sin args
            cls._db = Database()
        return cls._db

    @classmethod
    def all(cls: Type[T]) -> List[T]:
        """Obtiene todos los registros."""
        try:
            db = cls.get_db()
            cursor = db.conn.cursor()
            cursor.execute(f"SELECT * FROM {cls._table}")
            rows = cursor.fetchall()
            return [cls.from_row(row) for row in rows]
        except Exception as e:
            logger.error(f"Error obteniendo todos los registros de {cls._table}: {e}")
            return []

    @classmethod
    def find(cls: Type[T], pk_value: Any) -> Optional[T]:
        """Busca un registro por su clave primaria."""
        try:
            db = cls.get_db()
            cursor = db.conn.cursor()
            cursor.execute(f"SELECT * FROM {cls._table} WHERE {cls._pk} = ?", (pk_value,))
            row = cursor.fetchone()
            if row:
                return cls.from_row(row)
            return None
        except Exception as e:
            logger.error(f"Error buscando registro en {cls._table}: {e}")
            return None

    @classmethod
    def where(cls: Type[T], conditions: Dict[str, Any]) -> List[T]:
        """Busca registros que cumplan las condiciones."""
        try:
            db = cls.get_db()
            cursor = db.conn.cursor()
            
            query = f"SELECT * FROM {cls._table} WHERE "
            clauses = []
            values = []
            
            for key, value in conditions.items():
                clauses.append(f"{key} = ?")
                values.append(value)
            
            query += " AND ".join(clauses)
            
            cursor.execute(query, tuple(values))
            rows = cursor.fetchall()
            return [cls.from_row(row) for row in rows]
        except Exception as e:
            logger.error(f"Error buscando en {cls._table} con condiciones: {e}")
            return []

    def save(self) -> bool:
        """Guarda el registro (INSERT o UPDATE)."""
        try:
            db = self.get_db()
            cursor = db.conn.cursor()
            data = self.to_dict()
            pk_value = data.get(self._pk)
            
            # Remover PK del diccionario si es None (para INSERT)
            if pk_value is None:
                del data[self._pk]
                columns = ", ".join(data.keys())
                placeholders = ", ".join(["?" for _ in data])
                values = tuple(data.values())
                
                query = f"INSERT INTO {self._table} ({columns}) VALUES ({placeholders})"
                cursor.execute(query, values)
                
                # Actualizar ID en el objeto
                setattr(self, self._pk, cursor.lastrowid)
            else:
                # UPDATE
                # Remover PK de los datos a actualizar
                update_data = data.copy()
                if self._pk in update_data:
                    del update_data[self._pk]
                
                set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()])
                values = tuple(update_data.values()) + (pk_value,)
                
                query = f"UPDATE {self._table} SET {set_clause} WHERE {self._pk} = ?"
                cursor.execute(query, values)
                
                if cursor.rowcount == 0:
                    # Si no actualizó nada, intentar INSERT (caso de PK manual)
                    columns = ", ".join(data.keys())
                    placeholders = ", ".join(["?" for _ in data])
                    values = tuple(data.values())
                    
                    query = f"INSERT INTO {self._table} ({columns}) VALUES ({placeholders})"
                    cursor.execute(query, values)
            
            db.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error guardando registro en {self._table}: {e}")
            return False

    def delete(self) -> bool:
        """Elimina el registro."""
        try:
            pk_value = getattr(self, self._pk)
            if pk_value is None:
                return False
            
            db = self.get_db()
            cursor = db.conn.cursor()
            cursor.execute(f"DELETE FROM {self._table} WHERE {self._pk} = ?", (pk_value,))
            db.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error eliminando registro de {self._table}: {e}")
            return False

    @classmethod
    def from_row(cls: Type[T], row: Any) -> T:
        """Crea una instancia desde una fila de base de datos."""
        # Este método debe ser implementado o usar introspección en las clases hijas
        # Por defecto, asumimos que el constructor acepta kwargs que coinciden con las columnas
        data = dict(row)
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el objeto a diccionario."""
        raise NotImplementedError("Debe implementar to_dict()")
