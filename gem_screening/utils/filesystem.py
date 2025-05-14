from pathlib import Path
from datetime import datetime
from typing import Union


def create_timestamped_dir(parent: Union[str, Path], suffix: str = "", date_format: str = "%Y%m%d") -> Path:
    """
    Create (or return) a directory named by today's date plus an optional suffix.

    Args:
        parent: base folder (will be created if missing)
        suffix: extra text to append (no leading underscore — it'll be added for you)
        date_format: any valid strftime format, default 'YYYYMMDD'

    Returns:
        Path to the directory (always exists when returned)
    """
    p = Path(parent)
    p.mkdir(parents=True, exist_ok=True)

    date_part = datetime.now().strftime(date_format)
    name = f"{date_part}_{suffix}" if suffix else date_part
    target = p.joinpath(name)
    target.mkdir(exist_ok=True)
    return target