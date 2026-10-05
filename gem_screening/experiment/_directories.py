from pathlib import Path


def setup_dir(root_path: Path, new_dir_name: str, prefix: str | None = None) -> Path:
    """Create and return an experiment directory."""
    formatted_prefix = f"{prefix}_" if prefix is not None else ""
    new_dir = root_path / f"{formatted_prefix}{new_dir_name}"
    new_dir.mkdir(parents=True, exist_ok=True)
    return new_dir
