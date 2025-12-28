"""
XLAMP Manager - Main Window
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
from pathlib import Path

from ..core import StackDetector, ServiceManager, VHostManager, BackupManager, PHPManager
from ..data import Database, VirtualHost, Config
from .install_dialog import InstallDialog
from .vhost_dialog import VHostDialog

logger = logging.getLogger(__name__)


class MainWindow(Gtk.Window):
    """Ventana principal de XLAMP Manager."""
    
    def __init__(self, db: Database):
        """
        Inicializa la ventana principal.
        
        Args:
            db: Instancia de la base de datos
        """
        super().__init__(title="XLAMP Manager")
        
        self.db = db
        self.stack_detector = StackDetector()
        self.service_manager = ServiceManager()
        self.vhost_manager = VHostManager(use_flatpak=os.path.exists('/.flatpak-info'))
        self.php_manager = PHPManager(use_flatpak=os.path.exists('/.flatpak-info'))
        
        # Inicializar BackupManager
        backup_path = Config.get_value('backup_path') or 'backups/'
        self.backup_manager = BackupManager(
            backup_dir=backup_path,
            use_flatpak=os.path.exists('/.flatpak-info')
        )
        
        self.installed_components = {}  # Componentes instalados
        self.systemctl_available = self.service_manager.systemctl is not None
        self.is_busy = False  # Flag para bloquear acciones durante operaciones
        
        # Estado de paginación de VHosts
        self.vhost_current_page = 1
        self.vhost_items_per_page = 10
        self.vhost_search_text = ""
        
        # Cargar estilos CSS
        self._load_styles()
        
        # Configuración de la ventana (optimizada para pantallas pequeñas)
        self.set_default_size(850, 500)
        self.set_border_width(0)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Configurar icono de la aplicación
        self._set_window_icon()
        
        # Permitir redimensionar
        self.set_resizable(True)
        # Tamaño mínimo para pantallas de 13"
        self.set_size_request(800, 450)
        
        # Crear interfaz
        self._create_ui()
        
        # Detectar stack al inicio
        GLib.idle_add(self._detect_stack)
        
        # Actualizar estado de servicios cada 5 segundos
        GLib.timeout_add_seconds(5, self._update_services_status)
        
        # Limpiar backups antiguos cada 24 horas si está habilitado
        GLib.timeout_add_seconds(86400, self._auto_cleanup_backups)
    
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
    
    def _set_window_icon(self) -> None:
        """Configura el icono de la ventana y la aplicación."""
        try:
            # Buscar el archivo icon.png en la raíz del proyecto
            current_dir = Path(__file__).resolve().parent
            project_root = current_dir.parent.parent
            icon_path = project_root / 'icon.png'
            
            if icon_path.exists():
                self.set_icon_from_file(str(icon_path))
                # También configurar como icono predeterminado para todos los diálogos
                Gtk.Window.set_default_icon_from_file(str(icon_path))
                logger.info(f"Icono de la aplicación cargado: {icon_path}")
            else:
                logger.warning(f"Icono no encontrado: {icon_path}")
        except Exception as e:
            logger.error(f"Error cargando icono de la aplicación: {e}")
    
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
        self.notebook.set_scrollable(True)  # Pestañas con scroll si hay muchas
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
        
        # Cargar datos iniciales
        self._load_vhosts()
    
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
        title_label.set_markup("<span size='x-large' weight='bold'>XLAMP Manager</span>")
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
        
        # Header con Título y Botones Globales
        hbox_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        # Título
        title = Gtk.Label()
        title.set_markup("<span size='large' weight='bold'>Estado de Servicios</span>")
        title.set_halign(Gtk.Align.START)
        hbox_header.pack_start(title, True, True, 0)
        
        # Botones Globales
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        self.btn_start_all = Gtk.Button()
        hbox_start = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        icon_start = Gtk.Image.new_from_icon_name("media-playback-start", Gtk.IconSize.BUTTON)
        hbox_start.pack_start(icon_start, False, False, 0)
        hbox_start.pack_start(Gtk.Label(label="Iniciar Todos"), False, False, 0)
        self.btn_start_all.add(hbox_start)
        self.btn_start_all.get_style_context().add_class("suggested-action")
        self.btn_start_all.connect("clicked", self._on_start_all_clicked)
        btn_box.pack_start(self.btn_start_all, False, False, 0)
        
        self.btn_stop_all = Gtk.Button()
        hbox_stop = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        icon_stop = Gtk.Image.new_from_icon_name("media-playback-stop", Gtk.IconSize.BUTTON)
        hbox_stop.pack_start(icon_stop, False, False, 0)
        hbox_stop.pack_start(Gtk.Label(label="Detener Todos"), False, False, 0)
        self.btn_stop_all.add(hbox_stop)
        self.btn_stop_all.get_style_context().add_class("destructive-action")
        self.btn_stop_all.connect("clicked", self._on_stop_all_clicked)
        btn_box.pack_start(self.btn_stop_all, False, False, 0)
        
        hbox_header.pack_start(btn_box, False, False, 0)
        vbox.pack_start(hbox_header, False, False, 0)
        
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

    def _get_all_service_names(self) -> list:
        """Obtiene la lista de nombres de servicios actuales."""
        services = []
        # Recorrer los hijos del listbox para obtener los nombres
        for row in self.services_listbox.get_children():
            # Asumimos que guardamos el nombre del servicio en el widget row o lo podemos deducir
            # Pero mejor usamos la lista que ya tenemos en memoria si es posible
            # O iteramos sobre los widgets ServiceRow si tienen un método get_service_name
            if hasattr(row, 'service_name'):
                services.append(row.service_name)
        
        # Si la lista está vacía (aún no se cargó), usamos los defaults
        if not services:
            services = ['apache2', 'mysql']
            # Intentar adivinar PHP
            import glob
            for php_bin in glob.glob('/usr/bin/php[0-9]*'):
                 version = php_bin.replace('/usr/bin/php', '')
                 if '.' in version:
                     services.append(f'php{version}-fpm')
        
        return services

    def _on_start_all_clicked(self, widget):
        """Manejador para iniciar todos los servicios."""
        services = self._get_all_service_names()
        if not services:
            return

        self._update_statusbar("Iniciando todos los servicios...")
        self.btn_start_all.set_sensitive(False)
        self.btn_stop_all.set_sensitive(False)
        
        def run_start_all():
            success, msg = self.service_manager.manage_all_services('start', services)
            GLib.idle_add(self._on_all_services_action_finished, success, msg)
            
        threading.Thread(target=run_start_all, daemon=True).start()

    def _on_stop_all_clicked(self, widget):
        """Manejador para detener todos los servicios."""
        services = self._get_all_service_names()
        if not services:
            return

        self._update_statusbar("Deteniendo todos los servicios...")
        self.btn_start_all.set_sensitive(False)
        self.btn_stop_all.set_sensitive(False)
        
        def run_stop_all():
            success, msg = self.service_manager.manage_all_services('stop', services)
            GLib.idle_add(self._on_all_services_action_finished, success, msg)
            
        threading.Thread(target=run_stop_all, daemon=True).start()

    def _on_all_services_action_finished(self, success, msg):
        """Callback al finalizar acción masiva."""
        self.btn_start_all.set_sensitive(True)
        self.btn_stop_all.set_sensitive(True)
        self._update_statusbar(msg)
        if success:
            self._update_services_status()
        else:
            self._show_error(msg)
    
    def _create_vhosts_tab(self) -> None:
        """Crea el tab de hosts virtuales."""
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(10)
        
        # Header con botón de agregar y búsqueda
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        title = Gtk.Label()
        title.set_markup("<span size='large' weight='bold'>Hosts Virtuales</span>")
        title.set_halign(Gtk.Align.START)
        hbox.pack_start(title, False, False, 0)
        
        # Buscador
        self.vhost_search_entry = Gtk.SearchEntry()
        self.vhost_search_entry.set_placeholder_text("Buscar host...")
        self.vhost_search_entry.set_width_chars(20)
        self.vhost_search_entry.connect("search-changed", self._on_vhost_search_changed)
        hbox.pack_end(self.vhost_search_entry, False, False, 0)
        
        add_btn = Gtk.Button.new_from_icon_name("list-add", Gtk.IconSize.BUTTON)
        add_btn.set_label("Nuevo")
        add_btn.set_always_show_image(True)
        add_btn.connect("clicked", self._on_add_vhost_clicked)
        hbox.pack_end(add_btn, False, False, 0)
        
        # Botón Eliminar Seleccionados
        self.delete_selected_btn = Gtk.Button.new_from_icon_name("user-trash", Gtk.IconSize.BUTTON)
        self.delete_selected_btn.set_label("Eliminar Seleccionados")
        self.delete_selected_btn.set_always_show_image(True)
        self.delete_selected_btn.get_style_context().add_class("destructive-action")
        self.delete_selected_btn.set_sensitive(False)
        self.delete_selected_btn.connect("clicked", self._on_delete_selected_vhosts_clicked)
        hbox.pack_end(self.delete_selected_btn, False, False, 0)
        
        # Botón para abrir raíz del servidor
        www_btn = Gtk.Button.new_from_icon_name("folder", Gtk.IconSize.BUTTON)
        www_btn.set_label("Abrir /var/www")
        www_btn.set_always_show_image(True)
        www_btn.set_tooltip_text("Abrir directorio raíz del servidor Apache")
        www_btn.connect("clicked", self._on_open_www_clicked)
        hbox.pack_end(www_btn, False, False, 0)
        
        vbox.pack_start(hbox, False, False, 0)
        
        # Lista de vhosts
        self.vhosts_listbox = Gtk.ListBox()
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.vhosts_listbox)
        vbox.pack_start(scrolled, True, True, 0)
        
        # Paginación
        pagination_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        pagination_box.set_halign(Gtk.Align.CENTER)
        pagination_box.set_margin_top(5)
        pagination_box.set_margin_bottom(5)
        
        self.vhost_prev_btn = Gtk.Button.new_from_icon_name("go-previous", Gtk.IconSize.BUTTON)
        self.vhost_prev_btn.connect("clicked", self._on_vhost_prev_page)
        self.vhost_prev_btn.set_sensitive(False)
        pagination_box.pack_start(self.vhost_prev_btn, False, False, 0)
        
        self.vhost_page_label = Gtk.Label(label="Página 1")
        pagination_box.pack_start(self.vhost_page_label, False, False, 10)
        
        self.vhost_next_btn = Gtk.Button.new_from_icon_name("go-next", Gtk.IconSize.BUTTON)
        self.vhost_next_btn.connect("clicked", self._on_vhost_next_page)
        self.vhost_next_btn.set_sensitive(False)
        pagination_box.pack_start(self.vhost_next_btn, False, False, 0)
        
        vbox.pack_start(pagination_box, False, False, 0)
        
        label = Gtk.Label(label="Hosts Virtuales")
        self.notebook.append_page(vbox, label)
    
    def _create_php_tab(self) -> None:
        """Crea el tab de PHP."""
        # Contenedor principal con scroll
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        
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
        
        php_scrolled = Gtk.ScrolledWindow()
        php_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        php_scrolled.set_min_content_height(150)  # Altura mínima para la lista
        php_scrolled.add(self.php_listbox)
        vbox.pack_start(php_scrolled, True, True, 0)
        
        # Agregar vbox al scrolled principal
        scrolled.add(vbox)
        
        label = Gtk.Label(label="PHP")
        self.notebook.append_page(scrolled, label)
    
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
        # Contenedor principal con scroll
        main_scrolled = Gtk.ScrolledWindow()
        main_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        
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
        backup_enabled = Config.get_value('backup_enabled') == '1'
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
        backup_path = Config.get_value('backup_path') or 'backups/'
        self.backup_path_entry.set_text(backup_path)
        grid.attach(backup_path_label, 0, 1, 1, 1)
        grid.attach(self.backup_path_entry, 1, 1, 1, 1)
        
        config_frame.add(grid)
        vbox.pack_start(config_frame, False, False, 0)
        
        # Sección de Backups
        backup_frame = Gtk.Frame(label="Gestión de Backups")
        backup_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        backup_box.set_margin_start(10)
        backup_box.set_margin_end(10)
        backup_box.set_margin_top(10)
        backup_box.set_margin_bottom(10)
        
        # Estadísticas de backups
        self.backup_stats_label = Gtk.Label(xalign=0)
        self.backup_stats_label.set_markup("<i>Cargando estadísticas...</i>")
        backup_box.pack_start(self.backup_stats_label, False, False, 0)
        
        # Botones de backup
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        backup_db_btn = Gtk.Button(label="Backup Base de Datos")
        backup_db_btn.connect("clicked", self._on_backup_database_clicked)
        btn_box.pack_start(backup_db_btn, False, False, 0)
        
        backup_config_btn = Gtk.Button(label="Backup Apache Config")
        backup_config_btn.connect("clicked", self._on_backup_apache_clicked)
        btn_box.pack_start(backup_config_btn, False, False, 0)
        
        cleanup_btn = Gtk.Button(label="Limpiar Antiguos")
        cleanup_btn.connect("clicked", self._on_cleanup_backups_clicked)
        btn_box.pack_start(cleanup_btn, False, False, 0)
        
        backup_box.pack_start(btn_box, False, False, 0)
        backup_frame.add(backup_box)
        vbox.pack_start(backup_frame, False, False, 10)
        
        # Actualizar estadísticas iniciales
        GLib.idle_add(self._update_backup_stats)
        
        # Botón de guardar configuración
        save_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        save_btn = Gtk.Button(label="Guardar Configuración")
        save_btn.set_size_request(200, -1)
        save_btn.connect("clicked", self._on_save_config_clicked)
        save_btn_box.pack_start(save_btn, False, False, 0)
        vbox.pack_start(save_btn_box, False, False, 10)
        
        # Agregar vbox al scroll principal
        main_scrolled.add(vbox)
        
        label = Gtk.Label(label="Configuración")
        self.notebook.append_page(main_scrolled, label)
    
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
            logger.info("Obteniendo estado de servicios...")
            statuses = self.service_manager.get_all_status(self.installed_components)
            logger.info(f"Servicios detectados: {len(statuses)}")
            
            if not statuses:
                # No hay servicios disponibles (sin systemctl)
                logger.warning("No se detectaron servicios")
                row = Gtk.ListBoxRow()
                label = Gtk.Label(label="Gestión de servicios no disponible (systemctl no encontrado)")
                label.set_margin_top(20)
                label.set_margin_bottom(20)
                row.add(label)
                self.services_listbox.add(row)
            else:
                for status in statuses:
                    logger.info(f"Agregando servicio: {status.name}")
                    row = self._create_service_row(status)
                    self.services_listbox.add(row)
            
            self.services_listbox.show_all()
            
        except Exception as e:
            logger.error(f"Error actualizando servicios: {e}")
        
        return True  # Continuar ejecutando
    
    def _create_service_row(self, status) -> Gtk.ListBoxRow:
        """Crea una fila de servicio."""
        row = Gtk.ListBoxRow()
        row.service_name = status.name  # Guardar nombre para acciones masivas
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
        
        # Solo filtrar el paquete base de PHP (se gestiona en la pestaña PHP)
        # Las herramientas relacionadas (xdebug, phpmyadmin, etc.) se mantienen en Stack
        for name, component in components.items():
            # Filtrar solo PHP base
            if name == 'php':
                continue
            
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
        
        # Obtener versiones instaladas con PHPManager
        installed_versions = self.php_manager.detect_installed_versions()
        
        if not installed_versions:
            row = Gtk.ListBoxRow()
            row.set_selectable(False)
            label = Gtk.Label(label="No se detectaron versiones PHP instaladas\nInstale una versión usando los botones arriba")
            label.set_margin_top(20)
            label.set_margin_bottom(20)
            label.set_justify(Gtk.Justification.CENTER)
            row.add(label)
            self.php_listbox.add(row)
        else:
            for version, info in installed_versions.items():
                row = Gtk.ListBoxRow()
                row.set_selectable(False)
                
                hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                hbox.set_margin_start(10)
                hbox.set_margin_end(10)
                hbox.set_margin_top(10)
                hbox.set_margin_bottom(10)
                
                # Icono de estado
                icon = Gtk.Image()
                if info['is_default']:
                    icon.set_from_icon_name("emblem-default", Gtk.IconSize.BUTTON)
                    icon.set_tooltip_text("Versión predeterminada del sistema")
                else:
                    icon.set_from_icon_name("emblem-system", Gtk.IconSize.BUTTON)
                hbox.pack_start(icon, False, False, 0)
                
                # Info versión
                vbox_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                
                version_label = Gtk.Label()
                markup = f"<b>PHP {version}</b>"
                if info['is_default']:
                    markup += " <span foreground='#27ae60'>(predeterminada)</span>"
                version_label.set_markup(markup)
                version_label.set_halign(Gtk.Align.START)
                vbox_info.pack_start(version_label, False, False, 0)
                
                # Información adicional
                mode_text = "FPM" if info['fpm_installed'] else "mod_php"
                status_text = "corriendo" if info.get('fpm_running') else "detenido"
                status_color = "#27ae60" if info.get('fpm_running') else "#e74c3c"
                
                info_label = Gtk.Label()
                info_label.set_markup(
                    f"<small>Modo: {mode_text} • "
                    f"Estado: <span foreground='{status_color}'>{status_text}</span> • "
                    f"Módulos: {len(info.get('modules', []))}</small>"
                )
                info_label.set_halign(Gtk.Align.START)
                vbox_info.pack_start(info_label, False, False, 0)
                
                hbox.pack_start(vbox_info, True, True, 0)
                
                # Botones de acción
                btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
                
                if not info['is_default']:
                    default_btn = Gtk.Button(label="Predeterminada")
                    default_btn.set_tooltip_text("Establecer como versión predeterminada")
                    default_btn.connect("clicked", self._on_set_default_php, version)
                    btn_box.pack_start(default_btn, False, False, 0)
                
                uninstall_btn = Gtk.Button(label="Desinstalar")
                uninstall_btn.get_style_context().add_class("destructive-action")
                uninstall_btn.connect("clicked", self._on_uninstall_php_version, version)
                btn_box.pack_start(uninstall_btn, False, False, 0)
                
                hbox.pack_start(btn_box, False, False, 0)
                
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
    
    def _show_info(self, title: str, message: str) -> None:
        """Muestra un diálogo informativo."""
        try:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=title
            )
            dialog.format_secondary_text(message)
            dialog.run()
            dialog.destroy()
        except Exception as e:
            logger.error(f"Error mostrando diálogo: {e}")
    
    def _show_warning(self, title: str, message: str) -> None:
        """Muestra un diálogo de advertencia."""
        try:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.WARNING,
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
        if self.is_busy:
            self._show_error("Operación en curso", "Espere a que termine la operación actual")
            return
        
        try:
            # Confirmar reinicio
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text=f"Reiniciar servicio {service_name}"
            )
            dialog.format_secondary_text(
                f"¿Está seguro que desea reiniciar el servicio {service_name}?\n"
                "El servicio se detendrá y volverá a iniciar."
            )
            response = dialog.run()
            dialog.destroy()
            
            if response != Gtk.ResponseType.YES:
                return
            
            # Bloquear UI y mostrar progreso
            self.is_busy = True
            self.set_sensitive(False)
            self._update_statusbar(f"Reiniciando {service_name}...")
            
            # Reiniciar en thread separado
            def restart_thread():
                try:
                    success, message = self.service_manager.restart_service(service_name)
                    GLib.idle_add(self._on_restart_complete, success, message, service_name)
                except Exception as e:
                    logger.error(f"Error en thread de reinicio: {e}", exc_info=True)
                    GLib.idle_add(self._on_restart_complete, False, str(e), service_name)
            
            thread = threading.Thread(target=restart_thread, daemon=True)
            thread.start()
            
        except Exception as e:
            logger.error(f"Error reiniciando servicio: {e}", exc_info=True)
            self.is_busy = False
            self.set_sensitive(True)
            self._show_error("Error", str(e))
    
    def _on_restart_complete(self, success: bool, message: str, service_name: str) -> bool:
        """Callback cuando termina el reinicio del servicio."""
        self.is_busy = False
        self.set_sensitive(True)
        
        if success:
            self._update_statusbar(f"✓ {message}")
            self._show_info("Éxito", message)
        else:
            self._update_statusbar(f"✗ Error: {message}")
            self._show_error("Error reiniciando servicio", message)
        
        # Actualizar estado de servicios
        self._update_services_status()
        return False
    
    def _on_add_vhost_clicked(self, button) -> None:
        """Handler para agregar vhost."""
        if self.is_busy:
            self._show_error("Operación en curso", "Espere a que termine la operación actual")
            return
        
        dialog = VHostDialog(self)
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            # Validar datos
            valid, error_msg = dialog.validate()
            if not valid:
                dialog.destroy()
                self._show_error("Datos inválidos", error_msg)
                return
            
            # Obtener datos
            vhost = dialog.get_vhost_data()
            dialog.destroy()
            
            # Crear host virtual
            self.is_busy = True
            self.set_sensitive(False)
            self._update_statusbar("Creando host virtual...")
            
            def create_thread():
                try:
                    success, message = self.vhost_manager.create_vhost(vhost, vhost.document_root)
                    
                    GLib.idle_add(self._on_vhost_created, success, message, vhost)
                except Exception as e:
                    logger.error(f"Error creando vhost: {e}", exc_info=True)
                    GLib.idle_add(self._on_vhost_created, False, str(e), vhost)
            
            thread = threading.Thread(target=create_thread, daemon=True)
            thread.start()
        else:
            dialog.destroy()
    
    def _on_vhost_created(self, success: bool, message: str, vhost: VirtualHost) -> bool:
        """Callback cuando se crea un vhost."""
        self.is_busy = False
        self.set_sensitive(True)
        
        if success:
            # Guardar en base de datos
            vhost.save()
            logger.info(f"Host virtual guardado en BD con ID: {vhost.id}")
            
            self._update_statusbar(f"✓ {message}")
            self._show_info("Éxito", f"{message}\n\nAccede en: http://{vhost.server_name}")
            
            # Recargar lista de vhosts
            logger.info("Recargando lista de hosts virtuales...")
            self._load_vhosts()
        else:
            self._update_statusbar(f"✗ Error: {message}")
            self._show_error("Error creando host virtual", message)
        
        return False
    
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
        if self.is_busy:
            self._show_error("Operación en curso", "Espere a que termine la operación actual")
            return
        
        try:
            # Obtener la versión seleccionada
            selected_version = None
            for radio in self.php_version_radios:
                if radio.get_active():
                    label = radio.get_label()
                    # Extraer versión del label "PHP 8.3" -> "8.3"
                    selected_version = label.replace('PHP ', '').strip()
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
                f"¿Desea instalar PHP {selected_version} con PHP-FPM y módulos principales?\n\n"
                "Paquetes a instalar:\n"
                f"  • php{selected_version}, php{selected_version}-fpm\n"
                "  • php-mysql, php-xml, php-curl, php-mbstring\n"
                "  • php-zip, php-gd, php-intl\n\n"
                "Esto puede tardar varios minutos y requiere contraseña de administrador."
            )
            response = dialog.run()
            dialog.destroy()
            
            if response != Gtk.ResponseType.YES:
                return
            
            # Bloquear UI y mostrar progreso
            self.is_busy = True
            self.set_sensitive(False)
            
            # Crear diálogo de progreso
            progress_dialog = Gtk.Dialog(
                title=f"Instalando PHP {selected_version}",
                transient_for=self,
                flags=Gtk.DialogFlags.MODAL
            )
            progress_dialog.set_default_size(400, 150)
            
            box = progress_dialog.get_content_area()
            box.set_spacing(10)
            box.set_margin_start(20)
            box.set_margin_end(20)
            box.set_margin_top(20)
            box.set_margin_bottom(20)
            
            progress_label = Gtk.Label(label="Iniciando instalación...")
            box.pack_start(progress_label, False, False, 0)
            
            progress_bar = Gtk.ProgressBar()
            progress_bar.set_show_text(True)
            box.pack_start(progress_bar, False, False, 0)
            
            progress_dialog.show_all()
            
            # Instalar en thread
            def install_thread():
                def progress_callback(fraction, text):
                    GLib.idle_add(progress_bar.set_fraction, fraction)
                    GLib.idle_add(progress_bar.set_text, f"{int(fraction*100)}%")
                    GLib.idle_add(progress_label.set_text, text)
                
                success, message = self.php_manager.install_php_version(
                    selected_version,
                    with_fpm=True,
                    progress_callback=progress_callback
                )
                GLib.idle_add(self._on_php_install_complete, success, message, progress_dialog)
            
            thread = threading.Thread(target=install_thread, daemon=True)
            thread.start()
            
        except Exception as e:
            logger.error(f"Error instalando PHP: {e}", exc_info=True)
            self.is_busy = False
            self.set_sensitive(True)
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
        if self.is_busy:
            self._show_error("Operación en curso", "Espere a que termine la operación actual")
            return
        
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
                # Crear diálogo de progreso
                progress_dialog = Gtk.MessageDialog(
                    transient_for=self,
                    flags=0,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.NONE,
                    text=f"Desinstalando {comp_info.display_name}"
                )
                progress_dialog.format_secondary_text("Por favor espere...")
                
                spinner = Gtk.Spinner()
                spinner.start()
                spinner.set_margin_top(10)
                spinner.set_margin_bottom(10)
                content = progress_dialog.get_content_area()
                content.pack_start(spinner, False, False, 0)
                progress_dialog.show_all()
                
                # Bloquear ventana principal
                self.is_busy = True
                self.set_sensitive(False)
                self._update_statusbar(f"Desinstalando {comp_info.display_name}...")
                
                # Desinstalar en thread separado
                def uninstall_thread():
                    try:
                        from core import StackInstaller
                        installer = StackInstaller()
                        success, msg = installer.uninstall_component(component)
                        
                        GLib.idle_add(self._on_uninstall_complete, success, msg, comp_info.display_name, progress_dialog)
                    except Exception as e:
                        logger.error(f"Error desinstalando: {e}", exc_info=True)
                        GLib.idle_add(self._on_uninstall_complete, False, str(e), comp_info.display_name, progress_dialog)
                
                thread = threading.Thread(target=uninstall_thread, daemon=True)
                thread.start()
        except Exception as e:
            logger.error(f"Error desinstalando {component}: {e}", exc_info=True)
            self._show_error("Error", f"No se pudo desinstalar {component}: {str(e)}")
    
    def _on_uninstall_complete(self, success: bool, message: str, component_name: str, progress_dialog) -> bool:
        """Callback cuando termina la desinstalación."""
        # Cerrar diálogo de progreso
        progress_dialog.destroy()
        
        # Desbloquear ventana
        self.is_busy = False
        self.set_sensitive(True)
        
        if success:
            self._update_statusbar(f"✓ {component_name} desinstalado correctamente")
            logger.info(f"Desinstalación exitosa de {component_name}, re-detectando componentes...")
            
            # Forzar re-detección completa del stack
            # Esto limpiará el cache y volverá a verificar todos los componentes
            try:
                # Re-crear detector para limpiar cualquier cache
                self.stack_detector = StackDetector()
                
                # Detectar nuevamente
                components = self.stack_detector.detect_all()
                self.installed_components = components
                
                logger.info(f"Re-detección completada: {len(components)} componentes encontrados")
                
                # Actualizar BD con nuevo estado
                for name, component in components.items():
                    try:
                        self.db.execute("""
                            UPDATE stack_components 
                            SET installed = ?, version = ?, last_check = CURRENT_TIMESTAMP
                            WHERE name = ?
                        """, (int(component.installed), component.version, name))
                        logger.debug(f"BD actualizada: {name} -> installed={component.installed}")
                    except Exception as db_err:
                        logger.error(f"Error actualizando BD para {name}: {db_err}")
                
                # Actualizar UI con el nuevo estado
                self._update_stack_ui(components)
                self._update_php_ui()
                self._update_services_status()
                
                self._show_info("Desinstalación exitosa", message)
                logger.info("UI actualizada correctamente después de desinstalación")
                
            except Exception as e:
                logger.error(f"Error re-detectando después de desinstalar: {e}", exc_info=True)
                self._show_warning("Desinstalación completada", 
                    f"{message}\n\nNota: Reinicia la aplicación para ver los cambios.")
        else:
            self._update_statusbar(f"✗ Error desinstalando {component_name}")
            self._show_error("Error al desinstalar", message)
        
        return False
    
    def _load_vhosts(self) -> None:
        """Carga los hosts virtuales desde la base de datos."""
        try:
            logger.info("Cargando hosts virtuales desde la base de datos...")
            
            # Limpiar lista
            for child in self.vhosts_listbox.get_children():
                self.vhosts_listbox.remove(child)
            
            # Obtener vhosts de la BD
            all_vhosts = VirtualHost.all()
            
            # Ordenar descendente por ID (los más nuevos primero)
            all_vhosts.sort(key=lambda x: x.id if x.id else 0, reverse=True)
            
            # Filtrar si hay búsqueda
            if self.vhost_search_text:
                search = self.vhost_search_text.lower()
                vhosts = [v for v in all_vhosts if search in v.server_name.lower() or search in v.name.lower()]
            else:
                vhosts = all_vhosts
            
            logger.info(f"Se encontraron {len(vhosts)} hosts virtuales (Total: {len(all_vhosts)})")
            
            if not vhosts:
                # Mostrar mensaje cuando no hay vhosts
                row = Gtk.ListBoxRow()
                vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
                vbox.set_margin_top(40)
                vbox.set_margin_bottom(40)
                
                icon = Gtk.Image.new_from_icon_name("network-server-symbolic", Gtk.IconSize.DIALOG)
                vbox.pack_start(icon, False, False, 0)
                
                msg = "No se encontraron hosts virtuales" if self.vhost_search_text else "No hay hosts virtuales configurados"
                label = Gtk.Label(label=msg)
                label.set_margin_top(10)
                vbox.pack_start(label, False, False, 0)
                
                if not self.vhost_search_text:
                    hint = Gtk.Label()
                    hint.set_markup("<small>Haz clic en <b>Nuevo</b> para crear uno</small>")
                    vbox.pack_start(hint, False, False, 0)
                
                row.add(vbox)
                self.vhosts_listbox.add(row)
                
                # Resetear paginación UI
                self.vhost_page_label.set_text("Página 0 de 0")
                self.vhost_prev_btn.set_sensitive(False)
                self.vhost_next_btn.set_sensitive(False)
            else:
                # Paginación
                total_items = len(vhosts)
                total_pages = (total_items + self.vhost_items_per_page - 1) // self.vhost_items_per_page
                
                # Asegurar página válida
                if self.vhost_current_page > total_pages:
                    self.vhost_current_page = total_pages
                if self.vhost_current_page < 1:
                    self.vhost_current_page = 1
                
                start_idx = (self.vhost_current_page - 1) * self.vhost_items_per_page
                end_idx = start_idx + self.vhost_items_per_page
                page_vhosts = vhosts[start_idx:end_idx]
                
                for vhost in page_vhosts:
                    row = self._create_vhost_row(vhost)
                    self.vhosts_listbox.add(row)
                
                # Actualizar controles de paginación
                self.vhost_page_label.set_text(f"Página {self.vhost_current_page} de {total_pages}")
                self.vhost_prev_btn.set_sensitive(self.vhost_current_page > 1)
                self.vhost_next_btn.set_sensitive(self.vhost_current_page < total_pages)
            
            self.vhosts_listbox.show_all()
            
        except Exception as e:
            logger.error(f"Error cargando vhosts: {e}", exc_info=True)
    
    def _on_vhost_search_changed(self, entry):
        """Handler para búsqueda de vhosts."""
        self.vhost_search_text = entry.get_text()
        self.vhost_current_page = 1  # Resetear a primera página
        self._load_vhosts()
        
    def _on_vhost_prev_page(self, button):
        """Handler para página anterior."""
        if self.vhost_current_page > 1:
            self.vhost_current_page -= 1
            self._load_vhosts()
            
    def _on_vhost_next_page(self, button):
        """Handler para página siguiente."""
        self.vhost_current_page += 1
        self._load_vhosts()

    def _create_vhost_row(self, vhost: VirtualHost) -> Gtk.ListBoxRow:
        """Crea una fila para un host virtual."""
        row = Gtk.ListBoxRow()
        row.set_can_focus(False)
        row.vhost = vhost  # Guardar referencia al vhost
        
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        hbox.set_margin_start(10)
        hbox.set_margin_end(10)
        hbox.set_margin_top(6)
        hbox.set_margin_bottom(6)
        
        # Checkbox para selección múltiple
        checkbox = Gtk.CheckButton()
        checkbox.connect("toggled", self._on_vhost_selection_changed)
        row.checkbox = checkbox
        hbox.pack_start(checkbox, False, False, 0)
        
        # Icono
        icon = Gtk.Image.new_from_icon_name("network-server", Gtk.IconSize.DND)
        hbox.pack_start(icon, False, False, 0)
        
        # Información del vhost
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        
        # Nombre y dominio
        name_label = Gtk.Label()
        name_label.set_markup(f"<b>{vhost.server_name}</b>")
        name_label.set_halign(Gtk.Align.START)
        vbox.pack_start(name_label, False, False, 0)
        
        # Ruta y PHP
        info_label = Gtk.Label()
        php_info = f"PHP {vhost.php_version}" if vhost.php_version else "PHP por defecto"
        info_label.set_markup(f"<small>{vhost.document_root} • {php_info}</small>")
        info_label.set_halign(Gtk.Align.START)
        info_label.get_style_context().add_class("dim-label")
        vbox.pack_start(info_label, False, False, 0)
        
        hbox.pack_start(vbox, True, True, 0)
        
        # Estado
        status_label = Gtk.Label()
        if vhost.enabled:
            status_label.set_markup("<span foreground='#10b981'>● Habilitado</span>")
        else:
            status_label.set_markup("<span foreground='#6b7280'>○ Deshabilitado</span>")
        hbox.pack_start(status_label, False, False, 10)
        
        # Botones de acción
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        # Abrir en navegador
        open_btn = Gtk.Button.new_from_icon_name("web-browser", Gtk.IconSize.BUTTON)
        open_btn.set_tooltip_text(f"Abrir http://{vhost.server_name}")
        open_btn.connect("clicked", self._on_open_vhost_browser, vhost.server_name)
        btn_box.pack_start(open_btn, False, False, 0)
        
        # Abrir carpeta
        folder_btn = Gtk.Button.new_from_icon_name("folder", Gtk.IconSize.BUTTON)
        folder_btn.set_tooltip_text("Abrir carpeta del sitio")
        folder_btn.connect("clicked", self._on_open_vhost_folder, vhost.document_root)
        btn_box.pack_start(folder_btn, False, False, 0)
        
        # Eliminar
        delete_btn = Gtk.Button.new_from_icon_name("user-trash", Gtk.IconSize.BUTTON)
        delete_btn.set_tooltip_text("Eliminar host virtual")
        delete_btn.get_style_context().add_class("destructive-action")
        delete_btn.connect("clicked", self._on_delete_vhost, vhost)
        btn_box.pack_start(delete_btn, False, False, 0)
        
        hbox.pack_start(btn_box, False, False, 0)
        
        row.add(hbox)
        return row

    def _on_vhost_selection_changed(self, widget):
        """Actualiza el estado del botón de eliminar seleccionados."""
        has_selection = False
        for row in self.vhosts_listbox.get_children():
            if hasattr(row, 'checkbox') and row.checkbox.get_active():
                has_selection = True
                break
        self.delete_selected_btn.set_sensitive(has_selection)

    def _on_delete_selected_vhosts_clicked(self, button):
        """Elimina los hosts virtuales seleccionados."""
        selected_vhosts = []
        for row in self.vhosts_listbox.get_children():
            if hasattr(row, 'checkbox') and row.checkbox.get_active():
                selected_vhosts.append(row.vhost)
        
        if not selected_vhosts:
            return

        count = len(selected_vhosts)
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Eliminar {count} hosts virtuales"
        )
        
        vhost_names = "\n".join([f"• {v.server_name}" for v in selected_vhosts[:5]])
        if count > 5:
            vhost_names += f"\n... y {count - 5} más"
            
        dialog.format_secondary_text(
            f"¿Está seguro que desea eliminar estos {count} hosts virtuales?\n\n"
            f"{vhost_names}\n\n"
            f"Esta acción es irreversible y eliminará las configuraciones de Apache."
        )
        
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            self.is_busy = True
            self.set_sensitive(False)
            self._update_statusbar(f"Eliminando {count} hosts virtuales...")
            
            def delete_thread():
                try:
                    # Preparar lista de tuplas (name, domain)
                    vhosts_to_delete = [(v.name, v.server_name) for v in selected_vhosts]
                    success, message = self.vhost_manager.delete_vhosts(vhosts_to_delete)
                    
                    GLib.idle_add(self._on_vhosts_deleted_batch, success, message)
                except Exception as e:
                    logger.error(f"Error eliminando vhosts: {e}", exc_info=True)
                    GLib.idle_add(self._on_vhosts_deleted_batch, False, str(e))
            
            threading.Thread(target=delete_thread, daemon=True).start()

    def _on_vhosts_deleted_batch(self, success, message):
        """Callback tras eliminación masiva."""
        self.is_busy = False
        self.set_sensitive(True)
        
        if success:
            self._update_statusbar(message)
            self._load_vhosts()
            self.delete_selected_btn.set_sensitive(False)
        else:
            self._show_error("Error eliminando hosts", message)
            self._update_statusbar("Error en la operación")
    
    def _on_open_vhost_browser(self, button, domain: str) -> None:
        """Abre el vhost en el navegador."""
        try:
            import webbrowser
            webbrowser.open(f"http://{domain}")
        except Exception as e:
            logger.error(f"Error abriendo navegador: {e}")
            self._show_error("Error", f"No se pudo abrir el navegador: {str(e)}")
    
    def _on_open_vhost_folder(self, button, path: str) -> None:
        """Abre la carpeta del vhost."""
        try:
            if os.path.exists(path):
                subprocess.Popen(['xdg-open', path])
            else:
                self._show_error("Carpeta no encontrada", f"La carpeta {path} no existe")
        except Exception as e:
            logger.error(f"Error abriendo carpeta: {e}")
            self._show_error("Error", f"No se pudo abrir la carpeta: {str(e)}")
    
    def _on_delete_vhost(self, button, vhost: VirtualHost) -> None:
        """Elimina un host virtual."""
        if self.is_busy:
            self._show_error("Operación en curso", "Espere a que termine la operación actual")
            return
        
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Eliminar {vhost.server_name}"
        )
        dialog.format_secondary_text(
            f"¿Está seguro que desea eliminar el host virtual?\n\n"
            f"Esto eliminará:\n"
            f"• Configuración de Apache\n"
            f"• Entrada en /etc/hosts\n\n"
            f"Los archivos en {vhost.document_root} NO serán eliminados."
        )
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            self.is_busy = True
            self.set_sensitive(False)
            self._update_statusbar(f"Eliminando {vhost.server_name}...")
            
            def delete_thread():
                try:
                    success, message = self.vhost_manager.delete_vhost(vhost.name, vhost.server_name)
                    
                    GLib.idle_add(self._on_vhost_deleted, success, message, vhost)
                except Exception as e:
                    logger.error(f"Error eliminando vhost: {e}", exc_info=True)
                    GLib.idle_add(self._on_vhost_deleted, False, str(e), vhost)
            
            thread = threading.Thread(target=delete_thread, daemon=True)
            thread.start()
    
    def _on_vhost_deleted(self, success: bool, message: str, vhost: VirtualHost) -> bool:
        """Callback cuando se elimina un vhost."""
        self.is_busy = False
        self.set_sensitive(True)
        
        if success:
            # Eliminar de base de datos
            vhost.delete()
            self._update_statusbar(f"✓ {message}")
            self._show_info("Éxito", message)
            self._load_vhosts()
        else:
            self._update_statusbar(f"✗ Error: {message}")
            self._show_error("Error eliminando host virtual", message)
        
        return False
    
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
        
        # Actualizar ruta del backup manager
        self.backup_manager.backup_dir = Path(backup_path)
        for dir_name in ['databases', 'configs', 'vhosts']:
            (self.backup_manager.backup_dir / dir_name).mkdir(parents=True, exist_ok=True)
        
        self._update_statusbar("Configuración guardada")
        self._show_info("Éxito", "Configuración guardada correctamente")
    
    def _update_backup_stats(self) -> bool:
        """Actualiza las estadísticas de backups."""
        try:
            stats = self.backup_manager.get_backup_stats()
            
            markup = (
                f"<b>Estadísticas de Backups:</b>\n"
                f"  • Total: {stats.get('total_backups', 0)} backups\n"
                f"  • Bases de datos: {stats.get('database_backups', 0)}\n"
                f"  • Configuraciones: {stats.get('config_backups', 0)}\n"
                f"  • Virtual hosts: {stats.get('vhost_backups', 0)}\n"
                f"  • Espacio: {stats.get('total_size_mb', 0):.2f} MB"
            )
            
            self.backup_stats_label.set_markup(markup)
            
        except Exception as e:
            logger.error(f"Error actualizando estadísticas: {e}", exc_info=True)
            self.backup_stats_label.set_markup("<span foreground='#e74c3c'>Error cargando estadísticas</span>")
        
        return False
    
    def _on_backup_database_clicked(self, button) -> None:
        """Handler para crear backup de base de datos."""
        if self.is_busy:
            self._show_error("Operación en curso", "Espere a que termine la operación actual")
            return
        
        # Diálogo para solicitar contraseña
        dialog = Gtk.Dialog(
            title="Backup Base de Datos",
            transient_for=self,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK
        )
        
        box = dialog.get_content_area()
        box.set_spacing(10)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        
        label = Gtk.Label(label="Ingrese la contraseña de root de MySQL/MariaDB:")
        box.pack_start(label, False, False, 0)
        
        password_entry = Gtk.Entry()
        password_entry.set_visibility(False)
        password_entry.set_width_chars(30)
        box.pack_start(password_entry, False, False, 0)
        
        dialog.show_all()
        response = dialog.run()
        password = password_entry.get_text()
        dialog.destroy()
        
        if response != Gtk.ResponseType.OK:
            return
        
        # Ejecutar backup en thread
        self.is_busy = True
        self.set_sensitive(False)
        self._update_statusbar("Creando backup de base de datos...")
        
        def backup_thread():
            try:
                success, message = self.backup_manager.backup_all_mysql_databases(
                    user='root',
                    password=password if password else None
                )
                GLib.idle_add(self._on_backup_complete, success, message, 'database')
            except Exception as e:
                logger.error(f"Error en thread de backup: {e}", exc_info=True)
                GLib.idle_add(self._on_backup_complete, False, str(e), 'database')
        
        thread = threading.Thread(target=backup_thread, daemon=True)
        thread.start()
    
    def _on_backup_apache_clicked(self, button) -> None:
        """Handler para crear backup de configuración Apache."""
        if self.is_busy:
            self._show_error("Operación en curso", "Espere a que termine la operación actual")
            return
        
        self.is_busy = True
        self.set_sensitive(False)
        self._update_statusbar("Creando backup de configuración Apache...")
        
        def backup_thread():
            try:
                success, message = self.backup_manager.backup_apache_config()
                GLib.idle_add(self._on_backup_complete, success, message, 'config')
            except Exception as e:
                logger.error(f"Error en thread de backup: {e}", exc_info=True)
                GLib.idle_add(self._on_backup_complete, False, str(e), 'config')
        
        thread = threading.Thread(target=backup_thread, daemon=True)
        thread.start()
    
    def _on_cleanup_backups_clicked(self, button) -> None:
        """Handler para limpiar backups antiguos."""
        if self.is_busy:
            self._show_error("Operación en curso", "Espere a que termine la operación actual")
            return
        
        # Diálogo de confirmación
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Limpiar backups antiguos"
        )
        dialog.format_secondary_text(
            "Se eliminarán backups con más de 7 días de antigüedad y se mantendrán solo los últimos 10.\n"
            "¿Desea continuar?"
        )
        response = dialog.run()
        dialog.destroy()
        
        if response != Gtk.ResponseType.YES:
            return
        
        self._update_statusbar("Limpiando backups antiguos...")
        
        def cleanup_thread():
            try:
                deleted, message = self.backup_manager.clean_old_backups(days_to_keep=7, max_backups=10)
                GLib.idle_add(self._on_cleanup_complete, deleted, message)
            except Exception as e:
                logger.error(f"Error en limpieza: {e}", exc_info=True)
                GLib.idle_add(self._on_cleanup_complete, 0, str(e))
        
        thread = threading.Thread(target=cleanup_thread, daemon=True)
        thread.start()
    
    def _on_backup_complete(self, success: bool, message: str, backup_type: str) -> bool:
        """Callback cuando termina un backup."""
        self.is_busy = False
        self.set_sensitive(True)
        
        if success:
            self._update_statusbar(f"✓ {message}")
            self._show_info("Backup Completo", message)
        else:
            self._update_statusbar(f"✗ Error: {message}")
            self._show_error("Error en Backup", message)
        
        # Actualizar estadísticas
        self._update_backup_stats()
        return False
    
    def _on_cleanup_complete(self, deleted: int, message: str) -> bool:
        """Callback cuando termina la limpieza de backups."""
        self._update_statusbar(message)
        self._show_info("Limpieza Completa", message)
        self._update_backup_stats()
        return False
    
    def _auto_cleanup_backups(self) -> bool:
        """Limpieza automática de backups (ejecutada por timer)."""
        try:
            # Solo si está habilitado
            if Config.get_value('backup_enabled') != '1':
                return True  # Continuar timer
            
            logger.info("Ejecutando limpieza automática de backups")
            deleted, message = self.backup_manager.clean_old_backups(days_to_keep=7, max_backups=10)
            
            if deleted > 0:
                logger.info(f"Limpieza automática: {message}")
            
        except Exception as e:
            logger.error(f"Error en limpieza automática: {e}", exc_info=True)
        
        return True  # Continuar ejecutando cada 24 horas
    
    def _on_php_install_complete(self, success: bool, message: str, progress_dialog: Gtk.Dialog) -> bool:
        """Callback cuando termina la instalación de PHP."""
        self.is_busy = False
        self.set_sensitive(True)
        progress_dialog.destroy()
        
        if success:
            # Verificar que realmente se instaló antes de actualizar
            installed_versions = self.php_manager.detect_installed_versions()
            if installed_versions:
                self._update_statusbar(f"✓ {message}")
                self._show_info("Instalación Completa", message)
                # Actualizar UI de PHP
                self._update_php_ui()
                # Actualizar detección de stack
                self._detect_stack()
            else:
                # Falló la instalación aunque el script retornó success
                self._update_statusbar("✗ Error: Instalación falló")
                self._show_error(
                    "Error en Instalación",
                    "La instalación reportó éxito pero PHP no está disponible.\n\n"
                    "Posibles causas:\n"
                    "• Ejecutando en Flatpak sin permisos al sistema\n"
                    "• Repositorios no actualizados\n"
                    "• Errores de dependencias\n\n"
                    "Intenta instalar manualmente:\n"
                    "sudo apt update\n"
                    "sudo apt install php8.3 php8.3-fpm php8.3-mysql"
                )
        else:
            self._update_statusbar(f"✗ Error: {message}")
            self._show_error(
                "Error en Instalación", 
                f"{message}\n\n"
                "Si el problema persiste, revisa los logs:\n"
                "tail -f logs/lamp_manager.log"
            )
        
        return False
    
    def _on_uninstall_php_version(self, button, version: str) -> None:
        """Handler para desinstalar una versión de PHP."""
        if self.is_busy:
            self._show_error("Operación en curso", "Espere a que termine la operación actual")
            return
        
        # Confirmar desinstalación
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Desinstalar PHP {version}"
        )
        dialog.format_secondary_text(
            f"¿Está seguro que desea desinstalar PHP {version}?\n\n"
            "Se eliminarán todos los paquetes relacionados con esta versión.\n"
            "Los virtual hosts que usen esta versión dejarán de funcionar."
        )
        response = dialog.run()
        dialog.destroy()
        
        if response != Gtk.ResponseType.YES:
            return
        
        # Bloquear UI y mostrar progreso
        self.is_busy = True
        self.set_sensitive(False)
        
        # Crear diálogo de progreso
        progress_dialog = Gtk.Dialog(
            title=f"Desinstalando PHP {version}",
            transient_for=self,
            flags=Gtk.DialogFlags.MODAL
        )
        progress_dialog.set_default_size(400, 150)
        
        box = progress_dialog.get_content_area()
        box.set_spacing(10)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        
        progress_label = Gtk.Label(label="Iniciando desinstalación...")
        box.pack_start(progress_label, False, False, 0)
        
        progress_bar = Gtk.ProgressBar()
        progress_bar.set_show_text(True)
        box.pack_start(progress_bar, False, False, 0)
        
        progress_dialog.show_all()
        
        # Desinstalar en thread
        def uninstall_thread():
            def progress_callback(fraction, text):
                GLib.idle_add(progress_bar.set_fraction, fraction)
                GLib.idle_add(progress_bar.set_text, f"{int(fraction*100)}%")
                GLib.idle_add(progress_label.set_text, text)
            
            success, message = self.php_manager.uninstall_php_version(
                version,
                progress_callback=progress_callback
            )
            GLib.idle_add(self._on_php_uninstall_complete, success, message, progress_dialog)
        
        thread = threading.Thread(target=uninstall_thread, daemon=True)
        thread.start()
    
    def _on_php_uninstall_complete(self, success: bool, message: str, progress_dialog: Gtk.Dialog) -> bool:
        """Callback cuando termina la desinstalación de PHP."""
        self.is_busy = False
        self.set_sensitive(True)
        progress_dialog.destroy()
        
        if success:
            self._update_statusbar(f"✓ {message}")
            self._show_info("Desinstalación Completa", message)
            # Actualizar UI de PHP
            self._update_php_ui()
            # Actualizar detección de stack
            self._detect_stack()
        else:
            self._update_statusbar(f"✗ Error: {message}")
            self._show_error("Error en Desinstalación", message)
        
        return False
    
    def _on_set_default_php(self, button, version: str) -> None:
        """Handler para establecer versión de PHP como predeterminada."""
        try:
            success, message = self.php_manager.set_default_version(version)
            
            if success:
                self._update_statusbar(message)
                self._show_info("Éxito", message)
                self._update_php_ui()
            else:
                self._show_error("Error", message)
                
        except Exception as e:
            logger.error(f"Error estableciendo versión predeterminada: {e}", exc_info=True)
            self._show_error("Error", str(e))
