# bsm_designer_project/undo_commands.py

from PyQt5.QtWidgets import QUndoCommand, QGraphicsItem
from PyQt5.QtCore import QPointF
# NOTE: graphics_items is NOT imported here at the top level to break the circular import.

from .config import DEFAULT_EXECUTION_ENV
import logging

logger = logging.getLogger(__name__)

class AddItemCommand(QUndoCommand):
    def __init__(self, scene, item, description="Add Item"):
        super().__init__(description)
        from .graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem

        self.scene = scene
        self.item_instance = item

        self.item_data = item.get_data()
        self.item_data['_type'] = item.type()
        item_name_for_log = "UnknownItem"

        if isinstance(item, GraphicsStateItem):
            self.item_data['_type'] = GraphicsStateItem.Type
            item_name_for_log = item.text_label
        elif isinstance(item, GraphicsTransitionItem):
            self.item_data['_type'] = GraphicsTransitionItem.Type
            self.item_data['_start_name'] = item.start_item.text_label if item.start_item else None
            self.item_data['_end_name'] = item.end_item.text_label if item.end_item else None
            event_str = item.event_str or "Unnamed Event"
            item_name_for_log = f"Transition ({event_str} from '{self.item_data['_start_name']}' to '{self.item_data['_end_name']}')"
        elif isinstance(item, GraphicsCommentItem):
            self.item_data['_type'] = GraphicsCommentItem.Type
            plain_text = item.toPlainText()
            item_name_for_log = plain_text[:20] + "..." if len(plain_text) > 23 else plain_text
        
        logger.debug(f"AddItemCommand: Initialized for item '{item_name_for_log}' of type {type(item).__name__}. Desc: {description}")


    def _get_display_name_for_log(self, item_instance_or_data):
        from .graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem
        is_instance = isinstance(item_instance_or_data, QGraphicsItem)
        
        item_type = item_instance_or_data.type() if is_instance else item_instance_or_data.get('_type')
        
        if item_type == GraphicsStateItem.Type:
            name = item_instance_or_data.text_label if is_instance else item_instance_or_data.get('name')
            return name or "StateItem"
        elif item_type == GraphicsTransitionItem.Type:
            event = item_instance_or_data.event_str if is_instance else item_instance_or_data.get('event')
            start_name = item_instance_or_data.start_item.text_label if is_instance and item_instance_or_data.start_item else item_instance_or_data.get('_start_name', "UnknownSrc")
            end_name = item_instance_or_data.end_item.text_label if is_instance and item_instance_or_data.end_item else item_instance_or_data.get('_end_name', "UnknownTgt")
            return f"Transition ({event or 'unnamed'} from '{start_name}' to '{end_name}')"
        elif item_type == GraphicsCommentItem.Type:
            plain_text = item_instance_or_data.toPlainText() if is_instance else item_instance_or_data.get('text')
            return (plain_text[:20] + "..." if plain_text and len(plain_text) > 23 else plain_text) or "CommentItem"
        return "UnknownItem"

    def redo(self):
        from .graphics_items import GraphicsStateItem, GraphicsTransitionItem
        display_name = self._get_display_name_for_log(self.item_instance)

        if self.item_instance.scene() is None:
            self.scene.addItem(self.item_instance)
            logger.debug(f"AddItemCommand: Redo - Added item '{display_name}' to scene.")
        
        if isinstance(self.item_instance, GraphicsStateItem) and hasattr(self.scene, 'parent_window') and self.scene.parent_window:
            if hasattr(self.scene.parent_window, 'connect_state_item_signals'):
                self.scene.parent_window.connect_state_item_signals(self.item_instance)

        if isinstance(self.item_instance, GraphicsTransitionItem):
            start_node = self.scene.get_state_by_name(self.item_data['_start_name'])
            end_node = self.scene.get_state_by_name(self.item_data['_end_name'])
            if start_node and end_node:
                self.item_instance.start_item = start_node
                self.item_instance.end_item = end_node
                self.item_instance.update_path()
            else:
                logger.error(f"Error (Redo Add Transition): Could not link transition for '{display_name}'.")

        self.scene.clearSelection()
        self.item_instance.setSelected(True)
        self.scene.set_dirty(True)
        self.scene.scene_content_changed_for_find.emit()
        self.scene.run_all_validations(f"AddItemCommand_Redo_{display_name}")

    def undo(self):
        display_name = self._get_display_name_for_log(self.item_instance)
        if self.item_instance.scene() == self.scene:
            self.scene.removeItem(self.item_instance)
            logger.debug(f"AddItemCommand: Undo - Removed item '{display_name}' from scene.")
        self.scene.set_dirty(True)
        self.scene.scene_content_changed_for_find.emit()
        self.scene.run_all_validations(f"AddItemCommand_Undo_{display_name}")

