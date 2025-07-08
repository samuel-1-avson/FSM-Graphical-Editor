# fsm_designer_project/ui_modernization.py
"""
UI modernization integration helper.
Provides easy integration of modern UI components into the existing application.
"""

from PyQt5.QtWidgets import QMainWindow, QDockWidget, QTabWidget, QSplitter
from PyQt5.QtCore import Qt, QSettings

from .ribbon_toolbar import ModernRibbon
from .modern_properties_panel import ModernPropertiesPanel
from .modern_status_bar import ModernStatusBar
from .modern_welcome_screen import ModernWelcomeScreen


class UIModernizer:
    """Helper class to modernize the existing UI."""
    
    def __init__(self, main_window):
        self.main_window = main_window
        
    def apply_modern_ui(self):
        """Apply all modern UI improvements."""
        # Replace toolbar with ribbon
        self.setup_ribbon()
        
        # Replace properties panel
        self.setup_properties_panel()
        
        # Replace status bar
        self.setup_status_bar()
        
        # Enhanced welcome screen
        self.setup_welcome_screen()
        
        # Apply modern styling
        self.apply_modern_theme()
        
    def setup_ribbon(self):
        """Replace traditional toolbar with modern ribbon."""
        # Remove existing toolbars
        for toolbar in self.main_window.findChildren(QToolBar):
            self.main_window.removeToolBar(toolbar)
            toolbar.deleteLater()
            
        # Create and add ribbon
        self.ribbon = ModernRibbon(self.main_window)
        
        # Connect signals
        self.ribbon.newFileRequested.connect(self.main_window.action_handler.on_new_file)
        self.ribbon.openFileRequested.connect(self.main_window.action_handler.on_open_file)
        self.ribbon.saveFileRequested.connect(self.main_window.action_handler.on_save_file)
        self.ribbon.modeChanged.connect(self.on_mode_changed)
        self.ribbon.zoomChanged.connect(self.on_zoom_changed)
        
        # Add to main window
        self.main_window.setMenuWidget(self.ribbon)
        
    def setup_properties_panel(self):
        """Replace properties panel with modern version."""
        # Find existing properties dock
        old_dock = None
        for dock in self.main_window.findChildren(QDockWidget):
            if "properties" in dock.windowTitle().lower():
                old_dock = dock
                break
                
        if old_dock:
            # Create new modern properties panel
            self.properties_panel = ModernPropertiesPanel()
            
            # Connect signals
            self.properties_panel.propertyChanged.connect(self.on_property_changed)
            
            # Replace dock widget content
            old_dock.setWidget(self.properties_panel)
            old_dock.setWindowTitle("Properties")
            
            # Store reference
            self.main_window.modern_properties_panel = self.properties_panel
            
    def setup_status_bar(self):
        """Replace status bar with modern version."""
        # Remove old status bar
        old_status = self.main_window.statusBar()
        if old_status:
            old_status.hide()
            
        # Create new modern status bar
        self.status_bar = ModernStatusBar(self.main_window)
        self.main_window.setStatusBar(self.status_bar)
        
        # Connect signals
        self.status_bar.coordinatesClicked.connect(self.on_coordinates_clicked)
        self.status_bar.zoomClicked.connect(self.on_zoom_clicked)
        
        # Store reference
        self.main_window.modern_status_bar = self.status_bar
        
    def setup_welcome_screen(self):
        """Setup modern welcome screen."""
        # Create welcome screen
        self.welcome_screen = ModernWelcomeScreen()
        
        # Connect signals
        self.welcome_screen.newFileRequested.connect(self.main_window.action_handler.on_new_file)
        self.welcome_screen.openFileRequested.connect(self.main_window.action_handler.on_open_file)
        self.welcome_screen.openRecentRequested.connect(self.open_recent_file)
        self.welcome_screen.showGuideRequested.connect(self.main_window.action_handler.on_show_quick_start)
        self.welcome_screen.showExamplesRequested.connect(self.show_examples)
        
        # Set as the central widget when no tabs are open
        self.main_window.welcome_widget = self.welcome_screen
        
        # Update recent files
        recent_files = self.main_window.settings_manager.get("recent_files", [])
        self.welcome_screen.update_recent_files(recent_files)
        
        # Store reference
        self.main_window.modern_welcome_screen = self.welcome_screen
        
    def apply_modern_theme(self):
        """Apply modern theme and styling."""
        # Enhanced stylesheet with animations and modern design
        modern_stylesheet = """
        /* Global Font */
        * {
            font-family: 'Segoe UI', 'Arial', sans-serif;
        }
        
        /* Main Window */
        QMainWindow {
            background-color: #f5f5f5;
        }
        
        /* Dock Widgets */
        QDockWidget {
            color: #212121;
            font-weight: bold;
            titlebar-close-icon: url(close.png);
            titlebar-normal-icon: url(float.png);
        }
        
        QDockWidget::title {
            text-align: left;
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #f8f8f8, stop: 1 #e0e0e0);
            padding: 6px;
            border-top: 2px solid #0277BD;
            border-bottom: 1px solid #ccc;
        }
        
        QDockWidget::close-button, QDockWidget::float-button {
            border: 1px solid transparent;
            background: transparent;
            padding: 2px;
            border-radius: 3px;
        }
        
        QDockWidget::close-button:hover, QDockWidget::float-button:hover {
            background: rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(0, 0, 0, 0.2);
        }
        
        /* Tab Widget */
        QTabWidget::pane {
            border: 1px solid #ccc;
            background: white;
            border-radius: 4px;
        }
        
        QTabBar::tab {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #f8f8f8, stop: 1 #e0e0e0);
            padding: 8px 16px;
            margin: 2px;
            border: 1px solid #ccc;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        
        QTabBar::tab:selected {
            background: white;
            border-color: #0277BD;
            border-top: 2px solid #0277BD;
        }
        
        QTabBar::tab:hover:!selected {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #fff, stop: 1 #f0f0f0);
        }
        
        /* Scroll Bars */
        QScrollBar:vertical {
            background: #f5f5f5;
            width: 14px;
            margin: 0;
            border: 1px solid #e0e0e0;
        }
        
        QScrollBar::handle:vertical {
            background: #bdbdbd;
            min-height: 30px;
            border-radius: 7px;
            margin: 2px;
        }
        
        QScrollBar::handle:vertical:hover {
            background: #9e9e9e;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
            background: none;
        }
        
        /* Buttons */
        QPushButton {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #fff, stop: 1 #e0e0e0);
            border: 1px solid #bdbdbd;
            padding: 6px 16px;
            border-radius: 4px;
            font-weight: normal;
            min-height: 24px;
        }
        
        QPushButton:hover {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #f5f5f5, stop: 1 #e0e0e0);
            border: 1px solid #0277BD;
        }
        
        QPushButton:pressed {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #e0e0e0, stop: 1 #f5f5f5);
        }
        
        /* Line Edits */
        QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox {
            border: 1px solid #bdbdbd;
            padding: 4px;
            border-radius: 4px;
            background: white;
            selection-background-color: #0277BD;
            selection-color: white;
        }
        
        QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
            border: 2px solid #0277BD;
            padding: 3px;
        }
        
        /* Combo Box */
        QComboBox {
            border: 1px solid #bdbdbd;
            padding: 4px;
            border-radius: 4px;
            background: white;
            min-height: 24px;
        }
        
        QComboBox:hover {
            border: 1px solid #0277BD;
        }
        
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 24px;
            border-left: 1px solid #bdbdbd;
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;
        }
        
        QComboBox::down-arrow {
            image: url(down_arrow.png);
            width: 12px;
            height: 12px;
        }
        
        /* Menus */
        QMenu {
            background: white;
            border: 1px solid #bdbdbd;
            padding: 4px;
            border-radius: 4px;
        }
        
        QMenu::item {
            padding: 6px 24px;
            border-radius: 3px;
        }
        
        QMenu::item:selected {
            background: #0277BD;
            color: white;
        }
        
        QMenu::separator {
            height: 1px;
            background: #e0e0e0;
            margin: 4px 10px;
        }
        
        /* Tool Tips */
        QToolTip {
            background: #424242;
            color: white;
            border: none;
            padding: 6px;
            border-radius: 4px;
            font-size: 9pt;
        }
        
        /* Progress Bar */
        QProgressBar {
            border: 1px solid #bdbdbd;
            border-radius: 4px;
            text-align: center;
            background: #f5f5f5;
            min-height: 20px;
        }
        
        QProgressBar::chunk {
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #0277BD, stop: 1 #0288D1);
            border-radius: 3px;
        }
        """
        
        self.main_window.setStyleSheet(modern_stylesheet)
        
    def on_mode_changed(self, mode):
        """Handle mode change from ribbon."""
        if hasattr(self.main_window, 'current_editor') and self.main_window.current_editor():
            self.main_window.current_editor().scene.set_mode(mode)
            
    def on_zoom_changed(self, value):
        """Handle zoom change from ribbon."""
        if hasattr(self.main_window, 'current_editor') and self.main_window.current_editor():
            editor = self.main_window.current_editor()
            if isinstance(value, int) and value > 100:
                # Zoom in/out by wheel delta
                editor.view.wheelEvent(type('WheelEvent', (), {'angleDelta': lambda: type('QPoint', (), {'y': lambda: value})()}))
            else:
                # Set absolute zoom
                editor.view.setZoom(value)
                
    def on_property_changed(self, property_name, value):
        """Handle property change from modern properties panel."""
        if hasattr(self.main_window, '_current_edited_item_in_dock') and self.main_window._current_edited_item_in_dock:
            item = self.main_window._current_edited_item_in_dock
            # Update item with new property value
            # This would need to be implemented based on your item structure
            
    def on_coordinates_clicked(self):
        """Handle coordinates click in status bar."""
        # Could open a goto dialog
        pass
        
    def on_zoom_clicked(self):
        """Handle zoom click in status bar."""
        # Could open zoom presets menu
        pass
        
    def open_recent_file(self, file_path):
        """Open a recent file."""
        if hasattr(self.main_window, '_create_and_load_new_tab'):
            self.main_window._create_and_load_new_tab(file_path)
            
    def show_examples(self):
        """Show examples dialog or folder."""
        import os
        examples_path = os.path.join(os.path.dirname(__file__), "examples")
        if os.path.exists(examples_path):
            from PyQt5.QtGui import QDesktopServices
            from PyQt5.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(examples_path))


def modernize_ui(main_window):
    """Convenience function to modernize UI."""
    modernizer = UIModernizer(main_window)
    modernizer.apply_modern_ui()
    return modernizer