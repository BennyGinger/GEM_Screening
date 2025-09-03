"""Simple prompt GUI for pipeline decisions using PyQt6."""

import sys
import time
import logging

logger = logging.getLogger(__name__)


class PipelineQuit(Exception):
    """Raised when the user wants to quit the pipeline."""
    pass


# Try to import PyQt6 and define GUI components
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
        QWidget, QLabel, QPushButton
    )
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont
    PYQT_AVAILABLE = True

    class PromptWindow(QMainWindow):
        """Simple prompt window with Continue/Quit buttons."""
        
        def __init__(self, prompt_text: str):
            super().__init__()
            self.prompt_text = prompt_text
            self.result = None
            self.setup_ui()
            
        def setup_ui(self):
            """Set up the user interface."""
            self.setWindowTitle("Pipeline Prompt")
            self.setMinimumSize(400, 200)
            self.resize(500, 250)
            
            # Keep window on top and focused
            self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Window)
            self.activateWindow()
            self.raise_()
            
            # Central widget
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            # Main layout
            layout = QVBoxLayout(central_widget)
            layout.setSpacing(20)
            layout.setContentsMargins(20, 20, 20, 20)
            
            # Prompt text
            prompt_label = QLabel(self.prompt_text)
            prompt_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            prompt_label.setWordWrap(True)
            prompt_font = QFont()
            prompt_font.setPointSize(12)
            prompt_label.setFont(prompt_font)
            layout.addWidget(prompt_label)
            
            # Buttons
            button_layout = QHBoxLayout()
            button_layout.setSpacing(20)
            
            # Quit button
            self.quit_btn = QPushButton("❌ Quit Pipeline")
            self.quit_btn.setFixedSize(150, 40)
            self.quit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff4444;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #cc3333;
                }
            """)
            self.quit_btn.clicked.connect(self._on_quit)
            
            # Continue button
            self.continue_btn = QPushButton("✅ Continue")
            self.continue_btn.setFixedSize(150, 40)
            self.continue_btn.setStyleSheet("""
                QPushButton {
                    background-color: #44aa44;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #338833;
                }
            """)
            self.continue_btn.clicked.connect(self._on_continue)
            self.continue_btn.setDefault(True)  # Make it the default button
            
            # Add buttons to layout
            button_layout.addStretch()
            button_layout.addWidget(self.quit_btn)
            button_layout.addWidget(self.continue_btn)
            button_layout.addStretch()
            
            layout.addLayout(button_layout)
            
            # Set focus to continue button
            self.continue_btn.setFocus()
            
        def _on_quit(self):
            """Handle quit button click."""
            self.result = "quit"
            self.close()
            
        def _on_continue(self):
            """Handle continue button click."""
            self.result = "continue"
            self.close()

    def _show_prompt_gui(prompt_text: str) -> bool:
        """Show prompt using PyQt6 GUI."""
        # Check if QApplication already exists
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
            app_created = True
        else:
            app_created = False
        
        try:
            window = PromptWindow(prompt_text)
            window.show()
            
            # Use polling instead of exec() to avoid conflicts
            while window.result is None:
                app.processEvents()
                time.sleep(0.01)  # Small delay to prevent CPU spinning
            
            result = window.result
            window.close()
            
            if result == "quit":
                raise PipelineQuit("User chose to quit the pipeline")
            elif result == "continue":
                return True
            else:
                # Unexpected result - default to continue
                logger.warning("Unexpected prompt result, defaulting to continue")
                return True
                
        finally:
            if app_created:
                # Only quit the app if we created it
                app.quit()

    def _show_prompt_gui_impl(prompt_text: str) -> bool:
        """Show prompt using PyQt6 GUI implementation."""
        # Check if QApplication already exists
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
            app_created = True
        else:
            app_created = False
        
        try:
            window = PromptWindow(prompt_text)
            window.show()
            
            # Use polling instead of exec() to avoid conflicts
            while window.result is None:
                app.processEvents()
                time.sleep(0.01)  # Small delay to prevent CPU spinning
            
            result = window.result
            window.close()
            
            if result == "quit":
                raise PipelineQuit("User chose to quit the pipeline")
            elif result == "continue":
                return True
            else:
                # Unexpected result - default to continue
                logger.warning("Unexpected prompt result, defaulting to continue")
                return True
                
        finally:
            if app_created:
                # Only quit the app if we created it
                app.quit()

except ImportError:
    PYQT_AVAILABLE = False
    
    def _show_prompt_gui_impl(prompt_text: str) -> bool:
        """Dummy GUI function when PyQt6 is not available."""
        raise ImportError("PyQt6 not available")


def prompt_gui_with_fallback(prompt_text: str, use_gui: bool = True) -> bool:
    """
    Show a prompt with Continue/Quit buttons using PyQt6 GUI, with fallback to terminal.
    
    Args:
        prompt_text (str): The text to display in the prompt
        use_gui (bool): Whether to try using the GUI first
        
    Returns:
        bool: True if user chose to continue, False if quit
        
    Raises:
        PipelineQuit: If user chooses to quit
    """
    if use_gui and PYQT_AVAILABLE:
        try:
            return _show_prompt_gui(prompt_text)
        except ImportError as e:
            logger.warning(f"⚠️  GUI not available ({e}). Using terminal prompt.")
        except PipelineQuit:
            # Re-raise this exception - it's expected
            raise
        except Exception as e:
            logger.warning(f"⚠️  GUI failed ({e}). Using terminal prompt.")
    
    # Fallback to terminal prompt
    return _show_prompt_terminal(prompt_text)


def _show_prompt_gui(prompt_text: str) -> bool:
    """Show prompt using PyQt6 GUI."""
    if not PYQT_AVAILABLE:
        raise ImportError("PyQt6 not available")
    return _show_prompt_gui_impl(prompt_text)


def _show_prompt_terminal(prompt_text: str) -> bool:
    """Show prompt using terminal input."""
    print(f"\n{prompt_text}")
    resp = input("Press Enter to continue or 'q' and Enter to quit: ").strip().lower()
    
    if resp == 'q':
        raise PipelineQuit("User chose to quit the pipeline")
    
    return True
