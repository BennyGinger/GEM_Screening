"""A charcoal and slate palette shared by the application and its dialogs."""

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication


def apply_theme() -> None:
    app = QApplication.instance()
    if app is None:
        return
    app.setStyle("Fusion")
    palette = QPalette(app.palette())
    colors = {
        QPalette.ColorRole.Window: "#343c48",
        QPalette.ColorRole.WindowText: "#edf1f7",
        QPalette.ColorRole.Base: "#505d6e",
        QPalette.ColorRole.AlternateBase: "#465262",
        QPalette.ColorRole.Text: "#f3f6fa",
        QPalette.ColorRole.Button: "#566579",
        QPalette.ColorRole.ButtonText: "#f3f6fa",
        QPalette.ColorRole.Highlight: "#487da5",
        QPalette.ColorRole.HighlightedText: "#ffffff",
        QPalette.ColorRole.ToolTipBase: "#536174",
        QPalette.ColorRole.ToolTipText: "#f3f6fa",
        QPalette.ColorRole.Light: "#75869b",
        QPalette.ColorRole.Midlight: "#627286",
        QPalette.ColorRole.Mid: "#455263",
        QPalette.ColorRole.Dark: "#2c3440",
        QPalette.ColorRole.PlaceholderText: "#c0c9d5",
    }
    for role, color in colors.items():
        palette.setColor(role, QColor(color))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText,
                 QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor("#a4afbd"))
    app.setPalette(palette)
    app.setStyleSheet("""
        QGroupBox {
            background-color: #424e5e;
            border: 1px solid #718198;
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 8px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 5px;
            color: #f3f6fa;
        }
        QGroupBox QGroupBox { background-color: #4b586b; }
        QFrame#experimentSelector, QFrame#pipelineControls {
            background-color: #424e5e;
            border: 1px solid #718198;
            border-radius: 6px;
        }
        QTabWidget::pane {
            border: 1px solid #718198;
            background-color: #424e5e;
            top: -1px;
        }
        QTabBar::tab {
            background-color: #394453;
            color: #c6d0dd;
            border: 1px solid #718198;
            border-top-left-radius: 9px;
            border-top-right-radius: 9px;
            padding: 8px 20px;
            margin-right: 4px;
        }
        QTabBar::tab:hover { background-color: #526279; color: #ffffff; }
        QTabBar::tab:selected {
            background-color: #566579;
            color: #ffffff;
            border-bottom-color: #566579;
        }
        QTabBar#workspaceTabs::tab { font-size: 12pt; font-weight: bold; }
        QTabBar#settingsTabs::tab {
            font-size: 10pt;
            font-style: italic;
            font-weight: normal;
            padding: 6px 16px;
            background-color: #424e5e;
        }
        QTabBar#settingsTabs::tab:selected {
            background-color: #62758b;
            border-bottom-color: #62758b;
            color: #ffffff;
        }
    """)
