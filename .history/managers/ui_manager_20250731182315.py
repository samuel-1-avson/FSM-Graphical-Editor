# fsm_designer_project/managers/ui_manager.py
import sip 
import os
import json
from PyQt5.QtWidgets import (
    QMainWindow, QDockWidget, QToolBox, QAction, QToolBar, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QStatusBar, QTextEdit, QPushButton, QListWidget, QMenu, QActionGroup, QStyle,
    QToolButton, QGroupBox, QComboBox, QProgressBar, QFormLayout, QGraphicsView,
    QMessageBox, QInputDialog, QLineEdit, QSizePolicy, QTreeView, QFileSystemModel,QSpinBox,
    QDoubleSpinBox, QCheckBox, QColorDialog
)
from PyQt5.QtGui import QIcon, QKeySequence, QPalette, QPainter, QColor, QFont
from PyQt5.QtCore import Qt, QSize, QObject, QPointF, pyqtSlot, QDir, QEvent

from ..utils import get_standard_icon, _get_bundled_file_path
from ..utils.config import (
    APP_VERSION, APP_NAME, FILE_FILTER, MIME_TYPE_BSM_TEMPLATE,
    COLOR_TEXT_SECONDARY, APP_FONT_SIZE_SMALL,
    COLOR_ACCENT_PRIMARY, COLOR_BORDER_LIGHT, COLOR_BACKGROUND_APP
)
from ..assets.assets import FSM_TEMPLATES_BUILTIN
from ..assets.target_profiles import TARGET_PROFILES
from ..ui.widgets.code_editor import CodeEditor
from ..utils import config
from ..ui.graphics.graphics_scene import MinimapView
from ..ui.widgets.modern_welcome_screen import ModernWelcomeScreen
from ..ui.widgets.custom_widgets import CollapsibleSection, DraggableToolButton
from ..ui.widgets.ribbon_toolbar import ModernRibbon, RibbonGroup
from ..ui.widgets.global_search import GlobalSearchHandler
import logging

from ..managers.project_manager import PROJECT_FILE_FILTER, PROJECT_FILE_EXTENSION
from ..ui.widgets.modern_status_bar import ModernStatusBar
from ..undo_commands import EditItemPropertiesCommand

logger = logging.getLogger(__name__)

class StatusSegment(QWidget):
    def __init__(self, icon_enum, icon_alt, initial_text, tooltip, obj_name, parent=None):
        super().__init__(parent)
        self.setObjectName(f"{obj_name}_Container")
        self.setToolTip(tooltip)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(3)
        self.icon_label = QLabel()
        self.icon_label.setPixmap(get_standard_icon(icon_enum, icon_alt).pixmap(QSize(12, 12)))
        self.text_label = QLabel(initial_text)
        self.text_label.setObjectName(obj_name)
        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)

    def setText(self, text):
        self.text_label.setText(text)

    def setIcon(self, icon: QIcon):
        self.icon_label.setPixmap(icon.pixmap(QSize(12, 12)))

