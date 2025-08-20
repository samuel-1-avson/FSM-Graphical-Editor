# fsm_designer_project/ui/ui_builder.py

import logging
from PyQt6.QtWidgets import (
    QMainWindow, QDockWidget, QToolBar, QVBoxLayout, QWidget, QLabel,
    QStatusBar, QTextEdit, QPushButton, QListWidget, QMenu, QStyle, QLineEdit,
    QToolButton, QGroupBox, QComboBox, QProgressBar, QFormLayout, QGraphicsView,
    QTreeView, QFrame, QScrollArea, QHBoxLayout
)
from PyQt6.QtGui import QIcon, QKeySequence, QPalette, QPainter, QColor, QFont, QActionGroup, QAction, QFileSystemModel
from PyQt6.QtCore import Qt, QSize, QDir

from ..utils import get_standard_icon
from ..utils.theme_config import theme_config
from ..assets.target_profiles import TARGET_PROFILES
# --- MODIFIED: Corrected import names and added aliases ---
from .widgets.ribbon_toolbar import ModernRibbon as ProfessionalRibbon, ModernRibbonGroup as ProfessionalGroup
from .widgets.global_search import GlobalSearchHandler
from .widgets.modern_status_bar import ModernStatusBar
# --- FIX: Corrected import path for MinimapView ---
from .widgets.minimap_view import MinimapView
from ..managers.data_dictionary_manager import DataDictionaryManager
from ..managers.c_simulation_manager import CSimulationManager
from .simulation.data_dictionary_widget import DataDictionaryWidget

logger = logging.getLogger(__name__)

