# fsm_designer_project/main.py

import sys
import os

# --- BEGIN SYS.PATH MODIFICATION BLOCK ---
# This ensures the application can be run directly as a script
if __name__ == '__main__' and __package__ is None:
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_script_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    # Re-launch using the package context
    import fsm_designer_project.main
    sys.exit(fsm_designer_project.main.main_entry_point())
# --- END SYS.PATH MODIFICATION BLOCK ---

import json
import logging
import socket
from PyQt5.QtCore import (
    Qt, QTimer, QPoint, QUrl, pyqtSignal, pyqtSlot, QSize, QIODevice, QFile, QSaveFile
)
from PyQt5.QtGui import (
    QIcon, QKeySequence, QCloseEvent, QPalette, QColor, QPen, QDesktopServices, QTransform
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QDockWidget, QAction,
    QToolBar, QVBoxLayout, QWidget, QLabel,
    QStatusBar, QTextEdit,
    QPushButton, QMenu, QMessageBox,
    QInputDialog, QLineEdit, QColorDialog, QDialog, QFormLayout,
    QSpinBox, QComboBox, QDoubleSpinBox,
    QUndoStack, QStyle, QTabWidget, QGraphicsItem, QCheckBox,
    QListWidgetItem
)

# Local application imports
from .graphics_scene import DiagramScene, ZoomableView
from .graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem
from .undo_commands import EditItemPropertiesCommand
from .matlab_integration import MatlabConnection
from .settings_manager import SettingsManager
from .resource_estimator import ResourceEstimator
from . import config
from .config import (
    APP_VERSION, APP_NAME,
    DYNAMIC_UPDATE_COLORS_FROM_THEME, GET_CURRENT_STYLE_SHEET
)

from .ui_manager import UIManager
from .ide_manager import IDEManager
from .action_handlers import ActionHandler
from .resource_monitor import ResourceMonitorManager
from .snippet_manager import CustomSnippetManager
from .utils import get_standard_icon, _get_bundled_file_path
from .editor_widget import EditorWidget
from .ai_chatbot import AIChatbotManager, AIChatUIManager
from .ui_py_simulation_manager import PySimulationUIManager
from .dialogs import FindItemDialog, SettingsDialog
from .fsm_simulator import FSMSimulator, FSMError

# Imports for new live preview feature
from .c_code_generator import generate_c_code_content
from .python_code_generator import generate_python_fsm_code
from .export_utils import generate_plantuml_text, generate_mermaid_text


try:
    from .logging_setup import setup_global_logging
