
from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QStackedWidget, QCheckBox

class MainWindow(QMainWindow):
    def __init__(self, pages):
        super().__init__()
        self.setWindowTitle("Settings GUI")
        self.resize(900, 600)

        # Store all pages and advanced info
        self.all_pages = pages
        self.advanced_pages = [i for i, (name, _) in enumerate(pages) if name.lower() == "logging"]

        # Main layout
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        self.setCentralWidget(main_widget)

        # Sidebar layout (vertical)
        sidebar = QVBoxLayout()
        main_layout.addLayout(sidebar)

        # Advanced settings checkbox
        self.advanced_checkbox = QCheckBox("Advanced Settings")
        self.advanced_checkbox.stateChanged.connect(self.update_nav)
        sidebar.addWidget(self.advanced_checkbox)

        # Navigation list
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(180)
        sidebar.addWidget(self.nav_list)

        # Stacked widget for pages
        self.stack = QStackedWidget()
        for _, page in pages:
            self.stack.addWidget(page)
        main_layout.addWidget(self.stack, 1)

        self.nav_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.update_nav()
        self.nav_list.setCurrentRow(0)

    def update_nav(self):
        show_advanced = self.advanced_checkbox.isChecked()
        # Remember the currently selected logical page index (in all_pages)
        current_nav_row = self.nav_list.currentRow()
        current_logical_index = self.page_map[current_nav_row] if hasattr(self, 'page_map') and 0 <= current_nav_row < len(self.page_map) else None

        self.nav_list.clear()
        self.page_map = []
        for i, (name, _) in enumerate(self.all_pages):
            if i in self.advanced_pages and not show_advanced:
                continue
            self.nav_list.addItem(name)
            self.page_map.append(i)

        # Try to restore selection to the same logical page if still visible
        new_row = 0
        if current_logical_index is not None:
            try:
                new_row = self.page_map.index(current_logical_index)
            except ValueError:
                # If the previous tab is now hidden, select the next available tab
                if current_nav_row < len(self.page_map):
                    new_row = current_nav_row
                else:
                    new_row = max(0, len(self.page_map) - 1)

        self.nav_list.currentRowChanged.disconnect()
        self.nav_list.currentRowChanged.connect(self._sync_stack)
        self.nav_list.setCurrentRow(new_row)
        self._sync_stack(new_row)

    def _sync_stack(self, nav_row):
        if 0 <= nav_row < len(self.page_map):
            self.stack.setCurrentIndex(self.page_map[nav_row])
