import json
import os
import platform
import winreg
import ctypes
import requests
import datetime
from typing import List, Iterable
from core.handlers import starter
import tempfile
from urllib.parse import urlparse, parse_qs, unquote
from modules import path_helpers
import winreg as reg
import base64

REG_PATH_EXLUSIVE_PROXY = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
VALUE_NAME_EXCLUSIVE_PROXY = "ProxyOverride"
INTERNET_OPTION_SETTINGS_CHANGED = 39
INTERNET_OPTION_REFRESH = 37

class XrayConfigGenerator:
    def __init__(self, link: str, http_port: int = 10809, dns_servers=None):
        if dns_servers is None:
            dns_servers = ["8.8.8.8", "1.1.1.1"]
        self.link = link
        self.http_port = int(http_port)
        self.dns_servers = dns_servers

        self.scheme = None
        self.name = ""
        self.query = {}
        self.raw = {}
        self.host = None
        self.port = None
        self.user_id = None

        self._parse_link(link)

    def _parse_link(self, link: str):
        u = urlparse(link)
        scheme = (u.scheme or "").lower()
        if scheme not in ("vless", "vmess"):
            raise ValueError(f"unsupported scheme: {scheme}")
        self.scheme = scheme

        if scheme == "vless":
            # for vless urls like: vless://UUID@host:port?type=tcp&security=reality&pbk=...#name
            self.user_id = u.username or ""
            self.host = u.hostname
            self.port = u.port
            self.query = {k: v[0] for k, v in parse_qs(u.query).items()}
            self.name = unquote(u.fragment) if u.fragment else ""
            self.raw = {}

        else:
            payload = (u.netloc + u.path).lstrip("/")
            self.name = unquote(u.fragment) if u.fragment else ""
            try:
                decoded = base64.b64decode(payload + '=' * (-len(payload) % 4)).decode("utf-8")
                raw = json.loads(decoded)
            except Exception as e:
                raise ValueError(f"invalid vmess payload: {e}") from e
            self.raw = raw
            self.user_id = raw.get("id") or raw.get("uuid") or ""
            self.host = raw.get("add") or raw.get("host") or None
            try:
                self.port = int(raw.get("port")) if raw.get("port") is not None else None
            except Exception:
                self.port = None
            self.query = {}

    def _get_network(self):
        net = None
        if isinstance(self.query, dict):
            net = self.query.get("type")
        if not net and isinstance(self.raw, dict):
            net = self.raw.get("net")
        return (net or "").lower()

    def _build_common_cfg(self, outbound):
        cfg = {
            "log": {"loglevel": "debug"},
            "dns": {"hosts": {"localhost": "127.0.0.1"}, "servers": self.dns_servers},
            "inbounds": [
                {
                    "port": self.http_port,
                    "listen": "127.0.0.1",
                    "protocol": "http",
                    "settings": {},
                    "tag": "http-in",
                }
            ],
            "outbounds": [outbound, {"protocol": "freedom", "settings": {}, "tag": "direct"}],
            "routing": {"domainStrategy": "AsIs", "rules": []},
        }
        return cfg

    def _tls_settings_if_needed(self, stream: dict):
        """
        Handles both TLS and REALITY security based on URL/query/raw config.
        For 'tls' -> sets stream['security']='tls' and tlsSettings...
        For 'reality' -> sets stream['security']='reality' and realitySettings...
        """
        security = None
        if isinstance(self.query, dict):
            security = self.query.get("security")
        if not security and isinstance(self.raw, dict):
            raw_tls = self.raw.get("tls")
            if raw_tls in ("tls", "true", "1") or raw_tls is True:
                security = "tls"

        if not security:
            return

        sec_low = str(security).lower() if isinstance(security, str) else ""

        # TLS branch (regular TLS settings)
        if sec_low.startswith("tls"):
            server_name = (
                (self.query.get("sni") if isinstance(self.query, dict) else None)
                or (self.query.get("host") if isinstance(self.query, dict) else None)
                or (self.raw.get("sni") if isinstance(self.raw, dict) else None)
                or (self.raw.get("host") if isinstance(self.raw, dict) else None)
            )
            stream["security"] = "tls"
            tls_settings = {"allowInsecure": True, "serverName": server_name or ""}

            alpn_val = None
            if isinstance(self.query, dict):
                alpn_val = self.query.get("alpn") or alpn_val
            if not alpn_val and isinstance(self.raw, dict):
                alpn_val = self.raw.get("alpn") or alpn_val
            if alpn_val:
                try:
                    alpn_dec = unquote(str(alpn_val))
                except Exception:
                    alpn_dec = str(alpn_val)
                tls_settings["alpn"] = [a for a in [p.strip() for p in alpn_dec.split(",")] if a]

            allow_insecure = None
            if isinstance(self.query, dict) and "allowInsecure" in self.query:
                allow_insecure = str(self.query.get("allowInsecure")).lower() in ("1", "true", "yes")
            if allow_insecure is None and isinstance(self.raw, dict) and "allowInsecure" in self.raw:
                allow_insecure = str(self.raw.get("allowInsecure")).lower() in ("1", "true", "yes")
            if allow_insecure is not None:
                tls_settings["allowInsecure"] = allow_insecure

            fp = None
            if isinstance(self.query, dict):
                fp = self.query.get("fp") or fp
            if not fp and isinstance(self.raw, dict):
                fp = self.raw.get("fp") or fp
            if fp:
                tls_settings["fingerprint"] = fp

            stream["tlsSettings"] = tls_settings
            return

        # REALITY branch
        if sec_low == "reality":
            stream["security"] = "reality"
            # Map expected realitySettings fields (names per Xray: publicKey, shortId, spiderX, fingerprint, serverName)
            reality = {}

            # publicKey: from pbk OR publicKey
            public_key = None
            if isinstance(self.query, dict):
                public_key = self.query.get("pbk") or self.query.get("publicKey") or public_key
            if not public_key and isinstance(self.raw, dict):
                public_key = self.raw.get("pbk") or self.raw.get("publicKey") or public_key
            if public_key:
                reality["publicKey"] = public_key

            # fingerprint: from fp
            fp = None
            if isinstance(self.query, dict):
                fp = self.query.get("fp") or fp
            if not fp and isinstance(self.raw, dict):
                fp = self.raw.get("fp") or fp
            if fp:
                reality["fingerprint"] = fp

            # serverName: from sni or host
            server_name = None
            if isinstance(self.query, dict):
                server_name = self.query.get("sni") or self.query.get("serverName") or self.query.get("host") or server_name
            if not server_name and isinstance(self.raw, dict):
                server_name = self.raw.get("sni") or self.raw.get("serverName") or self.raw.get("host") or server_name
            if server_name:
                reality["serverName"] = server_name

            # shortId: from sid
            short_id = None
            if isinstance(self.query, dict):
                short_id = self.query.get("sid") or self.query.get("shortId") or short_id
            if not short_id and isinstance(self.raw, dict):
                short_id = self.raw.get("sid") or self.raw.get("shortId") or short_id
            if short_id:
                reality["shortId"] = short_id

            # spiderX: from spx (URL encoded usually)
            spx = None
            if isinstance(self.query, dict):
                spx = self.query.get("spx") or self.query.get("spiderX") or spx
            if not spx and isinstance(self.raw, dict):
                spx = self.raw.get("spx") or self.raw.get("spiderX") or spx
            if spx:
                try:
                    reality["spiderX"] = unquote(str(spx))
                except Exception:
                    reality["spiderX"] = str(spx)

            # other optional REALITY fields: xver/minClientVer etc. (not mandatory)
            # If query/raw contain 'xver' or 'xver' related fields, include them as-is
            if isinstance(self.query, dict) and "xver" in self.query:
                try:
                    reality["xver"] = int(self.query.get("xver"))
                except Exception:
                    reality["xver"] = self.query.get("xver")
            if isinstance(self.raw, dict) and "xver" in self.raw and "xver" not in reality:
                reality["xver"] = self.raw.get("xver")

            stream["realitySettings"] = reality
            return

    def _build_tcp_stream(self):
        stream = {"network": "tcp"}
        header_type = None
        if isinstance(self.query, dict):
            header_type = self.query.get("headerType")
        if not header_type and isinstance(self.raw, dict):
            header_type = self.raw.get("type")
        consumed = set()
        source = self.query if self.query else self.raw
        if header_type == "http":
            host_hdr = ""
            if isinstance(self.query, dict):
                host_hdr = self.query.get("host") or host_hdr
            if not host_hdr and isinstance(self.raw, dict):
                host_hdr = self.raw.get("host") or host_hdr

            request = {"headers": {"Host": [host_hdr]}} if host_hdr else {"headers": {}}

            path_val = None
            if isinstance(self.query, dict):
                path_val = self.query.get("path")
            if not path_val and isinstance(self.raw, dict):
                path_val = self.raw.get("path")
            if path_val:
                try:
                    path_dec = unquote(str(path_val))
                except Exception:
                    path_dec = str(path_val)
                request["path"] = [p for p in [p.strip() for p in path_dec.split(",")] if p]

            method_val = None
            if isinstance(self.query, dict):
                method_val = self.query.get("method")
            if not method_val and isinstance(self.raw, dict):
                method_val = self.raw.get("method")
            if method_val:
                request["method"] = method_val

            headers_val = None
            if isinstance(self.query, dict):
                headers_val = self.query.get("headers")
            if not headers_val and isinstance(self.raw, dict):
                headers_val = self.raw.get("headers")
            if headers_val:
                try:
                    hdrs = json.loads(headers_val) if isinstance(headers_val, str) else headers_val
                    for k, v in hdrs.items():
                        request["headers"][k] = v if isinstance(v, list) else [v]
                except Exception:
                    try:
                        pairs = str(headers_val).split(";")
                        for p in pairs:
                            if ":" in p:
                                k, vv = p.split(":", 1)
                                request["headers"][k.strip()] = [vv.strip()]
                    except Exception:
                        pass

            stream["tcpSettings"] = {"header": {"type": "http", "request": request}}
            consumed.update({"headerType", "host", "path", "method", "headers"})
        return stream

    def _build_grpc_stream(self):
        stream = {"network": "grpc"}
        service = None
        if isinstance(self.query, dict):
            service = self.query.get("serviceName") or self.query.get("service")
        if not service and isinstance(self.raw, dict):
            service = self.raw.get("serviceName") or self.raw.get("service")
        grpc_settings = {"serviceName": service or ""}

        authority = None
        if isinstance(self.query, dict):
            authority = self.query.get("authority") or authority
        if not authority and isinstance(self.raw, dict):
            authority = self.raw.get("authority") or authority
        if authority:
            grpc_settings["authority"] = authority

        stream["grpcSettings"] = grpc_settings
        return stream

    def _build_vless_outbound(self, stream):
        outbound = {
            "protocol": "vless",
            "settings": {
                "vnext": [
                    {
                        "address": self.host,
                        "port": int(self.port or 0),
                        "users": [
                            {
                                "id": self.user_id,
                                "encryption": ((self.query.get("encryption") if isinstance(self.query, dict) else None) or "none"),
                            }
                        ],
                    }
                ]
            },
        }
        if stream:
            outbound["streamSettings"] = stream
        return outbound

    def _build_vmess_outbound(self, stream):
        raw = self.raw or {}
        users = [
            {
                "id": raw.get("id") or raw.get("uuid") or self.user_id,
                "alterId": int(raw.get("aid", 0)) if raw.get("aid") is not None else 0,
                "security": raw.get("security", "auto"),
            }
        ]
        outbound = {
            "protocol": "vmess",
            "settings": {
                "vnext": [
                    {
                        "address": raw.get("add") or raw.get("host") or self.host,
                        "port": int(raw.get("port", 0)) if raw.get("port") is not None else int(self.port or 0),
                        "users": users,
                    }
                ]
            },
        }
        if stream:
            outbound["streamSettings"] = stream
        return outbound

    def generate(self):
        net = self._get_network()
        if net not in ("tcp", "grpc"):
            if not net and self.scheme == "vless":
                net = "tcp"
            else:
                raise ValueError(f"unsupported or missing network type: {net}")

        if net == "tcp":
            stream = self._build_tcp_stream()
        else:
            stream = self._build_grpc_stream()

        if self.scheme == "vless":
            if not self.host or not self.port or not self.user_id:
                raise ValueError("missing host/port/id for vless")
            outbound = self._build_vless_outbound(stream)
        elif self.scheme == "vmess":
            if not (self.raw and (self.raw.get("add") or self.raw.get("host"))) and not self.host:
                raise ValueError("missing host for vmess")
            outbound = self._build_vmess_outbound(stream)
        else:
            raise ValueError(f"unsupported scheme {self.scheme}")

        cfg = self._build_common_cfg(outbound)
        # apply TLS or REALITY settings if needed
        if stream:
            # ensure outbound has a streamSettings object we can pass into the helper
            self._tls_settings_if_needed(cfg["outbounds"][0].setdefault("streamSettings", stream))
        return cfg

