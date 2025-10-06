from __future__ import annotations
import subprocess
import tempfile
import os
from typing import Optional
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

_proc: Optional[subprocess.Popen] = None
_last_cfg_path: Optional[str] = None

def _default_xray_path() -> str:
    return os.getenv("XRAY_PATH", f"{BASE_DIR}\\core\\binding\\xray.exe")

def startFromJSON(cfg_path, cfg_json: str, xray_path: Optional[str] = None) -> subprocess.Popen:
    global _proc, _last_cfg_path
    if _proc is not None:
        raise RuntimeError("xray is already running")

    _last_cfg_path = cfg_path

    if xray_path is None:
        xray_path = _default_xray_path()

    cmd = [xray_path, "-c", _last_cfg_path]
    env = os.environ.copy()
    _proc = subprocess.Popen(cmd, env=env)
    return _proc

