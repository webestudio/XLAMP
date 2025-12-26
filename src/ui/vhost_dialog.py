"""
LAMP Manager - VHost Dialog
Diálogo para crear/editar hosts virtuales.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import logging
import os
from typing import Tuple

from data.models import VirtualHost

logger = logging.getLogger(__name__)


class VHostDialog(Gtk.Dialog):
    """Diálogo para crear/editar hosts virtuales."""
    
    def __init__(self, parent, vhost: VirtualHost = None):
        """
        Inicializa el diálogo.
        
        Args:
            parent: Ventana padre
            vhost: Host virtual a editar (None para crear nuevo)
        """
        title = "Editar Host Virtual" if vhost else "Nuevo Host Virtual"
        super().__init__(title=title, transient_for=parent, flags=0)
        
        self.vhost = vhost or VirtualHost()
        self.is_edit = vhost is not None
        
        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            "Guardar" if self.is_edit else "Crear", Gtk.ResponseType.OK
        )
        
        self.set_default_size(500, 400)
        self.set_border_width(10)
        
        # Contenedor principal
        box = self.get_content_area()
        box.set_spacing(10)
        
        # Grid para el formulario
        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(10)
        grid.set_margin_start(10)
        grid.set_margin_end(10)
        grid.set_margin_top(10)
        grid.set_margin_bottom(10)
        
        row = 0
        
        # Nombre del sitio
        label = Gtk.Label(label="Nombre del sitio:", xalign=0)
        grid.attach(label, 0, row, 1, 1)
        
        self.name_entry = Gtk.Entry()
        self.name_entry.set_placeholder_text("mi-proyecto")
        self.name_entry.set_hexpand(True)
        if self.vhost.name:
            self.name_entry.set_text(self.vhost.name)
        grid.attach(self.name_entry, 1, row, 1, 1)
        
        row += 1
        
        # Dominio
        label = Gtk.Label(label="Dominio:", xalign=0)
        grid.attach(label, 0, row, 1, 1)
        
        domain_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        self.domain_entry = Gtk.Entry()
        self.domain_entry.set_placeholder_text("midominio")
        self.domain_entry.set_hexpand(True)
        if self.vhost.server_name:
            domain_name = self.vhost.server_name.replace('.test', '')
            self.domain_entry.set_text(domain_name)
        domain_box.pack_start(self.domain_entry, True, True, 0)
        
        suffix_label = Gtk.Label(label=".test")
        suffix_label.get_style_context().add_class("dim-label")
        domain_box.pack_start(suffix_label, False, False, 0)
        
        grid.attach(domain_box, 1, row, 1, 1)
        
        row += 1
        
        # Document Root
        label = Gtk.Label(label="Document Root:", xalign=0)
        grid.attach(label, 0, row, 1, 1)
        
        root_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        self.root_entry = Gtk.Entry()
        self.root_entry.set_placeholder_text("/var/www/mi-proyecto")
        self.root_entry.set_hexpand(True)
        if self.vhost.document_root:
            self.root_entry.set_text(self.vhost.document_root)
        root_box.pack_start(self.root_entry, True, True, 0)
        
        browse_btn = Gtk.Button(label="Examinar...")
        browse_btn.connect("clicked", self._on_browse_clicked)
        root_box.pack_start(browse_btn, False, False, 0)
        
        grid.attach(root_box, 1, row, 1, 1)
        
        row += 1
        
        # Puerto
        label = Gtk.Label(label="Puerto:", xalign=0)
        grid.attach(label, 0, row, 1, 1)
        
        self.port_spin = Gtk.SpinButton()
        self.port_spin.set_adjustment(Gtk.Adjustment(
            value=self.vhost.port or 80,
            lower=1,
            upper=65535,
            step_increment=1,
            page_increment=10
        ))
        self.port_spin.set_digits(0)
        grid.attach(self.port_spin, 1, row, 1, 1)
        
        row += 1
        
        # Versión PHP
        label = Gtk.Label(label="Versión PHP:", xalign=0)
        grid.attach(label, 0, row, 1, 1)
        
        self.php_combo = Gtk.ComboBoxText()
        self.php_combo.append("", "PHP por defecto")
        self.php_combo.append("8.3", "PHP 8.3")
        self.php_combo.append("8.2", "PHP 8.2")
        self.php_combo.append("8.1", "PHP 8.1")
        self.php_combo.append("8.0", "PHP 8.0")
        
        if self.vhost.php_version:
            self.php_combo.set_active_id(self.vhost.php_version)
        else:
            self.php_combo.set_active(0)
        
        grid.attach(self.php_combo, 1, row, 1, 1)
        
        row += 1
        
        # Habilitado
        self.enabled_check = Gtk.CheckButton(label="Habilitar sitio")
        self.enabled_check.set_active(self.vhost.enabled if self.vhost else True)
        grid.attach(self.enabled_check, 0, row, 2, 1)
        
        row += 1
        
        # SSL (deshabilitado por ahora)
        self.ssl_check = Gtk.CheckButton(label="Habilitar SSL (HTTPS)")
        self.ssl_check.set_active(self.vhost.ssl_enabled if self.vhost else False)
        self.ssl_check.set_sensitive(False)  # TODO: Implementar SSL
        self.ssl_check.set_tooltip_text("Función en desarrollo")
        grid.attach(self.ssl_check, 0, row, 2, 1)
        
        box.pack_start(grid, True, True, 0)
        
        # Info adicional
        info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        info_box.set_margin_start(10)
        info_box.set_margin_end(10)
        
        info_icon = Gtk.Image.new_from_icon_name("dialog-information", Gtk.IconSize.BUTTON)
        info_box.pack_start(info_icon, False, False, 0)
        
        info_label = Gtk.Label()
        info_label.set_markup(
            "<small>El sitio será accesible en <b>http://dominio.test</b>\n"
            "Se agregará automáticamente a /etc/hosts</small>"
        )
        info_label.set_xalign(0)
        info_box.pack_start(info_label, True, True, 0)
        
        box.pack_start(info_box, False, False, 5)
        
        self.show_all()
    
    def _on_browse_clicked(self, button):
        """Abre diálogo para seleccionar carpeta."""
        dialog = Gtk.FileChooserDialog(
            title="Seleccionar Document Root",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            folder = dialog.get_filename()
            self.root_entry.set_text(folder)
        
        dialog.destroy()
    
    def get_vhost_data(self) -> VirtualHost:
        """
        Obtiene los datos del formulario.
        
        Returns:
            Objeto VirtualHost con los datos
        """
        name = self.name_entry.get_text().strip()
        domain = self.domain_entry.get_text().strip()
        document_root = self.root_entry.get_text().strip()
        port = int(self.port_spin.get_value())
        php_version = self.php_combo.get_active_id()
        enabled = self.enabled_check.get_active()
        ssl_enabled = self.ssl_check.get_active()
        
        # Si no hay nombre, usar el dominio
        if not name:
            name = domain.replace('.', '-')
        
        # Asegurar extensión .test
        if not domain.endswith('.test'):
            domain = f"{domain}.test"
        
        vhost = VirtualHost(
            id=self.vhost.id if self.vhost else None,
            name=name,
            server_name=domain,
            document_root=document_root,
            port=port,
            php_version=php_version if php_version else None,
            enabled=enabled,
            ssl_enabled=ssl_enabled
        )
        
        return vhost
    
    def validate(self) -> Tuple[bool, str]:
        """
        Valida los datos del formulario.
        
        Returns:
            Tupla (válido, mensaje de error)
        """
        domain = self.domain_entry.get_text().strip()
        document_root = self.root_entry.get_text().strip()
        
        if not domain:
            return False, "El dominio es obligatorio"
        
        if not document_root:
            return False, "El Document Root es obligatorio"
        
        # Validar caracteres del dominio
        if not domain.replace('-', '').replace('_', '').isalnum():
            return False, "El dominio solo puede contener letras, números, guiones y guiones bajos"
        
        return True, ""
