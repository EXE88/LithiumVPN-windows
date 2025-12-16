from pathlib import Path
import sys
import os
from configuration import CONFIG

def is_frozen() -> bool:
    return getattr(sys, 'frozen', False)

def get_app_name() -> str:
    return CONFIG.get("PRODUCT_NAME", "MyApp")

def get_company_name() -> str:
    return CONFIG.get("PRODUCT_NAME", "MyCompany")

def get_base_app_dir() -> Path:
    location = CONFIG.get("DATABASE_LOCATION", "LOCALAPPDATA").upper()

    if location == "LOCALAPPDATA":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    elif location == "APPDATA":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif location == "PROGRAMDATA":
        base = Path(os.environ.get("PROGRAMDATA", "C:/ProgramData"))
    elif location == "APP_DIR":
        if is_frozen():
            base = Path(sys.executable).parent
        else:
            base = Path(__file__).resolve().parent.parent
        return base
    else:
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))

    return base / get_company_name() / get_app_name()

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def get_database_path(db_name: str) -> Path:
    base_dir = get_base_app_dir()
    ensure_dir(base_dir)
    return base_dir / db_name

def get_basedir():
    if is_frozen():
        return Path(sys._MEIPASS)
    else:
        return Path(__file__).resolve().parent.parent
    
BASE_DIR = get_basedir()

def get_path(*relative_parts: str):
    return BASE_DIR.joinpath(*relative_parts)