def write_temp_config(cfg):
    temp_dir = path_helpers.get_path("core","temp")
    tf = tempfile.NamedTemporaryFile(delete=False, suffix=".json", prefix="xray_conf_", dir=temp_dir)
    tf.write(json.dumps(cfg, indent=2).encode("utf-8"))
    tf.flush()
    tf.close()
    return tf.name

def set_windows_system_proxy(http_host="127.0.0.1", http_port=10809):
    proxy = f"{http_host}:{http_port}"
    k = reg.OpenKey(reg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 0, reg.KEY_SET_VALUE)
    reg.SetValueEx(k, "ProxyEnable", 0, reg.REG_DWORD, 1)
    reg.SetValueEx(k, "ProxyServer", 0, reg.REG_SZ, proxy)
    reg.CloseKey(k)

def unset_windows_system_proxy():
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
    def __init__(self, config_code, xray_path=None, http_port=10809, set_system_proxy=False, manage_global_proc=True):
        self.config_code = config_code
        self.xray_path = xray_path
        self.http_port = http_port
        self.set_system_proxy = set_system_proxy
        self.manage_global_proc = manage_global_proc
        self.xray_proc = None
        self.cfg_path = None

    def start(self):
        gen = XrayConfigGenerator(self.config_code, http_port=self.http_port)
        cfg = gen.generate()
        self.cfg_path = write_temp_config(cfg)
        self.xray_proc = starter.startFromJSON(self.cfg_path, json.dumps(cfg), allow_parallel=not self.manage_global_proc)
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
        if self.manage_global_proc:
            starter._proc = None

    def ping(self,port=10810):
        proxies = {
            "http":f"http://127.0.0.1:{port}",
            "https":f"http://127.0.0.1:{port}"
        }
        xray_proc = XrayClient(self.config_code, http_port=port, manage_global_proc=False)
        start_time = datetime.datetime.now()
        xray_proc.start()
        try:
            requests.get("https://www.google.com/generate_204",proxies=proxies,timeout=10)
            end_time = datetime.datetime.now()
            delta = end_time - start_time
            xray_proc.stop()
            return True, (delta.total_seconds()*100).__round__()
        except:
            xray_proc.stop()
            return False, "EOF"