class UIManager(QObject): 
    def __init__(self, main_window: QMainWindow):
        super().__init__(main_window) 
        self.mw = main_window
        self._property_editors = {}
        self._current_edited_items = []
        self._props_pre_edit_data = {}
        self.global_search_handler = None

    def _safe_get_style_enum(self, attr_name, fallback_attr_name=None):
        try:
            return getattr(QStyle, attr_name)
        except AttributeError:
            if fallback_attr_name:
                try:
                    return getattr(QStyle, fallback_attr_name)
                except AttributeError:
                    pass
            return QStyle.SP_CustomBase

    def setup_ui(self):
        self.mw.setWindowIcon(get_standard_icon(QStyle.SP_DesktopIcon, "BSM"))
        self._create_actions()
        self._create_ribbon()
        self._create_docks()
        self._create_status_bar()

    def populate_dynamic_docks(self):
        mw = self.mw
        if hasattr(mw, 'py_sim_ui_manager') and hasattr(mw, 'py_sim_dock'):
            py_sim_contents_widget = mw.py_sim_ui_manager.create_dock_widget_contents()
            mw.py_sim_dock.setWidget(py_sim_contents_widget)
        if hasattr(mw, 'ai_chat_ui_manager') and hasattr(mw, 'ai_chatbot_dock'):
            ai_chat_contents_widget = mw.ai_chat_ui_manager.create_dock_widget_contents()
            mw.ai_chatbot_dock.setWidget(ai_chat_contents_widget)
        if hasattr(mw, 'hardware_sim_ui_manager') and hasattr(mw, 'hardware_sim_dock'):
            hardware_sim_contents_widget = mw.hardware_sim_ui_manager.create_dock_widget_contents()
            mw.hardware_sim_dock.setWidget(hardware_sim_contents_widget)
        self._populate_resource_estimation_dock()

    def _create_actions(self):
        mw = self.mw
        mw.new_action = QAction(get_standard_icon(QStyle.SP_FileIcon, "New"), "&New Project...", mw, shortcut=QKeySequence.New, statusTip="Create a new project or diagram file")
        mw.open_action = QAction(get_standard_icon(QStyle.SP_DialogOpenButton, "Opn"), "&Open Project/File...", mw, shortcut=QKeySequence.Open, statusTip="Open an existing project or file")
        mw.save_action = QAction(get_standard_icon(QStyle.SP_DialogSaveButton, "Sav"), "&Save File", mw, shortcut=QKeySequence.Save, statusTip="Save the current active file", enabled=False)
        mw.save_as_action = QAction(get_standard_icon(self._safe_get_style_enum("SP_DriveHDIcon", "SP_DialogSaveButton"), "SA"), "Save File &As...", mw, shortcut=QKeySequence.SaveAs, statusTip="Save the current file with a new name")
        mw.save_as_action.setEnabled(False)
        mw.close_project_action = QAction(get_standard_icon(QStyle.SP_DialogCancelButton, "CloseProj"), "Close Project", mw, statusTip="Close the current project", enabled=False)
        mw.import_from_text_action = QAction(get_standard_icon(QStyle.SP_FileLinkIcon, "Imp"), "Import from Text...", mw, statusTip="Create a diagram from PlantUML or Mermaid text")
        mw.exit_action = QAction(get_standard_icon(QStyle.SP_DialogCloseButton, "Exit"), "E&xit", mw, shortcut=QKeySequence.Quit, triggered=mw.close)
        # --- MODIFICATION: Actions are now defined here but grouped in the new ribbon tab ---
        mw.export_png_action = QAction(get_standard_icon(self._safe_get_style_enum("SP_MediaSave", "Img"), "Export PNG"), "&PNG Image...", mw)
        mw.export_svg_action = QAction(get_standard_icon(self._safe_get_style_enum("SP_MediaSave", "Img"), "Export SVG"), "&SVG Image...", mw)
        mw.export_simulink_action = QAction(get_standard_icon(QStyle.SP_ComputerIcon, "Simulink"), "&Simulink Model...", mw)
        mw.generate_c_code_action = QAction(get_standard_icon(QStyle.SP_DialogSaveButton, "C"), "Basic &C/C++ Code...", mw)
        mw.export_python_fsm_action = QAction(get_standard_icon(QStyle.SP_DialogSaveButton, "Py"), "&Python FSM Class...", mw)
        mw.export_plantuml_action = QAction(get_standard_icon(QStyle.SP_FileLinkIcon, "Doc"), "&PlantUML...", mw)
        mw.export_mermaid_action = QAction(get_standard_icon(QStyle.SP_FileLinkIcon, "Doc"), "&Mermaid...", mw)
        testbench_icon = get_standard_icon(self._safe_get_style_enum("SP_FileIcon", "Test"), "Test")
        mw.export_c_testbench_action = QAction(testbench_icon, "C &Testbench...", mw, statusTip="Generate a C test harness for the FSM")
        hdl_icon = get_standard_icon(self._safe_get_style_enum("SP_DriveNetIcon", "SP_ComputerIcon"), "HDL")
        mw.export_vhdl_action = QAction(hdl_icon, "&VHDL Code...", mw, statusTip="Export the FSM as synthesizable VHDL code")
        mw.export_verilog_action = QAction(hdl_icon, "&Verilog Code...", mw, statusTip="Export the FSM as synthesizable Verilog code")
        mw.undo_action = QAction(get_standard_icon(QStyle.SP_ArrowBack, "Un"), "&Undo", mw, shortcut=QKeySequence.Undo)
        mw.redo_action = QAction(get_standard_icon(QStyle.SP_ArrowForward, "Re"), "&Redo", mw, shortcut=QKeySequence.Redo)
        mw.delete_action = QAction(get_standard_icon(QStyle.SP_TrashIcon, "Del"), "&Delete", mw, shortcut=QKeySequence.Delete)
        mw.select_all_action = QAction("Select &All", mw, shortcut=QKeySequence.SelectAll)
        mw.find_item_action = QAction("&Find Item...", mw, shortcut=QKeySequence.Find)
        mw.manage_snippets_action = QAction("Manage Custom Snippets...", mw)
        mw.save_selection_as_template_action = QAction("Save Selection as Template...", mw, enabled=False) 
        mw.manage_fsm_templates_action = QAction("Manage FSM Templates...", mw)
        mw.preferences_action = QAction(get_standard_icon(QStyle.SP_FileDialogDetailedView, "Prefs"), "&Preferences...", mw)
        mw.log_clear_action = QAction(get_standard_icon(QStyle.SP_DialogResetButton, "Clr"), "Clear Log", mw)
        mw.log_save_action = QAction(get_standard_icon(QStyle.SP_DialogSaveButton, "SaveLog"), "Save Log As...", mw)
        mw.log_copy_action = QAction(get_standard_icon(QStyle.SP_FileLinkIcon, "CpyLog"), "Copy All to Clipboard", mw)
        mw.mode_action_group = QActionGroup(mw); mw.mode_action_group.setExclusive(True)
        def create_mode_action(name, text, icon_name, shortcut):
            action = QAction(get_standard_icon(getattr(QStyle, icon_name), shortcut), text, mw, checkable=True)
            action.setShortcut(shortcut); action.setToolTip(f"Activate {text} mode ({shortcut})")
            mw.mode_action_group.addAction(action)
            return action
        mw.select_mode_action = create_mode_action("select", "Select/Move", "SP_ArrowRight", "S")
        mw.add_state_mode_action = create_mode_action("state", "Add State", "SP_FileDialogNewFolder", "A")
        mw.add_transition_mode_action = create_mode_action("transition", "Add Transition", "SP_ArrowForward", "T")
        mw.add_comment_mode_action = create_mode_action("comment", "Add Comment", "SP_MessageBoxInformation", "C")
        mw.select_mode_action.setChecked(True)
        mw.align_left_action = QAction("Align Left", mw)
        mw.align_center_h_action = QAction("Align Center Horizontally", mw)
        mw.align_right_action = QAction("Align Right", mw)
        mw.align_top_action = QAction("Align Top", mw)
        mw.align_middle_v_action = QAction("Align Middle Vertically", mw)
        mw.align_bottom_action = QAction("Align Bottom", mw)
        mw.distribute_h_action = QAction("Distribute Horizontally", mw)
        mw.distribute_v_action = QAction("Distribute Vertically", mw)
        mw.align_actions = [mw.align_left_action, mw.align_center_h_action, mw.align_right_action, mw.align_top_action, mw.align_middle_v_action, mw.align_bottom_action]
        mw.distribute_actions = [mw.distribute_h_action, mw.distribute_v_action]
        for action in mw.align_actions + mw.distribute_actions: action.setEnabled(False)
        mw.zoom_in_action = QAction("Zoom In", mw, shortcut="Ctrl++")
        mw.zoom_out_action = QAction("Zoom Out", mw, shortcut="Ctrl+-")
        mw.reset_zoom_action = QAction("Reset Zoom/View", mw, shortcut="Ctrl+0")
        mw.zoom_to_selection_action = QAction("Zoom to Selection", mw, enabled=False)
        mw.fit_diagram_action = QAction("Fit Diagram in View", mw)
        mw.auto_layout_action = QAction("Auto-Layout Diagram", mw, shortcut="Ctrl+L")
        mw.show_grid_action = QAction("Show Grid", mw, checkable=True, checked=True)
        mw.snap_to_objects_action = QAction("Snap to Objects", mw, checkable=True, checked=True)
        mw.snap_to_grid_action = QAction("Snap to Grid", mw, checkable=True, checked=True)
        mw.show_snap_guidelines_action = QAction("Show Dynamic Snap Guidelines", mw, checkable=True, checked=True)
        mw.save_perspective_action = QAction("Save Current As...", mw)
        mw.reset_perspectives_action = QAction("Reset to Defaults", mw)
        mw.start_py_sim_action = QAction(get_standard_icon(QStyle.SP_MediaPlay, "Py▶"), "&Start Python Simulation", mw)
        mw.stop_py_sim_action = QAction(get_standard_icon(QStyle.SP_MediaStop, "Py■"), "S&top Python Simulation", mw, enabled=False)
        mw.reset_py_sim_action = QAction(get_standard_icon(QStyle.SP_MediaSkipBackward, "Py«"), "&Reset Python Simulation", mw, enabled=False)
        mw.run_simulation_action = QAction(get_standard_icon(QStyle.SP_MediaPlay, "Run"), "&Run in MATLAB...", mw)
        mw.git_commit_action = QAction("Commit...", mw)
        mw.git_push_action = QAction("Push", mw)
        mw.git_pull_action = QAction("Pull", mw)
        mw.git_show_changes_action = QAction("Show Changes...", mw)
        mw.git_actions = [mw.git_commit_action, mw.git_push_action, mw.git_pull_action, mw.git_show_changes_action]
        for action in mw.git_actions: action.setEnabled(False)
        mw.ide_new_file_action = QAction(get_standard_icon(QStyle.SP_FileIcon, "IDENew"), "New Script", mw)
        mw.ide_open_file_action = QAction(get_standard_icon(QStyle.SP_DialogOpenButton, "IDEOpn"), "Open Script...", mw)
        mw.ide_save_file_action = QAction(get_standard_icon(QStyle.SP_DialogSaveButton, "IDESav"), "Save Script", mw)
        mw.ide_save_as_file_action = QAction("Save Script As...", mw)
        mw.ide_run_script_action = QAction(get_standard_icon(QStyle.SP_MediaPlay, "IDERunPy"), "Run Python Script", mw)
        mw.ide_analyze_action = QAction("Analyze with AI", mw)
        mw.ide_analyze_selection_action = QAction("Analyze Selection with AI", mw)
        mw.show_resource_estimation_action = QAction("Resource Estimation", mw, checkable=True)
        mw.show_live_preview_action = QAction("Live Code Preview", mw, checkable=True)
        mw.ask_ai_to_generate_fsm_action = QAction("Generate FSM from Description...", mw)
        mw.clear_ai_chat_action = QAction("Clear Chat History", mw)
        mw.openai_settings_action = QAction("AI Assistant Settings...", mw)
        mw.quick_start_action = QAction(get_standard_icon(QStyle.SP_MessageBoxQuestion, "QS"), "&Quick Start Guide", mw)
        mw.about_action = QAction(get_standard_icon(QStyle.SP_DialogHelpButton, "?"), "&About", mw)
        mw.customize_quick_access_action = QAction("Customize Quick Access Toolbar...", mw)
        mw.host_action = QAction(get_standard_icon(QStyle.SP_ComputerIcon, "Host"), "Host", mw)
        logger.debug("UIManager: Actions created.")

    def _create_ribbon(self):
        mw = self.mw
        for tb in mw.findChildren(QToolBar):
            mw.removeToolBar(tb)
            tb.deleteLater()
        if mw.menuBar():
            mw.menuBar().clear()
            mw.setMenuBar(None)

        # --- MODIFICATION: Create the Quick Access Toolbar ---
        self.quick_toolbar = QToolBar("Quick Access")
        self.quick_toolbar.setMovable(False)
        self.quick_toolbar.setFixedHeight(28)
        mw.addToolBar(Qt.TopToolBarArea, self.quick_toolbar)

        mw.ribbon = ModernRibbon(mw)
        ribbon_container_toolbar = QToolBar("Ribbon")
        ribbon_container_toolbar.setObjectName("RibbonToolbarContainer")
        ribbon_container_toolbar.setMovable(False)
        ribbon_container_toolbar.addWidget(mw.ribbon)
        mw.addToolBar(Qt.TopToolBarArea, ribbon_container_toolbar)

        # --- NEW: Instantiate and connect the global search handler ---
        self.global_search_handler = GlobalSearchHandler(mw, mw.ribbon.search_bar)

        mw.view_menu = QMenu("&View", mw)
        mw.toolbars_menu = mw.view_menu.addMenu("Toolbars")
        mw.docks_menu = mw.view_menu.addMenu("Docks & Panels")
        mw.perspectives_menu = mw.view_menu.addMenu("Perspectives")
        mw.toolbars_menu.clear()
        mw.toolbars_menu.addAction(self.quick_toolbar.toggleViewAction())
        mw.toolbars_menu.addAction(ribbon_container_toolbar.toggleViewAction())

        file_menu = QMenu(mw)
        file_menu.addActions([mw.new_action, mw.open_action])
        mw.recent_files_menu = file_menu.addMenu("Open &Recent")
        mw.recent_files_menu.aboutToShow.connect(mw._populate_recent_files_menu)
        file_menu.addSeparator()
        example_menu = file_menu.addMenu("Open E&xample")
        mw.open_example_traffic_action = QAction("Traffic Light FSM", mw)
        mw.open_example_toggle_action = QAction("Simple Toggle FSM", mw)
        example_menu.addActions([mw.open_example_traffic_action, mw.open_example_toggle_action])
        file_menu.addSeparator()
        file_menu.addAction(mw.import_from_text_action)
        file_menu.addSeparator()
        file_menu.addActions([mw.save_action, mw.save_as_action, mw.close_project_action])
        file_menu.addSeparator()
        file_menu.addAction(mw.preferences_action)
        file_menu.addSeparator()
        file_menu.addAction(mw.exit_action)
        mw.ribbon.set_file_menu(file_menu)

        home_tab = mw.ribbon.add_tab("Home")
        clipboard_group = RibbonGroup("Clipboard")
        clipboard_group.add_action_button(mw.undo_action)
        clipboard_group.add_action_button(mw.redo_action)
        home_tab.add_group(clipboard_group)
        editing_group = RibbonGroup("Editing")
        editing_group.add_action_button(mw.delete_action)
        editing_group.add_action_button(mw.select_all_action, is_large=False)
        editing_group.add_action_button(mw.find_item_action, is_large=False)
        home_tab.add_group(editing_group)
        mode_group = RibbonGroup("Mode")
        for action in mw.mode_action_group.actions():
            mode_group.add_action_button(action, is_large=False)
        home_tab.add_group(mode_group)
        layout_group = RibbonGroup("Layout")
        layout_group.add_action_button(mw.auto_layout_action)
        align_btn = QToolButton(); align_btn.setText("Align"); align_btn.setPopupMode(QToolButton.InstantPopup)
        align_menu = QMenu(mw); align_menu.addActions(mw.align_actions); align_btn.setMenu(align_menu)
        dist_btn = QToolButton(); dist_btn.setText("Distribute"); dist_btn.setPopupMode(QToolButton.InstantPopup)
        dist_menu = QMenu(mw); dist_menu.addActions(mw.distribute_actions); dist_btn.setMenu(dist_menu)
        layout_group.add_widget(align_btn)
        layout_group.add_widget(dist_btn)
        home_tab.add_group(layout_group)

        view_tab = mw.ribbon.add_tab("View")
        zoom_group = RibbonGroup("Zoom")
        zoom_group.add_action_button(mw.zoom_in_action)
        zoom_group.add_action_button(mw.zoom_out_action)
        zoom_group.add_action_button(mw.reset_zoom_action)
        zoom_group.add_separator()
        zoom_group.add_action_button(mw.fit_diagram_action)
        zoom_group.add_action_button(mw.zoom_to_selection_action)
        view_tab.add_group(zoom_group)
        canvas_group = RibbonGroup("Canvas")
        canvas_group.add_action_button(mw.show_grid_action, is_large=False)
        canvas_group.add_action_button(mw.snap_to_grid_action, is_large=False)
        canvas_group.add_action_button(mw.snap_to_objects_action, is_large=False)
        canvas_group.add_action_button(mw.show_snap_guidelines_action, is_large=False)
        view_tab.add_group(canvas_group)
        window_group = RibbonGroup("Window")
        perspectives_btn = QToolButton(); perspectives_btn.setText("Perspectives"); perspectives_btn.setPopupMode(QToolButton.InstantPopup)
        perspectives_btn.setMenu(mw.perspectives_menu)
        docks_btn = QToolButton(); docks_btn.setText("Docks"); docks_btn.setPopupMode(QToolButton.InstantPopup)
        docks_btn.setMenu(mw.docks_menu)
        window_group.add_widget(perspectives_btn)
        window_group.add_widget(docks_btn)
        view_tab.add_group(window_group)

        sim_tab = mw.ribbon.add_tab("Simulation")
        pysim_group = RibbonGroup("Python Simulation")
        pysim_group.add_action_button(mw.start_py_sim_action)
        pysim_group.add_action_button(mw.stop_py_sim_action)
        pysim_group.add_action_button(mw.reset_py_sim_action)
        sim_tab.add_group(pysim_group)
        # --- MODIFICATION: Cleaned up MATLAB group ---
        matlab_group = RibbonGroup("MATLAB/Simulink")
        matlab_group.add_action_button(mw.run_simulation_action)
        # Note: MATLAB settings moved to Preferences dialog, Export moved to Code & Export tab.
        sim_tab.add_group(matlab_group)

        # --- NEW TAB: Code Export ---
        code_export_tab = mw.ribbon.add_tab("Code Export")
        code_gen_group = RibbonGroup("Generate Code")
        mw.export_arduino_action = QAction(get_standard_icon(QStyle.SP_DialogSaveButton, "ino"), "Arduino Sketch...", mw)
        code_gen_group.add_action_button(mw.export_python_fsm_action, is_large=False)
        code_gen_group.add_action_button(mw.generate_c_code_action, is_large=False)
        code_gen_group.add_action_button(mw.export_arduino_action, is_large=False)
        code_gen_group.add_action_button(mw.export_c_testbench_action, is_large=False)
        code_export_tab.add_group(code_gen_group)
        hdl_group = RibbonGroup("Generate HDL")
        hdl_group.add_action_button(mw.export_vhdl_action, is_large=False)
        hdl_group.add_action_button(mw.export_verilog_action, is_large=False)
        code_export_tab.add_group(hdl_group)
        model_export_group = RibbonGroup("Model Export")
        model_export_group.add_action_button(mw.export_simulink_action)
        code_export_tab.add_group(model_export_group)
        doc_export_group = RibbonGroup("Export Document")
        doc_export_group.add_action_button(mw.export_plantuml_action, is_large=False)
        doc_export_group.add_action_button(mw.export_mermaid_action, is_large=False)
        doc_export_group.add_action_button(mw.export_png_action, is_large=False)
        doc_export_group.add_action_button(mw.export_svg_action, is_large=False)
        code_export_tab.add_group(doc_export_group)

        ai_tab = mw.ribbon.add_tab("AI Assistant")
        ai_gen_group = RibbonGroup("Generation")
        ai_gen_group.add_action_button(mw.ask_ai_to_generate_fsm_action)
        ai_tab.add_group(ai_gen_group)
        ai_chat_group = RibbonGroup("Chat")
        ai_chat_group.add_action_button(mw.clear_ai_chat_action, is_large=False)
        ai_chat_group.add_action_button(mw.openai_settings_action, is_large=False)
        ai_tab.add_group(ai_chat_group)

        help_tab = mw.ribbon.add_tab("Help")
        resources_group = RibbonGroup("Resources")
        resources_group.add_action_button(mw.quick_start_action)
        resources_group.add_action_button(mw.about_action, is_large=False)
        help_tab.add_group(resources_group)

        mw.ribbon.select_first_tab()
        logger.debug("UIManager: Modern ribbon created and populated.")
        self._populate_quick_access_toolbar()

    def _populate_quick_access_toolbar(self):
        """Clears and rebuilds the Quick Access Toolbar from settings."""
        self.quick_toolbar.clear()
        
        command_texts = self.mw.settings_manager.get("quick_access_commands", [])
        all_actions = self.mw.findChildren(QAction)
        action_map = {action.text().replace('&', ''): action for action in all_actions}

        for text in command_texts:
            if action := action_map.get(text):
                self.quick_toolbar.addAction(action)

        self.quick_toolbar.addSeparator()
        self.quick_toolbar.addAction(self.mw.host_action)

        customize_btn = QToolButton()
        customize_btn.setIcon(get_standard_icon(QStyle.SP_ToolBarVerticalExtensionButton, "Cust"))
        customize_btn.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self.mw); menu.addAction(self.mw.customize_quick_access_action); customize_btn.setMenu(menu)
        self.quick_toolbar.addWidget(customize_btn)

    def _create_docks(self):
        mw = self.mw
        mw.setDockOptions(QMainWindow.AnimatedDocks | QMainWindow.AllowTabbedDocks | QMainWindow.AllowNestedDocks)
        mw.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)
        docks_to_create = {
            "project_explorer_dock": ("ProjectExplorerDock", "Project Explorer"),
            "elements_palette_dock": ("ElementsPaletteDock", "Elements"),
            "properties_dock": ("PropertiesDock", "Properties"),
            "log_dock": ("LogDock", "Log"),
            "problems_dock": ("ProblemsDock", "Validation Issues"),
            "py_sim_dock": ("PySimDock", "Python Simulation"),
            "ai_chatbot_dock": ("AIChatbotDock", "AI Chatbot"),
            "ide_dock": ("IDEDock", "Code IDE"),
            "resource_estimation_dock": ("ResourceEstimationDock", "Resource Estimation"),
            "live_preview_dock": ("LivePreviewDock", "Code Scratchpad"),
            "minimap_dock": ("MinimapDock", "Navigator"),
            "hardware_sim_dock": ("HardwareSimDock", "Hardware Simulator"),
            "serial_monitor_dock": ("SerialMonitorDock", "Serial Monitor"),
        }
        for attr_name, (object_name, title) in docks_to_create.items():
            setattr(mw, attr_name, QDockWidget(title, mw, objectName=object_name))
        mw.project_explorer_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        mw.elements_palette_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        mw.properties_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        mw.py_sim_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        mw.ai_chatbot_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        mw.ide_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        mw.minimap_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        mw.hardware_sim_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        bottom_only = Qt.BottomDockWidgetArea
        mw.log_dock.setAllowedAreas(bottom_only)
        mw.problems_dock.setAllowedAreas(bottom_only)
        mw.resource_estimation_dock.setAllowedAreas(bottom_only)
        mw.live_preview_dock.setAllowedAreas(bottom_only)
        mw.serial_monitor_dock.setAllowedAreas(bottom_only)
        self._populate_project_explorer_dock()
        self._populate_elements_palette_dock()
        self._populate_properties_dock()
        self._populate_live_preview_dock()
        self._populate_serial_monitor_dock()
        log_widget_container = QWidget()
        log_layout = QVBoxLayout(log_widget_container)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(0)
        log_toolbar = QToolBar("Log Tools")
        log_toolbar.setIconSize(QSize(16, 16))
        log_toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        mw.log_level_filter_combo = QComboBox()
        mw.log_level_filter_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        mw.log_level_filter_combo.setCurrentText("INFO")
        mw.log_level_filter_combo.setToolTip("Filter logs by severity level")
        log_toolbar.addWidget(QLabel(" Min Level: "))
        log_toolbar.addWidget(mw.log_level_filter_combo)
        log_toolbar.addSeparator()
        mw.log_filter_edit = QLineEdit()
        mw.log_filter_edit.setPlaceholderText("Filter by text or module name...")
        mw.log_filter_edit.setClearButtonEnabled(True)
        log_toolbar.addWidget(mw.log_filter_edit)
        log_toolbar.addSeparator()
        log_toolbar.addAction(mw.log_clear_action)
        log_toolbar.addAction(mw.log_copy_action)
        log_toolbar.addAction(mw.log_save_action)
        log_layout.addWidget(log_toolbar)
        mw.log_output = QTextEdit(); mw.log_output.setReadOnly(True); mw.log_output.setObjectName("LogOutputWidget"); 
        mw.log_output.setStyleSheet(f"QTextEdit#LogOutputWidget {{ border-top: 1px solid {COLOR_BORDER_LIGHT}; border-radius: 0px; }}")
        log_layout.addWidget(mw.log_output, 1)
        mw.log_dock.setWidget(log_widget_container)
        problems_widget = QWidget()
        problems_layout = QVBoxLayout(problems_widget)
        problems_layout.setContentsMargins(0,0,0,0)
        problems_layout.setSpacing(4)
        mw.problems_list_widget = QListWidget(); mw.problems_list_widget.setObjectName("ProblemsListWidget")
        mw.problems_list_widget.itemDoubleClicked.connect(mw.on_problem_item_double_clicked)
        mw.problems_list_widget.currentItemChanged.connect(lambda current, prev: mw.problems_ask_ai_btn.setEnabled(current is not None))
        problems_layout.addWidget(mw.problems_list_widget)
        mw.problems_ask_ai_btn = QPushButton("Ask AI for help on this issue...")
        mw.problems_ask_ai_btn.setIcon(get_standard_icon(QStyle.SP_MessageBoxQuestion, "AIHelp"))
        mw.problems_ask_ai_btn.setEnabled(False)
        problems_layout.addWidget(mw.problems_ask_ai_btn)
        mw.problems_dock.setWidget(problems_widget)
        mw.minimap_view = MinimapView()
        mw.minimap_dock.setWidget(mw.minimap_view)
        if not hasattr(mw, 'docks_menu'):
            mw.view_menu = QMenu("&View", mw)
            mw.docks_menu = mw.view_menu.addMenu("Docks & Panels")
        mw.docks_menu.clear()
        dock_list = [getattr(mw, attr_name) for attr_name in docks_to_create.keys()]
        mw.docks_menu.addActions([d.toggleViewAction() for d in dock_list if d])
        mw.resource_estimation_dock.visibilityChanged.connect(mw.show_resource_estimation_action.setChecked)
        mw.show_resource_estimation_action.triggered.connect(mw.resource_estimation_dock.setVisible)
        mw.live_preview_dock.visibilityChanged.connect(mw.show_live_preview_action.setChecked)
        mw.show_live_preview_action.triggered.connect(mw.live_preview_dock.setVisible)

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
        mw.project_tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        mw.project_tree_view.doubleClicked.connect(mw.action_handler.on_project_file_double_clicked)
        mw.project_explorer_dock.setWidget(mw.project_tree_view)
        logger.debug("UIManager: Project explorer dock populated.")

    def _populate_elements_palette_dock(self):
        mw = self.mw
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.palette_search_bar = QLineEdit()
        self.palette_search_bar.setPlaceholderText("Filter elements...")
        self.palette_search_bar.setClearButtonEnabled(True)
        layout.addWidget(self.palette_search_bar)
        self.drag_elements_group = QGroupBox("Drag Elements")
        drag_layout = QVBoxLayout()
        drag_layout.setSpacing(4)
        drag_items = {
            "State": ("State", "SP_ToolBarHorizontalExtensionButton"),
            "Initial State": ("Initial State", "SP_ArrowRight"),
            "Final State": ("Final State", "SP_DialogOkButton"),
            "Comment": ("Comment", "SP_MessageBoxInformation")
        }
        for text, (data, icon_name_str) in drag_items.items():
            icon_enum = getattr(QStyle, icon_name_str, QStyle.SP_CustomBase)
            btn = DraggableToolButton(text, "application/x-bsm-tool", data)
            btn.setIcon(get_standard_icon(icon_enum, text[:2]))
            btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            drag_layout.addWidget(btn)
        self.drag_elements_group.setLayout(drag_layout)
        layout.addWidget(self.drag_elements_group)
        self.templates_group = QGroupBox("FSM Templates")
        template_layout = QVBoxLayout()
        mw.template_buttons_container = QWidget()
        mw.template_buttons_layout = QVBoxLayout(mw.template_buttons_container)
        mw.template_buttons_layout.setContentsMargins(4,0,4,0); mw.template_buttons_layout.setSpacing(4)
        self._load_and_display_templates()
        template_layout.addWidget(mw.template_buttons_container)
        manage_templates_btn = QPushButton("Manage Assets...")
        manage_templates_btn.clicked.connect(self.mw.action_handler.on_manage_snippets)
        template_layout.addWidget(manage_templates_btn)
        self.templates_group.setLayout(template_layout)
        layout.addWidget(self.templates_group)
        layout.addStretch()
        mw.elements_palette_dock.setWidget(widget)
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
            icon_to_use = QIcon()
            actual_path = _get_bundled_file_path(os.path.basename(icon_resource_path), "icons")
            if actual_path:
                icon_to_use = QIcon(actual_path)
            else:
                logger.warning(f"Built-in template icon resource not found: {icon_resource_path}")
                icon_to_use = get_standard_icon(QStyle.SP_FileLinkIcon, "Tpl")
            btn = DraggableToolButton(data['name'], MIME_TYPE_BSM_TEMPLATE, json.dumps(data)); btn.setIcon(icon_to_use)
            btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            btn.setToolTip(data.get('description',''))
            layout.addWidget(btn)
        if hasattr(mw, 'custom_snippet_manager'):
            custom_templates = mw.custom_snippet_manager.get_custom_templates()
            for name, data in custom_templates.items():
                btn = DraggableToolButton(name, MIME_TYPE_BSM_TEMPLATE, json.dumps(data))
                btn.setIcon(get_standard_icon(QStyle.SP_FileLinkIcon, "CustomTpl"))
                btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
                btn.setToolTip(data.get('description', f"Custom template: {name}"))
                layout.addWidget(btn)

    def _populate_properties_dock(self):
        mw = self.mw
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8,8,8,8)
        layout.setSpacing(6)
        mw.properties_multi_select_container = CollapsibleSection("Align & Distribute")
        mw.properties_multi_layout = QVBoxLayout()
        align_widget = QWidget()
        align_widget.setLayout(mw.properties_multi_layout)
        mw.properties_multi_select_container.add_widget(align_widget)
        mw.properties_multi_select_container.set_collapsed(True)
        layout.addWidget(mw.properties_multi_select_container)
        mw.properties_search_bar = QLineEdit()
        mw.properties_search_bar.setPlaceholderText("Filter properties...")
        mw.properties_search_bar.setClearButtonEnabled(True)
        mw.properties_search_bar.textChanged.connect(self._on_filter_properties_dock)
        layout.addWidget(mw.properties_search_bar)
        mw.properties_placeholder_label = QLabel("<i>Select an item...</i>")
        mw.properties_placeholder_label.setAlignment(Qt.AlignCenter)
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

    @pyqtSlot(str)
    def _on_filter_properties_dock(self, text: str):
        filter_text = text.lower().strip()
        mw = self.mw
        for i in range(mw.properties_editor_layout.count()):
            section_widget = mw.properties_editor_layout.itemAt(i).widget()
            if not isinstance(section_widget, CollapsibleSection):
                continue
            section_visible_due_to_match = False
            content_layout = section_widget.content_widget.layout()
            if not content_layout:
                continue
            for row_index in range(content_layout.count()):
                row_item = content_layout.itemAt(row_index)
                if not row_item or not row_item.widget():
                    continue
                row_widget = row_item.widget()
                row_layout = row_widget.layout()
                if row_layout and row_layout.count() > 0:
                    label_widget = row_layout.itemAt(0).widget()
                    if isinstance(label_widget, QLabel):
                        label_matches = filter_text in label_widget.text().lower()
                        section_title_matches = filter_text in section_widget.title_label.text().lower()
                        matches = not filter_text or label_matches or section_title_matches
                        row_widget.setVisible(matches)
                        if matches:
                            section_visible_due_to_match = True
                elif isinstance(row_widget, QCheckBox):
                    matches = not filter_text or filter_text in row_widget.text().lower()
                    row_widget.setVisible(matches)
                    if matches:
                        section_visible_due_to_match = True
            section_widget.setVisible(section_visible_due_to_match or not filter_text)

    @pyqtSlot()
    def on_advanced_edit_button_clicked(self):
        if self._current_edited_items and len(self._current_edited_items) == 1:
            self.mw.on_item_edit_requested(self._current_edited_items[0])

    def update_properties_dock_title_after_rename(self, new_name: str):
        from ..ui.graphics.graphics_items import GraphicsStateItem
        if self._current_edited_items and len(self._current_edited_items) == 1 and \
           isinstance(self._current_edited_items[0], GraphicsStateItem):
            self.mw.properties_dock.setWindowTitle(f"Properties: {new_name}")

    def update_properties_dock(self):
        editor = self.mw.current_editor()
        self._commit_property_changes()
        selected_items = editor.scene.selectedItems() if editor else []
        self._current_edited_items = selected_items
        self._clear_properties_layout()
        if not selected_items:
            self._display_no_selection_view()
        elif len(selected_items) == 1:
            self._display_single_item_view(selected_items[0])
        else:
            self._display_multi_item_view(selected_items)

    def _clear_properties_layout(self):
        while self.mw.properties_editor_layout.count():
            child_item = self.mw.properties_editor_layout.takeAt(0)
            if widget := child_item.widget():
                widget.deleteLater()
        while self.mw.properties_multi_layout.count():
            child_item = self.mw.properties_multi_layout.takeAt(0)
            if widget := child_item.widget():
                widget.deleteLater()
        self._property_editors.clear()

    def _display_no_selection_view(self):
        self.mw.properties_dock.setWindowTitle("Properties")
        self.mw.properties_placeholder_label.setText(f"<i>No item selected.</i><br><span style='font-size:{APP_FONT_SIZE_SMALL}; color:{COLOR_TEXT_SECONDARY};'>Click an item or use tools to add elements.</span>")
        self.mw.properties_placeholder_label.show()
        self.mw.properties_editor_container.hide()
        self.mw.properties_multi_select_container.hide()
        self.mw.properties_edit_dialog_button.setEnabled(False)

    def _display_single_item_view(self, item):
        self._build_common_editors(item)
        self.mw.properties_multi_select_container.hide()
        self.mw.properties_edit_dialog_button.setEnabled(True)

    def _display_multi_item_view(self, items):
        self.mw.properties_multi_select_container.show()
        self._populate_alignment_tools()
        
        # --- START MODIFICATION ---
        item_type = type(items[0])
        # Check if all items are of the same type
        if all(isinstance(i, item_type) for i in items):
            self.mw.properties_dock.setWindowTitle(f"Properties ({len(items)} {item_type.__name__.replace('Graphics','').replace('Item','')+'s'})")
            # Use a specific, limited schema for multi-editing
            multi_edit_schema = self._get_multi_edit_schema_for_item_type(item_type)
            self._build_common_editors(items, multi_edit_schema)
        else:
            self.mw.properties_dock.setWindowTitle(f"Properties ({len(items)} items)")
            self.mw.properties_placeholder_label.setText("<i>Multiple item types selected. Only alignment is available.</i>")
            self.mw.properties_placeholder_label.show()
            self.mw.properties_editor_container.hide()
            self.mw.properties_edit_dialog_button.setEnabled(False)
        # --- END MODIFICATION ---

    def _get_property_schema_for_item(self, item):
        from ..ui.graphics.graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem
        from ..ui.widgets.code_editor import CodeEditor
        item_type = type(item)
        if item_type is GraphicsStateItem:
            return {
                "General": [
                    {'key': 'name', 'label': 'Name:', 'widget': QLineEdit},
                    {'key': 'description', 'label': 'Description:', 'widget': QTextEdit, 'config': {'setFixedHeight': 60}},
                ],
                "Behavior": [
                    {'key': 'is_initial', 'label': 'Is Initial State', 'widget': QCheckBox},
                    {'key': 'is_final', 'label': 'Is Final State', 'widget': QCheckBox},
                    {'key': 'is_superstate', 'label': 'Is Superstate', 'widget': QCheckBox},
                ],
                "Actions": [
                    {'key': 'entry_action', 'label': 'Entry Action:', 'widget': CodeEditor, 'config': {'setFixedHeight': 70}},
                    {'key': 'during_action', 'label': 'During Action:', 'widget': CodeEditor, 'config': {'setFixedHeight': 70}},
                    {'key': 'exit_action', 'label': 'Exit Action:', 'widget': CodeEditor, 'config': {'setFixedHeight': 70}},
                ],
                "Appearance": [
                    {'key': 'color', 'label': 'Color:', 'widget': QPushButton, 'is_color': True},
                    {'key': 'font_size', 'label': 'Font Size:', 'widget': QSpinBox, 'config': {'setRange': (6, 72)}},
                    {'key': 'border_width', 'label': 'Border Width:', 'widget': QDoubleSpinBox, 'config': {'setRange': (0.5, 10.0), 'setSingleStep': 0.1, 'setDecimals': 1}},
                ]
            }
        elif item_type is GraphicsTransitionItem:
            return {
                "Logic": [
                    {'key': 'event', 'label': 'Event:', 'widget': QLineEdit},
                    {'key': 'condition', 'label': 'Condition:', 'widget': QLineEdit},
                    {'key': 'action', 'label': 'Action:', 'widget': CodeEditor, 'config': {'setFixedHeight': 70}},
                ],
                "Appearance": [
                    {'key': 'color', 'label': 'Color:', 'widget': QPushButton, 'is_color': True},
                    {'key': 'control_offset_x', 'label': 'Curve Bend (Perp):', 'widget': QSpinBox, 'config': {'setRange': (-1000, 1000)}},
                    {'key': 'control_offset_y', 'label': 'Curve Shift (Tang):', 'widget': QSpinBox, 'config': {'setRange': (-1000, 1000)}},
                ]
            }
        elif item_type is GraphicsCommentItem:
             return {
                "Content": [
                    {'key': 'text', 'label': 'Text:', 'widget': QTextEdit, 'config': {'setFixedHeight': 80}},
                ]
             }
        return {}


    # --- NEW METHOD ---
    def _get_multi_edit_schema_for_item_type(self, item_type):
        """Returns a reduced schema of properties suitable for batch editing."""
        from ..ui.graphics.graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem
        from ..managers.settings_manager import SettingsManager

        if item_type is GraphicsStateItem:
            return {
                "Appearance": [
                    {'key': 'color', 'label': 'Color:', 'widget': QPushButton, 'is_color': True},
                    {'key': 'font_size', 'label': 'Font Size:', 'widget': QSpinBox, 'config': {'setRange': (6, 72)}},
                    {'key': 'border_width', 'label': 'Border Width:', 'widget': QDoubleSpinBox, 'config': {'setRange': (0.5, 10.0), 'setSingleStep': 0.1, 'setDecimals': 1}},
                ]
            }
        elif item_type is GraphicsTransitionItem:
            return {
                "Appearance": [
                    {'key': 'color', 'label': 'Color:', 'widget': QPushButton, 'is_color': True},
                    {'key': 'line_width', 'label': 'Line Width:', 'widget': QDoubleSpinBox, 'config': {'setRange': (0.5, 10.0), 'setSingleStep': 0.1, 'setDecimals': 1}},
                    {'key': 'line_style_str', 'label': 'Line Style:', 'widget': QComboBox, 'items': list(SettingsManager.STRING_TO_QT_PEN_STYLE.keys())},
                ]
            }
        elif item_type is GraphicsCommentItem:
            return {
                "Appearance": [
                    {'key': 'font_size', 'label': 'Font Size:', 'widget': QSpinBox, 'config': {'setRange': (6, 72)}},
                ]
            }
        return {}


    def _build_common_editors(self, items, schema=None):
        items_list = items if isinstance(items, list) else [items]
        is_multi_edit = len(items_list) > 1
        first_item = items_list[0]
        
        # --- MODIFICATION: Use provided schema or get default ---
        if schema is None:
            schema = self._get_property_schema_for_item(first_item)
        # --- END MODIFICATION ---

        if not schema:
            self.mw.properties_placeholder_label.setText(f"<i>No editable properties for {type(first_item).__name__}.</i>")
            self.mw.properties_placeholder_label.show()
            self.mw.properties_editor_container.hide()
            return

        self.mw.properties_placeholder_label.hide()
        self.mw.properties_editor_container.show()
        
        for section_title, props in schema.items():
            section = CollapsibleSection(section_title, self.mw.properties_editor_container)
            self.mw.properties_editor_layout.addWidget(section)
            for prop_info in props:
                key = prop_info['key']
                first_value = first_item.get_data().get(key)
                all_same = True
                if is_multi_edit:
                    for other_item in items_list[1:]:
                        if other_item.get_data().get(key) != first_value:
                            all_same = False
                            break
                
                # --- MODIFICATION: Pass all_same to the creator ---
                editor_widget = self._create_editor_widget(prop_info, first_value, all_same)
                # --- END MODIFICATION ---

                if isinstance(editor_widget, QCheckBox):
                    section.add_widget(editor_widget)
                else:
                    section.add_row(prop_info['label'], editor_widget)
                self._property_editors[key] = editor_widget

    def _create_editor_widget(self, prop_info, value, all_same):
        WidgetClass = prop_info['widget']
        editor_widget = WidgetClass()
        
        # --- MODIFICATION: Handle ComboBox "Multiple Values" state ---
        if all_same:
            if isinstance(editor_widget, QLineEdit): editor_widget.setText(str(value or ''))
            elif isinstance(editor_widget, QTextEdit): editor_widget.setPlainText(str(value or ''))
            elif isinstance(editor_widget, QCheckBox): editor_widget.setChecked(bool(value))
            elif isinstance(editor_widget, QSpinBox): editor_widget.setValue(int(value or 0))
            elif isinstance(editor_widget, QDoubleSpinBox): editor_widget.setValue(float(value or 0.0))
            elif isinstance(editor_widget, QComboBox):
                if 'items' in prop_info:
                    editor_widget.addItems(prop_info['items'])
                editor_widget.setCurrentText(str(value).capitalize() if isinstance(value, str) else str(value))
        else:
            if isinstance(editor_widget, QLineEdit): editor_widget.setPlaceholderText("(Multiple Values)")
            elif isinstance(editor_widget, QCheckBox): editor_widget.setCheckState(Qt.PartiallyChecked)
            elif isinstance(editor_widget, QComboBox):
                if 'items' in prop_info:
                    editor_widget.addItems(prop_info['items'])
                editor_widget.insertItem(0, "(Multiple Values)")
                editor_widget.setCurrentIndex(0)
        # --- END MODIFICATION ---

        if 'config' in prop_info:
            for func_name, func_val in prop_info['config'].items():
                getattr(editor_widget, func_name)(func_val)
        
        if prop_info.get('is_color') and isinstance(editor_widget, QPushButton):
            color = QColor(value) if all_same and value else QColor(Qt.gray)
            self.mw._update_dock_color_button_style(editor_widget, color)
            editor_widget.setProperty("currentColorHex", color.name())
            editor_widget.clicked.connect(self._on_live_color_button_clicked)
            
        editor_widget.installEventFilter(self)
        return editor_widget

    def _populate_alignment_tools(self):
        self.mw.properties_multi_layout.addWidget(QPushButton("Left", clicked=self.mw.align_left_action.trigger))
        self.mw.properties_multi_layout.addWidget(QPushButton("Center", clicked=self.mw.align_center_h_action.trigger))
        self.mw.properties_multi_layout.addStretch()

    def eventFilter(self, obj, event):
        if obj in self._property_editors.values():
            if event.type() == QEvent.FocusIn:
                if not self._props_pre_edit_data:
                    for item in self._current_edited_items:
                        self._props_pre_edit_data[item] = item.get_data()
                return False
            if event.type() == QEvent.FocusOut:
                self._commit_property_changes()
                return False
        return super().eventFilter(obj, event)

    def _commit_property_changes(self):
        if not self._props_pre_edit_data or not self._current_edited_items:
            return
        old_props_list = []
        new_props_list = []
        for item in self._current_edited_items:
            old_props = self._props_pre_edit_data.get(item)
            if not old_props: continue
            current_props = item.get_data()
            new_props_for_item = old_props.copy()
            for key, editor_widget in self._property_editors.items():
                if not editor_widget.hasFocus() and not isinstance(editor_widget, QPushButton):
                     if isinstance(editor_widget, QLineEdit) and editor_widget.placeholderText() == "(Multiple Values)":
                         continue
                     if isinstance(editor_widget, QCheckBox) and editor_widget.checkState() == Qt.PartiallyChecked:
                         continue
                new_val = self._get_value_from_editor(editor_widget)
                if new_val is not None:
                    new_props_for_item[key] = new_val
            if new_props_for_item != old_props:
                old_props_list.append(old_props)
                new_props_list.append(new_props_for_item)
        if old_props_list and new_props_list:
            if editor := self.mw.current_editor():
                cmd = EditItemPropertiesCommand(self._current_edited_items, old_props_list, new_props_list, f"Edit Properties via Dock")
                editor.undo_stack.push(cmd)
        self._props_pre_edit_data.clear()

    def _get_value_from_editor(self, editor_widget):
        if isinstance(editor_widget, QLineEdit): return editor_widget.text().strip()
        elif isinstance(editor_widget, QTextEdit): return editor_widget.toPlainText().strip()
        elif isinstance(editor_widget, QCheckBox): return editor_widget.isChecked() if editor_widget.checkState() != Qt.PartiallyChecked else None
        elif isinstance(editor_widget, (QSpinBox, QDoubleSpinBox)): return editor_widget.value()
        elif isinstance(editor_widget, QPushButton) and editor_widget.property("currentColorHex"): return editor_widget.property("currentColorHex")
        return None

    def _on_live_color_button_clicked(self, *args):
        color_button = self.mw.sender()
        if not color_button: return
        current_color_hex = color_button.property("currentColorHex")
        initial_color = QColor(current_color_hex) if current_color_hex else QColor(Qt.white)
        dialog = QColorDialog(self.mw)
        dialog.setCurrentColor(initial_color)
        if dialog.exec_():
            new_color = dialog.selectedColor()
            if new_color.isValid() and new_color != initial_color:
                if not self._props_pre_edit_data:
                     for item in self._current_edited_items:
                        self._props_pre_edit_data[item] = item.get_data()
                self.mw._update_dock_color_button_style(color_button, new_color)
                color_button.setProperty("currentColorHex", new_color.name())
                for item in self._current_edited_items:
                    item.set_properties(color=new_color.name())
                self._commit_property_changes()

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
        mw.scratchpad_revert_action = QAction(get_standard_icon(QStyle.SP_BrowserReload, "Revert"), "Regenerate from Diagram", mw)
        mw.scratchpad_revert_action.setToolTip("Discard edits and reload code from the visual diagram.")
        mw.scratchpad_sync_action = QAction(get_standard_icon(QStyle.SP_ArrowUp, "Sync"), "Sync Code to Diagram", mw)
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

    def _create_status_bar(self):
        mw = self.mw
        mw.setStatusBar(ModernStatusBar(mw))
        status_bar = mw.statusBar()
        if isinstance(status_bar, ModernStatusBar):
             mw.main_op_status_label = status_bar.status_indicator.text_label
             pass
        else:
            status_bar = QStatusBar(mw)
            mw.setStatusBar(status_bar)
            mw.main_op_status_label = QLabel("Ready")
            status_bar.addWidget(mw.main_op_status_label, 1)
            mw.mode_status_segment = StatusSegment(QStyle.SP_ArrowRight, "Sel", "Select", "Interaction Mode", "InteractionModeStatusLabel")
            mw.zoom_status_segment = StatusSegment(QStyle.SP_FileDialogInfoView, "Zoom", "100%", "Zoom Level", "ZoomStatusLabel")
            mw.pysim_status_segment = StatusSegment(QStyle.SP_MediaStop, "PySim", "Idle", "Python Sim Status", "PySimStatusLabel")
            mw.matlab_status_segment = StatusSegment(QStyle.SP_MessageBoxWarning, "MATLAB", "Not Conn.", "MATLAB Status", "MatlabStatusLabel")
            mw.net_status_segment = StatusSegment(QStyle.SP_MessageBoxQuestion, "Net", "Checking...", "Internet Status", "InternetStatusLabel")
            status_bar.addPermanentWidget(mw.mode_status_segment)
            status_bar.addPermanentWidget(mw.zoom_status_segment)
            status_bar.addPermanentWidget(mw.pysim_status_segment)
            status_bar.addPermanentWidget(mw.matlab_status_segment)
            status_bar.addPermanentWidget(mw.net_status_segment)
            mw.resource_monitor_widget = QWidget()
            res_layout = QHBoxLayout(mw.resource_monitor_widget)
            res_layout.setContentsMargins(4, 0, 4, 0)
            res_layout.setSpacing(5)
            mw.cpu_status_label = QLabel("CPU: --%")
            res_layout.addWidget(mw.cpu_status_label)
            mw.ram_status_label = QLabel("RAM: --%")
            res_layout.addWidget(mw.ram_status_label)
            mw.gpu_status_label = QLabel("GPU: N/A")
            res_layout.addWidget(mw.gpu_status_label)
            status_bar.addPermanentWidget(mw.resource_monitor_widget)
            mw.resource_monitor_widget.setVisible(False)
            mw.progress_bar = QProgressBar()
            mw.progress_bar.setRange(0, 0)
            mw.progress_bar.hide()
            mw.progress_bar.setMaximumWidth(120)
            mw.progress_bar.setTextVisible(False)
            status_bar.addPermanentWidget(mw.progress_bar)

    def update_undo_redo_state(self):
        mw = self.mw
        editor = mw.current_editor()
        can_undo = editor and editor.undo_stack.canUndo()
        can_redo = editor and editor.undo_stack.canRedo()
        if hasattr(mw, 'undo_action'):
            mw.undo_action.setEnabled(can_undo)
            undo_text = editor.undo_stack.undoText() if can_undo else ""
            mw.undo_action.setText(f"&Undo{(' ' + undo_text) if undo_text else ''}")
            mw.undo_action.setToolTip(f"Undo: {undo_text}" if undo_text else "Undo")
        if hasattr(mw, 'redo_action'):
            mw.redo_action.setEnabled(can_redo)
            redo_text = editor.undo_stack.redoText() if can_redo else ""
            mw.redo_action.setText(f"&Redo{(' ' + redo_text) if redo_text else ''}")
            mw.redo_action.setToolTip(f"Redo: {redo_text}" if redo_text else "Redo")

    def update_save_actions_state(self):
        mw = self.mw
        if hasattr(mw, 'save_action'):
            is_dirty = mw.current_editor() and mw.current_editor().is_dirty()
            mw.save_action.setEnabled(is_dirty)
        if hasattr(mw, 'save_as_action'):
            is_project_open = mw.project_manager.is_project_open() if hasattr(mw, 'project_manager') else False
            mw.save_as_action.setEnabled(is_project_open and mw.current_editor() is not None)