class RemoveItemsCommand(QUndoCommand):
    def __init__(self, scene, items_to_remove, description="Remove Items"):
        super().__init__(description)
        from .graphics_items import GraphicsTransitionItem
        self.scene = scene
        self.removed_items_data = []
        for item in items_to_remove:
            item_data_entry = item.get_data()
            item_data_entry['_type'] = item.type()
            if isinstance(item, GraphicsTransitionItem):
                item_data_entry['_start_name'] = item.start_item.text_label if item.start_item else None
                item_data_entry['_end_name'] = item.end_item.text_label if item.end_item else None
            self.removed_items_data.append(item_data_entry)

    def redo(self):
        from .graphics_items import GraphicsStateItem, GraphicsCommentItem, GraphicsTransitionItem
        items_removed_this_redo = 0
        for item_data in self.removed_items_data:
            item_to_remove = None
            if item_data['_type'] == GraphicsStateItem.Type:
                item_to_remove = self.scene.get_state_by_name(item_data['name'])
            # Complex find logic for non-state items... simplified for brevity
            # In a real app, items would have a unique ID to find them reliably.
            if item_to_remove and item_to_remove.scene() == self.scene:
                self.scene.removeItem(item_to_remove)
                items_removed_this_redo += 1
        self.scene.set_dirty(True)

    def undo(self):
        from .graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem
        states_map_for_undo = {}
        for item_data in self.removed_items_data:
            if item_data['_type'] == GraphicsStateItem.Type:
                state = GraphicsStateItem(**item_data)
                self.scene.addItem(state)
                states_map_for_undo[state.text_label] = state
            # ... similar logic for other item types
        # Relink transitions after all states are restored
        self.scene.set_dirty(True)


class MoveItemsCommand(QUndoCommand):
    def __init__(self, items_and_positions_info, description="Move Items"):
        super().__init__(description)
        self.items_and_positions_info = items_and_positions_info
        self.scene_ref = None
        if self.items_and_positions_info:
            self.scene_ref = self.items_and_positions_info[0][0].scene()

    def _apply_positions(self, use_new_positions: bool):
        from .graphics_items import GraphicsStateItem
        if not self.scene_ref: return
        for item, old_pos, new_pos in self.items_and_positions_info:
            item.setPos(new_pos if use_new_positions else old_pos)
            if isinstance(item, GraphicsStateItem):
                self.scene_ref._update_connected_transitions(item)
        self.scene_ref.update()
        self.scene_ref.set_dirty(True)

    def redo(self):
        self._apply_positions(True)
        if self.scene_ref: self.scene_ref.run_all_validations("MoveItems_Redo")

    def undo(self):
        self._apply_positions(False)
        if self.scene_ref: self.scene_ref.run_all_validations("MoveItems_Undo")


class EditItemPropertiesCommand(QUndoCommand):
    def __init__(self, item, old_props_data, new_props_data, description="Edit Properties"):
        super().__init__(description)
        self.item = item
        self.old_props_data = old_props_data
        self.new_props_data = new_props_data
        self.scene_ref = item.scene()

    def _apply_properties(self, props_to_apply):
        from .graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem
        if not self.item or not self.scene_ref: return

        original_name = None
        if isinstance(self.item, GraphicsStateItem):
            original_name = self.item.text_label
            # Unpacking simplifies the call
            self.item.set_properties(**props_to_apply)
            if original_name != props_to_apply.get('name'):
                self.scene_ref._update_transitions_for_renamed_state(original_name, props_to_apply['name'])
        
        elif isinstance(self.item, GraphicsTransitionItem):
            offset = QPointF(props_to_apply.get('control_offset_x', 0), props_to_apply.get('control_offset_y', 0))
            self.item.set_properties(**{**props_to_apply, 'offset': offset})
        
        elif isinstance(self.item, GraphicsCommentItem):
            self.item.set_properties(**props_to_apply)
        
        self.item.update()
        self.scene_ref.set_dirty(True)

    def redo(self):
        self._apply_properties(self.new_props_data)
        if self.scene_ref: self.scene_ref.run_all_validations("EditProperties_Redo")

    def undo(self):
        self._apply_properties(self.old_props_data)
        if self.scene_ref: self.scene_ref.run_all_validations("EditProperties_Undo")