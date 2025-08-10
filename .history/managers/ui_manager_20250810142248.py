# fsm_designer_project/managers/ui_manager.py

import os
import json
from PyQt6.QtWidgets import (
    QMainWindow, QDockWidget, QToolBox, QToolBar, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QStatusBar, QTextEdit, QPushButton, QListWidget, QMenu, QStyle,
    QToolButton, QGroupBox, QComboBox, QProgressBar, QFormLayout, QGraphicsView,
    QMessageBox, QInputDialog, QLineEdit, QSizePolicy, QTreeView, QSpinBox,
    QDoubleSpinBox, QCheckBox, QColorDialog, QScrollArea, QFrame
)
from PyQt6.QtGui import QIcon, QKeySequence, QPalette, QPainter, QColor, QFont, QActionGroup, QAction, QFileSystemModel
from PyQt6.QtCore import Qt, QSize, QObject, QPointF, pyqtSlot, QDir, QEvent

from ..utils import get_standard_icon, _get_bundled_file_path
from ..utils.config import (
    COLOR_TEXT_SECONDARY, APP_FONT_SIZE_SMALL,
    COLOR_ACCENT_PRIMARY, COLOR_BORDER_LIGHT,
    COLOR_TEXT_ON_ACCENT,
    COLOR_TEXT_PRIMARY
)
from ..assets.assets import FSM_TEMPLATES_BUILTIN
from ..assets.target_profiles import TARGET_PROFILES
from ..ui.widgets.code_editor import CodeEditor
from ..utils import config
from ..ui.graphics.graphics_scene import MinimapView
from ..ui.widgets.modern_welcome_screen import ModernWelcomeScreen
from ..ui.widgets.custom_widgets import CollapsibleSection, DraggableToolButton
from ..ui.widgets.ribbon_toolbar import ProfessionalRibbon, ProfessionalGroup
from ..ui.widgets.global_search import GlobalSearchHandler
import logging

from ..managers.project_manager import PROJECT_FILE_FILTER, PROJECT_FILE_EXTENSION
from ..ui.widgets.modern_status_bar import ModernStatusBar
from ..undo_commands import EditItemPropertiesCommand
from .c_simulation_manager import CSimulationManager
from ..ui.simulation.data_dictionary_widget import DataDictionaryWidget

logger = logging.getLogger(__name__)

