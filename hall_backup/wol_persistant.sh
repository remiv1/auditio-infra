#!/bin/bash
# Script pour activer le Wake-on-LAN de façon persistante sur une interface réseau Linux
# Demande le nom de l'interface réseau (par défaut eth0)

read -p "Nom de l'interface réseau à configurer pour WoL [eth0] : " IFACE
IFACE=${IFACE:-eth0}

# Vérification de la présence de l'interface
if ! ip link show "$IFACE" > /dev/null 2>&1; then
    echo "Erreur : l'interface $IFACE n'existe pas."
    exit 1
fi

echo "Activation du WoL sur $IFACE..."
sudo ethtool -s "$IFACE" wol g

# Création d'un service systemd pour la persistance
SERVICE_FILE="/etc/systemd/system/wol-$IFACE.service"

sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Wake-on-LAN pour $IFACE
After=network.target

[Service]
Type=oneshot
ExecStart=/sbin/ethtool -s $IFACE wol g

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable wol-$IFACE.service
sudo systemctl start wol-$IFACE.service

echo "WoL activé et persistant sur $IFACE."
