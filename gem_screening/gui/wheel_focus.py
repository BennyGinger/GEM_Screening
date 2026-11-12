"""Keep page scrolling from changing parameters under the pointer."""

from weakref import WeakSet

from PyQt6.QtCore import QEvent, QObject, QPointF, Qt
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QApplication, QAbstractScrollArea, QAbstractSpinBox, QComboBox, QSlider, QWidget


class FocusedNumericWheelFilter(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._clicked = WeakSet()
        self._popup_controls = WeakSet()

    def eventFilter(self, watched, event):
        control = watched
        while isinstance(control, QWidget) and not isinstance(
            control, (QAbstractSpinBox, QComboBox, QSlider)
        ):
            if control.isWindow():
                return False
            control = control.parentWidget()
        if not isinstance(control, (QAbstractSpinBox, QComboBox, QSlider)):
            return False
        if event.type() == QEvent.Type.MouseButtonPress:
            control.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self._clicked.add(control)
        elif event.type() == QEvent.Type.FocusOut:
            if event.reason() == Qt.FocusReason.PopupFocusReason:
                self._popup_controls.add(control)
            elif control not in self._popup_controls:
                self._clicked.discard(control)
        elif event.type() == QEvent.Type.FocusIn:
            self._popup_controls.discard(control)
        elif event.type() == QEvent.Type.Wheel:
            if control not in self._clicked or not control.hasFocus():
                event.ignore()
                parent = control.parentWidget()
                while parent is not None:
                    if isinstance(parent, QAbstractScrollArea):
                        if isinstance(event, QWheelEvent):
                            viewport = parent.viewport()
                            forwarded = QWheelEvent(
                                QPointF(viewport.mapFromGlobal(event.globalPosition().toPoint())),
                                event.globalPosition(), event.pixelDelta(), event.angleDelta(),
                                event.buttons(), event.modifiers(), event.phase(), event.inverted(),
                            )
                            QApplication.sendEvent(viewport, forwarded)
                        break
                    parent = parent.parentWidget()
                return True
        return False


def install_parameter_wheel_filter() -> None:
    """Install once per application, including controls created later in dialogs."""
    app = QApplication.instance()
    if app is not None and not hasattr(app, "_parameter_wheel_filter"):
        app._parameter_wheel_filter = FocusedNumericWheelFilter(app)
        app.installEventFilter(app._parameter_wheel_filter)
