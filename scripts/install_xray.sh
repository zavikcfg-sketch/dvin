#!/bin/bash
# Install Xray with VLESS Reality on Ubuntu/Debian VPS
set -euo pipefail

echo "=== Installing Xray-core ==="
bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install

UUID=$(xray uuid)
SHORT_ID=$(openssl rand -hex 4)
KEYS=$(xray x25519)
PRIVATE_KEY=$(echo "$KEYS" | grep "Private" | awk '{print $3}')
PUBLIC_KEY=$(echo "$KEYS" | grep "Public" | awk '{print $3}')

CONFIG_DIR="/usr/local/etc/xray"
mkdir -p "$CONFIG_DIR"

cat > "$CONFIG_DIR/config.json" << EOF
{
  "log": { "loglevel": "warning" },
  "inbounds": [{
    "port": 443,
    "protocol": "vless",
    "settings": {
      "clients": [],
      "decryption": "none"
    },
    "streamSettings": {
      "network": "tcp",
      "security": "reality",
      "realitySettings": {
        "show": false,
        "dest": "www.microsoft.com:443",
        "xver": 0,
        "serverNames": ["www.microsoft.com", "microsoft.com"],
        "privateKey": "$PRIVATE_KEY",
        "shortIds": ["", "$SHORT_ID"]
      }
    },
    "sniffing": { "enabled": true, "destOverride": ["http", "tls"] }
  }],
  "outbounds": [{ "protocol": "freedom" }]
}
EOF

systemctl enable xray
systemctl restart xray

echo ""
echo "=== Xray installed ==="
echo "UUID:       $UUID"
echo "Public Key: $PUBLIC_KEY"
echo "Short ID:   $SHORT_ID"
echo "Port:       443"
echo "SNI:        www.microsoft.com"
echo ""
echo "Save these values — add them to the admin panel."
echo "Add clients to $CONFIG_DIR/config.json or use the bot API."
