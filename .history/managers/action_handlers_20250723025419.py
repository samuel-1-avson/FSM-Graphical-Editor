# fsm_designer_project/managers/action_handlers.py
import os
import json
import logging
from PyQt5.QtWidgets import (
    QFileDialog, QMessageBox, QInputDialog, QDialog, QFormLayout, QLineEdit, QPushButton, QHBoxLayout,
    QStyle, QDialogButtonBox, QVBoxLayout, QTextEdit,
    QGraphicsScene, QComboBox, QApplication, QCheckBox, QMenu, QAction, QGroupBox, QPoint, QTreeView
)
# --- MODIFIED IMPORT: Added QModelIndex ---
from PyQt5.QtCore import QObject, pyqtSlot, QDir, QUrl, QPointF, Qt, QRectF, QSizeF, QDateTime, QFile, QIODevice, QModelIndex, QVariant, QTimer
from PyQt5.QtGui import QDesktopServices, QImage, QPainter, QPixmap, QIcon
from PyQt5.QtSvg import QSvgGenerator
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QGroupBox
from ..io.c_code_generator import generate_c_code_files, generate_c_testbench_content, sanitize_c_identifier
# Import pygraphviz optionally
try:
    import pygraphviz as pgv
    PYGRAPHVIZ_AVAILABLE = True
except ImportError:
    PYGRAPHVIZ_AVAILABLE = False
    pgv = None # Ensure pgv is defined to avoid runtime errors on check

from ..utils import get_standard_icon, _get_bundled_file_path
from ..utils.config import FILE_FILTER, FILE_EXTENSION, DEFAULT_EXECUTION_ENV
from ..undo_commands import MoveItemsCommand, AddItemCommand, EditItemPropertiesCommand
from ..io.python_code_generator import generate_python_fsm_file
from ..io.export_utils import generate_plantuml_text, generate_mermaid_text
from ..io.hdl_code_generator import generate_vhdl_content, sanitize_vhdl_identifier, generate_verilog_content
from ..ui.graphics.graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem
from ..plugins.api import BsmExporterPlugin
from ..ui.dialogs import ImportFromTextDialog
from ..ui.dialogs.tool_dialogs import NewProjectDialog
from ..managers.project_manager import PROJECT_FILE_FILTER, PROJECT_FILE_EXTENSION
logger = logging.getLogger(__name__)

