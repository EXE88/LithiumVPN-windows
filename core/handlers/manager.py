import json
import os
import platform
import winreg
import ctypes
from typing import List, Iterable
from core.handlers import starter
import tempfile
from urllib.parse import urlparse, parse_qs, unquote
from modules import path_helpers

REG_PATH_EXLUSIVE_PROXY = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
VALUE_NAME_EXCLUSIVE_PROXY = "ProxyOverride"
INTERNET_OPTION_SETTINGS_CHANGED = 39
INTERNET_OPTION_REFRESH = 37

def parse_vless(url: str):
    u = urlparse(url)
    if u.scheme not in ("vless", "vmess", "trojan", "ss"):
        raise ValueError("unsupported scheme: " + u.scheme)
    userinfo = u.username or ""
    port = u.port
    host = u.hostname
    query = {k: v[0] for k, v in parse_qs(u.query).items()}
    name = unquote(u.fragment) if u.fragment else ""
    return {
        "scheme": u.scheme,
        "id": userinfo,
        "host": host,
        "port": port,
        "query": query,
        "name": name,
    }

def generate_xray_config(parsed, http_port=10809, enable_geosite=False, dns_servers=None):
    if dns_servers is None:
        dns_servers = ["8.8.8.8", "1.1.1.1"]
    outbound = {}
    proto = parsed.get("scheme", "vless")
    outbound["protocol"] = "vless" if proto == "vless" else proto
    if proto == "vless":
        outbound["settings"] = {
            "vnext": [
                {
                    "address": parsed["host"],
                    "port": int(parsed["port"]),
                    "users": [
                        {
                            "id": parsed["id"],
                            "encryption": parsed["query"].get("encryption", "none")
                        }
                    ]
                }
            ]
        }
    elif proto == "vmess":
        raw = parsed.get("raw", {})
        users = [{
            "id": raw.get("id") or raw.get("uuid"),
            "alterId": int(raw.get("aid", 0)) if raw.get("aid") is not None else 0,
            "security": raw.get("security", "auto")
        }]
        outbound["settings"] = {
            "vnext": [
                {
                    "address": raw.get("add") or raw.get("host"),
                    "port": int(raw.get("port", 0)),
                    "users": users
                }
            ]
        }
    else:
        outbound["settings"] = {
            "vnext": [
                {
                    "address": parsed.get("host"),
                    "port": int(parsed.get("port") or 0),
                    "users": [
                        {"id": parsed.get("id", ""), "encryption": parsed.get("query", {}).get("encryption", "none")}
                    ]
                }
            ]
        }
    stream = {}
    net = parsed.get("query", {}).get("type") or (parsed.get("raw", {}) .get("net") if parsed.get("raw") else None)
    if net:
        stream["network"] = net
    if net == "ws":
        ws_headers = {}
        host_hdr = parsed.get("query", {}).get("host") or (parsed.get("raw", {}).get("host") if parsed.get("raw") else None)
        if host_hdr:
            ws_headers["Host"] = host_hdr
        ws_path = parsed.get("query", {}).get("path") or (parsed.get("raw", {}).get("path") if parsed.get("raw") else "/")
        stream["wsSettings"] = {"path": ws_path, "headers": ws_headers}
    if net == "tcp":
        header_type = parsed.get("query", {}).get("headerType") or (parsed.get("raw", {}).get("type") if parsed.get("raw") else None)
        if header_type == "http":
            host_hdr = parsed.get("query", {}).get("host") or (parsed.get("raw", {}).get("host") if parsed.get("raw") else "")
            stream["tcpSettings"] = {
                "header": {
                    "type": "http",
                    "request": {"headers": {"Host": [host_hdr]}}
                }
            }
    security = parsed.get("query", {}).get("security")
    if parsed.get("raw"):
        raw_tls = parsed["raw"].get("tls")
        if raw_tls in ("tls", "true", "1") or raw_tls is True:
            security = "tls"
    if security and security.lower().startswith("tls"):
        stream["security"] = "tls"
        server_name = parsed.get("query", {}).get("sni") or parsed.get("query", {}).get("host") \
                      or (parsed.get("raw", {}).get("sni") if parsed.get("raw") else None) \
                      or (parsed.get("raw", {}).get("host") if parsed.get("raw") else None)
        stream["tlsSettings"] = {"allowInsecure": True, "serverName": server_name or ""}
    if stream:
        outbound["streamSettings"] = stream
    cfg = {
        "log": {"loglevel": "debug"},
        "dns": {
            "hosts": {
                "localhost": "127.0.0.1"
            },
            "servers": dns_servers
        },
        "inbounds": [
            {"port": http_port, "listen": "127.0.0.1", "protocol": "http",
             "settings": {}, "tag": "http-in"}
        ],
        "outbounds": [
            outbound,
            {"protocol": "freedom", "settings": {}, "tag": "direct"}
        ],
        "routing": {
            "domainStrategy": "AsIs",
            "rules": []
        }
    }
    if enable_geosite:
        cfg["routing"]["rules"].append({
            "type": "field",
            "domain": ["geosite:cn"],
            "outboundTag": "direct"
        })
    return cfg