except ImportError:
    print("CRITICAL: logging_setup.py not found (relative import failed). Logging will be basic.")
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

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
    DEFAULT_PERSPECTIVES_ORDER = [
        PERSPECTIVE_DESIGN_FOCUS,
        PERSPECTIVE_SIMULATION_FOCUS,
        PERSPECTIVE_IDE_FOCUS,
        PERSPECTIVE_AI_FOCUS
    ]

    def __init__(self):
        super().__init__()
        # Ensure SettingsManager is available globally for other components
        if not hasattr(QApplication.instance(), 'settings_manager'):
             QApplication.instance().settings_manager = SettingsManager(app_name=APP_NAME)
        self.settings_manager = QApplication.instance().settings_manager

        # --- INITIALIZATION ORDER ---

        # 1. Initialize core attributes
        self.current_perspective_name = self.settings_manager.get("last_used_perspective", self.PERSPECTIVE_DESIGN_FOCUS)
        self._find_dialogs = {} # Dictionary to hold find dialogs per editor
        self._dock_property_editors = {}
        self._current_edited_item_in_dock = None
        self._current_edited_item_original_props_in_dock = {}
        self._internet_connected: bool | None = None
        self.py_sim_active = False # Global state for UI locking
        self.py_fsm_engine: FSMSimulator | None = None # Engine for current tab only

        # 2. Setup the central tabbed widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.setDocumentMode(True)
        self.setCentralWidget(self.tab_widget)

        # 3. Instantiate all manager classes BEFORE using their methods
        self.custom_snippet_manager = CustomSnippetManager(app_name=APP_NAME)
        self.resource_estimator = ResourceEstimator()
        self.ui_manager = UIManager(self)
        self.action_handler = ActionHandler(self)
        self.resource_monitor_manager = ResourceMonitorManager(self, settings_manager=self.settings_manager)
        self.matlab_connection = MatlabConnection()
        self.ai_chatbot_manager = AIChatbotManager(self)
        self.py_sim_ui_manager = PySimulationUIManager(self)

        # 4. Now, call setup_ui which creates the actions, menus, toolbars, and dock widgets
        self.ui_manager.setup_ui()

        # 5. Populate docks whose content is managed by other classes.
        self.ide_manager = IDEManager(self) # Must be after its dock is created in setup_ui
        self.ai_chat_ui_manager = AIChatUIManager(self) # Has to be after setup_ui finds its actions
        self.ui_manager.populate_dynamic_docks()

        # 6. Setup Logging
        try:
            if not hasattr(self, 'log_output') or not self.log_output:
                self.log_output = QTextEdit()
                logger.warning("MainWindow: log_output fallback used before logging setup.")
            setup_global_logging(self.log_output)
            logger.info("Main window initialized and logging configured.")
        except Exception as e:
            print(f"ERROR: Failed to run setup_global_logging: {e}. UI logs might not work.")
            if not logging.getLogger().hasHandlers():
                 logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

        # 7. Finalize UI and connect signals
        self._connect_signals()
        self.action_handler.connect_actions()
        self._apply_initial_settings()
        self._populate_perspectives_menu()
        self.restore_geometry_and_state()
        QTimer.singleShot(50, lambda: self.apply_perspective(self.current_perspective_name))

        # 8. Start background services
        self.internet_check_timer = QTimer(self)
        self._init_internet_status_check()
        if self.settings_manager.get("resource_monitor_enabled"):
            self.resource_monitor_manager.setup_and_start_monitor()

        # 9. Initial Actions & UI State
        self._set_status_label_object_names()
        QTimer.singleShot(100, lambda: self.action_handler.on_new_file(silent=True)) # Create initial tab
        QTimer.singleShot(300, lambda: self.ai_chatbot_manager.set_online_status(self._internet_connected if self._internet_connected is not None else False))
        logger.info(f"{APP_NAME} v{APP_VERSION} initialized successfully.")

    def _connect_signals(self):
        """Connects signals from UI elements and managers to MainWindow slots."""
        # Window & Managers
        self.tab_widget.currentChanged.connect(self._on_current_tab_changed)
        self.tab_widget.tabCloseRequested.connect(self._on_close_tab_requested)
        self.settings_manager.settingChanged.connect(self._handle_setting_changed)
        self.matlab_connection.connectionStatusChanged.connect(self._update_matlab_status_display)
        self.matlab_connection.simulationFinished.connect(lambda s,m,d: self._finish_matlab_operation())
        self.matlab_connection.codeGenerationFinished.connect(lambda s,m,d: self._finish_matlab_operation())

        # UI Manager Signals
        self.preferences_action.triggered.connect(self.on_show_preferences_dialog)
        self.save_perspective_action.triggered.connect(self.save_current_perspective_as)
        self.reset_perspectives_action.triggered.connect(self.reset_all_custom_perspectives)
        self.target_device_combo.currentTextChanged.connect(self.on_target_device_changed)

        # Properties Dock
        self.properties_apply_button.clicked.connect(self._on_apply_dock_properties)
        self.properties_revert_button.clicked.connect(self._on_revert_dock_properties)
        self.properties_edit_dialog_button.clicked.connect(lambda: self.current_editor().scene.edit_item_properties(self._current_edited_item_in_dock) if self.current_editor() and self._current_edited_item_in_dock else None)

        # Sim & IDE Managers
        self.py_sim_ui_manager.simulationStateChanged.connect(self._handle_py_sim_state_changed_by_manager)
        self.py_sim_ui_manager.requestGlobalUIEnable.connect(self._handle_py_sim_global_ui_enable_by_manager)
        self.ide_manager.ide_dirty_state_changed.connect(self._on_ide_dirty_state_changed_by_manager)
        self.ide_manager.ide_file_path_changed.connect(lambda: self._update_window_title())
        self.ide_manager.ide_language_combo_changed.connect(self._on_ide_language_changed_by_manager)

        # Live Preview
        self.live_preview_combo.currentTextChanged.connect(self._update_live_preview)
        self.live_preview_dock.visibilityChanged.connect(lambda visible: self._update_live_preview() if visible else None)

    # --- ARCHITECTURE: TAB MANAGEMENT ---

    def current_editor(self) -> EditorWidget | None:
        """Helper function to get the currently active EditorWidget."""
        return self.tab_widget.currentWidget() if isinstance(self.tab_widget.currentWidget(), EditorWidget) else None

    def find_editor_by_path(self, file_path: str) -> EditorWidget | None:
        """Finds an editor tab corresponding to a given absolute file path."""
        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            if editor and editor.file_path and os.path.normpath(editor.file_path) == os.path.normpath(file_path):
                return editor
        return None

    def add_new_editor_tab(self) -> EditorWidget:
        """Creates a new editor tab, connects its signals, and makes it active."""
        new_editor = EditorWidget(self, self.custom_snippet_manager)
        index = self.tab_widget.addTab(new_editor, new_editor.get_tab_title())
        self.tab_widget.setCurrentIndex(index)
        new_editor.view.setFocus()
        self._connect_editor_signals(new_editor)
        return new_editor

    def _connect_editor_signals(self, editor: EditorWidget):
        """Connects signals from a newly created editor tab to main window handlers."""
        editor.undo_stack.indexChanged.connect(self._update_all_ui_element_states)
        editor.undo_stack.indexChanged.connect(self._update_live_preview) # Update preview on undo/redo
        editor.scene.selectionChanged.connect(self._update_all_ui_element_states)
        editor.scene.scene_content_changed_for_find.connect(self._refresh_find_dialog_if_visible)
        editor.scene.modifiedStatusChanged.connect(self._update_window_title)
        editor.scene.validation_issues_updated.connect(self.update_problems_dock)
        editor.scene.interaction_mode_changed.connect(self._on_interaction_mode_changed_by_scene)
        editor.scene.item_moved.connect(self._on_item_moved_in_editor)
        editor.view.zoomChanged.connect(self.update_zoom_status_display)

    @pyqtSlot(int)
    def _on_close_tab_requested(self, index: int):
        editor_to_close = self.tab_widget.widget(index)
        if not self._prompt_save_on_close(editor_to_close):
            return

        if editor_to_close in self._find_dialogs:
            self._find_dialogs[editor_to_close].close()
            del self._find_dialogs[editor_to_close]

        self.tab_widget.removeTab(index)
        editor_to_close.deleteLater()
        if self.tab_widget.count() == 0:
            self.action_handler.on_new_file(silent=True)

    @pyqtSlot(int)
    def _on_current_tab_changed(self, index: int):
        editor = self.current_editor()
        
        # Re-bind main undo/redo actions to the active tab's stack
        if hasattr(self, 'undo_action'):
            try: self.undo_action.triggered.disconnect()
            except (TypeError, RuntimeError): pass
            if editor: self.undo_action.triggered.connect(editor.undo_stack.undo)
        if hasattr(self, 'redo_action'):
            try: self.redo_action.triggered.disconnect()
            except (TypeError, RuntimeError): pass
            if editor: self.redo_action.triggered.connect(editor.undo_stack.redo)

        self._update_all_ui_element_states()
        self._update_live_preview()

    def _prompt_save_on_close(self, editor: EditorWidget) -> bool:
        """Prompts to save a single editor tab if it is dirty. Returns False if user cancels."""
        if not editor.is_dirty():
            return True
        self.tab_widget.setCurrentWidget(editor)
        file_desc = os.path.basename(editor.file_path) if editor.file_path else "Untitled"
        reply = QMessageBox.question(self, f"Save '{file_desc}'?",
                                     f"The diagram '{file_desc}' has unsaved changes. Do you want to save them?",
                                     QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                                     QMessageBox.Save)
        if reply == QMessageBox.Save:
            return self.action_handler.on_save_file()
        return reply != QMessageBox.Cancel

    def _create_and_load_new_tab(self, file_path: str):
        """Creates a new editor tab and loads a file into it."""
        if not os.path.exists(file_path) and not file_path.startswith(":/"):
            self.log_message("ERROR", f"Attempted to open non-existent file: {file_path}")
            return
        new_editor = self.add_new_editor_tab()
        if self._load_into_editor(new_editor, file_path):
            new_editor.file_path = file_path
            new_editor.set_dirty(False)
            new_editor.undo_stack.clear()
            self.action_handler.add_to_recent_files(file_path)
            self.tab_widget.setTabText(self.tab_widget.indexOf(new_editor), new_editor.get_tab_title())
            self._update_window_title()
        else:
            if (index := self.tab_widget.indexOf(new_editor)) != -1:
                self.tab_widget.removeTab(index)
            new_editor.deleteLater()
            QMessageBox.critical(self, "Error Opening File", f"Could not load diagram from:\n{file_path}")

    def _load_into_editor(self, editor: EditorWidget, file_path: str) -> bool:
        """Helper to load file content into a specific editor instance."""
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
            self.log_message("INFO", f"Loaded '{os.path.basename(file_path)}' into tab.")
            return True
        except Exception as e:
            logger.error(f"Failed to load file {file_path}: {e}", exc_info=True)
            return False

    def _save_editor_to_path(self, editor: EditorWidget, file_path: str) -> bool:
        """Helper to save a specific editor's content to a path."""
        save_file = QSaveFile(file_path)
        if not save_file.open(QIODevice.WriteOnly | QIODevice.Text):
            QMessageBox.critical(self, "Save Error", f"Could not open file for saving:\n{save_file.errorString()}")
            return False
        try:
            json_data = json.dumps(editor.scene.get_diagram_data(), indent=4, ensure_ascii=False)
            save_file.write(json_data.encode('utf-8'))
            if save_file.commit():
                editor.file_path = file_path
                editor.set_dirty(False)
                self.tab_widget.setTabText(self.tab_widget.indexOf(editor), editor.get_tab_title())
                self._update_window_title()
                self.log_message("INFO", f"Saved to {file_path}")
                return True
            QMessageBox.critical(self, "Save Error", f"Could not finalize saving:\n{save_file.errorString()}")
            return False
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"An unexpected error occurred during saving:\n{e}")
            save_file.cancelWriting()
            return False

    # --- UI & STATE UPDATES ---

    def _update_all_ui_element_states(self):
        """A central hub to call all UI element state update methods."""
        self._update_window_title()
        self._update_undo_redo_actions_enable_state()
        self._update_save_actions_enable_state()
        self._update_properties_dock()
        self._update_py_simulation_actions_enabled_state()
        self._update_zoom_to_selection_action_enable_state()
        self._update_align_distribute_actions_enable_state()
        self.update_resource_estimation()

        editor = self.current_editor()
        if editor and editor.view:
            self.update_zoom_status_display(editor.view.transform().m11())

    def _update_window_title(self):
        """Updates the main window title based on the active tab's state."""
        base_title = APP_NAME
        editor = self.current_editor()
        ide_dirty = self.ide_manager.ide_editor_is_dirty if self.ide_manager else False

        if editor:
            file_name = os.path.basename(editor.file_path) if editor.file_path else "Untitled"
            dirty_indicator = "[*]" if editor.is_dirty() or ide_dirty else ""
            self.setWindowTitle(f"{file_name}{dirty_indicator} - {base_title}")
        elif ide_dirty:
            ide_file_name = os.path.basename(self.ide_manager.current_ide_file_path) if self.ide_manager.current_ide_file_path else "IDE Script"
            self.setWindowTitle(f"{ide_file_name}[*] - {base_title}")
        else:
            self.setWindowTitle(base_title)

        self.setWindowModified(editor.is_dirty() if editor else ide_dirty)

    def _update_undo_redo_actions_enable_state(self):
        editor = self.current_editor()
        can_undo = editor.undo_stack.canUndo() if editor else False
        can_redo = editor.undo_stack.canRedo() if editor else False
        undo_text = editor.undo_stack.undoText() if can_undo and editor else ""
        redo_text = editor.undo_stack.redoText() if can_redo and editor else ""

        self.undo_action.setEnabled(can_undo)
        self.undo_action.setText(f"&Undo{' ' + undo_text if undo_text else ''}")
        self.redo_action.setEnabled(can_redo)
        self.redo_action.setText(f"&Redo{' ' + redo_text if redo_text else ''}")

    def _update_save_actions_enable_state(self):
        self.save_action.setEnabled(bool(self.current_editor() and self.current_editor().is_dirty()))

    # --- PERSPECTIVES ---

    def _populate_perspectives_menu(self):
        """Dynamically populates the perspectives menu from settings."""
        if not hasattr(self, 'perspectives_menu') or not self.perspectives_menu:
            logger.error("Perspectives menu not found. Cannot populate.")
            return

        self.perspectives_menu.clear()
        for action in self.perspectives_action_group.actions():
            self.perspectives_action_group.removeAction(action)

        for p_name in self.DEFAULT_PERSPECTIVES_ORDER:
            action = self.perspectives_menu.addAction(p_name)
            action.setCheckable(True)
            action.triggered.connect(lambda checked=False, name=p_name: self.apply_perspective(name))
            self.perspectives_action_group.addAction(action)

        self.perspectives_menu.addSeparator()

        user_perspective_names = self.settings_manager.get("user_perspective_names", [])
        if user_perspective_names:
            for p_name in sorted(user_perspective_names):
                action = self.perspectives_menu.addAction(p_name)
                action.setCheckable(True)
                action.triggered.connect(lambda checked=False, name=p_name: self.apply_perspective(name))
                self.perspectives_action_group.addAction(action)
            self.perspectives_menu.addSeparator()

        self.perspectives_menu.addAction(self.save_perspective_action)
        self.perspectives_menu.addAction(self.reset_perspectives_action)
        self._update_current_perspective_check()

    def _update_current_perspective_check(self):
        """Ensures the correct perspective action in the menu is checked."""
        for action in self.perspectives_action_group.actions():
            action.setChecked(action.text() == self.current_perspective_name)

    def apply_perspective(self, perspective_name: str):
        """Restores a saved dock layout or applies a default programmatic layout."""
        logger.info(f"Applying perspective: {perspective_name}")
        saved_state_hex = self.settings_manager.get(f"perspective_{perspective_name}", None)

        applied_from_saved_state = False
        if saved_state_hex and isinstance(saved_state_hex, str):
            try:
                state_data_bytes = bytes.fromhex(saved_state_hex)
                if self.restoreState(state_data_bytes):
                    logger.info(f"Restored layout from saved state for perspective: {perspective_name}")
                    applied_from_saved_state = True
                else:
                    logger.warning(f"Failed to restore layout from saved state for: {perspective_name}.")
            except ValueError:
                logger.error(f"Invalid hex string for perspective '{perspective_name}'.")

        if not applied_from_saved_state:
            self._apply_default_perspective_layout(perspective_name)

        self.current_perspective_name = perspective_name
        self._update_current_perspective_check()

    def _apply_default_perspective_layout(self, perspective_name: str):
        """Applies a hard-coded default layout for the built-in perspectives."""
        logger.info(f"Applying default programmatic layout for perspective: {perspective_name}")
        all_docks = [
            self.elements_palette_dock, self.properties_dock, self.log_dock,
            self.problems_dock, self.py_sim_dock, self.ai_chatbot_dock, self.ide_dock,
            self.resource_estimation_dock, self.live_preview_dock
        ]
        for dock in all_docks:
            if dock: dock.setFloating(False); dock.setVisible(False)

        if perspective_name == self.PERSPECTIVE_DESIGN_FOCUS:
            self.addDockWidget(Qt.LeftDockWidgetArea, self.elements_palette_dock)
            self.addDockWidget(Qt.RightDockWidgetArea, self.properties_dock)
            self.addDockWidget(Qt.BottomDockWidgetArea, self.problems_dock)
            self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)
            self.elements_palette_dock.setVisible(True)
            self.properties_dock.setVisible(True)
            self.problems_dock.setVisible(True)
            self.tabifyDockWidget(self.problems_dock, self.log_dock)
            self.properties_dock.raise_()

        elif perspective_name == self.PERSPECTIVE_SIMULATION_FOCUS:
            self.addDockWidget(Qt.RightDockWidgetArea, self.py_sim_dock)
            self.addDockWidget(Qt.RightDockWidgetArea, self.properties_dock)
            self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)
            self.py_sim_dock.setVisible(True)
            self.properties_dock.setVisible(True)
            self.log_dock.setVisible(True)
            self.tabifyDockWidget(self.py_sim_dock, self.properties_dock)
            self.py_sim_dock.raise_()

        elif perspective_name == self.PERSPECTIVE_IDE_FOCUS:
            self.splitDockWidget(self.properties_dock, self.ide_dock, Qt.Horizontal)
            self.ide_dock.setVisible(True)
            self.ide_dock.raise_()

        elif perspective_name == self.PERSPECTIVE_AI_FOCUS:
            self.splitDockWidget(self.properties_dock, self.ai_chatbot_dock, Qt.Horizontal)
            self.ai_chatbot_dock.setVisible(True)
            self.ai_chatbot_dock.raise_()

        else:
            logger.warning(f"Unknown default perspective: {perspective_name}")
            self._apply_default_perspective_layout(self.PERSPECTIVE_DESIGN_FOCUS)

    def save_current_perspective_as(self):
        """Saves the current dock layout as a named perspective."""
        name, ok = QInputDialog.getText(self, "Save Perspective", "Enter name for current layout:", QLineEdit.Normal)
        if ok and (name := name.strip()):
            is_default_name = name in self.DEFAULT_PERSPECTIVES_ORDER
            user_perspective_names = self.settings_manager.get("user_perspective_names", [])

            if (is_default_name or name in user_perspective_names):
                 reply = QMessageBox.question(self, "Overwrite?", f"Perspective '{name}' already exists. Overwrite?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                 if reply == QMessageBox.No: return

            state_data_hex = self.saveState().toHex().data().decode('ascii')
            self.settings_manager.set(f"perspective_{name}", state_data_hex)

            if not is_default_name and name not in user_perspective_names:
                user_perspective_names.append(name)
                self.settings_manager.set("user_perspective_names", sorted(user_perspective_names))

            logger.info(f"Saved current layout as perspective: {name}")
            self._populate_perspectives_menu()
            self.apply_perspective(name)

    def reset_all_custom_perspectives(self):
        """Resets all dock layouts to their application defaults."""
        reply = QMessageBox.question(self, "Reset Layouts",
                                     "This will reset all dock layouts to their application defaults and remove any user-saved custom layouts. Are you sure?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            user_perspective_names = self.settings_manager.get("user_perspective_names", [])
            for p_name in user_perspective_names + self.DEFAULT_PERSPECTIVES_ORDER:
                self.settings_manager.remove_setting(f"perspective_{p_name}", save_immediately=False)
            self.settings_manager.set("user_perspective_names", [], save_immediately=True)
            logger.info("All custom perspectives have been reset.")
            self._populate_perspectives_menu()
            self.apply_perspective(self.PERSPECTIVE_DESIGN_FOCUS)
            QMessageBox.information(self, "Layouts Reset", "All perspectives have been reset to their default layouts.")

    # --- Other Implemented Methods ---

    def log_message(self, level_str: str, message: str):
        level = getattr(logging, level_str.upper(), logging.INFO)
        logger.log(level, message)

    def closeEvent(self, event: QCloseEvent):
        """Overrides QMainWindow.closeEvent to check for unsaved changes."""
        logger.info("Main window close event triggered.")

        if self.py_sim_active:
            self.py_sim_ui_manager.on_stop_py_simulation(silent=True)

        if self.ide_manager and not self.ide_manager.prompt_ide_save_if_dirty():
            event.ignore()
            return

        for i in range(self.tab_widget.count() - 1, -1, -1):
            if not self._prompt_save_on_close(self.tab_widget.widget(i)):
                event.ignore()
                return

        # Stop background services
        self.internet_check_timer.stop()
        self.ai_chatbot_manager.stop_chatbot()
        if self.resource_monitor_manager:
            self.resource_monitor_manager.stop_monitoring_system()

        self.settings_manager.set("last_used_perspective", self.current_perspective_name)
        self.settings_manager.set("window_geometry", self.saveGeometry().toHex().data().decode('ascii'))
        self.settings_manager.set("window_state", self.saveState().toHex().data().decode('ascii'))
        logger.info("Application closeEvent accepted. Settings saved.")
        event.accept()

    def _set_status_label_object_names(self):
        if hasattr(self, 'main_op_status_label'):
            self.main_op_status_label.setObjectName("MainOpStatusLabel")
        if hasattr(self, 'mode_status_label'):
            self.mode_status_label.setObjectName("InteractionModeStatusLabel")
            
    # --- Previously Placeholder Methods - Full Implementation ---
    
    @pyqtSlot(str, object)
    def _handle_setting_changed(self, key: str, value: object):
        logger.info(f"Setting '{key}' changed to '{value}'. Updating UI.")

        theme_related_change = False
        if key == "appearance_theme":
            self._apply_theme(str(value))
            theme_related_change = True
            QTimer.singleShot(100, lambda: QMessageBox.information(self, "Theme Changed", "Application restart may be required for the theme to apply to all elements fully."))
        elif key in ["canvas_grid_minor_color", "canvas_grid_major_color", "canvas_snap_guideline_color"]:
            current_theme = self.settings_manager.get("appearance_theme")
            config.DYNAMIC_UPDATE_COLORS_FROM_THEME(current_theme)
            theme_related_change = True
            for i in range(self.tab_widget.count()):
                if editor := self.tab_widget.widget(i): editor.scene.update()

        if theme_related_change:
            # Re-apply the global stylesheet after a theme/color change
            if key != "appearance_theme":
                new_stylesheet = config.GET_CURRENT_STYLE_SHEET()
                app_instance = QApplication.instance()
                if app_instance: app_instance.setStyleSheet(new_stylesheet)
                self.update()
                self.repaint()
                for child_widget in self.findChildren(QWidget):
                    if child_widget:
                        child_widget.style().unpolish(child_widget)
                        child_widget.style().polish(child_widget)
                        child_widget.update()
                if app_instance: app_instance.processEvents()

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
                elif not is_enabled and self.resource_monitor_manager.thread and self.resource_monitor_manager.thread.isRunning():
                    self.resource_monitor_manager.stop_monitoring_system()

        elif key == "resource_monitor_interval_ms":
            if self.resource_monitor_manager and self.resource_monitor_manager.worker:
                self.resource_monitor_manager.worker.data_collection_interval_ms = int(value)

        self._update_window_title()

    def _apply_initial_settings(self):
        logger.debug("Applying initial settings from SettingsManager.")
        initial_theme = self.settings_manager.get("appearance_theme")
        self._apply_theme(initial_theme)

        # Connect view actions to settings
        def connect_view_action(action, key):
            action.setChecked(self.settings_manager.get(key))
        
        connect_view_action(self.show_grid_action, "view_show_grid")
        connect_view_action(self.snap_to_grid_action, "view_snap_to_grid")
        connect_view_action(self.snap_to_objects_action, "view_snap_to_objects")
        connect_view_action(self.show_snap_guidelines_action, "view_show_snap_guidelines")

        # Update resource monitor based on settings
        if self.settings_manager.get("resource_monitor_enabled"):
            self.resource_monitor_manager.setup_and_start_monitor()
        self._update_window_title()

    def _apply_theme(self, theme_name: str):
        logger.info(f"Applying theme: {theme_name}")
        config.DYNAMIC_UPDATE_COLORS_FROM_THEME(theme_name)

        new_stylesheet = config.GET_CURRENT_STYLE_SHEET()
        app_instance = QApplication.instance()
        if app_instance: app_instance.setStyleSheet(new_stylesheet)
        
        # Force a refresh of scenes and UI elements
        for i in range(self.tab_widget.count()):
            if editor := self.tab_widget.widget(i):
                editor.scene.setBackgroundBrush(QColor(config.COLOR_BACKGROUND_LIGHT))
                editor.scene.update()
        for child in self.findChildren(QWidget):
            child.style().unpolish(child); child.style().polish(child); child.update()

        self.update()
        self.repaint()
        if app_instance: app_instance.processEvents()
        logger.info(f"Theme '{theme_name}' applied.")

    def restore_geometry_and_state(self):
        """Restores window geometry and perspective from settings."""
        try:
            if geom_hex := self.settings_manager.get("window_geometry"):
                self.restoreGeometry(bytes.fromhex(geom_hex))
            if state_hex := self.settings_manager.get("window_state"):
                self.restoreState(bytes.fromhex(state_hex))
            else: # Fallback if state is missing
                self.apply_perspective(self.current_perspective_name)
        except Exception as e:
            logger.warning(f"Could not restore window state/geometry: {e}. Applying default.")
            self.apply_perspective(self.current_perspective_name)

    @pyqtSlot()
    def _update_live_preview(self):
        """Generates and displays the code preview for the active editor."""
        editor = self.current_editor()
        if not self.live_preview_dock.isVisible() or not editor:
            self.live_preview_editor.clear()
            self.live_preview_editor.setPlaceholderText("Live Preview is off or no diagram is active.")
            return

        diagram_data = editor.scene.get_diagram_data()
        preview_mode = self.live_preview_combo.currentText()
        generated_code = ""
        editor_lang = "Text"

        try:
            if not diagram_data['states']:
                generated_code = f"// {preview_mode} Preview: Diagram is empty."
            elif preview_mode == "Python FSM":
                base_name = os.path.splitext(os.path.basename(editor.file_path or "MyFSM"))[0]
                class_name = "".join(word.capitalize() for word in base_name.replace('-', '_').split('_')) or "MyFSM"
                generated_code = generate_python_fsm_code(diagram_data, class_name)
                editor_lang = "Python"
            elif preview_mode == "C Code":
                base_filename = os.path.splitext(os.path.basename(editor.file_path or "fsm_generated"))[0]
                c_content = generate_c_code_content(diagram_data, base_filename)
                generated_code = f"// ---- {base_filename}.h ----\n\n{c_content['h']}\n\n// ---- {base_filename}.c ----\n\n{c_content['c']}"
                editor_lang = "C/C++ (Generic)"
            elif preview_mode == "PlantUML":
                diagram_name = os.path.splitext(os.path.basename(editor.file_path or "FSM_Diagram"))[0]
                generated_code = generate_plantuml_text(diagram_data, diagram_name)
            elif preview_mode == "Mermaid":
                diagram_name = os.path.splitext(os.path.basename(editor.file_path or "FSM_Diagram"))[0]
                generated_code = generate_mermaid_text(diagram_data, diagram_name)

            self.live_preview_editor.set_language(editor_lang)
            self.live_preview_editor.setPlainText(generated_code)

        except Exception as e:
            logger.error(f"Error generating live preview for {preview_mode}: {e}", exc_info=True)
            self.live_preview_editor.setPlainText(f"// Error generating {preview_mode} preview:\n// {type(e).__name__}: {e}")
            
    # --- ALL OTHER SLOTS AND METHODS --- (alphabetized for findability)

    def _add_fsm_data_to_scene(self, fsm_data: dict, clear_current_diagram: bool = False, original_user_prompt: str | None = None):
        if not isinstance(fsm_data, dict):
            QMessageBox.critical(self, "Error Adding FSM Data", "Received invalid FSM data structure.")
            return

        editor = self.add_new_editor_tab() if clear_current_diagram else self.current_editor() or self.add_new_editor_tab()

        if original_user_prompt and not editor.file_path:
            editor.set_dirty(True)

        undo_stack = editor.undo_stack
        undo_stack.beginMacro(f"Add FSM from AI: {original_user_prompt[:20] if original_user_prompt else '...'}")
        
        # Calculate offset to place new items away from existing ones
        base_x, base_y = 0, 0
        if not clear_current_diagram and editor.scene.items():
            occupied_rect = editor.scene.itemsBoundingRect()
            if not occupied_rect.isEmpty():
                base_x, base_y = occupied_rect.right() + 100, occupied_rect.top()
        
        new_items = editor.scene._add_template_to_scene(fsm_data, QPoint(base_x, base_y))

        undo_stack.endMacro()
        editor.scene.run_all_validations("AddFSMDataFromAI")
        if new_items:
            # Zoom to the newly added items
            newly_added_rect = QRectF()
            for i, item in enumerate(new_items):
                if i == 0: newly_added_rect = item.sceneBoundingRect()
                else: newly_added_rect = newly_added_rect.united(item.sceneBoundingRect())
            if not newly_added_rect.isEmpty(): editor.view.zoom_to_rect(newly_added_rect)

        self.log_message("INFO", "Successfully added FSM data to the scene.")

    @pyqtSlot(float, float, float, str)
    def _update_resource_display(self, cpu_usage, ram_usage, gpu_util, gpu_name):
        # Implementation in ui_manager for separation of concerns is good, but if called directly here...
        if not self.settings_manager.get("resource_monitor_enabled"):
            self.resource_monitor_widget.setVisible(False); return
        if not self.resource_monitor_widget.isVisible(): self.resource_monitor_widget.setVisible(True)

        self.cpu_status_label.setText(f"CPU: {cpu_usage:.0f}%")
        self.ram_status_label.setText(f"RAM: {ram_usage:.0f}%")
        gpu_text = "GPU: N/A"
        if gpu_util >= 0: gpu_text = f"GPU: {gpu_util:.0f}%"
        elif gpu_name: gpu_text = f"GPU: {gpu_name}"
        self.gpu_status_label.setText(gpu_text)
        self.gpu_status_label.setToolTip(gpu_name)
    
    # ... Continue with other implementations ...
    def on_show_preferences_dialog(self): self.action_handler.on_show_preferences_dialog()
    def _update_matlab_status_display(self, *args): pass
    def _finish_matlab_operation(self, *args): pass
    def _update_py_sim_status_display(self, *args): self.py_sim_ui_manager.update_dock_ui_contents()
    def _update_py_simulation_actions_enabled_state(self, *args): self.py_sim_ui_manager._update_internal_controls_enabled_state()
    def _update_zoom_to_selection_action_enable_state(self): self.zoom_to_selection_action.setEnabled(bool(self.current_editor() and self.current_editor().scene.selectedItems()))
    def _update_align_distribute_actions_enable_state(self):
        count = len(self.current_editor().scene.selectedItems()) if self.current_editor() else 0
        for action in self.align_actions: action.setEnabled(count >= 2)
        for action in self.distribute_actions: action.setEnabled(count >= 3)
    def update_zoom_status_display(self, scale_factor: float): self.zoom_status_label.setText(f"{int(scale_factor * 100)}%")
    def _handle_py_sim_state_changed_by_manager(self, is_running: bool): self.py_sim_active = is_running; self._update_all_ui_element_states()
    def _handle_py_sim_global_ui_enable_by_manager(self, enable: bool):
        # Lock/unlock UI elements that modify the diagram
        actions_to_toggle = [self.new_action, self.open_action, self.save_action, self.save_as_action, self.delete_action] + self.mode_action_group.actions() + self.align_actions + self.distribute_actions
        for action in actions_to_toggle: action.setEnabled(enable)
        self.elements_palette_dock.setEnabled(enable)
        self.properties_dock.setEnabled(enable) # Can still view properties, but applying is disabled by other logic
        if self.current_editor():
            for item in self.current_editor().scene.items(): item.setFlag(QGraphicsItem.ItemIsMovable, enable and self.current_editor().scene.current_mode == "select")
        
        self._update_all_ui_element_states() # Refresh states
    
    def update_problems_dock(self, issues_with_items: list):
        self.problems_list_widget.clear()
        if issues_with_items:
            for issue_msg, item_ref in issues_with_items:
                list_item_widget = QListWidgetItem(str(issue_msg))
                if item_ref: list_item_widget.setData(Qt.UserRole, item_ref)
                self.problems_list_widget.addItem(list_item_widget)
            self.problems_dock.setWindowTitle(f"Validation Issues ({len(issues_with_items)})")
        else:
            self.problems_list_widget.addItem("No validation issues found.")
            self.problems_dock.setWindowTitle("Validation Issues")

    def on_problem_item_double_clicked(self, list_item: QListWidgetItem):
        if item_ref := list_item.data(Qt.UserRole): self.focus_on_item(item_ref)

    def _on_ide_dirty_state_changed_by_manager(self, is_dirty: bool): self._update_ide_save_actions_enable_state(); self._update_window_title()
    def _on_ide_language_changed_by_manager(self, language: str): self._update_ai_features_enabled_state()
    
    def _init_internet_status_check(self): self.internet_check_timer.timeout.connect(self._run_internet_check_job); QTimer.singleShot(100, self._run_internet_check_job); self.internet_check_timer.start(30000)
    def _run_internet_check_job(self):
        try: s = socket.create_connection(("8.8.8.8", 53), timeout=1.5); s.close(); new_status, msg = True, "Online"
        except (socket.timeout, OSError): new_status, msg = False, "Offline"
        if new_status != self._internet_connected: self._internet_connected = new_status; self._update_internet_status_display(new_status, msg)

    def _update_ai_features_enabled_state(self):
        is_ready = self._internet_connected and self.ai_chatbot_manager and bool(self.ai_chatbot_manager.api_key)
        self.ask_ai_to_generate_fsm_action.setEnabled(is_ready)
        if self.ai_chat_ui_manager and self.ai_chat_ui_manager.ai_chat_send_button:
            self.ai_chat_ui_manager.ai_chat_send_button.setEnabled(is_ready)
        if hasattr(self.ide_manager, 'ide_analyze_action'): self.ide_manager.ide_analyze_action.setEnabled(is_ready and (self.ide_manager.ide_language_combo.currentText() == "Python" or self.ide_manager.ide_language_combo.currentText().startswith("C/C++")))
            
    def _update_internet_status_display(self, is_connected, msg):
        self.net_status_label.setText(msg)
        icon = QStyle.SP_DriveNetIcon if is_connected else QStyle.SP_MessageBoxWarning
        self.net_icon_label.setPixmap(get_standard_icon(icon, "Net").pixmap(QSize(12, 12)))
        self.ai_chatbot_manager.set_online_status(is_connected)
        self._update_ai_features_enabled_state()

    def on_target_device_changed(self, profile_name): self.resource_estimator.set_target(profile_name); self.update_resource_estimation()
    def update_resource_estimation(self):
        if self.resource_estimation_dock.isVisible() and (editor := self.current_editor()):
            profile_name = self.target_device_combo.currentText()
            self.resource_estimator.set_target(profile_name)
            est = self.resource_estimator.estimate(editor.scene.get_diagram_data())
            sram_b, flash_b = est['sram_b'], est['flash_b']
            total_sram, total_flash = self.resource_estimator.target_profile['sram_b'], self.resource_estimator.target_profile['flash_kb'] * 1024
            sram_p = min(100, int((sram_b / total_sram) * 100)) if total_sram > 0 else 0
            flash_p = min(100, int((flash_b / total_flash) * 100)) if total_flash > 0 else 0
            self.sram_usage_bar.setValue(sram_p); self.sram_usage_bar.setFormat(f"~{sram_b}/{total_sram} B")
            self.flash_usage_bar.setValue(flash_p); self.flash_usage_bar.setFormat(f"~{flash_b/1024:.1f}/{total_flash/1024:.0f} KB")

    def _update_ide_save_actions_enable_state(self): self.ide_manager.update_ide_save_actions_enable_state()
    def _update_matlab_actions_enabled_state(self):
        can_run = self.matlab_connection.connected and not self.py_sim_active
        self.export_simulink_action.setEnabled(can_run)
    
    def _start_matlab_operation(self, op_name):
        self.main_op_status_label.setText(f"MATLAB: {op_name}..."); self.progress_bar.setVisible(True)
    def set_ui_enabled_for_matlab_op(self, enabled):
        self.menuBar().setEnabled(enabled); self.main_toolbar.setEnabled(enabled); self.centralWidget().setEnabled(enabled)
        for dock in [self.elements_palette_dock, self.properties_dock, self.py_sim_dock]: dock.setEnabled(enabled)

    def focus_on_item(self, item_to_focus: QGraphicsItem):
        if editor := self.current_editor(): editor.view.ensureVisible(item_to_focus, 50, 50); item_to_focus.setSelected(True)
    def show_find_item_dialog_for_editor(self, editor: EditorWidget):
        if editor not in self._find_dialogs:
            dialog = FindItemDialog(self, editor.scene); dialog.item_selected_for_focus.connect(self.focus_on_item)
            self._find_dialogs[editor] = dialog
        self._find_dialogs[editor].show(); self._find_dialogs[editor].raise_()

    def _refresh_find_dialog_if_visible(self):
        if (editor := self.current_editor()) and (dialog := self._find_dialogs.get(editor)) and dialog.isVisible():
            dialog.refresh_list()
    
    @pyqtSlot(str)
    def _on_interaction_mode_changed_by_scene(self, mode: str):
        self.mode_status_label.setText(f"Mode: {mode.capitalize()}")
        icon = QStyle.SP_ArrowRight
        if mode == "state": icon = QStyle.SP_FileDialogNewFolder
        elif mode == "transition": icon = QStyle.SP_ArrowForward
        elif mode == "comment": icon = QStyle.SP_MessageBoxInformation
        self.mode_icon_label.setPixmap(get_standard_icon(icon, mode[:3]).pixmap(QSize(12,12)))

    def connect_state_item_signals(self, item: GraphicsStateItem): item.signals.textChangedViaInlineEdit.connect(self._handle_state_renamed_inline)
    
    @pyqtSlot(str, str)
    def _handle_state_renamed_inline(self, old_name: str, new_name: str):
        if (editor := self.current_editor()):
            editor.scene._update_transitions_for_renamed_state(old_name, new_name)
            self._update_properties_dock() # Refresh dock if the selected item was renamed

    @pyqtSlot(GraphicsItem)
    def _on_item_moved_in_editor(self, item: QGraphicsItem):
        if self._current_edited_item_in_dock == item: self._update_properties_dock()
    
    def on_toggle_state_breakpoint(self, *args, **kwargs): self.py_sim_ui_manager.on_toggle_state_breakpoint(*args, **kwargs)

    def _populate_recent_files_menu(self):
        self.action_handler._populate_recent_files_menu()

    def _get_property_schema_for_item(self, *args, **kwargs): return [] # No longer used directly, but keep for legacy connections if any
    def _update_dock_color_button_style(self, button, color): self.ui_manager._update_dock_color_button_style(button, color)
    def _on_dock_color_button_clicked(self, *args, **kwargs): pass # Logic is inside properties dock update
    def _on_dock_property_changed(self, *args, **kwargs): pass
    def _on_apply_dock_properties(self, *args, **kwargs): self.ui_manager._on_apply_dock_properties()
    def _on_revert_dock_properties(self, *args, **kwargs): self.ui_manager._on_revert_dock_properties()


def main_entry_point():
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)
    
    # Apply theme early before MainWindow creation for better initial appearance
    settings = SettingsManager(app_name=config.APP_NAME)
    initial_theme = settings.get("appearance_theme")
    config.DYNAMIC_UPDATE_COLORS_FROM_THEME(initial_theme)
    app.setStyleSheet(config.GET_CURRENT_STYLE_SHEET())

    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main_entry_point()