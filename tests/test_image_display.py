import numpy as np
import pytest

from a1_manager.utils.image_display import apply_display_lut


def test_display_lut_preserves_camera_intensities() -> None:
    """
    Apply levels to full precision camera values before converting to display pixels.
    """
    raw = np.array([999, 1000, 1024, 1048, 1049], dtype=np.uint16)
    original = raw.copy()
    normalized = apply_display_lut(raw, 1000, 1048)
    np.testing.assert_allclose(normalized, [0, 0, 0.5, 1, 1])
    np.testing.assert_array_equal(raw, original)


@pytest.mark.parametrize(("brightness", "contrast", "expected"),
                         [(50, 50, [0, 0.5, 1]),
                          (100, 50, [0.3, 0.8, 1]),
                          (0, 50, [0, 0.2, 0.7]),
                          (50, 100, [0, 0.5, 1]),
                          (50, 0, [0.5, 0.5, 0.5])],
                         )
def test_display_lut_matches_tuning_adjustments(brightness: int, contrast: int, expected: list[float]) -> None:
    """
    Preserve the segmentation tuning viewer's brightness and contrast behavior.
    """
    raw = np.array([0, 1000, 2000], dtype=np.uint16)
    np.testing.assert_allclose(apply_display_lut(raw, 0, 2000, brightness, contrast), expected, atol=1e-7)
