# fsm_designer_project/ui_manager.py
import sip 
import os
import json
from PyQt5.QtWidgets import (
    QMainWindow, QDockWidget, QToolBox, QAction, QToolBar, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QStatusBar, QTextEdit, QPushButton, QListWidget, QMenu, QActionGroup, QStyle,
    QToolButton, QGroupBox, QComboBox, QProgressBar, QFormLayout, QGraphicsView,
    QMessageBox, QInputDialog, QLineEdit, QSizePolicy
)
from PyQt5.QtGui import QIcon, QKeySequence, QPalette, QPainter, QColor, QFont
from PyQt5.QtCore import Qt, QSize, QObject, QPointF, pyqtSlot

from .utils import get_standard_icon, _get_bundled_file_path
from .custom_widgets import DraggableToolButton
from .config import (
    APP_VERSION, APP_NAME, FILE_FILTER, MIME_TYPE_BSM_TEMPLATE,
    FSM_TEMPLATES_BUILTIN, COLOR_TEXT_SECONDARY, APP_FONT_SIZE_SMALL,
    COLOR_ACCENT_PRIMARY, COLOR_BORDER_LIGHT
)
from .target_profiles import TARGET_PROFILES
from .code_editor import CodeEditor
from .graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem
from . import config
from .graphics_scene import MinimapView
from .modern_welcome_screen import ModernWelcomeScreen
from .custom_widgets import CollapsibleSection
from .ribbon_toolbar import ModernRibbon, RibbonGroup, RibbonButton
import logging

logger = logging.getLogger(__name__)

