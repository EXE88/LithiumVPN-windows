from __future__ import annotations
import subprocess
from typing import Optional
from modules import path_helpers 

_proc: Optional[subprocess.Popen] = None
_last_cfg_path: Optional[str] = None

def _default_xray_path() -> str:
    return path_helpers.get_path("core","binding","xray.exe")

def startFromJSON(cfg_path, cfg_json: str, xray_path: Optional[str] = None) -> subprocess.Popen:
    global _proc, _last_cfg_path
    if _proc is not None:
        raise RuntimeError("xray is already running")

    _last_cfg_path = cfg_path

    if xray_path is None:
        xray_path = _default_xray_path()

    cmd = [xray_path, "-c", _last_cfg_path]
    _proc = subprocess.Popen(cmd)
    return _proc

