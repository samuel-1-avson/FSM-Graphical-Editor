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
from . import config
from .graphics_scene import MinimapView # NEW: Import MinimapView
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
                # Correctly handle the slot connection for opening a file
                btn.clicked.connect(lambda ch, p=path: self.mw._create_and_load_new_tab(p) if not self.mw.find_editor_by_path(p) else self.mw.tab_widget.setCurrentWidget(self.mw.find_editor_by_path(p)))
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

    def _create_tool