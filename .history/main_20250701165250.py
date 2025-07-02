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
    QIcon, QKeySequence, QCloseEvent, QPalette, QColor, QPen, QFont, QDesktopServices
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QDockWidget, QAction,
    QToolBar, QVBoxLayout, QWidget, QLabel,
    QStatusBar, QTextEdit,
    QPushButton, QMenu, QMessageBox,
    QInputDialog, QLineEdit, QColorDialog, QDialog, QFormLayout,
    QSpinBox, QComboBox, QDoubleSpinBox,
    QUndoStack, QStyle, QTabWidget, QGraphicsItem, QCheckBox,QHBoxLayout
)
from PyQt5.QtWidgets import QListWidgetItem
from PyQt5.QtCore import QPointF

# Local application imports
from .graphics_scene import DiagramScene, ZoomableView
from .graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem
from .undo_commands import EditItemPropertiesCommand, AddItemCommand
from .matlab_integration import MatlabConnection
from .settings_manager import SettingsManager
from .resource_estimator import ResourceEstimator
from . import config  
from .config import ( 
    APP_VERSION, APP_NAME,
    DYNAMIC_UPDATE_COLORS_FROM_THEME, GET_CURRENT_STYLE_SHEET,
    COLOR_TEXT_SECONDARY, APP_FONT_SIZE_SMALL, COLOR_ACCENT_PRIMARY
)
from .theme_manager import ThemeManager
from .ui_manager import UIManager, WelcomeWidget # MODIFIED: Import WelcomeWidget
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
from .git_manager import GitManager
from .perspective_manager import PerspectiveManager

