from pathlib import Path
import sys

def is_frozen() -> bool:
    return getattr(sys, 'frozen', False)

def get_basedir():
    if is_frozen():
        return Path(sys._MEIPASS)
    else:
        return Path(__file__).resolve().parent.parent
    
BASE_DIR = get_basedir()

def get_path(*relative_parts: str):
    return BASE_DIR.joinpath(*relative_parts)