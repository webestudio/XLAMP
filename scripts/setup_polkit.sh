#!/bin/bash
# Script para crear el archivo de PolicyKit para pkexec

POLICY_FILE="/usr/share/polkit-1/actions/com.lampmanager.pkexec.policy"

cat > "$POLICY_FILE" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE policyconfig PUBLIC
 "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/PolicyKit/1/policyconfig.dtd">
<policyconfig>

  <action id="com.lampmanager.systemctl">
    <description>Run systemctl commands for LAMP services</description>
    <message>Authentication is required to manage LAMP services</message>
    <icon_name>system-run</icon_name>
    <defaults>
      <allow_any>auth_admin</allow_any>
      <allow_inactive>auth_admin</allow_inactive>
      <allow_active>auth_admin_keep</allow_active>
    </defaults>
    <annotate key="org.freedesktop.policykit.exec.path">/usr/bin/systemctl</annotate>
    <annotate key="org.freedesktop.policykit.exec.allow_gui">true</annotate>
  </action>

  <action id="com.lampmanager.apache">
    <description>Manage Apache configuration</description>
    <message>Authentication is required to modify Apache configuration</message>
    <icon_name>system-run</icon_name>
    <defaults>
      <allow_any>auth_admin</allow_any>
      <allow_inactive>auth_admin</allow_inactive>
      <allow_active>auth_admin_keep</allow_active>
    </defaults>
    <annotate key="org.freedesktop.policykit.exec.allow_gui">true</annotate>
  </action>

</policyconfig>
EOF

echo "PolicyKit policy created at $POLICY_FILE"
echo "XLAMP Manager can now use pkexec for privileged operations"
