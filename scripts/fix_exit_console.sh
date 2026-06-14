#!/bin/bash
# Run via Firstbyte VNC/console if SSH was blocked
set -euo pipefail

ufw allow 22/tcp 2>/dev/null || true
ufw allow 443/tcp 2>/dev/null || true
ufw --force enable 2>/dev/null || true

bash /root/install_exit_node.sh

echo ""
systemctl status xray --no-pager
ss -tlnp | grep ':443 ' || true
cat /root/exit-node.env
