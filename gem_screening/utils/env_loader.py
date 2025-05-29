# gem_screening/utils/env_loader.py
import os
from dotenv import load_dotenv

from gem_screening import ROOT_DIR


TEMPLATE = """\
# ⚠️ Please review and customize before running:
FASTAPI_BASE_URL=http://localhost:8000
# Control logging verbosity: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO
"""

def load_pipeline_env(
    default_fastapi_url: str = "http://localhost:8000",
    default_log_level: str = "INFO",
    override_log_level: str | None = None,
                    ) -> str:
    
    env_path = ROOT_DIR.joinpath(".env")
    if not env_path.exists():
        env_path.write_text(TEMPLATE)
        raise FileNotFoundError(
            f".env not found; template created at {env_path}. Please update it and rerun.")

    load_dotenv(env_path, override=False)

    # set FASTAPI_BASE_URL
    fastapi_url = os.getenv("FASTAPI_BASE_URL", default_fastapi_url)
    os.environ["FASTAPI_BASE_URL"] = fastapi_url

    # set LOG_LEVEL (override first, then file, then default)
    if override_log_level:
        lvl = override_log_level.upper()
    else:
        lvl = os.getenv("LOG_LEVEL", default_log_level).upper()
    os.environ["LOG_LEVEL"] = lvl

    return fastapi_url



