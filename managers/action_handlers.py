# fsm_designer_project/actions/action_handlers.py
import logging
from PyQt6.QtCore import QObject
from ..actions import (
    EditActionHandler, ExportActionHandler, FileActionHandler, GitActionHandler,
    HelpActionHandler, SimulationActionHandler, ViewActionHandler
)

logger = logging.getLogger(__name__)

class ActionHandler(QObject):
    """
    Coordinator for all user actions.
    This class instantiates and delegates to more focused action handlers.
    """
    def __init__(self, main_window):
        super().__init__(main_window)
        self.mw = main_window

        # Instantiate sub-handlers
        self.file_handler = FileActionHandler(main_window)
        self.edit_handler = EditActionHandler(main_window)
        self.view_handler = ViewActionHandler(main_window)
        self.sim_handler = SimulationActionHandler(main_window)
        self.export_handler = ExportActionHandler(main_window)
        self.git_handler = GitActionHandler(main_window)
        self.help_handler = HelpActionHandler(main_window)

        self.editing_actions = []

    def populate_editing_actions(self):
        """Populates the list of editing actions after the UI has been created."""
        self.editing_actions = [
            self.mw.new_action, self.mw.open_action, self.mw.save_action, 
            self.mw.save_as_action, self.mw.undo_action, self.mw.redo_action,
            self.mw.delete_action, self.mw.select_all_action,
            self.mw.find_item_action,
            self.mw.add_state_mode_action, self.mw.add_transition_mode_action,
            self.mw.add_comment_mode_action, self.mw.auto_layout_action,
            self.mw.save_selection_as_template_action, self.mw.import_from_text_action
        ]
        if hasattr(self.mw, 'align_actions'):
            self.editing_actions.extend(self.mw.align_actions)
        if hasattr(self.mw, 'distribute_actions'):
            self.editing_actions.extend(self.mw.distribute_actions)

    def set_editing_actions_enabled(self, enabled: bool):
        for action in self.editing_actions:
            if hasattr(action, 'setEnabled'):
                action.setEnabled(enabled)
        if hasattr(self.mw, 'mode_action_group'):
            self.mw.mode_action_group.setEnabled(enabled)

    def connect_actions(self):
        """Connects all QAction triggers to the appropriate sub-handler slots."""
        # --- FIX: The main window's "New Project" action was inconsistently connected to creating a new file.
        # It is now correctly connected to the on_new_project handler to match its text.
        # The welcome screen button creates projects, and the main menu's "New" creates a file. This was swapped.
        self.mw.new_action.triggered.connect(self.file_handler.on_new_project)
        self.mw.new_file_action.triggered.connect(self.file_handler.on_new_file)
        self.mw.open_action.triggered.connect(self.file_handler.on_open_file)
        self.mw.close_project_action.triggered.connect(self.file_handler.on_close_project)
        self.mw.save_action.triggered.connect(self.file_handler.on_save_file)
        self.mw.save_as_action.triggered.connect(self.file_handler.on_save_file_as)
        self.mw.import_from_text_action.triggered.connect(self.file_handler.on_import_from_text)
        self.mw.export_png_action.triggered.connect(self.file_handler.on_export_png)
        self.mw.export_svg_action.triggered.connect(self.file_handler.on_export_svg)

        # EXPORT ACTIONS
        self.mw.export_simulink_action.triggered.connect(self.export_handler.on_export_simulink)
        self.mw.generate_c_code_action.triggered.connect(self.export_handler.on_generate_c_code)
        self.mw.generate_matlab_code_action.triggered.connect(self.export_handler.on_generate_matlab_code)
        self.mw.export_arduino_action.triggered.connect(self.export_handler.on_export_arduino)
        self.mw.export_plantuml_action.triggered.connect(self.export_handler.on_export_plantuml)
        self.mw.export_mermaid_action.triggered.connect(self.export_handler.on_export_mermaid)
        self.mw.export_python_fsm_action.triggered.connect(self.export_handler.on_export_python_fsm)
        self.mw.export_c_testbench_action.triggered.connect(self.export_handler.on_export_c_testbench)
        self.mw.export_vhdl_action.triggered.connect(self.export_handler.on_export_vhdl)
        self.mw.export_verilog_action.triggered.connect(self.export_handler.on_export_verilog)

        # EDIT ACTIONS
        self.mw.select_all_action.triggered.connect(self.edit_handler.on_select_all)
        self.mw.delete_action.triggered.connect(self.edit_handler.on_delete_selected)
        self.mw.find_item_action.triggered.connect(self.edit_handler.on_show_find_item_dialog)
        self.mw.save_selection_as_template_action.triggered.connect(self.edit_handler.on_save_selection_as_template)

        # VIEW ACTIONS
        self.mw.zoom_in_action.triggered.connect(self.view_handler.on_zoom_in)
        self.mw.zoom_out_action.triggered.connect(self.view_handler.on_zoom_out)
        self.mw.reset_zoom_action.triggered.connect(self.view_handler.on_reset_zoom)
        self.mw.zoom_to_selection_action.triggered.connect(self.view_handler.on_zoom_to_selection)
        self.mw.fit_diagram_action.triggered.connect(self.view_handler.on_fit_diagram_in_view)
        self.mw.auto_layout_action.triggered.connect(self.view_handler.on_auto_layout_diagram)
        self.mw.show_grid_action.triggered.connect(lambda c: self.view_handler.on_toggle_view_setting("view_show_grid", c))
        self.mw.snap_to_grid_action.triggered.connect(lambda c: self.view_handler.on_toggle_view_setting("view_snap_to_grid", c))
        self.mw.snap_to_objects_action.triggered.connect(lambda c: self.view_handler.on_toggle_view_setting("view_snap_to_objects", c))
        self.mw.show_snap_guidelines_action.triggered.connect(lambda c: self.view_handler.on_toggle_view_setting("view_show_snap_guidelines", c))
        self.mw.align_left_action.triggered.connect(lambda: self.view_handler.on_align_items("left"))
        self.mw.align_center_h_action.triggered.connect(lambda: self.view_handler.on_align_items("center_h"))
        self.mw.align_right_action.triggered.connect(lambda: self.view_handler.on_align_items("right"))
        self.mw.align_top_action.triggered.connect(lambda: self.view_handler.on_align_items("top"))
        self.mw.align_middle_v_action.triggered.connect(lambda: self.view_handler.on_align_items("middle_v"))
        self.mw.align_bottom_action.triggered.connect(lambda: self.view_handler.on_align_items("bottom"))
        self.mw.distribute_h_action.triggered.connect(lambda: self.view_handler.on_distribute_items("horizontal"))
        self.mw.distribute_v_action.triggered.connect(lambda: self.view_handler.on_distribute_items("vertical"))

        # SIMULATION ACTIONS
        self.mw.start_py_sim_action.triggered.connect(self.sim_handler.on_start_python_simulation)
        self.mw.stop_py_sim_action.triggered.connect(self.sim_handler.on_stop_python_simulation)
        self.mw.reset_py_sim_action.triggered.connect(self.sim_handler.on_reset_python_simulation)
        self.mw.run_simulation_action.triggered.connect(self.sim_handler.on_run_matlab_simulation)

        # GIT ACTIONS
        self.mw.git_commit_action.triggered.connect(self.git_handler.on_git_commit)
        self.mw.git_push_action.triggered.connect(self.git_handler.on_git_push)
        self.mw.git_pull_action.triggered.connect(self.git_handler.on_git_pull)
        self.mw.git_show_changes_action.triggered.connect(self.git_handler.on_git_show_changes)
        
        # HELP & MISC ACTIONS
        self.mw.quick_start_action.triggered.connect(self.help_handler.on_show_quick_start)
        self.mw.about_action.triggered.connect(self.help_handler.on_about)
        self.mw.host_action.triggered.connect(self.help_handler.on_show_system_info)
        self.mw.customize_quick_access_action.triggered.connect(self.help_handler.on_customize_quick_access)
        self.mw.open_example_traffic_action.triggered.connect(lambda: self.file_handler._open_example_file("traffic_light.bsm"))
        self.mw.open_example_toggle_action.triggered.connect(lambda: self.file_handler._open_example_file("simple_toggle.bsm"))
        self.mw.open_example_coffee_action.triggered.connect(lambda: self.file_handler._open_example_file("coffee_machine.bsm")) 
        
        # --- NEW CONNECTION ---
        self.mw.generate_docs_action.triggered.connect(self.mw.ai_chat_ui_manager.on_generate_docs_with_ai)
        # --- END NEW ---

        # Log Actions
        if hasattr(self.mw, 'log_save_action'):
            self.mw.log_save_action.triggered.connect(self.file_handler.on_save_log)
        if hasattr(self.mw, 'log_copy_action'):
            self.mw.log_copy_action.triggered.connect(self.edit_handler.on_copy_log)

    def on_open_recent_file(self):
        self.file_handler.on_open_recent_file()
        
    def add_to_recent_files(self, file_path):
        self.file_handler.add_to_recent_files(file_path)

    def remove_from_recent_files(self, file_path):
        self.file_handler.remove_from_recent_files(file_path)
    
    def on_project_explorer_context_menu(self, point):
        self.file_handler.on_project_explorer_context_menu(point)

    def apply_ai_fix(self, fix_data):
        self.edit_handler.apply_ai_fix(fix_data)

    def _open_example_file(self, filename):
        self.file_handler._open_example_file(filename)