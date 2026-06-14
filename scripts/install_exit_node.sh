#!/bin/bash
# Exit node (EU): VLESS + xHTTP + Reality for bridge connection
set -euo pipefail

echo "=== Exit node (EU) — Xray install ==="

bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install

EXIT_UUID=$(xray uuid)
EXIT_SHORT_ID=$(openssl rand -hex 4)
KEYS=$(xray x25519)
EXIT_PRIVATE_KEY=$(echo "$KEYS" | awk -F': ' '/PrivateKey|Private key/ {print $2}' | tr -d ' ')
EXIT_PUBLIC_KEY=$(echo "$KEYS" | awk -F': ' '/Password|Public key/ {print $2}' | tr -d ' ')
if [ -z "$EXIT_PRIVATE_KEY" ] || [ -z "$EXIT_PUBLIC_KEY" ]; then
  EXIT_PRIVATE_KEY=$(echo "$KEYS" | sed -n '1p' | awk '{print $NF}')
  EXIT_PUBLIC_KEY=$(echo "$KEYS" | sed -n '2p' | awk '{print $NF}')
fi
EXIT_SNI="${EXIT_SNI:-www.microsoft.com}"
XHTTP_PATH="${XHTTP_PATH:-/api/v1/update}"

CONFIG_DIR="/usr/local/etc/xray"
mkdir -p "$CONFIG_DIR"

cat > "$CONFIG_DIR/config.json" << EOF
{
  "log": { "loglevel": "warning" },
  "inbounds": [{
    "listen": "0.0.0.0",
    "port": 443,
    "protocol": "vless",
    "tag": "vless-xhttp-in",
    "settings": {
      "clients": [{
        "id": "$EXIT_UUID",
        "email": "bridge@exit"
      }],
      "decryption": "none"
    },
    "streamSettings": {
      "network": "xhttp",
      "security": "reality",
      "realitySettings": {
        "show": false,
        "dest": "${EXIT_SNI}:443",
        "xver": 0,
        "serverNames": ["$EXIT_SNI", "microsoft.com", "www.microsoft.com"],
        "privateKey": "$EXIT_PRIVATE_KEY",
        "shortIds": ["", "$EXIT_SHORT_ID"]
      },
      "xhttpSettings": {
        "mode": "packet-up",
        "path": "$XHTTP_PATH"
      }
    },
    "sniffing": {
      "enabled": true,
      "destOverride": ["http", "tls", "quic"]
    }
  }],
  "outbounds": [
    { "protocol": "freedom", "tag": "direct" },
    { "protocol": "blackhole", "tag": "block" }
  ],
  "routing": {
    "rules": [
      { "type": "field", "ip": ["geoip:private"], "outboundTag": "direct" }
    ]
  }
}
EOF

if command -v ufw >/dev/null 2>&1; then
  ufw allow 22/tcp
  ufw allow 443/tcp
  ufw --force enable
fi

systemctl enable xray
systemctl restart xray
sleep 1
if ! systemctl is-active --quiet xray; then
  echo "Xray failed to start. Check: journalctl -u xray -n 20"
  journalctl -u xray -n 10 --no-pager || true
  exit 1
fi

ENV_FILE="/root/exit-node.env"
cat > "$ENV_FILE" << EOF
EU_IP=$(curl -4 -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
EXIT_UUID=$EXIT_UUID
EXIT_PUBLIC_KEY=$EXIT_PUBLIC_KEY
EXIT_PRIVATE_KEY=$EXIT_PRIVATE_KEY
EXIT_SHORT_ID=$EXIT_SHORT_ID
EXIT_SNI=$EXIT_SNI
XHTTP_PATH=$XHTTP_PATH
EOF
chmod 600 "$ENV_FILE"

echo ""
echo "============================================"
echo "  EXIT NODE READY"
echo "============================================"
echo "EU_IP:            $(grep EU_IP "$ENV_FILE" | cut -d= -f2)"
echo "EXIT_UUID:        $EXIT_UUID"
echo "EXIT_PUBLIC_KEY:  $EXIT_PUBLIC_KEY"
echo "EXIT_SHORT_ID:    $EXIT_SHORT_ID"
echo "EXIT_SNI:         $EXIT_SNI"
echo "XHTTP_PATH:       $XHTTP_PATH"
echo ""
echo "Saved to: $ENV_FILE"
echo "Use these values when running install_bridge_ru.sh on RU server."
echo "============================================"
