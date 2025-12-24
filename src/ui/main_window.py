"""
LAMP Manager - Main Window
Ventana principal de la aplicación con tabs.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk
import logging
from typing import Optional
import os
import shutil
import subprocess
import threading

from core import StackDetector, ServiceManager
from data import Database
from .install_dialog import InstallDialog

logger = logging.getLogger(__name__)


class MainWindow(Gtk.Window):
    """Ventana principal de LAMP Manager."""
    
    def __init__(self, db: Database):
        """
        Inicializa la ventana principal.
        
        Args:
            db: Instancia de la base de datos
        """
        super().__init__(title="LAMP Manager")
        
        self.db = db
        self.stack_detector = StackDetector()
        self.service_manager = ServiceManager()
        self.installed_components = {}  # Componentes instalados
        self.systemctl_available = self.service_manager.systemctl is not None
        
        # Cargar estilos CSS
        self._load_styles()
        
        # Configuración de la ventana
        self.set_default_size(900, 550)
        self.set_border_width(0)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Permitir redimensionar
        self.set_resizable(True)
        
        # Crear interfaz
        self._create_ui()
        
        # Detectar stack al inicio
        GLib.idle_add(self._detect_stack)
        
        # Actualizar estado de servicios cada 5 segundos
        GLib.timeout_add_seconds(5, self._update_services_status)
    
    def _load_styles(self) -> None:
        """Carga los estilos CSS de la aplicación."""
        try:
            css_provider = Gtk.CssProvider()
            css_file = os.path.join(os.path.dirname(__file__), 'styles.css')
            
            if os.path.exists(css_file):
                css_provider.load_from_path(css_file)
                screen = Gdk.Screen.get_default()
                style_context = Gtk.StyleContext()
                style_context.add_provider_for_screen(
                    screen,
                    css_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
                logger.info("Estilos CSS cargados correctamente")
            else:
                logger.warning(f"Archivo CSS no encontrado: {css_file}")
        except Exception as e:
            logger.error(f"Error cargando estilos CSS: {e}")
    
    def _create_ui(self) -> None:
        """Crea la interfaz de usuario."""
        # Container principal
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox)
        
        # Header con título y logo
        header = self._create_header()
        vbox.pack_start(header, False, False, 0)
        
        # Mensaje de advertencia si systemctl no está disponible
        if not self.systemctl_available:
            warning = self._create_warning_banner()
            vbox.pack_start(warning, False, False, 0)
        
        # Notebook con tabs
        self.notebook = Gtk.Notebook()
        self.notebook.set_margin_start(10)
        self.notebook.set_margin_end(10)
        self.notebook.set_margin_bottom(10)
        vbox.pack_start(self.notebook, True, True, 0)
        
        # Tabs
        self._create_services_tab()
        self._create_vhosts_tab()
        self._create_php_tab()
        self._create_stack_tab()
        self._create_config_tab()
        
        # Statusbar
        self.statusbar = Gtk.Statusbar()
        vbox.pack_start(self.statusbar, False, False, 0)
        self._update_statusbar("Listo")
    
    def _create_header(self) -> Gtk.Box:
        """Crea el header de la aplicación."""
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        header.set_margin_start(20)
        header.set_margin_end(20)
        header.set_margin_top(15)
        header.set_margin_bottom(15)
        
        # Icono y título
        hbox_title = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        # Icono
        icon = Gtk.Image.new_from_icon_name("applications-system", Gtk.IconSize.DIALOG)
        hbox_title.pack_start(icon, False, False, 0)
        
        # Título y subtítulo
        vbox_title = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        
        title_label = Gtk.Label()
        title_label.set_markup("<span size='x-large' weight='bold'>LAMP Manager</span>")
        title_label.set_halign(Gtk.Align.START)
        title_label.get_style_context().add_class("header-title")
        vbox_title.pack_start(title_label, False, False, 0)
        
        subtitle_label = Gtk.Label()
        subtitle_label.set_markup("<span size='small'>Gestión de Stack Apache, MySQL y PHP</span>")
        subtitle_label.set_halign(Gtk.Align.START)
        subtitle_label.get_style_context().add_class("dim-label")
        vbox_title.pack_start(subtitle_label, False, False, 0)
        
        hbox_title.pack_start(vbox_title, False, False, 0)
        header.pack_start(hbox_title, True, True, 0)
        
        # Botón de actualizar
        refresh_btn = Gtk.Button.new_from_icon_name("view-refresh", Gtk.IconSize.BUTTON)
        refresh_btn.set_tooltip_text("Actualizar estado")
        refresh_btn.connect("clicked", self._on_refresh_clicked)
        header.pack_start(refresh_btn, False, False, 0)
        
        return header
    
    def _create_warning_banner(self) -> Gtk.Box:
        """Crea un banner de advertencia para systemctl no disponible."""
        banner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        banner.get_style_context().add_class("warning-box")
        banner.set_margin_start(20)
        banner.set_margin_end(20)
        banner.set_margin_bottom(10)
        
        icon = Gtk.Image.new_from_icon_name("dialog-warning", Gtk.IconSize.BUTTON)
        banner.pack_start(icon, False, False, 0)
        
        vbox_msg = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        
        # Mensaje principal
        label = Gtk.Label()
        method = self.service_manager.method
        if method:
            label.set_markup(
                f"<b>Modo de compatibilidad:</b> Usando <tt>{method}</tt> en lugar de systemctl. "
                f"Funcionalidad completa disponible."
            )
        else:
            label.set_markup(
                "<b>Funcionalidad limitada:</b> No se encontró systemctl, service ni invoke-rc.d. "
                "La gestión de servicios no funcionará. "
            )
        label.set_line_wrap(True)
        label.set_halign(Gtk.Align.START)
        vbox_msg.pack_start(label, False, False, 0)
        
        # Sugerencia si está en Flatpak
        if not method:
            hint_label = Gtk.Label()
            hint_label.set_markup(
                "<small>💡 <i>Ejecuta desde terminal del sistema (fuera de Flatpak/sandbox) para gestión completa</i></small>"
            )
            hint_label.set_line_wrap(True)
            hint_label.set_halign(Gtk.Align.START)
            hint_label.get_style_context().add_class("dim-label")
            vbox_msg.pack_start(hint_label, False, False, 0)
        
        banner.pack_start(vbox_msg, True, True, 0)
        
        return banner
    
    def _show_services_placeholder(self) -> None:
        """Muestra placeholder mientras se detectan servicios."""
        row = Gtk.ListBoxRow()
        label = Gtk.Label(label="Detectando servicios...")
        label.set_margin_top(20)
        label.set_margin_bottom(20)
        row.add(label)
        self.services_listbox.add(row)
        self.services_listbox.show_all()
    
    def _create_services_tab(self) -> None:
        """Crea el tab de servicios."""
        # Container
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(10)
        
        # Título
        title = Gtk.Label()
        title.set_markup("<span size='large' weight='bold'>Estado de Servicios</span>")
        title.set_halign(Gtk.Align.START)
        vbox.pack_start(title, False, False, 0)
        
        # Lista de servicios
        self.services_listbox = Gtk.ListBox()
        self.services_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.services_listbox)
        vbox.pack_start(scrolled, True, True, 0)
        
        # Mensaje inicial
        self._show_services_placeholder()
        
        # Agregar tab
        label = Gtk.Label(label="Servicios")
        self.notebook.append_page(vbox, label)
    
    def _create_vhosts_tab(self) -> None:
        """Crea el tab de hosts virtuales."""
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(10)
        
        # Header con botón de agregar
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        title = Gtk.Label()
        title.set_markup("<span size='large' weight='bold'>Hosts Virtuales</span>")
        title.set_halign(Gtk.Align.START)
        hbox.pack_start(title, True, True, 0)
        
        add_btn = Gtk.Button.new_from_icon_name("list-add", Gtk.IconSize.BUTTON)
        add_btn.set_label("Nuevo VHost")
        add_btn.set_always_show_image(True)
        add_btn.connect("clicked", self._on_add_vhost_clicked)
        hbox.pack_start(add_btn, False, False, 0)
        
        # Botón para abrir raíz del servidor
        www_btn = Gtk.Button.new_from_icon_name("folder", Gtk.IconSize.BUTTON)
        www_btn.set_label("Abrir /var/www")
        www_btn.set_always_show_image(True)
        www_btn.set_tooltip_text("Abrir directorio raíz del servidor Apache")
        www_btn.connect("clicked", self._on_open_www_clicked)
        hbox.pack_start(www_btn, False, False, 0)
        
        vbox.pack_start(hbox, False, False, 0)
        
        # Lista de vhosts
        self.vhosts_listbox = Gtk.ListBox()
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.vhosts_listbox)
        vbox.pack_start(scrolled, True, True, 0)
        
        label = Gtk.Label(label="Hosts Virtuales")
        self.notebook.append_page(vbox, label)
    
    def _create_php_tab(self) -> None:
        """Crea el tab de PHP."""
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(10)
        
        # Header
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        title = Gtk.Label()
        title.set_markup("<span size='large' weight='bold'>Gestión de PHP</span>")
        title.set_halign(Gtk.Align.START)
        hbox.pack_start(title, True, True, 0)
        
        vbox.pack_start(hbox, False, False, 0)
        
        # Frame de versiones disponibles
        versions_frame = Gtk.Frame(label="Versiones de PHP Soportadas")
        versions_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        versions_box.set_margin_start(10)
        versions_box.set_margin_end(10)
        versions_box.set_margin_top(10)
        versions_box.set_margin_bottom(10)
        
        # Lista de versiones PHP soportadas (últimas 4 versiones)
        php_versions = [
            {'version': '8.3', 'description': 'PHP 8.3 - Última versión estable (Recomendada)', 'recommended': True},
            {'version': '8.2', 'description': 'PHP 8.2 - Versión LTS con soporte extendido', 'recommended': False},
            {'version': '8.1', 'description': 'PHP 8.1 - Versión estable', 'recommended': False},
            {'version': '8.0', 'description': 'PHP 8.0 - Compatibilidad legacy', 'recommended': False},
        ]
        
        self.php_version_radios = []
        first_radio = None
        
        for php_ver in php_versions:
            radio_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            
            if first_radio is None:
                radio = Gtk.RadioButton.new_with_label_from_widget(None, f"PHP {php_ver['version']}")
                first_radio = radio
            else:
                radio = Gtk.RadioButton.new_with_label_from_widget(first_radio, f"PHP {php_ver['version']}")
            
            radio.set_name(php_ver['version'])
            self.php_version_radios.append(radio)
            radio_box.pack_start(radio, False, False, 0)
            
            desc_label = Gtk.Label()
            desc_label.set_markup(f"<small>{php_ver['description']}</small>")
            desc_label.set_halign(Gtk.Align.START)
            desc_label.get_style_context().add_class("dim-label")
            radio_box.pack_start(desc_label, True, True, 0)
            
            if php_ver['recommended']:
                badge = Gtk.Label()
                badge.set_markup("<span foreground='#27ae60' weight='bold' size='small'>RECOMENDADA</span>")
                radio_box.pack_start(badge, False, False, 0)
            
            versions_box.pack_start(radio_box, False, False, 0)
        
        install_php_btn = Gtk.Button(label="Instalar Versión Seleccionada")
        install_php_btn.get_style_context().add_class("suggested-action")
        install_php_btn.connect("clicked", self._on_install_php_version_clicked)
        versions_box.pack_start(install_php_btn, False, False, 10)
        
        versions_frame.add(versions_box)
        vbox.pack_start(versions_frame, False, False, 0)
        
        # Lista de versiones PHP instaladas
        installed_label = Gtk.Label()
        installed_label.set_markup("<b>Versiones Instaladas</b>")
        installed_label.set_halign(Gtk.Align.START)
        vbox.pack_start(installed_label, False, False, 5)
        
        self.php_listbox = Gtk.ListBox()
        self.php_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.php_listbox)
        vbox.pack_start(scrolled, True, True, 0)
        
        label = Gtk.Label(label="PHP")
        self.notebook.append_page(vbox, label)
    
    def _create_stack_tab(self) -> None:
        """Crea el tab del stack."""
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(10)
        
        # Header
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        title = Gtk.Label()
        title.set_markup("<span size='large' weight='bold'>Componentes del Stack</span>")
        title.set_halign(Gtk.Align.START)
        hbox.pack_start(title, True, True, 0)
        
        install_btn = Gtk.Button.new_from_icon_name("list-add", Gtk.IconSize.BUTTON)
        install_btn.set_label("Instalar Componentes")
        install_btn.set_always_show_image(True)
        install_btn.get_style_context().add_class("suggested-action")
        install_btn.connect("clicked", self._on_install_stack_clicked)
        hbox.pack_start(install_btn, False, False, 0)
        
        vbox.pack_start(hbox, False, False, 0)
        
        # Filtros y ordenamiento
        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        filter_box.set_margin_start(10)
        filter_box.set_margin_end(10)
        filter_box.set_margin_top(5)
        
        # Filtro por categoría
        cat_label = Gtk.Label(label="Categoría:")
        filter_box.pack_start(cat_label, False, False, 0)
        
        self.category_combo = Gtk.ComboBoxText()
        self.category_combo.append("all", "Todas")
        self.category_combo.append("servidores", "Servidores")
        self.category_combo.append("lenguajes", "Lenguajes")
        self.category_combo.append("dependencias", "Dependencias")
        self.category_combo.append("versionado", "Versionado")
        self.category_combo.append("cache", "Caché")
        self.category_combo.append("desarrollo", "Desarrollo")
        self.category_combo.append("testing", "Testing")
        self.category_combo.append("cms", "CMS")
        self.category_combo.set_active(0)
        self.category_combo.connect("changed", self._on_filter_changed)
        filter_box.pack_start(self.category_combo, False, False, 0)
        
        # Ordenar por estado
        sort_label = Gtk.Label(label="Ordenar:")
        filter_box.pack_start(sort_label, False, False, 20)
        
        self.sort_combo = Gtk.ComboBoxText()
        self.sort_combo.append("name", "Nombre")
        self.sort_combo.append("status", "Estado")
        self.sort_combo.append("category", "Categoría")
        self.sort_combo.set_active(0)
        self.sort_combo.connect("changed", self._on_filter_changed)
        filter_box.pack_start(self.sort_combo, False, False, 0)
        
        vbox.pack_start(filter_box, False, False, 0)
        
        # Contenedor con scroll para las categorías
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        self.stack_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.stack_container.set_margin_start(15)
        self.stack_container.set_margin_end(15)
        self.stack_container.set_margin_top(15)
        self.stack_container.set_margin_bottom(15)
        
        scrolled.add(self.stack_container)
        vbox.pack_start(scrolled, True, True, 0)
        
        label = Gtk.Label(label="Stack")
        self.notebook.append_page(vbox, label)
    
    def _create_config_tab(self) -> None:
        """Crea el tab de configuración."""
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(10)
        
        title = Gtk.Label()
        title.set_markup("<span size='large' weight='bold'>Configuración</span>")
        title.set_halign(Gtk.Align.START)
        vbox.pack_start(title, False, False, 0)
        
        # Estado del sistema
        info_frame = Gtk.Frame(label="Estado del Sistema")
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        info_box.set_margin_start(10)
        info_box.set_margin_end(10)
        info_box.set_margin_top(10)
        info_box.set_margin_bottom(10)
        
        # Gestor de servicios
        service_mgr_label = Gtk.Label(xalign=0)
        method = self.service_manager.method
        if method == 'systemctl':
            service_mgr_label.set_markup(
                f"✓ <b>Gestor de servicios:</b> systemctl <span foreground='#27ae60'>(moderno)</span>\n"
                f"   <small><tt>{self.service_manager.systemctl}</tt></small>"
            )
        elif method == 'service':
            service_mgr_label.set_markup(
                f"✓ <b>Gestor de servicios:</b> service <span foreground='#f39c12'>(compatible)</span>\n"
                f"   <small><tt>{self.service_manager.service_cmd}</tt></small>"
            )
        elif method == 'invoke-rc.d':
            service_mgr_label.set_markup(
                f"✓ <b>Gestor de servicios:</b> invoke-rc.d <span foreground='#f39c12'>(Debian/Ubuntu)</span>\n"
                f"   <small><tt>{self.service_manager.invoke_rc}</tt></small>"
            )
        else:
            service_mgr_label.set_markup(
                "✗ <b>Gestor de servicios:</b> <span foreground='#e74c3c'>No disponible</span>\n"
                "   <small>Ejecuta desde terminal del sistema para gestión completa</small>"
            )
        info_box.pack_start(service_mgr_label, False, False, 0)
        
        # Separador
        sep1 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        info_box.pack_start(sep1, False, False, 5)
        
        # pkexec
        pkexec_label = Gtk.Label(xalign=0)
        pkexec_path = shutil.which('pkexec')
        if pkexec_path:
            pkexec_label.set_markup(
                f"✓ <b>Elevación de privilegios:</b> pkexec disponible\n"
                f"   <small><tt>{pkexec_path}</tt></small>"
            )
        else:
            pkexec_label.set_markup(
                "✗ <b>Elevación de privilegios:</b> <span foreground='#e74c3c'>pkexec no disponible</span>\n"
                "   <small>Instala policykit-1 para gestión de servicios</small>"
            )
        info_box.pack_start(pkexec_label, False, False, 0)
        
        info_frame.add(info_box)
        vbox.pack_start(info_frame, False, False, 10)
        
        # Opciones de configuración
        config_frame = Gtk.Frame(label="Configuración")
        grid = Gtk.Grid()
        grid.set_column_spacing(15)
        grid.set_row_spacing(10)
        grid.set_margin_start(10)
        grid.set_margin_end(10)
        grid.set_margin_top(10)
        grid.set_margin_bottom(10)
        
        # Backups automáticos
        backup_label = Gtk.Label(label="Backups automáticos:", xalign=0)
        backup_label.set_hexpand(False)
        self.backup_switch = Gtk.Switch()
        self.backup_switch.set_halign(Gtk.Align.START)
        backup_enabled = self.db.get_config('backup_enabled') == '1'
        self.backup_switch.set_active(backup_enabled)
        self.backup_switch.connect("notify::active", self._on_backup_toggled)
        grid.attach(backup_label, 0, 0, 1, 1)
        grid.attach(self.backup_switch, 1, 0, 1, 1)
        
        # Ruta de backups
        backup_path_label = Gtk.Label(label="Directorio de backups:", xalign=0)
        backup_path_label.set_hexpand(False)
        self.backup_path_entry = Gtk.Entry()
        self.backup_path_entry.set_hexpand(True)
        self.backup_path_entry.set_width_chars(30)
        backup_path = self.db.get_config('backup_path') or 'backups/'
        self.backup_path_entry.set_text(backup_path)
        grid.attach(backup_path_label, 0, 1, 1, 1)
        grid.attach(self.backup_path_entry, 1, 1, 1, 1)
        
        config_frame.add(grid)
        vbox.pack_start(config_frame, False, False, 0)
        
        # Botón de guardar configuración
        save_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        save_btn = Gtk.Button(label="Guardar Configuración")
        save_btn.set_size_request(200, -1)
        save_btn.connect("clicked", self._on_save_config_clicked)
        save_btn_box.pack_start(save_btn, False, False, 0)
        vbox.pack_start(save_btn_box, False, False, 10)
        
        label = Gtk.Label(label="Configuración")
        self.notebook.append_page(vbox, label)
    
    def _detect_stack(self) -> bool:
        """Detecta el stack instalado."""
        try:
            self._update_statusbar("Detectando componentes del stack...")
            
            # Detectar componentes
            components = self.stack_detector.detect_all()
            self.installed_components = components
            
            # Actualizar la base de datos
            for name, component in components.items():
                try:
                    self.db.execute("""
                        UPDATE stack_components 
                        SET installed = ?, version = ?, last_check = CURRENT_TIMESTAMP
                        WHERE name = ?
                    """, (int(component.installed), component.version, name))
                except Exception as db_err:
                    logger.error(f"Error actualizando BD para {name}: {db_err}")
            
            # Actualizar UI
            self._update_stack_ui(components)
            self._update_php_ui()
            self._update_services_status()
            
            self._update_statusbar("Detección completada")
            
        except Exception as e:
            logger.error(f"Error detectando stack: {e}", exc_info=True)
            self._update_statusbar(f"Error: {str(e)}")
            self._show_error("Error detectando stack", str(e))
        
        return False  # No repetir
    
    def _update_services_status(self) -> bool:
        """Actualiza el estado de los servicios."""
        try:
            # Limpiar lista
            try:
                for child in self.services_listbox.get_children():
                    self.services_listbox.remove(child)
            except Exception as e:
                logger.error(f"Error limpiando lista de servicios: {e}")
            
            # Si no hay componentes instalados, mostrar mensaje
            if not self.installed_components or not any(c.installed for c in self.installed_components.values()):
                row = Gtk.ListBoxRow()
                vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
                vbox.set_margin_top(40)
                vbox.set_margin_bottom(40)
                
                icon = Gtk.Image.new_from_icon_name("dialog-information-symbolic", Gtk.IconSize.DIALOG)
                vbox.pack_start(icon, False, False, 0)
                
                label = Gtk.Label(label="No hay componentes del stack LAMP instalados")
                label.set_margin_top(10)
                vbox.pack_start(label, False, False, 0)
                
                hint = Gtk.Label()
                hint.set_markup("<small>Ve a la pestaña <b>Stack</b> para instalar componentes</small>")
                vbox.pack_start(hint, False, False, 0)
                
                row.add(vbox)
                self.services_listbox.add(row)
                self.services_listbox.show_all()
                return True
            
            # Obtener solo servicios de componentes instalados
            statuses = self.service_manager.get_all_status(self.installed_components)
            
            if not statuses:
                # No hay servicios disponibles (sin systemctl)
                row = Gtk.ListBoxRow()
                label = Gtk.Label(label="Gestión de servicios no disponible (systemctl no encontrado)")
                label.set_margin_top(20)
                label.set_margin_bottom(20)
                row.add(label)
                self.services_listbox.add(row)
            else:
                for status in statuses:
                    row = self._create_service_row(status)
                    self.services_listbox.add(row)
            
            self.services_listbox.show_all()
            
        except Exception as e:
            logger.error(f"Error actualizando servicios: {e}")
        
        return True  # Continuar ejecutando
    
    def _create_service_row(self, status) -> Gtk.ListBoxRow:
        """Crea una fila de servicio."""
        row = Gtk.ListBoxRow()
        row.get_style_context().add_class("service-row")
        
        # Añadir clase según estado
        if status.running:
            row.get_style_context().add_class("active")
        else:
            row.get_style_context().add_class("inactive")
        
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        hbox.set_margin_start(15)
        hbox.set_margin_end(15)
        hbox.set_margin_top(12)
        hbox.set_margin_bottom(12)
        
        # Indicador de estado con icono más grande
        status_icon = Gtk.Image()
        if status.running:
            status_icon.set_from_icon_name("emblem-default", Gtk.IconSize.LARGE_TOOLBAR)
        else:
            status_icon.set_from_icon_name("process-stop", Gtk.IconSize.LARGE_TOOLBAR)
        hbox.pack_start(status_icon, False, False, 0)
        
        # Información del servicio
        vbox_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        
        # Nombre del servicio
        name_label = Gtk.Label()
        name_label.set_markup(f"<span size='large' weight='bold'>{status.name}</span>")
        name_label.set_halign(Gtk.Align.START)
        vbox_info.pack_start(name_label, False, False, 0)
        
        # Estado y info adicional
        info_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        # Badge de estado
        status_label = Gtk.Label()
        status_label.get_style_context().add_class("status-badge")
        if status.running:
            status_label.set_markup("<span>● Activo</span>")
            status_label.get_style_context().add_class("status-active")
        else:
            status_label.set_markup("<span>○ Inactivo</span>")
            status_label.get_style_context().add_class("status-inactive")
        status_label.set_halign(Gtk.Align.START)
        info_hbox.pack_start(status_label, False, False, 0)
        
        # Info adicional si está ejecutándose
        if status.running and status.uptime:
            uptime_label = Gtk.Label()
            uptime_label.set_markup(f"<small>Uptime: {status.uptime}</small>")
            uptime_label.get_style_context().add_class("dim-label")
            info_hbox.pack_start(uptime_label, False, False, 0)
        
        vbox_info.pack_start(info_hbox, False, False, 0)
        hbox.pack_start(vbox_info, True, True, 0)
        
        # Botones de acción
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        if status.running:
            stop_btn = Gtk.Button.new_from_icon_name("media-playback-stop", Gtk.IconSize.BUTTON)
            stop_btn.set_label("Detener")
            stop_btn.set_always_show_image(True)
            stop_btn.set_tooltip_text(f"Detener servicio {status.name}")
            stop_btn.get_style_context().add_class("destructive-action")
            stop_btn.connect("clicked", self._on_stop_service, status.name)
            btn_box.pack_start(stop_btn, False, False, 0)
            
            restart_btn = Gtk.Button.new_from_icon_name("view-refresh", Gtk.IconSize.BUTTON)
            restart_btn.set_label("Reiniciar")
            restart_btn.set_always_show_image(True)
            restart_btn.set_tooltip_text(f"Reiniciar servicio {status.name}")
            restart_btn.connect("clicked", self._on_restart_service, status.name)
            btn_box.pack_start(restart_btn, False, False, 0)
        else:
            start_btn = Gtk.Button.new_from_icon_name("media-playback-start", Gtk.IconSize.BUTTON)
            start_btn.set_label("Iniciar")
            start_btn.set_always_show_image(True)
            start_btn.set_tooltip_text(f"Iniciar servicio {status.name}")
            start_btn.get_style_context().add_class("suggested-action")
            start_btn.connect("clicked", self._on_start_service, status.name)
            btn_box.pack_start(start_btn, False, False, 0)
        
        hbox.pack_start(btn_box, False, False, 0)
        
        row.add(hbox)
        return row
    
    def _on_filter_changed(self, widget) -> None:
        """Callback cuando cambian los filtros."""
        self._update_stack_ui(self.installed_components)
    
    def _update_stack_ui(self, components: dict) -> None:
        """Actualiza la UI del stack con agrupación por categorías."""
        # Limpiar contenedor
        for child in self.stack_container.get_children():
            self.stack_container.remove(child)
        
        if not components:
            no_data_label = Gtk.Label()
            no_data_label.set_markup("<span size='large'>No hay componentes instalados</span>")
            no_data_label.set_margin_top(50)
            no_data_label.set_margin_bottom(50)
            self.stack_container.pack_start(no_data_label, True, False, 0)
            self.stack_container.show_all()
            return
        
        # Obtener filtros
        selected_category = self.category_combo.get_active_id()
        sort_by = self.sort_combo.get_active_id()
        
        # Agrupar componentes por categoría
        from core.stack_installer import StackInstaller
        categories = {}
        category_names = {
            'servidores': 'Servidores',
            'lenguajes': 'Lenguajes',
            'dependencias': 'Gestión de Dependencias',
            'versionado': 'Control de Versiones',
            'cache': 'Caché y Rendimiento',
            'desarrollo': 'Desarrollo y Debugging',
            'testing': 'Testing',
            'cms': 'CMS y Frameworks'
        }
        
        for name, component in components.items():
            comp_info = StackInstaller.COMPONENTS.get(name, {})
            category = comp_info.get('category', 'otros')
            
            # Aplicar filtro de categoría
            if selected_category != 'all' and category != selected_category:
                continue
            
            if category not in categories:
                categories[category] = []
            categories[category].append((name, component, comp_info))
        
        # Ordenar componentes según el criterio
        for category in categories:
            if sort_by == 'name':
                categories[category].sort(key=lambda x: x[1].display_name)
            elif sort_by == 'status':
                categories[category].sort(key=lambda x: (not x[1].installed, x[1].display_name))
            elif sort_by == 'category':
                pass  # Ya están agrupados por categoría
        
        # Ordenar categorías
        sorted_categories = sorted(categories.items(), key=lambda x: x[0])
        
        # Crear secciones por categoría
        for category, items in sorted_categories:
            if not items:
                continue
            
            # Frame de categoría
            frame = Gtk.Frame()
            frame.get_style_context().add_class("card")
            
            vbox_cat = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            vbox_cat.set_margin_start(15)
            vbox_cat.set_margin_end(15)
            vbox_cat.set_margin_top(12)
            vbox_cat.set_margin_bottom(12)
            
            # Título de categoría
            cat_title = Gtk.Label()
            cat_title.set_markup(f"<span size='medium' weight='bold'>{category_names.get(category, category.title())}</span>")
            cat_title.set_halign(Gtk.Align.START)
            vbox_cat.pack_start(cat_title, False, False, 0)
            
            # Separador
            sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            vbox_cat.pack_start(sep, False, False, 5)
            
            # Grid de componentes de esta categoría
            grid = Gtk.Grid()
            grid.set_column_spacing(15)
            grid.set_row_spacing(8)
            grid.set_margin_top(5)
            
            row = 0
            for name, component, comp_info in items:
                # Columna 0: Nombre del componente
                name_label = Gtk.Label()
                name_label.set_markup(f"<b>{component.display_name}</b>")
                name_label.set_halign(Gtk.Align.START)
                name_label.set_hexpand(True)
                grid.attach(name_label, 0, row, 1, 1)
                
                # Columna 1: Estado
                status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
                status_icon = Gtk.Image()
                if component.installed:
                    status_icon.set_from_icon_name("emblem-default", Gtk.IconSize.BUTTON)
                    status_label = Gtk.Label()
                    status_label.set_markup("<span foreground='#10b981'>● Instalado</span>")
                else:
                    status_icon.set_from_icon_name("dialog-warning", Gtk.IconSize.BUTTON)
                    status_label = Gtk.Label()
                    status_label.set_markup("<span foreground='#f59e0b'>○ No instalado</span>")
                status_box.pack_start(status_icon, False, False, 0)
                status_box.pack_start(status_label, False, False, 0)
                grid.attach(status_box, 1, row, 1, 1)
                
                # Columna 2: Versión
                version_label = Gtk.Label(label=f"v{component.version}" if component.version else "-")
                version_label.set_halign(Gtk.Align.CENTER)
                version_label.get_style_context().add_class("dim-label")
                grid.attach(version_label, 2, row, 1, 1)
                
                # Columna 3: Servicio
                service_name = comp_info.get('service', '')
                service_label = Gtk.Label(label=service_name if service_name else "-")
                service_label.set_halign(Gtk.Align.CENTER)
                service_label.get_style_context().add_class("dim-label")
                grid.attach(service_label, 3, row, 1, 1)
                
                # Columna 4: Acciones
                action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
                action_box.set_halign(Gtk.Align.END)
                
                if component.installed:
                    uninstall_btn = Gtk.Button(label="Desinstalar")
                    uninstall_btn.get_style_context().add_class("destructive-action")
                    uninstall_btn.connect("clicked", self._on_uninstall_component, name)
                    action_box.pack_start(uninstall_btn, False, False, 0)
                else:
                    install_btn = Gtk.Button(label="Instalar")
                    install_btn.get_style_context().add_class("suggested-action")
                    install_btn.connect("clicked", self._on_install_single_component, name)
                    action_box.pack_start(install_btn, False, False, 0)
                
                grid.attach(action_box, 4, row, 1, 1)
                
                row += 1
            
            vbox_cat.pack_start(grid, False, False, 0)
            frame.add(vbox_cat)
            self.stack_container.pack_start(frame, False, False, 0)
        
        self.stack_container.show_all()
    
    def _get_service_name(self, component_name: str) -> str:
        """Obtiene el nombre del servicio para un componente."""
        service_map = {
            'apache2': 'apache2',
            'mysql': 'mysql',
            'php': 'php-fpm'
        }
        return service_map.get(component_name, '')
    
    def _update_php_ui(self) -> None:
        """Actualiza la UI de versiones PHP."""
        # Limpiar lista
        for child in self.php_listbox.get_children():
            self.php_listbox.remove(child)
        
        php_versions = self.stack_detector.php_versions
        
        if not php_versions:
            row = Gtk.ListBoxRow()
            label = Gtk.Label(label="No se detectaron versiones PHP instaladas")
            label.set_margin_top(20)
            label.set_margin_bottom(20)
            row.add(label)
            self.php_listbox.add(row)
        else:
            for php in php_versions:
                row = Gtk.ListBoxRow()
                hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                hbox.set_margin_start(10)
                hbox.set_margin_end(10)
                hbox.set_margin_top(10)
                hbox.set_margin_bottom(10)
                
                # Icono
                icon = Gtk.Image()
                if php.is_active:
                    icon.set_from_icon_name("emblem-default-symbolic", Gtk.IconSize.BUTTON)
                else:
                    icon.set_from_icon_name("emblem-system-symbolic", Gtk.IconSize.BUTTON)
                hbox.pack_start(icon, False, False, 0)
                
                # Versión
                label = Gtk.Label()
                markup = f"<b>PHP {php.version}</b>"
                if php.is_active:
                    markup += " (activa)"
                label.set_markup(markup)
                label.set_halign(Gtk.Align.START)
                hbox.pack_start(label, False, False, 0)
                
                # Ruta
                path_label = Gtk.Label()
                path_label.set_markup(f"<small>{php.path}</small>")
                hbox.pack_start(path_label, True, True, 0)
                
                row.add(hbox)
                self.php_listbox.add(row)
        
        self.php_listbox.show_all()
    
    def _update_statusbar(self, message: str) -> None:
        """Actualiza la barra de estado."""
        try:
            context_id = self.statusbar.get_context_id("main")
            self.statusbar.pop(context_id)
            self.statusbar.push(context_id, message)
        except Exception as e:
            logger.error(f"Error actualizando statusbar: {e}")
    
    def _show_error(self, title: str, message: str) -> None:
        """Muestra un diálogo de error."""
        try:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=title
            )
            dialog.format_secondary_text(message)
            dialog.run()
            dialog.destroy()
        except Exception as e:
            logger.error(f"Error mostrando diálogo: {e}")
    
    # Event handlers
    def _on_refresh_clicked(self, button) -> None:
        """Handler para el botón de actualizar."""
        try:
            self._detect_stack()
        except Exception as e:
            logger.error(f"Error al refrescar: {e}", exc_info=True)
            self._show_error("Error", f"No se pudo actualizar: {str(e)}")
    
    def _on_start_service(self, button, service_name: str) -> None:
        """Handler para iniciar servicio."""
        try:
            self._update_statusbar(f"Iniciando {service_name}...")
            success, message = self.service_manager.start_service(service_name)
            self._update_statusbar(message)
            if not success:
                self._show_error("Error iniciando servicio", message)
            self._update_services_status()
        except Exception as e:
            logger.error(f"Error iniciando servicio: {e}", exc_info=True)
            self._show_error("Error", str(e))
    
    def _on_stop_service(self, button, service_name: str) -> None:
        """Handler para detener servicio."""
        try:
            self._update_statusbar(f"Deteniendo {service_name}...")
            success, message = self.service_manager.stop_service(service_name)
            self._update_statusbar(message)
            if not success:
                self._show_error("Error deteniendo servicio", message)
            self._update_services_status()
        except Exception as e:
            logger.error(f"Error deteniendo servicio: {e}", exc_info=True)
            self._show_error("Error", str(e))
    
    def _on_restart_service(self, button, service_name: str) -> None:
        """Handler para reiniciar servicio."""
        try:
            self._update_statusbar(f"Reiniciando {service_name}...")
            success, message = self.service_manager.restart_service(service_name)
            self._update_statusbar(message)
            if not success:
                self._show_error("Error reiniciando servicio", message)
            self._update_services_status()
        except Exception as e:
            logger.error(f"Error reiniciando servicio: {e}", exc_info=True)
            self._show_error("Error", str(e))
    
    def _on_add_vhost_clicked(self, button) -> None:
        """Handler para agregar vhost."""
        # TODO: Implementar diálogo de crear vhost
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Crear Virtual Host"
        )
        dialog.format_secondary_text("Función en desarrollo")
        dialog.run()
        dialog.destroy()
    
    def _on_open_www_clicked(self, button) -> None:
        """Handler para abrir directorio raíz de Apache."""
        try:
            # Verificar directorios comunes de Apache
            www_paths = ['/var/www/html', '/var/www']
            www_path = None
            
            for path in www_paths:
                if os.path.exists(path):
                    www_path = path
                    break
            
            if www_path:
                # Usar xdg-open para abrir el directorio en el explorador de archivos
                subprocess.run(['xdg-open', www_path], check=False)
                self._update_statusbar(f"Abriendo {www_path}")
            else:
                self._show_error("Error", "No se encontró el directorio de Apache (/var/www)")
        except Exception as e:
            logger.error(f"Error abriendo directorio www: {e}", exc_info=True)
            self._show_error("Error", f"No se pudo abrir el directorio: {str(e)}")
    
    def _on_install_php_version_clicked(self, button) -> None:
        """Handler para instalar versión seleccionada de PHP."""
        try:
            # Obtener la versión seleccionada de los radio buttons
            selected_version = None
            for radio in self.php_version_radios:
                if radio.get_active():
                    selected_version = radio.get_label().split()[0]  # Extrae "8.3", "8.2", etc
                    break
            
            if not selected_version:
                self._show_error("Error", "Seleccione una versión de PHP")
                return
            
            # Confirmar instalación
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text=f"Instalar PHP {selected_version}"
            )
            dialog.format_secondary_text(
                f"¿Desea instalar PHP {selected_version} y sus módulos principales?\n"
                "Esto puede tardar varios minutos."
            )
            response = dialog.run()
            dialog.destroy()
            
            if response == Gtk.ResponseType.YES:
                # Usar el instalador con solo el componente PHP
                installer_dialog = InstallDialog(self, self.installed_components)
                installer_dialog.run()
                installer_dialog.destroy()
                
                # Actualizar estado
                self._detect_stack()
                self._update_statusbar(f"PHP {selected_version} instalado correctamente")
        except Exception as e:
            logger.error(f"Error instalando PHP: {e}", exc_info=True)
            self._show_error("Error", f"No se pudo instalar PHP: {str(e)}")
    
    def _on_install_single_component(self, button, component: str) -> None:
        """Handler para instalar un componente individual."""
        try:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text=f"Instalar {component}"
            )
            dialog.format_secondary_text(f"¿Desea instalar {component}?")
            response = dialog.run()
            dialog.destroy()
            
            if response == Gtk.ResponseType.YES:
                # Crear instalador con solo este componente
                installer_dialog = InstallDialog(self, self.installed_components)
                installer_dialog.run()
                installer_dialog.destroy()
                
                # Actualizar estado
                self._detect_stack()
                self._update_statusbar(f"{component} instalado correctamente")
        except Exception as e:
            logger.error(f"Error instalando {component}: {e}", exc_info=True)
            self._show_error("Error", f"No se pudo instalar {component}: {str(e)}")
    
    def _on_uninstall_component(self, button, component: str) -> None:
        """Handler para desinstalar un componente."""
        try:
            # Obtener nombre del componente
            comp_info = self.installed_components.get(component)
            if not comp_info:
                self._show_error("Error", f"Componente {component} no encontrado")
                return
            
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.YES_NO,
                text=f"Desinstalar {comp_info.display_name}"
            )
            dialog.format_secondary_text(
                f"¿Está seguro que desea desinstalar {comp_info.display_name}?\n"
                "Esta acción eliminará todos los paquetes asociados.\n\n"
                "El servicio será detenido antes de desinstalar."
            )
            response = dialog.run()
            dialog.destroy()
            
            if response == Gtk.ResponseType.YES:
                self._update_statusbar(f"Desinstalando {comp_info.display_name}...")
                
                # Desinstalar en thread separado para no bloquear UI
                def uninstall_thread():
                    try:
                        from core import StackInstaller
                        installer = StackInstaller()
                        success, msg = installer.uninstall_component(component)
                        
                        def update_ui():
                            if success:
                                self._update_statusbar(f"{comp_info.display_name} desinstalado correctamente")
                                # Re-detectar componentes
                                self._detect_stack()
                            else:
                                self._show_error("Error al desinstalar", msg)
                                self._update_statusbar("Error en desinstalación")
                            return False
                        
                        GLib.idle_add(update_ui)
                    except Exception as e:
                        logger.error(f"Error en thread de desinstalación: {e}", exc_info=True)
                        GLib.idle_add(self._show_error, "Error", str(e))
                
                thread = threading.Thread(target=uninstall_thread)
                thread.daemon = True
                thread.start()
        except Exception as e:
            logger.error(f"Error desinstalando {component}: {e}", exc_info=True)
            self._show_error("Error", f"No se pudo desinstalar {component}: {str(e)}")
    
    def _on_install_stack_clicked(self, button) -> None:
        """Handler para instalar stack."""
        try:
            dialog = InstallDialog(self, self.installed_components)
            response = dialog.run()
            
            if response == Gtk.ResponseType.OK:
                # Re-detectar componentes después de la instalación
                self._detect_stack()
                self._update_statusbar("Stack actualizado correctamente")
            
            dialog.destroy()
        except Exception as e:
            logger.error(f"Error en diálogo de instalación: {e}", exc_info=True)
            self._show_error("Error", f"No se pudo abrir el instalador: {str(e)}")
    
    def _on_backup_toggled(self, switch, gparam) -> None:
        """Handler para toggle de backups."""
        enabled = '1' if switch.get_active() else '0'
        self.db.set_config('backup_enabled', enabled)
    
    def _on_save_config_clicked(self, button) -> None:
        """Handler para guardar configuración."""
        backup_path = self.backup_path_entry.get_text()
        self.db.set_config('backup_path', backup_path)
        self._update_statusbar("Configuración guardada")
