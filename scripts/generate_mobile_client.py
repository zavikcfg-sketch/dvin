#!/usr/bin/env python3
"""Generate VLESS link for mobile whitelist chain (client → RU bridge)."""
import urllib.parse


def main() -> None:
    print("=== Mobile VPN client link generator ===\n")
    bridge_ip = input("Bridge IP (RU): ").strip()
    client_uuid = input("CLIENT_UUID: ").strip()
    public_key = input("BRIDGE_PUBLIC_KEY: ").strip()
    short_id = input("BRIDGE_SHORT_ID: ").strip()
    bridge_sni = input("BRIDGE_SNI [ya.ru]: ").strip() or "ya.ru"

    params = {
        "encryption": "none",
        "flow": "xtls-rprx-vision",
        "security": "reality",
        "sni": bridge_sni,
        "fp": "chrome",
        "pbk": public_key,
        "sid": short_id,
        "type": "tcp",
    }
    query = urllib.parse.urlencode(params)
    name = urllib.parse.quote("Mobile-4G-RU")
    link = f"vless://{client_uuid}@{bridge_ip}:443?{query}#{name}"

    print("\n--- Import this link ---\n")
    print(link)
    print("\n--- Admin panel (add as server) ---")
    print(f"Host:       {bridge_ip}")
    print(f"Public Key: {public_key}")
    print(f"Short ID:   {short_id}")
    print(f"SNI:        {bridge_sni}")


if __name__ == "__main__":
    main()
