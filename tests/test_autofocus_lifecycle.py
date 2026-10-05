import numpy as np
import pytest
from PyQt6.QtWidgets import QApplication

from a1_manager.autofocus.af_utils import QuitAutofocus, RestartAutofocus
from a1_manager.autofocus.autofocus_gui import AutofocusWidget
from a1_manager.autofocus_main import _autofocus_review


@pytest.mark.parametrize(
    ("choice", "expected"),
    [("restart", RestartAutofocus), ("quit", QuitAutofocus)],
)
def test_review_choice_controls_autofocus(choice, expected):
    with pytest.raises(expected):
        _autofocus_review(np.zeros((4, 4)), lambda _image: choice)


def test_continue_choice_accepts_autofocus():
    _autofocus_review(np.zeros((4, 4)), lambda _image: "continue")


def test_autofocus_widget_accepts_constant_and_empty_images():
    app = QApplication.instance() or QApplication([])
    for image in (np.zeros((8, 8), dtype=np.uint16), np.empty((0, 0))):
        widget = AutofocusWidget(image)
        assert not widget.original_pixmap.isNull()
        widget.close()
    app.processEvents()
