import pytest
from PyQt6.QtCore import QPoint, QPointF, Qt
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QDoubleSpinBox, QLineEdit, QScrollArea,
    QSlider, QSpinBox, QVBoxLayout, QWidget,
)

from gem_screening.gui.wheel_focus import install_parameter_wheel_filter


APP = QApplication.instance() or QApplication([])


def wheel(widget):
    position = widget.rect().center()
    event = QWheelEvent(QPointF(position), QPointF(widget.mapToGlobal(position)),
                        QPoint(), QPoint(0, -120), Qt.MouseButton.NoButton,
                        Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
    APP.sendEvent(widget, event)


@pytest.mark.parametrize("factory", [QSpinBox, QDoubleSpinBox, QComboBox, QSlider])
def test_parameter_wheel_requires_click_and_current_focus(factory):
    install_parameter_wheel_filter()
    window = QWidget()
    layout = QVBoxLayout(window)
    other = QLineEdit()
    layout.addWidget(other)
    control = factory()
    if isinstance(control, QComboBox):
        control.addItems([str(i) for i in range(10)])
        control.setCurrentIndex(5)
        value = control.currentIndex
    else:
        control.setValue(5)
        value = control.value
    layout.addWidget(control)
    window.show()
    window.activateWindow()
    APP.processEvents()
    control.setFocus()  # Automatic/keyboard focus alone must not enable the wheel.
    APP.processEvents()
    wheel(control)
    assert value() == 5
    QTest.mouseClick(control, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
    if isinstance(control, QComboBox):
        control.hidePopup()
    control.setFocus()
    APP.processEvents()
    previous = value()
    wheel(control)
    assert value() != previous
    previous = value()
    other.setFocus()
    APP.processEvents()
    wheel(control)
    assert value() == previous
    window.close()


def test_wheel_over_unfocused_parameter_scrolls_page():
    install_parameter_wheel_filter()
    area = QScrollArea()
    area.setWidgetResizable(True)
    content = QWidget()
    layout = QVBoxLayout(content)
    control = QSpinBox()
    control.setValue(5)
    layout.addWidget(control)
    layout.addStretch()
    content.setMinimumHeight(2000)
    area.setWidget(content)
    area.resize(400, 300)
    area.show()
    APP.processEvents()
    wheel(control)
    assert control.value() == 5
    assert area.verticalScrollBar().value() > 0
    area.close()
