# fsm_designer_project/actions/file_actions.py
import logging
import os
import json
from PyQt6.QtCore import QObject, pyqtSlot, QDir, QUrl, QPoint
from PyQt6.QtGui import QDesktopServices, QImage, QPainter, QPixmap, QAction
from PyQt6.QtSvg import QSvgGenerator
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QInputDialog, QLineEdit, QDialog, QMenu, QStyle
from ..utils.config import FILE_EXTENSION, FILE_FILTER, PROJECT_FILE_EXTENSION, PROJECT_FILE_FILTER
from ..plugins.api import BsmExporterPlugin
from ..codegen import parse_plantuml, parse_mermaid
from ..ui.dialogs import ImportFromTextDialog
# --- FIX: ADD THIS IMPORT ---
from ..utils import _get_bundled_file_path
# --- END FIX ---


logger = logging.getLogger(__name__)

class FileActionHandler(QObject):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.mw = main_window

    @pyqtSlot()
    @pyqtSlot(bool)
    def on_new_file(self, silent=False):
        from ..ui.dialogs import NewProjectDialog

        if silent:
            self.mw.add_new_editor_tab()
            logger.info("New silent diagram tab created.")
            return

        if self.mw.project_manager.is_project_open():
            project_dir = os.path.dirname(self.mw.project_manager.current_project_path)
            i = 1
            while os.path.exists(os.path.join(project_dir, f"diagram_{i}.bsm")):
                i += 1
            default_name = f"diagram_{i}.bsm"

            file_name, ok = QInputDialog.getText(self.mw, "New Diagram File", "Enter file name:", text=default_name)
            if ok and file_name:
                if not file_name.lower().endswith(FILE_EXTENSION):
                    file_name += FILE_EXTENSION
                
                new_path = os.path.join(project_dir, file_name)
                if os.path.exists(new_path):
                    QMessageBox.warning(self.mw, "File Exists", "A file with that name already exists in this project.")
                    return

                try:
                    with open(new_path, 'w', encoding='utf-8') as f:
                        json.dump({"states": [], "transitions": [], "comments": []}, f, indent=4)
                    self.mw.log_message("INFO", f"Created new file: {new_path}")
                    self.mw._create_and_load_new_tab(new_path)
                except OSError as e:
                    QMessageBox.critical(self.mw, "Error", f"Could not create file: {e}")
            return

        dialog = NewProjectDialog(self.mw)
        if dialog.exec():
            project_name, project_dir, main_diagram = dialog.get_project_details()
            project_path = os.path.join(project_dir, project_name, f"{project_name}{PROJECT_FILE_EXTENSION}")
            
            if not self.mw.project_manager.create_new_project(project_path, project_name, main_diagram):
                QMessageBox.critical(self.mw, "Project Creation Failed", "Could not create the project. Please check permissions and the log for details.")

    @pyqtSlot()
    def on_open_file(self):
        if self.mw.project_manager.is_project_open():
            diagram_filters = [FILE_FILTER]
            if hasattr(self.mw, 'plugin_manager') and self.mw.plugin_manager.importer_plugins:
                importer_filters = [p.file_filter for p in self.mw.plugin_manager.importer_plugins]
                diagram_filters.extend(importer_filters)
        
            start_dir = os.path.dirname(self.mw.project_manager.current_project_path)
            file_path, _ = QFileDialog.getOpenFileName(self.mw, "Open Diagram or Import File", start_dir, ";;".join (diagram_filters))
        
            if not file_path:
                return

            importer_plugin = self._find_importer_by_extension(file_path)
            if importer_plugin:
                self._import_with_plugin(file_path, importer_plugin)
            elif file_path.endswith(FILE_EXTENSION):
                self.mw._create_and_load_new_tab(file_path)
            else:
                QMessageBox.warning(self.mw, "Unsupported File", f"No importer found for this file type within the current project:\n{file_path}")
            return

        start_dir = QDir.homePath()
        all_filters = [PROJECT_FILE_FILTER, FILE_FILTER]
        if hasattr(self.mw, 'plugin_manager') and self.mw.plugin_manager.importer_plugins:
            importer_filters = [p.file_filter for p in self.mw.plugin_manager.importer_plugins]
            all_filters.extend(importer_filters)
    
        file_paths, _ = QFileDialog.getOpenFileNames(self.mw, "Open Project or File(s)", start_dir, ";;".join(all_filters))
    
        if not file_paths:
            return

        project_files = [f for f in file_paths if f.endswith(PROJECT_FILE_EXTENSION)]
        if project_files:
            if len(project_files) > 1:
                QMessageBox.information(self.mw, "Multiple Projects Selected", "Please open only one project at a time.")
        
            if not self.mw.project_manager.load_project(project_files[0]):
                QMessageBox.critical(self.mw, "Project Load Failed", f"Could not load the project file:\n{project_files[0]}")
            return

        for file_path in file_paths:
            if self.mw.find_editor_by_path(file_path):
                self.mw.tab_widget.setCurrentWidget(self.mw.find_editor_by_path(file_path))
                continue

            importer_plugin = self._find_importer_by_extension(file_path)
            if importer_plugin:
                self._import_with_plugin(file_path, importer_plugin)
            elif file_path.endswith(FILE_EXTENSION):
                self.mw._create_and_load_new_tab(file_path)
            else:
                self.mw.log_message("WARNING", f"No handler found for file: {file_path}")

    @pyqtSlot()
    def on_close_project(self):
        """Closes the current project after ensuring all files are saved."""
        if not self.mw.project_manager.is_project_open():
            return

        # Iterate backwards to safely remove tabs
        for i in range(self.mw.tab_widget.count() - 1, -1, -1):
            editor = self.mw.tab_widget.widget(i)
            if not self.mw._prompt_save_on_close(editor):
                # User cancelled the save/close operation
                return

        # If we get here, all tabs were either saved or discarded
        self.mw.project_manager.close_project()

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
    def on_sync_from_scratchpad(self):
        """Parses the text from the scratchpad and updates the current diagram."""
        editor = self.mw.current_editor()
        if not editor:
            QMessageBox.warning(self.mw, "No Active Diagram", "Please open or create a diagram to sync to.")
            return

        text = self.mw.live_preview_editor.toPlainText()
        format_type = self.mw.live_preview_combo.currentText()
        if not text.strip():
            QMessageBox.information(self.mw, "Empty Scratchpad", "There is no text in the scratchpad to parse.")
            return

        reply = QMessageBox.question(self.mw, "Confirm Sync",
                                     f"This will replace the content of the current diagram with the parsed {format_type} text. Are you sure?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return

        try:
            if format_type == "PlantUML":
                new_data = parse_plantuml(text)
            elif format_type == "Mermaid":
                new_data = parse_mermaid(text)
            else:
                QMessageBox.critical(self, "Unsupported Format", f"Cannot sync from '{format_type}'.")
                return

            if new_data and (new_data.get('states') or new_data.get('transitions')):
                editor.scene.clear()
                editor.scene.load_diagram_data(new_data)
                editor.set_dirty(True)
                self.mw.action_handler.view_handler.on_fit_diagram_in_view()
                self.mw.log_message("INFO", f"Diagram synced from {format_type} scratchpad.")
            else:
                QMessageBox.warning(self, "Parsing Failed", f"Could not extract a valid FSM from the provided {format_type} text.")

        except Exception as e:
            QMessageBox.critical(self, "Parsing Error", f"Failed to parse the diagram text: {e}")
            logger.error(f"Error syncing FSM from text: {e}", exc_info=True)
            
    @pyqtSlot()
    def on_import_from_text(self):
        from ..ui.dialogs import ImportFromTextDialog
        dialog = ImportFromTextDialog(self.mw)
        if dialog.exec():
            diagram_data = dialog.get_diagram_data()
            if diagram_data:
                new_editor = self.mw.add_new_editor_tab()
                new_editor.scene.load_diagram_data(diagram_data)
                new_editor.set_dirty(True)
                self.mw.action_handler.view_handler.on_fit_diagram_in_view()

    @pyqtSlot()
    def on_save_log(self):
        """Saves the content of the log dock to a text file."""
        if not hasattr(self.mw, 'log_output'):
            return

        log_content = self.mw.log_output.toPlainText()
        if not log_content:
            QMessageBox.information(self.mw, "Empty Log", "There is no content in the log to save.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self.mw,
            "Save Log File",
            QDir.homePath(),
            "Log Files (*.log);;Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                self.mw.log_message("INFO", f"Log saved successfully to: {file_path}")
            except OSError as e:
                QMessageBox.critical(self.mw, "Save Error", f"Could not save log file:\n{e}")
                logger.error(f"Error saving log file to '{file_path}': {e}")
    
    @pyqtSlot(QPoint)
    def on_project_explorer_context_menu(self, point):
        """Shows a context menu for items in the project explorer."""
        if not (hasattr(self.mw, 'project_tree_view') and self.mw.project_tree_view):
            return
        
        index = self.mw.project_tree_view.indexAt(point)
        if not index.isValid():
            return
            
        file_path = self.mw.project_fs_model.filePath(index)
        
        menu = QMenu(self.mw)
        
        if os.path.isfile(file_path):
            if file_path.endswith(FILE_EXTENSION):
                open_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_DialogOpenButton), "Open", self.mw)
                open_action.triggered.connect(lambda: self.mw._create_and_load_new_tab(file_path))
                menu.addAction(open_action)

            rename_action = QAction("Rename...", self.mw)
            rename_action.triggered.connect(lambda: self._rename_project_file(file_path))
            menu.addAction(rename_action)
            
            delete_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_TrashIcon), "Delete", self.mw)
            delete_action.triggered.connect(lambda: self._delete_project_file(file_path))
            menu.addAction(delete_action)

        menu.addSeparator()
        
        reveal_action = QAction("Show in File Explorer", self.mw)
        reveal_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(file_path))))
        menu.addAction(reveal_action)
        
        menu.exec(self.mw.project_tree_view.viewport().mapToGlobal(point))

    def _rename_project_file(self, old_path):
        """Handles renaming a file from the project explorer."""
        old_name = os.path.basename(old_path)
        new_name, ok = QInputDialog.getText(self.mw, "Rename File", "Enter new name:", text=old_name)
        if ok and new_name and new_name != old_name:
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            if os.path.exists(new_path):
                QMessageBox.warning(self.mw, "File Exists", "A file with that name already exists.")
                return
            try:
                os.rename(old_path, new_path)
                # If the file is open, update its path
                editor = self.mw.find_editor_by_path(old_path)
                if editor:
                    editor.file_path = new_path
                    self.mw._update_window_title()
            except OSError as e:
                QMessageBox.critical(self.mw, "Rename Error", f"Could not rename file: {e}")

    def _delete_project_file(self, file_path):
        """Handles deleting a file from the project explorer."""
        file_name = os.path.basename(file_path)
        reply = QMessageBox.question(self.mw, "Delete File", f"Are you sure you want to permanently delete '{file_name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Check if the file is open and close it first
                editor = self.mw.find_editor_by_path(file_path)
                if editor:
                    index = self.mw.tab_widget.indexOf(editor)
                    if index != -1:
                        self.mw.tab_widget.removeTab(index)
                        editor.deleteLater()

                os.remove(file_path)
            except OSError as e:
                QMessageBox.critical(self.mw, "Delete Error", f"Could not delete file: {e}")

    # --- FIX: ADD THIS METHOD ---
    def _open_example_file(self, filename: str):
        """Opens a bundled example file."""
        if not self.mw._prompt_save_if_dirty():
            return

        full_path = _get_bundled_file_path(filename, resource_prefix="examples")
        if full_path and os.path.exists(full_path):
            self.mw._create_and_load_new_tab(full_path)
        else:
            QMessageBox.warning(self.mw, "Example Not Found", f"Could not locate the example file: {filename}")
    # --- END FIX ---


    @pyqtSlot()
    def on_export_png(self):
        # Implementation moved from UIManager
        pass # Placeholder for brevity

    @pyqtSlot()
    def on_export_svg(self):
        # Implementation moved from UIManager
        pass # Placeholder for brevity

    def add_to_recent_files(self, file_path):
        if not self.mw.settings_manager:
            return

        if not file_path or (not file_path.endswith(PROJECT_FILE_EXTENSION) and not file_path.endswith(FILE_EXTENSION)):
            return

        recent_files = self.mw.settings_manager.get("recent_files", [])
        normalized_path = os.path.normpath(file_path)
        recent_files = [p for p in recent_files if os.path.normpath(p) != normalized_path]
        recent_files.insert(0, normalized_path)
        del recent_files[10:]
        self.mw.settings_manager.set("recent_files", recent_files)
        self.mw._populate_recent_files_menu()

    def remove_from_recent_files(self, file_path):
        if not self.mw.settings_manager:
            return
        recent_files = self.mw.settings_manager.get("recent_files", [])
        if file_path in recent_files:
            recent_files.remove(file_path)
            self.mw.settings_manager.set("recent_files", recent_files)
            self.mw._populate_recent_files_menu()

    # (Add other file-related actions here as needed)