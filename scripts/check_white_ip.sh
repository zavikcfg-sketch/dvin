#!/bin/bash
# Quick check: is this server reachable on 443 from outside?
# Real whitelist test must be done from MOBILE 4G (not Wi-Fi).
set -euo pipefail

PORT="${1:-443}"
IP=$(curl -4 -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')

echo "=== White IP check helper ==="
echo "Server IP: $IP"
echo "Port:      $PORT"
echo ""
echo "1. Install temporary web server on 443 (if xray not yet running):"
echo "   apt install -y nginx && systemctl stop xray 2>/dev/null; ..."
echo ""
echo "2. From your PHONE on MOBILE DATA (Wi-Fi OFF), open:"
echo "   https://${IP}/"
echo ""
echo "3. Results:"
echo "   - Page loads     → IP likely WHITELISTED (good for bridge)"
echo "   - Timeout / fail → IP NOT whitelisted, try another VPS/IP"
echo ""
echo "Listening on $PORT:"
ss -tlnp | grep ":$PORT " || echo "(nothing on $PORT yet)"
