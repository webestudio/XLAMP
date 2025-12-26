#!/bin/bash
# Script para instalar reglas de PolicyKit para LAMP Manager
# Esto evitará solicitudes repetidas de contraseña

set -e

echo "=== Instalando reglas de PolicyKit para LAMP Manager ==="

# Crear regla de PolicyKit
POLKIT_RULE="/etc/polkit-1/rules.d/50-lamp-manager.rules"

cat > /tmp/lamp-manager.rules << 'EOF'
// Reglas de PolicyKit para LAMP Manager
// Permite operaciones de Apache y systemctl sin solicitar contraseña repetidamente

polkit.addRule(function(action, subject) {
    // Permitir operaciones de systemctl para apache2
    if ((action.id == "org.freedesktop.systemd1.manage-units" ||
         action.id == "org.freedesktop.systemd1.manage-unit-files") &&
        subject.isInGroup("sudo")) {
        
        // Solo para apache2, mysql y mariadb
        if (action.lookup("unit") == "apache2.service" ||
            action.lookup("unit") == "mysql.service" ||
            action.lookup("unit") == "mariadb.service") {
            return polkit.Result.YES;
        }
    }
    
    // Permitir comandos específicos de Apache
    if (action.id == "org.freedesktop.policykit.exec" &&
        subject.isInGroup("sudo")) {
        
        var program = action.lookup("program");
        
        // Comandos permitidos
        if (program == "/usr/sbin/a2ensite" ||
            program == "/usr/sbin/a2dissite" ||
            program == "/usr/sbin/apache2ctl" ||
            program == "/bin/bash") {  // Para nuestros scripts temporales
            return polkit.Result.YES;
        }
    }
    
    return polkit.Result.NOT_HANDLED;
});
EOF

# Copiar con sudo
echo "Instalando regla en $POLKIT_RULE"
sudo cp /tmp/lamp-manager.rules "$POLKIT_RULE"
sudo chmod 644 "$POLKIT_RULE"

# Limpiar
rm /tmp/lamp-manager.rules

echo ""
echo "✓ Reglas de PolicyKit instaladas correctamente"
echo ""
echo "NOTA: Es posible que necesites reiniciar la sesión o ejecutar:"
echo "  sudo systemctl restart polkit"
echo ""
echo "Después de esto, las operaciones de Apache no solicitarán contraseña"
echo "siempre que pertenezcas al grupo 'sudo'."
