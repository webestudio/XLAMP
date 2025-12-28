"""
XLAMP Manager - Install Dialog
Diálogo de instalación de componentes del stack.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import logging
import threading

from ..core import StackInstaller

logger = logging.getLogger(__name__)


class InstallDialog(Gtk.Dialog):
    """Diálogo para instalar componentes del stack LAMP."""
    
    def __init__(self, parent, installed_components: dict = None):
        """
        Inicializa el diálogo.
        
        Args:
            parent: Ventana padre
            installed_components: Componentes ya instalados
        """
        super().__init__(
            title="Instalar Stack LAMP",
            parent=parent,
            flags=0
        )
        
        self.installer = StackInstaller()
        self.installed_components = installed_components or {}
        self.selected_components = []
        
        # Configurar diálogo
        self.set_default_size(600, 450)
        self.set_border_width(0)
        
        # Crear contenido
        self._create_ui()
        
        # Botones
        self.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        self.install_button = self.add_button("Instalar", Gtk.ResponseType.OK)
        self.install_button.get_style_context().add_class("suggested-action")
        self.install_button.set_sensitive(False)
        
        # Conectar señal de respuesta para manejar el botón Instalar
        self.connect("response", self._on_response)
        
        # Flag para indicar si la instalación fue exitosa
        self.installation_successful = False
    
    def _on_response(self, dialog, response_id):
        """Maneja la respuesta del diálogo."""
        if response_id == Gtk.ResponseType.OK and not self.installation_successful:
            # Prevenir que el diálogo se cierre
            self.stop_emission_by_name("response")
            # Iniciar instalación
            self.start_installation()
    
    def _create_ui(self) -> None:
        """Crea la interfaz del diálogo."""
        content = self.get_content_area()
        content.set_spacing(0)
        
        # Header con icono
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        header.set_margin_start(20)
        header.set_margin_end(20)
        header.set_margin_top(20)
        header.set_margin_bottom(15)
        
        icon = Gtk.Image.new_from_icon_name("system-software-install", Gtk.IconSize.DIALOG)
        header.pack_start(icon, False, False, 0)
        
        vbox_header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        
        title_label = Gtk.Label()
        title_label.set_markup("<span size='large' weight='bold'>Instalar componentes del Stack LAMP</span>")
        title_label.set_halign(Gtk.Align.START)
        vbox_header.pack_start(title_label, False, False, 0)
        
        desc_label = Gtk.Label()
        desc_label.set_markup("<span>Selecciona los componentes que deseas instalar en tu sistema</span>")
        desc_label.set_halign(Gtk.Align.START)
        desc_label.get_style_context().add_class("dim-label")
        vbox_header.pack_start(desc_label, False, False, 0)
        
        header.pack_start(vbox_header, True, True, 0)
        content.pack_start(header, False, False, 0)
        
        # Separador
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        content.pack_start(sep, False, False, 0)
        
        # ScrolledWindow para componentes
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_margin_start(20)
        scrolled.set_margin_end(20)
        scrolled.set_margin_top(10)
        scrolled.set_min_content_height(200)
        
        components_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        # Lista de componentes
        self.checkboxes = {}
        
        for comp_id, comp_info in self.installer.COMPONENTS.items():
            # Solo filtrar el paquete base PHP (se gestiona en pestaña PHP)
            # Las herramientas relacionadas se mantienen disponibles
            if comp_id == 'php':
                continue
            
            # Verificar si está instalado
            is_installed = (comp_id in self.installed_components and 
                          self.installed_components[comp_id].installed)
            
            frame = Gtk.Frame()
            frame.get_style_context().add_class("component-frame")
            if is_installed:
                frame.get_style_context().add_class("installed")
            
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            hbox.set_margin_start(12)
            hbox.set_margin_end(12)
            hbox.set_margin_top(8)
            hbox.set_margin_bottom(8)
            
            # Checkbox
            checkbox = Gtk.CheckButton()
            checkbox.set_active(False)
            checkbox.connect("toggled", self._on_component_toggled)
            
            if is_installed:
                checkbox.set_sensitive(False)
            
            self.checkboxes[comp_id] = checkbox
            hbox.pack_start(checkbox, False, False, 0)
            
            # Información del componente
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            
            name_label = Gtk.Label()
            name_text = f"<span weight='bold'>{comp_info['name']}</span>"
            if is_installed:
                version = self.installed_components[comp_id].version
                name_text += f" <span foreground='#27ae60' size='small'>✓"
                if version:
                    name_text += f" v{version}"
                name_text += "</span>"
            name_label.set_markup(name_text)
            name_label.set_halign(Gtk.Align.START)
            vbox.pack_start(name_label, False, False, 0)
            
            desc_label = Gtk.Label(label=comp_info['description'])
            desc_label.set_halign(Gtk.Align.START)
            desc_label.set_line_wrap(True)
            desc_label.set_max_width_chars(50)
            desc_label.get_style_context().add_class("component-description")
            vbox.pack_start(desc_label, False, False, 0)
            
            hbox.pack_start(vbox, True, True, 0)
            
            frame.add(hbox)
            components_box.pack_start(frame, False, False, 0)
        
        scrolled.add(components_box)
        content.pack_start(scrolled, True, True, 0)
        
        # Frame de progreso (oculto inicialmente)
        self.progress_frame = Gtk.Frame(label="Estado de Instalación")
        self.progress_frame.get_style_context().add_class("info-box")
        self.progress_frame.set_margin_start(20)
        self.progress_frame.set_margin_end(20)
        self.progress_frame.set_margin_top(10)
        self.progress_frame.set_margin_bottom(15)
        self.progress_frame.set_no_show_all(True)
        
        progress_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        progress_inner.set_margin_start(15)
        progress_inner.set_margin_end(15)
        progress_inner.set_margin_top(10)
        progress_inner.set_margin_bottom(10)
        
        # Componente actual
        self.current_component_label = Gtk.Label()
        self.current_component_label.set_markup("<b>Preparando instalación...</b>")
        self.current_component_label.set_halign(Gtk.Align.START)
        progress_inner.pack_start(self.current_component_label, False, False, 0)
        
        # Mensaje de estado
        self.progress_label = Gtk.Label(label="Iniciando...")
        self.progress_label.set_halign(Gtk.Align.START)
        self.progress_label.get_style_context().add_class("dim-label")
        progress_inner.pack_start(self.progress_label, False, False, 0)
        
        # Barra de progreso
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        progress_inner.pack_start(self.progress_bar, False, False, 0)
        
        # Estado final (oculto inicialmente)
        self.status_label = Gtk.Label()
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.set_no_show_all(True)
        progress_inner.pack_start(self.status_label, False, False, 0)
        
        self.progress_frame.add(progress_inner)
        content.pack_start(self.progress_frame, False, False, 0)
        
        self.show_all()
    
    def _on_component_toggled(self, checkbox) -> None:
        """Handler cuando se marca/desmarca un componente."""
        # Actualizar lista de seleccionados
        self.selected_components = [
            comp_id for comp_id, cb in self.checkboxes.items()
            if cb.get_active()
        ]
        
        # Habilitar botón de instalar si hay selección
        self.install_button.set_sensitive(len(self.selected_components) > 0)
    
    def get_selected_components(self) -> list:
        """Retorna los componentes seleccionados."""
        return self.selected_components
    
    def start_installation(self) -> None:
        """Inicia la instalación de componentes seleccionados."""
        if not self.selected_components:
            return
        
        # Deshabilitar controles
        for checkbox in self.checkboxes.values():
            checkbox.set_sensitive(False)
        self.install_button.set_sensitive(False)
        
        # Mostrar frame de progreso
        self.progress_frame.show()
        
        # Instalar en thread separado
        thread = threading.Thread(
            target=self._install_thread,
            args=(self.selected_components,)
        )
        thread.daemon = True
        thread.start()
    
    def _install_thread(self, components: list) -> None:
        """Thread de instalación."""
        try:
            total = len(components)
            
            for i, comp_id in enumerate(components):
                try:
                    comp_name = self.installer.COMPONENTS[comp_id]['name']
                    
                    # Actualizar componente actual
                    GLib.idle_add(
                        self._update_current_component,
                        comp_name,
                        i + 1,
                        total
                    )
                    
                    # Actualizar UI - iniciando componente
                    base_progress = int((i / total) * 100)
                    GLib.idle_add(
                        self._update_progress,
                        base_progress,
                        f"Preparando instalación..."
                    )
                    
                    # Definir callback de progreso para este componente
                    def progress_callback(percent, message):
                        # Calcular progreso combinado
                        component_progress = base_progress + int((percent / 100) * (100 / total))
                        # Limpiar emojis del mensaje
                        clean_message = message.replace('🔄', '').replace('📥', '').replace('⚙️', '').replace('✅', '').strip()
                        GLib.idle_add(self._update_progress, component_progress, clean_message)
                        return False
                    
                    # Instalar componente con callback
                    success, msg = self.installer.install_component(comp_id, progress_callback)
                    
                    if not success:
                        logger.error(f"Fallo en instalación de {comp_name}: {msg}")
                        GLib.idle_add(self._update_status, f"Error: {msg}", False)
                        GLib.idle_add(self._show_error, f"{comp_name}: {msg}")
                        return
                    else:
                        logger.info(f"✓ {comp_name} instalado correctamente")
                        GLib.idle_add(self._update_status, f"{comp_name} instalado correctamente", True)
                        
                except Exception as e:
                    logger.error(f"Error instalando {comp_id}: {e}", exc_info=True)
                    GLib.idle_add(self._update_status, f"Error: {str(e)}", False)
                    GLib.idle_add(self._show_error, f"Error instalando {comp_name}: {str(e)}")
                    return
            
            # Completado
            GLib.idle_add(self._update_progress, 100, "Instalación completada")
            GLib.idle_add(self._update_status, "✓ Todos los componentes instalados correctamente", True)
            import time
            time.sleep(1.5)  # Dar tiempo para ver el 100%
            GLib.idle_add(self._installation_complete)
        except Exception as e:
            logger.error(f"Error fatal en instalación: {e}", exc_info=True)
            GLib.idle_add(self._update_status, f"Error fatal: {str(e)}", False)
            GLib.idle_add(self._show_error, f"Error fatal: {str(e)}")
    
    def _update_current_component(self, component_name: str, current: int, total: int) -> bool:
        """Actualiza el componente actual en instalación."""
        self.current_component_label.set_markup(
            f"<b>Instalando {component_name}</b> ({current} de {total})"
        )
        return False
    
    def _update_progress(self, progress: int, message: str) -> bool:
        """Actualiza la barra de progreso."""
        self.progress_bar.set_fraction(progress / 100.0)
        self.progress_bar.set_text(f"{progress}%")
        self.progress_label.set_text(message)
        return False
    
    def _update_status(self, message: str, success: bool) -> bool:
        """Actualiza el estado final."""
        if success:
            self.status_label.set_markup(f"<span foreground='#27ae60'>{message}</span>")
        else:
            self.status_label.set_markup(f"<span foreground='#e74c3c'>{message}</span>")
        self.status_label.show()
        return False
    
    def _show_error(self, message: str) -> bool:
        """Muestra un error."""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Error de instalación"
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()
        
        # Re-habilitar botón de cancelar para poder cerrar
        self.installation_successful = False
        return False
    
    def _installation_complete(self) -> bool:
        """Maneja la finalización de la instalación."""
        # Marcar instalación como exitosa
        self.installation_successful = True
        # Cerrar el diálogo
        self.response(Gtk.ResponseType.OK)
        return False
