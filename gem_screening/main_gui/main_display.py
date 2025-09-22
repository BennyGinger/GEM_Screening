from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

class MainDisplay(QWidget):
    def __init__(self):
        super().__init__()
        self._layout = QVBoxLayout(self)
        self.placeholder = QLabel("Main Area (2/3 of window)")
        self._layout.addWidget(self.placeholder)

    def set_widget(self, widget):
        # Remove all widgets from layout
        while self._layout.count():
            child = self._layout.takeAt(0)
            widget_to_remove = child.widget() if child is not None else None
            if widget_to_remove is not None:
                widget_to_remove.setParent(None)
        # Add the new widget
        self._layout.addWidget(widget)

    def clear(self):
        self.set_widget(self.placeholder)
