# fsm_designer_project/undo_commands.py

from PyQt5.QtWidgets import QUndoCommand, QGraphicsItem
from PyQt5.QtCore import QPointF
from PyQt5.QtCore import Qt
# Import at top level only what's needed for type hinting or base classes.
# Graphics items will be imported inside methods to break circular dependencies.
# from .graphics_items import ... (REMOVED FROM TOP LEVEL)

import logging

logger = logging.getLogger(__name__)

class AddItemCommand(QUndoCommand):
    """Adds a single graphics item to the scene."""
    def __init__(self, scene, item, description="Add Item"):
        super().__init__(description)
        # Import necessary classes inside the method
        from .graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem

        self.scene = scene
        self.item_data = item.get_data() # Capture all data needed for recreation
        self.item_type = item.type()

        # Store extra linkage info for transitions
        if isinstance(item, GraphicsTransitionItem):
            self.item_data['_start_name'] = item.start_item.text_label if item.start_item else None
            self.item_data['_end_name'] = item.end_item.text_label if item.end_item else None
        
        # We don't store the item instance itself anymore, to avoid reference issues.
        # We will recreate it from data, making the command more robust.
        
        # For logging/display
        display_name = "UnknownItem"
        if self.item_type == GraphicsStateItem.Type:
            display_name = self.item_data.get('name', "State")
        elif self.item_type == GraphicsTransitionItem.Type:
            display_name = f"Transition '{self.item_data.get('event', '...')}'"
        elif self.item_type == GraphicsCommentItem.Type:
            display_name = "Comment"
        logger.debug(f"AddItemCommand: Initialized for adding a {display_name}.")


    def redo(self):
        """Re-adds the item to the scene."""
        # Import here to avoid circular dependency
        from .graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem
        from .settings_manager import SettingsManager

        item_to_add = None
        settings = self.scene.parent_window.settings_manager if hasattr(self.scene, 'parent_window') and hasattr(self.scene.parent_window, 'settings_manager') else SettingsManager()

        if self.item_type == GraphicsStateItem.Type:
            props = self.item_data.copy()
            # We must map the string name of the style back to the Qt enum
            props['border_style_qt'] = SettingsManager.STRING_TO_QT_PEN_STYLE.get(props.get('border_style_str'), Qt.SolidLine)
            item_to_add = GraphicsStateItem(
                    props.get('x', 0),
                    props.get('y', 0),
                    props.get('width', 120),
                    props.get('height', 60),
                    props.get('name', ''),  # This is likely the text_label
                    props.get('is_initial', False),
                    props.get('is_final', False),
                    props.get('color', config.COLOR_ITEM_STATE_DEFAULT_BG),
                    props.get('entry_action', ''),
                    props.get('during_action', ''),
                    props.get('exit_action', ''),
                    props.get('description', ''),
                    props.get('is_superstate', False),
                    props.get('sub_fsm_data', {'states':[], 'transitions':[], 'comments':[]}),
                    action_language=props.get('action_language', config.DEFAULT_EXECUTION_ENV)
)
        elif self.item_type == GraphicsCommentItem.Type:
            item_to_add = GraphicsCommentItem(**self.item_data)
            item_to_add.setTextWidth(self.item_data.get('width', 150))
        elif self.item_type == GraphicsTransitionItem.Type:
            start_node = self.scene.get_state_by_name(self.item_data['_start_name'])
            end_node = self.scene.get_state_by_name(self.item_data['_end_name'])
            if start_node and end_node:
                props = self.item_data.copy()
                props.pop('_type', None); props.pop('_start_name', None); props.pop('_end_name', None)
                props['line_style_qt'] = SettingsManager.STRING_TO_QT_PEN_STYLE.get(props.get('line_style_str'), Qt.SolidLine)
                item_to_add = GraphicsTransitionItem(start_node, end_node, **props)
                item_to_add.set_control_point_offset(QPointF(self.item_data['control_offset_x'], self.item_data['control_offset_y']))
            else:
                logger.error(f"Redo Add Transition: Could not find source '{self.item_data['_start_name']}' or target '{self.item_data['_end_name']}' in scene.")
        
        if item_to_add:
            self.item_instance_ref = item_to_add # Keep a reference for undo
            self.scene.addItem(self.item_instance_ref)
            self.scene.clearSelection()
            self.item_instance_ref.setSelected(True)
            self.scene.set_dirty(True)
            self.scene.scene_content_changed_for_find.emit()
            self.scene.run_all_validations("AddItem_Redo")

    def undo(self):
        """Removes the item that was added."""
        if hasattr(self, 'item_instance_ref') and self.item_instance_ref.scene() == self.scene:
            self.scene.removeItem(self.item_instance_ref)
            self.scene.set_dirty(True)
            self.scene.scene_content_changed_for_find.emit()
            self.scene.run_all_validations("AddItem_Undo")


