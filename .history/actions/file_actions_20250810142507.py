# fsm_designer_project/actions/file_actions.py
import logging
import os
from PyQt6.QtCore import QObject, pyqtSlot, QDir
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QInputDialog, QLineEdit, QDialog
from ..utils.config import FILE_EXTENSION, FILE_FILTER, PROJECT_FILE_EXTENSION, PROJECT_FILE_FILTER
from ..plugins.api import BsmExporterPlugin

logger = logging.getLogger(__name__)

class FileActionHandler(QObject):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.mw = main_window

    @pyqtSlot()
    def on_new_file(self, silent=False):
        # Implementation remains here
        from ..ui.dialogs import NewProjectDialog
        # ... (full implementation from original action_handler) ...
        pass # Placeholder for brevity

    @pyqtSlot()
    def on_open_file(self):
        # Implementation remains here
        pass # Placeholder for brevity

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
    
    # ... other file-related actions like on_open_recent_file, add_to_recent_files, etc. ...
    # ... on_export_png, on_export_svg ...
    # ... on_export_vhdl, on_export_verilog ... (and other exports that are file-based)

    def add_to_recent_files(self, file_path):
        # Implementation remains here
        pass # Placeholder for brevity

    # (Add other methods from main ActionHandler that are purely about files)