# --- Self-Contained Status Bar Segment ---
# --- Self-Contained Status Bar Segment ---
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
        
        # --- FILE ---
        mw.new_action = QAction(get_standard_icon(QStyle.SP_FileIcon, "New"), "&New", mw, shortcut=QKeySequence.New, statusTip="Create a new diagram tab")
        mw.open_action = QAction(get_standard_icon(QStyle.SP_DialogOpenButton, "Opn"), "&Open...", mw, shortcut=QKeySequence.Open, statusTip="Open an existing file")
        mw.save_action = QAction(get_standard_icon(QStyle.SP_DialogSaveButton, "Sav"), "&Save", mw, shortcut=QKeySequence.Save, statusTip="Save the current diagram", enabled=False)
        mw.save_as_action = QAction(get_standard_icon(self._safe_get_style_enum("SP_DriveHDIcon", "SP_DialogSaveButton"), "SA"), "Save &As...", mw, shortcut=QKeySequence.SaveAs, statusTip="Save the current diagram with a new name")
        mw.import_from_text_action = QAction(get_standard_icon(QStyle.SP_FileLinkIcon, "Imp"), "Import from Text...", mw, statusTip="Create a diagram from PlantUML or Mermaid text")
        mw.exit_action = QAction(get_standard_icon(QStyle.SP_DialogCloseButton, "Exit"), "E&xit", mw, shortcut=QKeySequence.Quit, triggered=mw.close)
        
        # ... (rest of actions are the same)
        mw.export_png_action = QAction("&PNG Image...", mw)
        mw.export_svg_action = QAction("&SVG Image...", mw)
        mw.export_simulink_action = QAction("&Simulink Model...", mw)
        mw.generate_c_code_action = QAction("Basic &C/C++ Code...", mw)
        mw.export_python_fsm_action = QAction("&Python FSM Class...", mw)
        mw.export_plantuml_action = QAction("&PlantUML...", mw)
        mw.export_mermaid_action = QAction("&Mermaid...", mw)
        
        testbench_icon = get_standard_icon(self._safe_get_style_enum("SP_FileIcon", "SP_CustomBase"), "Test")
        mw.export_c_testbench_action = QAction(testbench_icon, "C &Testbench...", mw, statusTip="Generate a C test harness for the FSM")
        
        hdl_icon = get_standard_icon(self._safe_get_style_enum("SP_DriveNetIcon", "SP_ComputerIcon"), "HDL")
        mw.export_vhdl_action = QAction(hdl_icon, "&VHDL Code...", mw, statusTip="Export the FSM as synthesizable VHDL code")
        mw.export_verilog_action = QAction(hdl_icon, "&Verilog Code...", mw, statusTip="Export the FSM as synthesizable Verilog code")
        
        mw.undo_action = QAction(get_standard_icon(QStyle.SP_ArrowBack, "Un"), "&Undo", mw, shortcut=QKeySequence.Undo)
        mw.redo_action = QAction(get_standard_icon(QStyle.SP_ArrowForward, "Re"), "&Redo", mw, shortcut=QKeySequence.Redo)
        mw.delete_action = QAction(get_standard_icon(QStyle.SP_TrashIcon, "Del"), "&Delete", mw, shortcut=QKeySequence.Delete)
        mw.select_all_action = QAction("Select &All", mw, shortcut=QKeySequence.SelectAll)
        mw.find_item_action = QAction("&Find Item...", mw, shortcut=QKeySequence.Find)
        mw.save_selection_as_template_action = QAction("Save Selection as Template...", mw, enabled=False) 
        mw.manage_snippets_action = QAction("Manage Custom Snippets...", mw)
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

        # --- ALIGN/DISTRIBUTE ---
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

        # --- VIEW ---
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

        # --- SIMULATION ---
        mw.start_py_sim_action = QAction(get_standard_icon(QStyle.SP_MediaPlay, "Py▶"), "&Start Python Simulation", mw)
        mw.stop_py_sim_action = QAction(get_standard_icon(QStyle.SP_MediaStop, "Py■"), "S&top Python Simulation", mw, enabled=False)
        mw.reset_py_sim_action = QAction(get_standard_icon(QStyle.SP_MediaSkipBackward, "Py«"), "&Reset Python Simulation", mw, enabled=False)
        mw.matlab_settings_action = QAction(get_standard_icon(QStyle.SP_ComputerIcon, "Cfg"), "&MATLAB Settings...", mw)
        mw.run_simulation_action = QAction(get_standard_icon(QStyle.SP_MediaPlay, "Run"), "&Run Simulation (MATLAB)...", mw)
        mw.generate_matlab_code_action = QAction(get_standard_icon(QStyle.SP_DialogSaveButton, "CdeM"), "Generate &Code (C/C++ via MATLAB)...", mw)
        
        # --- GIT ---
        mw.git_commit_action = QAction("Commit...", mw)
        mw.git_push_action = QAction("Push", mw)
        mw.git_pull_action = QAction("Pull", mw)
        mw.git_show_changes_action = QAction("Show Changes...", mw)
        mw.git_actions = [mw.git_commit_action, mw.git_push_action, mw.git_pull_action, mw.git_show_changes_action]
        for action in mw.git_actions: action.setEnabled(False)

        # --- TOOLS (IDE & Other) ---
        mw.ide_new_file_action = QAction(get_standard_icon(QStyle.SP_FileIcon, "IDENew"), "New Script", mw)
        mw.ide_open_file_action = QAction(get_standard_icon(QStyle.SP_DialogOpenButton, "IDEOpn"), "Open Script...", mw)
        mw.ide_save_file_action = QAction(get_standard_icon(QStyle.SP_DialogSaveButton, "IDESav"), "Save Script", mw)
        mw.ide_save_as_file_action = QAction("Save Script As...", mw)
        mw.ide_run_script_action = QAction(get_standard_icon(QStyle.SP_MediaPlay, "IDERunPy"), "Run Python Script", mw)
        mw.ide_analyze_action = QAction("Analyze with AI", mw)
        mw.ide_analyze_selection_action = QAction("Analyze Selection with AI", mw)

        mw.show_resource_estimation_action = QAction("Resource Estimation", mw, checkable=True)
        mw.show_live_preview_action = QAction("Live Code Preview", mw, checkable=True)

        # --- AI ---
        mw.ask_ai_to_generate_fsm_action = QAction("Generate FSM from Description...", mw)
        mw.clear_ai_chat_action = QAction("Clear Chat History", mw)
        mw.openai_settings_action = QAction("AI Assistant Settings...", mw)
        
        # --- HELP ---
        mw.quick_start_action = QAction(get_standard_icon(QStyle.SP_MessageBoxQuestion, "QS"), "&Quick Start Guide", mw)
        mw.about_action = QAction(get_standard_icon(QStyle.SP_DialogHelpButton, "?"), "&About", mw)
        
        logger.debug("UIManager: Actions created.")
        
    def _create_menus(self):
        pass

    def _create_ribbon(self):
        mw = self.mw
        for tb in mw.findChildren(QToolBar):
            mw.removeToolBar(tb)
            tb.deleteLater()
        if mw.menuBar():
            mw.menuBar().clear()
            mw.setMenuBar(None)

        mw.ribbon = ModernRibbon(mw)
        ribbon_container_toolbar = QToolBar("Ribbon")
        ribbon_container_toolbar.setObjectName("RibbonToolbarContainer")
        ribbon_container_toolbar.setMovable(False)
        ribbon_container_toolbar.addWidget(mw.ribbon)
        mw.addToolBar(Qt.TopToolBarArea, ribbon_container_toolbar)
        
        mw.view_menu = QMenu("&View", mw)
        mw.toolbars_menu = mw.view_menu.addMenu("Toolbars")
        mw.docks_menu = mw.view_menu.addMenu("Docks & Panels")
        mw.perspectives_menu = mw.view_menu.addMenu("Perspectives")
        
        mw.toolbars_menu.clear()
        mw.toolbars_menu.addAction(ribbon_container_toolbar.toggleViewAction())

        file_menu = QMenu(mw)
        file_menu.addActions([mw.new_action, mw.open_action])
        mw.recent_files_menu = file_menu.addMenu("Open &Recent")
        mw.recent_files_menu.aboutToShow.connect(mw._populate_recent_files_menu)
        file_menu.addSeparator()
        example_menu = file_menu.addMenu("Open E&xample")
        mw.open_example_traffic_action = QAction("Traffic Light FSM", mw)
        mw.open_example_toggle_action = QAction("Simple Toggle FSM", mw)
        example_menu.addAction(mw.open_example_traffic_action)
        example_menu.addAction(mw.open_example_toggle_action)
        
        export_menu = file_menu.addMenu("E&xport")
        export_menu.addActions([mw.export_png_action, mw.export_svg_action, mw.export_python_fsm_action, mw.export_plantuml_action, mw.export_mermaid_action])
        
        # --- NEW: Add Import Action to File Menu ---
        file_menu.addSeparator()
        file_menu.addAction(mw.import_from_text_action)
        file_menu.addSeparator()

        file_menu.addActions([mw.save_action, mw.save_as_action])
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
        editing_group.add_action_button(mw.select_all_action)
        editing_group.add_action_button(mw.find_item_action)
        home_tab.add_group(editing_group)
        mode_group = RibbonGroup("Mode")
        for action in mw.mode_action_group.actions():
            mode_group.add_action_button(action)
        home_tab.add_group(mode_group)

        view_tab = mw.ribbon.add_tab("View")
        zoom_group = RibbonGroup("Zoom")
        zoom_group.add_action_button(mw.zoom_in_action)
        zoom_group.add_action_button(mw.zoom_out_action)
        zoom_group.add_action_button(mw.reset_zoom_action)
        zoom_group.add_separator()
        zoom_group.add_action_button(mw.fit_diagram_action)
        zoom_group.add_action_button(mw.zoom_to_selection_action)
        view_tab.add_group(zoom_group)

        layout_group = RibbonGroup("Layout")
        layout_group.add_action_button(mw.auto_layout_action)
        align_btn = QToolButton(); align_btn.setText("Align"); align_btn.setPopupMode(QToolButton.InstantPopup)
        align_btn.setDefaultAction(mw.align_left_action)
        align_menu = QMenu(mw); align_menu.addActions(mw.align_actions); align_btn.setMenu(align_menu)
        dist_btn = QToolButton(); dist_btn.setText("Distribute"); dist_btn.setPopupMode(QToolButton.InstantPopup)
        dist_btn.setDefaultAction(mw.distribute_h_action)
        dist_menu = QMenu(mw); dist_menu.addActions(mw.distribute_actions); dist_btn.setMenu(dist_menu)
        layout_group.add_widget(align_btn); layout_group.add_widget(dist_btn)
        view_tab.add_group(layout_group)
        
        window_group = RibbonGroup("Window")
        perspectives_btn = QToolButton(); perspectives_btn.setText("Perspectives"); perspectives_btn.setPopupMode(QToolButton.InstantPopup)
        perspectives_btn.setMenu(mw.perspectives_menu)
        window_group.add_widget(perspectives_btn)
        docks_btn = QToolButton(); docks_btn.setText("Docks"); docks_btn.setPopupMode(QToolButton.InstantPopup)
        docks_btn.setMenu(mw.docks_menu)
        window_group.add_widget(docks_btn)
        view_tab.add_group(window_group)
        
        sim_tab = mw.ribbon.add_tab("Simulation")
        pysim_group = RibbonGroup("Python Simulation")
        pysim_group.add_action_button(mw.start_py_sim_action)
        pysim_group.add_action_button(mw.stop_py_sim_action)
        pysim_group.add_action_button(mw.reset_py_sim_action)
        sim_tab.add_group(pysim_group)
        matlab_group = RibbonGroup("MATLAB/Simulink")
        matlab_group.add_action_button(mw.export_simulink_action)
        matlab_group.add_action_button(mw.run_simulation_action)
        matlab_group.add_action_button(mw.matlab_settings_action)
        sim_tab.add_group(matlab_group)

        mw.ribbon.select_first_tab()
        logger.debug("UIManager: Ribbon toolbar created and populated.")

    def _create_docks(self):
        mw = self.mw
        mw.setDockOptions(QMainWindow.AnimatedDocks | QMainWindow.AllowTabbedDocks | QMainWindow.AllowNestedDocks)
        
        docks_to_create = {
            "elements_palette_dock": ("ElementsPaletteDock", "Elements"),
            "properties_dock": ("PropertiesDock", "Properties"),
            "log_dock": ("LogDock", "Log"),
            "problems_dock": ("ProblemsDock", "Validation Issues"),
            "py_sim_dock": ("PySimDock", "Python Simulation"),
            "ai_chatbot_dock": ("AIChatbotDock", "AI Chatbot"),
            "ide_dock": ("IDEDock", "Code IDE"),
            "resource_estimation_dock": ("ResourceEstimationDock", "Resource Estimation"),
            "live_preview_dock": ("LivePreviewDock", "Live Code Preview"),
            "minimap_dock": ("MinimapDock", "Navigator"),
            "hardware_sim_dock": ("HardwareSimDock", "Hardware Simulator"),
            "serial_monitor_dock": ("SerialMonitorDock", "Serial Monitor"),
        }
        
        for attr_name, (object_name, title) in docks_to_create.items():
            setattr(mw, attr_name, QDockWidget(title, mw, objectName=object_name))
        
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
        mw.log_output.setStyleSheet(f"QTextEdit#LogOutputWidget {{ border-top: 1px solid {config.COLOR_BORDER_LIGHT}; border-radius: 0px; }}")
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

        mw.properties_placeholder_label = QLabel("<i>Select an item...</i>")
        mw.properties_placeholder_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(mw.properties_placeholder_label)

        mw.properties_editor_container = QWidget()
        mw.properties_editor_layout = QVBoxLayout(mw.properties_editor_container)
        mw.properties_editor_layout.setContentsMargins(0,0,0,0)
        mw.properties_editor_layout.setSpacing(5)
        mw.properties_editor_container.setHidden(True)
        layout.addWidget(mw.properties_editor_container)
        
        mw.properties_multi_select_container = QWidget()
        mw.properties_multi_layout = QVBoxLayout(mw.properties_multi_select_container)
        mw.properties_multi_layout.setContentsMargins(0,0,0,0)
        mw.properties_multi_select_container.setHidden(True)
        layout.addWidget(mw.properties_multi_select_container)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        mw.properties_revert_button = QPushButton("Revert")
        mw.properties_apply_button = QPushButton("Apply")
        btn_layout.addWidget(mw.properties_revert_button)
        btn_layout.addStretch()
        btn_layout.addWidget(mw.properties_apply_button)
        layout.addLayout(btn_layout)

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

        toolbar = QToolBar("Live Preview Toolbar")
        toolbar.setIconSize(QSize(16, 16))
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        toolbar.addWidget(QLabel(" Language: "))
        mw.live_preview_combo = QComboBox()
        mw.live_preview_combo.addItems(["Python FSM", "C Code", "PlantUML", "Mermaid"])
        toolbar.addWidget(mw.live_preview_combo)
        
        layout.addWidget(toolbar)
        
        mw.live_preview_editor = CodeEditor()
        mw.live_preview_editor.setReadOnly(True)
        mw.live_preview_editor.setObjectName("LivePreviewEditor") 
        mw.live_preview_editor.setPlaceholderText("Edit the diagram to see a live code preview...")
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
            mw.save_action.setEnabled(mw.current_editor() and mw.current_editor().is_dirty())