class RemoveItemsCommand(QUndoCommand):
    """Removes a list of graphics items from the scene."""
    def __init__(self, scene, items_to_remove, description="Remove Items"):
        super().__init__(description)
        from .graphics_items import GraphicsTransitionItem
        self.scene = scene
        self.removed_items_data = []
        for item in items_to_remove:
            item_data_entry = item.get_data()
            item_data_entry['_type'] = item.type()
            # Store linkage info for transitions before they are deleted
            if isinstance(item, GraphicsTransitionItem):
                item_data_entry['_start_name'] = item.start_item.text_label if item.start_item else None
                item_data_entry['_end_name'] = item.end_item.text_label if item.end_item else None
            self.removed_items_data.append(item_data_entry)
        
        self.item_instances_cache = list(items_to_remove) # Cache instances for redo

    def redo(self):
        """Performs the removal of the items."""
        for item in self.item_instances_cache:
            if item.scene() == self.scene:
                self.scene.removeItem(item)
        self.scene.set_dirty(True)
        self.scene.scene_content_changed_for_find.emit()
        self.scene.run_all_validations("RemoveItems_Redo")

    def undo(self):
        """Restores the removed items to the scene."""
        from .graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem
        from .settings_manager import SettingsManager

        # A two-pass approach is essential for restoring transitions correctly.
        # Pass 1: Restore all non-transition items (States, Comments) and cache them.
        restored_items_map = {} # Maps original item data to newly created instances
        states_map_for_undo = {}  # Maps original state name to new state item instance

        for item_data in self.removed_items_data:
            item_type = item_data['_type']
            if item_type != GraphicsTransitionItem.Type:
                item_to_add = None
                settings = self.scene.parent_window.settings_manager if hasattr(self.scene, 'parent_window') and hasattr(self.scene.parent_window, 'settings_manager') else SettingsManager()
                
                if item_type == GraphicsStateItem.Type:
                    props = item_data.copy()
                    props['border_style_qt'] = SettingsManager.STRING_TO_QT_PEN_STYLE.get(props.get('border_style_str'), Qt.SolidLine)
                    item_to_add = GraphicsStateItem(**props)
                    states_map_for_undo[item_data['name']] = item_to_add
                elif item_type == GraphicsCommentItem.Type:
                    item_to_add = GraphicsCommentItem(**item_data)
                    item_to_add.setTextWidth(item_data.get('width', 150))
                
                if item_to_add:
                    self.scene.addItem(item_to_add)
                    # Cache the new instance against its original data's id for consistency
                    restored_items_map[id(item_data)] = item_to_add
        
        # Pass 2: Restore transitions and link them to the newly created states.
        for item_data in self.removed_items_data:
            if item_data['_type'] == GraphicsTransitionItem.Type:
                start_node = states_map_for_undo.get(item_data['_start_name'])
                end_node = states_map_for_undo.get(item_data['_end_name'])

                if start_node and end_node:
                    props = item_data.copy()
                    # Remove special keys before passing to constructor
                    props.pop('_type', None); props.pop('_start_name', None); props.pop('_end_name', None)
                    props['line_style_qt'] = SettingsManager.STRING_TO_QT_PEN_STYLE.get(props.get('line_style_str'), Qt.SolidLine)
                    
                    trans_to_add = GraphicsTransitionItem(start_node, end_node, **props)
                    trans_to_add.set_control_point_offset(QPointF(item_data['control_offset_x'], item_data['control_offset_y']))
                    self.scene.addItem(trans_to_add)
                    restored_items_map[id(item_data)] = trans_to_add
                else:
                    logger.error(f"Undo Remove: Could not restore transition from '{item_data['_start_name']}' to '{item_data['_end_name']}' because one or both states were not found in the restoration cache.")
        
        # Re-establish the cache for the next 'redo' call
        self.item_instances_cache = list(restored_items_map.values())
        
        self.scene.set_dirty(True)
        self.scene.scene_content_changed_for_find.emit()
        self.scene.run_all_validations("RemoveItems_Undo")


