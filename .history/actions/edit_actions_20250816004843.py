# fsm_designer_project/actions/edit_actions.py
import logging
import json
from PyQt6.QtCore import QObject, pyqtSlot, QPointF
from PyQt6.QtWidgets import QMessageBox, QInputDialog, QStyle, QApplication

# --- MODIFIED: Import the signal bus ---
from ..managers.signal_bus import signal_bus

from ..ui.graphics.graphics_items import GraphicsStateItem, GraphicsCommentItem, GraphicsTransitionItem
from ..undo_commands import AddItemCommand, EditItemPropertiesCommand, RemoveItemsCommand
from ..utils import config

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
    
    @pyqtSlot()
    def on_copy_log(self):
        """Copies the entire content of the log dock to the clipboard."""
        if hasattr(self.mw, 'log_output'):
            clipboard = QApplication.clipboard()
            clipboard.setText(self.mw.log_output.toPlainText())
            self.mw.log_message("INFO", "Log content copied to clipboard.")

    @pyqtSlot(dict)
    def apply_ai_fix(self, fix_data: dict):
        """Applies a fix or action proposed by the AI to the current diagram."""
        editor = self.mw.current_editor()
        if not editor:
            QMessageBox.warning(self.mw, "No Active Diagram", "Cannot apply AI fix without an active diagram.")
            return

        action = fix_data.get("action")
        details = fix_data.get("details", {})
        scene = editor.scene
        undo_stack = editor.undo_stack

        try:
            if action == "add_state":
                name = details.get("name")
                if not name: raise ValueError("State name is missing.")
                
                unique_name = scene._generate_unique_state_name(name)
                if unique_name != name:
                    self.mw.log_message("INFO", f"AI proposed state name '{name}' already exists. Renamed to '{unique_name}'.")

                # Position the new state near the center of the current view
                pos = editor.view.mapToScene(editor.view.viewport().rect().center())
                
                new_state = GraphicsStateItem(
                    pos.x(), pos.y(), 120, 60, unique_name,
                    color=config.COLOR_ITEM_STATE_DEFAULT_BG
                )
                self.mw.connect_state_item_signals(new_state)
                cmd = AddItemCommand(scene, new_state, f"AI: Add State '{unique_name}'")
                undo_stack.push(cmd)

            elif action == "add_transition":
                src = scene.get_state_by_name(details.get("source"))
                tgt = scene.get_state_by_name(details.get("target"))
                if not src or not tgt: raise ValueError("Source or target state not found for transition.")
                
                new_trans = GraphicsTransitionItem(
                    src, tgt, event_str=details.get("event", "")
                )
                cmd = AddItemCommand(scene, new_trans, "AI: Add Transition")
                undo_stack.push(cmd)

            elif action == "rename_state":
                old_name = details.get("old_name")
                new_name = details.get("new_name")
                if not old_name or not new_name: raise ValueError("Old or new name missing for rename.")
                
                item_to_rename = scene.get_state_by_name(old_name)
                if not item_to_rename: raise ValueError(f"State '{old_name}' not found for renaming.")
                
                if scene.get_state_by_name(new_name):
                    raise ValueError(f"A state named '{new_name}' already exists.")

                old_props = item_to_rename.get_data()
                new_props = old_props.copy()
                new_props["name"] = new_name
                cmd = EditItemPropertiesCommand(item_to_rename, old_props, new_props, f"AI: Rename State '{old_name}'")
                undo_stack.push(cmd)
            
            elif action == "delete_item":
                name = details.get("name")
                if not name: raise ValueError("Item name missing for deletion.")
                
                item_to_delete = scene.get_state_by_name(name)
                if not item_to_delete: raise ValueError(f"Item '{name}' not found for deletion.")
                
                cmd = RemoveItemsCommand(scene, [item_to_delete], f"AI: Delete '{name}'")
                undo_stack.push(cmd)

            else:
                raise ValueError(f"Unknown AI action: '{action}'")

            self.mw.log_message("INFO", f"Successfully applied AI action: {action}")

        except (ValueError, KeyError) as e:
            QMessageBox.critical(self.mw, "AI Action Failed", f"Could not apply the proposed AI action:\n{e}")
            logger.error(f"Error applying AI fix '{action}': {e}", exc_info=True)

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
            
    # --- MODIFIED METHOD ---
    @pyqtSlot()
    def on_auto_layout_diagram(self):
        """Triggers the auto-layout functionality by emitting a signal."""
        editor = self.mw.current_editor()
        if not editor:
            return
            
        if not editor.scene.items():
            QMessageBox.information(self.mw, "Empty Diagram", "Cannot auto-layout an empty diagram.")
            return

        # REMOVED: Deferred import to prevent circular dependency issues
        # from ..ui.dialogs.tool_dialogs import AutoLayoutPreviewDialog
        
        try:
            # This calls the method on the DiagramScene to get the preview
            preview_pixmap = editor.scene.generate_auto_layout_preview()
            if not preview_pixmap:
                QMessageBox.warning(self.mw, "Layout Error", "Could not generate an auto-layout preview. Check logs for details.")
                return

            # --- REFACTORED LOGIC ---
            # Instead of creating the dialog here, we emit a signal.
            # The UIManager will be responsible for creating the dialog and handling its result.
            dialog_data = {"preview_pixmap": preview_pixmap}
            signal_bus.dialog_requested.emit("auto_layout_preview", dialog_data)
            # --- END REFACTORED LOGIC ---

        except Exception as e:
            QMessageBox.critical(self.mw, "Auto-Layout Error", f"An error occurred during auto-layout: {e}")
            logger.error("Auto-layout failed: %s", e, exc_info=True)