def write_temp_config(cfg):
    temp_dir = path_helpers.get_path("core","temp")
    tf = tempfile.NamedTemporaryFile(delete=False, suffix=".json", prefix="xray_conf_", dir=temp_dir)
    tf.write(json.dumps(cfg, indent=2).encode("utf-8"))
    tf.flush()
    tf.close()
    return tf.name

def set_windows_system_proxy(http_host="127.0.0.1", http_port=10809):
    try:
        import winreg as reg
    except Exception:
        return
    proxy = f"{http_host}:{http_port}"
    k = reg.OpenKey(reg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 0, reg.KEY_SET_VALUE)
    reg.SetValueEx(k, "ProxyEnable", 0, reg.REG_DWORD, 1)
    reg.SetValueEx(k, "ProxyServer", 0, reg.REG_SZ, proxy)
    reg.CloseKey(k)

def unset_windows_system_proxy():
    try:
        import winreg as reg
    except Exception:
        return
    k = reg.OpenKey(reg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 0, reg.KEY_SET_VALUE)
    reg.SetValueEx(k, "ProxyEnable", 0, reg.REG_DWORD, 0)
    try:
        reg.DeleteValue(k, "ProxyServer")
    except Exception:
        pass
    reg.CloseKey(k)

def _notify_windows():
    try:
        ctypes.windll.Wininet.InternetSetOptionW(None, INTERNET_OPTION_SETTINGS_CHANGED, None, 0)
        ctypes.windll.Wininet.InternetSetOptionW(None, INTERNET_OPTION_REFRESH, None, 0)
    except Exception:
        pass

def _normalize_entries(entries: Iterable[str]) -> List[str]:
    out = []
    for e in entries:
        if e is None:
            continue
        s = str(e).strip()
        if s == "":
            continue
        if s.endswith(";"):
            s = s[:-1].strip()
        if s and s not in out:
            out.append(s)
    return out

def _write_proxy_override_string(value_str: str):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH_EXLUSIVE_PROXY, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.SetValueEx(key, VALUE_NAME_EXCLUSIVE_PROXY, 0, winreg.REG_SZ, value_str)
        finally:
            winreg.CloseKey(key)
    except FileNotFoundError:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH_EXLUSIVE_PROXY)
        try:
            winreg.SetValueEx(key, VALUE_NAME_EXCLUSIVE_PROXY, 0, winreg.REG_SZ, value_str)
        finally:
            winreg.CloseKey(key)
    except OSError as e:
        raise RuntimeError(f"exception in writing registery : {e}") from e

def set_proxy_exceptions(entries: Iterable[str]) -> List[str]:
    normalized = _normalize_entries(entries)
    value_str = ";".join(normalized)
    _write_proxy_override_string(value_str)
    _notify_windows()
    return normalized

class XrayClient:
    def __init__(self, config_code, xray_path=None, http_port=10809, set_system_proxy=False):
        self.config_code = config_code
        self.xray_path = xray_path
        self.http_port = http_port
        self.set_system_proxy = set_system_proxy
        self.xray_proc = None
        self.cfg_path = None

    def start(self):
        parsed = parse_vless(self.config_code)
        cfg = generate_xray_config(parsed, http_port=self.http_port)
        self.cfg_path = write_temp_config(cfg)
        self.xray_proc = starter.startFromJSON(self.cfg_path,json.dumps(cfg))
        if self.set_system_proxy and platform.system().lower().startswith("win"):
            set_windows_system_proxy("127.0.0.1", self.http_port)

    def stop(self):
        if self.set_system_proxy and platform.system().lower().startswith("win"):
            unset_windows_system_proxy()
        if self.xray_proc:
            self.xray_proc.terminate()
            try:
                self.xray_proc.wait(timeout=5)
            except Exception:
                pass
        if self.cfg_path and os.path.exists(self.cfg_path):
            os.remove(self.cfg_path)
        starter._proc = None