class ActionHandler(QObject):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.mw = main_window
        self.last_commit_message = "" # For async git commit

        # --- MODIFIED: Defer initialization of this list until actions are created. ---
        self.editing_actions = []
        # --- END MODIFICATION ---

    # --- NEW METHOD TO DEFER POPULATION ---
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
        # Also include alignment/distribution actions if they exist
        if hasattr(self.mw, 'align_actions'):
            self.editing_actions.extend(self.mw.align_actions)
        if hasattr(self.mw, 'distribute_actions'):
            self.editing_actions.extend(self.mw.distribute_actions)
    # --- END NEW METHOD ---

    # --- NEW: Method to control editing actions ---
    def set_editing_actions_enabled(self, enabled: bool):
        """Enables or disables all actions related to diagram editing."""
        for action in self.editing_actions:
            if hasattr(action, 'setEnabled'):
                action.setEnabled(enabled)

        # Also manage the mode action group as a whole
        if hasattr(self.mw, 'mode_action_group'):
            self.mw.mode_action_group.setEnabled(enabled)
            
        logger.debug(f"Editing actions enabled state set to: {enabled}")
    # --- END NEW ---

    def connect_actions(self):
        # File Actions
        self.mw.new_action.triggered.connect(self.on_new_file)
        self.mw.open_action.triggered.connect(self.on_open_file)
        self.mw.close_project_action.triggered.connect(self.on_close_project)
        self.mw.save_action.triggered.connect(self.on_save_file)
        self.mw.save_as_action.triggered.connect(self.on_save_file_as)
        self.mw.export_simulink_action.triggered.connect(self.on_export_simulink)
        self.mw.generate_c_code_action.triggered.connect(self.on_generate_c_code)
        self.mw.export_arduino_action.triggered.connect(self.on_export_arduino)
        if hasattr(self.mw, 'export_c_testbench_action'):
            self.mw.export_c_testbench_action.triggered.connect(self.on_export_c_testbench)
        self.mw.export_plantuml_action.triggered.connect(self.on_export_plantuml)
        self.mw.export_mermaid_action.triggered.connect(self.on_export_mermaid)
        self.mw.export_python_fsm_action.triggered.connect(self.on_export_python_fsm)
        self.mw.export_png_action.triggered.connect(self.on_export_png)
        self.mw.export_svg_action.triggered.connect(self.on_export_svg)
        if hasattr(self.mw, 'export_vhdl_action'):
            self.mw.export_vhdl_action.triggered.connect(self.on_export_vhdl)
        if hasattr(self.mw, 'export_verilog_action'):
            self.mw.export_verilog_action.triggered.connect(self.on_export_verilog)


        # Edit Actions
        self.mw.select_all_action.triggered.connect(self.on_select_all)
        self.mw.delete_action.triggered.connect(self.on_delete_selected)
        self.mw.find_item_action.triggered.connect(self.on_show_find_item_dialog)
        self.mw.save_selection_as_template_action.triggered.connect(self.on_save_selection_as_template) # New
       
        # --- LOG ACTIONS (NEW) ---
        if hasattr(self.mw, 'log_save_action'):
            self.mw.log_save_action.triggered.connect(self.on_save_log)
        if hasattr(self.mw, 'log_copy_action'):
            self.mw.log_copy_action.triggered.connect(self.on_copy_log)

        # View Actions
        self.mw.show_grid_action.triggered.connect(lambda checked: self.on_toggle_view_setting("view_show_grid", checked))
        self.mw.snap_to_grid_action.triggered.connect(lambda checked: self.on_toggle_view_setting("view_snap_to_grid", checked))
        self.mw.snap_to_objects_action.triggered.connect(lambda checked: self.on_toggle_view_setting("view_snap_to_objects", checked))
        self.mw.show_snap_guidelines_action.triggered.connect(lambda checked: self.on_toggle_view_setting("view_show_snap_guidelines", checked))
        self.mw.zoom_to_selection_action.triggered.connect(self.on_zoom_to_selection)
        self.mw.fit_diagram_action.triggered.connect(self.on_fit_diagram_in_view)
        self.mw.auto_layout_action.triggered.connect(self.on_auto_layout_diagram)

        # Align/Distribute Actions
        self.mw.align_left_action.triggered.connect(lambda: self.on_align_items("left"))
        self.mw.align_center_h_action.triggered.connect(lambda: self.on_align_items("center_h"))
        self.mw.align_right_action.triggered.connect(lambda: self.on_align_items("right"))
        self.mw.align_top_action.triggered.connect(lambda: self.on_align_items("top"))
        self.mw.align_middle_v_action.triggered.connect(lambda: self.on_align_items("middle_v"))
        self.mw.align_bottom_action.triggered.connect(lambda: self.on_align_items("bottom"))
        self.mw.distribute_h_action.triggered.connect(lambda: self.on_distribute_items("horizontal"))
        self.mw.distribute_v_action.triggered.connect(lambda: self.on_distribute_items("vertical"))
        
        # --- FIX: ADD MISSING SIMULATION ACTION CONNECTIONS ---
        if hasattr(self.mw, 'start_py_sim_action'):
            self.mw.start_py_sim_action.triggered.connect(self.mw.py_sim_ui_manager.on_start_py_simulation)
        if hasattr(self.mw, 'stop_py_sim_action'):
            self.mw.stop_py_sim_action.triggered.connect(lambda: self.mw.py_sim_ui_manager.on_stop_py_simulation(silent=False))
        if hasattr(self.mw, 'reset_py_sim_action'):
            self.mw.reset_py_sim_action.triggered.connect(self.mw.py_sim_ui_manager.on_reset_py_simulation)
        # --- END FIX ---
        
        # --- Git Actions ---
        if hasattr(self.mw, 'git_commit_action'):
            self.mw.git_commit_action.triggered.connect(self.on_git_commit)
            self.mw.git_pull_action.triggered.connect(self.on_git_pull)
            self.mw.git_push_action.triggered.connect(self.on_git_push)
            self.mw.git_show_changes_action.triggered.connect(self.on_git_show_changes)
            
        # Help Actions
        self.mw.quick_start_action.triggered.connect(self.on_show_quick_start)
        self.mw.about_action.triggered.connect(self.on_about)


        if hasattr(self.mw, 'import_from_text_action'):
            self.mw.import_from_text_action.triggered.connect(self.on_import_from_text)


        # Example Actions
        self.mw.open_example_traffic_action.triggered.connect(lambda: self._open_example_file("traffic_light.bsm"))
        self.mw.open_example_toggle_action.triggered.connect(lambda: self._open_example_file("simple_toggle.bsm"))

    @pyqtSlot()
    def on_close_project(self):
        """Closes the current project after prompting to save all open files."""
        if not self.mw.project_manager.is_project_open():
            self.mw.log_message("INFO", "Close project action triggered, but no project is open.")
            return

        # Prompt to save all dirty tabs
        for i in range(self.mw.tab_widget.count()):
            editor = self.mw.tab_widget.widget(i)
            if not self.mw._prompt_save_on_close(editor):
                # User cancelled, so abort closing the project
                return

        # All saves/discards were successful, proceed with closing
        self.mw.project_manager.close_project()

    # --- GIT ACTION HANDLERS ---
    def _get_current_file_path_for_git(self) -> str | None:
        """Helper to get a valid file path from the current editor for Git operations."""
        editor = self.mw.current_editor()
        if not editor or not editor.file_path:
            QMessageBox.warning(self.mw, "Git Error", "The current file has not been saved yet.")
            return None
        return editor.file_path

    # --- START: NEW LOG ACTION HANDLERS ---
    @pyqtSlot()
    def on_save_log(self):
        """Saves the entire log history to a text file."""
        if not hasattr(self.mw, 'ui_log_handler'):
            QMessageBox.warning(self.mw, "Error", "Log handler not available.")
            return

        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd_HH-mm-ss")
        default_filename = f"fsm_designer_log_{timestamp}.log"
        start_dir = QDir.homePath()

        file_path, _ = QFileDialog.getSaveFileName(self.mw, "Save Log File",
                                                   os.path.join(start_dir, default_filename),
                                                   "Log Files (*.log);;Text Files (*.txt);;All Files (*)")
        if file_path:
            try:
                log_content = self.mw.ui_log_handler.get_full_log_text(plain=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                self.mw.log_message("INFO", f"Log saved successfully to: {file_path}")
            except Exception as e:
                logger.error(f"Error saving log file: {e}", exc_info=True)
                QMessageBox.critical(self.mw, "File Save Error", f"Could not save log file: {e}")


    @pyqtSlot()
    def on_import_from_text(self):
        dialog = ImportFromTextDialog(self.mw)
        if dialog.exec_():
            diagram_data = dialog.get_diagram_data()
            if diagram_data and (diagram_data['states'] or diagram_data['transitions']):
                # Decide whether to clear or add to the current diagram
                reply = QMessageBox.question(self.mw, "Import FSM",
                                             "Do you want to clear the current diagram before importing?",
                                             QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                                             QMessageBox.Yes)
                
                if reply == QMessageBox.Cancel:
                    return
                
                clear_current = (reply == QMessageBox.Yes)
                self.mw._add_fsm_data_to_scene(diagram_data, clear_current_diagram=clear_current, original_user_prompt="Text Import")
                self.mw.log_message("INFO", "Successfully imported FSM from text.")

    @pyqtSlot()
    def on_copy_log(self):
        """Copies the entire log history to the clipboard."""
        if not hasattr(self.mw, 'ui_log_handler'):
            QMessageBox.warning(self.mw, "Error", "Log handler not available.")
            return

        log_content = self.mw.ui_log_handler.get_full_log_text(plain=True)
        clipboard = QApplication.clipboard()
        clipboard.setText(log_content)
        self.mw.log_message("INFO", "Log content copied to clipboard.")
    # --- END: NEW LOG ACTION HANDLERS ---

    # --- NEW: Generic Handler for Plugins ---
    @pyqtSlot(dict)
    def apply_ai_fix(self, fix_data: dict):
        """
        Dispatcher to apply a fix suggested by the AI.
        All operations must use the undo stack.
        """
        editor = self.mw.current_editor()
        if not editor:
            self.mw.log_message("WARNING", "Cannot apply AI fix: No active editor.")
            return

        action_type = fix_data.get("action")
        details = fix_data.get("details", {})
        
        self.mw.log_message("INFO", f"Attempting to apply AI-suggested fix: {action_type}")

        try:
            if action_type == "add_transition":
                source_item = editor.scene.get_state_by_name(details.get("source"))
                target_item = editor.scene.get_state_by_name(details.get("target"))
                if source_item and target_item:
                    new_trans = GraphicsTransitionItem(
                        start_item=source_item,
                        end_item=target_item,
                        event_str=details.get("event", "ai_event")
                    )
                    cmd = AddItemCommand(editor.scene, new_trans, "AI: Add Transition")
                    editor.undo_stack.push(cmd)
                    new_trans.setSelected(True)
                else:
                    raise ValueError(f"Source or target state not found ('{details.get('source')}' -> '{details.get('target')}').")
            
            elif action_type == "add_state":
                name = details.get("name", "AI_State")
                if editor.scene.get_state_by_name(name):
                    raise ValueError(f"State '{name}' already exists.")
                
                # Position the new state near the center of the current view
                view_center = editor.view.mapToScene(editor.view.viewport().rect().center())
                new_state = GraphicsStateItem(view_center.x(), view_center.y(), 120, 60, name)
                if self.mw: self.mw.connect_state_item_signals(new_state)
                
                cmd = AddItemCommand(editor.scene, new_state, f"AI: Add State '{name}'")
                editor.undo_stack.push(cmd)
                new_state.setSelected(True)

            elif action_type == "rename_state":
                old_name = details.get("old_name")
                new_name = details.get("new_name")
                item_to_rename = editor.scene.get_state_by_name(old_name)
                if not item_to_rename:
                    raise ValueError(f"State '{old_name}' not found for renaming.")
                if editor.scene.get_state_by_name(new_name):
                     raise ValueError(f"Cannot rename to '{new_name}' because a state with that name already exists.")

                old_props = item_to_rename.get_data()
                new_props = old_props.copy()
                new_props["name"] = new_name
                cmd = EditItemPropertiesCommand(item_to_rename, old_props, new_props, f"AI: Rename State")
                editor.undo_stack.push(cmd)
            
            else:
                raise NotImplementedError(f"AI action '{action_type}' is not yet implemented.")
            
            self.mw.log_message("SUCCESS", f"Successfully applied AI fix: {action_type}")
            editor.scene.run_all_validations("AfterAIAction")

        except (ValueError, NotImplementedError) as e:
            self.mw.log_message("ERROR", f"Failed to apply AI fix: {e}")
            QMessageBox.critical(self.mw, "AI Fix Failed", f"Could not apply the suggested fix:\n{e}")


    @pyqtSlot(QPoint)
    def on_project_explorer_context_menu(self, point):
        """Creates and displays a context menu for the project explorer."""
        if not self.mw.project_manager.is_project_open():
            return # No context menu if no project is open

        index = self.mw.project_tree_view.indexAt(point)
        model = self.mw.project_fs_model
    
        path = model.filePath(index) if index.isValid() else self.mw.project_manager.current_project_path
        if not path: return
        
        is_dir = model.isDir(index)
        is_root = model.index(path) == self.mw.project_tree_view.rootIndex()

        menu = QMenu(self.mw)

        if is_dir:
            menu.addAction("New Diagram...", lambda: self._create_new_project_file('bsm', path))
            menu.addAction("New Python Script...", lambda: self._create_new_project_file('py', path))
            menu.addSeparator()
            if not is_root:
                menu.addAction("Rename Folder...", lambda: self._rename_project_item(index))
                menu.addAction("Delete Folder", lambda: self._delete_project_item(index))
        elif index.isValid(): # It's a file
            if path.endswith(".bsm"):
                menu.addAction("Open in New Tab", lambda: self.mw._create_and_load_new_tab(path))
                menu.addAction("Set as Main Diagram", lambda: self._on_set_as_main_diagram(path))
                menu.addSeparator()
            elif path.endswith(('.py', '.c', '.h', '.ino')):
                menu.addAction("Open in IDE", lambda: self._on_open_in_ide(path))
                menu.addSeparator()

            menu.addAction("Rename File...", lambda: self._rename_project_item(index))
            menu.addAction("Delete File", lambda: self._delete_project_item(index))
    
        # Reveal in system file browser is always useful
        menu.addSeparator()
        menu.addAction("Reveal in File Explorer", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path) if  index.isValid() else path)))
    
        menu.exec_(self.mw.project_tree_view.viewport().mapToGlobal(point))


    @pyqtSlot(BsmExporterPlugin)
    def on_export_with_plugin(self, plugin: BsmExporterPlugin):
        """Generic handler that uses a plugin to export the diagram."""
        editor = self.mw.current_editor()
        if not editor or not editor.scene.items():
            QMessageBox.information(self.mw, "Empty Diagram", f"Cannot generate {plugin.name} for an empty diagram.")
            return

        start_dir = os.path.dirname(editor.file_path) if editor.file_path else QDir.homePath()
        
        # Use the file filter provided by the plugin
        file_path, _ = QFileDialog.getSaveFileName(self.mw, f"Export as {plugin.name}",
                                                   start_dir,
                                                   plugin.file_filter)
        if not file_path:
            return

        diagram_data = editor.scene.get_diagram_data()
        try:
            # Call the plugin's export method
            file_content = plugin.export(diagram_data)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_content)
            
            QMessageBox.information(self.mw, "Export Successful", f"{plugin.name} exported successfully to:\n{file_path}")
            logger.info(f"Successfully exported '{plugin.name}' to {file_path}")
        except Exception as e:
            QMessageBox.critical(self.mw, "Plugin Export Error", f"An error occurred while exporting with '{plugin.name}':\n{e}")
            logger.error(f"Error during plugin export for '{plugin.name}': {e}", exc_info=True)


    @pyqtSlot()
    def on_export_c_testbench(self):
        """Handler for exporting a C testbench file for the FSM."""
        editor = self.mw.current_editor()
        if not editor or not editor.scene.items():
            QMessageBox.information(self.mw, "Empty Diagram", "Cannot generate a testbench for an empty diagram.")
            return

        # Use the same base name as the FSM code for consistency.
        default_filename_base = "fsm_generated"
        if editor.file_path:
            default_filename_base = os.path.splitext(os.path.basename(editor.file_path))[0]
        
        # We need the sanitized name to suggest the filename.
        fsm_name_c = sanitize_c_identifier(default_filename_base, "fsm_")

        # Suggest a filename like 'my_fsm_test.c'
        default_test_filename = f"{fsm_name_c}_test.c"
        start_dir = os.path.dirname(editor.file_path) if editor.file_path else QDir.homePath()

        file_path, _ = QFileDialog.getSaveFileName(self.mw, "Save C Testbench File",
                                                   os.path.join(start_dir, default_test_filename),
                                                   "C Source Files (*.c);;All Files (*)")
        if not file_path:
            return

        diagram_data = editor.scene.get_diagram_data()
        try:
            # Call the new backend function
            testbench_code = generate_c_testbench_content(diagram_data, fsm_name_c)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(testbench_code)
            
            QMessageBox.information(self.mw, "Testbench Generation Successful", f"C testbench file generated successfully:\n{file_path}\n\nRemember to also export the main FSM C files to compile against it.")
        except Exception as e:
            QMessageBox.critical(self.mw, "Testbench Generation Error", f"Failed to generate testbench: {e}")


    @pyqtSlot()
    def on_git_commit(self):
        file_path = self._get_current_file_path_for_git()
        if not file_path:
            return

        editor = self.mw.current_editor()
        if editor.is_dirty():
            reply = QMessageBox.question(self.mw, "Unsaved Changes",
                                         "The current file has unsaved changes. You should save before committing.\nSave now?",
                                         QMessageBox.Save | QMessageBox.Cancel, QMessageBox.Save)
            if reply == QMessageBox.Save:
                if not self.on_save_file(): # on_save_file returns False on failure/cancel
                    return
            else:
                return

        commit_message, ok = QInputDialog.getMultiLineText(self.mw, "Git Commit", "Enter commit message for this file:")
        if ok and commit_message.strip():
            self.last_commit_message = commit_message.strip()
            if hasattr(self.mw, 'statusBar') and self.mw.statusBar() and hasattr(self.mw.statusBar(), 'set_status'):
                self.mw.statusBar().set_status(f"Staging {os.path.basename(file_path)}...")
            else:
                self.mw.main_op_status_label.setText(f"Staging {os.path.basename(file_path)}...")

            # Use '--' for safety with weird filenames
            self.mw.git_manager.run_command_in_repo(
                ['git', 'add', '--', file_path],
                file_path,
                self._on_git_add_finished_for_commit
            )
        elif ok:
            QMessageBox.warning(self.mw, "Empty Message", "Commit message cannot be empty.")

    def _on_git_add_finished_for_commit(self, success, stdout, stderr):
        """Callback after 'git add' completes, before 'git commit'."""
        if not success:
            QMessageBox.critical(self.mw, "Git Add Error", f"Could not stage file for commit:\n{stderr}")
            if hasattr(self.mw, 'statusBar') and self.mw.statusBar() and hasattr(self.mw.statusBar(), 'set_status'):
                self.mw.statusBar().set_status("Ready.", "info", 3000)
            else:
                self.mw.main_op_status_label.setText("Ready.")
            return
            
        # Get the file path again to ensure we commit only this file.
        file_path = self._get_current_file_path_for_git()
        if not file_path:
            QMessageBox.critical(self.mw, "Git Commit Error", "Could not determine the file path to commit.")
            if hasattr(self.mw, 'statusBar') and self.mw.statusBar() and hasattr(self.mw.statusBar(), 'set_status'):
                self.mw.statusBar().set_status("Ready.", "info", 3000)
            else:
                self.mw.main_op_status_label.setText("Ready.")
            return

        # Now that the file is staged, proceed with the commit for only this file.
        # The path argument ensures we commit ONLY the changes for the specified file.
        # The '--' ensures the path is not misinterpreted as an option.
        command = ['git', 'commit', '-m', self.last_commit_message, '--', file_path]
        self.mw.run_git_command(command, "Commit")
    
    @pyqtSlot()
    def on_git_pull(self):
        if self._get_current_file_path_for_git():
            self.mw.run_git_command(['git', 'pull'], "Pull")

    @pyqtSlot()
    def on_git_push(self):
        if self._get_current_file_path_for_git():
            self.mw.run_git_command(['git', 'push'], "Push")

    @pyqtSlot()
    def on_git_show_changes(self):
        file_path = self._get_current_file_path_for_git()
        if not file_path:
            return

        self.mw.git_manager.run_command_in_repo(
            ['git', 'diff', '--', file_path],
            file_path,
            self._on_git_show_changes_finished
        )
        if hasattr(self.mw, 'statusBar') and self.mw.statusBar() and hasattr(self.mw.statusBar(), 'set_status'):
            self.mw.statusBar().set_status("Checking Git diff...")
        else:
            self.mw.main_op_status_label.setText("Checking Git diff...")

    def _on_git_show_changes_finished(self, success, stdout, stderr):
        if hasattr(self.mw, 'statusBar') and self.mw.statusBar() and hasattr(self.mw.statusBar(), 'set_status'):
            self.mw.statusBar().set_status("Ready.", "info", 3000)
        else:
            self.mw.main_op_status_label.setText("Ready.")
        if not success:
            QMessageBox.critical(self.mw, "Git Diff Error", f"Could not get diff:\n{stderr}")
            return
        
        if not stdout.strip():
            QMessageBox.information(self.mw, "Git Diff", "No changes detected for the current file.")
            return

        dialog = QDialog(self.mw)
        dialog.setWindowTitle(f"Changes for {os.path.basename(self.mw.current_editor().file_path)}")
        dialog.setMinimumSize(700, 500)
        layout = QVBoxLayout(dialog)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setFontFamily("Consolas, 'Courier New', monospace")
        text_edit.setPlainText(stdout)
        layout.addWidget(text_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec_()
    
    
    
    def _on_set_as_main_diagram(self, file_path):
        """Sets the selected BSM file as the project's main diagram."""
        if not self.mw.project_manager.is_project_open(): return
    
        project_dir = os.path.dirname(self.mw.project_manager.current_project_path)
        relative_path = os.path.relpath(file_path, project_dir)
    
        self.mw.project_manager.project_data['main_diagram'] = relative_path
        if self.mw.project_manager.save_project():
            self.mw.log_message("INFO", f"Set '{relative_path}' as the main project diagram.")
        else:
            self.mw.log_message("ERROR", "Failed to save project after setting main diagram.")
    
    def _on_open_in_ide(self, file_path):
        """Opens a file in the integrated IDE dock."""
        if not hasattr(self.mw, 'ide_manager'): return
    
        if self.mw.ide_manager.prompt_ide_save_if_dirty():
            self.mw.ide_manager.open_file(file_path)
            self.mw.ide_dock.setVisible(True)
            self.mw.ide_dock.raise_()
    
    
    def _create_new_project_file(self, file_type: str, parent_dir: str):
        """Dialog to create a new file within the project."""
        title = "New BSM Diagram" if file_type == 'bsm' else "New Python Script"
        default_name = f"new_diagram.{file_type}" if file_type == 'bsm' else f"script.{file_type}"
    
        file_name, ok = QInputDialog.getText(self.mw, title, "Enter file name:", text=default_name)
        if ok and file_name:
            if not file_name.endswith(f".{file_type}"):
                file_name += f".{file_type}"
        
            new_path = os.path.join(parent_dir, file_name)
            if os.path.exists(new_path):
                QMessageBox.warning(self.mw, "File Exists", "A file with that name already exists in this location.")
                return

            try:
                # Create a minimal empty file
                with open(new_path, 'w', encoding='utf-8') as f:
                    if file_type == 'bsm':
                        f.write('{"states": [], "transitions": [], "comments": []}')
                    else:
                        f.write("# New script file\n")
                self.mw.log_message("INFO", f"Created new file: {new_path}")
            except OSError as e:
                QMessageBox.critical(self.mw, "Error", f"Could not create file: {e}")
                self.mw.log_message("ERROR", f"Could not create file: {e}")
    
    
    def _rename_project_item(self, index):
        """Renames a file or folder in the project explorer."""
        model = self.mw.project_fs_model
        old_path = model.filePath(index)
        old_name = model.fileName(index)

        new_name, ok = QInputDialog.getText(self.mw, "Rename Item", "Enter new name:", text=old_name)
        if ok and new_name and new_name != old_name:
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            if os.path.exists(new_path):
                QMessageBox.warning(self.mw, "Error", "An item with the new name already exists.")
                 return
        
            if not QDir().rename(old_path, new_path):
                QMessageBox.critical(self, "Rename Failed", "Could not rename the item.")
    
    
        
    def add_to_recent_files(self, file_path):
        """Adds a file path to the recent files list in settings."""
        if not self.mw.settings_manager:
            return
        
        recent_files = self.mw.settings_manager.get("recent_files", [])
        
        # Remove if it already exists to move it to the top
        if file_path in recent_files:
            recent_files.remove(file_path)
            
        # Add to the beginning of the list
        recent_files.insert(0, file_path)
        
        # Keep the list at a manageable size (e.g., 10 files)
        MAX_RECENT_FILES = 10
        del recent_files[MAX_RECENT_FILES:]
        
        self.mw.settings_manager.set("recent_files", recent_files)
        self.mw._populate_recent_files_menu() # Refresh menu
     
    @pyqtSlot()
    def on_open_recent_file(self):
        """Slot to open a file OR a project from the recent files menu."""
        action = self.mw.sender()
        if not action: return

        file_path = action.data()

        if file_path.endswith(PROJECT_FILE_EXTENSION):
            # It's a project file
            if self.mw.project_manager.is_project_open():
                # Don't open a project over another one
                QMessageBox.information(self.mw, "Project Open", "Please close the current project before opening another.")
                return
        
            if os.path.exists(file_path):
                self.mw.project_manager.load_project(file_path)
            else:
                QMessageBox.warning(self.mw, "File Not Found", f"The project file '{file_path}' could not be found.")
                self.remove_from_recent_files(file_path)
    
        else: # It's a single diagram file
            if self.mw.find_editor_by_path(file_path):
                self.mw.tab_widget.setCurrentWidget(self.mw.find_editor_by_path(file_path))
                return
         
            if os.path.exists(file_path):
                # Open the single file without a project context
                if self.mw.project_manager.is_project_open():
                     # You might want to ask the user if they want to add this file to the project here.
                     # For now, we'll just open it.
                     pass
                self.mw._create_and_load_new_tab(file_path)
            else:
                QMessageBox.warning(self.mw, "File Not Found", f"The diagram file '{file_path}' could not be found.")
                self.remove_from_recent_files(file_path)
    
    def remove_from_recent_files(self, file_path):
        """Removes a file path from the recent files list."""
        if not self.mw.settings_manager:
            return
        recent_files = self.mw.settings_manager.get("recent_files", [])
        if file_path in recent_files:
            recent_files.remove(file_path)
            self.mw.settings_manager.set("recent_files", recent_files)
            self.mw._populate_recent_files_menu() # Refresh menu
            
    @pyqtSlot()
    def on_auto_layout_diagram(self):
        editor = self.mw.current_editor()
        if not editor: return
        scene = editor.scene

        if not PYGRAPHVIZ_AVAILABLE:
            QMessageBox.critical(self.mw, "Dependency Error", "The 'pygraphviz' library is required for auto-layout but is not installed.\nPlease install it (`pip install pygraphviz`) and ensure Graphviz is in your system PATH.")
            return

        diagram_data = scene.get_diagram_data()
        states = diagram_data.get('states', [])
        transitions = diagram_data.get('transitions', [])

        if len(states) < 2:
            QMessageBox.information(self.mw, "Auto-Layout", "Auto-layout requires at least two states.")
            return

        try:
            # --- 1. Calculate new positions (without modifying the scene) ---
            G = pgv.AGraph(directed=True, strict=False, splines='spline')
            G.graph_attr.update(rankdir='TB', nodesep='0.8', ranksep='1.2')
            G.node_attr.update(shape='box', fixedsize='false', width='1.5', height='0.75')
            
            state_item_map = {state['name']: scene.get_state_by_name(state['name']) for state in states}
            for state_name, item in state_item_map.items():
                if item: G.add_node(state_name)
            
            for t in diagram_data.get('transitions', []):
                if t['source'] in state_item_map and t['target'] in state_item_map:
                    G.add_edge(t['source'], t['target'])
            
            G.layout(prog='dot')

            new_positions = {}
            graph_bbox = [float(val) for val in G.graph_attr['bb'].split(',')]
            offset_x = -graph_bbox[0] - (graph_bbox[2] - graph_bbox[0]) / 2.0
            offset_y = graph_bbox[3] + (graph_bbox[3] - graph_bbox[1]) / 2.0
            
            for node_name in G.nodes():
                item = state_item_map.get(node_name)
                if not item: continue
                try:
                    pos_str = node_name.attr['pos']
                    gv_x, gv_y = [float(p) for p in pos_str.split(',')]
                    new_pos = QPointF((gv_x + offset_x) - item.rect().width()/2, (-gv_y + offset_y) - item.rect().height()/2)
                    new_positions[item] = new_pos
                except (ValueError, KeyError) as e_pos:
                    logger.error(f"Error parsing position for node {node_name}: {e_pos}")

            # --- 2. Generate a preview image ---
            from ..ui.dialogs import AutoLayoutPreviewDialog
            preview_scene = QGraphicsScene()
            cloned_items = []
            for item, new_pos in new_positions.items():
                clone = GraphicsStateItem(0, 0, item.rect().width(), item.rect().height(), item.text_label)
                clone.set_properties(**item.get_data()) # Copy properties
                clone.setPos(new_pos)
                preview_scene.addItem(clone)
                cloned_items.append(clone)
            
            cloned_states_map = {clone.text_label: clone for clone in cloned_items}
            for t in diagram_data.get('transitions', []):
                src_clone = cloned_states_map.get(t['source'])
                tgt_clone = cloned_states_map.get(t['target'])
                if src_clone and tgt_clone:
                    # Create a temporary transition item for preview
                    trans_clone = GraphicsTransitionItem(src_clone, tgt_clone)
                    trans_clone.set_properties(**t) # Copy properties
                    preview_scene.addItem(trans_clone)

            preview_rect = preview_scene.itemsBoundingRect().adjusted(-20, -20, 20, 20)
            preview_pixmap = QPixmap(preview_rect.size().toSize())
            preview_pixmap.fill(Qt.white)
            painter = QPainter(preview_pixmap)
            preview_scene.render(painter, source=preview_rect)
            painter.end()

            # --- 3. Show the preview dialog ---
            preview_dialog = AutoLayoutPreviewDialog(preview_pixmap, self.mw)
            if preview_dialog.exec() == QDialog.Accepted:
                # --- 4. If accepted, apply the layout to the real scene ---
                moved_items_data = []
                for item, new_pos in new_positions.items():
                     if (new_pos - item.pos()).manhattanLength() > 1:
                        moved_items_data.append((item, item.pos(), new_pos))

                mean_delta = QPointF(0,0)
                if moved_items_data:
                    mean_delta = QPointF(sum(d[2].x() - d[1].x() for d in moved_items_data) / len(moved_items_data),
                                         sum(d[2].y() - d[1].y() for d in moved_items_data) / len(moved_items_data))

                comment_items = [item for item in scene.items() if isinstance(item, GraphicsCommentItem)]
                for item in comment_items:
                    moved_items_data.append((item, item.pos(), item.pos() + mean_delta))

                if moved_items_data:
                    cmd = MoveItemsCommand(moved_items_data, "Auto-Layout Diagram")
                    editor.undo_stack.push(cmd)
                    editor.set_dirty(True)
                    QTimer.singleShot(50, self.on_fit_diagram_in_view)
                    logger.info("Auto-layout applied successfully after preview.")
            else:
                logger.info("Auto-layout cancelled by user from preview.")

        except Exception as e:
            error_msg = str(e).strip()
            if 'dot' in error_msg.lower() and ('not found' in error_msg.lower() or 'no such file' in error_msg.lower()):
                 msg_detail = "Graphviz 'dot' command not found. Please ensure Graphviz is installed and its 'bin' directory is in your system's PATH."
            else:
                 msg_detail = f"An unexpected error occurred during auto-layout: {e}"
            QMessageBox.critical(self.mw, "Auto-Layout Error", msg_detail)
            logger.error(f"Auto-layout failed: {msg_detail}", exc_info=True)


    @pyqtSlot()
    def on_manage_snippets(self):
        from ..ui.dialogs import SnippetManagerDialog
        
        if not self.mw.custom_snippet_manager:
            logger.error("Cannot open snippet manager: CustomSnippetManager not initialized in MainWindow.")
            QMessageBox.critical(self.mw, "Error", "The Custom Snippet Manager is not available.")
            return

        dialog = SnippetManagerDialog(self.mw.custom_snippet_manager, self.mw)
        dialog.exec_()
        logger.info("Snippet Manager dialog closed.")

    @pyqtSlot()
    def on_save_selection_as_template(self):
        editor = self.mw.current_editor()
        if not editor:
            return

        selected_items = editor.scene.selectedItems()
        selected_states = [item for item in selected_items if isinstance(item, GraphicsStateItem)]

        if not selected_states:
            QMessageBox.information(self.mw, "No States Selected", "You must select at least one state to create a template.")
            return

        template_name, ok = QInputDialog.getText(self.mw, "Save as Template", "Enter a name for the new template:")
        if not ok or not template_name.strip():
            return

        template_name = template_name.strip()
        if self.mw.custom_snippet_manager.template_exists(template_name):
            reply = QMessageBox.question(self.mw, "Template Exists", 
                                         f"A template named '{template_name}' already exists. Overwrite it?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return

        template_data = {
            "name": template_name, "description": "A user-defined custom FSM template.",
            "states": [], "transitions": [], "comments": []
        }

        selected_state_names = {state.text_label for state in selected_states}
        
        min_x = min((item.x() for item in selected_items), default=0)
        min_y = min((item.y() for item in selected_items), default=0)

        for item in selected_items:
            data = item.get_data()
            data['x'] -= min_x
            data['y'] -= min_y
            
            if isinstance(item, GraphicsStateItem):
                template_data["states"].append(data)
            elif isinstance(item, GraphicsCommentItem):
                template_data["comments"].append(data)
            elif isinstance(item, GraphicsTransitionItem):
                if data['source'] in selected_state_names and data['target'] in selected_state_names:
                    template_data["transitions"].append(data)

        if self.mw.custom_snippet_manager.save_custom_template(template_name, template_data):
            QMessageBox.information(self.mw, "Template Saved", f"Template '{template_name}' saved successfully.")
            self.mw.ui_manager._load_and_display_templates()
        else:
            QMessageBox.critical(self.mw, "Error", "Failed to save the custom template.")

    @pyqtSlot()
    def on_manage_fsm_templates(self):
        QMessageBox.information(self.mw, "Manage Templates", "Template management (edit/delete) will be implemented here.\nFor now, please manually edit the 'custom_code_snippets.json' file in your app config directory.")

    @pyqtSlot()
    @pyqtSlot(bool)
    def on_new_file(self, silent=False):
        """Opens a dialog to create a new project. (Renamed from on_new_project for consistency)."""
        if self.mw.project_manager.is_project_open():
            QMessageBox.warning(self.mw, "Project Already Open", "Please close the current project before creating a new one.")
            return

        dialog = NewProjectDialog(self.mw)
        if dialog.exec_():
            project_name, project_dir, main_diagram = dialog.get_project_details()
            # The project file itself will be inside the new project directory
            project_path = os.path.join(project_dir, project_name, f"{project_name}{PROJECT_FILE_EXTENSION}")
        
            if not self.mw.project_manager.create_new_project(project_path, project_name, main_diagram):
                QMessageBox.critical(self.mw, "Project Creation Failed", "Could not create the project. Please check permissions and the log for details.")

    @pyqtSlot()
    def on_open_file(self):
        """Opens a file dialog to select and load a project file."""
        if self.mw.project_manager.is_project_open():
            QMessageBox.warning(self.mw, "Project Already Open", "Please close the current project before opening another.")
            return
        
        # Temporarily re-enable import plugins for the file dialog
        filters = [PROJECT_FILE_FILTER]
        if hasattr(self.mw, 'plugin_manager'):
            for plugin in self.mw.plugin_manager.importer_plugins:
                filters.append(plugin.file_filter)
        all_files_filter = "All Files (*)"
        if all_files_filter in filters:
            filters.remove(all_files_filter)
        filters.append(all_files_filter)
        file_filter_str = ";;".join(filters)

        start_dir = QDir.homePath()
        file_path, selected_filter = QFileDialog.getOpenFileName(self.mw, "Open Project or File", start_dir, file_filter_str)

        if not file_path:
            return

        if PROJECT_FILE_EXTENSION in selected_filter or file_path.endswith(PROJECT_FILE_EXTENSION):
            # It's a project file
            if not self.mw.project_manager.load_project(file_path):
                QMessageBox.critical(self.mw, "Project Load Failed", f"Could not load the project file:\n{file_path}")
        else:
            # It's a single diagram file or other import
            # For now, let's just open it without a project context
            editor = self.mw.find_editor_by_path(file_path)
            if editor:
                self.mw.tab_widget.setCurrentWidget(editor)
            else:
                self.mw._create_and_load_new_tab(file_path)

    # --- ADD THESE TWO NEW HELPER METHODS ---
    def _find_importer_by_extension(self, file_path):
        """Finds a suitable importer plugin by matching file extension."""
        if not hasattr(self.mw, 'plugin_manager'):
            return None
            
        file_ext = os.path.splitext(file_path)[1]
        if not file_ext:
            return None
        
        for plugin in self.mw.plugin_manager.importer_plugins:
            # Simple check if the file extension is present in the filter string
            if f"*{file_ext}" in plugin.file_filter:
                return plugin
        return None
    
    
    def _import_with_plugin(self, file_path, plugin):
        """Handles the logic of reading a file and using a plugin to import it."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            diagram_data = plugin.import_data(content)
            
            if diagram_data:
                new_editor = self.mw.add_new_editor_tab()
                new_editor.scene.load_diagram_data(diagram_data)
                new_editor.set_dirty(True) # Imported files are considered unsaved
                self.mw.log_message("INFO", f"Imported '{os.path.basename(file_path)}' using '{plugin.name}' plugin.")
            else:
                raise ValueError("Importer plugin returned no data or failed to parse.")
        except Exception as e:
            QMessageBox.critical(self.mw, "Import Error", f"Failed to import file with '{plugin.name}' plugin:\n{e}")
            logger.error(f"Error importing '{file_path}' with '{plugin.name}': {e}", exc_info=True)
    # --- END ADDITION ---

    # --- NEW METHOD: FIX FOR AttributeError ---
    @pyqtSlot(QModelIndex)
    def on_project_file_double_clicked(self, index: QModelIndex):
        """
        Handles the double-click event from the project tree view to open a file.
        """
        if not self.mw.project_fs_model:
            return

        file_path = self.mw.project_fs_model.filePath(index)
        
        # 1. Check if the clicked item is a file and has the correct extension
        if not self.mw.project_fs_model.isDir(index) and file_path.endswith(FILE_EXTENSION):
            
            # 2. Check if the file is already open in a tab
            editor = self.mw.find_editor_by_path(file_path)
            if editor:
                # If it's open, just switch to that tab
                self.mw.tab_widget.setCurrentWidget(editor)
                self.mw.log_message("INFO", f"Switched to already open file: {os.path.basename(file_path)}")
                return
            
            # 3. If not open, use the existing logic to open it in a new tab
            if os.path.exists(file_path):
                self.mw._create_and_load_new_tab(file_path)
            else:
                QMessageBox.warning(self.mw, "File Not Found", f"The file '{file_path}' could not be found.")
                self.remove_from_recent_files(file_path) # Clean up if it was a broken recent link
    # --- END NEW METHOD ---

    @pyqtSlot()
    def on_save_file(self) -> bool:
        editor = self.mw.current_editor()
        if not editor: return False

        if not editor.file_path:
            return self.on_save_file_as()
        
        if editor.is_dirty():
            if self.mw._save_editor_to_path(editor, editor.file_path):
                self.add_to_recent_files(editor.file_path)
                return True
            return False
        return True

    @pyqtSlot()
    def on_save_file_as(self) -> bool:
        editor = self.mw.current_editor()
        if not editor: return False

        default_filename = os.path.basename(editor.file_path or "untitled" + FILE_EXTENSION)
        start_dir = os.path.dirname(editor.file_path) if editor.file_path else QDir.homePath()

        file_path, _ = QFileDialog.getSaveFileName(self.mw, "Save BSM File As", os.path.join(start_dir, default_filename), FILE_FILTER)
        if file_path:
            if not file_path.lower().endswith(FILE_EXTENSION):
                file_path += FILE_EXTENSION
            
            other_editor = self.mw.find_editor_by_path(file_path)
            if other_editor and other_editor != editor:
                QMessageBox.warning(self.mw, "File In Use", f"The file '{os.path.basename(file_path)}' is already open in another tab. Please choose a different name.")
                return self.on_save_file_as()

            if self.mw._save_editor_to_path(editor, file_path):
                self.add_to_recent_files(file_path)
                return True
        return False
        
    @pyqtSlot()
    def on_export_simulink(self):
        editor = self.mw.current_editor()
        if not editor: return

        if not self.mw.matlab_connection.connected:
            QMessageBox.warning(self.mw, "MATLAB Not Connected", "Please configure MATLAB path in Settings first.")
            return
        if self.mw.current_editor().py_sim_active:
            QMessageBox.warning(self.mw, "Python Simulation Active", "Please stop the Python simulation before exporting to Simulink.")
            return

        dialog = QDialog(self.mw); dialog.setWindowTitle("Export to Simulink")
        dialog.setWindowIcon(get_standard_icon(QStyle.SP_ArrowUp, "->M")); layout = QFormLayout(dialog)
        layout.setSpacing(8); layout.setContentsMargins(10,10,10,10)
        base_name = os.path.splitext(os.path.basename(editor.file_path or "BSM_Model"))[0]
        default_model_name = "".join(c if c.isalnum() or c=='_' else '_' for c in base_name)
        if not default_model_name or not default_model_name[0].isalpha(): default_model_name = "Mdl_" + (default_model_name if default_model_name else "MyStateMachine")
        default_model_name = default_model_name.replace('-','_')
        name_edit = QLineEdit(default_model_name); layout.addRow("Simulink Model Name:", name_edit)
        default_output_dir = os.path.dirname(editor.file_path or QDir.homePath())
        output_dir_edit = QLineEdit(default_output_dir)
        browse_btn = QPushButton(get_standard_icon(QStyle.SP_DirOpenIcon,"Brw")," Browse..."); browse_btn.clicked.connect(lambda: output_dir_edit.setText(QFileDialog.getExistingDirectory(dialog, "Select Output Directory", output_dir_edit.text()) or output_dir_edit.text()))
        dir_layout = QHBoxLayout(); dir_layout.addWidget(output_dir_edit, 1); dir_layout.addWidget(browse_btn); layout.addRow("Output Directory:", dir_layout)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); btns.accepted.connect(dialog.accept); btns.rejected.connect(dialog.reject); layout.addRow(btns)
        dialog.setMinimumWidth(450)
        if dialog.exec() == QDialog.Accepted:
            model_name = name_edit.text().strip(); output_dir = output_dir_edit.text().strip()
            if not model_name or not output_dir: QMessageBox.warning(self.mw, "Input Error", "Model name and output directory are required."); return
            if not model_name[0].isalpha() or not all(c.isalnum() or c=='_' for c in model_name): QMessageBox.warning(self.mw, "Invalid Model Name", "Simulink model name must start with a letter and contain only alphanumeric characters or underscores."); return
            try: os.makedirs(output_dir, exist_ok=True)
            except OSError as e: QMessageBox.critical(self.mw, "Directory Error", f"Could not create output directory:\n{e}"); return
            diagram_data = editor.scene.get_diagram_data()
            if not diagram_data['states']: QMessageBox.information(self.mw, "Empty Diagram", "Cannot export an empty diagram (no states defined)."); return
            self.mw._start_matlab_operation(f"Exporting '{model_name}' to Simulink")
            self.mw.matlab_connection.generate_simulink_model(diagram_data['states'], diagram_data['transitions'], output_dir, model_name)

    @pyqtSlot()
    def on_export_arduino(self):
        """Handler for exporting a dedicated Arduino sketch."""
        editor = self.mw.current_editor()
        if not editor or not editor.scene.items():
            QMessageBox.information(self.mw, "Empty Diagram", "Cannot generate an Arduino sketch for an empty diagram.")
            return

        default_filename_base = "fsm_generated"
        if editor.file_path:
            default_filename_base = os.path.splitext(os.path.basename(editor.file_path))[0]
        
        # Arduino sketches are folders, so we ask for a directory and a base name.
        start_dir = os.path.dirname(editor.file_path) if editor.file_path else QDir.homePath()
        output_dir = QFileDialog.getExistingDirectory(self.mw, "Select Output Directory for Arduino Sketch", start_dir)
        
        if output_dir:
            sketch_name, ok = QInputDialog.getText(self.mw, "Arduino Sketch Name",
                                                   "Enter a name for the Arduino sketch (this will be the folder and .ino file name):",
                                                   QLineEdit.Normal, default_filename_base)
            if not (ok and sketch_name.strip()):
                return
            
            sketch_name = sketch_name.strip()
            if not sketch_name[0].isalpha() or not all(c.isalnum() or c == '_' for c in sketch_name):
                QMessageBox.warning(self.mw, "Invalid Sketch Name", "Arduino sketch name must start with a letter and contain only alphanumeric characters or underscores.")
                return
            
            # Create the sketch directory
            sketch_dir_path = os.path.join(output_dir, sketch_name)
            try:
                os.makedirs(sketch_dir_path, exist_ok=True)
            except OSError as e:
                QMessageBox.critical(self.mw, "Directory Creation Error", f"Could not create sketch directory:\n{e}")
                return

            diagram_data = editor.scene.get_diagram_data()
            try:
                # Generate the code with the specific Arduino platform target
                generate_c_code_files(
                    diagram_data, sketch_dir_path, sketch_name, 
                    target_platform="Arduino (.ino Sketch)"
                )
                QMessageBox.information(self.mw, "Arduino Sketch Generated", f"Arduino sketch '{sketch_name}' created successfully in:\n{sketch_dir_path}")
            except Exception as e:
                QMessageBox.critical(self.mw, "Arduino Code Generation Error", f"Failed to generate Arduino code: {e}")
                logger.error(f"Error generating Arduino sketch: {e}", exc_info=True)


    @pyqtSlot()
    def on_generate_c_code(self):
        editor = self.mw.current_editor()
        if not editor or not editor.scene.items():
            QMessageBox.information(self.mw, "Empty Diagram", "Cannot generate code for an empty diagram.")
            return

        default_filename_base = "fsm_generated"
        if editor.file_path:
            default_filename_base = os.path.splitext(os.path.basename(editor.file_path))[0]
        default_filename_base = "".join(c if c.isalnum() or c == '_' else '_' for c in default_filename_base)
        if not default_filename_base or not default_filename_base[0].isalpha():
            default_filename_base = "bsm_" + (default_filename_base if default_filename_base else "model")
        
        output_dir = QFileDialog.getExistingDirectory(self.mw, "Select Output Directory for C/C++ Code", os.path.dirname(editor.file_path or QDir.homePath()))
        
        if output_dir:
            dialog = QDialog(self.mw)
            dialog.setWindowTitle("Generate C/C++ Code")
            layout = QFormLayout(dialog)
            layout.setSpacing(10)

            filename_base_edit = QLineEdit(default_filename_base)
            layout.addRow("Base Filename:", filename_base_edit)

            platform_combo = QComboBox()
            from ..io.c_code_generator import PLATFORM_TEMPLATE_MAP
            platform_combo.addItems(list(PLATFORM_TEMPLATE_MAP.keys()))
            layout.addRow("Target Platform:", platform_combo)
            
            advanced_group = QGroupBox("Advanced Generation Options")
            advanced_group.setCheckable(True)
            advanced_group.setChecked(False)
            advanced_layout = QFormLayout(advanced_group)
            advanced_layout.setSpacing(8)

            impl_style_combo = QComboBox()
            impl_style_combo.addItems(["Switch-Case Statement", "State Table (Function Pointers)"])
            impl_style_combo.setToolTip("Switch-Case is highly readable. State Table can produce smaller code size.")
            advanced_layout.addRow("Implementation Style:", impl_style_combo)

            data_type_combo = QComboBox()
            data_type_combo.addItems(["int", "uint16_t", "uint8_t"])
            data_type_combo.setToolTip("Use smaller types like uint8_t to save SRAM on embedded targets.")
            advanced_layout.addRow("State/Event Type:", data_type_combo)
            
            include_comments_cb = QCheckBox("Include detailed comments and original action code")
            include_comments_cb.setChecked(True)
            advanced_layout.addRow(include_comments_cb)

            layout.addWidget(advanced_group)
            
            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addRow(button_box)

            if dialog.exec() == QDialog.Accepted:
                filename_base = filename_base_edit.text().strip()
                selected_platform = platform_combo.currentText()
                
                if not filename_base or not filename_base[0].isalpha():
                    QMessageBox.warning(self.mw, "Invalid Filename", "Base filename must start with a letter and contain only alphanumeric characters or underscores.")
                    return
                
                generation_options = {
                    "implementation_style": impl_style_combo.currentText() if advanced_group.isChecked() else "Switch-Case Statement",
                    "data_type": data_type_combo.currentText() if advanced_group.isChecked() else "int",
                    "include_comments": include_comments_cb.isChecked() if advanced_group.isChecked() else True,
                }
                    
                diagram_data = editor.scene.get_diagram_data()
                try:
                    logger.info(f"Generating C code for platform '{selected_platform}' with base name '{filename_base}' and options: {generation_options}")
                    c_file_path, h_file_path = generate_c_code_files(
                        diagram_data, output_dir, filename_base, 
                        target_platform=selected_platform,
                        generation_options=generation_options 
                    )
                    QMessageBox.information(self.mw, "C Code Generation Successful", f"Generated files for {selected_platform}:\n{c_file_path}\n{h_file_path}")
                    logger.info(f"C code generated successfully to {output_dir}")
                except Exception as e:
                    QMessageBox.critical(self.mw, "C Code Generation Error", f"Failed to generate C code: {e}")
                    logger.error(f"Error generating C code: {e}", exc_info=True)

    @pyqtSlot()
    def on_export_python_fsm(self):
        editor = self.mw.current_editor()
        if not editor or not editor.scene.items(): QMessageBox.information(self.mw, "Empty Diagram", "Cannot generate Python FSM for an empty diagram."); return
        
        default_classname_base = "MyFSM"
        if editor.file_path:
            base_name = os.path.splitext(os.path.basename(editor.file_path))[0]
            default_classname_base = "".join(word.capitalize() for word in base_name.replace('-', '_').split('_'))
        if not default_classname_base or not default_classname_base[0].isalpha():
            default_classname_base = "GeneratedFSM"

        output_dir = QFileDialog.getExistingDirectory(self.mw, "Select Output Directory for Python FSM", os.path.dirname(editor.file_path or QDir.homePath()))
        if output_dir:
            class_name, ok = QInputDialog.getText(self.mw, "FSM Class Name",
                                                  "Enter a name for the Python FSM class:",
                                                  QLineEdit.Normal, default_classname_base)
            if ok and class_name.strip():
                class_name = class_name.strip()
                if not class_name[0].isalpha() or not class_name.replace('_', '').isalnum():
                    QMessageBox.warning(self.mw, "Invalid Class Name", "Class name must start with a letter and contain only alphanumeric characters or underscores.")
                    return

                diagram_data = editor.scene.get_diagram_data()
                try:
                    py_file_path = generate_python_fsm_file(diagram_data, output_dir, class_name)
                    QMessageBox.information(self.mw, "Python FSM Generation Successful", f"Generated file:\n{py_file_path}")
                    logger.info(f"Python FSM generated successfully to {output_dir} with class name {class_name}")
                except Exception as e:
                    QMessageBox.critical(self.mw, "Python FSM Generation Error", f"Failed to generate Python FSM: {e}")
                    logger.error(f"Error generating Python FSM: {e}", exc_info=True)
            elif ok:
                QMessageBox.warning(self, "Invalid Class Name", "Class name cannot be empty.")

    @pyqtSlot()
    def on_export_plantuml(self):
        editor = self.mw.current_editor()
        if not editor or not editor.scene.items(): QMessageBox.information(self.mw, "Empty Diagram", "Cannot export an empty diagram."); return
        
        diagram_data = editor.scene.get_diagram_data()
        diagram_name = os.path.splitext(os.path.basename(editor.file_path or "FSM_Diagram"))[0]

        try:
            puml_text = generate_plantuml_text(diagram_data, diagram_name)
        except Exception as e:
            QMessageBox.critical(self.mw, "PlantUML Export Error", f"Failed to generate PlantUML text: {e}")
            logger.error(f"Error generating PlantUML text: {e}", exc_info=True)
            return

        default_filename = f"{diagram_name}.puml"
        start_dir = os.path.dirname(editor.file_path) if editor.file_path else QDir.homePath()
        file_path, _ = QFileDialog.getSaveFileName(self.mw, "Save PlantUML File",
                                                   os.path.join(start_dir, default_filename),
                                                   "PlantUML Files (*.puml *.plantuml);;Text Files (*.txt);;All Files (*)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(puml_text)
                QMessageBox.information(self.mw, "PlantUML Export Successful", f"Diagram exported to:\n{file_path}")
                logger.info(f"PlantUML diagram exported to {file_path}")
            except IOError as e:
                QMessageBox.critical(self.mw, "File Save Error", f"Could not save PlantUML file: {e}")
                logger.error(f"Error saving PlantUML file to {file_path}: {e}", exc_info=True)

    @pyqtSlot()
    def on_export_mermaid(self):
        editor = self.mw.current_editor()
        if not editor or not editor.scene.items(): QMessageBox.information(self.mw, "Empty Diagram", "Cannot export an empty diagram."); return
        
        diagram_data = editor.scene.get_diagram_data()
        diagram_name = os.path.splitext(os.path.basename(editor.file_path or "FSM_Diagram"))[0]

        try:
            mermaid_text = generate_mermaid_text(diagram_data, diagram_name)
        except Exception as e:
            QMessageBox.critical(self.mw, "Mermaid Export Error", f"Failed to generate Mermaid text: {e}")
            logger.error(f"Error generating Mermaid text: {e}", exc_info=True)
            return

        default_filename = f"{diagram_name}.md"
        start_dir = os.path.dirname(editor.file_path) if editor.file_path else QDir.homePath()
        file_path, _ = QFileDialog.getSaveFileName(self.mw, "Save Mermaid File",
                                                   os.path.join(start_dir, default_filename),
                                                   "Markdown Files (*.md);;Mermaid Files (*.mmd);;Text Files (*.txt);;All Files (*)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(mermaid_text)
                QMessageBox.information(self.mw, "Mermaid Export Successful", f"Diagram exported to:\n{file_path}")
                logger.info(f"Mermaid diagram exported to {file_path}")
            except IOError as e:
                QMessageBox.critical(self.mw, "File Save Error", f"Could not save Mermaid file: {e}")
                logger.error(f"Error saving Mermaid file to {file_path}: {e}", exc_info=True)


    @pyqtSlot()
    def on_export_vhdl(self):
        """Handler for exporting the FSM diagram to a VHDL file."""
        editor = self.mw.current_editor()
        if not editor or not editor.scene.items():
            QMessageBox.information(self.mw, "Empty Diagram", "Cannot generate VHDL for an empty diagram.")
            return

        default_entity_name = "fsm_generated"
        if editor.file_path:
            base_name = os.path.splitext(os.path.basename(editor.file_path))[0]
            default_entity_name = sanitize_vhdl_identifier(base_name)
        
        entity_name, ok = QInputDialog.getText(self.mw, "VHDL Entity Name",
                                               "Enter a name for the VHDL entity:",
                                               QLineEdit.Normal, default_entity_name)
        if not (ok and entity_name.strip()):
            return

        entity_name = entity_name.strip()
        
        default_filename = f"{sanitize_vhdl_identifier(entity_name)}.vhd"
        start_dir = os.path.dirname(editor.file_path) if editor.file_path else QDir.homePath()
        
        file_path, _ = QFileDialog.getSaveFileName(self.mw, "Save VHDL File",
                                                   os.path.join(start_dir, default_filename),
                                                   "VHDL Files (*.vhd *.vhdl);;All Files (*)")
        
        if not file_path:
            return

        diagram_data = editor.scene.get_diagram_data()
        try:
            vhdl_code = generate_vhdl_content(diagram_data, entity_name)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(vhdl_code)
            QMessageBox.information(self.mw, "VHDL Export Successful", f"VHDL code exported to:\n{file_path}")
            logger.info(f"VHDL code for entity '{entity_name}' exported to {file_path}")
        except Exception as e:
            QMessageBox.critical(self.mw, "VHDL Export Error", f"Failed to generate VHDL code: {e}")
            logger.error(f"Error generating VHDL code: {e}", exc_info=True)

    @pyqtSlot()
    def on_export_verilog(self):
        """Handler for exporting the FSM diagram to a Verilog file."""
        editor = self.mw.current_editor()
        if not editor or not editor.scene.items():
            QMessageBox.information(self.mw, "Empty Diagram", "Cannot generate Verilog for an empty diagram.")
            return

        default_module_name = "fsm_generated"
        if editor.file_path:
            base_name = os.path.splitext(os.path.basename(editor.file_path))[0]
            default_module_name = sanitize_vhdl_identifier(base_name) # Verilog sanitizer is similar enough for default
        
        module_name, ok = QInputDialog.getText(self.mw, "Verilog Module Name",
                                               "Enter a name for the Verilog module:",
                                               QLineEdit.Normal, default_module_name)
        if not (ok and module_name.strip()): return
        module_name = module_name.strip()
        
        default_filename = f"{sanitize_vhdl_identifier(module_name)}.v"
        start_dir = os.path.dirname(editor.file_path) if editor.file_path else QDir.homePath()
        
        file_path, _ = QFileDialog.getSaveFileName(self.mw, "Save Verilog File",
                                                   os.path.join(start_dir, default_filename),
                                                   "Verilog Files (*.v *.sv);;All Files (*)")
        
        if not file_path: return

        diagram_data = editor.scene.get_diagram_data()
        try:
            verilog_code = generate_verilog_content(diagram_data, module_name)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(verilog_code)
            QMessageBox.information(self.mw, "Verilog Export Successful", f"Verilog code exported to:\n{file_path}")
            logger.info(f"Verilog code for module '{module_name}' exported to {file_path}")
        except Exception as e:
            QMessageBox.critical(self.mw, "Verilog Export Error", f"Failed to generate Verilog code: {e}")
            logger.error(f"Error generating Verilog code: {e}", exc_info=True)

    @pyqtSlot()
    def on_export_png(self):
        editor = self.mw.current_editor()
        if not editor or not editor.scene.items(): QMessageBox.information(self.mw, "Empty Diagram", "Cannot export an empty diagram."); return
        
        diagram_name = os.path.splitext(os.path.basename(editor.file_path or "FSM_Diagram"))[0]
        default_filename = f"{diagram_name}.png"
        start_dir = os.path.dirname(editor.file_path) if editor.file_path else QDir.homePath()

        file_path, _ = QFileDialog.getSaveFileName(self.mw, "Save Diagram as PNG",
                                                   os.path.join(start_dir, default_filename),
                                                   "PNG Image (*.png);;All Files (*)")
        if file_path:
            try:
                rect = editor.scene.itemsBoundingRect()
                if rect.isEmpty():
                    QMessageBox.information(self.mw, "Empty Content", "No items to export.")
                    return

                padding = 20
                padded_rect = rect.adjusted(-padding, -padding, padding, padding)

                image_size = padded_rect.size().toSize()
                if image_size.width() < 1 or image_size.height() < 1:
                    image_size.setWidth(max(1, image_size.width()))
                    image_size.setHeight(max(1, image_size.height()))

                image = QImage(image_size, QImage.Format_ARGB32_Premultiplied)
                bg_brush = editor.scene.backgroundBrush()
                if bg_brush.style() == Qt.NoBrush:
                     image.fill(Qt.white)
                else:
                     image.fill(bg_brush.color())

                painter = QPainter(image)
                painter.setRenderHint(QPainter.Antialiasing)
                selected_items_backup = editor.scene.selectedItems()
                editor.scene.clearSelection()
                editor.scene.render(painter, QRectF(QPointF(0,0), QSizeF(image.size())), padded_rect)
                painter.end()

                for item in selected_items_backup:
                    item.setSelected(True)

                if image.save(file_path, "png"):
                    QMessageBox.information(self.mw, "PNG Export Successful", f"Diagram exported to:\n{file_path}")
                    logger.info(f"Diagram exported to PNG: {file_path}")
                else:
                    QMessageBox.critical(self.mw, "File Save Error", f"Could not save PNG image to:\n{file_path}")
                    logger.error(f"Error saving PNG to {file_path}")

            except Exception as e:
                QMessageBox.critical(self.mw, "PNG Export Error", f"Failed to export diagram to PNG: {e}")
                logger.error(f"Error exporting to PNG: {e}", exc_info=True)

    @pyqtSlot()
    def on_export_svg(self):
        editor = self.mw.current_editor()
        if not editor or not editor.scene.items(): QMessageBox.information(self.mw, "Empty Diagram", "Cannot export an empty diagram."); return
        
        diagram_name = os.path.splitext(os.path.basename(editor.file_path or "FSM_Diagram"))[0]
        default_filename = f"{diagram_name}.svg"
        start_dir = os.path.dirname(editor.file_path) if editor.file_path else QDir.homePath()

        file_path, _ = QFileDialog.getSaveFileName(self.mw, "Save Diagram as SVG",
                                                   os.path.join(start_dir, default_filename),
                                                   "SVG Image (*.svg);;All Files (*)")
        if file_path:
            try:
                rect = editor.scene.itemsBoundingRect()
                if rect.isEmpty():
                    QMessageBox.information(self.mw, "Empty Content", "No items to export.")
                    return

                padding = 20
                padded_rect = rect.adjusted(-padding, -padding, padding, padding)

                svg_generator = QSvgGenerator()
                svg_generator.setFileName(file_path)
                svg_generator.setSize(padded_rect.size().toSize())
                svg_generator.setViewBox(padded_rect)
                svg_generator.setTitle(diagram_name)
                svg_generator.setDescription(f"Generated by {self.mw.windowTitle()}")

                painter = QPainter(svg_generator)
                selected_items_backup = editor.scene.selectedItems()
                editor.scene.clearSelection()
                editor.scene.render(painter, source=padded_rect)

                for item in selected_items_backup:
                    item.setSelected(True)
                painter.end()

                QMessageBox.information(self.mw, "SVG Export Successful", f"Diagram exported to:\n{file_path}")
                logger.info(f"Diagram exported to SVG: {file_path}")

            except Exception as e:
                QMessageBox.critical(self.mw, "SVG Export Error", f"Failed to export diagram to SVG: {e}")
                logger.error(f"Error exporting to SVG: {e}", exc_info=True)


    @pyqtSlot()
    def on_select_all(self):
        editor = self.mw.current_editor()
        if editor: editor.scene.select_all()

    @pyqtSlot()
    def on_delete_selected(self):
        editor = self.mw.current_editor()
        if editor: editor.scene.delete_selected_items()
        
    @pyqtSlot(str, bool)
    def on_toggle_view_setting(self, key: str, checked: bool):
        if self.mw.settings_manager:
            self.mw.settings_manager.set(key, checked)
        else:
            logger.error(f"Cannot toggle view setting '{key}': SettingsManager not available.")

    @pyqtSlot()
    def on_zoom_to_selection(self):
        editor = self.mw.current_editor()
        if editor and hasattr(editor.view, 'zoom_to_selection'): editor.view.zoom_to_selection()

    @pyqtSlot()
    def on_fit_diagram_in_view(self):
        editor = self.mw.current_editor()
        if editor and hasattr(editor.view, 'fit_diagram_in_view'): editor.view.fit_diagram_in_view()
        
    @pyqtSlot(str)
    def on_align_items(self, mode: str):
        editor = self.mw.current_editor()
        if not editor:
            return

        scene = editor.scene
        selected_items = [item for item in scene.selectedItems() if isinstance(item, (GraphicsStateItem, GraphicsCommentItem))]
        if len(selected_items) < 2:
            return

        old_positions_map = {item: item.pos() for item in selected_items}
        moved_items_data_for_command = []

        overall_selection_rect = QRectF()
        first = True
        for item in selected_items:
            if first:
                overall_selection_rect = item.sceneBoundingRect()
                first = False
            else:
                overall_selection_rect = overall_selection_rect.united(item.sceneBoundingRect())

        if overall_selection_rect.isEmpty():
            return

        ref_pos = overall_selection_rect.center()
        for item in selected_items:
            item_rect = item.sceneBoundingRect()
            new_x, new_y = item.x(), item.y()

            if mode == "left":
                new_x = overall_selection_rect.left()
            elif mode == "center_h":
                new_x = ref_pos.x() - item_rect.width() / 2.0
            elif mode == "right":
                new_x = overall_selection_rect.right() - item_rect.width()
            elif mode == "top":
                new_y = overall_selection_rect.top()
            elif mode == "middle_v":
                new_y = ref_pos.y() - item_rect.height() / 2.0
            elif mode == "bottom":
                new_y = overall_selection_rect.bottom() - item_rect.height()

            item.setPos(new_x, new_y)

        for item in selected_items:
            new_pos = item.pos()
            old_pos = old_positions_map[item]
            if (new_pos - old_pos).manhattanLength() > 0.1:
                moved_items_data_for_command.append((item, old_pos, new_pos))
            if isinstance(item, GraphicsStateItem):
                scene._update_connected_transitions(item)
                
        if moved_items_data_for_command:
            cmd = MoveItemsCommand(moved_items_data_for_command, f"Align {mode.replace('_', ' ').title()}")
            editor.undo_stack.push(cmd)
            editor.set_dirty(True)

    @pyqtSlot(str)
    def on_distribute_items(self, mode: str):
        editor = self.mw.current_editor()
        if not editor:
            return

        scene = editor.scene
        selected_items = [item for item in scene.selectedItems() if isinstance(item, (GraphicsStateItem, GraphicsCommentItem))]
        if len(selected_items) < 3:
            return

        old_positions_map = {item: item.pos() for item in selected_items}
        moved_items_data_for_command = []

        if mode == "horizontal":
            selected_items.sort(key=lambda item: item.sceneBoundingRect().left())
            
            total_width_of_items = sum(item.sceneBoundingRect().width() for item in selected_items)
            span = selected_items[-1].sceneBoundingRect().right() - selected_items[0].sceneBoundingRect().left()
            
            if span - total_width_of_items < 0:
                spacing = 10
                logger.warning("Distribute Horizontal: Items wider than span, distributing with minimal spacing.")
            else:
                spacing = (span - total_width_of_items) / (len(selected_items) - 1)
            
            current_x = selected_items[0].pos().x()
            for i, item in enumerate(selected_items):
                item.setPos(current_x, old_positions_map[item].y())
                current_x += item.sceneBoundingRect().width() + spacing

        elif mode == "vertical":
            selected_items.sort(key=lambda item: item.sceneBoundingRect().top())

            total_height_of_items = sum(item.sceneBoundingRect().height() for item in selected_items)
            span = selected_items[-1].sceneBoundingRect().bottom() - selected_items[0].sceneBoundingRect().top()
            
            if span - total_height_of_items < 0:
                spacing = 10
                logger.warning("Distribute Vertical: Items taller than span, distributing with minimal spacing.")
            else:
                spacing = (span - total_height_of_items) / (len(selected_items) - 1)
                
            current_y = selected_items[0].pos().y()
            for item in selected_items:
                item.setPos(old_positions_map[item].x(), current_y)
                current_y += item.sceneBoundingRect().height() + spacing
        
        for item in selected_items:
            new_pos = item.pos()
            old_pos = old_positions_map[item]
            if (new_pos - old_pos).manhattanLength() > 0.1:
                moved_items_data_for_command.append((item, old_pos, new_pos))
            if isinstance(item, GraphicsStateItem):
                scene._update_connected_transitions(item)
                
        if moved_items_data_for_command:
            cmd_text = "Distribute Horizontally" if mode == "horizontal" else "Distribute Vertically"
            cmd = MoveItemsCommand(moved_items_data_for_command, cmd_text)
            editor.undo_stack.push(cmd)
            editor.set_dirty(True)
        
    @pyqtSlot()
    def on_show_find_item_dialog(self): 
        if self.mw.current_editor():
            self.mw.show_find_item_dialog_for_editor(self.mw.current_editor())

    def _open_example_file(self, filename: str):
        # --- FIX: Welcome Screen Integration and Robust Example Handling ---
        # If the current editor is the welcome screen, close it to make way for the example
        editor = self.mw.current_editor()
        if editor is None and self.mw.centralWidget() == self.mw.welcome_widget:
            # No action needed, a new tab will be created and replace the welcome screen.
            pass
        # If the current editor is an empty, unmodified "Untitled" tab, reuse it.
        elif editor and not editor.is_dirty() and not editor.file_path:
             # Silently close this tab, the new one will take its place.
             # This provides a cleaner experience than having "Untitled" linger.
             self.mw.tab_widget.removeTab(self.mw.tab_widget.indexOf(editor))
             editor.deleteLater()


        example_path = _get_bundled_file_path(filename, resource_prefix="examples")
        if example_path:
            base_name_check = f":/examples/{filename}" 
            for i in range(self.mw.tab_widget.count()):
                editor = self.mw.tab_widget.widget(i)
                if (editor.file_path and os.path.basename(editor.file_path) == filename) or \
                   editor.file_path == base_name_check:
                    self.mw.tab_widget.setCurrentIndex(i)
                    self.mw.log_message("INFO", f"Example '{filename}' is already open in a tab.")
                    return

            self.mw._create_and_load_new_tab(example_path)

        else: 
            QMessageBox.warning(self.mw, "Example File Not Found", f"The example file '{filename}' could not be found.")
            logger.warning("Example file '%s' not found.", filename)

    @pyqtSlot()
    def on_show_quick_start(self):
        guide_path = _get_bundled_file_path("QUICK_START.html", resource_prefix="docs")
        if guide_path:
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(guide_path)): QMessageBox.warning(self.mw, "Could Not Open Guide", f"Failed to open the Quick Start Guide.\nPath: {guide_path}"); logger.warning("Failed to open Quick Start Guide from: %s", guide_path)
        else: QMessageBox.information(self, "Guide Not Found", "The Quick Start Guide (QUICK_START.html) was not found.")

    @pyqtSlot()
    def on_about(self):
        from ..utils.config import APP_NAME, APP_VERSION, COLOR_ACCENT_PRIMARY, COLOR_TEXT_SECONDARY
        QMessageBox.about(self.mw, f"About {APP_NAME}",
                          f"""<h3 style='color:{COLOR_ACCENT_PRIMARY};'>{APP_NAME} v{APP_VERSION}</h3>
                             <p>A graphical tool for designing and simulating Brain State Machines.</p>
                             <ul>
                                 <li>Visual FSM design and editing.</li>
                                 <li>Internal Python-based FSM simulation.</li>
                                 <li>MATLAB/Simulink model generation and simulation control.</li>
                                 <li>AI Assistant for FSM generation and chat.</li>
                             </ul>
                             <p style='font-size:8pt;color:{COLOR_TEXT_SECONDARY};'>
                                 This software is intended for research and educational purposes.
                                 Always verify generated models and code.
                             </p>
                          """)