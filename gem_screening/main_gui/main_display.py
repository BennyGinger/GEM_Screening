from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

class MainDisplay(QWidget):
    def __init__(self):
        super().__init__()
        self._layout = QVBoxLayout(self)
        self.placeholder = QLabel()
        self._current_widget: QWidget | None = None
        # Start with placeholder visible
        self._layout.addWidget(self.placeholder)

    def set_widget(self, widget: QWidget):
        # Remove and delete current widget if any
        if self._current_widget is not None:
            try:
                self._layout.removeWidget(self._current_widget)
            except Exception:
                pass
            self._current_widget.setParent(None)
            self._current_widget.deleteLater()
            self._current_widget = None
        # Ensure placeholder is not in layout before adding new widget
        try:
            self._layout.removeWidget(self.placeholder)
            self.placeholder.setParent(None)
        except Exception:
            pass
        # Add the new widget and track it
        self._layout.addWidget(widget)
        self._current_widget = widget

    def clear(self):
        # Remove and delete current widget if present
        if self._current_widget is not None:
            try:
                self._layout.removeWidget(self._current_widget)
            except Exception:
                pass
            self._current_widget.setParent(None)
            self._current_widget.deleteLater()
            self._current_widget = None
        # Show placeholder
        if self.placeholder.parent() is None:
            self._layout.addWidget(self.placeholder)
