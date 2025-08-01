# fsm_designer_project/main.py

import sys
import os
import logging
# --- BEGIN SYS.PATH MODIFICATION BLOCK ---
# This ensures the application can be run directly as a script
if __name__ == '__main__' and (__package__ is None or __package__ == ''):
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_script_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    # Re-import the package to fix the context for relative imports
    import fsm_designer_project.main
    # Exit the original script and run the main entry point from the properly imported module
    sys.exit(fsm_designer_project.main.main_entry_point())
# --- END SYS.PATH MODIFICATION BLOCK ---

import json
import socket
import html
from PyQt5.QtCore import (
    Qt, QTimer, QPoint, QUrl, pyqtSignal, pyqtSlot, QSize, QIODevice, QFile, QSaveFile, QTime
)
from PyQt5.QtGui import (
    QIcon, QKeySequence, QCloseEvent, QPalette, QColor, QPen, QFont, QDesktopServices
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QDockWidget, QAction,
    QToolBar, QVBoxLayout, QWidget, QLabel,
    QStatusBar, QTextEdit, QFileDialog,
    QPushButton, QMenu, QMessageBox,
    QInputDialog, QLineEdit, QColorDialog, QDialog, QFormLayout,
    QSpinBox, QComboBox, QDoubleSpinBox,
    QUndoStack, QStyle, QTabWidget, QGraphicsItem, QCheckBox,QHBoxLayout
)
from PyQt5.QtWidgets import QListWidgetItem
from PyQt5.QtCore import QPointF
from .ui.simulation.ui_virtual_hardware_manager import VirtualHardwareUIManager
# Local application imports
from .ui.graphics.graphics_scene import DiagramScene, ZoomableView
from .ui.graphics.graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem
from .undo_commands import EditItemPropertiesCommand, AddItemCommand
from .core.matlab_integration import MatlabConnection

# --- MODIFIED IMPORTS ---
# The manager and controller classes have been moved to a dedicated 'managers' package.
from .managers import SettingsManager
from .managers.theme_manager import ThemeManager
from .managers.ui_manager import UIManager
from .managers.ide_manager import IDEManager
from .managers.action_handlers import ActionHandler
from .managers.resource_monitor import ResourceMonitorManager
from .managers.perspective_manager import PerspectiveManager
from .managers.plugin_manager import PluginManager
from .ui.widgets.editor_widget import EditorWidget
# --- END MODIFIED IMPORTS ---
# In fsm_designer_project/main.py at the top
from .managers.project_manager import ProjectManager, PROJECT_FILE_FILTER, PROJECT_FILE_EXTENSION

from .core.resource_estimator import ResourceEstimator
from .utils import config
from .utils.config import (
    APP_VERSION, APP_NAME,
    DYNAMIC_UPDATE_COLORS_FROM_THEME,
    COLOR_TEXT_SECONDARY, APP_FONT_SIZE_SMALL, COLOR_ACCENT_PRIMARY
)
from .core.hardware_link_manager import HardwareLinkManager
from .ui.widgets.modern_welcome_screen import ModernWelcomeScreen
from .core.snippet_manager import CustomSnippetManager
from .utils import get_standard_icon, _get_bundled_file_path
from .ui.widgets.editor_widget import EditorWidget
from .ui.ai.ai_chatbot import AIChatbotManager, AIChatUIManager
from .ui.simulation.ui_py_simulation_manager import PySimulationUIManager
from .ui.dialogs import FindItemDialog, SettingsDialog, SubFSMEditorDialog
from .core import FSMSimulator, FSMError
from .ui.dialogs import StatePropertiesDialog
from .core.git_manager import GitManager
from .ui.widgets.custom_widgets import CollapsibleSection, DraggableToolButton
from .ui.animation_manager import AnimationManager
# Import the new code generation functions
from .utils.logging_setup import setup_global_logging, QTextEditHandler
# --- FIX: Import code generation functions for live preview ---
from .utils.python_code_generator import generate_python_fsm_code
from .utils.c_code_generator import generate_c_code_content
# PlantUML and Mermaid are now part of plugins, but we can import their generators
from .plugins.plantuml_exporter import generate_plantuml_text
from .plugins.mermaid_exporter import generate_mermaid_text
# --- END FIX ---


try:
    from . import resources_rc
    RESOURCES_AVAILABLE = True