class UIManager(QObject):
    """
    Manages the dynamic state and interactions of the user interface after it has been constructed.
    This includes populating docks, handling property edits, and updating UI elements based on application state.
    """
    def __init__(self, main_window: QMainWindow):
        super().__init__(main_window)
        self.mw = main_window
        self._property_editors = {}
        self._current_edited_items = []
        self._props_pre_edit_data = {}
        self.global_search_handler = None
        self.c_sim_manager = CSimulationManager(main_window)

    def setup_ui(self):
        """
        Calls the UIBuilder to construct the main window's UI.
        This method is kept for backward compatibility with the old initialization sequence in main.py.
        """
        # In the new architecture, UIBuilder is called directly from MainWindow's __init__.
        # This UIManager is now primarily for state management, not building.
        # For now, we assume the UI is already built when this manager is used.
        pass

    def populate_dynamic_docks(self):
        """Populates docks that require managers to be initialized first."""
        mw = self.mw
        if hasattr(mw, 'py_sim_ui_manager') and hasattr(mw, 'py_sim_dock'):
            py_sim_contents_widget = mw.py_sim_ui_manager.create_dock_widget_contents()
            mw.py_sim_dock.setWidget(py_sim_contents_widget)
        if hasattr(self, 'c_sim_manager') and hasattr(mw, 'c_sim_dock'):
            c_sim_contents_widget = self.c_sim_manager.create_dock_widget_contents()
            mw.c_sim_dock.setWidget(c_sim_contents_widget)
        if hasattr(mw, 'ai_chat_ui_manager') and hasattr(mw, 'ai_chatbot_dock'):
            ai_chat_contents_widget = mw.ai_chat_ui_manager.create_dock_widget_contents()
            mw.ai_chatbot_dock.setWidget(ai_chat_contents_widget)
        if hasattr(mw, 'hardware_sim_ui_manager') and hasattr(mw, 'hardware_sim_dock'):
            hardware_sim_contents_widget = mw.hardware_sim_ui_manager.create_dock_widget_contents()
            mw.hardware_sim_dock.setWidget(hardware_sim_contents_widget)
        self._populate_resource_estimation_dock()

    def _populate_quick_access_toolbar(self):
        """Clears and rebuilds the Quick Access Toolbar from settings."""
        self.mw.quick_toolbar.clear()
        
        command_texts = self.mw.settings_manager.get("quick_access_commands", [])
        all_actions = self.mw.findChildren(QAction)
        action_map = {action.text().replace('&', ''): action for action in all_actions}

        for text in command_texts:
            if action := action_map.get(text):
                self.mw.quick_toolbar.addAction(action)

        self.mw.quick_toolbar.addSeparator()
        self.mw.quick_toolbar.addAction(self.mw.host_action)

        customize_btn = QToolButton()
        customize_btn.setIcon(get_standard_icon(QStyle.StandardPixmap.SP_ToolBarVerticalExtensionButton, "Cust"))
        customize_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self.mw); menu.addAction(self.mw.customize_quick_access_action); customize_btn.setMenu(menu)
        self.mw.quick_toolbar.addWidget(customize_btn)

    def _update_dock_color_button_style(self, button: QPushButton, color: QColor):
        if not color.isValid():
            return
        luminance = color.lightnessF()
        text_color = COLOR_TEXT_ON_ACCENT if luminance < 0.5 else COLOR_TEXT_PRIMARY
        button.setStyleSheet(f"""
            QPushButton#ColorButtonPropertiesDock {{
                background-color: {color.name()};
                color: {text_color};
            }}
        """)

    def _safe_get_style_enum(self, attr_name, fallback_attr_name=None):
        try:
            return getattr(QStyle.StandardPixmap, attr_name)
        except AttributeError:
            if fallback_attr_name:
                try:
                    return getattr(QStyle.StandardPixmap, fallback_attr_name)
                except AttributeError:
                    pass
            return QStyle.StandardPixmap.SP_CustomBase

    def _populate_project_explorer_dock(self):
        mw = self.mw
        mw.project_fs_model = QFileSystemModel()
        mw.project_fs_model.setRootPath(QDir.homePath())
        hidden_items = [".git", ".venv", "__pycache__", ".vscode", "*.pyc"]
        mw.project_fs_model.setNameFilters(hidden_items)
        mw.project_fs_model.setNameFilterDisables(True)
        mw.project_tree_view = QTreeView()
        mw.project_tree_view.setModel(mw.project_fs_model)
        mw.project_tree_view.setObjectName("ProjectTreeView")
        mw.project_tree_view.setHeaderHidden(True)
        for i in range(1, mw.project_fs_model.columnCount()):
            mw.project_tree_view.hideColumn(i)
        mw.project_tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        mw.project_tree_view.doubleClicked.connect(mw.action_handler.file_handler.on_project_file_double_clicked)
        mw.project_explorer_dock.setWidget(mw.project_tree_view)
        logger.debug("UIManager: Project explorer dock populated.")

    def _populate_data_dictionary_dock(self):
        """Creates and populates the data dictionary dock widget."""
        mw = self.mw
        data_dict_widget = DataDictionaryWidget(mw.data_dictionary_manager)
        mw.data_dictionary_dock.setWidget(data_dict_widget)
        logger.debug("UIManager: Data Dictionary dock populated.")

    def _populate_elements_palette_dock(self):
        mw = self.mw
        dock_widget = QWidget()
        dock_layout = QVBoxLayout(dock_widget)
        dock_layout.setContentsMargins(4, 4, 4, 4)
        dock_layout.setSpacing(4)
        self.palette_search_bar = QLineEdit()
        self.palette_search_bar.setPlaceholderText("Filter elements...")
        self.palette_search_bar.setClearButtonEnabled(True)
        dock_layout.addWidget(self.palette_search_bar)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        dock_layout.addWidget(scroll_area, 1)
        scroll_content_widget = QWidget()
        scroll_area.setWidget(scroll_content_widget)
        content_layout = QVBoxLayout(scroll_content_widget)
        content_layout.setContentsMargins(0, 4, 0, 4)
        content_layout.setSpacing(10)
        self.drag_elements_group = QGroupBox("Drag Elements")
        drag_layout = QVBoxLayout()
        drag_layout.setSpacing(4); drag_layout.setContentsMargins(4, 8, 4, 4)
        drag_items = {
            "State": ("State", "SP_ToolBarHorizontalExtensionButton"),
            "Initial State": ("Initial State", "SP_ArrowRight"),
            "Final State": ("Final State", "SP_DialogOkButton"),
            "Comment": ("Comment", "SP_MessageBoxInformation")
        }
        for text, (data, icon_name) in drag_items.items():
            icon_enum = getattr(QStyle.StandardPixmap, icon_name, QStyle.StandardPixmap.SP_CustomBase)
            btn = DraggableToolButton(text, "application/x-bsm-tool", data)
            btn.setIcon(get_standard_icon(icon_enum, text[:2]))
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            drag_layout.addWidget(btn)
        self.drag_elements_group.setLayout(drag_layout)
        content_layout.addWidget(self.drag_elements_group)
        self.templates_group = QGroupBox("FSM Templates")
        mw.template_buttons_layout = QVBoxLayout()
        mw.template_buttons_layout.setContentsMargins(4, 8, 4, 4); mw.template_buttons_layout.setSpacing(4)
        self._load_and_display_templates()
        self.templates_group.setLayout(mw.template_buttons_layout)
        content_layout.addWidget(self.templates_group)
        content_layout.addStretch()
        manage_templates_btn = QPushButton("Manage Assets...")
        manage_templates_btn.clicked.connect(self.mw.action_handler.edit_handler.on_manage_snippets)
        dock_layout.addWidget(manage_templates_btn)
        mw.elements_palette_dock.setWidget(dock_widget)
        self.palette_search_bar.textChanged.connect(self._filter_palette_elements)

    def _filter_palette_elements(self, text):
        text = text.lower()
        if hasattr(self, 'drag_elements_group'):
            for button in self.drag_elements_group.findChildren(DraggableToolButton):
                matches = text in button.text().lower()
                button.setVisible(matches)
        if hasattr(self, 'templates_group'):
            for button in self.templates_group.findChildren(DraggableToolButton):
                matches = text in button.text().lower() or text in button.toolTip().lower()
                button.setVisible(matches)

    def _load_and_display_templates(self):
        mw = self.mw; layout = mw.template_buttons_layout
        while layout.count(): 
            item = layout.takeAt(0)
            if item and item.widget(): 
                item.widget().deleteLater()
        for key, data in FSM_TEMPLATES_BUILTIN.items():
            icon_resource_path = data.get('icon_resource', ':/icons/default.png')
            icon_to_use = QIcon(icon_resource_path)
            if icon_to_use.isNull():
                logger.warning(f"Built-in template icon resource not found: {icon_resource_path}")                
                icon_to_use = get_standard_icon(QStyle.StandardPixmap.SP_FileLinkIcon, "Tpl")
            btn = DraggableToolButton(data['name'], MIME_TYPE_BSM_TEMPLATE, json.dumps(data)); btn.setIcon(icon_to_use)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            btn.setToolTip(data.get('description',''))
            layout.addWidget(btn)
        if hasattr(mw, 'custom_snippet_manager'):
            custom_templates = mw.custom_snippet_manager.get_custom_templates()
            for name, data in custom_templates.items():
                btn = DraggableToolButton(name, MIME_TYPE_BSM_TEMPLATE, json.dumps(data))
                btn.setIcon(get_standard_icon(QStyle.StandardPixmap.SP_FileLinkIcon, "CustomTpl"))
                btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
                btn.setToolTip(data.get('description', f"Custom template: {name}"))
                layout.addWidget(btn)

    def _populate_properties_dock(self):
        mw = self.mw
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        mw.properties_multi_select_container = CollapsibleSection("Align & Distribute")
        mw.properties_multi_layout = QVBoxLayout()
        mw.properties_multi_select_container.content_layout.addLayout(mw.properties_multi_layout)
        mw.properties_multi_select_container.set_collapsed(True)
        layout.addWidget(mw.properties_multi_select_container)
        mw.properties_search_bar = QLineEdit()
        mw.properties_search_bar.setPlaceholderText("Filter properties...")
        mw.properties_search_bar.setClearButtonEnabled(True)
        mw.properties_search_bar.textChanged.connect(self._on_filter_properties_dock)
        layout.addWidget(mw.properties_search_bar)
        mw.properties_placeholder_label = QLabel("<i>Select an item...</i>")
        mw.properties_placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(mw.properties_placeholder_label)
        mw.properties_editor_container = QWidget()
        mw.properties_editor_layout = QVBoxLayout(mw.properties_editor_container)
        mw.properties_editor_layout.setContentsMargins(0,0,0,0)
        mw.properties_editor_layout.setSpacing(5)
        mw.properties_editor_container.setHidden(True)
        layout.addWidget(mw.properties_editor_container)
        layout.addStretch()
        mw.properties_edit_dialog_button = QPushButton("Advanced Edit...")
        layout.addWidget(mw.properties_edit_dialog_button)
        mw.properties_dock.setWidget(widget)

    def _populate_resource_estimation_dock(self):
        mw = self.mw; widget = QWidget(); layout = QVBoxLayout(widget)
        target_group = QGroupBox("Target Device"); target_layout = QFormLayout(target_group)
        mw.target_device_combo = QComboBox(); target_layout.addRow("Profile:", mw.target_device_combo)
        for profile in TARGET_PROFILES: mw.target_device_combo.addItem(profile, TARGET_PROFILES[profile])
        layout.addWidget(target_group)
        usage_group = QGroupBox("Estimated Usage"); usage_layout = QFormLayout(usage_group)
        mw.flash_usage_bar = QProgressBar(); mw.sram_usage_bar = QProgressBar(); usage_layout.addRow("Flash/Code:", mw.flash_usage_bar); usage_layout.addRow("SRAM:", mw.sram_usage_bar)
        layout.addWidget(usage_group); disclaimer = QLabel("<small><i>Estimates are heuristics.</i></small>"); disclaimer.setWordWrap(True); layout.addWidget(disclaimer); layout.addStretch(); mw.resource_estimation_dock.setWidget(widget)

    def _populate_live_preview_dock(self):
        mw = self.mw
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        toolbar = QToolBar("Scratchpad Toolbar")
        toolbar.setIconSize(QSize(16, 16))
        toolbar.addWidget(QLabel(" Language: "))
        mw.live_preview_combo = QComboBox()
        mw.live_preview_combo.addItems(["Python FSM", "C Code", "PlantUML", "Mermaid"])
        toolbar.addWidget(mw.live_preview_combo)
        toolbar.addSeparator()
        mw.scratchpad_revert_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_BrowserReload, "Revert"), "Regenerate from Diagram", mw)
        mw.scratchpad_revert_action.setToolTip("Discard edits and reload code from the visual diagram.")
        mw.scratchpad_sync_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_ArrowUp, "Sync"), "Sync Code to Diagram", mw)
        mw.scratchpad_sync_action.setToolTip("Parse the code below and replace the current diagram.")
        toolbar.addAction(mw.scratchpad_revert_action)
        toolbar.addAction(mw.scratchpad_sync_action)
        mw.scratchpad_sync_action.setEnabled(False)
        layout.addWidget(toolbar)
        mw.live_preview_editor = CodeEditor()
        mw.live_preview_editor.setReadOnly(False) 
        mw.live_preview_editor.setObjectName("LivePreviewEditor") 
        mw.live_preview_editor.setPlaceholderText("Code from the diagram will appear here. You can also edit it and sync back.")
        layout.addWidget(mw.live_preview_editor, 1)
        mw.live_preview_dock.setWidget(widget)

    def _populate_serial_monitor_dock(self):
        mw = self.mw
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        mw.serial_monitor_output = QTextEdit()
        mw.serial_monitor_output.setReadOnly(True)
        mw.serial_monitor_output.setObjectName("SerialMonitorOutput")
        mw.serial_monitor_output.setPlaceholderText("Raw serial data will appear here when connected...")
        font = QFont("Consolas, 'Courier New', monospace")
        font.setPointSize(9)
        mw.serial_monitor_output.setFont(font)
        layout.addWidget(mw.serial_monitor_output)
        mw.serial_monitor_dock.setWidget(widget)