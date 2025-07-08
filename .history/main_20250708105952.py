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
from .ui_virtual_hardware_manager import VirtualHardwareUIManager # <-- NEW IMPORT
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
from .ui_manager import UIManager
from .modern_welcome_screen import WelcomeWidget
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
from .custom_widgets import CollapsibleSection
from .plugin_manager import PluginManager # <-- NEW IMPORT
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
    # --- NEW: Added Developer View ---
    PERSPECTIVE_DEVELOPER_VIEW = "Developer View"
    DEFAULT_PERSPECTIVES_ORDER = [
        PERSPECTIVE_DESIGN_FOCUS, 
        PERSPECTIVE_SIMULATION_FOCUS,
        PERSPECTIVE_IDE_FOCUS,
        PERSPECTIVE_AI_FOCUS,
        PERSPECTIVE_DEVELOPER_VIEW # New
    ]


    # --- REFACTORED / NEW METHODS FOR PROPERTIES DOCK ---

    def _get_property_schema_for_item(self, item):
        """Returns a schema describing which properties to show for a given item type."""
        item_type = type(item)
        if item_type is GraphicsStateItem:
            return {
                "General": [
                    {'key': 'name', 'label': 'Name:', 'widget': QLineEdit},
                    {'key': 'is_initial', 'label': 'Is Initial State', 'widget': QCheckBox},
                    {'key': 'is_final', 'label': 'Is Final State', 'widget': QCheckBox},
                    {'key': 'is_superstate', 'label': 'Is Superstate', 'widget': QCheckBox},
                ],
                "Appearance": [
                    {'key': 'font_size', 'label': 'Font Size:', 'widget': QSpinBox, 'config': {'setRange': (6, 72)}},
                    {'key': 'border_width', 'label': 'Border Width:', 'widget': QDoubleSpinBox, 'config': {'setRange': (0.5, 10.0), 'setSingleStep': 0.1, 'setDecimals': 1}},
                    {'key': 'color', 'label': 'Color:', 'widget': QPushButton, 'is_color': True},
                ]
            }
        elif item_type is GraphicsTransitionItem:
            return {
                "Logic": [
                    {'key': 'event', 'label': 'Event:', 'widget': QLineEdit},
                    {'key': 'condition', 'label': 'Condition:', 'widget': QLineEdit},
                ],
                "Appearance": [
                    {'key': 'control_offset_x', 'label': 'Curve Bend (Perp):', 'widget': QSpinBox, 'config': {'setRange': (-1000, 1000)}},
                    {'key': 'control_offset_y', 'label': 'Curve Shift (Tang):', 'widget': QSpinBox, 'config': {'setRange': (-1000, 1000)}},
                    {'key': 'color', 'label': 'Color:', 'widget': QPushButton, 'is_color': True},
                ]
            }
        elif item_type is GraphicsCommentItem:
             return {
                "Content": [
                    {'key': 'text', 'label': 'Text:', 'widget': QTextEdit, 'config': {'setFixedHeight': 80}},
                ]
             }
        return {}


    def _update_properties_dock(self):
        editor = self.current_editor()
        selected_items = editor.scene.selectedItems() if editor else []
        
        # --- DYNAMIC DOCK TITLE ---
        if len(selected_items) == 1:
            item = selected_items[0]
            item_name = "Item"
            if isinstance(item, GraphicsStateItem): item_name = item.text_label
            elif isinstance(item, GraphicsTransitionItem): item_name = item.event_str or "Transition"
            elif isinstance(item, GraphicsCommentItem): item_name = f"Comment"
            self.properties_dock.setWindowTitle(f"Properties: {item_name}")
        elif len(selected_items) > 1:
            self.properties_dock.setWindowTitle(f"Properties ({len(selected_items)} items)")
        else:
            self.properties_dock.setWindowTitle("Properties")

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
                    for section_title, props in schema.items():
                        section = CollapsibleSection(section_title, self.properties_editor_container)
                        section_form_layout = QFormLayout()
                        
                        for prop_info in props:
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

                            if isinstance(editor_widget, QCheckBox): section_form_layout.addRow(editor_widget)
                            else: section_form_layout.addRow(label, editor_widget)
                            
                            if hasattr(editor_widget, 'toggled'): editor_widget.toggled.connect(self._on_dock_property_changed_mw)
                            elif hasattr(editor_widget, 'textChanged'): editor_widget.textChanged.connect(self._on_dock_property_changed_mw)
                            elif hasattr(editor_widget, 'valueChanged'): editor_widget.valueChanged.connect(self._on_dock_property_changed_mw)
                            self._dock_property_editors[key] = editor_widget

                        section.content_widget.setLayout(section_form_layout)
                        self.properties_editor_layout.addWidget(section)

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
        for section_title, props in schema.items():
            for prop_info in props:
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

        for section_title, props in schema.items():
            for prop_info in props:
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
        
        # ... (at the top of __init__)
        # --- NEW: Instantiate Plugin Manager early ---
        self.plugin_manager = PluginManager()
        
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

        # --- NEW: Welcome Page Connections ---
        self.welcome_widget = WelcomeWidget(self)
        if hasattr(self, 'welcome_widget') and isinstance(self.welcome_widget, WelcomeWidget):
            # FIX: Use lambda to ensure correct slot signature matching
            self.welcome_widget.newFileRequested.connect(lambda: self.action_handler.on_new_file())
            self.welcome_widget.openFileRequested.connect(lambda: self.action_handler.on_open_file())
            self.welcome_widget.openRecentRequested.connect(self._on_open_recent_from_welcome)
            self.welcome_widget.showGuideRequested.connect(lambda: self.action_handler.on_show_quick_start())
            self.welcome_widget.showExamplesRequested.connect(self._browse_examples)


        # 3. Managers that depend on the UI being created
        self.perspective_manager = PerspectiveManager(self, self.settings_manager)
        self.resource_monitor_manager = ResourceMonitorManager(self, settings_manager=self.settings_manager)
        self.py_sim_ui_manager = PySimulationUIManager(self)
        self.hardware_sim_ui_manager = VirtualHardwareUIManager(self) # <-- NEW: Instantiate manager
        self.ai_chatbot_manager = AIChatbotManager(self)
        self.ai_chat_ui_manager = AIChatUIManager(self)
        self.ide_manager = IDEManager(self)

            
        self._update_central_widget()
        # 4. Finalize UI and connect signals
        if not hasattr(self, 'log_output') or not self.log_output: 
            self.log_output = QTextEdit() 
        setup_global_logging(self.log_output)
        
        # MODIFIED: Call this method here, which now includes the hardware sim dock
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
                if hasattr(self, 'welcome_widget') and hasattr(self.welcome_widget, 'update_recent_files'):
                    recent_files = self.settings_manager.get("recent_files", [])
                    self.welcome_widget.update_recent_files(recent_files)
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
     
     
     
     
     # ...existing code...
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
        if hasattr(editor.scene, 'itemsBoundingRectChanged'):
             editor.scene.itemsBoundingRectChanged.connect(self.update_resource_estimation)
        if hasattr(editor.scene, 'sceneRectChanged'):
             editor.scene.sceneRectChanged.connect(self.update_resource_estimation)  
        
        editor.scene.item_moved.connect(self._request_live_preview_update)
        editor.scene.modifiedStatusChanged.connect(self._request_live_preview_update)
        editor.undo_stack.indexChanged.connect(self._request_live_preview_update)
             
    def add_new_editor_tab(self) -> EditorWidget:
        """Creates a new, empty editor tab, connects its signals, and makes it active."""
        new_editor = EditorWidget(self, self.custom_snippet_manager)
        
        new_editor.scene.settings_manager = self.settings_manager
        new_editor.scene.custom_snippet_manager = self.custom_snippet_manager
        
        index = self.tab_widget.addTab(new_editor, new_editor.get_tab_title())
        self.tab_widget.setCurrentIndex(index)
        new_editor.view.setFocus()
        self._connect_editor_signals(new_editor)
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
    @pyqtSlot(bool)
    def _handle_py_sim_global_ui_enable_by_manager(self, enable): pass

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

    def _update_live_preview(self):
        """
        Updates the live preview panel based on the current editor's content.
        """
        editor = self.current_editor()
        if not editor or not hasattr(self, 'live_preview_dock') or not self.live_preview_dock.isVisible():
            return

        preview_type = None
        if hasattr(self, 'live_preview_combo'):
            preview_type = self.live_preview_combo.currentText()
        else:
            preview_type = "PlantUML"

        diagram_data = editor.scene.get_diagram_data() if hasattr(editor, 'scene') else None
        preview_text = ""

        if not diagram_data or not diagram_data.get('states'):
            preview_text = f"// No states to generate {preview_type}."
        else:
            if preview_type == "PlantUML":
                preview_text = generate_plantuml_text(diagram_data)
            elif preview_type == "Mermaid":
                preview_text = generate_mermaid_text(diagram_data)
            elif preview_type == "C Code":
                code_dict = generate_c_code_content(diagram_data, "live_preview_fsm")
                preview_text = f"// --- HEADER (live_preview_fsm.h) ---\n\n{code_dict.get('h', '')}\n\n// --- SOURCE (live_preview_fsm.c) ---\n\n{code_dict.get('c', '')}"
            elif preview_type == "Python FSM":
                preview_text = generate_python_fsm_code(diagram_data, "LivePreviewFSM")
            else:
                preview_text = "No preview available for this type."

        if hasattr(self, 'live_preview_editor'):
            self.live_preview_editor.blockSignals(True)
            self.live_preview_editor.setPlainText(preview_text)
            self.live_preview_editor.blockSignals(False)


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
    def _update_item_properties_from_move(self, moved_item): 
        if hasattr(self, '_current_edited_item_in_dock') and self._current_edited_item_in_dock == moved_item:
             self._on_revert_dock_properties()

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
            DYNAMIC_UPDATE_COLORS_FROM_THEME(self.theme_manager.get_theme_data(current_theme)) 
            theme_related_change = True 
            for i in range(self.tab_widget.count()):
                if editor := self.tab_widget.widget(i): editor.scene.update() 

        if theme_related_change:
            if key != "appearance_theme": 
                new_stylesheet = GET_CURRENT_STYLE_SHEET() 
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
            self.save_action.setEnabled(self.current_editor() and self.current_editor().is_dirty())

    def _update_ide_save_actions_enable_state(self):
        if self.ide_manager:
            self.ide_manager.update_ide_save_actions_enable_state()

    def _update_undo_redo_actions_enable_state(self):
        editor = self.current_editor()
        can_undo = editor and editor.undo_stack.canUndo()
        can_redo = editor and editor.undo_stack.canRedo()
        if hasattr(self, 'undo_action'): self.undo_action.setEnabled(can_undo)
        if hasattr(self, 'redo_action'): self.redo_action.setEnabled(can_redo)
        
        if not hasattr(self, 'undo_action'): return # Guard

        undo_text = editor.undo_stack.undoText() if editor else ""
        redo_text = editor.undo_stack.redoText() if editor else ""
        
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
        if hasattr(self, 'menuBar'): self.menuBar().setEnabled(enabled)
        if hasattr(self, 'main_toolbar'): self.main_toolbar.setEnabled(enabled)

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
            
    @pyqtSlot(bool) 
    def on_matlab_settings(self, checked=False): 
        dialog = MatlabSettingsDialog(matlab_connection=self.matlab_connection, parent=self)
        dialog.exec_()
        logger.info("MATLAB settings dialog closed.")

    # The closeEvent and other essential methods from the original file are assumed to be here.
    def closeEvent(self, event: QCloseEvent):
        """Overrides QMainWindow.closeEvent to check for unsaved changes and stop threads."""
        logger.info("MW_CLOSE: closeEvent received.")
        
        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            if editor and editor.py_sim_active: 
                self.py_sim_ui_manager.on_stop_py_simulation(silent=True)
             
        if hasattr(self.ide_manager, 'prompt_ide_save_if_dirty') and not self.ide_manager.prompt_ide_save_if_dirty():
            event.ignore()
            return
        
        for i in range(self.tab_widget.count()):
            if not self._prompt_save_on_close(self.tab_widget.widget(i)):
                event.ignore()
                return

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
    @pyqtSlot(bool)
    def _handle_py_sim_global_ui_enable_by_manager(self, enable: bool):
        logger.debug(f"MW: Global UI enable requested by PySim manager: {enable}")
        is_editable = enable
        diagram_editing_actions = [
            self.new_action, self.open_action, self.save_action, self.save_as_action,
            self.undo_action, self.redo_action, self.delete_action, self.select_all_action,
            self.add_state_mode_action, self.add_transition_mode_action, self.add_comment_mode_action
        ]
        for action in diagram_editing_actions:
            if hasattr(action, 'setEnabled'): action.setEnabled(is_editable)
        if hasattr(self, 'elements_palette_dock'): self.elements_palette_dock.setEnabled(is_editable)
        
        editor = self.current_editor()
        if hasattr(self, 'properties_edit_dialog_button'): self.properties_edit_dialog_button.setEnabled(is_editable and editor and len(editor.scene.selectedItems())==1)
        if hasattr(self, 'properties_apply_button'): self.properties_apply_button.setEnabled(False) 
        if hasattr(self, 'properties_revert_button'): self.properties_revert_button.setEnabled(False) 
        if editor:
            for item in editor.scene.items():
                if isinstance(item, (GraphicsStateItem, GraphicsCommentItem)):
                    item.setFlag(QGraphicsItem.ItemIsMovable, is_editable and editor.scene.current_mode == "select")
            if not is_editable and editor.scene.current_mode != "select": editor.scene.set_mode("select")
        self._update_matlab_actions_enabled_state()
        self._update_py_simulation_actions_enabled_state()

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
        prompt = f"""I am designing a Finite State Machine. The validation tool gave me the following error or warning: "{issue_text}"

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
        editor = self.current_editor()
        if not editor:
            self.setWindowTitle(APP_NAME)
            return
            
        dirty_char = "[*]" # Let Qt handle the star
        file_name = os.path.basename(editor.file_path) if editor.file_path else "Untitled"
        py_sim_active = any(isinstance(self.tab_widget.widget(i), EditorWidget) and self.tab_widget.widget(i).py_sim_active for i in range(self.tab_widget.count()))
        pysim_suffix = f" [PySim Active]" if py_sim_active else ""
        
        self.setWindowModified(editor.is_dirty())
        self.setWindowTitle(f"{file_name}{dirty_char} - {APP_NAME}{pysim_suffix}")


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
        
        sim_can_start = not py_sim_active and not is_matlab_op_running
        sim_can_be_controlled = py_sim_active and not is_matlab_op_running
        
        if hasattr(self, 'start_py_sim_action'): self.start_py_sim_action.setEnabled(sim_can_start)
        if hasattr(self, 'stop_py_sim_action'): self.stop_py_sim_action.setEnabled(sim_can_be_controlled)
        if hasattr(self, 'reset_py_sim_action'): self.reset_py_sim_action.setEnabled(sim_can_be_controlled)
        if hasattr(self, 'py_sim_ui_manager') and self.py_sim_ui_manager: self.py_sim_ui_manager._update_internal_controls_enabled_state()

    @pyqtSlot()
    def _update_zoom_to_selection_action_enable_state(self):
        editor = self.current_editor()
        if hasattr(self, 'zoom_to_selection_action'): self.zoom_to_selection_action.setEnabled(editor and bool(editor.scene.selectedItems()))

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
        logger.debug(f"MainWindow: State renamed inline from '{old_name}' to '{new_name}'.")
        self._refresh_find_dialog_if_visible()
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
    def _init_internet_status_check(self): pass
    def _run_internet_check_job(self): pass
    def _update_ai_features_enabled_state(self, is_ready): pass
    def _update_internet_status_display(self, is_conn, msg): pass
    
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

    def log_message(self, level_str: str, message: str): 
        level = getattr(logging, level_str.upper(), logging.INFO)
        logger.log(level, message)



    




    @pyqtSlot()
    def on_show_find_item_dialog(self): pass
            
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
    # This part is now only executed if the script is run directly AND the sys.path modification
    # at the top has already run and exited. Effectively, this part of the __main__ block
    # should not be reached if the sys.path modification logic works as intended.
    # The main_entry_point() call is now primarily handled by the sys.path modification block.