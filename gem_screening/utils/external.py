from pathlib import Path
import subprocess
import sys


def run_celltinder(csv_path: Path, n_frames: int = 2, crop_size: int = 251) -> None:
    """
    Run the CellTinder application.
    Args:
        csv_path: Path to the CSV file containing cell data.
        n_frames: Number of frames to load for each cell.
        crop_size: Size of the cropped images.
    """
    subprocess.run([
        sys.executable, '-m', 'celltinder',
        str(csv_path), str(n_frames), str(crop_size)
    ], check=True)