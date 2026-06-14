import json
import urllib.parse
import uuid

from core.models import VpnKey, VpnServer


def build_vless_reality_link(key: VpnKey, server: VpnServer) -> str:
    """Build VLESS Reality link compatible with v2rayN, Hiddify, Streisand."""
    params = {
        "encryption": "none",
        "flow": "xtls-rprx-vision",
        "security": "reality",
        "sni": server.sni,
        "fp": server.fingerprint,
        "pbk": server.public_key,
        "sid": server.short_id,
        "type": "tcp",
    }
    query = urllib.parse.urlencode(params)
    name = urllib.parse.quote(f"{server.name}-{server.country}")
    return f"vless://{key.uuid}@{server.host}:{server.port}?{query}#{name}"


def build_xray_client_config(key: VpnKey, server: VpnServer) -> dict:
    """Full Xray JSON config for manual import."""
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "tag": "socks",
                "port": 10808,
                "listen": "127.0.0.1",
                "protocol": "socks",
                "settings": {"udp": True},
            },
            {
                "tag": "http",
                "port": 10809,
                "listen": "127.0.0.1",
                "protocol": "http",
            },
        ],
        "outbounds": [
            {
                "tag": "proxy",
                "protocol": "vless",
                "settings": {
                    "vnext": [
                        {
                            "address": server.host,
                            "port": server.port,
                            "users": [
                                {
                                    "id": key.uuid,
                                    "encryption": "none",
                                    "flow": "xtls-rprx-vision",
                                }
                            ],
                        }
                    ]
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "reality",
                    "realitySettings": {
                        "serverName": server.sni,
                        "fingerprint": server.fingerprint,
                        "publicKey": server.public_key,
                        "shortId": server.short_id,
                        "spiderX": "",
                    },
                },
            },
            {"tag": "direct", "protocol": "freedom"},
            {"tag": "block", "protocol": "blackhole"},
        ],
        "routing": {
            "domainStrategy": "IPIfNonMatch",
            "rules": [
                {"type": "field", "ip": ["geoip:private"], "outboundTag": "direct"},
            ],
        },
    }


def build_xray_server_inbound(key_uuid: str) -> dict:
    """Inbound client entry for Xray server config."""
    return {
        "id": key_uuid,
        "flow": "xtls-rprx-vision",
        "email": f"user-{key_uuid[:8]}",
    }


def generate_new_uuid() -> str:
    return str(uuid.uuid4())


def config_to_json(config: dict) -> str:
    return json.dumps(config, indent=2, ensure_ascii=False)