# Import the new code generation functions
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


    # --- REFACTORED / NEW METHODS FOR PROPERTIES DOCK ---

    def _get_property_schema_for_item(self, item):
        """Returns a schema describing which properties to show for a given item type."""
        item_type = type(item)
        if item_type is GraphicsStateItem:
            return [
                {'key': 'name', 'label': 'Name:', 'widget': QLineEdit},
                {'key': 'font_size', 'label': 'Font Size:', 'widget': QSpinBox, 'config': {'setRange': (6, 72)}},
                {'key': 'border_width', 'label': 'Border Width:', 'widget': QDoubleSpinBox, 'config': {'setRange': (0.5, 10.0), 'setSingleStep': 0.1, 'setDecimals': 1}},
                {'key': 'is_initial', 'label': 'Is Initial State', 'widget': QCheckBox},
                {'key': 'is_final', 'label': 'Is Final State', 'widget': QCheckBox},
                {'key': 'is_superstate', 'label': 'Is Superstate', 'widget': QCheckBox},
                {'key': 'color', 'label': 'Color:', 'widget': QPushButton, 'is_color': True},
            ]
        elif item_type is GraphicsTransitionItem:
            return [
                {'key': 'event', 'label': 'Event:', 'widget': QLineEdit},
                {'key': 'condition', 'label': 'Condition:', 'widget': QLineEdit},
                {'key': 'control_offset_x', 'label': 'Curve Bend (Perp):', 'widget': QSpinBox, 'config': {'setRange': (-1000, 1000)}},
                {'key': 'control_offset_y', 'label': 'Curve Shift (Tang):', 'widget': QSpinBox, 'config': {'setRange': (-1000, 1000)}},
                {'key': 'color', 'label': 'Color:', 'widget': QPushButton, 'is_color': True},
            ]
        elif item_type is GraphicsCommentItem:
             return [
                {'key': 'text', 'label': 'Text:', 'widget': QTextEdit, 'config': {'setFixedHeight': 80}},
             ]
        return []



    def _update_properties_dock(self):
        editor = self.current_editor()
        selected_items = editor.scene.selectedItems() if editor else []
        
        # --- MODIFIED: Clear old content ---
        while self.properties_editor_layout.count():
            child_item = self.properties_editor_layout.takeAt(0)
            if widget := child_item.widget():
                widget.deleteLater()
        
        while self.properties_multi_layout.count():
            child_item = self.properties_multi_layout.takeAt(0)
            if widget := child_item.widget():
                widget.deleteLater()

        self._dock_property_editors.clear()
        self._current_edited_item_in_dock = None
        self._current_edited_item_original_props_in_dock = {}
        
        show_editor = False
        show_multi_select_editor = False

        if len(selected_items) == 1:
            self._current_edited_item_in_dock = selected_items[0]
            if hasattr(self._current_edited_item_in_dock, 'get_data'):
                item_data = self._current_edited_item_in_dock.get_data()
                self._current_edited_item_original_props_in_dock = item_data.copy()
                
                schema = self._get_property_schema_for_item(self._current_edited_item_in_dock)

                if schema:
                    show_editor = True
                    for prop_info in schema:
                        key = prop_info['key']
                        label = prop_info['label']
                        WidgetClass = prop_info['widget']
                        current_value = item_data.get(key, None)

                        editor_widget = WidgetClass()
                        if isinstance(editor_widget, QLineEdit): editor_widget.setText(str(current_value or ''))
                        elif isinstance(editor_widget, QTextEdit): editor_widget.setPlainText(str(current_value or ''))
                        elif isinstance(editor_widget, QCheckBox): editor_widget.setChecked(bool(current_value))
                        elif isinstance(editor_widget, QSpinBox): editor_widget.setValue(int(current_value or 0))
                        elif isinstance(editor_widget, QDoubleSpinBox): editor_widget.setValue(float(current_value or 0))
                        
                        if widget_config := prop_info.get('config'):
                            for method_name, args in widget_config.items():
                                if hasattr(editor_widget, method_name):
                                    if isinstance(args, tuple): getattr(editor_widget, method_name)(*args)
                                    else: getattr(editor_widget, method_name)(args)

                        if prop_info.get('is_color', False) and isinstance(editor_widget, QPushButton):
                            editor_widget.setObjectName("ColorButtonPropertiesDock")
                            color = QColor(current_value) if current_value else QColor(Qt.white)
                            self._update_dock_color_button_style(editor_widget, color)
                            editor_widget.setProperty("currentColorHex", color.name())
                            editor_widget.clicked.connect(lambda ch, btn=editor_widget: self._on_dock_color_button_clicked(btn))

                        if isinstance(editor_widget, QCheckBox): self.properties_editor_layout.addRow(editor_widget)
                        else: self.properties_editor_layout.addRow(label, editor_widget)
                        
                        if hasattr(editor_widget, 'toggled'): editor_widget.toggled.connect(self._on_dock_property_changed_mw)
                        elif hasattr(editor_widget, 'textChanged'): editor_widget.textChanged.connect(self._on_dock_property_changed_mw)
                        elif hasattr(editor_widget, 'valueChanged'): editor_widget.valueChanged.connect(self._on_dock_property_changed_mw)
                        self._dock_property_editors[key] = editor_widget
                else:
                    self.properties_placeholder_label.setText(f"<i>Editing: {type(self._current_edited_item_in_dock).__name__}.<br>Use 'Advanced Edit...' for details.</i>")
        
        # --- NEW: Handle multi-selection ---
        elif len(selected_items) > 1:
            show_multi_select_editor = True
            
            # Add align/distribute actions directly to the dock
            align_distribute_label = QLabel("<b>Align & Distribute</b>")
            self.properties_multi_layout.addWidget(align_distribute_label)
            
            align_layout = QHBoxLayout()
            align_layout.addWidget(QPushButton("Left", clicked=self.align_left_action.trigger))
            align_layout.addWidget(QPushButton("Center", clicked=self.align_center_h_action.trigger))
            align_layout.addWidget(QPushButton("Right", clicked=self.align_right_action.trigger))
            self.properties_multi_layout.addLayout(align_layout)
            
            valign_layout = QHBoxLayout()
            valign_layout.addWidget(QPushButton("Top", clicked=self.align_top_action.trigger))
            valign_layout.addWidget(QPushButton("Middle", clicked=self.align_middle_v_action.trigger))
            valign_layout.addWidget(QPushButton("Bottom", clicked=self.align_bottom_action.trigger))
            self.properties_multi_layout.addLayout(valign_layout)
            
            distribute_layout = QHBoxLayout()
            distribute_layout.addWidget(QPushButton("Dist. Horiz.", clicked=self.distribute_h_action.trigger))
            distribute_layout.addWidget(QPushButton("Dist. Vert.", clicked=self.distribute_v_action.trigger))
            self.properties_multi_layout.addLayout(distribute_layout)
            
            self.properties_multi_layout.addStretch()

        self.properties_editor_container.setVisible(show_editor)
        self.properties_multi_select_container.setVisible(show_multi_select_editor)
        self.properties_placeholder_label.setVisible(not show_editor and not show_multi_select_editor)
        self.properties_edit_dialog_button.setEnabled(show_editor)

        if not selected_items:
             self.properties_placeholder_label.setText(f"<i>No item selected.</i><br><span style='font-size:{config.APP_FONT_SIZE_SMALL}; color:{config.COLOR_TEXT_SECONDARY};'>Click an item or use tools to add elements.</span>")
        
        self.properties_apply_button.setEnabled(False)
        self.properties_revert_button.setEnabled(False)


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
    def on_matlab_settings(self): pass
    @pyqtSlot(str, object)
    def _handle_setting_changed(self, key, value): pass
    @pyqtSlot()
    def _on_dock_property_changed_mw(self): 
        if hasattr(self, 'properties_apply_button'): self.properties_apply_button.setEnabled(True)
        if hasattr(self, 'properties_revert_button'): self.properties_revert_button.setEnabled(True)

    def _on_apply_dock_properties(self):
        if not self._current_edited_item_in_dock or not self._current_edited_item_original_props_in_dock: return
        
        old_props = self._current_edited_item_original_props_in_dock.copy()
        new_props = old_props.copy() # Start with old to ensure all props are preserved
        
        schema = self._get_property_schema_for_item(self._current_edited_item_in_dock)
        
        something_changed = False
        for prop_info in schema:
            key = prop_info['key']
            editor = self._dock_property_editors.get(key)
            if not editor: continue
            
            new_val = None
            if isinstance(editor, QLineEdit): new_val = editor.text().strip()
            elif isinstance(editor, QTextEdit): new_val = editor.toPlainText().strip()
            elif isinstance(editor, QCheckBox): new_val = editor.isChecked()
            elif isinstance(editor, (QSpinBox, QDoubleSpinBox)): new_val = editor.value()
            elif prop_info.get('is_color'): new_val = editor.property("currentColorHex")
            
            if new_val is not None and new_val != old_props.get(key):
                new_props[key] = new_val
                something_changed = True

        if not something_changed:
            logger.info("Properties in dock are identical to original, no changes applied.")
            self.properties_apply_button.setEnabled(False)
            self.properties_revert_button.setEnabled(False)
            return

        # Validate name for StateItems before proceeding
        if isinstance(self._current_edited_item_in_dock, GraphicsStateItem):
            new_name = new_props.get('name', '')
            if not new_name:
                QMessageBox.warning(self, "Invalid Name", "State name cannot be empty."); return
            
            editor = self.current_editor()
            if not editor: return
            
            existing_state = editor.scene.get_state_by_name(new_name)
            if new_name != old_props.get('name') and existing_state and existing_state != self._current_edited_item_in_dock:
                QMessageBox.warning(self, "Duplicate Name", f"A state named '{new_name}' already exists."); return

        cmd = EditItemPropertiesCommand(self._current_edited_item_in_dock, old_props, new_props, f"Edit Properties via Dock")
        
        if editor := self.current_editor():
            editor.undo_stack.push(cmd) 
        
        self._current_edited_item_original_props_in_dock = new_props.copy()

        self.properties_apply_button.setEnabled(False)
        self.properties_revert_button.setEnabled(False)
        self.log_message("INFO", f"Properties updated via dock for item.")



    def _on_revert_dock_properties(self):
        if not self._current_edited_item_in_dock or not self._current_edited_item_original_props_in_dock: return

        original_props = self._current_edited_item_original_props_in_dock
        schema = self._get_property_schema_for_item(self._current_edited_item_in_dock)

        for prop_info in schema:
            key = prop_info['key']
            editor = self._dock_property_editors.get(key)
            original_value = original_props.get(key)
            if not editor or original_value is None: continue
            
            editor.blockSignals(True)
            if isinstance(editor, QLineEdit): editor.setText(str(original_value))
            elif isinstance(editor, QTextEdit): editor.setPlainText(str(original_value))
            elif isinstance(editor, QCheckBox): editor.setChecked(bool(original_value))
            elif isinstance(editor, (QSpinBox, QDoubleSpinBox)): editor.setValue(original_value)
            elif prop_info.get('is_color'):
                color = QColor(original_value)
                self._update_dock_color_button_style(editor, color)
                editor.setProperty("currentColorHex", color.name())
            editor.blockSignals(False)
            
        self.properties_apply_button.setEnabled(False)
        self.properties_revert_button.setEnabled(False)
        self.log_message("INFO", "Properties in dock reverted to selection state.")

    def __init__(self):
        super().__init__()
        
        # --- CORRECTED INITIALIZATION ORDER ---

        # 1. Core non-UI managers and settings
        if not hasattr(QApplication.instance(), 'settings_manager'):
             QApplication.instance().settings_manager = SettingsManager(app_name=APP_NAME)
        self.settings_manager = QApplication.instance().settings_manager
        self.theme_manager = ThemeManager()
        self.custom_snippet_manager = CustomSnippetManager(app_name=APP_NAME)
        self.resource_estimator = ResourceEstimator()
        self.matlab_connection = MatlabConnection()
        self.git_manager = GitManager(self)
        self.action_handler = ActionHandler(self)
        self._find_dialogs = {}
        self.live_preview_update_timer = QTimer(self)
        self.live_preview_update_timer.setSingleShot(True)
        self.live_preview_update_timer.setInterval(300) # 300ms delay
        self._dock_property_editors = {}
        self._current_edited_item_in_dock = None
        self._current_edited_item_original_props_in_dock = {}

        # 2. Central UI setup
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.setDocumentMode(True)
        
        self.ui_manager = UIManager(self)
        self.ui_manager.setup_ui() # CRITICAL: This creates all menus, docks, and toolbars

        # 3. Managers that depend on the UI being created
        self.perspective_manager = PerspectiveManager(self, self.settings_manager)
        self.resource_monitor_manager = ResourceMonitorManager(self, settings_manager=self.settings_manager)
        self.py_sim_ui_manager = PySimulationUIManager(self)
        self.ai_chatbot_manager = AIChatbotManager(self)
        self.ai_chat_ui_manager = AIChatUIManager(self)
        self.ide_manager = IDEManager(self)
        
        # --- NEW: Welcome Page Setup ---
        self.welcome_widget = WelcomeWidget(self)
        self._update_central_widget()

        # 4. Finalize UI and connect signals
        if not hasattr(self, 'log_output') or not self.log_output: 
            self.log_output = QTextEdit() 
        setup_global_logging(self.log_output)
        
        self.ui_manager.populate_dynamic_docks()
        self._connect_application_signals() 
        self._apply_initial_settings()
        self.restore_geometry_and_state()

        # 5. Start background services and initial actions
        self._internet_connected: bool | None = None
        self.internet_check_timer = QTimer(self)
        self._init_internet_status_check()
        if self.settings_manager.get("resource_monitor_enabled"):
            self.resource_monitor_manager.setup_and_start_monitor()

        self._set_status_label_object_names() 
        QTimer.singleShot(100, lambda: self.perspective_manager.apply_perspective(self.perspective_manager.current_perspective_name))
        QTimer.singleShot(250, lambda: self.ai_chatbot_manager.set_online_status(self._internet_connected if self._internet_connected is not None else False))
        
        logger.info("Main window initialization complete.")
    
    # --- NEW: Welcome Page Logic ---
    def _update_central_widget(self):
        """Swaps the central widget between the tab widget and the welcome page."""
        if self.tab_widget.count() == 0:
            if self.centralWidget() != self.welcome_widget:
                self.setCentralWidget(self.welcome_widget)
                self.welcome_widget.update_recent_files()
        else:
            if self.centralWidget() != self.tab_widget:
                self.setCentralWidget(self.tab_widget)
    
    def _connect_application_signals(self):
        """Central hub for all application-level signal connections."""
        logger.debug("Connecting application-level signals...")
        
        self.action_handler.connect_actions()
        
        if hasattr(self, 'preferences_action'):
            self.preferences_action.triggered.connect(self.on_show_preferences_dialog)
            
        self.tab_widget.currentChanged.connect(self._on_current_tab_changed)
        self.tab_widget.tabCloseRequested.connect(self._on_close_tab_requested)
        
        if hasattr(self, 'properties_apply_button'): self.properties_apply_button.clicked.connect(self._on_apply_dock_properties)
        if hasattr(self, 'properties_revert_button'): self.properties_revert_button.clicked.connect(self._on_revert_dock_properties)
        if hasattr(self, 'properties_edit_dialog_button'): self.properties_edit_dialog_button.clicked.connect(lambda: self.current_editor().scene.edit_item_properties(self._current_edited_item_in_dock) if self.current_editor() and self._current_edited_item_in_dock else None)
        
        if hasattr(self, 'problems_ask_ai_btn'):
            self.problems_ask_ai_btn.clicked.connect(self.on_ask_ai_about_validation_issue)

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
            self.py_sim_ui_manager.requestGlobalUIEnable.connect(self._handle_py_sim_global_ui_enable_by_manager)
        if self.ide_manager:
            self.ide_manager.ide_dirty_state_changed.connect(self._on_ide_dirty_state_changed_by_manager)
            self.ide_manager.ide_file_path_changed.connect(self._update_window_title)
            self.ide_manager.ide_language_combo_changed.connect(self._on_ide_language_changed_by_manager)
        if hasattr(self, 'target_device_combo'):
            self.target_device_combo.currentTextChanged.connect(self.on_target_device_changed)

        self.live_preview_update_timer.timeout.connect(self._update_live_preview)
        if hasattr(self, 'live_preview_combo'):
            self.live_preview_combo.currentTextChanged.connect(self._request_live_preview_update)
        if hasattr(self, 'live_preview_dock'):
            self.live_preview_dock.visibilityChanged.connect(self._request_live_preview_update)

        logger.info("Application-level signals connected.")
   
       
    # --- NEW Method for Recent Files Menu ---
    def _populate_recent_files_menu(self):
        if hasattr(self, 'recent_files_menu'):
            self.recent_files_menu.clear()
            recent_files = self.settings_manager.get("recent_files", [])
            if not recent_files:
                self.recent_files_menu.addAction("(No Recent Files)").setEnabled(False)
                return
            for i, file_path in enumerate(recent_files):
                action = QAction(f"&{i+1} {os.path.basename(file_path)}", self, triggered=self.action_handler.on_open_recent_file)
                action.setData(file_path)
                action.setToolTip(file_path)
                self.recent_files_menu.addAction(action)
            self.recent_files_menu.addSeparator()
            self.recent_files_menu.addAction("Clear List", self._clear_recent_files_list)
    
    def _clear_recent_files_list(self):
        self.settings_manager.set("recent_files", [])
        self.log_message("INFO", "Recent files list cleared.")
     
    def _apply_theme(self, theme_name: str):
        logger.info(f"Applying theme: {theme_name}")

        app_instance = QApplication.instance()

        theme_data = self.theme_manager.get_theme_data(theme_name)
        if not theme_data:
            logger.error(f"Theme '{theme_name}' not found. Falling back to Light theme.")
            theme_data = self.theme_manager.get_theme_data("Light")

        DYNAMIC_UPDATE_COLORS_FROM_THEME(theme_data) 
        new_stylesheet = GET_CURRENT_STYLE_SHEET()
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

    # --- Architecture Change: Tab Management Methods ---
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
        if hasattr(editor.scene, 'itemsBoundingRectChanged'):
             editor.scene.itemsBoundingRectChanged.connect(self.update_resource_estimation)
        if hasattr(editor.scene, 'sceneRectChanged'):
             editor.scene.sceneRectChanged.connect(self.update_resource_estimation)  
        
        editor.scene.item_moved.connect(self._request_live_preview_update)
        editor.scene.modifiedStatusChanged.connect(self._request_live_preview_update)
        editor.undo_stack.indexChanged.connect(self._request_live_preview_update)
             
             
    def add_new_editor_tab(self) -> EditorWidget:
        """Creates a new, empty editor tab, connects its signals, and makes it active."""
        new_editor = EditorWidget(self, self.custom_snippet_manager, self.settings_manager)
        
        new_editor.scene.settings_manager = self.settings_manager
        new_editor.scene.custom_snippet_manager = self.custom_snippet_manager
        
        index = self.tab_widget.addTab(new_editor, new_editor.get_tab_title())
        self.tab_widget.setCurrentIndex(index)
        new_editor.view.setFocus()
        self._connect_editor_signals(new_editor)
        self._on_current_tab_changed(index)
        self._update_window_title()
        self._update_central_widget()
        QTimer.singleShot(10, self._update_git_menu_actions_state)
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


    def _update_live_preview(self):
        """Updates the live preview panel based on the current editor's content."""
        editor = self.current_editor()
        if not editor or not hasattr(self, 'live_preview_dock') or not self.live_preview_dock.isVisible():
            return

        preview_type = self.live_preview_combo.currentText() if hasattr(self, 'live_preview_combo') else "PlantUML"
        diagram_data = editor.scene.get_diagram_data() if hasattr(editor, 'scene') else None
        preview_text = ""

        if not diagram_data or not diagram_data.get('states'):
            preview_text = f"// No states to generate {preview_type}."
        else:
            try:
                if preview_type == "PlantUML": preview_text = generate_plantuml_text(diagram_data)
                elif preview_type == "Mermaid": preview_text = generate_mermaid_text(diagram_data)
                elif preview_type == "C Code":
                    code_dict = generate_c_code_content(diagram_data, "live_preview_fsm")
                    preview_text = f"// --- HEADER (live_preview_fsm.h) ---\n\n{code_dict.get('h', '')}\n\n// --- SOURCE (live_preview_fsm.c) ---\n\n{code_dict.get('c', '')}"
                elif preview_type == "Python FSM": preview_text = generate_python_fsm_code(diagram_data, "LivePreviewFSM")
            except Exception as e:
                preview_text = f"// Error generating preview for {preview_type}:\n// {e}"
                logger.error(f"Error during live preview generation for {preview_type}", exc_info=True)


        if hasattr(self, 'live_preview_editor'):
            self.live_preview_editor.blockSignals(True)
            self.live_preview_editor.setPlainText(preview_text)
            self.live_preview_editor.blockSignals(False)


    def _request_live_preview_update(self, *args):
        """Requests a live preview update by starting/restarting the timer."""
        if hasattr(self, 'live_preview_update_timer'):
            self.live_preview_update_timer.start()

    def _on_git_command_finished(self, success: bool, stdout: str, stderr: str):
        self.set_ui_for_git_op(False, "Git operation finished.")
        if success:
            QMessageBox.information(self, "Git Success", f"Git operation completed:\n\n{stdout}\n{stderr}")
        else:
            QMessageBox.critical(self, "Git Error", f"Git operation failed:\n\n{stderr}\n\n{stdout}")
        
        if editor := self.current_editor():
            if editor.file_path:
                self.git_manager.check_file_status(editor.file_path)

    def set_ui_for_git_op(self, is_running: bool, op_name: str):
        if hasattr(self, 'main_op_status_label'): self.main_op_status_label.setText(f"Git: {op_name}...")
        if hasattr(self, 'progress_bar'): self.progress_bar.setVisible(is_running)
        self.setEnabled(not is_running)         

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


    @pyqtSlot(int)
    def _on_current_tab_changed(self, index: int):
        if hasattr(self, 'undo_action'): 
            try: self.undo_action.triggered.disconnect()
            except (TypeError, RuntimeError): pass
        if hasattr(self, 'redo_action'): 
            try: self.redo_action.triggered.disconnect()
            except (TypeError, RuntimeError): pass
        
        editor = self.current_editor()
        if editor:
            if hasattr(self, 'undo_action'): self.undo_action.triggered.connect(editor.undo_stack.undo)
            if hasattr(self, 'redo_action'): self.redo_action.triggered.connect(editor.undo_stack.redo)
            editor.undo_stack.canUndoChanged.connect(self.undo_action.setEnabled)
            editor.undo_stack.canRedoChanged.connect(self.redo_action.setEnabled)
            editor.undo_stack.undoTextChanged.connect(lambda text, a=self.undo_action: a.setText(f"&Undo {text}"))
            editor.undo_stack.redoTextChanged.connect(lambda text, a=self.redo_action: a.setText(f"&Redo {text}"))

        if editor and hasattr(self, 'minimap_view'):
            self.minimap_view.setScene(editor.scene)
            self.minimap_view.setMainView(editor.view)
            QTimer.singleShot(50, self.minimap_view.update_viewport_rect)
        elif hasattr(self, 'minimap_view'):
            self.minimap_view.setScene(None)

        if editor and editor.file_path and self.git_manager:
            self.git_manager.check_file_status(editor.file_path)

        self._update_git_menu_actions_state()
        self._update_all_ui_element_states()

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
        self._update_properties_dock()
        self._update_py_simulation_actions_enabled_state()
        self._update_zoom_to_selection_action_enable_state()
        self._update_align_distribute_actions_enable_state()
        self.update_resource_estimation()
        
        if editor := self.current_editor():
            if editor.view: self.update_zoom_status_display(editor.view.transform().m11())
        
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
    
    @pyqtSlot(QGraphicsItem)
    def _update_item_properties_from_move(self, moved_item): 
        if hasattr(self, '_current_edited_item_in_dock') and self._current_edited_item_in_dock == moved_item:
             self._on_revert_dock_properties()

    @pyqtSlot(str, object)
    def _handle_setting_changed(self, key: str, value: object):
        logger.info(f"Setting '{key}' changed to '{value}'. Updating UI.")
        
        if key == "appearance_theme":
            self._apply_theme(str(value))
        elif key.startswith("view_"):
            if editor := self.current_editor():
                setattr(editor.scene, key.replace("view_", "") + "_enabled", bool(value))
                editor.scene.update()
        elif key.startswith("canvas_"):
            if editor := self.current_editor():
                editor.scene.update()

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
        if hasattr(self, 'main_op_status_label'): self.main_op_status_label.setObjectName("MainOpStatusLabel")
        if hasattr(self, 'mode_status_label'): self.mode_status_label.setObjectName("InteractionModeStatusLabel") 

    # --- Start of Restored Method Implementations ---

    def _init_internet_status_check(self):
        self.internet_check_timer.timeout.connect(self._run_internet_check_job)
        self.internet_check_timer.start(15000) 
        QTimer.singleShot(100, self._run_internet_check_job) 

    def _run_internet_check_job(self):
        current_status = False; status_detail = "Checking..."
        try:
            s = socket.create_connection(("8.8.8.8", 53), timeout=1.5) 
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

    def _update_internet_status_display(self, is_connected: bool, message_detail: str):
        if hasattr(self, 'internet_status_label') and self.internet_status_label:
            self.internet_status_label.setText(message_detail)
            self.internet_status_label.parentWidget().setToolTip(f"Internet Status: {message_detail}")
            if hasattr(self, 'net_icon_label'):
                 self.net_icon_label.setPixmap(get_standard_icon(QStyle.SP_DriveNetIcon if is_connected else QStyle.SP_MessageBoxCritical, "Net").pixmap(QSize(12,12)))

        logging.debug("Internet Status Update: %s", message_detail)
        key_present = self.ai_chatbot_manager is not None and self.ai_chatbot_manager.is_configured()
        ai_ready = is_connected and key_present
        if hasattr(self.ai_chatbot_manager, 'set_online_status'): self.ai_chatbot_manager.set_online_status(is_connected)
        self._update_ai_features_enabled_state(ai_ready)

    def _update_ai_features_enabled_state(self, is_online_and_key_present: bool):
        actions_to_toggle = [
            getattr(self, 'ask_ai_to_generate_fsm_action', None),
            getattr(self, 'clear_ai_chat_action', None),
            getattr(self, 'ide_analyze_action', None),
            getattr(self, 'problems_ask_ai_btn', None)
        ]
        for action in actions_to_toggle:
            if action: action.setEnabled(is_online_and_key_present)
        
        if self.ai_chat_ui_manager:
            self.ai_chat_ui_manager.update_status_display(self.ai_chatbot_manager.get_current_ai_status(), "Status text would be updated by manager")

    @pyqtSlot(list)
    def update_problems_dock(self, issues_with_items: list):
        if not hasattr(self, 'problems_list_widget'): return
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
        
        if hasattr(self, 'problems_ask_ai_btn'):
            self.problems_ask_ai_btn.setEnabled(False) # Reset on update, enable on selection

    @pyqtSlot()
    def _update_undo_redo_actions_enable_state(self):
        editor = self.current_editor()
        can_undo = editor and editor.undo_stack.canUndo()
        can_redo = editor and editor.undo_stack.canRedo()
        if hasattr(self, 'undo_action'): self.undo_action.setEnabled(can_undo)
        if hasattr(self, 'redo_action'): self.redo_action.setEnabled(can_redo)
        
        if not hasattr(self, 'undo_action'): return
        undo_text = editor.undo_stack.undoText() if editor else ""
        redo_text = editor.undo_stack.redoText() if editor else ""
        
        self.undo_action.setText(f"&Undo{(' ' + undo_text) if undo_text else ''}")
        self.redo_action.setText(f"&Redo{(' ' + redo_text) if redo_text else ''}")
        self.undo_action.setToolTip(f"Undo: {undo_text}" if undo_text else "Undo")
        self.redo_action.setToolTip(f"Redo: {redo_text}" if redo_text else "Redo")

    @pyqtSlot()
    def _update_save_actions_enable_state(self):
        if hasattr(self, 'save_action'):
            self.save_action.setEnabled(self.current_editor() and self.current_editor().is_dirty())

    @pyqtSlot()
    def _update_ide_save_actions_enable_state(self):
        if self.ide_manager:
            self.ide_manager.update_ide_save_actions_enable_state()

    @pyqtSlot()
    def _update_py_simulation_actions_enabled_state(self):
        if self.py_sim_ui_manager:
            self.py_sim_ui_manager._update_internal_controls_enabled_state()

    @pyqtSlot()
    def _update_zoom_to_selection_action_enable_state(self):
        editor = self.current_editor()
        if hasattr(self, 'zoom_to_selection_action'): 
            self.zoom_to_selection_action.setEnabled(editor and bool(editor.scene.selectedItems()))

    @pyqtSlot()
    def _update_align_distribute_actions_enable_state(self):
        editor = self.current_editor()
        selected_count = len(editor.scene.selectedItems()) if editor else 0
        if hasattr(self, 'align_actions'):
            for action in self.align_actions: action.setEnabled(selected_count >= 2)
        if hasattr(self, 'distribute_actions'):
            for action in self.distribute_actions: action.setEnabled(selected_count >= 3)
            
    # --- End of Restored Method Implementations ---

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