#!/bin/bash
# Bridge node (RU): client-facing VLESS Reality + xHTTP chain to EU exit
set -euo pipefail

: "${EU_IP:?Set EU_IP (exit server IP)}"
: "${EU_UUID:?Set EU_UUID}"
: "${EU_PUBLIC_KEY:?Set EU_PUBLIC_KEY}"
: "${EU_SHORT_ID:?Set EU_SHORT_ID}"

EU_SNI="${EU_SNI:-www.microsoft.com}"
BRIDGE_SNI="${BRIDGE_SNI:-ya.ru}"
XHTTP_PATH="${XHTTP_PATH:-/api/v1/update}"

echo "=== Bridge node (RU) — Xray install ==="
echo "Exit: $EU_IP | Bridge SNI: $BRIDGE_SNI"

bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install

CLIENT_UUID=$(xray uuid)
BRIDGE_SHORT_ID=$(openssl rand -hex 4)
KEYS=$(xray x25519)
BRIDGE_PRIVATE_KEY=$(echo "$KEYS" | grep "Private" | awk '{print $3}')
BRIDGE_PUBLIC_KEY=$(echo "$KEYS" | grep "Public" | awk '{print $3}')

# Reality dest for bridge — must be real TLS 1.3 site (ya.ru for Yandex IPs)
BRIDGE_DEST="${BRIDGE_DEST:-${BRIDGE_SNI}:443}"

CONFIG_DIR="/usr/local/etc/xray"
mkdir -p "$CONFIG_DIR"

cat > "$CONFIG_DIR/config.json" << EOF
{
  "log": { "loglevel": "warning" },
  "inbounds": [{
    "listen": "0.0.0.0",
    "port": 443,
    "protocol": "vless",
    "tag": "bridge-in",
    "settings": {
      "clients": [{
        "id": "$CLIENT_UUID",
        "flow": "xtls-rprx-vision",
        "email": "mobile-client"
      }],
      "decryption": "none"
    },
    "streamSettings": {
      "network": "tcp",
      "security": "reality",
      "realitySettings": {
        "show": false,
        "dest": "$BRIDGE_DEST",
        "xver": 0,
        "serverNames": ["$BRIDGE_SNI", "www.$BRIDGE_SNI", "yandex.ru", "ya.ru"],
        "privateKey": "$BRIDGE_PRIVATE_KEY",
        "shortIds": ["", "$BRIDGE_SHORT_ID"]
      }
    },
    "sniffing": {
      "enabled": true,
      "destOverride": ["http", "tls", "quic"],
      "routeOnly": true
    }
  }],
  "outbounds": [
    {
      "tag": "chain-to-europe",
      "protocol": "vless",
      "settings": {
        "vnext": [{
          "address": "$EU_IP",
          "port": 443,
          "users": [{
            "id": "$EU_UUID",
            "encryption": "none",
            "flow": "xtls-rprx-vision"
          }]
        }]
      },
      "streamSettings": {
        "network": "xhttp",
        "security": "reality",
        "realitySettings": {
          "fingerprint": "chrome",
          "serverName": "$EU_SNI",
          "publicKey": "$EU_PUBLIC_KEY",
          "shortId": "$EU_SHORT_ID"
        },
        "xhttpSettings": {
          "mode": "packet-up",
          "path": "$XHTTP_PATH"
        }
      }
    },
    { "protocol": "freedom", "tag": "direct" },
    { "protocol": "blackhole", "tag": "block" }
  ],
  "routing": {
    "domainStrategy": "AsIs",
    "rules": [
      {
        "type": "field",
        "inboundTag": ["bridge-in"],
        "outboundTag": "chain-to-europe"
      }
    ]
  }
}
EOF

systemctl enable xray
systemctl restart xray

BRIDGE_IP=$(curl -4 -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
ENV_FILE="/root/bridge-node.env"

cat > "$ENV_FILE" << EOF
BRIDGE_IP=$BRIDGE_IP
CLIENT_UUID=$CLIENT_UUID
BRIDGE_PUBLIC_KEY=$BRIDGE_PUBLIC_KEY
BRIDGE_SHORT_ID=$BRIDGE_SHORT_ID
BRIDGE_SNI=$BRIDGE_SNI
EU_IP=$EU_IP
EOF
chmod 600 "$ENV_FILE"

# Client link (connect to BRIDGE only)
LINK="vless://${CLIENT_UUID}@${BRIDGE_IP}:443?encryption=none&flow=xtls-rprx-vision&security=reality&sni=${BRIDGE_SNI}&fp=chrome&pbk=${BRIDGE_PUBLIC_KEY}&sid=${BRIDGE_SHORT_ID}&type=tcp#Mobile-Bridge-RU"

echo "$LINK" > /root/client-link.txt
chmod 600 /root/client-link.txt

echo ""
echo "============================================"
echo "  BRIDGE NODE READY"
echo "============================================"
echo "BRIDGE_IP:         $BRIDGE_IP"
echo "CLIENT_UUID:       $CLIENT_UUID"
echo "BRIDGE_PUBLIC_KEY: $BRIDGE_PUBLIC_KEY"
echo "BRIDGE_SHORT_ID:   $BRIDGE_SHORT_ID"
echo "BRIDGE_SNI:        $BRIDGE_SNI"
echo ""
echo "CLIENT LINK (import to Hiddify / Shadowrocket):"
echo "$LINK"
echo ""
echo "Saved: $ENV_FILE, /root/client-link.txt"
echo "============================================"
echo ""
echo "TEST: disable Wi-Fi, use 4G only, import link and open https://2ip.ru"
