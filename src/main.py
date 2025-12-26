#!/usr/bin/env python3
"""
LAMP Manager - Main Entry Point
Aplicación GUI para gestión del stack LAMP en Linux.
"""

import sys
import signal
import logging
import traceback
from pathlib import Path

# Agregar directorio src al path
sys.path.insert(0, str(Path(__file__).parent))

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from .data import Database
from .ui import MainWindow
from .utils import setup_logging

logger = logging.getLogger(__name__)


def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Maneja excepciones no capturadas globalmente."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    logger.error(
        "Excepción no manejada:",
        exc_info=(exc_type, exc_value, exc_traceback)
    )
    
    # Mostrar diálogo de error al usuario
    try:
        dialog = Gtk.MessageDialog(
            parent=None,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.CLOSE,
            text="Error Fatal"
        )
        error_detail = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        dialog.format_secondary_text(
            f"La aplicación encontró un error inesperado:\n\n"
            f"{exc_type.__name__}: {exc_value}\n\n"
            f"Revisa los logs en: logs/lamp_manager.log"
        )
        dialog.run()
        dialog.destroy()
    except:
        pass  # Si falla el diálogo, al menos está en el log


# Instalar manejador global de excepciones
sys.excepthook = global_exception_handler


class LAMPManagerApp:
    """Aplicación principal de LAMP Manager."""
    
    def __init__(self):
        """Inicializa la aplicación."""
        # Configurar logging
        setup_logging()
        logger.info("Iniciando LAMP Manager...")
        
        # Verificar que no se ejecute como root
        from utils import is_root
        if is_root():
            logger.warning("No se recomienda ejecutar la aplicación como root")
        
        # Inicializar base de datos
        try:
            self.db = Database()
            logger.info("Base de datos inicializada correctamente")
        except Exception as e:
            logger.error(f"Error inicializando base de datos: {e}")
            sys.exit(1)
        
        # Crear ventana principal
        try:
            self.window = MainWindow(self.db)
            self.window.connect("destroy", self.on_quit)
            logger.info("Interfaz gráfica creada correctamente")
        except Exception as e:
            logger.error(f"Error creando interfaz: {e}")
            sys.exit(1)
        
        # Manejar señales del sistema
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def run(self) -> None:
        """Ejecuta la aplicación."""
        try:
            self.window.show_all()
            logger.info("LAMP Manager iniciado correctamente")
            Gtk.main()
        except KeyboardInterrupt:
            logger.info("Interrupción por teclado")
            self.on_quit()
        except Exception as e:
            logger.error(f"Error en el loop principal: {e}", exc_info=True)
            self._show_error_dialog(f"Error fatal: {str(e)}")
            sys.exit(1)
    
    def _show_error_dialog(self, message: str) -> None:
        """Muestra un diálogo de error."""
        try:
            dialog = Gtk.MessageDialog(
                parent=self.window if hasattr(self, 'window') else None,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Error en LAMP Manager"
            )
            dialog.format_secondary_text(message)
            dialog.run()
            dialog.destroy()
        except:
            print(f"ERROR: {message}", file=sys.stderr)
    
    def on_quit(self, *args) -> None:
        """Cierra la aplicación limpiamente."""
        logger.info("Cerrando LAMP Manager...")
        
        # Cerrar base de datos
        if hasattr(self, 'db'):
            self.db.close()
        
        Gtk.main_quit()
    
    def signal_handler(self, sig, frame) -> None:
        """Maneja señales del sistema."""
        logger.info(f"Señal recibida: {sig}")
        self.on_quit()


def main() -> int:
    """
    Punto de entrada principal.
    
    Returns:
        Código de salida
    """
    try:
        app = LAMPManagerApp()
        app.run()
        return 0
    except Exception as e:
        print(f"Error fatal: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
