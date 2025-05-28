from pathlib import Path


ROOT_DIR = Path(__file__).parent.parent.resolve()
if not ROOT_DIR.exists():
    raise FileNotFoundError(f"Root directory {ROOT_DIR!r} does not exist. Please check your setup.")