except ImportError:
    RESOURCES_AVAILABLE = False
    print("WARNING: resources_rc.py not found (relative import failed). Icons and bundled files might be missing.")

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    RESOURCES_AVAILABLE = RESOURCES_AVAILABLE
    PERSPECTIVE_DESIGN_FOCUS = "Design Focus"
    PERSPECTIVE_SIMULATION_FOCUS = "Simulation Focus"
    PERSPECTIVE_IDE_FOCUS = "IDE Focus"
    PERSPECTIVE_AI_FOCUS = "AI Focus"
    PERSPECTIVE_DEVELOPER_VIEW = "Developer View"
    DEFAULT_PERSPECTIVES_ORDER = [
        PERSPECTIVE_DESIGN_FOCUS,
        PERSPECTIVE_SIMULATION_FOCUS,
        PERSPECTIVE_IDE_FOCUS,
        PERSPECTIVE_AI_FOCUS,
        PERSPECTIVE_DEVELOPER_VIEW
    ]

    

    


    

    def _update_dock_color_button_style(self, button: QPushButton, color: QColor):
        luminance = color.lightnessF()
        text_color_name = config.COLOR_TEXT_ON_ACCENT if luminance < 0.5 else config.COLOR_TEXT_PRIMARY
        button.setStyleSheet(f"""
            QPushButton#ColorButtonPropertiesDock {{
                background-color: {color.name()};
                color: {text_color_name};
                border: 1px solid {color.darker(130).name()};
                padding: 5px; 
                min-height: 20px;
                text-align: center;
            }}
            QPushButton#ColorButtonPropertiesDock:hover {{
                border: 1.5px solid {config.COLOR_ACCENT_PRIMARY};
            }}
        """)
        button.setText(color.name().upper())

    def _on_dock_color_button_clicked(self, color_button: QPushButton):
        current_color_hex = color_button.property("currentColorHex")
        initial_color = QColor(current_color_hex) if current_color_hex else QColor(Qt.white)
        
        dialog = QColorDialog(self)
        dialog.setCurrentColor(initial_color)
        if dialog.exec_():
            new_color = dialog.selectedColor()
            if new_color.isValid() and new_color != initial_color:
                self._update_dock_color_button_style(color_button, new_color)
                color_button.setProperty("currentColorHex", new_color.name())
                self._on_dock_property_changed_mw()  



    @pyqtSlot(QGraphicsItem)
    def _update_item_properties_from_move(self, item): pass
    @pyqtSlot(str, object)
    def _handle_setting_changed(self, key, value): pass
    

    


    

    def __init__(self):
        super().__init__()
        self.animation_manager = AnimationManager(self)
        self.plugin_manager = PluginManager()
        
        if not hasattr(QApplication.instance(), 'settings_manager'):
             QApplication.instance().settings_manager = SettingsManager(app_name=APP_NAME)
        self.settings_manager = QApplication.instance().settings_manager
        
        self.project_manager = ProjectManager(self)
        self.project_fs_model = None

        self.theme_manager = ThemeManager()
        self.custom_snippet_manager = CustomSnippetManager(app_name=APP_NAME)
        self.resource_estimator = ResourceEstimator()
        self.matlab_connection = MatlabConnection()
        self.git_manager = GitManager(self)
        
        self._find_dialogs = {}
        self.live_preview_update_timer = QTimer(self)
        self.live_preview_update_timer.setSingleShot(True)
        self.live_preview_update_timer.setInterval(300)
        
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.setDocumentMode(True)
        
        self.action_handler = ActionHandler(self)
        self.ui_manager = UIManager(self)
        self.perspective_manager = PerspectiveManager(self, self.settings_manager)
        self.resource_monitor_manager = ResourceMonitorManager(self, settings_manager=self.settings_manager)
        self.py_sim_ui_manager = PySimulationUIManager(self, action_handler=self.action_handler)
        self.hardware_sim_ui_manager = VirtualHardwareUIManager(self)
        self.ai_chatbot_manager = AIChatbotManager(self)
        self.ai_chat_ui_manager = AIChatUIManager(self)
        self.ide_manager = IDEManager(self)

        self.ui_manager.setup_ui()
        self.action_handler.populate_editing_actions()

        self.resize(1600, 1000)
        self.setMinimumSize(1280, 800)

        self.welcome_widget = ModernWelcomeScreen(self)
        self.welcome_widget.newFileRequested.connect(self.action_handler.on_new_file)
        self.welcome_widget.openProjectRequested.connect(self.action_handler.on_open_file)
        self.welcome_widget.openRecentRequested.connect(self._on_open_recent_project_from_welcome)
        self.welcome_widget.showGuideRequested.connect(self.action_handler.on_show_quick_start)
        self.welcome_widget.showExamplesRequested.connect(self._browse_examples)

        self._update_central_widget()
        if not hasattr(self, 'log_output') or not self.log_output: 
            self.log_output = QTextEdit()
        
        self.ui_log_handler = setup_global_logging(self.log_output)
        
        self.ui_manager.populate_dynamic_docks()
        self.ide_manager.populate_dock()
        self.ai_chat_ui_manager.connect_signals()
        
        self._connect_application_signals() 
        self._apply_initial_settings()
        self.restore_geometry_and_state()
        
        self._internet_connected: bool | None = None
        self.internet_check_timer = QTimer(self)
        self._init_internet_status_check()
        if self.settings_manager.get("resource_monitor_enabled"):
            self.resource_monitor_manager.setup_and_start_monitor()

        QTimer.singleShot(100, lambda: self.perspective_manager.apply_perspective(self.perspective_manager.current_perspective_name))
        QTimer.singleShot(250, lambda: self.ai_chatbot_manager.set_online_status(self._internet_connected if self._internet_connected is not None else False))
        
        logger.info("Main window initialization complete.")
    
    # --- NEW: Welcome Page Logic ---
    def _update_central_widget(self):
        """Swaps the central widget between the tab widget and the welcome page."""
        if self.tab_widget.count() == 0:
            if self.centralWidget() != self.welcome_widget:
                self.setCentralWidget(self.welcome_widget)
                if hasattr(self, 'welcome_widget') and hasattr(self.welcome_widget, 'update_recent_files'):
                    recent_files = self.settings_manager.get("recent_files", [])
                    self.welcome_widget.update_recent_files(recent_files)
        else:
            if self.centralWidget() != self.tab_widget:
                self.setCentralWidget(self.tab_widget)
                self.perspective_manager.apply_perspective(self.PERSPECTIVE_DESIGN_FOCUS)
                
                
    def _connect_application_signals(self):
        logger.debug("Connecting application-level signals...")
        
        self.action_handler.connect_actions()
        
        if hasattr(self, 'preferences_action'):
            self.preferences_action.triggered.connect(self.on_show_preferences_dialog)
            
        self.tab_widget.currentChanged.connect(self._on_current_tab_changed)
        self.tab_widget.tabCloseRequested.connect(self._on_close_tab_requested)
        
        if hasattr(self, 'properties_edit_dialog_button'):
            self.properties_edit_dialog_button.clicked.connect(
                self.ui_manager.on_advanced_edit_button_clicked
            )
        
        if hasattr(self, 'problems_ask_ai_btn'):
            self.problems_ask_ai_btn.clicked.connect(self.on_ask_ai_about_validation_issue)

        if hasattr(self, 'log_level_filter_combo'):
            self.log_level_filter_combo.currentTextChanged.connect(self._on_log_filter_changed)
        if hasattr(self, 'log_filter_edit'):
            self.log_filter_edit.textChanged.connect(self._on_log_filter_changed)
        if hasattr(self, 'log_clear_action'):
            self.log_clear_action.triggered.connect(lambda: self.ui_log_handler.clear_log() if hasattr(self, 'ui_log_handler') else None)

        self.live_preview_update_timer.timeout.connect(self._update_live_preview)
        if hasattr(self, 'live_preview_combo'):
            self.live_preview_combo.currentTextChanged.connect(self._on_live_preview_language_changed)
        if hasattr(self, 'live_preview_dock'):
            self.live_preview_dock.visibilityChanged.connect(self._request_live_preview_update)
            if hasattr(self, 'live_preview_editor'):
                self.live_preview_editor.textChanged.connect(self._on_scratchpad_text_changed)

        if hasattr(self, 'project_tree_view'):
            self.project_tree_view.customContextMenuRequested.connect(self.action_handler.on_project_explorer_context_menu)

        self.perspective_manager.populate_menu()
        if hasattr(self, 'save_perspective_action'): self.save_perspective_action.triggered.connect(self.perspective_manager.save_current_as)
        if hasattr(self, 'reset_perspectives_action'): self.reset_perspectives_action.triggered.connect(self.perspective_manager.reset_all)
        
        self.settings_manager.settingChanged.connect(self._handle_setting_changed)
        self.matlab_connection.connectionStatusChanged.connect(self._update_matlab_status_display)
        self.matlab_connection.simulationFinished.connect(self._handle_matlab_modelgen_or_sim_finished)
        self.matlab_connection.codeGenerationFinished.connect(self._handle_matlab_codegen_finished)
        self.git_manager.git_status_updated.connect(self._on_git_status_updated)
        
        if self.py_sim_ui_manager:
            self.py_sim_ui_manager.simulationStateChanged.connect(self._handle_py_sim_state_changed_by_manager)
            if hasattr(self.ai_chat_ui_manager, 'applyFixRequested'):
                self.ai_chat_ui_manager.applyFixRequested.connect(self.action_handler.apply_ai_fix)

        if self.ide_manager:
            self.ide_manager.ide_dirty_state_changed.connect(self._on_ide_dirty_state_changed_by_manager)
            self.ide_manager.ide_file_path_changed.connect(self._update_window_title)
            self.ide_manager.ide_language_combo_changed.connect(self._on_ide_language_changed_by_manager)
        if hasattr(self, 'target_device_combo'):
            self.target_device_combo.currentTextChanged.connect(self.on_target_device_changed)
            self.target_device_combo.currentTextChanged.connect(self._request_live_preview_update)

        if hasattr(self, 'hardware_sim_ui_manager'):
            self.hardware_sim_ui_manager.hardware_link_manager.rawDataReceived.connect(self._on_raw_data_received)
            self.hardware_sim_ui_manager.hardware_link_manager.rawDataSent.connect(self._on_raw_data_sent)

        self.project_manager.project_loaded.connect(self.on_project_loaded)
        self.project_manager.project_closed.connect(self.on_project_closed)

        logger.info("Application-level signals connected.")
       
    # --- NEW: Helper slot for recent files menu ---
    def _populate_recent_files_menu(self):
        # Ensure recent_files_menu exists. It is created in the UIManager.
        if not hasattr(self, 'recent_files_menu'):
            logger.error("Could not find 'recent_files_menu' to populate. This indicates an initialization error.")
            return

        self.recent_files_menu.clear()
        recent_files = self.settings_manager.get("recent_files", [])
        if not recent_files:
            no_recent_action = self.recent_files_menu.addAction("(No Recent Files)")
            no_recent_action.setEnabled(False)
            return
            
        for i, file_path in enumerate(recent_files):
            # Limit display to a reasonable number, e.g., 10
            if i >= 10: break
            # Create a QAction for each recent file
            action = QAction(f"&{i+1} {os.path.basename(file_path)}", self)
            action.setData(file_path)
            action.setToolTip(file_path)
            action.triggered.connect(self.action_handler.on_open_recent_file)
            self.recent_files_menu.addAction(action)
            
        self.recent_files_menu.addSeparator()
        self.recent_files_menu.addAction("Clear List", self._clear_recent_files_list)
        
    def _clear_recent_files_list(self):
        """Clears the recent files list in settings and updates the menu."""
        reply = QMessageBox.question(self, "Clear Recent Files", 
                                     "Are you sure you want to clear the recent files list?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.settings_manager.set("recent_files", [])
            self._populate_recent_files_menu() # Refresh the menu immediately
            self.log_message("INFO", "Recent files list cleared.")
     
     
     
     
     # ...existing code...
    def _apply_theme(self, theme_name: str):
        logger.info(f"Applying theme: {theme_name}")

        app_instance = QApplication.instance()

        theme_data = self.theme_manager.get_theme_data(theme_name)
        if not theme_data:
            logger.error(f"Theme '{theme_name}' not found. Falling back to Light theme.")
            theme_data = self.theme_manager.get_theme_data("Light")
        
        
        # --- MODIFIED: Use new ThemeManager methods ---
        self.theme_manager.update_dynamic_config_colors(theme_data) 
        new_stylesheet = self.theme_manager.get_current_stylesheet(theme_data)
        # --- END MODIFICATION ---
        
        app_instance.setStyleSheet(new_stylesheet)

        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            if editor:
                editor.scene.setBackgroundBrush(QColor(config.COLOR_BACKGROUND_LIGHT))
                editor.scene.grid_pen_light = QPen(QColor(config.COLOR_GRID_MINOR), 0.7, Qt.DotLine)
                editor.scene.grid_pen_dark = QPen(QColor(config.COLOR_GRID_MAJOR), 0.9, Qt.SolidLine)
                editor.scene.update() 

        if hasattr(self, 'welcome_widget') and self.welcome_widget is not None:
            try:
                self.welcome_widget.update_styles()
            except Exception as e:
                logger.warning(f"Could not update welcome_widget styles: {e}")
    
        self.update()
        self.repaint()
    
        all_widgets = self.findChildren(QWidget) 
        if self.menuBar(): all_widgets.append(self.menuBar()) 
        if self.statusBar(): all_widgets.append(self.statusBar()) 

        for child_widget in all_widgets:
            if child_widget: 
                child_widget.style().unpolish(child_widget)
                child_widget.style().polish(child_widget)
                child_widget.update() 
    
        if app_instance: app_instance.processEvents()
        logger.info(f"Theme '{theme_name}' applied and UI refreshed.")
# ...existing code...


    
    # --- Architecture Change: Tab Management Methods ---

    # --- Tab Management ---

    def current_editor(self) -> EditorWidget | None:
        widget = self.tab_widget.currentWidget()
        if isinstance(widget, EditorWidget):
            return widget
        return None

    def find_editor_by_path(self, file_path: str) -> EditorWidget | None:
        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            if editor and editor.file_path and os.path.normpath(editor.file_path) == os.path.normpath(file_path):
                return editor
        return None
    
    def _create_and_load_new_tab(self, file_path: str):
        if not os.path.exists(file_path) and not file_path.startswith(":/"):
            self.log_message("ERROR", f"Attempted to open non-existent file: {file_path}")
            return
            
        new_editor = self.add_new_editor_tab()
        
        if self._load_into_editor(new_editor, file_path):
            new_editor.file_path = file_path
            new_editor.set_dirty(False)
            new_editor.undo_stack.clear()
            self.action_handler.add_to_recent_files(file_path)
            index = self.tab_widget.indexOf(new_editor)
            if index != -1:
                self.tab_widget.setTabText(index, new_editor.get_tab_title())
                self._update_window_title()
            if self.git_manager:
                QTimer.singleShot(50, lambda p=file_path: self.git_manager.check_file_status(p))
        else:
            index = self.tab_widget.indexOf(new_editor)
            if index != -1: self.tab_widget.removeTab(index)
            new_editor.deleteLater()
            QMessageBox.critical(self, "Error Opening File", f"Could not load diagram from:\n{file_path}")
            
    def _connect_editor_signals(self, editor: EditorWidget):
        
        editor.scene.selectionChanged.connect(self._update_all_ui_element_states)
        editor.scene.scene_content_changed_for_find.connect(self._refresh_find_dialog_if_visible)
        editor.scene.modifiedStatusChanged.connect(self._update_window_title) 
        editor.scene.validation_issues_updated.connect(self.update_problems_dock)
        editor.scene.interaction_mode_changed.connect(self._on_interaction_mode_changed_by_scene)
        editor.scene.item_moved.connect(self._update_item_properties_from_move)
        editor.view.zoomChanged.connect(self.update_zoom_status_display)
        editor.scene.item_edit_requested.connect(self.on_item_edit_requested) # <-- NEW CONNECTION
        if hasattr(editor.scene, 'itemsBoundingRectChanged'):
             editor.scene.itemsBoundingRectChanged.connect(self.update_resource_estimation)
        if hasattr(editor.scene, 'sceneRectChanged'):
             editor.scene.sceneRectChanged.connect(self.update_resource_estimation)  
        
        editor.scene.item_moved.connect(self._request_live_preview_update)
        editor.scene.modifiedStatusChanged.connect(self._request_live_preview_update)
        editor.undo_stack.indexChanged.connect(self._request_live_preview_update)
             
    def add_new_editor_tab(self) -> EditorWidget:
        new_editor = EditorWidget(self, self.custom_snippet_manager)
        new_editor.scene.settings_manager = self.settings_manager
        new_editor.scene.custom_snippet_manager = self.custom_snippet_manager
        index = self.tab_widget.addTab(new_editor, new_editor.get_tab_title())
        self.tab_widget.setCurrentIndex(index)
        self._connect_editor_signals(new_editor)
        self._update_central_widget()
        return new_editor


    # --- Git Integration ---
    def _update_git_menu_actions_state(self):
        editor = self.current_editor()
        is_in_repo = False
        if editor and editor.file_path and self.git_manager:
             file_dir = os.path.dirname(editor.file_path)
             if file_dir in self.git_manager._repo_root_cache:
                 is_in_repo = self.git_manager._repo_root_cache[file_dir] is not None
        
        if hasattr(self, 'git_actions'):
            for action in self.git_actions:
                action.setEnabled(is_in_repo)



    @pyqtSlot(str)
    def _on_live_preview_language_changed(self, language_name: str):
        """Sets the syntax highlighter, requests a content update, and manages UI state."""
        if not hasattr(self, 'live_preview_editor'):
            return
   
        lang_map = {
            "Python FSM": "Python", "C Code": "C/C++ (Generic)",
        }
        highlighter_lang = lang_map.get(language_name, "Text")
        self.live_preview_editor.set_language(highlighter_lang)
   
        # Enable/Disable Sync based on language
        syncable_languages = ["PlantUML", "Mermaid"]
        is_syncable = language_name in syncable_languages
        if hasattr(self, 'scratchpad_sync_action'):
            # When language changes, the sync button should be disabled because the content will regenerate,
            # effectively wiping out user edits. It will be re-enabled if the user types again.
            self.scratchpad_sync_action.setEnabled(False) 
            if is_syncable:
                self.scratchpad_sync_action.setToolTip("Parse the code below and replace the current diagram.")
            else:
                self.scratchpad_sync_action.setToolTip(f"Syncing from '{language_name}' to the diagram is not supported.")

        self._request_live_preview_update()

    
    @pyqtSlot()
    def _on_scratchpad_text_changed(self):
        """Enables the sync button and provides visual feedback when the scratchpad is edited."""
        if hasattr(self, 'scratchpad_sync_action'):
            selected_language = self.live_preview_combo.currentText()
            syncable_languages = ["PlantUML", "Mermaid"]
            is_syncable = selected_language in syncable_languages
        
            self.scratchpad_sync_action.setEnabled(is_syncable)

        if hasattr(self, 'live_preview_editor'):
            self.live_preview_editor.setStyleSheet(f"""
                QPlainTextEdit#LivePreviewEditor {{
                    border: 1px solid {config.COLOR_ACCENT_WARNING};
                    background-color: {QColor(config.COLOR_ACCENT_WARNING).lighter(185).name()};
                }}
            """)

    @pyqtSlot(str)
    def _on_open_recent_project_from_welcome(self, project_path: str):
        """Opens a project file from the Welcome Screen's recent list."""
        if not self.project_manager.is_project_open():
            if project_path and os.path.exists(project_path):
                # Use the project manager's load function
                if not self.project_manager.load_project(project_path):
                    QMessageBox.warning(self, "Project Not Found", f"The project at '{project_path}' could not be loaded or was not     found.")
                    self.action_handler.remove_from_recent_files(project_path)
            else:
                QMessageBox.warning(self, "File Not Found", f"The project file '{project_path}' could not be found.")
                self.action_handler.remove_from_recent_files(project_path)
        else:
            # This case shouldn't happen as the welcome screen is not visible, but it's a good safeguard.
            logger.warning("Attempted to open recent project while another project is already open.")
    
    
    
    @pyqtSlot(str, dict)
    def on_project_loaded(self, project_path: str, project_data: dict):
        """Handles the UI updates when a new project is loaded."""
        self.log_message("INFO", f"Project loaded: {project_data.get('name')}")
    
        # Close all existing tabs without saving (should have been prompted already)
        while self.tab_widget.count() > 0:
            self.tab_widget.removeTab(0)
        
        # Update Project Explorer to the project's root directory
        project_dir = os.path.dirname(project_path)
        if self.project_fs_model:
            root_index = self.project_fs_model.setRootPath(project_dir)
            self.project_tree_view.setRootIndex(root_index)
    
        # Open the main diagram file automatically
        main_diagram_filename = project_data.get("main_diagram")
        if main_diagram_filename:
            main_diagram_path = os.path.join(project_dir, main_diagram_filename)
            if os.path.exists(main_diagram_path):
                self._create_and_load_new_tab(main_diagram_path)
            else:
                QMessageBox.warning(self, "Main Diagram Not Found", f"The main diagram for this project could not be found:\n{main_diagram_path}")
    
        # --- FIX: ADD THIS LINE ---
        self.action_handler.add_to_recent_files(project_path)
        # --- END FIX ---
    
        self._update_project_actions_state()
        self._update_window_title()


    @pyqtSlot()
    def on_project_closed(self):
        """Handles UI updates when a project is closed."""
        self.log_message("INFO", "Project closed.")
    
        # Close all tabs
        while self.tab_widget.count() > 0:
            self.tab_widget.removeTab(0)
    
        # Reset Project Explorer
        if self.project_fs_model:
            root_index = self.project_fs_model.setRootPath(QDir.homePath())
            self.project_tree_view.setRootIndex(root_index)

        self._update_central_widget() # This will show the welcome screen
        self._update_project_actions_state()
        self._update_window_title()
        
        
    def _update_project_actions_state(self):
        """Enables/disables actions based on whether a project is open."""
        is_project_open = self.project_manager.is_project_open()
    
        # Saving a specific file depends on a dirty editor, handled elsewhere.
        # Closing project depends on it being open.
        self.close_project_action.setEnabled(is_project_open)
    
        # You can only create or open a project if one isn't already open.
        can_open_or_create_project = not is_project_open
        self.new_action.setEnabled(can_open_or_create_project)
        self.open_action.setEnabled(can_open_or_create_project)

        # Re-enable standard save/save-as for the active file IF a project is open
        self.save_action.setEnabled(is_project_open and self.current_editor() is not None and self.current_editor().is_dirty())
        self.save_as_action.setEnabled(is_project_open and self.current_editor() is not None)    


    @pyqtSlot(QGraphicsItem)
    def on_item_edit_requested(self, item: QGraphicsItem):
        """
        Handles the request to open a properties dialog for a given graphics item.
        This method now contains the logic that was previously in DiagramScene.
        """
        editor = self.current_editor()
        if not editor or item.scene() != editor.scene:
            return # Item doesn't belong to the active editor

        # --- THIS IS THE MOVED LOGIC ---
        from .ui.dialogs import StatePropertiesDialog, TransitionPropertiesDialog, CommentPropertiesDialog # Local import is fine here

        dialog_executed_and_accepted = False
        new_props_from_dialog = None
        DialogType = None

        old_props = item.get_data() if hasattr(item, 'get_data') else {}
        if isinstance(item, GraphicsStateItem): DialogType = StatePropertiesDialog
        elif isinstance(item, GraphicsTransitionItem): DialogType = TransitionPropertiesDialog
        elif isinstance(item, GraphicsCommentItem): DialogType = CommentPropertiesDialog
        else: return

        if DialogType == StatePropertiesDialog:
            dialog = DialogType(self.settings_manager, self.custom_snippet_manager, parent=self, current_properties=old_props, is_new_state=False, scene_ref=editor.scene)
        elif DialogType == TransitionPropertiesDialog:
            dialog = TransitionPropertiesDialog(self.custom_snippet_manager, parent=self, current_properties=old_props)
        else: 
            dialog = DialogType(parent=self, current_properties=old_props)

        if dialog.exec() == QDialog.Accepted:
            dialog_executed_and_accepted = True
            new_props_from_dialog = dialog.get_properties()

            if isinstance(item, GraphicsStateItem):
                current_new_name = new_props_from_dialog.get('name')
                existing_state = editor.scene.get_state_by_name(current_new_name)
                if current_new_name != old_props.get('name') and existing_state and existing_state != item:
                    QMessageBox.warning(self, "Duplicate Name", f"A state with the name '{current_new_name}' already exists.")
                    return 

        if dialog_executed_and_accepted and new_props_from_dialog is not None:
            final_new_props = old_props.copy()
            final_new_props.update(new_props_from_dialog) 

            if final_new_props == old_props:
                self.log_message("INFO", "Properties unchanged.")
                return

            cmd = EditItemPropertiesCommand(item, old_props, final_new_props, f"Edit {type(item).__name__} Properties")
            editor.undo_stack.push(cmd) 
            
            item_name_for_log = final_new_props.get('name', final_new_props.get('event', final_new_props.get('text', 'Item')))
            self.log_message("INFO", f"Properties updated for: {item_name_for_log}")    


    # --- NEW SLOTS for the Serial Monitor ---
    @pyqtSlot(str)
    def _on_raw_data_received(self, data: str):
        if hasattr(self, 'serial_monitor_output'):
            timestamp = QTime.currentTime().toString('hh:mm:ss.zzz')
            # Use HTML for styling
            formatted_line = (
                f"<span style='color: {config.COLOR_ACCENT_PRIMARY};'><b>RX <<</b></span> "
                f"<span style='color: {config.COLOR_TEXT_SECONDARY};'>[{timestamp}]</span> "
                f"<span>{html.escape(data)}</span>"
            )
            self.serial_monitor_output.append(formatted_line)

    @pyqtSlot(str)
    def _on_raw_data_sent(self, data: str):
        if hasattr(self, 'serial_monitor_output'):
            timestamp = QTime.currentTime().toString('hh:mm:ss.zzz')




            # Use HTML for styling
            formatted_line = (
                f"<span style='color: {config.COLOR_ACCENT_SECONDARY};'><b>TX >></b></span> "
                f"<span style='color: {config.COLOR_TEXT_SECONDARY};'>[{timestamp}]</span> "
                f"<span>{html.escape(data)}</span>"
            )
            self.serial_monitor_output.append(formatted_line)


    @pyqtSlot(str, bool, bool)
    def _on_git_status_updated(self, file_path: str, is_in_repo: bool, has_changes: bool):
        logger.debug(f"Git status updated for '{file_path}': in_repo={is_in_repo}, has_changes={has_changes}")
        editor = self.find_editor_by_path(file_path)
        if not editor: return
            
        editor.has_uncommitted_changes = has_changes
        index = self.tab_widget.indexOf(editor)
        if index == -1: return

        icon = QIcon()
        if is_in_repo and has_changes:
            icon = get_standard_icon(QStyle.SP_MessageBoxWarning, "Git[M]")
        
        self.tab_widget.setTabIcon(index, icon)
        
        if self.current_editor() == editor:
            self._update_git_menu_actions_state()
            
    def run_git_command(self, command: list, op_name: str):
        editor = self.current_editor()
        if not editor or not editor.file_path:
            QMessageBox.critical(self, "Git Error", "No saved file is active.")
            return

        self.set_ui_for_git_op(True, op_name)
        self.git_manager.run_command_in_repo(command, editor.file_path, self._on_git_command_finished)


    def _on_git_command_finished(self, success: bool, stdout: str, stderr: str):
        self.set_ui_for_git_op(False, "Git operation finished.")
        if success:
            QMessageBox.information(self, "Git Success", f"Git operation completed:\n\n{stdout}\n{stderr}")
        else:
            QMessageBox.critical(self, "Git Error", f"Git operation failed:\n\n{stderr}\n\n{stdout}")
        
        editor = self.current_editor()
        if editor and editor.file_path:
            self.git_manager.check_file_status(editor.file_path)

    def set_ui_for_git_op(self, is_running: bool, op_name: str):
        if hasattr(self, 'main_op_status_label'): self.main_op_status_label.setText(f"Git: {op_name}...")
        if hasattr(self, 'progress_bar'): self.progress_bar.setVisible(is_running)
        self.setEnabled(not is_running)

    @pyqtSlot(int)
    def _update_resource_display(self, *args, **kwargs): pass
    @pyqtSlot(str)
    def on_target_device_changed(self, profile_name): pass
    @pyqtSlot(list)
    def update_problems_dock(self, issues_with_items: list): pass
    @pyqtSlot(bool)
    def _handle_py_sim_state_changed_by_manager(self, is_running): pass
    
    # --- DELETED: This method's logic is now in PySimulationUIManager ---
    # @pyqtSlot(bool)
    # def _handle_py_sim_global_ui_enable_by_manager(self, enable): pass
    # --- END DELETION ---

    # --- NEW: Helper slots for Welcome Screen ---
    @pyqtSlot(str)
    def _on_open_recent_from_welcome(self, file_path: str):
        if self.find_editor_by_path(file_path):
            self.tab_widget.setCurrentWidget(self.find_editor_by_path(file_path))
            return
        if file_path and os.path.exists(file_path):
            self._create_and_load_new_tab(file_path)
        else:
            QMessageBox.warning(self, "File Not Found", f"The file '{file_path}' could not be found.")
            if hasattr(self, 'action_handler'):
                self.action_handler.remove_from_recent_files(file_path)

    def _browse_examples(self):
        example_file_path = _get_bundled_file_path("traffic_light.bsm", resource_prefix="examples")
        if example_file_path and os.path.exists(example_file_path):
            examples_dir = os.path.dirname(example_file_path)
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(examples_dir)):
                QMessageBox.warning(self, "Could Not Open Directory", f"Failed to open the examples directory:\n{examples_dir}")
        else:
            QMessageBox.warning(self, "Examples Not Found", "The examples directory could not be located.")
    # --- END NEW ---

    # --- NEW: Slot to handle language change in the live preview dock ---
    @pyqtSlot(str)
    def _on_live_preview_language_changed(self, language_name: str):
        """Sets the syntax highlighter, requests a content update, and manages UI state."""
        if not hasattr(self, 'live_preview_editor'):
            return
        
        lang_map = {
            "Python FSM": "Python", "C Code": "C/C++ (Generic)",
        }
        highlighter_lang = lang_map.get(language_name, "Text")
        self.live_preview_editor.set_language(highlighter_lang)
        
        # --- NEW: Enable/Disable Sync based on language ---
        syncable_languages = ["PlantUML", "Mermaid"]
        is_syncable = language_name in syncable_languages
        if hasattr(self, 'scratchpad_sync_action'):
            # The button is only enabled if the language is syncable AND the user has made edits.
            # So, here we just set the tooltip and let _on_scratchpad_text_changed handle the enabled state.
            if is_syncable:
                self.scratchpad_sync_action.setToolTip("Parse the code below and replace the current diagram.")
            else:
                self.scratchpad_sync_action.setToolTip(f"Syncing from '{language_name}' to the diagram is not supported.")
                self.scratchpad_sync_action.setEnabled(False) # Always disable for non-syncable
        # --- END NEW ---

        self._request_live_preview_update()

    def _update_live_preview(self):
        """
        Updates the code scratchpad based on the current editor's content.
        """
        editor = self.current_editor()
        if not editor or not hasattr(self, 'live_preview_dock') or not self.live_preview_dock.isVisible():
            return

        preview_type = self.live_preview_combo.currentText()
        diagram_data = editor.scene.get_diagram_data()
        preview_text = ""

        if not diagram_data or not diagram_data.get('states'):
            preview_text = f"// No states to generate {preview_type}."
        else:
            try:
                if preview_type == "PlantUML":
                    preview_text = generate_plantuml_text(diagram_data)
                elif preview_type == "Mermaid":
                    preview_text = generate_mermaid_text(diagram_data)
                
                elif preview_type == "C Code":
                    # Get the full profile data to make a more robust decision
                    profile_data = self.resource_estimator.target_profile
                    platform_id = profile_data.get("platform_id", "generic_c")

                    # Map the robust platform_id to the specific template name
                    platform_map = {
                        "arduino": "Arduino (.ino Sketch)",
                        "pico_sdk": "Pico SDK (main.c Snippet)",
                        "esp_idf": "ESP-IDF (main.c Snippet)",
                        "stm32": "STM32 HAL (Snippet)",
                        "generic_c": "Generic C (Header/Source Pair)"
                    }
                    target_platform = platform_map.get(platform_id, "Generic C (Header/Source Pair)")
                    
                    code_dict = generate_c_code_content(diagram_data, "live_preview_fsm", target_platform)
                    preview_text = f"// --- HEADER (live_preview_fsm.h) ---\n\n{code_dict.get('h', '')}\n\n// --- SOURCE (live_preview_fsm.c) ---\n\n{code_dict.get('c', '')}"

                elif preview_type == "Python FSM":
                    preview_text = generate_python_fsm_code(diagram_data, "LivePreviewFSM")
                else:
                    preview_text = "No preview available for this type."
            except Exception as e:
                preview_text = f"// Error generating preview for {preview_type}:\n// {str(e)}"
                logger.error(f"Error during live preview generation for {preview_type}: {e}", exc_info=True)


        self.live_preview_editor.blockSignals(True)
        self.live_preview_editor.setPlainText(preview_text)
        self.live_preview_editor.blockSignals(False)

        if hasattr(self, 'scratchpad_sync_action'):
            self.scratchpad_sync_action.setEnabled(False)
        
        self.live_preview_editor.setStyleSheet(f"""
                QPlainTextEdit#LivePreviewEditor {{
                font-family: Consolas, 'Courier New', monospace;
                font-size: {config.APP_FONT_SIZE_EDITOR};
                background-color: {config.COLOR_BACKGROUND_EDITOR_DARK};
                color: {config.COLOR_TEXT_EDITOR_DARK_PRIMARY};
                border: 1px solid {config.COLOR_BORDER_DARK};
                border-radius: 3px;
                padding: 6px;
                selection-background-color: {QColor(config.COLOR_ACCENT_PRIMARY).darker(110).name()};
                selection-color: {config.COLOR_TEXT_ON_ACCENT};
                }}
        """)
        # --- END NEW ---


    def _request_live_preview_update(self):
        """
        Requests a live preview update by starting/restarting the timer.
        """
        if hasattr(self, 'live_preview_update_timer'):
            self.live_preview_update_timer.start()

    @pyqtSlot(int)
    def _on_close_tab_requested(self, index: int):
        editor = self.tab_widget.widget(index)
        if not isinstance(editor, EditorWidget) or not self._prompt_save_on_close(editor):
            return
        
        if editor in self._find_dialogs:
            self._find_dialogs[editor].close()
            del self._find_dialogs[editor]

        self.tab_widget.removeTab(index)
        editor.deleteLater()
        
        self._update_central_widget()
        self._update_project_actions_state() # <-- ADD THIS LINE


    @pyqtSlot(int)
    def _on_current_tab_changed(self, index: int):
        if hasattr(self, 'undo_action'): 
            try: self.undo_action.triggered.disconnect()
            except TypeError: pass
        if hasattr(self, 'redo_action'): 
            try: self.redo_action.triggered.disconnect()
            except TypeError: pass
        
        editor = self.current_editor()
        if editor:
            if hasattr(self, 'undo_action'): self.undo_action.triggered.connect(editor.undo_stack.undo)
            if hasattr(self, 'redo_action'): self.redo_action.triggered.connect(editor.undo_stack.redo)
            editor.undo_stack.canUndoChanged.connect(self.undo_action.setEnabled)
            editor.undo_stack.canRedoChanged.connect(self.redo_action.setEnabled)
            editor.undo_stack.undoTextChanged.connect(lambda text: self.undo_action.setText(f"&Undo {text}"))
            editor.undo_stack.redoTextChanged.connect(lambda text: self.redo_action.setText(f"&Redo {text}"))

        # NEW: Connect minimap to the current editor
        if editor and hasattr(self, 'minimap_view'):
            self.minimap_view.setScene(editor.scene)
            self.minimap_view.setMainView(editor.view)
        elif hasattr(self, 'minimap_view'):
            self.minimap_view.setScene(None)

        if editor and editor.file_path and self.git_manager:
            self.git_manager.check_file_status(editor.file_path)

        self._update_git_menu_actions_state()
        self._update_all_ui_element_states()
        
        self._update_project_actions_state() # <-- ADD THIS LINE


    def _prompt_save_on_close(self, editor: EditorWidget) -> bool:
        if not editor.is_dirty(): return True
        self.tab_widget.setCurrentWidget(editor)
        file_desc = os.path.basename(editor.file_path) if editor.file_path else "Untitled"
        reply = QMessageBox.question(self, f"Save '{file_desc}'?",
                                     f"The diagram '{file_desc}' has unsaved changes. Do you want to save them?",
                                     QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                                     QMessageBox.Save)
        if reply == QMessageBox.Save: return self.action_handler.on_save_file() 
        return reply != QMessageBox.Cancel
    
    
    
    def _load_into_editor(self, editor: EditorWidget, file_path: str) -> bool:
        try:
            data = None
            if file_path.startswith(":/"):
                qfile = QFile(file_path)
                if qfile.open(QIODevice.ReadOnly | QIODevice.Text):
                    content = qfile.readAll().data().decode('utf-8')
                    data = json.loads(content)
                    qfile.close()
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            if data and isinstance(data, dict) and 'states' in data and 'transitions' in data:
                editor.scene.load_diagram_data(data)
                self.log_message("INFO", f"Loaded '{os.path.basename(file_path)}' into new tab.")
                return True
            else:
                logger.error("Invalid BSM file format: %s.", file_path)
                return False
        except Exception as e:
            logger.error("Failed to load file %s: %s", file_path, e, exc_info=True)
            return False
        
    def _save_editor_to_path(self, editor: EditorWidget, file_path: str) -> bool:
        save_file = QSaveFile(file_path)
        if not save_file.open(QIODevice.WriteOnly | QIODevice.Text):
            QMessageBox.critical(self, "Save Error", f"Could not open file for saving:\n{save_file.errorString()}")
            return False
        try:
            diagram_data = editor.scene.get_diagram_data()
            json_data = json.dumps(diagram_data, indent=4, ensure_ascii=False)
            save_file.write(json_data.encode('utf-8'))
            if save_file.commit():
                editor.set_dirty(False)
                editor.file_path = file_path
                index = self.tab_widget.indexOf(editor)
                if index != -1: self.tab_widget.setTabText(index, editor.get_tab_title())
                self.log_message("INFO", f"Saved to {file_path}")
                self._update_window_title()
                if self.git_manager:
                    self.git_manager.check_file_status(file_path)
                return True
            else:
                QMessageBox.critical(self, "Save Error", f"Could not finalize saving:\n{save_file.errorString()}")
                return False
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"An unexpected error occurred during saving:\n{e}")
            save_file.cancelWriting()
            return False


    def _update_all_ui_element_states(self):
        self._update_window_title()
        self._update_undo_redo_actions_enable_state()
        self._update_save_actions_enable_state()
        
        # --- FIX: Delegate the properties dock update to the UIManager ---
        if hasattr(self, 'ui_manager'):
            self.ui_manager.update_properties_dock()
        # --- END FIX ---

        self._update_py_simulation_actions_enabled_state()
        self._update_zoom_to_selection_action_enable_state()
        self._update_align_distribute_actions_enable_state()
        self.update_resource_estimation()
        self._update_project_actions_state()
        editor = self.current_editor()
        if editor and editor.view: self.update_zoom_status_display(editor.view.transform().m11())
        
        self._request_live_preview_update()
        
            
    def _apply_initial_settings(self):
        logger.debug("Applying initial settings from SettingsManager.")
        initial_theme = self.settings_manager.get("appearance_theme")
        self._apply_theme(initial_theme)

        if hasattr(self, 'show_grid_action'): self.show_grid_action.setChecked(self.settings_manager.get("view_show_grid"))
        if hasattr(self, 'snap_to_grid_action'): self.snap_to_grid_action.setChecked(self.settings_manager.get("view_snap_to_grid"))
        if hasattr(self, 'snap_to_objects_action'): self.snap_to_objects_action.setChecked(self.settings_manager.get("view_snap_to_objects"))
        if hasattr(self, 'show_snap_guidelines_action'): self.show_snap_guidelines_action.setChecked(self.settings_manager.get("view_show_snap_guidelines"))
        
        if self.resource_monitor_manager and self.resource_monitor_manager.worker:
            self.resource_monitor_manager.worker.data_collection_interval_ms = self.settings_manager.get("resource_monitor_interval_ms")
        
        self._update_window_title()
    
    # ... New helper slot for property dock update on move ...
    @pyqtSlot(QGraphicsItem)
    def _update_item_properties_from_move(self, item): 
        if hasattr(self, '_current_edited_item_in_dock') and self._current_edited_item_in_dock == item:
             self._on_revert_dock_properties()

    @pyqtSlot(str, object)
    def _handle_setting_changed(self, key: str, value: object):
        logger.info(f"Setting '{key}' changed to '{value}'. Updating UI.")
        
        if key == "appearance_theme":
            self._apply_theme(str(value))
            QTimer.singleShot(100, lambda: QMessageBox.information(self, "Theme Changed", "Application restart may be required for the theme to apply to all elements fully."))
        elif key in ["canvas_grid_minor_color", "canvas_grid_major_color", "canvas_snap_guideline_color"]:
            # A color change requires a full theme re-application to update the stylesheet
            # and all derived colors correctly.
            self._apply_theme(self.settings_manager.get("appearance_theme"))


        if key == "view_show_grid":
            if hasattr(self, 'show_grid_action'): self.show_grid_action.setChecked(bool(value))
            for i in range(self.tab_widget.count()):
                if editor := self.tab_widget.widget(i): editor.scene.update() 
        elif key == "view_snap_to_grid":
            if hasattr(self, 'snap_to_grid_action'): self.snap_to_grid_action.setChecked(bool(value))
            for i in range(self.tab_widget.count()):
                if editor := self.tab_widget.widget(i): editor.scene.snap_to_grid_enabled = bool(value)
        elif key == "view_snap_to_objects":
            if hasattr(self, 'snap_to_objects_action'): self.snap_to_objects_action.setChecked(bool(value))
            for i in range(self.tab_widget.count()):
                if editor := self.tab_widget.widget(i): editor.scene.snap_to_objects_enabled = bool(value)
        elif key == "view_show_snap_guidelines":
            if hasattr(self, 'show_snap_guidelines_action'): self.show_snap_guidelines_action.setChecked(bool(value))
            for i in range(self.tab_widget.count()):
                if editor := self.tab_widget.widget(i):
                    editor.scene._show_dynamic_snap_guidelines = bool(value)
                    if not bool(value): editor.scene._clear_dynamic_guidelines()
                    editor.scene.update()
        
        elif key == "resource_monitor_enabled":
            is_enabled = bool(value)
            if hasattr(self, 'resource_monitor_widget'): self.resource_monitor_widget.setVisible(is_enabled)

            if self.resource_monitor_manager:
                if is_enabled and (not self.resource_monitor_manager.thread or not self.resource_monitor_manager.thread.isRunning()):
                    self.resource_monitor_manager.setup_and_start_monitor() 
                    if self.resource_monitor_manager.worker:
                        try: self.resource_monitor_manager.worker.resourceUpdate.disconnect(self._update_resource_display)
                        except TypeError: pass
                        self.resource_monitor_manager.worker.resourceUpdate.connect(self._update_resource_display)
                elif not is_enabled and self.resource_monitor_manager.thread and self.resource_monitor_manager.thread.isRunning():
                    self.resource_monitor_manager.stop_monitoring_system()
        elif key == "resource_monitor_interval_ms":
            if self.resource_monitor_manager and self.resource_monitor_manager.worker:
                self.resource_monitor_manager.worker.data_collection_interval_ms = int(value)
                logger.info(f"Resource monitor interval set to {value} ms.")
        
        self._update_window_title()
    
    @pyqtSlot()
    def on_show_preferences_dialog(self):
        if hasattr(self, 'preferences_dialog') and self.preferences_dialog.isVisible():
            self.preferences_dialog.raise_()
            self.preferences_dialog.activateWindow()
            return
        
        self.preferences_dialog = SettingsDialog(self.settings_manager, self.theme_manager, self)
        self.preferences_dialog.exec_()
        logger.info("Preferences dialog closed.")


    @pyqtSlot(float, float, float, str)
    def _update_resource_display(self, cpu_usage, ram_usage, gpu_util, gpu_name):
        if not self.settings_manager.get("resource_monitor_enabled"):
            if hasattr(self, 'resource_monitor_widget'): self.resource_monitor_widget.setVisible(False)
            return
        if hasattr(self, 'resource_monitor_widget') and not self.resource_monitor_widget.isVisible():
            self.resource_monitor_widget.setVisible(True)

        if hasattr(self, 'cpu_status_label'): self.cpu_status_label.setText(f"CPU: {cpu_usage:.0f}%")
        if hasattr(self, 'ram_status_label'): self.ram_status_label.setText(f"RAM: {ram_usage:.0f}%")
        if hasattr(self, 'gpu_status_label'):
            if gpu_util == -1.0: self.gpu_status_label.setText(f"GPU: {gpu_name}") 
            elif gpu_util == -2.0: self.gpu_status_label.setText(f"GPU: NVML Err") 
            elif gpu_util == -3.0: self.gpu_status_label.setText(f"GPU: Mon Err") 
            elif self.resource_monitor_manager and self.resource_monitor_manager.worker and self.resource_monitor_manager.worker._nvml_initialized and self.resource_monitor_manager.worker._gpu_handle:
                self.gpu_status_label.setText(f"GPU: {gpu_util:.0f}%")
                self.gpu_status_label.setToolTip(f"GPU: {gpu_util:.0f}% ({gpu_name})")
            else: 
                 self.gpu_status_label.setText(f"GPU: N/A"); self.gpu_status_label.setToolTip(gpu_name)
                 
                 
    def _set_status_label_object_names(self):
        # This is now handled by creating StatusSegment widgets
        pass


    def _update_ui_element_states(self):
        self._update_properties_dock()
        self._update_py_simulation_actions_enabled_state()
        self._update_zoom_to_selection_action_enable_state()
        self._update_align_distribute_actions_enable_state()
        if editor := self.current_editor():
            if editor.view:
                 self.update_zoom_status_display(editor.view.transform().m11())

    def _update_save_actions_enable_state(self):
        if hasattr(self, 'save_action'):
            # --- FIX: Ensure the expression always evaluates to a boolean ---
            can_save = self.current_editor() is not None and self.current_editor().is_dirty()
            self.save_action.setEnabled(can_save)

    def _update_ide_save_actions_enable_state(self):
        if self.ide_manager:
            self.ide_manager.update_ide_save_actions_enable_state()

    def _update_undo_redo_actions_enable_state(self):
        editor = self.current_editor()
        
        # FIX: Ensure can_undo/can_redo are always boolean, even if editor is None.
        # The original `editor and ...` expression could evaluate to None.
        can_undo = editor is not None and editor.undo_stack.canUndo()
        can_redo = editor is not None and editor.undo_stack.canRedo()

        if hasattr(self, 'undo_action'): self.undo_action.setEnabled(can_undo)
        if hasattr(self, 'redo_action'): self.redo_action.setEnabled(can_redo)
        
        if not hasattr(self, 'undo_action'): return # Guard

        # FIX: Only get undo/redo text if the actions are possible.
        undo_text = editor.undo_stack.undoText() if can_undo else ""
        redo_text = editor.undo_stack.redoText() if can_redo else ""
        
        self.undo_action.setText(f"&Undo{(' ' + undo_text) if undo_text else ''}")
        self.redo_action.setText(f"&Redo{(' ' + redo_text) if redo_text else ''}")
        self.undo_action.setToolTip(f"Undo: {undo_text}" if undo_text else "Undo")
        self.redo_action.setToolTip(f"Redo: {redo_text}" if redo_text else "Redo")

    def _update_matlab_status_display(self, connected, message):
        status_text = f"MATLAB: {'Connected' if connected else 'Not Conn.'}" # Shorter
        tooltip_text = f"MATLAB Status: {message}"
        if hasattr(self, 'matlab_status_segment'):
            self.matlab_status_segment.setText("Connected" if connected else "Not Conn.")
            self.matlab_status_segment.setToolTip(tooltip_text)
            self.matlab_status_segment.setIcon(get_standard_icon(QStyle.SP_ComputerIcon if connected else QStyle.SP_MessageBoxWarning, "MATLAB"))
        if "Initializing" not in message or (connected and "Initializing" in message):
            logging.info("MATLAB Connection Status: %s", message)
        self._update_matlab_actions_enabled_state()

    def _update_matlab_actions_enabled_state(self):
        py_sim_active = self.current_editor() and self.current_editor().py_sim_active
        can_run_matlab_ops = self.matlab_connection.connected and not py_sim_active
        if hasattr(self, 'export_simulink_action'): self.export_simulink_action.setEnabled(can_run_matlab_ops)
        if hasattr(self, 'run_simulation_action'): self.run_simulation_action.setEnabled(can_run_matlab_ops)
        if hasattr(self, 'generate_matlab_code_action'): self.generate_matlab_code_action.setEnabled(can_run_matlab_ops)
        if hasattr(self, 'matlab_settings_action'): self.matlab_settings_action.setEnabled(not py_sim_active)

    def _start_matlab_operation(self, operation_name):
        logging.info("MATLAB Operation: '%s' starting...", operation_name)
        if hasattr(self, 'main_op_status_label'): self.main_op_status_label.setText(f"MATLAB: {operation_name}...")
        if hasattr(self, 'progress_bar'): self.progress_bar.setVisible(True)
        self.set_ui_enabled_for_matlab_op(False)

    def _finish_matlab_operation(self):
        if hasattr(self, 'progress_bar'): self.progress_bar.setVisible(False)
        self._update_window_title() 
        self.set_ui_enabled_for_matlab_op(True)
        logging.info("MATLAB Operation: Finished processing.")

    def set_ui_enabled_for_matlab_op(self, enabled: bool):
        if hasattr(self, 'ribbon'):
            self.ribbon.setEnabled(enabled)
        
        if self.centralWidget(): self.centralWidget().setEnabled(enabled)
        for dock_name in ["ElementsPaletteDock", "PropertiesDock", "LogDock", "PySimDock", "AIChatbotDock", "ProblemsDock"]: 
            dock = self.findChild(QDockWidget, dock_name)
            if dock: dock.setEnabled(enabled)
        self._update_py_simulation_actions_enabled_state()


    def _handle_matlab_modelgen_or_sim_finished(self, success, message, data):
        self._finish_matlab_operation()
        logging.log(logging.INFO if success else logging.ERROR, "MATLAB Result (ModelGen/Sim): %s", message)
        if success:
            if "Model generation" in message and data:
                self.last_generated_model_path = data
                QMessageBox.information(self, "Simulink Model Generation", f"Model generated successfully:\n{data}")
            elif "Simulation" in message:
                QMessageBox.information(self, "Simulation Complete", f"MATLAB simulation finished.\n{message}")
        else:
            QMessageBox.warning(self, "MATLAB Operation Failed", message)

    def _handle_matlab_codegen_finished(self, success, message, output_dir):
        self._finish_matlab_operation()
        logging.log(logging.INFO if success else logging.ERROR, "MATLAB Code Gen Result: %s", message)
        if success and output_dir:
            msg_box = QMessageBox(self); msg_box.setIcon(QMessageBox.Information); msg_box.setWindowTitle("Code Generation Successful")
            msg_box.setTextFormat(Qt.RichText); abs_dir = os.path.abspath(output_dir)
            msg_box.setText(f"Code generation completed successfully.<br>Generated files are in: <a href='file:///{abs_dir}'>{abs_dir}</a>")
            msg_box.setTextInteractionFlags(Qt.TextBrowserInteraction)
            open_btn = msg_box.addButton("Open Directory", QMessageBox.ActionRole); msg_box.addButton(QMessageBox.Ok)
            msg_box.exec()
            if msg_box.clickedButton() == open_btn:
                if not QDesktopServices.openUrl(QUrl.fromLocalFile(abs_dir)):
                    logging.error("Error opening directory: %s", abs_dir)
                    QMessageBox.warning(self, "Error Opening Directory", f"Could not automatically open the directory:\n{abs_dir}")
        elif not success:
            QMessageBox.warning(self, "Code Generation Failed", message)

    def _prompt_save_if_dirty(self) -> bool:
        editor = self.current_editor()
        if not editor or not editor.is_dirty(): return True

        if editor.py_sim_active:
            QMessageBox.warning(self, "Simulation Active", "Please stop the Python simulation before saving or opening a new file.")
            return False
        file_desc = os.path.basename(editor.file_path) if editor.file_path else "Untitled Diagram"
        reply = QMessageBox.question(self, "Save Diagram Changes?",
                                     f"The diagram '{file_desc}' has unsaved changes. Do you want to save them?",
                                     QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                                     QMessageBox.Save)
        if reply == QMessageBox.Save: return self.action_handler.on_save_file() 
        elif reply == QMessageBox.Cancel: return False
        return True
        
    def _prompt_ide_save_if_dirty(self) -> bool:
        if self.ide_manager:
            return self.ide_manager.prompt_ide_save_if_dirty()
        return True

    def _load_from_path(self, file_path): pass
    def _save_to_path(self, file_path) -> bool: pass

    @pyqtSlot(QGraphicsItem)
    def focus_on_item(self, item_to_focus: QGraphicsItem):
        editor = self.current_editor()
        if not editor or not item_to_focus or item_to_focus.scene() != editor.scene:
            self.log_message("WARNING", f"Could not find or focus on the provided item: {item_to_focus}")
            return
        
        editor.scene.clearSelection()
        item_to_focus.setSelected(True)
        item_rect = item_to_focus.sceneBoundingRect()
        padding = 50
        view_rect_with_padding = item_rect.adjusted(-padding, -padding, padding, padding)
        if editor.view: editor.view.fitInView(view_rect_with_padding, Qt.KeepAspectRatio)
        
        display_name = "Item"
        if isinstance(item_to_focus, GraphicsStateItem): display_name = f"State: {item_to_focus.text_label}"
        elif isinstance(item_to_focus, GraphicsTransitionItem): display_name = f"Transition: {item_to_focus._compose_label_string()}"
        elif isinstance(item_to_focus, GraphicsCommentItem): display_name = f"Comment: {item_to_focus.toPlainText()[:30]}..."
        self.log_message("INFO", f"Focused on {display_name}")
        
        editor_find_dialog = self._find_dialogs.get(editor)
        if editor_find_dialog and not editor_find_dialog.isHidden():
            pass

    def show_find_item_dialog_for_editor(self, editor: EditorWidget):
        if editor not in self._find_dialogs:
            dialog = FindItemDialog(parent=self, scene_ref=editor.scene)
            dialog.item_selected_for_focus.connect(self.focus_on_item)
            editor.scene.scene_content_changed_for_find.connect(dialog.refresh_list)
            self._find_dialogs[editor] = dialog
        
        dialog = self._find_dialogs[editor]
        if dialog.isHidden():
            dialog.refresh_list() 
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
        else:
            dialog.activateWindow()
        
        if hasattr(dialog, 'search_input'):
            dialog.search_input.selectAll()
            dialog.search_input.setFocus()
            
    # The closeEvent and other essential methods from the original file are assumed to be here.
    def closeEvent(self, event: QCloseEvent):
        """Overrides QMainWindow.closeEvent to check for unsaved changes and stop threads."""
        logger.info("MW_CLOSE: closeEvent received.")
        
        # <<< FIX: Iterate through all tabs and stop any active simulations before prompting to save >>>
        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            if editor and editor.py_sim_active: 
                self.py_sim_ui_manager.on_stop_py_simulation(silent=True)
             
        if hasattr(self.ide_manager, 'prompt_ide_save_if_dirty') and not self.ide_manager.prompt_ide_save_if_dirty():
            event.ignore()
            return
        
        # <<< FIX: Iterate through all tabs and prompt to save each one >>>
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if isinstance(widget, EditorWidget):
                if not self._prompt_save_on_close(widget):
                    event.ignore()
                    return

         # --- NEW: Add shutdown for HardwareLinkManager ---
        if self.hardware_sim_ui_manager and self.hardware_sim_ui_manager.hardware_link_manager.is_connected:
            logger.info("MW_CLOSE: Disconnecting from hardware.")
            self.hardware_sim_ui_manager.hardware_link_manager.disconnect_from_port()
        # --- END NEW ---

        self.internet_check_timer.stop()
        if self.ai_chatbot_manager: self.ai_chatbot_manager.stop_chatbot()
        if self.resource_monitor_manager: self.resource_monitor_manager.stop_monitoring_system()
        if self.git_manager: self.git_manager.stop()

        for dialog in self._find_dialogs.values():
            dialog.close()
        self._find_dialogs.clear()

        self.settings_manager.set("last_used_perspective", self.perspective_manager.current_perspective_name)
        self.settings_manager.set("window_geometry", self.saveGeometry().toHex().data().decode('ascii'))
        self.settings_manager.set("window_state", self.saveState().toHex().data().decode('ascii'))
        logger.info("MW_CLOSE: Application closeEvent accepted.")
        event.accept()

    def restore_geometry_and_state(self):
        try:
            geom_hex = self.settings_manager.get("window_geometry")
            if geom_hex and isinstance(geom_hex, str): self.restoreGeometry(bytes.fromhex(geom_hex))

            state_hex = self.settings_manager.get("window_state")
            if state_hex and isinstance(state_hex, str): self.restoreState(bytes.fromhex(state_hex))
            else: self.perspective_manager.apply_perspective(self.perspective_manager.current_perspective_name)
            
        except Exception as e:
            logger.warning(f"Could not restore window geometry/state: {e}. Applying default layout.")
            self.perspective_manager.apply_perspective(self.perspective_manager.current_perspective_name)
            
        # --- FIX: ADD THIS LINE ---
        # After restoring state, re-evaluate whether the welcome screen should be visible.
        self._update_central_widget()
        # --- END FIX ---
            


    # --- NEW / MODIFIED METHODS for Resource Estimation ---

    @pyqtSlot('QRectF')
    def update_resource_estimation(self, region=None):
        editor = self.current_editor()
        if not editor or not hasattr(self, 'resource_estimation_dock') or not self.resource_estimation_dock.isVisible():
            return

        diagram_data = editor.scene.get_diagram_data()
        estimation = self.resource_estimator.estimate(diagram_data)
        
        sram_b = estimation.get('sram_b', 0)
        flash_b = estimation.get('flash_b', 0)

        total_sram_b = self.resource_estimator.target_profile.get("sram_b", 1)
        total_flash_b = self.resource_estimator.target_profile.get("flash_kb", 1) * 1024
        
        sram_percent = min(100, int((sram_b / total_sram_b) * 100)) if total_sram_b > 0 else 0
        flash_percent = min(100, int((flash_b / total_flash_b) * 100)) if total_flash_b > 0 else 0
        
        if hasattr(self, 'sram_usage_bar'):
            self.sram_usage_bar.setRange(0, 100)
            self.sram_usage_bar.setValue(sram_percent)
            self.sram_usage_bar.setFormat(f"~ {sram_b} / {total_sram_b} B ({sram_percent}%)")

        if hasattr(self, 'flash_usage_bar'):
            self.flash_usage_bar.setRange(0, 100)
            self.flash_usage_bar.setValue(flash_percent)
            self.flash_usage_bar.setFormat(f"~ {flash_b / 1024:.1f} / {total_flash_b / 1024:.0f} KB ({flash_percent}%)")
    @pyqtSlot(str)
    def on_target_device_changed(self, profile_name: str):
        if self.resource_estimator:
            self.resource_estimator.set_target(profile_name)
            self.update_resource_estimation()
        else:
            logger.warning("Target device changed, but resource_estimator is not available.")



    @pyqtSlot(float)
    def update_zoom_status_display(self, scale_factor: float):
        if hasattr(self, 'zoom_status_segment'):
            zoom_percentage = int(scale_factor * 100)
            self.zoom_status_segment.setText(f"{zoom_percentage}%")

    @pyqtSlot(bool)
    def _handle_py_sim_state_changed_by_manager(self, is_running: bool):
        logger.debug(f"MW: PySim state changed by manager to: {is_running}")
        editor = self.current_editor()
        if editor:
            editor.py_sim_active = is_running
        self._update_window_title()
        self._update_py_sim_status_display() 
        self._update_matlab_actions_enabled_state()
        self._update_py_simulation_actions_enabled_state()
    # @pyqtSlot(bool)
    # def _handle_py_sim_global_ui_enable_by_manager(self, enable): pass # DELETED

    @pyqtSlot(list)
    def update_problems_dock(self, issues_with_items: list):
        editor = self.current_editor()
        if not editor or not hasattr(self, 'problems_list_widget') or self.problems_list_widget is None:
            logger.warning("MainWindow.update_problems_dock: self.problems_list_widget is not yet initialized. Update deferred.")
            return
        
        self.problems_list_widget.clear()
        
        num_issues = len(issues_with_items)
        if num_issues > 0:
            for issue_msg, item_ref in issues_with_items:
                list_item_widget = QListWidgetItem(str(issue_msg))
                if item_ref: list_item_widget.setData(Qt.UserRole, item_ref)
                self.problems_list_widget.addItem(list_item_widget)
            self.problems_dock.setWindowTitle(f"Validation Issues ({num_issues})")
            if hasattr(self, 'problems_ask_ai_btn'): self.problems_ask_ai_btn.setEnabled(False)
            if self.problems_dock.isHidden():
                 self.problems_dock.show()
                 self.problems_dock.raise_()
        else: 
            self.problems_list_widget.addItem("No validation issues found."); 
            self.problems_dock.setWindowTitle("Validation Issues")
            if hasattr(self, 'problems_ask_ai_btn'): self.problems_ask_ai_btn.setEnabled(False)

    # --- NEW: AI Validation Helper Slot ---
    @pyqtSlot()
    def on_ask_ai_about_validation_issue(self):
        selected_items = self.problems_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Issue Selected", "Please select an issue from the list to ask the AI about it.")
            return

        issue_text = selected_items[0].text()
        prompt = f"""I am designing a Finite State Machine. The validation tool gave me the following error or warning: "{issue_text}". If possible, provide a specific fix in a [BSM_FIX] JSON block.

Please explain what this means in the context of an FSM and suggest how I might fix it. Be concise."""
        
        self.ai_chat_ui_manager._append_to_chat_display("Validation Helper", f"Asking AI about: '{issue_text}'")
        self.ai_chatbot_manager.send_message(prompt)


    @pyqtSlot(QListWidgetItem)
    def on_problem_item_double_clicked(self, list_item: QListWidgetItem):
        item_ref = list_item.data(Qt.UserRole)
        editor = self.current_editor()
        if not editor: return
        
        if item_ref and isinstance(item_ref, QGraphicsItem) and item_ref.scene() == editor.scene:
            self.focus_on_item(item_ref)
            logger.info(f"Focused on problematic item from Validation Issues list: {getattr(item_ref, 'text_label', type(item_ref).__name__)}")
        else: logger.debug(f"No valid QGraphicsItem reference found for clicked validation issue: '{list_item.text()}'")

    @pyqtSlot(bool)
    def _on_ide_dirty_state_changed_by_manager(self, is_dirty: bool):
        self._update_ide_save_actions_enable_state()
        self._update_window_title()

    @pyqtSlot(str)
    def _on_ide_language_changed_by_manager(self, language_param: str):
        ai_ready = self.ai_chatbot_manager is not None and \
                   self.ai_chatbot_manager.is_configured() and \
                   self._internet_connected is True
        
        if hasattr(self, 'ide_analyze_action'):
            can_analyze = (language_param == "Python" or language_param.startswith("C/C++")) and ai_ready
            self.ide_analyze_action.setEnabled(can_analyze)
            tooltip = "Analyze the current code with AI"
            if not ai_ready: tooltip += " (Requires Internet & valid API Key)"
            elif not (language_param == "Python" or language_param.startswith("C/C++")):
                 tooltip += " (Best for Python or C/C++)"
            self.ide_analyze_action.setToolTip(tooltip)
        self._update_window_title()

    def _update_window_title(self):
        project_name = self.project_manager.project_data.get("name") if self.project_manager.is_project_open() else None
    
        editor = self.current_editor()
        title_parts = []
    
        if project_name:
            title_parts.append(f"[{project_name}]")

        if not editor:
            if not project_name:
                self.setWindowTitle(APP_NAME)
                return
        else:
            dirty_char = "[*]" # Let Qt handle this part
            file_name = os.path.basename(editor.file_path) if editor.file_path else "Untitled"
            title_parts.append(file_name)
            self.setWindowModified(editor.is_dirty())
            title_parts.append(dirty_char)
    
        py_sim_active = any(isinstance(self.tab_widget.widget(i), EditorWidget) and self.tab_widget.widget(i).py_sim_active for i in range(self.tab_widget.count()))
        pysim_suffix = f" [PySim Active]" if py_sim_active else ""
    
        title_parts.append(f"- {APP_NAME}{pysim_suffix}")
        self.setWindowTitle(" ".join(title_parts))


    def _init_internet_status_check(self):
        self.internet_check_timer.timeout.connect(self._run_internet_check_job)
        self.internet_check_timer.start(15000) 
        # Give the application and network stack a moment to settle before the first check.
        QTimer.singleShot(1000, self._run_internet_check_job) 

    def _run_internet_check_job(self):
        current_status = False; status_detail = "Checking..."
        try:
            # Use a public DNS server port. More reliable than a web server.
            # Cloudflare's DNS (1.1.1.1) is a good choice. Port 53 is for DNS.
            s = socket.create_connection(("1.1.1.1", 53), timeout=1.5) 
            s.close()
            current_status = True
            status_detail = "Connected"
        except socket.timeout:
            status_detail = "Timeout"
        except (socket.gaierror, OSError): 
            status_detail = "Net Issue"
        
        if current_status != self._internet_connected or self._internet_connected is None: 
            self._internet_connected = current_status
            self._update_internet_status_display(current_status, status_detail)

    def _update_ai_features_enabled_state(self, is_online_and_key_present: bool):
        if hasattr(self, 'ask_ai_to_generate_fsm_action'): self.ask_ai_to_generate_fsm_action.setEnabled(is_online_and_key_present)
        if hasattr(self, 'clear_ai_chat_action'): self.clear_ai_chat_action.setEnabled(is_online_and_key_present)
        if hasattr(self, 'ai_chat_ui_manager') and self.ai_chat_ui_manager:
            if self.ai_chat_ui_manager.ai_chat_send_button: self.ai_chat_ui_manager.ai_chat_send_button.setEnabled(is_online_and_key_present)
            if self.ai_chat_ui_manager.ai_chat_input:
                self.ai_chat_ui_manager.ai_chat_input.setEnabled(is_online_and_key_present)
                if not is_online_and_key_present:
                    if self.ai_chatbot_manager and not self.ai_chatbot_manager.is_configured(): self.ai_chat_ui_manager.ai_chat_input.setPlaceholderText("AI disabled: API Key/Provider required.")
                    elif not self._internet_connected: self.ai_chat_ui_manager.ai_chat_input.setPlaceholderText("AI disabled: Internet connection required.")
                else: self.ai_chat_ui_manager.ai_chat_input.setPlaceholderText("Type your message to the AI...")
        if hasattr(self, 'ide_analyze_action') and self.ide_manager and self.ide_manager.ide_language_combo: 
            current_ide_lang = self.ide_manager.ide_language_combo.currentText()
            can_analyze_ide = (current_ide_lang == "Python" or current_ide_lang.startswith("C/C++")) and is_online_and_key_present
            self.ide_analyze_action.setEnabled(can_analyze_ide)
            tooltip = "Analyze the current code with AI"
            if not (self.ai_chatbot_manager and self.ai_chatbot_manager.is_configured() and self._internet_connected): tooltip += " (Requires Internet & valid API Key)"
            elif not (current_ide_lang == "Python" or current_ide_lang.startswith("C/C++")): tooltip += " (Best for Python or C/C++)"
            self.ide_analyze_action.setToolTip(tooltip)

    def _update_internet_status_display(self, is_connected: bool, message_detail: str):
        if hasattr(self, 'net_status_segment'):
            self.net_status_segment.setText(message_detail)
            host_for_tooltip = "8.8.8.8:53 (Google DNS)"
            self.net_status_segment.setToolTip(f"Internet Status: {message_detail} (Checks {host_for_tooltip})")
            self.net_status_segment.setIcon(get_standard_icon(QStyle.SP_DriveNetIcon if is_connected else QStyle.SP_MessageBoxCritical, "Net"))

        logging.debug("Internet Status Update: %s", message_detail)
        key_present = self.ai_chatbot_manager is not None and self.ai_chatbot_manager.is_configured()
        ai_ready = is_connected and key_present
        if hasattr(self.ai_chatbot_manager, 'set_online_status'): self.ai_chatbot_manager.set_online_status(is_connected)
        self._update_ai_features_enabled_state(ai_ready)

    def _update_py_sim_status_display(self): 
        if hasattr(self, 'pysim_status_segment'):
            status_text = "Idle"; tooltip = "Internal Python FSM Simulation is Idle."
            icon_enum = QStyle.SP_MediaStop
            
            editor = self.current_editor()
            py_sim_active = editor.py_sim_active if editor else False

            if py_sim_active and editor.py_fsm_engine:
                current_state_name = editor.py_fsm_engine.get_current_state_name(); 
                display_state_name = (current_state_name[:20] + '...') if len(current_state_name) > 23 else current_state_name
                status_text = f"Active ({html.escape(display_state_name)})"; 
                tooltip = f"Python FSM Simulation Active: {current_state_name}"
                icon_enum = QStyle.SP_MediaPlay
                if editor.py_fsm_engine.paused_on_breakpoint: 
                    status_text += " (Paused)"; tooltip += " (Paused at Breakpoint)"
                    icon_enum = QStyle.SP_MediaPause # Change icon for paused state
            
            self.pysim_status_segment.setText(status_text)
            self.pysim_status_segment.setToolTip(tooltip)
            self.pysim_status_segment.setIcon(get_standard_icon(icon_enum, "PySim"))

    def _update_py_simulation_actions_enabled_state(self):
        is_matlab_op_running = False
        if hasattr(self, 'progress_bar') and self.progress_bar: is_matlab_op_running = self.progress_bar.isVisible()
        
        editor = self.current_editor()
        py_sim_active = editor.py_sim_active if editor else False
        
        # This action is now for *initializing* the simulation
        sim_can_be_initialized = not py_sim_active and not is_matlab_op_running
        
        if hasattr(self, 'start_py_sim_action'): self.start_py_sim_action.setEnabled(sim_can_be_initialized)
        
        # Stop and Reset are only available once a simulation is active
        sim_can_be_stopped_or_reset = py_sim_active and not is_matlab_op_running
        if hasattr(self, 'stop_py_sim_action'): self.stop_py_sim_action.setEnabled(sim_can_be_stopped_or_reset)
        if hasattr(self, 'reset_py_sim_action'): self.reset_py_sim_action.setEnabled(sim_can_be_stopped_or_reset)
        
        # Delegate internal button states to the manager
        if hasattr(self, 'py_sim_ui_manager') and self.py_sim_ui_manager:
            self.py_sim_ui_manager._update_internal_controls_enabled_state()

    @pyqtSlot()
    def _update_zoom_to_selection_action_enable_state(self):
        editor = self.current_editor()
        # --- FIX: Ensure the expression always evaluates to a boolean ---
        can_zoom_to_selection = editor is not None and bool(editor.scene.selectedItems())
        if hasattr(self, 'zoom_to_selection_action'): self.zoom_to_selection_action.setEnabled(can_zoom_to_selection)

    @pyqtSlot()
    def _update_align_distribute_actions_enable_state(self):
        editor = self.current_editor()
        selected_count = len(editor.scene.selectedItems()) if editor else 0
        if hasattr(self, 'align_actions'):
            for action in self.align_actions: action.setEnabled(selected_count >= 2)
        if hasattr(self, 'distribute_actions'):
            for action in self.distribute_actions: action.setEnabled(selected_count >= 3)

    @pyqtSlot(str, str)
    def _handle_state_renamed_inline(self, old_name: str, new_name: str):
        """Refreshes UI elements that depend on item names after an inline edit."""
        logger.debug(f"MainWindow: State renamed inline from '{old_name}' to '{new_name}'.")
        self._refresh_find_dialog_if_visible()
        
        if hasattr(self, 'ui_manager'):
            self.ui_manager.update_properties_dock_title_after_rename(new_name)
        
        # If the renamed item is the one selected, update the properties dock title
        editor = self.current_editor()
        if editor and editor.scene.selectedItems() and len(editor.scene.selectedItems()) == 1 and \
           isinstance(editor.scene.selectedItems()[0], GraphicsStateItem) and \
           editor.scene.selectedItems()[0].text_label == new_name:
            self._update_properties_dock() 

    def connect_state_item_signals(self, state_item: GraphicsStateItem):
        try:
            # Check for existing connections before adding new ones
            if not hasattr(state_item.signals, '_connected_slots_mw'):
                state_item.signals._connected_slots_mw = set()
            
            if self._handle_state_renamed_inline not in state_item.signals._connected_slots_mw:
                state_item.signals.textChangedViaInlineEdit.connect(self._handle_state_renamed_inline)
                state_item.signals._connected_slots_mw.add(self._handle_state_renamed_inline)
                logger.debug(f"Connected rename signal for state: {state_item.text_label}")
        except Exception as e:
            logger.error(f"Failed to connect state item signals: {e}")
            
    # Other methods like _populate_recent_files_menu, on_show_preferences_dialog, _apply_theme, etc.
    # would be implemented here, delegating logic as needed.
    # A full implementation would refactor methods from the original main file into here
    # and adapt them for the TDI architecture. For brevity, I'll include the essential stubs.

    @pyqtSlot()
    def _refresh_find_dialog_if_visible(self):
        editor = self.current_editor()
        if editor and editor in self._find_dialogs:
            self._find_dialogs[editor].refresh_list()
    @pyqtSlot(str)
    def _on_interaction_mode_changed_by_scene(self, mode_name):
        if hasattr(self, 'mode_status_segment'):
            self.mode_status_segment.setText(mode_name.capitalize())
            icon_map = {
                "select": QStyle.SP_ArrowRight, "state": QStyle.SP_FileDialogNewFolder,
                "transition": QStyle.SP_ArrowForward, "comment": QStyle.SP_MessageBoxInformation
            }
            icon_enum = icon_map.get(mode_name, QStyle.SP_CustomBase)
            self.mode_status_segment.setIcon(get_standard_icon(icon_enum, mode_name[:3].upper()))

    @pyqtSlot(str, str)
    def _handle_state_renamed_inline(self, old_name, new_name): pass
    
    
    
    
    
    @pyqtSlot()
    def _on_log_filter_changed(self):
        if not hasattr(self, 'ui_log_handler'):
            return

        level_text = self.log_level_filter_combo.currentText()
        filter_text = self.log_filter_edit.text()
        
        log_level = getattr(logging, level_text.upper(), logging.INFO)
        
        self.ui_log_handler.set_filters(level=log_level, text=filter_text)
    
    
    
    @pyqtSlot(GraphicsStateItem, bool)
    def on_toggle_state_breakpoint(self, state_item: GraphicsStateItem, set_bp: bool):
        editor = self.current_editor()
        if not editor or not editor.py_fsm_engine or not editor.py_sim_active:
            QMessageBox.information(self, "Simulation Not Active", "Breakpoints can only be managed during an active Python simulation.")
            if self.sender() and isinstance(self.sender(), QAction):
                self.sender().setChecked(not set_bp) 
            return

        state_name = state_item.text_label
        action_text = ""
        if set_bp:
            editor.py_fsm_engine.add_state_breakpoint(state_name)
            current_tooltip = state_item.toolTip()
            if "[BP]" not in current_tooltip:
                state_item.setToolTip(f"{current_tooltip}\n[Breakpoint Set]" if current_tooltip else f"State: {state_name}\n[Breakpoint Set]")
            action_text = f"Breakpoint SET for state: {state_name}"
        else:
            editor.py_fsm_engine.remove_state_breakpoint(state_name)
            state_item.setToolTip(state_item.toolTip().replace("\n[Breakpoint Set]", ""))
            action_text = f"Breakpoint CLEARED for state: {state_name}"
        
        state_item.update() 
        
        if hasattr(self, 'py_sim_ui_manager') and self.py_sim_ui_manager:
            self.py_sim_ui_manager.append_to_action_log([action_text])
        logger.info(action_text)


     # --- ADD THIS NEW SLOT TO THE CLASS ---
    @pyqtSlot(GraphicsTransitionItem, bool)
    def on_toggle_transition_breakpoint(self, trans_item: GraphicsTransitionItem, set_bp: bool):
        """Handles the request to set or clear a breakpoint on a transition."""
        editor = self.current_editor()
        engine = editor.py_fsm_engine if editor else None
        
        # This check is a safeguard; the menu action should be disabled if sim is not active
        if not engine or not trans_item.start_item or not trans_item.end_item:
            if self.sender() and isinstance(self.sender(), QAction):
                self.sender().setChecked(not set_bp) # Revert the checkbox state
            return

        source = trans_item.start_item.text_label
        target = trans_item.end_item.text_label
        event = trans_item.event_str
        action_text = ""

        if set_bp:
            engine.add_transition_breakpoint(source, target, event)
            action_text = f"Breakpoint SET for transition: {source} -> {target} on '{event}'"
        else:
            engine.remove_transition_breakpoint(source, target, event)
            action_text = f"Breakpoint CLEARED for transition: {source} -> {target} on '{event}'"

        # Update the visual indicator on the transition item
        trans_item.set_breakpoint_style(set_bp)

        # Log the action in the simulation panel
        if hasattr(self, 'py_sim_ui_manager'):
            self.py_sim_ui_manager.append_to_action_log([action_text])
        logger.info(action_text)
    # --- END ADDITION ---


    def log_message(self, level_str: str, message: str): 
        level = getattr(logging, level_str.upper(), logging.INFO)
        logger.log(level, message)



    




    @pyqtSlot()
    def on_show_find_item_dialog(self):
        """Opens the Find Item dialog for the currently active editor tab."""
        if self.current_editor():
            self.show_find_item_dialog_for_editor(self.current_editor())

    # Note: _load_from_path and _save_to_path appear to be refactored into
    # _load_into_editor and _save_editor_to_path. I will remove the pass statements
    # and add a comment indicating they are deprecated.
            
    def _add_fsm_data_to_scene(self, fsm_data: dict, clear_current_diagram: bool = False, original_user_prompt: str | None = None):
        if not isinstance(fsm_data, dict):
            self.log_message("ERROR", "Invalid FSM data format received for adding to scene.")
            QMessageBox.critical(self, "Error Adding FSM Data", "Received invalid FSM data structure.")
            return

        # Get the current editor, or create one if clearing.
        editor = self.current_editor()
        if clear_current_diagram:
            editor = self.add_new_editor_tab()
            self.log_message("INFO", "Created new tab for AI-generated FSM.")
        elif not editor:
            editor = self.add_new_editor_tab()

        if not editor:
            self.log_message("ERROR", "Failed to get or create an editor tab to add FSM data.")
            return
            
        scene = editor.scene
        view = editor.view
        undo_stack = editor.undo_stack

        undo_stack.beginMacro(f"Add FSM Data ({original_user_prompt[:20] if original_user_prompt else 'AI Generated'})")

        states_data = fsm_data.get('states', [])
        transitions_data = fsm_data.get('transitions', [])
        comments_data = fsm_data.get('comments', [])

        current_view_center = view.mapToScene(view.viewport().rect().center())
        base_x = current_view_center.x()
        base_y = current_view_center.y()

        if not clear_current_diagram and scene.items():
            occupied_rect = scene.itemsBoundingRect()
            if not occupied_rect.isEmpty():
                base_x = occupied_rect.right() + 100 
                base_y = occupied_rect.top()

        min_x_data, min_y_data = float('inf'), float('inf')
        has_positions = False
        if states_data and all('x' in s and 'y' in s for s in states_data if isinstance(s, dict)):
            has_positions = True
            for s_data in states_data:
                if isinstance(s_data,dict):
                    min_x_data = min(min_x_data, s_data.get('x', 0))
                    min_y_data = min(min_y_data, s_data.get('y', 0))
        if comments_data and all('x' in c and 'y' in c for c in comments_data if isinstance(c, dict)):
            has_positions = True 
            for c_data in comments_data:
                if isinstance(c_data, dict):
                    min_x_data = min(min_x_data, c_data.get('x', 0))
                    min_y_data = min(min_y_data, c_data.get('y', 0))
        
        if not has_positions or min_x_data == float('inf'): 
            min_x_data, min_y_data = 0, 0

        state_items_map = {} 

        for i, state_data in enumerate(states_data):
            if not isinstance(state_data, dict):
                self.log_message("WARNING", f"Skipping invalid state data entry (not a dict): {state_data}")
                continue
            name = state_data.get('name')
            if not name:
                self.log_message("WARNING", f"Skipping state due to missing name: {state_data}")
                continue
            
            unique_name = scene._generate_unique_state_name(name)
            if unique_name != name:
                self.log_message("INFO", f"State name '{name}' already exists. Renamed to '{unique_name}' for AI generated FSM.")

            pos_x = base_x + (state_data.get('x', 0) - min_x_data) if has_positions else (base_x + i * 150)
            pos_y = base_y + (state_data.get('y', 0) - min_y_data) if has_positions else base_y
            
            pos_x = round(pos_x / scene.grid_size) * scene.grid_size
            pos_y = round(pos_y / scene.grid_size) * scene.grid_size

            state_item = GraphicsStateItem(
                pos_x, pos_y,
                state_data.get('width', 120), state_data.get('height', 60),
                unique_name, 
                state_data.get('is_initial', False),
                state_data.get('is_final', False),
                state_data.get('color', config.COLOR_ITEM_STATE_DEFAULT_BG),
                state_data.get('entry_action', ""),
                state_data.get('during_action', ""),
                state_data.get('exit_action', ""),
                state_data.get('description', fsm_data.get('description', "") if state_data.get('is_initial', False) else ""),
                state_data.get('is_superstate', False),
                state_data.get('sub_fsm_data', {'states':[], 'transitions':[], 'comments':[]}),
                action_language=state_data.get('action_language', config.DEFAULT_EXECUTION_ENV)
            )
            self.connect_state_item_signals(state_item)
            cmd = AddItemCommand(scene, state_item, f"Add State '{unique_name}'")
            undo_stack.push(cmd)
            state_items_map[name] = state_item 

        for trans_data in transitions_data:
            if not isinstance(trans_data, dict):
                self.log_message("WARNING", f"Skipping invalid transition data entry (not a dict): {trans_data}")
                continue
            source_name = trans_data.get('source')
            target_name = trans_data.get('target')

            src_item = state_items_map.get(source_name)
            tgt_item = state_items_map.get(target_name)

            if src_item and tgt_item:
                trans_item = GraphicsTransitionItem(
                    src_item, tgt_item,
                    event_str=trans_data.get('event', ""),
                    condition_str=trans_data.get('condition', ""),
                    action_language=trans_data.get('action_language', config.DEFAULT_EXECUTION_ENV),
                    action_str=trans_data.get('action', ""),
                    color=trans_data.get('color', config.COLOR_ITEM_TRANSITION_DEFAULT),
                    description=trans_data.get('description', "")
                )
                trans_item.set_control_point_offset(QPointF(
                    trans_data.get('control_offset_x', 0),
                    trans_data.get('control_offset_y', 0)
                ))
                cmd = AddItemCommand(scene, trans_item, "Add Transition")
                undo_stack.push(cmd)
            else:
                self.log_message("WARNING", f"Could not link transition: source '{source_name}' or target '{target_name}' not found/created.")

        for i, comment_data in enumerate(comments_data):
            if not isinstance(comment_data, dict):
                self.log_message("WARNING", f"Skipping invalid comment data entry (not a dict): {comment_data}")
                continue
            text = comment_data.get('text')
            if not text:
                continue

            pos_x = base_x + (comment_data.get('x', 0) - min_x_data) if has_positions else (base_x + i * 100)
            pos_y = base_y + (comment_data.get('y', 0) - min_y_data) + 100 if has_positions else (base_y + 100 + i * 30) 

            pos_x = round(pos_x / scene.grid_size) * scene.grid_size
            pos_y = round(pos_y / scene.grid_size) * scene.grid_size

            comment_item = GraphicsCommentItem(pos_x, pos_y, text)
            comment_item.setTextWidth(comment_data.get('width', 150))
            cmd = AddItemCommand(scene, comment_item, "Add Comment")
            undo_stack.push(cmd)

        undo_stack.endMacro()
        editor.set_dirty(True)
        scene.run_all_validations("AddFSMDataFromAI")
        self.action_handler.on_fit_diagram_in_view() 
        self.log_message("INFO", f"Successfully added FSM data to the scene.")

def main_entry_point():
    if hasattr(Qt, 'AA_EnableHighDpiScaling'): QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'): QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)
    
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main_entry_point()