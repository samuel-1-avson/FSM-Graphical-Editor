# fsm_designer_project/actions/edit_actions.py
import logging
import json
from PyQt6.QtCore import QObject, pyqtSlot, QPointF
# --- FIX: ADD THIS IMPORT ---
from PyQt6.QtWidgets import QMessageBox, QInputDialog, QStyle, QApplication
# --- END FIX ---
from ..ui.graphics.graphics_items import GraphicsStateItem, GraphicsCommentItem

logger = logging.getLogger(__name__)

class EditActionHandler(QObject):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.mw = main_window

    @pyqtSlot()
    def on_select_all(self):
        editor = self.mw.current_editor()
        if editor: editor.scene.select_all()

    @pyqtSlot()
    def on_delete_selected(self):
        editor = self.mw.current_editor()
        if editor: editor.scene.delete_selected_items()
        
    @pyqtSlot()
    def on_show_find_item_dialog(self):
        if self.mw.current_editor():
            self.mw.show_find_item_dialog_for_editor(self.mw.current_editor())
    
    # --- FIX: ADD THIS METHOD ---
    @pyqtSlot()
    def on_copy_log(self):
        """Copies the entire content of the log dock to the clipboard."""
        if hasattr(self.mw, 'log_output'):
            clipboard = QApplication.clipboard()
            clipboard.setText(self.mw.log_output.toPlainText())
            self.mw.log_message("INFO", "Log content copied to clipboard.")
    # --- END FIX ---

    @pyqtSlot()
    def on_manage_snippets(self):
        from ..ui.dialogs import SnippetManagerDialog
        
        if not self.mw.asset_manager:
            logger.error("Cannot open asset manager: AssetManager not initialized in MainWindow.")
            QMessageBox.critical(self.mw, "Error", "The Custom Asset Manager is not available.")
            return

        dialog = SnippetManagerDialog(self.mw.asset_manager, self.mw)
        dialog.exec()
        logger.info("Snippet Manager dialog closed.")

    @pyqtSlot()
    def on_save_selection_as_template(self):
        from ..ui.graphics.graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem
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
        if self.mw.asset_manager.template_exists(template_name):
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

        if self.mw.asset_manager.save_custom_template(template_name, template_data):
            QMessageBox.information(self.mw, "Template Saved", f"Template '{template_name}' saved successfully.")
            self.mw.ui_manager._load_and_display_templates()
        else:
            QMessageBox.critical(self.mw, "Error", "Failed to save the custom template.")