# fsm_designer_project/actions/file_actions.py
import logging
import os
import json
from PyQt6.QtCore import QObject, pyqtSlot, QDir, QUrl
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QInputDialog, QLineEdit, QDialog
from PyQt6.QtGui import QDesktopServices, QImage, QPainter, QPixmap
from PyQt6.QtSvg import QSvgGenerator
from ..utils.config import FILE_EXTENSION, FILE_FILTER, PROJECT_FILE_EXTENSION, PROJECT_FILE_FILTER
from ..plugins.api import BsmExporterPlugin
from ..codegen.c_code_generator import generate_c_code_content, sanitize_c_identifier
from ..codegen.hdl_code_generator import generate_vhdl_content, generate_verilog_content, sanitize_vhdl_identifier, sanitize_verilog_identifier
from ..codegen.python_code_generator import generate_python_fsm_file

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

            importer_plugin = self.mw.action_handler.file_handler._find_importer_by_extension(file_path)
            if importer_plugin:
                self.mw.action_handler.file_handler._import_with_plugin(file_path, importer_plugin)
            elif file_path.endswith(FILE_EXTENSION):
                self.mw._create_and_load_new_tab(file_path)
            else:
                QMessageBox.warning(self.mw, "Unsupported File", f"No importer found for this file type within the current  project:\n{file_path}")
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

            importer_plugin = self.mw.action_handler.file_handler._find_importer_by_extension(file_path)
            if importer_plugin:
                self.mw.action_handler.file_handler._import_with_plugin(file_path, importer_plugin)
            elif file_path.endswith(FILE_EXTENSION):
                self.mw._create_and_load_new_tab(file_path)
            else:
                self.mw.log_message("WARNING", f"No handler found for file: {file_path}")

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