class MoveItemsCommand(QUndoCommand):
    """Moves one or more graphics items."""
    def __init__(self, items_and_positions_info, description="Move Items"):
        super().__init__(description)
        self.items_and_positions_info = items_and_positions_info
        self.scene_ref = None
        if self.items_and_positions_info:
            # All items must be from the same scene
            self.scene_ref = self.items_and_positions_info[0][0].scene()

    def _apply_positions(self, use_new_positions: bool):
        from .graphics_items import GraphicsStateItem # Import locally

        if not self.scene_ref: return
        for item, old_pos, new_pos in self.items_and_positions_info:
            target_pos = new_pos if use_new_positions else old_pos
            if item.scene(): # Check if item is still in a scene
                item.setPos(target_pos)
                if isinstance(item, GraphicsStateItem):
                    # Use a guarded method call on the scene
                    if hasattr(self.scene_ref, '_update_connected_transitions'):
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
    """Edits the properties of a single graphics item."""
    def __init__(self, item, old_props_data, new_props_data, description="Edit Properties"):
        super().__init__(description)
        self.item = item
        self.old_props_data = old_props_data
        self.new_props_data = new_props_data
        self.scene_ref = item.scene()

    def _apply_properties(self, props_to_apply):
        # Local import to prevent circular dependencies
        from .graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem
        from .settings_manager import SettingsManager

        if not self.item or not self.scene_ref or not self.item.scene(): 
            logger.warning(f"EditItemPropertiesCommand: Cannot apply properties, item '{self.item}' is no longer in a scene.")
            return

        original_name = None
        if isinstance(self.item, GraphicsStateItem):
            original_name = self.item.text_label
            # The properties dialog may send string names for enums, which we need to convert back.
            props_to_apply['border_style_qt'] = SettingsManager.STRING_TO_QT_PEN_STYLE.get(props_to_apply.get('border_style_str'))
            self.item.set_properties(**props_to_apply)
            # Handle name changes, which affect transitions
            if original_name != props_to_apply.get('name') and hasattr(self.scene_ref, '_update_transitions_for_renamed_state'):
                self.scene_ref._update_transitions_for_renamed_state(original_name, props_to_apply['name'])
        
        elif isinstance(self.item, GraphicsTransitionItem):
            # The Transition set_properties is a bit different, it needs a QPointF for offset
            offset = QPointF(props_to_apply.get('control_offset_x', 0), props_to_apply.get('control_offset_y', 0))
            props_to_apply['offset'] = offset # Add the QPointF to the dict for unpacking
            props_to_apply['line_style_qt'] = SettingsManager.STRING_TO_QT_PEN_STYLE.get(props_to_apply.get('line_style_str'))
            self.item.set_properties(**props_to_apply)
        
        elif isinstance(self.item, GraphicsCommentItem):
            self.item.set_properties(**props_to_apply)
            self.item.setTextWidth(props_to_apply.get('width', 150)) # Ensure width is also set
        
        self.item.update()
        self.scene_ref.set_dirty(True)

    def redo(self):
        self._apply_properties(self.new_props_data)
        if self.scene_ref: 
            self.scene_ref.scene_content_changed_for_find.emit()
            self.scene_ref.run_all_validations("EditProperties_Redo")


    def undo(self):
        self._apply_properties(self.old_props_data)
        if self.scene_ref: 
            self.scene_ref.scene_content_changed_for_find.emit()
            self.scene_ref.run_all_validations("EditProperties_Undo")