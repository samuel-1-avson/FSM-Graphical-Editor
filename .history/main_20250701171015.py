# fsm_designer_project/main.py

import sys
import os

# This block ensures the application can be run directly as a script
# from the project root, making imports work correctly.
if __name__ == '__main__' and __package__ is None:
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_script_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    # Re-launch the script using the correct module path
    import fsm_designer_project.main
    sys.exit(fsm_designer_project.main.main_entry_point())

import json
import logging
import socket
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QSize, QIODevice, QFile, QSaveFile
from PyQt5.QtGui import QIcon, QKeySequence, QCloseEvent
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QTabWidget, QGraphicsItem

# Local application imports (organized by function)
from . import config
from . import resources_rc
from .logging_setup import setup_global_logging
from .settings_manager import SettingsManager
from .theme_manager import ThemeManager
from .snippet_manager import CustomSnippetManager
from .action_handlers import ActionHandler
from .ui_manager import UIManager, WelcomeWidget
from .perspective_manager import PerspectiveManager
from .resource_monitor import ResourceMonitorManager
from .editor_widget import EditorWidget
from .git_manager import GitManager
from .matlab_integration import MatlabConnection
from .ai_chatbot import AIChatbotManager, AIChatUIManager
from .ui_py_simulation_manager import PySimulationUIManager
from .ide_manager import IDEManager
from .dialogs import FindItemDialog
from .graphics_items import GraphicsStateItem

