### `fsm_designer_project/ui_manager.py`

This file is updated to create the new `WelcomeWidget`, add the multi-select container to the properties dock, and add the AI helper button to the problems dock.

```python
# fsm_designer_project/ui_manager.py

import os
import json
from PyQt5.QtWidgets import (
    QMainWindow, QDockWidget, QToolBox, QAction, QToolBar, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QStatusBar, QTextEdit, QPushButton, QListWidget, QMenu, QActionGroup, QStyle,
    QToolButton, QGroupBox, QComboBox, QProgressBar, QFormLayout, QGraphicsView,
    QMessageBox, QInputDialog, QLineEdit, QSizePolicy
)
from PyQt5.QtGui import QIcon, QKeySequence, QPalette, QPainter, QColor, QFont
from PyQt5.QtCore import Qt, QSize, QObject, QPointF

from .utils import get_standard_icon
from .custom_widgets import DraggableToolButton
from .config import (
    APP_VERSION, APP_NAME, FILE_FILTER, MIME_TYPE_BSM_TEMPLATE,
    FSM_TEMPLATES_BUILTIN, COLOR_TEXT_SECONDARY, APP_FONT_SIZE_SMALL,
    COLOR_ACCENT_PRIMARY, COLOR_BORDER_LIGHT
)
from .target_profiles import TARGET_PROFILES
from .code_editor import CodeEditor
from .graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem

import logging

logger = logging.getLogger(__name__)

# --- NEW: Welcome Page Widget ---
class WelcomeWidget(QWidget):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.mw = main_window
        self.setObjectName("WelcomePage")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignCenter)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)
        content_layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(content_widget, 0, Qt.AlignCenter)

        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title = QLabel(APP_NAME)
        title.setFont(title_font)
        title.setObjectName("WelcomeTitle")
        content_layout.addWidget(title, 0, Qt.AlignCenter)

        version = QLabel(f"Version {APP_VERSION}")
        version.setObjectName("WelcomeVersion")
        content_layout.addWidget(version, 0, Qt.AlignCenter)
        
        content_layout.addSpacing(30)
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.new_button = self._create_welcome_button(
            "New Diagram", get_standard_icon(QStyle.SP_FileIcon, "New"), self.mw.action_handler.on_new_file
        )
        self.open_button = self._create_welcome_button(
            "Open Diagram...", get_standard_icon(QStyle.SP_DialogOpenButton, "Opn"), self.mw.action_handler.on_open_file
        )
        self.guide_button = self._create_welcome_button(
            "Quick Start Guide", get_standard_icon(QStyle.SP_MessageBoxQuestion, "QS"), self.mw.action_handler.on_show_quick_start
        )
        button_layout.addWidget(self.new_button)
        button_layout.addWidget(self.open_button)
        button_layout.addWidget(self.guide_button)
        content_layout.addLayout(button_layout)
        
        content_layout.addSpacing(30)

        self.recent_files_group = QGroupBox("Recent Files")
        self.recent_files_layout = QVBoxLayout(self.recent_files_group)
        content_layout.addWidget(self.recent_files_group)
        
        self.update_styles()

    def _create_welcome_button(self, text, icon, slot):
        button = QPushButton(icon, f" {text}")
        button.setIconSize(QSize(22, 22))
        button.setMinimumHeight(40)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        button.clicked.connect(slot)
        button.setObjectName("WelcomeButton")
        return button

    def update_recent_files(self):
        while self.recent_files_layout.count():
            item = self.recent_files_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        recent_files = self.mw.settings_manager.get("recent_files", [])
        if not recent_files:
            no_files_label = QLabel("<i>No recent files to show.</i>")
            no_files_label.setAlignment(Qt.AlignCenter)
            self.recent_files_layout.addWidget(no_files_label)
        else:
            for path in recent_files[:5]: # Show up to 5
                btn = QPushButton(os.path.basename(path))
                btn.setToolTip(path)
                btn.clicked.connect(lambda ch, p=path: self.mw.action_handler.on_open_recent_file.__self__.mw._create_and_load_new_tab(p) if self.mw.find_editor_by_path(p) is None else None)
                btn.setObjectName("RecentFileButton")
                self.recent_files_layout.addWidget(btn)

    def update_styles(self):
        self.setStyleSheet(f"""
            #WelcomePage {{
                background-color: {config.COLOR_BACKGROUND_APP};
            }}
            #WelcomeTitle {{
                color: {config.COLOR_ACCENT_PRIMARY};
            }}
            #WelcomeVersion {{
                color: {config.COLOR_TEXT_SECONDARY};
                font-size: {APP_FONT_SIZE_SMALL};
            }}
            #WelcomeButton {{
                font-size: 11pt;
                padding: 8px;
            }}
            #RecentFileButton {{
                text-align: left;
                padding: 6px;
                background-color: transparent;
                border: none;
                color: {config.COLOR_ACCENT_PRIMARY};
            }}
            #RecentFileButton:hover {{
                text-decoration: underline;
            }}
        """)

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
        """Initializes the entire UI structure."""
        self.mw.setWindowIcon(get_standard_icon(QStyle.SP_DesktopIcon, "BSM"))
        self._create_actions()
        self._create_menus()
        self._create_toolbars()
        self._create_docks()
        self._create_status_bar()

    def populate_dynamic_docks(self):
        """Populates docks whose content is managed by other classes."""
        mw = self.mw
        if mw.py_sim_ui_manager and hasattr(mw, 'py_sim_dock'):
            py_sim_contents_widget = mw.py_sim_ui_manager.create_dock_widget_contents()
            mw.py_sim_dock.setWidget(py_sim_contents_widget)
        
        if mw.ai_chat_ui_manager and hasattr(mw, 'ai_chatbot_dock'):
            ai_chat_contents_widget = mw.ai_chat_ui_manager.create_dock_widget_contents()
            mw.ai_chatbot_dock.setWidget(ai_chat_contents_widget)
            
        self._populate_resource_estimation_dock()

    def _create_actions(self):
        mw = self.mw
        
        # --- FILE ---
        mw.new_action = QAction(get_standard_icon(QStyle.SP_FileIcon, "New"), "&New", mw, shortcut=QKeySequence.New, statusTip="Create a new diagram tab")
        mw.open_action = QAction(get_standard_icon(QStyle.SP_DialogOpenButton, "Opn"), "&Open...", mw, shortcut=QKeySequence.Open, statusTip="Open an existing file")
        mw.save_action = QAction(get_standard_icon(QStyle.SP_DialogSaveButton, "Sav"), "&Save", mw, shortcut=QKeySequence.Save, statusTip="Save the current diagram", enabled=False)
        mw.save_as_action = QAction(get_standard_icon(self._safe_get_style_enum("SP_DriveHDIcon", "SP_DialogSaveButton"), "SA"), "Save &As...", mw, shortcut=QKeySequence.SaveAs, statusTip="Save the current diagram with a new name")
        mw.exit_action = QAction(get_standard_icon(QStyle.SP_DialogCloseButton, "Exit"), "E&xit", mw, shortcut=QKeySequence.Quit, triggered=mw.close)

        # --- EXPORT ---
        mw.export_png_action = QAction("&PNG Image...", mw)
        mw.export_svg_action = QAction("&SVG Image...", mw)
        mw.export_simulink_action = QAction("&Simulink...", mw)
        mw.generate_c_code_action = QAction("Basic &C Code...", mw)
        mw.export_python_fsm_action = QAction("&Python FSM Class...", mw)
        mw.export_plantuml_action = QAction("&PlantUML...", mw)
        mw.export_mermaid_action = QAction("&Mermaid...", mw)

        # --- EDIT ---
        mw.undo_action = QAction(get_standard_icon(QStyle.SP_ArrowBack, "Un"), "&Undo", mw, shortcut=QKeySequence.Undo)
        mw.redo_action = QAction(get_standard_icon(QStyle.SP_ArrowForward, "Re"), "&Redo", mw, shortcut=QKeySequence.Redo)
        mw.delete_action = QAction(get_standard_icon(QStyle.SP_TrashIcon, "Del"), "&Delete", mw, shortcut=QKeySequence.Delete)
        mw.select_all_action = QAction("Select &All", mw, shortcut=QKeySequence.SelectAll)
        mw.find_item_action = QAction("&Find Item...", mw, shortcut=QKeySequence.Find)
        mw.save_selection_as_template_action = QAction("Save Selection as Template...", mw, enabled=False) # New action
        mw.manage_snippets_action = QAction("Manage Custom Snippets...", mw)
        mw.preferences_action = QAction(get_standard_icon(QStyle.SP_FileDialogDetailedView, "Prefs"), "&Preferences...", mw)
        
        # --- INTERACTION MODE ---
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
        # AI IMPROVEMENT: New action for analyzing selection
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
        mw = self.mw; mb = mw.menuBar()
        # --- FILE MENU ---
        file_menu = mb.addMenu("&File")
        file_menu.addActions([mw.new_action, mw.open_action])
        mw.recent_files_menu = file_menu.addMenu("Open &Recent")
        mw.recent_files_menu.aboutToShow.connect(mw._populate_recent_files_menu)
        file_menu.addSeparator()
        example_menu = file_menu.addMenu("Open E&xample")
        mw.open_example_traffic_action = example_menu.addAction("Traffic Light FSM")
        mw.open_example_toggle_action = example_menu.addAction("Simple Toggle FSM")
        export_menu = file_menu.addMenu("E&xport"); export_menu.addActions([mw.export_png_action, mw.export_svg_action]); export_menu.addSeparator()
        export_menu.addActions([mw.export_simulink_action, mw.generate_c_code_action, mw.export_python_fsm_action])
        export_menu.addSeparator(); export_menu.addActions([mw.export_plantuml_action, mw.export_mermaid_action])
        file_menu.addSeparator(); file_menu.addActions([mw.save_action, mw.save_as_action]); file_menu.addSeparator(); file_menu.addAction(mw.exit_action)
        # --- EDIT MENU ---
        edit_menu = mb.addMenu("&Edit")
        edit_menu.addActions([mw.undo_action, mw.redo_action]); edit_menu.addSeparator()
        edit_menu.addActions([mw.delete_action, mw.select_all_action]); edit_menu.addSeparator()
        edit_menu.addAction(mw.find_item_action); edit_menu.addSeparator()
        edit_menu.addAction(mw.save_selection_as_template_action); edit_menu.addSeparator()
        edit_menu.addMenu("Interaction Mode").addActions(mw.mode_action_group.actions())
        align_menu = edit_menu.addMenu("Align & Distribute"); align_menu.addMenu("Align").addActions(mw.align_actions); align_menu.addMenu("Distribute").addActions(mw.distribute_actions)
        edit_menu.addSeparator(); edit_menu.addAction(mw.manage_snippets_action); edit_menu.addSeparator(); edit_menu.addAction(mw.preferences_action)
        # --- VIEW MENU ---
        mw.view_menu = mb.addMenu("&View")
        zoom_menu = mw.view_menu.addMenu("Zoom"); zoom_menu.addActions([mw.zoom_in_action, mw.zoom_out_action, mw.reset_zoom_action]); zoom_menu.addSeparator(); zoom_menu.addActions([mw.zoom_to_selection_action, mw.fit_diagram_action])
        mw.view_menu.addSeparator(); mw.view_menu.addAction(mw.auto_layout_action)
        mw.view_menu.addSeparator();
        mw.view_menu.addAction(mw.show_grid_action)
        snap_menu = mw.view_menu.addMenu("Snapping"); snap_menu.addActions([mw.snap_to_grid_action, mw.snap_to_objects_action, mw.show_snap_guidelines_action])
        mw.view_menu.addSeparator(); mw.toolbars_menu = mw.view_menu.addMenu("Toolbars"); mw.docks_menu = mw.view_menu.addMenu("Docks & Panels")
        mw.view_menu.addSeparator()
        mw.perspectives_menu = mw.view_menu.addMenu("Perspectives")
        mw.perspectives_action_group = QActionGroup(mw)
        mw.save_perspective_action = QAction("Save Current As...", mw); mw.reset_perspectives_action = QAction("Reset to Defaults", mw)
        
        # --- GIT MENU ---
        git_menu = mb.addMenu("&Git")
        git_menu.addActions(mw.git_actions)
        
        # --- SIMULATION, TOOLS, AI, HELP MENUS ---
        sim_menu = mb.addMenu("&Simulation")
        sim_menu.addMenu("Python Simulation").addActions([mw.start_py_sim_action, mw.stop_py_sim_action, mw.reset_py_sim_action])
        sim_menu.addMenu("MATLAB/Simulink").addActions([mw.run_simulation_action, mw.generate_matlab_code_action, mw.matlab_settings_action])
        tools_menu = mb.addMenu("&Tools")
        ide_menu = tools_menu.addMenu("Standalone Code IDE")
        ide_menu.addActions([mw.ide_new_file_action, mw.ide_open_file_action, mw.ide_save_file_action, mw.ide_save_as_file_action])
        ide_menu.addSeparator()
        ide_menu.addAction(mw.ide_run_script_action)
        ide_menu.addSeparator()
        # AI IMPROVEMENT: Add new action to menu
        ide_menu.addActions([mw.ide_analyze_action, mw.ide_analyze_selection_action])

        tools_menu.addMenu("Development Tools").addActions([mw.show_resource_estimation_action, mw.show_live_preview_action])
        ai_menu = mb.addMenu("&AI Assistant")
        ai_menu.addActions([mw.ask_ai_to_generate_fsm_action, mw.clear_ai_chat_action]); ai_menu.addSeparator(); ai_menu.addAction(mw.openai_settings_action)
        help_menu = mb.addMenu("&Help"); help_menu.addActions([mw.quick_start_action, mw.about_action])
        logger.debug("UIManager: Menus created.")

    def _create_toolbars(self):
        mw = self.mw
        for tb in mw.findChildren(QToolBar): mw.removeToolBar(tb); tb.deleteLater() # Clear old toolbars
        tb = mw.addToolBar("Main"); tb.setObjectName("MainToolbar"); tb.setIconSize(QSize(20, 20)); tb.setToolButtonStyle(Qt.ToolButtonIconOnly)
        tb.addActions([mw.new_action, mw.open_action, mw.save_action]); tb.addSeparator()
        tb.addActions([mw.undo_action, mw.redo_action, mw.delete_action]); tb.addSeparator()
        tb.addActions(mw.mode_action_group.actions()); tb.addSeparator()
        tb.addAction(mw.auto_layout_action)
        align_btn = QToolButton(mw); align_btn.setIcon(get_standard_icon(QStyle.SP_FileDialogDetailedView, "Align")); align_btn.setToolTip("Align & Distribute"); align_btn.setPopupMode(QToolButton.InstantPopup)
        align_menu = QMenu(mw); align_sub = align_menu.addMenu("Align"); align_sub.addActions(mw.align_actions); dist_sub = align_menu.addMenu("Distribute"); dist_sub.addActions(mw.distribute_actions)
        align_btn.setMenu(align_menu); tb.addWidget(align_btn)
        
        # Add Git button to toolbar
        git_btn = QToolButton(mw)
        git_btn.setIcon(get_standard_icon(QStyle.SP_ToolBarHorizontalExtensionButton, "Git")) # A generic icon for now
        git_btn.setToolTip("Git Actions")
        git_btn.setPopupMode(QToolButton.InstantPopup)
        git_menu_for_button = QMenu(mw)
        git_menu_for_button.addActions(mw.git_actions)
        git_btn.setMenu(git_menu_for_button)
        tb.addWidget(git_btn)
        
        tb.addSeparator()
        
        tb.addActions([mw.zoom_in_action, mw.zoom_out_action, mw.reset_zoom_action, mw.fit_diagram_action]); tb.addSeparator()
        tb.addActions([mw.start_py_sim_action, mw.stop_py_sim_action, mw.reset_py_sim_action]); tb.addSeparator()
        export_btn = QToolButton(mw); export_btn.setIcon(get_standard_icon(QStyle.SP_DialogSaveButton, "Export")); export_btn.setToolTip("Export & Generate Code"); export_btn.setPopupMode(QToolButton.InstantPopup)
        export_menu = QMenu(mw); export_menu.addActions([mw.export_png_action, mw.export_svg_action]); export_menu.addSeparator(); export_menu.addActions([mw.export_simulink_action, mw.generate_c_code_action, mw.export_python_fsm_action, mw.generate_matlab_code_action]); export_menu.addSeparator(); export_menu.addActions([mw.export_plantuml_action, mw.export_mermaid_action])
        export_btn.setMenu(export_menu); tb.addWidget(export_btn)
        mw.toolbars_menu.clear(); mw.toolbars_menu.addAction(tb.toggleViewAction())
        logger.debug("UIManager: Toolbar created.")

    def _create_docks(self):
        mw = self.mw
        mw.setDockOptions(QMainWindow.AnimatedDocks | QMainWindow.AllowTabbedDocks | QMainWindow.AllowNestedDocks)
        
        # Consistent snake_case for attributes
        docks_to_create = {
            "elements_palette_dock": ("ElementsPaletteDock", "Elements"),
            "properties_dock": ("PropertiesDock", "Properties"),
            "log_dock": ("LogDock", "Log"),
            "problems_dock": ("ProblemsDock", "Validation Issues"),
            "py_sim_dock": ("PySimDock", "Python Simulation"),
            "ai_chatbot_dock": ("AIChatbotDock", "AI Chatbot"),
            "ide_dock": ("IDEDock", "Code IDE"),
            "resource_estimation_dock": ("ResourceEstimationDock", "Resource Estimation"),
            "live_preview_dock": ("LivePreviewDock", "Live Code Preview")
        }
        
        for attr_name, (object_name, title) in docks_to_create.items():
            setattr(mw, attr_name, QDockWidget(title, mw, objectName=object_name))
        
        self._populate_elements_palette_dock()
        self._populate_properties_dock()
        self._populate_live_preview_dock()
        
        mw.log_output = QTextEdit(); mw.log_output.setReadOnly(True); mw.log_output.setObjectName("LogOutputWidget"); mw.log_dock.setWidget(mw.log_output)
        
        # --- MODIFIED: Problems Dock with AI Button ---
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
        
        mw.addDockWidget(Qt.LeftDockWidgetArea, mw.elements_palette_dock)
        mw.addDockWidget(Qt.RightDockWidgetArea, mw.properties_dock)
        mw.addDockWidget(Qt.BottomDockWidgetArea, mw.log_dock)
        mw.addDockWidget(Qt.BottomDockWidgetArea, mw.problems_dock)
        mw.addDockWidget(Qt.RightDockWidgetArea, mw.py_sim_dock)
        mw.addDockWidget(Qt.RightDockWidgetArea, mw.ai_chatbot_dock)
        mw.addDockWidget(Qt.RightDockWidgetArea, mw.ide_dock)
        mw.addDockWidget(Qt.RightDockWidgetArea, mw.resource_estimation_dock)
        mw.addDockWidget(Qt.BottomDockWidgetArea, mw.live_preview_dock)

        
        mw.docks_menu.clear()
        dock_list = [getattr(mw, attr_name) for attr_name in docks_to_create.keys()]
        mw.docks_menu.addActions([d.toggleViewAction() for d in dock_list[:4]]); mw.docks_menu.addSeparator()
        mw.docks_menu.addActions([d.toggleViewAction() for d in dock_list[4:7]]); mw.docks_menu.addSeparator()
        mw.docks_menu.addActions([mw.resource_estimation_dock.toggleViewAction(), mw.live_preview_dock.toggleViewAction()])

        
        mw.log_dock.raise_(); mw.problems_dock.setVisible(False); mw.py_sim_dock.setVisible(False); mw.ai_chatbot_dock.setVisible(False); mw.ide_dock.setVisible(False); mw.resource_estimation_dock.setVisible(False)
        mw.live_preview_dock.setVisible(False)
        
        # Connect the manually created action from the Tools menu to the dock's visibility
        mw.resource_estimation_dock.visibilityChanged.connect(mw.show_resource_estimation_action.setChecked)
        mw.show_resource_estimation_action.triggered.connect(mw.resource_estimation_dock.setVisible)
        mw.live_preview_dock.visibilityChanged.connect(mw.show_live_preview_action.setChecked)
        mw.show_live_preview_action.triggered.connect(mw.live_preview_dock.setVisible)
        
    def _populate_elements_palette_dock(self):
        mw = self.mw; widget = QWidget(); layout = QVBoxLayout(widget)
        drag_group = QGroupBox("Drag Elements"); drag_layout = QVBoxLayout(); drag_layout.setSpacing(4)
        drag_items = {"State": "State", "Initial State": "Initial State", "Final State": "Final State", "Comment": "Comment"}
        for text, data in drag_items.items(): btn = DraggableToolButton(text, "application/x-bsm-tool", data); drag_layout.addWidget(btn)
        drag_group.setLayout(drag_layout); layout.addWidget(drag_group)
        
        template_group = QGroupBox("FSM Templates"); template_layout = QVBoxLayout()
        mw.template_buttons_container = QWidget(); mw.template_buttons_layout = QVBoxLayout(mw.template_buttons_container); mw.template_buttons_layout.setContentsMargins(0,0,0,0)
        self._load_and_display_templates(); template_layout.addWidget(mw.template_buttons_container)
        
        # --- NEW ---
        manage_templates_btn = QPushButton("Manage Snippets...")
        manage_templates_btn.clicked.connect(self.mw.action_handler.on_manage_snippets)
        template_layout.addWidget(manage_templates_btn)
        # --- END NEW ---

        template_group.setLayout(template_layout); layout.addWidget(template_group)
        layout.addStretch(); mw.elements_palette_dock.setWidget(widget)
        
    def _load_and_display_templates(self):
        mw = self.mw; layout = mw.template_buttons_layout
        # Clear existing buttons
        while layout.count(): 
            item = layout.takeAt(0)
            if item and item.widget(): 
                item.widget().deleteLater()
        
        # Load built-in templates
        for key, data in FSM_TEMPLATES_BUILTIN.items():
            btn = DraggableToolButton(data['name'], MIME_TYPE_BSM_TEMPLATE, json.dumps(data))
            btn.setIcon(QIcon(data.get('icon_resource', ':/icons/default.png')))
            btn.setToolTip(data.get('description',''))
            layout.addWidget(btn)

        # Load custom templates
        if hasattr(mw, 'custom_snippet_manager'):
            custom_templates = mw.custom_snippet_manager.get_custom_templates()
            for name, data in custom_templates.items():
                btn = DraggableToolButton(name, MIME_TYPE_BSM_TEMPLATE, json.dumps(data))
                btn.setIcon(get_standard_icon(QStyle.SP_FileLinkIcon, "CustomTpl"))
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
        mw.properties_editor_layout = QFormLayout(mw.properties_editor_container)
        mw.properties_editor_layout.setContentsMargins(0,0,0,0)
        mw.properties_editor_container.setHidden(True)
        layout.addWidget(mw.properties_editor_container)
        
        # --- NEW: Multi-select container ---
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
        mw.flash_usage_bar = QProgressBar(); mw.sram_usage_bar = QProgressBar(); usage_layout.addRow("Flash/Code:", mw.flash_usage_bar); usage_layout.addRow("SRAM/Data:", mw.sram_usage_bar)
        layout.addWidget(usage_group); disclaimer = QLabel("<small><i>Estimates are heuristics.</i></small>"); disclaimer.setWordWrap(True); layout.addWidget(disclaimer); layout.addStretch(); mw.resource_estimation_dock.setWidget(widget)

    def _populate_live_preview_dock(self):
        """Creates the contents of the live code preview dock."""
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
        mw.live_preview_editor.setObjectName("LivePreviewEditor") # For styling
        mw.live_preview_editor.setPlaceholderText("Edit the diagram to see a live code preview...")
        layout.addWidget(mw.live_preview_editor, 1)

        mw.live_preview_dock.setWidget(widget)

    def _create_status_bar(self):
        mw = self.mw; status_bar = QStatusBar(mw); mw.setStatusBar(status_bar)
        
        mw.main_op_status_label = QLabel("Ready"); status_bar.addWidget(mw.main_op_status_label, 1)

        def create_status_segment(icon_enum, icon_alt, text, tooltip, obj_name):
            container = QWidget()
            layout = QHBoxLayout(container); layout.setContentsMargins(4,0,4,0); layout.setSpacing(3)
            icon_label = QLabel(); icon_label.setPixmap(get_standard_icon(icon_enum, icon_alt).pixmap(QSize(12,12)))
            text_label = QLabel(text); text_label.setObjectName(obj_name)
            layout.addWidget(icon_label); layout.addWidget(text_label)
            container.setToolTip(tooltip)
            status_bar.addPermanentWidget(container)
            return text_label, icon_label

        mw.mode_status_label, mw.mode_icon_label = create_status_segment(QStyle.SP_ArrowRight, "Sel", "Select", "Interaction Mode", "InteractionModeStatusLabel")
        mw.zoom_status_label, mw.zoom_icon_label = create_status_segment(QStyle.SP_FileDialogInfoView, "Zoom", "100%", "Zoom Level", "ZoomStatusLabel")
        mw.pysim_status_label, mw.pysim_icon_label = create_status_segment(QStyle.SP_MediaStop, "PySim", "Idle", "Python Sim Status", "PySimStatusLabel")
        mw.matlab_status_label, mw.matlab_icon_label = create_status_segment(QStyle.SP_MessageBoxWarning, "MATLAB", "Not Conn.", "MATLAB Status", "MatlabStatusLabel")
        mw.net_icon_label, mw.net_status_label = create_status_segment(QStyle.SP_MessageBoxQuestion, "Net", "Checking...", "Internet Status", "InternetStatusLabel") # Note: swapped order for consistency

        mw.resource_monitor_widget = QWidget()
        res_layout = QHBoxLayout(mw.resource_monitor_widget); res_layout.setContentsMargins(4,0,4,0); res_layout.setSpacing(5)
        mw.cpu_status_label = QLabel("CPU: --%"); res_layout.addWidget(mw.cpu_status_label)
        mw.ram_status_label = QLabel("RAM: --%"); res_layout.addWidget(mw.ram_status_label)
        mw.gpu_status_label = QLabel("GPU: N/A"); res_layout.addWidget(mw.gpu_status_label)
        status_bar.addPermanentWidget(mw.resource_monitor_widget)
        mw.resource_monitor_widget.setVisible(False)
        
        mw.progress_bar = QProgressBar(); mw.progress_bar.setRange(0,0); mw.progress_bar.hide(); mw.progress_bar.setMaximumWidth(120); mw.progress_bar.setTextVisible(False)
        status_bar.addPermanentWidget(mw.progress_bar)