class UIBuilder:
    """
    Responsible for constructing the main UI components of the MainWindow.
    This class populates the main window with actions, menus, toolbars, docks,
    and the status bar, but does not manage their state.
    """
    def __init__(self, main_window: QMainWindow):
        self.mw = main_window

    def build_ui(self):
        """Constructs all UI elements for the main window."""
        self.mw.setWindowIcon(get_standard_icon(QStyle.StandardPixmap.SP_DesktopIcon, "BSM"))
        self._create_actions()
        self._create_ribbon()
        self._create_docks()
        self._create_status_bar()
        # --- NEW: Add context menu for toggling docks ---
        self.mw.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.mw.customContextMenuRequested.connect(self._show_toolbar_dock_context_menu)

    def _create_actions(self):
        mw = self.mw
         # --- MODIFIED: The "New" action is now explicitly for Projects ---
        mw.new_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_FileIcon, "New"), "&New Project...", mw)
        mw.new_action.setShortcut(QKeySequence("Ctrl+Shift+N")) # A less common shortcut for a less frequent action
        mw.new_action.setStatusTip("Create a new project folder and structure")


        

        # --- ADD A NEW, DEDICATED "NEW FILE" ACTION ---
        mw.new_file_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_FileLinkIcon, "NewFile"), "New &File...", mw)
        mw.new_file_action.setShortcut("Ctrl+N") # Re-assign the common shortcut
        mw.new_action.setShortcut("") # Remove the shortcut from "New Project"
        mw.new_file_action.setStatusTip("Create a new diagram file in the current project or as a standalone file")

        mw.open_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_DialogOpenButton, "Opn"), "&Open Project/File...", mw)
        mw.open_action.setShortcut(QKeySequence.StandardKey.Open)
        mw.open_action.setStatusTip("Open an existing project or file")

        mw.save_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_DialogSaveButton, "Sav"), "&Save File", mw)
        mw.save_action.setShortcut(QKeySequence.StandardKey.Save)
        mw.save_action.setStatusTip("Save the current active file")
        mw.save_action.setEnabled(False)

        mw.save_as_action = QAction(get_standard_icon(self.mw.ui_manager._safe_get_style_enum("SP_DriveHDIcon", "SP_DialogSaveButton"), "SA"), "Save File &As...", mw)
        mw.save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        mw.save_as_action.setStatusTip("Save the current file with a new name")
        mw.save_as_action.setEnabled(False)

        mw.close_project_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_DialogCancelButton, "CloseProj"), "Close Project", mw)
        mw.close_project_action.setStatusTip("Close the current project")
        mw.close_project_action.setEnabled(False)

        mw.import_from_text_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_FileLinkIcon, "Imp"), "Import from Text...", mw)
        mw.import_from_text_action.setStatusTip("Create a diagram from PlantUML or Mermaid text")

        mw.exit_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_DialogCloseButton, "Exit"), "E&xit", mw)
        mw.exit_action.setShortcut(QKeySequence(QKeySequence.StandardKey.Quit))
        mw.exit_action.triggered.connect(mw.close)

        mw.export_png_action = QAction(get_standard_icon(self.mw.ui_manager._safe_get_style_enum("SP_MediaSave", "Img"), "Export PNG"), "&PNG Image...", mw)
        mw.export_svg_action = QAction(get_standard_icon(self.mw.ui_manager._safe_get_style_enum("SP_MediaSave", "Img"), "Export SVG"), "&SVG Image...", mw)
        mw.export_simulink_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_ComputerIcon, "Simulink"), "&Simulink Model...", mw)
        mw.generate_c_code_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_DialogSaveButton, "C"), "Basic &C/C++ Code...", mw)
        mw.export_python_fsm_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_DialogSaveButton, "Py"), "&Python FSM Class...", mw)
        mw.export_plantuml_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_FileLinkIcon, "Doc"), "&PlantUML...", mw)
        mw.export_mermaid_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_FileLinkIcon, "Doc"), "&Mermaid...", mw)
        testbench_icon = get_standard_icon(self.mw.ui_manager._safe_get_style_enum("SP_FileIcon", "Test"), "Test")
        mw.export_c_testbench_action = QAction(testbench_icon, "C &Testbench...", mw, statusTip="Generate a C test harness for the FSM")
        hdl_icon = get_standard_icon(self.mw.ui_manager._safe_get_style_enum("SP_DriveNetIcon", "SP_ComputerIcon"), "HDL")
        mw.export_vhdl_action = QAction(hdl_icon, "&VHDL Code...", mw, statusTip="Export the FSM as synthesizable VHDL code")
        mw.export_verilog_action = QAction(hdl_icon, "&Verilog Code...", mw, statusTip="Export the FSM as synthesizable Verilog code")
        mw.generate_matlab_code_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_DialogSaveButton, "C++"), "Generate Code from Simulink...", mw)
        mw.undo_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_ArrowBack, "Un"), "&Undo", mw)
        mw.undo_action.setShortcut(QKeySequence(QKeySequence.StandardKey.Undo))
        mw.redo_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_ArrowForward, "Re"), "&Redo", mw)
        mw.redo_action.setShortcut(QKeySequence(QKeySequence.StandardKey.Redo))
        mw.delete_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_TrashIcon, "Del"), "&Delete", mw)
        mw.delete_action.setShortcut(QKeySequence(QKeySequence.StandardKey.Delete))
        mw.select_all_action = QAction("Select &All", mw)
        mw.select_all_action.setShortcut(QKeySequence(QKeySequence.StandardKey.SelectAll))
        mw.find_item_action = QAction("&Find Item...", mw)
        mw.find_item_action.setShortcut(QKeySequence(QKeySequence.StandardKey.Find))
        mw.manage_snippets_action = QAction("Manage Custom Snippets...", mw)
        mw.save_selection_as_template_action = QAction("Save Selection as Template...", mw, enabled=False)
        mw.manage_fsm_templates_action = QAction("Manage FSM Templates...", mw)
        mw.preferences_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_FileDialogDetailedView, "Prefs"), "&Preferences...", mw)
        mw.log_clear_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_DialogResetButton, "Clr"), "Clear Log", mw)
        mw.log_save_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_DialogSaveButton, "SaveLog"), "Save Log As...", mw)
        mw.log_copy_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_FileLinkIcon, "CpyLog"), "Copy All to Clipboard", mw)
        mw.mode_action_group = QActionGroup(mw); mw.mode_action_group.setExclusive(True)
        def create_mode_action(name, text, icon_name, shortcut_key):
            icon_enum = getattr(QStyle.StandardPixmap, icon_name)
            action = QAction(get_standard_icon(icon_enum, shortcut_key), text, mw)
            action.setCheckable(True)
            action.setShortcut(QKeySequence(shortcut_key))
            action.setToolTip(f"Activate {text} mode ({shortcut_key})")
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
        mw.zoom_in_action = QAction("Zoom In", mw, shortcut=QKeySequence(QKeySequence.StandardKey.ZoomIn))
        mw.zoom_out_action = QAction("Zoom Out", mw, shortcut=QKeySequence(QKeySequence.StandardKey.ZoomOut))
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
        # --- MODIFIED ACTIONS ---
        mw.start_py_sim_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_MediaPlay, "Py▶"), "Initialize", mw)
        mw.start_py_sim_action.setStatusTip("Initialize the Python simulator engine with the current diagram")
        mw.stop_py_sim_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_MediaStop, "Py■"), "Stop Simulation", mw, enabled=False)
        mw.stop_py_sim_action.setStatusTip("Stop the current Python simulation")
        mw.reset_py_sim_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_MediaSkipBackward, "Py«"), "Reset Simulation", mw, enabled=False)
        mw.reset_py_sim_action.setStatusTip("Reset the Python simulation to its initial state")
        mw.run_simulation_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_MediaPlay, "Run"), "Run in MATLAB", mw)
        mw.run_simulation_action.setStatusTip("Run the exported Simulink model in MATLAB")
        # --- END MODIFIED ACTIONS ---
        mw.git_commit_action = QAction("Commit...", mw)
        mw.git_push_action = QAction("Push", mw)
        mw.git_pull_action = QAction("Pull", mw)
        mw.git_show_changes_action = QAction("Show Changes...", mw)
        mw.git_actions = [mw.git_commit_action, mw.git_push_action, mw.git_pull_action, mw.git_show_changes_action]
        for action in mw.git_actions: action.setEnabled(False)
        mw.ide_new_file_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_FileIcon, "IDENew"), "New Script", mw)
        mw.ide_open_file_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_DialogOpenButton, "IDEOpn"), "Open Script...", mw)
        mw.ide_save_file_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_DialogSaveButton, "IDESav"), "Save Script", mw)
        mw.ide_save_as_file_action = QAction("Save Script As...", mw)
        mw.ide_run_script_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_MediaPlay, "IDERunPy"), "Run Python Script", mw)
        mw.ide_analyze_action = QAction("Analyze with AI", mw)
        mw.ide_analyze_selection_action = QAction("Analyze Selection with AI", mw)
        mw.show_resource_estimation_action = QAction("Resource Estimation", mw, checkable=True)
        mw.show_live_preview_action = QAction("Live Code Preview", mw, checkable=True)
        mw.ask_ai_to_generate_fsm_action = QAction("Generate FSM from Description...", mw)
        mw.analyze_diagram_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_DialogHelpButton, "AI-Analyze"), "Analyze Diagram", mw)
        mw.analyze_diagram_action.setToolTip("Ask the AI to review the entire diagram for issues and improvements")
        # --- NEW ACTION ---
        mw.generate_docs_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_FileIcon, "AI-Doc"), "Generate Documentation", mw)
        mw.generate_docs_action.setToolTip("Ask the AI to generate Markdown documentation for the current diagram")
        # --- END NEW ---
        mw.clear_ai_chat_action = QAction("Clear Chat History", mw)
        mw.openai_settings_action = QAction("AI Assistant Settings...", mw)
        mw.quick_start_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_MessageBoxQuestion, "QS"), "&Quick Start Guide", mw)
        mw.about_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_DialogHelpButton, "?"), "&About", mw)
        mw.customize_quick_access_action = QAction("Customize Quick Access Toolbar...", mw)
        mw.host_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_ComputerIcon, "Host"), "Host", mw)
        logger.debug("UIBuilder: Actions created.")

    def _create_ribbon(self):
        mw = self.mw
        for tb in mw.findChildren(QToolBar):
            mw.removeToolBar(tb)
            tb.deleteLater()
        if mw.menuBar():
            mw.menuBar().clear()
            mw.setMenuBar(None)

        mw.quick_toolbar = QToolBar("Quick Access")
        mw.quick_toolbar.setMovable(False)
        mw.quick_toolbar.setFixedHeight(28)
        mw.addToolBar(Qt.ToolBarArea.TopToolBarArea, mw.quick_toolbar)

        mw.ribbon = ProfessionalRibbon(mw)
        ribbon_container_toolbar = QToolBar("Ribbon")
        ribbon_container_toolbar.setObjectName("RibbonToolbarContainer")
        ribbon_container_toolbar.setMovable(False)
        ribbon_container_toolbar.addWidget(mw.ribbon)
        mw.addToolBar(Qt.ToolBarArea.TopToolBarArea, ribbon_container_toolbar)

        self.mw.ui_manager.global_search_handler = GlobalSearchHandler(mw, mw.ribbon.search_bar)

        mw.view_menu = QMenu("&View", mw)
        mw.toolbars_menu = mw.view_menu.addMenu("Toolbars")
        mw.docks_menu = mw.view_menu.addMenu("Docks & Panels")
        mw.perspectives_menu = mw.view_menu.addMenu("Perspectives")
        mw.toolbars_menu.clear()
        mw.toolbars_menu.addAction(mw.quick_toolbar.toggleViewAction())
        mw.toolbars_menu.addAction(ribbon_container_toolbar.toggleViewAction())

        file_menu = QMenu(mw)
        
        
        
        
        file_menu.addActions([mw.new_action, mw.new_file_action, mw.open_action])
        mw.recent_files_menu = file_menu.addMenu("Open &Recent")
        mw.recent_files_menu.aboutToShow.connect(mw._populate_recent_files_menu)
        file_menu.addSeparator()
        example_menu = file_menu.addMenu("Open E&xample")
        mw.open_example_traffic_action = QAction("Traffic Light FSM", mw)
        mw.open_example_toggle_action = QAction("Simple Embedded Toggle", mw)
        mw.open_example_coffee_action = QAction("Hierarchical Coffee Machine", mw)
        example_menu.addActions([mw.open_example_traffic_action, mw.open_example_toggle_action, mw.open_example_coffee_action])
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
        file_group = ProfessionalGroup("File")
        # --- FIX: Changed add_action_button to add_button ---
        file_group.add_button(mw.new_action)
        file_group.add_button(mw.new_file_action)
        file_group.add_button(mw.open_action)
        home_tab.add_group(file_group)
        clipboard_group = ProfessionalGroup("Clipboard")
        clipboard_group.add_button(mw.undo_action)
        clipboard_group.add_button(mw.redo_action)
        home_tab.add_group(clipboard_group)
        editing_group = ProfessionalGroup("Editing")
        editing_group.add_button(mw.delete_action)
        editing_group.add_button(mw.select_all_action, style="medium")
        editing_group.add_button(mw.find_item_action, style="medium")
        home_tab.add_group(editing_group)
        mode_group = ProfessionalGroup("Mode")
        for action in mw.mode_action_group.actions():            
            mode_group.add_button(action, style="medium")
        home_tab.add_group(mode_group)        
        layout_group = ProfessionalGroup("Layout")
        layout_group.add_button(mw.auto_layout_action)
        align_btn = QToolButton(); align_btn.setText("Align"); align_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        align_menu = QMenu(mw); align_menu.addActions(mw.align_actions); align_btn.setMenu(align_menu)
        dist_btn = QToolButton(); dist_btn.setText("Distribute"); dist_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        dist_menu = QMenu(mw); dist_menu.addActions(mw.distribute_actions); dist_btn.setMenu(dist_menu)
        layout_group.add_widget(align_btn)
        layout_group.add_widget(dist_btn)        
        home_tab.add_group(layout_group)

        view_tab = mw.ribbon.add_tab("View")
        zoom_group = ProfessionalGroup("Zoom")
        zoom_group.add_button(mw.zoom_in_action)
        zoom_group.add_button(mw.zoom_out_action)
        zoom_group.add_button(mw.reset_zoom_action)
        zoom_group.add_separator()
        zoom_group.add_button(mw.fit_diagram_action)
        zoom_group.add_button(mw.zoom_to_selection_action)
        view_tab.add_group(zoom_group)
        canvas_group = ProfessionalGroup("Canvas")
        canvas_group.add_button(mw.show_grid_action, style="medium")
        canvas_group.add_button(mw.snap_to_grid_action, style="medium")
        canvas_group.add_button(mw.snap_to_objects_action, style="medium")
        canvas_group.add_button(mw.show_snap_guidelines_action, style="medium")
        view_tab.add_group(canvas_group)
        window_group = ProfessionalGroup("Window")
        perspectives_btn = QToolButton(); perspectives_btn.setText("Perspectives"); perspectives_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        perspectives_btn.setMenu(mw.perspectives_menu)
        docks_btn = QToolButton(); docks_btn.setText("Docks"); docks_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        docks_btn.setMenu(mw.docks_menu)
        window_group.add_widget(perspectives_btn)
        window_group.add_widget(docks_btn)
        view_tab.add_group(window_group)

        sim_tab = mw.ribbon.add_tab("Simulation")
        pysim_group = ProfessionalGroup("Python Simulation")
        pysim_group.add_button(mw.start_py_sim_action)
        pysim_group.add_button(mw.stop_py_sim_action)
        pysim_group.add_button(mw.reset_py_sim_action)
        sim_tab.add_group(pysim_group)
        matlab_group = ProfessionalGroup("MATLAB/Simulink")
        matlab_group.add_button(mw.run_simulation_action)
        sim_tab.add_group(matlab_group)

        code_export_tab = mw.ribbon.add_tab("Code Export")
        code_gen_group = ProfessionalGroup("Generate Code")
        mw.export_arduino_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_DialogSaveButton, "ino"), "Arduino Sketch...", mw)
        code_gen_group.add_button(mw.export_python_fsm_action, style="medium")
        code_gen_group.add_button(mw.generate_c_code_action, style="medium")
        code_gen_group.add_button(mw.export_arduino_action, style="medium")
        code_gen_group.add_button(mw.export_c_testbench_action, style="medium")
        code_export_tab.add_group(code_gen_group)
        hdl_group = ProfessionalGroup("Generate HDL")
        hdl_group.add_button(mw.export_vhdl_action, style="medium")
        hdl_group.add_button(mw.export_verilog_action, style="medium")
        code_export_tab.add_group(hdl_group)
        model_export_group = ProfessionalGroup("Model Export")
        model_export_group.add_button(mw.export_simulink_action)
        model_export_group.add_button(mw.generate_matlab_code_action, style="medium")
        code_export_tab.add_group(model_export_group)
        doc_export_group = ProfessionalGroup("Export Document")
        doc_export_group.add_button(mw.export_plantuml_action, style="medium")
        doc_export_group.add_button(mw.export_mermaid_action, style="medium")
        doc_export_group.add_button(mw.export_png_action, style="medium")
        doc_export_group.add_button(mw.export_svg_action, style="medium")
        code_export_tab.add_group(doc_export_group)
        # --- END FIX ---

        ai_tab = mw.ribbon.add_tab("AI Assistant")
        # --- MODIFIED GROUP ---
        ai_gen_group = ProfessionalGroup("Generation & Analysis")
        ai_gen_group.add_button(mw.ask_ai_to_generate_fsm_action)
        ai_gen_group.add_button(mw.analyze_diagram_action, style="medium")
        ai_gen_group.add_button(mw.generate_docs_action, style="medium")
        ai_tab.add_group(ai_gen_group)
        # --- END MODIFIED GROUP ---
        ai_chat_group = ProfessionalGroup("Chat")
        ai_chat_group.add_button(mw.clear_ai_chat_action, style="medium")
        ai_chat_group.add_button(mw.openai_settings_action, style="medium")
        ai_tab.add_group(ai_chat_group)

        help_tab = mw.ribbon.add_tab("Help")
        resources_group = ProfessionalGroup("Resources")
        resources_group.add_button(mw.quick_start_action)
        resources_group.add_button(mw.about_action, style="medium")
        help_tab.add_group(resources_group)

        mw.ribbon.select_first_tab()
        logger.debug("UIBuilder: Modern ribbon created and populated.")
        self.mw.ui_manager._populate_quick_access_toolbar()

    def _create_docks(self):
        mw = self.mw
        mw.setDockOptions(QMainWindow.DockOption.AnimatedDocks | QMainWindow.DockOption.AllowTabbedDocks | QMainWindow.DockOption.AllowNestedDocks)
        mw.setCorner(Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.RightDockWidgetArea)
        # --- MODIFIED: Added icons to dock definitions ---
        docks_to_create = {
            "project_explorer_dock": ("ProjectExplorerDock", "Project Explorer", QStyle.StandardPixmap.SP_DirIcon),
            "data_dictionary_dock": ("DataDictionaryDock", "Data Dictionary", QStyle.StandardPixmap.SP_FileIcon),
            "elements_palette_dock": ("ElementsPaletteDock", "Elements", QStyle.StandardPixmap.SP_FileDialogNewFolder),
            "properties_dock": ("PropertiesDock", "Properties", QStyle.StandardPixmap.SP_FileDialogDetailedView),
            "log_dock": ("LogDock", "Log", QStyle.StandardPixmap.SP_MessageBoxInformation),
            "problems_dock": ("ProblemsDock", "Validation Issues", QStyle.StandardPixmap.SP_MessageBoxWarning),
            "py_sim_dock": ("PySimDock", "Python Simulation", QStyle.StandardPixmap.SP_MediaPlay),
            "c_sim_dock": ("CSimDock", "C Simulation", QStyle.StandardPixmap.SP_MediaPlay),
            "ai_chatbot_dock": ("AIChatbotDock", "AI Chatbot", QStyle.StandardPixmap.SP_MessageBoxQuestion),
            "ide_dock": ("IDEDock", "Code IDE", QStyle.StandardPixmap.SP_FileIcon),
            "resource_estimation_dock": ("ResourceEstimationDock", "Resource Estimation", QStyle.StandardPixmap.SP_ComputerIcon),
            "live_preview_dock": ("LivePreviewDock", "Code Scratchpad", QStyle.StandardPixmap.SP_FileLinkIcon),
            "minimap_dock": ("MinimapDock", "Navigator", QStyle.StandardPixmap.SP_FileDialogListView),
            "hardware_sim_dock": ("HardwareSimDock", "Hardware Simulator", QStyle.StandardPixmap.SP_DriveNetIcon),
            "serial_monitor_dock": ("SerialMonitorDock", "Serial Monitor", QStyle.StandardPixmap.SP_ComputerIcon),
        }
        for attr_name, (object_name, title, icon_enum) in docks_to_create.items():
            dock = QDockWidget(title, mw, objectName=object_name)
            dock.setWindowIcon(get_standard_icon(icon_enum))
            setattr(mw, attr_name, dock)
        # --- END MODIFICATION ---

        # --- MODIFIED: Explicitly set features to allow user interaction ---
        dock_list = [getattr(mw, attr_name) for attr_name in docks_to_create.keys()]
        for dock in dock_list:
            if dock:
                dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | 
                                 QDockWidget.DockWidgetFeature.DockWidgetFloatable | 
                                 QDockWidget.DockWidgetFeature.DockWidgetClosable)
        # --- END MODIFICATION ---

        left_right_area = Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        bottom_only = Qt.DockWidgetArea.BottomDockWidgetArea
        all_areas = left_right_area | bottom_only

        mw.project_explorer_dock.setAllowedAreas(left_right_area)
        mw.data_dictionary_dock.setAllowedAreas(left_right_area)
        mw.elements_palette_dock.setAllowedAreas(left_right_area)
        mw.properties_dock.setAllowedAreas(left_right_area)
        mw.py_sim_dock.setAllowedAreas(left_right_area)
        mw.c_sim_dock.setAllowedAreas(left_right_area)
        mw.ai_chatbot_dock.setAllowedAreas(all_areas)
        mw.ide_dock.setAllowedAreas(all_areas)
        mw.minimap_dock.setAllowedAreas(left_right_area)
        mw.hardware_sim_dock.setAllowedAreas(left_right_area)
        
        mw.log_dock.setAllowedAreas(bottom_only)
        mw.problems_dock.setAllowedAreas(bottom_only)
        mw.resource_estimation_dock.setAllowedAreas(bottom_only)
        mw.live_preview_dock.setAllowedAreas(bottom_only)
        mw.serial_monitor_dock.setAllowedAreas(bottom_only)
        mw.c_sim_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        mw.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, mw.py_sim_dock)
        mw.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, mw.c_sim_dock)
        mw.tabifyDockWidget(mw.py_sim_dock, mw.c_sim_dock)
        
        log_widget_container = QWidget()
        log_layout = QVBoxLayout(log_widget_container)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(0)
        log_toolbar = QToolBar("Log Tools")
        log_toolbar.setIconSize(QSize(16, 16))
        log_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
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
        mw.log_output.setStyleSheet(f"QTextEdit#LogOutputWidget {{ border-top: 1px solid {theme_config.COLOR_BORDER_LIGHT}; border-radius: 0px; }}")
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
        mw.problems_ask_ai_btn.setIcon(get_standard_icon(QStyle.StandardPixmap.SP_MessageBoxQuestion, "AIHelp"))
        mw.problems_ask_ai_btn.setEnabled(False)
        problems_layout.addWidget(mw.problems_ask_ai_btn)
        mw.problems_dock.setWidget(problems_widget)

        self._populate_properties_dock()
        mw.ui_manager._populate_project_explorer_dock()
        mw.ui_manager._populate_data_dictionary_dock()
        mw.ui_manager._populate_elements_palette_dock()
        mw.ui_manager._populate_live_preview_dock()
        mw.ui_manager._populate_serial_monitor_dock()

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

    def _populate_properties_dock(self):
        mw = self.mw
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(4, 4, 4, 4)
        container_layout.setSpacing(4)

        # Filter Bar
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        mw.properties_filter_edit = QLineEdit()
        mw.properties_filter_edit.setPlaceholderText("Filter properties...")
        mw.properties_filter_edit.setClearButtonEnabled(True)
        mw.properties_filter_edit.textChanged.connect(mw.ui_manager._on_filter_properties_dock)
        filter_layout.addWidget(mw.properties_filter_edit)
        container_layout.addLayout(filter_layout)

        # Scroll Area for properties
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        container_layout.addWidget(scroll_area, 1)

        scroll_area_widget = QWidget()
        scroll_area.setWidget(scroll_area_widget)
        
        main_properties_layout = QVBoxLayout(scroll_area_widget)
        main_properties_layout.setContentsMargins(2, 2, 2, 2)
        main_properties_layout.setSpacing(6)
        
        mw.main_properties_layout = main_properties_layout

        mw.properties_placeholder_label = QLabel()
        mw.properties_placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mw.properties_placeholder_label.setWordWrap(True)
        main_properties_layout.addWidget(mw.properties_placeholder_label)

        mw.properties_editor_container = QFrame()
        mw.properties_editor_container.setObjectName("PropertiesEditorContainer")
        mw.properties_editor_layout = QVBoxLayout(mw.properties_editor_container)
        mw.properties_editor_layout.setContentsMargins(0, 0, 0, 0)
        mw.properties_editor_layout.setSpacing(6)
        main_properties_layout.addWidget(mw.properties_editor_container)

        mw.properties_multi_select_container = QFrame()
        mw.properties_multi_layout = QHBoxLayout(mw.properties_multi_select_container)
        mw.properties_multi_layout.setContentsMargins(0, 0, 0, 0)
        main_properties_layout.addWidget(mw.properties_multi_select_container)
        main_properties_layout.addStretch()

        # Button Bar
        button_bar = QFrame()
        button_bar.setObjectName("PropertiesButtonBar")
        button_bar_layout = QHBoxLayout(button_bar)
        button_bar_layout.setContentsMargins(0, 4, 0, 0)
        
        mw.properties_apply_button = QPushButton("Apply")
        mw.properties_apply_button.setToolTip("Apply changes to selected item(s)")
        mw.properties_apply_button.setEnabled(False)
        mw.properties_apply_button.clicked.connect(mw.ui_manager._on_apply_dock_properties)

        mw.properties_revert_button = QPushButton("Revert")
        mw.properties_revert_button.setToolTip("Discard changes and reload properties")
        mw.properties_revert_button.setEnabled(False)
        mw.properties_revert_button.clicked.connect(mw.ui_manager._on_revert_dock_properties)

        mw.properties_edit_dialog_button = QPushButton("Advanced Edit...")
        mw.properties_edit_dialog_button.setToolTip("Open the detailed property editor dialog")
        
        button_bar_layout.addWidget(mw.properties_revert_button)
        button_bar_layout.addStretch()
        button_bar_layout.addWidget(mw.properties_apply_button)
        button_bar_layout.addWidget(mw.properties_edit_dialog_button)
        
        container_layout.addWidget(button_bar)
        mw.properties_dock.setWidget(container)

    def _create_status_bar(self):
        mw = self.mw
        mw.setStatusBar(ModernStatusBar(mw))
        status_bar = mw.statusBar()
        if isinstance(status_bar, ModernStatusBar):
            mw.main_op_status_label = status_bar.status_indicator.text_label
        else:
            mw.main_op_status_label = QLabel("Ready")
            status_bar.addWidget(mw.main_op_status_label, 1) # Fallback
            mw.progress_bar = QProgressBar()
            mw.progress_bar.setRange(0, 0)
            mw.progress_bar.hide()
            mw.progress_bar.setMaximumWidth(120)
            mw.progress_bar.setTextVisible(False)
            status_bar.addPermanentWidget(mw.progress_bar)
            
    def _show_toolbar_dock_context_menu(self, pos):
        """Show a context menu to toggle toolbars and docks."""
        # Check if the right-click was over a toolbar area
        is_over_toolbar = False
        for toolbar in self.mw.findChildren(QToolBar):
            if toolbar.isVisible() and toolbar.geometry().contains(toolbar.mapFromGlobal(pos)):
                is_over_toolbar = True
                break
        
        # Or if it's over an empty dock area
        is_over_dock_area = self.mw.dockWidgetArea(pos) != Qt.DockWidgetArea.NoDockWidgetArea

        if not (is_over_toolbar or is_over_dock_area):
            return

        context_menu = QMenu(self.mw)
        context_menu.setTitle("Panels & Toolbars")
        
        context_menu.addSection("Toolbars")
        context_menu.addAction(self.mw.quick_toolbar.toggleViewAction())
        # The ribbon is inside another toolbar, so we find its parent
        ribbon_toolbar = self.mw.ribbon.parentWidget()
        if isinstance(ribbon_toolbar, QToolBar):
            context_menu.addAction(ribbon_toolbar.toggleViewAction())
        
        context_menu.addSection("Docks")
        context_menu.addActions(self.mw.docks_menu.actions())

        context_menu.exec(pos)