# Check if Qt resources were compiled and imported successfully
RESOURCES_AVAILABLE = 'resources_rc' in sys.modules
if not RESOURCES_AVAILABLE:
    print("WARNING: resources_rc.py not found. Icons and bundled files might be missing.")

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    The main window of the FSM Designer application.

    This class acts as the central coordinator, initializing and connecting various
    manager components (UI, Actions, Settings, etc.) that handle the application's
    functionality. It manages top-level state, such as the editor tabs and window
    geometry, but delegates detailed logic to specialized managers.
    """
    # Expose this flag for utils.py to check if resources can be accessed
    RESOURCES_AVAILABLE = RESOURCES_AVAILABLE

    # Constants for default perspective names
    PERSPECTIVE_DESIGN_FOCUS = "Design Focus"
    PERSPECTIVE_SIMULATION_FOCUS = "Simulation Focus"
    PERSPECTIVE_IDE_FOCUS = "IDE Focus"
    PERSPECTIVE_AI_FOCUS = "AI Focus"
    DEFAULT_PERSPECTIVES_ORDER = [
        PERSPECTIVE_DESIGN_FOCUS, PERSPECTIVE_SIMULATION_FOCUS,
        PERSPECTIVE_IDE_FOCUS, PERSPECTIVE_AI_FOCUS
    ]

    def __init__(self):
        super().__init__()

        # 1. Initialize Core, Non-UI Managers first
        if not hasattr(QApplication.instance(), 'settings_manager'):
            QApplication.instance().settings_manager = SettingsManager(app_name=config.APP_NAME)
        self.settings_manager = QApplication.instance().settings_manager
        self.theme_manager = ThemeManager(app_name=config.APP_NAME)
        self.custom_snippet_manager = CustomSnippetManager(app_name=config.APP_NAME)
        self.git_manager = GitManager(self)
        self.matlab_connection = MatlabConnection()
        self.action_handler = ActionHandler(self)
        self._find_dialogs = {}

        # 2. Setup the UI structure using the UIManager
        self.ui_manager = UIManager(self)
        self.ui_manager.setup_ui()  # Creates menus, toolbars, docks, etc.

        # 3. Initialize UI-Dependent Managers
        self.perspective_manager = PerspectiveManager(self, self.settings_manager)
        self.resource_monitor_manager = ResourceMonitorManager(self, self.settings_manager)
        self.ai_chatbot_manager = AIChatbotManager(self)
        self.ai_chat_ui_manager = AIChatUIManager(self)
        self.py_sim_ui_manager = PySimulationUIManager(self)
        self.ide_manager = IDEManager(self)

        # 4. Setup Central Widget and Logging
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.setDocumentMode(True)  # Modern browser-style tabs
        self.welcome_widget = WelcomeWidget(self)
        self._update_central_widget()
        setup_global_logging(self.log_output) # Log dock was created by UIManager

        # 5. Connect all signals and apply initial settings
        self.ui_manager.populate_dynamic_docks() # Populate docks with content from their managers
        self._connect_signals()
        self._apply_initial_settings()
        self.restore_geometry_and_state()

        # 6. Start background tasks
        self._internet_connected: bool | None = None
        self.internet_check_timer = QTimer(self)
        self._init_internet_status_check()
        if self.settings_manager.get("resource_monitor_enabled"):
            self.resource_monitor_manager.setup_and_start_monitor()

        # Initial UI state update after a short delay
        QTimer.singleShot(50, lambda: self.perspective_manager.apply_perspective(self.perspective_manager.current_perspective_name))
        logger.info(f"{config.APP_NAME} v{config.APP_VERSION} initialization complete.")

    def _connect_signals(self):
        """Connects signals from managers and UI components to appropriate slots."""
        logger.debug("Connecting application-level signals...")

        self.action_handler.connect_actions()
        self.preferences_action.triggered.connect(self.on_show_preferences_dialog)
        self.tab_widget.currentChanged.connect(self._on_current_tab_changed)
        self.tab_widget.tabCloseRequested.connect(self._on_close_tab_requested)

        # Connect dock signals
        self.ui_manager.connect_dock_signals()

        # Connect manager signals
        self.settings_manager.settingChanged.connect(self._handle_setting_changed)
        self.matlab_connection.connectionStatusChanged.connect(self.ui_manager.update_matlab_status_display)
        self.matlab_connection.simulationFinished.connect(self.action_handler.on_matlab_op_finished)
        self.matlab_connection.codeGenerationFinished.connect(self.action_handler.on_matlab_op_finished)
        self.git_manager.git_status_updated.connect(self._on_git_status_updated)
        self.py_sim_ui_manager.simulationStateChanged.connect(self._on_pysim_state_changed)
        self.py_sim_ui_manager.requestGlobalUIEnable.connect(self.ui_manager.set_global_ui_enabled)
        self.ide_manager.ide_dirty_state_changed.connect(self.ui_manager.update_ide_save_actions_enable_state)
        self.ide_manager.ide_file_path_changed.connect(self._update_window_title)
        self.ide_manager.ide_language_combo_changed.connect(self._on_ide_language_changed)

        logger.info("Application-level signals connected.")

    def _connect_editor_signals(self, editor: EditorWidget):
        """Connects signals for a newly created editor tab."""
        editor.scene.selectionChanged.connect(self.ui_manager.update_all_ui_element_states)
        editor.scene.scene_content_changed_for_find.connect(self._refresh_find_dialog_if_visible)
        editor.scene.modifiedStatusChanged.connect(self.ui_manager.update_save_actions_state)
        editor.scene.validation_issues_updated.connect(self.ui_manager.update_problems_dock)
        editor.scene.interaction_mode_changed.connect(self.ui_manager.on_mode_changed)
        editor.scene.item_moved.connect(self.ui_manager.update_item_properties_from_move)
        editor.view.zoomChanged.connect(self.ui_manager.update_zoom_status_display)
        editor.scene.itemsBoundingRectChanged.connect(self.ui_manager.update_resource_estimation)

    def _apply_initial_settings(self):
        """Applies settings from the SettingsManager when the application starts."""
        self._apply_theme(self.settings_manager.get("appearance_theme"))

        self.show_grid_action.setChecked(self.settings_manager.get("view_show_grid"))
        self.snap_to_grid_action.setChecked(self.settings_manager.get("view_snap_to_grid"))
        self.snap_to_objects_action.setChecked(self.settings_manager.get("view_snap_to_objects"))
        self.show_snap_guidelines_action.setChecked(self.settings_manager.get("view_show_snap_guidelines"))
        self._update_window_title()

    def _apply_theme(self, theme_name: str):
        """Applies a visual theme to the entire application."""
        logger.info(f"Applying theme: {theme_name}")
        theme_data = self.theme_manager.get_theme_data(theme_name)
        if not theme_data:
            logger.error(f"Theme '{theme_name}' not found. Falling back to Light theme.")
            theme_data = self.theme_manager.get_theme_data("Light")

        config.DYNAMIC_UPDATE_COLORS_FROM_THEME(theme_data)
        QApplication.instance().setStyleSheet(config.GET_CURRENT_STYLE_SHEET())
        self.ui_manager.refresh_all_ui_styles()

    # --- Tab and Editor Management ---

    def current_editor(self) -> EditorWidget | None:
        return self.tab_widget.currentWidget() if isinstance(self.tab_widget.currentWidget(), EditorWidget) else None

    def find_editor_by_path(self, file_path: str) -> EditorWidget | None:
        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            if editor and editor.file_path and os.path.normpath(editor.file_path) == os.path.normpath(file_path):
                return editor
        return None

    def add_new_editor_tab(self) -> EditorWidget:
        """Creates a new, empty editor tab, connects its signals, and makes it active."""
        new_editor = EditorWidget(self, self.custom_snippet_manager, self.settings_manager)
        index = self.tab_widget.addTab(new_editor, new_editor.get_tab_title())
        self._connect_editor_signals(new_editor)
        self.tab_widget.setCurrentIndex(index)
        new_editor.view.setFocus()
        return new_editor

    def _create_and_load_new_tab(self, file_path: str):
        """Creates a new tab and loads a file into it, handling errors."""
        if not os.path.exists(file_path) and not file_path.startswith(":/"):
            self.log_message("ERROR", f"Attempted to open non-existent file: {file_path}")
            return

        new_editor = self.add_new_editor_tab()
        if self._load_into_editor(new_editor, file_path):
            new_editor.set_dirty(False)
            new_editor.undo_stack.clear()
            self.action_handler.add_to_recent_files(file_path)
            self._update_window_title()
            if self.git_manager:
                QTimer.singleShot(50, lambda p=file_path: self.git_manager.check_file_status(p))
        else:
            index = self.tab_widget.indexOf(new_editor)
            if index != -1: self.tab_widget.removeTab(index)
            new_editor.deleteLater()
            QMessageBox.critical(self, "Error Opening File", f"Could not load diagram from:\n{file_path}")

    def _load_into_editor(self, editor: EditorWidget, file_path: str) -> bool:
        """Helper to load file content into a given editor."""
        try:
            content = ""
            if file_path.startswith(":/"):
                qfile = QFile(file_path)
                qfile.open(QIODevice.ReadOnly | QIODevice.Text)
                content = qfile.readAll().data().decode('utf-8')
                qfile.close()
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            data = json.loads(content)
            editor.scene.load_diagram_data(data)
            editor.file_path = file_path
            self.log_message("INFO", f"Loaded '{os.path.basename(file_path)}' into new tab.")
            return True
        except Exception as e:
            logger.error(f"Failed to load file {file_path}: {e}", exc_info=True)
            return False

    def _save_editor_to_path(self, editor: EditorWidget, file_path: str) -> bool:
        """Helper to save an editor's content to a specific file path."""
        save_file = QSaveFile(file_path)
        if not save_file.open(QIODevice.WriteOnly | QIODevice.Text):
            QMessageBox.critical(self, "Save Error", f"Could not open file for saving:\n{save_file.errorString()}")
            return False
        try:
            json_data = json.dumps(editor.scene.get_diagram_data(), indent=4)
            save_file.write(json_data.encode('utf-8'))
            if save_file.commit():
                editor.file_path = file_path
                editor.set_dirty(False)
                self.log_message("INFO", f"Saved to {file_path}")
                if self.git_manager:
                    self.git_manager.check_file_status(file_path)
                return True
            else:
                raise IOError(save_file.errorString())
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"An unexpected error occurred during saving:\n{e}")
            save_file.cancelWriting()
            return False

    def _add_fsm_data_to_scene(self, fsm_data: dict, clear_current_diagram: bool = False, original_user_prompt: str = ""):
        """Adds FSM data (e.g., from AI or a template) to the current or a new scene."""
        editor = self.current_editor()
        if clear_current_diagram or not editor:
            editor = self.add_new_editor_tab()
        editor.scene._add_template_to_scene(fsm_data, editor.view.mapToScene(editor.view.viewport().rect().center()))
        self.log_message("INFO", f"Added FSM data from '{original_user_prompt[:30]}...' to the scene.")

    # --- Event Handlers and Slots ---

    def closeEvent(self, event: QCloseEvent):
        """Handles the application close event, checking for unsaved changes."""
        logger.info("Close event received. Checking for unsaved changes.")
        for i in range(self.tab_widget.count() - 1, -1, -1):
            if not self._prompt_save_on_close(self.tab_widget.widget(i)):
                event.ignore()
                return
        if not self.ide_manager.prompt_ide_save_if_dirty():
            event.ignore()
            return
        
        self.internet_check_timer.stop()
        self.ai_chatbot_manager.stop_chatbot()
        self.resource_monitor_manager.stop_monitoring_system()
        self.git_manager.stop()
        for dialog in self._find_dialogs.values():
            dialog.close()

        self.settings_manager.set("last_used_perspective", self.perspective_manager.current_perspective_name)
        self.settings_manager.set("window_geometry", self.saveGeometry().toHex().data().decode('ascii'))
        self.settings_manager.set("window_state", self.saveState().toHex().data().decode('ascii'))
        logger.info("Application close event accepted.")
        event.accept()

    def _prompt_save_on_close(self, editor: EditorWidget) -> bool:
        """Prompts the user to save if the editor tab has unsaved changes."""
        if not editor or not editor.is_dirty():
            return True
        self.tab_widget.setCurrentWidget(editor)
        file_desc = os.path.basename(editor.file_path) if editor.file_path else "Untitled"
        reply = QMessageBox.question(self, f"Save '{file_desc}'?",
                                     f"The diagram '{file_desc}' has unsaved changes. Save them?",
                                     QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                                     QMessageBox.Save)
        if reply == QMessageBox.Save: return self.action_handler.on_save_file()
        return reply != QMessageBox.Cancel

    @pyqtSlot(int)
    def _on_close_tab_requested(self, index: int):
        editor = self.tab_widget.widget(index)
        if not isinstance(editor, EditorWidget) or not self._prompt_save_on_close(editor):
            return

        if editor in self._find_dialogs:
            self._find_dialogs.pop(editor).deleteLater()
        self.tab_widget.removeTab(index)
        editor.deleteLater()
        self._update_central_widget()

    @pyqtSlot(int)
    def _on_current_tab_changed(self, index: int):
        editor = self.current_editor()
        self.ui_manager.connect_undo_stack(editor.undo_stack if editor else None)
        self.ui_manager.connect_minimap_view(editor)
        self.ui_manager.update_all_ui_element_states() # This handles all UI element states
        if editor and editor.file_path:
            self.git_manager.check_file_status(editor.file_path)
        self._update_window_title()

    def _update_central_widget(self):
        """Shows the welcome page if no tabs are open, otherwise shows the tab widget."""
        show_welcome = self.tab_widget.count() == 0
        if show_welcome and self.centralWidget() != self.welcome_widget:
            self.setCentralWidget(self.welcome_widget)
            self.welcome_widget.update_recent_files()
        elif not show_welcome and self.centralWidget() != self.tab_widget:
            self.setCentralWidget(self.tab_widget)
    
    def _update_window_title(self):
        """Updates the main window title based on the active tab and its state."""
        editor = self.current_editor()
        title = APP_NAME
        if editor:
            file_name = os.path.basename(editor.file_path) if editor.file_path else "Untitled"
            dirty_char = "[*]"  # Let Qt handle the star based on `isWindowModified`
            pysim_suffix = " [Simulating]" if editor.py_sim_active else ""
            title = f"{file_name}{dirty_char} - {APP_NAME}{pysim_suffix}"
            self.setWindowModified(editor.is_dirty())
        else:
            self.setWindowModified(False)
        self.setWindowTitle(title)
        
    def _init_internet_status_check(self):
        """Starts a recurring check for internet connectivity."""
        self.internet_check_timer.timeout.connect(self._run_internet_check_job)
        QTimer.singleShot(100, self._run_internet_check_job)
        self.internet_check_timer.start(15000)

    def _run_internet_check_job(self):
        """Performs a non-blocking check for internet connectivity."""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=1.5).close()
            is_connected, detail = True, "Connected"
        except (socket.timeout, socket.gaierror, OSError):
            is_connected, detail = False, "Offline"
        
        if is_connected != self._internet_connected:
            self._internet_connected = is_connected
            self.ui_manager.update_internet_status_display(is_connected, detail)
            self.ai_chatbot_manager.set_online_status(is_connected)

    def log_message(self, level: str, message: str):
        """Convenience method to log a message from the main window."""
        logger.log(getattr(logging, level.upper(), logging.INFO), message)

    def show_find_item_dialog_for_editor(self, editor: EditorWidget):
        """Shows the 'Find Item' dialog for a specific editor tab."""
        if editor not in self._find_dialogs:
            dialog = FindItemDialog(parent=self, scene_ref=editor.scene)
            dialog.item_selected_for_focus.connect(self.action_handler.on_focus_item)
            editor.scene.scene_content_changed_for_find.connect(dialog.refresh_list)
            self._find_dialogs[editor] = dialog
        dialog = self._find_dialogs[editor]
        dialog.show()
        dialog.activateWindow()

    @pyqtSlot(str, object)
    def _handle_setting_changed(self, key, value):
        if key == "appearance_theme": self._apply_theme(str(value))
        self.ui_manager.handle_setting_changed(key, value)

    @pyqtSlot(bool)
    def _on_pysim_state_changed(self, is_running: bool):
        if editor := self.current_editor():
            editor.py_sim_active = is_running
        self._update_window_title()
        self.ui_manager.update_py_sim_status_display()

    @pyqtSlot(str)
    def _on_ide_language_changed(self, language: str):
        ai_ready = self.ai_chatbot_manager.is_configured() and self._internet_connected
        self.ui_manager.update_ide_analysis_action_state(language, ai_ready)

    @pyqtSlot()
    def _refresh_find_dialog_if_visible(self):
        if editor := self.current_editor():
            if dialog := self._find_dialogs.get(editor):
                dialog.refresh_list()

    @pyqtSlot(str, bool, bool)
    def _on_git_status_updated(self, file_path, is_in_repo, has_changes):
        if editor := self.find_editor_by_path(file_path):
            editor.has_uncommitted_changes = has_changes
            self.ui_manager.update_tab_icon(editor, is_in_repo and has_changes)
            if self.current_editor() == editor:
                self.ui_manager.update_git_actions_state(is_in_repo)

    @pyqtSlot()
    def on_show_preferences_dialog(self):
        self.ui_manager.show_preferences_dialog()
        
    @pyqtSlot(GraphicsStateItem, bool)
    def on_toggle_state_breakpoint(self, state_item, set_bp):
        self.py_sim_ui_manager.on_toggle_state_breakpoint(state_item, set_bp)

def main_entry_point():
    """The main entry point for the application."""
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)
    app.setOrganizationName("BSM-Devs")

    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    # This block is now primarily for ensuring the script can be run directly,
    # the logic inside the initial `if` block at the top handles the re-execution.
    main_entry_point()