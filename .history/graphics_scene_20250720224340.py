# fsm_designer_project/graphics_scene.py

import sys
import os
import json
import logging
import math
import re
import sip
from PyQt5.QtWidgets import (
    QGraphicsScene, QGraphicsView, QGraphicsItem, QGraphicsLineItem,
    QMenu, QMessageBox, QDialog, QStyle, QGraphicsSceneMouseEvent,
    QGraphicsSceneDragDropEvent, QApplication, QGraphicsSceneContextMenuEvent,QMainWindow,
    QGraphicsRectItem
)
from PyQt5.QtGui import QWheelEvent,QMouseEvent, QDrag, QDropEvent, QPixmap
from PyQt5.QtGui import QKeyEvent, QKeySequence, QCursor, QPainter, QColor, QPen, QBrush, QTransform
from PyQt5.QtCore import Qt, QRectF, QPointF, QLineF, pyqtSignal, QPoint, QMarginsF, QEvent, QMimeData, QTimer

from . import config

from .utils import get_standard_icon

from .config import (
    COLOR_ACCENT_PRIMARY,
    COLOR_ITEM_STATE_DEFAULT_BG, COLOR_ITEM_TRANSITION_DEFAULT, COLOR_ITEM_COMMENT_BG,
    DEFAULT_EXECUTION_ENV,
    MIME_TYPE_BSM_ITEMS,
    MIME_TYPE_BSM_TEMPLATE
)
from .graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem
from .undo_commands import AddItemCommand, MoveItemsCommand, RemoveItemsCommand, EditItemPropertiesCommand
from .snippet_manager import CustomSnippetManager
from .settings_manager import SettingsManager

logger = logging.getLogger(__name__)

SNAP_THRESHOLD_PIXELS = 8
GUIDELINE_PEN_WIDTH = 0.8



class DiagramScene(QGraphicsScene):
    item_moved = pyqtSignal(QGraphicsItem)
    modifiedStatusChanged = pyqtSignal(bool)
    scene_content_changed_for_find = pyqtSignal()
    validation_issues_updated = pyqtSignal(list)
    interaction_mode_changed = pyqtSignal(str)


    def __init__(self, undo_stack, parent_window=None, custom_snippet_manager: CustomSnippetManager | None = None, settings_manager: SettingsManager | None = None):
        super().__init__(parent_window)
        self.parent_window = parent_window
        
        self.custom_snippet_manager = custom_snippet_manager
        self.settings_manager = settings_manager if settings_manager is not None else SettingsManager()
        
        self.setSceneRect(0, 0, 6000, 4500)
        self.current_mode = "select"
        self.transition_start_item = None
        self.undo_stack = undo_stack
        self._dirty = False
        self._mouse_press_items_positions = {}
        self._temp_transition_line = None
        self.current_hovered_target_item: GraphicsStateItem | None = None
        self._is_alt_dragging_transition = False


        self.item_moved.connect(self._handle_item_moved_visual_update)

        self.grid_size = self.settings_manager.get("grid_size", 20)

        self.grid_pen_light = QPen(QColor(config.COLOR_GRID_MINOR), 0.7, Qt.DotLine)
        self.grid_pen_dark = QPen(QColor(config.COLOR_GRID_MAJOR), 0.9, Qt.SolidLine)
        self.setBackgroundBrush(QColor(config.COLOR_BACKGROUND_LIGHT))

        self.snap_to_grid_enabled = self.settings_manager.get("view_snap_to_grid")
        self.snap_to_objects_enabled = self.settings_manager.get("view_snap_to_objects")
        self._show_dynamic_snap_guidelines = self.settings_manager.get("view_show_snap_guidelines")
        self._guideline_pen = QPen(QColor(config.COLOR_SNAP_GUIDELINE), GUIDELINE_PEN_WIDTH, Qt.DashLine)


        self._horizontal_snap_lines: list[QLineF] = []
        self._vertical_snap_lines: list[QLineF] = []
        self._validation_issues = []
        self._problematic_items = set()
        
        self.validation_timer = QTimer(self)
        self.validation_timer.setSingleShot(True)
        self.validation_timer.setInterval(400) # 400ms delay after the last change
        self.validation_timer.timeout.connect(lambda: self.run_all_validations("LiveValidationTimer"))
        
        self.grid_pen_light.setColor(QColor(self.settings_manager.get("canvas_grid_minor_color")))
        self.grid_pen_dark.setColor(QColor(self.settings_manager.get("canvas_grid_major_color")))
        self._guideline_pen.setColor(QColor(self.settings_manager.get("canvas_snap_guideline_color")))
        self.setBackgroundBrush(QColor(config.COLOR_BACKGROUND_LIGHT))

    def _request_validation_update(self):
        """Starts the single-shot timer to run validation after a short delay."""
        if hasattr(self, 'validation_timer'):
            self.validation_timer.start()

    def drawBackground(self, painter: QPainter, rect: QRectF):
        painter.fillRect(rect, self.backgroundBrush())
        show_grid = self.settings_manager.get("view_show_grid")
        if not show_grid or self.grid_size < 5:
            return

        self.grid_pen_light.setColor(QColor(self.settings_manager.get("canvas_grid_minor_color")))
        self.grid_pen_dark.setColor(QColor(self.settings_manager.get("canvas_grid_major_color")))
        self._guideline_pen.setColor(QColor(self.settings_manager.get("canvas_snap_guideline_color")))
        self.setBackgroundBrush(QColor(config.COLOR_BACKGROUND_LIGHT))

        left = int(rect.left()) - (int(rect.left()) % self.grid_size)
        top = int(rect.top()) - (int(rect.top()) % self.grid_size)
        right = int(rect.right()) + self.grid_size
        bottom = int(rect.bottom()) + self.grid_size

        max_lines = 1000
        lines_light, lines_dark = [], []
        count = 0

        x = left
        while x <= right and count < max_lines:
            line = QLineF(x, rect.top(), x, rect.bottom())
            if x % (self.grid_size * 5) == 0: lines_dark.append(line)
            else: lines_light.append(line)
            x += self.grid_size
            count += 1

        y = top
        while y <= bottom and count < max_lines:
            line = QLineF(rect.left(), y, rect.right(), y)
            if y % (self.grid_size * 5) == 0: lines_dark.append(line)
            else: lines_light.append(line)
            y += self.grid_size
            count += 1

        if lines_light:
            painter.setPen(self.grid_pen_light)
            painter.drawLines(lines_light)
        if lines_dark:
            painter.setPen(self.grid_pen_dark)
            painter.drawLines(lines_dark)

        if self._show_dynamic_snap_guidelines and (self._horizontal_snap_lines or self._vertical_snap_lines):
            painter.setPen(self._guideline_pen)
            painter.drawLines(self._horizontal_snap_lines)
            painter.drawLines(self._vertical_snap_lines)
                
    def _log_to_parent(self, level, message):
        if self.parent_window and hasattr(self.parent_window, 'log_message'):
            self.parent_window.log_message(level, message)
        else:
            logger.log(getattr(logging, level.upper(), logging.INFO), f"(SceneDirect) {message}")

    def log_function(self, message: str, level: str = "ERROR"): 
        self._log_to_parent(level.upper(), message)

    def _update_connected_transitions(self, state_item: GraphicsStateItem):
        for item in self.items():
            if isinstance(item, GraphicsTransitionItem):
                if item.start_item == state_item or item.end_item == state_item:
                    item.update_path()

    def _update_transitions_for_renamed_state(self, old_name:str, new_name:str):
        self._log_to_parent("INFO", f"Scene notified: State '{old_name}' changed to '{new_name}'. Validating.")
        self._request_validation_update()
        self.scene_content_changed_for_find.emit()

    def get_state_by_name(self, name: str) -> GraphicsStateItem | None:
        for item in self.items():
            if isinstance(item, GraphicsStateItem) and item.text_label == name:
                return item
        return None

    def set_dirty(self, dirty=True):
        if self._dirty != dirty:
            self._dirty = dirty
            self.modifiedStatusChanged.emit(dirty)
        if self.parent_window and hasattr(self.parent_window, '_update_save_actions_enable_state'):
             self.parent_window._update_save_actions_enable_state()

    def is_dirty(self):
        return self._dirty

    def set_mode(self, mode: str):
        old_mode = self.current_mode
        if old_mode == mode: return
        
        if self.current_hovered_target_item:
            self.current_hovered_target_item.set_potential_transition_target_style(False)
            self.current_hovered_target_item = None

        self.current_mode = mode
        self.interaction_mode_changed.emit(mode)
        self._log_to_parent("INFO", f"Interaction mode changed to: {mode}")
        self.transition_start_item = None
        if self._temp_transition_line:
            self.removeItem(self._temp_transition_line)
            self._temp_transition_line = None
        
        self._is_alt_dragging_transition = False

        if self.views():
            main_view = self.views()[0]
            if hasattr(main_view, '_restore_cursor_to_scene_mode'):
                main_view._restore_cursor_to_scene_mode()

        for item in self.items():
            movable_flag = mode == "select"
            if isinstance(item, (GraphicsStateItem, GraphicsCommentItem)):
                item.setFlag(QGraphicsItem.ItemIsMovable, movable_flag)

        if self.parent_window and hasattr(self.parent_window, 'mode_action_group'):
            actions_map = {
                "select": getattr(self.parent_window, 'select_mode_action', None),
                "state": getattr(self.parent_window, 'add_state_mode_action', None),
                "transition": getattr(self.parent_window, 'add_transition_mode_action', None),
                "comment": getattr(self.parent_window, 'add_comment_mode_action', None)
            }
            action_to_check = actions_map.get(mode)
            if action_to_check and hasattr(action_to_check, 'isChecked') and not action_to_check.isChecked():
                action_to_check.setChecked(True)
        elif self.parent_window and hasattr(self.parent_window, 'sub_mode_action_group'): 
            actions_map_sub = {
                "select": getattr(self.parent_window, 'sub_select_action', None),
                "state": getattr(self.parent_window, 'sub_state_action', None), 
                "transition": getattr(self.parent_window, 'sub_transition_action', None),
                "comment": getattr(self.parent_window, 'sub_comment_action', None) 
            }
            action_to_check_sub = actions_map_sub.get(mode)
            if action_to_check_sub and hasattr(action_to_check_sub, 'isChecked') and not action_to_check_sub.isChecked():
                action_to_check_sub.setChecked(True)

    def select_all(self):
        for item in self.items():
            if item.flags() & QGraphicsItem.ItemIsSelectable:
                item.setSelected(True)

    def _handle_item_moved_visual_update(self, moved_item):
        if isinstance(moved_item, GraphicsStateItem):
            self._update_connected_transitions(moved_item)

    def _clear_dynamic_guidelines(self):
        if self._horizontal_snap_lines or self._vertical_snap_lines:
            self._horizontal_snap_lines.clear()
            self._vertical_snap_lines.clear()
            self.update()

    def _mark_item_as_problematic(self, item, problem_description="Validation Issue"):
        if hasattr(item, 'set_problematic_style'):
            item.set_problematic_style(True, problem_description)
            self._problematic_items.add(item)

    def _clear_all_visual_validation_warnings(self):
        for item in list(self._problematic_items):
            if hasattr(item, 'set_problematic_style'):
                item.set_problematic_style(False)
        self._problematic_items.clear()

    def run_all_validations(self, trigger_source="unknown_source"):
        logger.debug(f"Running all validations, triggered by: {trigger_source}")
        self._clear_all_visual_validation_warnings() 
        current_validation_issues = [] 

        states = [item for item in self.items() if isinstance(item, GraphicsStateItem)]
        transitions = [item for item in self.items() if isinstance(item, GraphicsTransitionItem)]

        if not states and transitions:
            issue_msg = "Diagram has transitions but no states defined."
            current_validation_issues.append((issue_msg, None))
            for t in transitions: self._mark_item_as_problematic(t, "Orphaned Transition")

        if not states:
            if not current_validation_issues: 
                 current_validation_issues.append(("Diagram is empty or has no states.", None))
            self._validation_issues = current_validation_issues 
            self.validation_issues_updated.emit(self._validation_issues)
            self.update()
            return

        initial_states = [s for s in states if s.is_initial]
        if not initial_states:
            current_validation_issues.append(("Missing Initial State: The diagram must have exactly one initial state.", None))
        elif len(initial_states) > 1:
            issue_msg = f"Multiple Initial States: Found {len(initial_states)} initial states ({', '.join([s.text_label for s in initial_states])}). Only one is allowed."
            current_validation_issues.append((issue_msg, None)) 
            for s_init in initial_states:
                self._mark_item_as_problematic(s_init, "Multiple Initials")

        for state in states:
            if state.is_final:
                outgoing_transitions = [t for t in transitions if t.start_item == state]
                if outgoing_transitions:
                    issue_msg = f"Invalid Transition from Final State: State '{state.text_label}' is final and cannot have outgoing transitions."
                    current_validation_issues.append((issue_msg, state))
                    self._mark_item_as_problematic(state, "Final State with Outgoing Transition")
                    for t_out in outgoing_transitions:
                        self._mark_item_as_problematic(t_out, "Transition From Final State")
        
        unreachable_states_set = set() 
        if initial_states and len(initial_states) == 1:
            start_node = initial_states[0]
            reachable_states_bfs = set()
            q = [start_node]
            visited_for_reachability = {start_node}

            while q:
                current = q.pop(0)
                reachable_states_bfs.add(current)
                for t in transitions:
                    if t.start_item == current and t.end_item and t.end_item not in visited_for_reachability:
                        q.append(t.end_item)
                        visited_for_reachability.add(t.end_item)
            
            for s_state in states:
                if s_state not in reachable_states_bfs:
                    unreachable_states_set.add(s_state)
                    issue_msg = f"Unreachable State: State '{s_state.text_label}' cannot be reached from the initial state ('{start_node.text_label}')."
                    current_validation_issues.append((issue_msg, s_state))
                    self._mark_item_as_problematic(s_state, "Unreachable")
        elif not initial_states: 
            for s_state in states:
                unreachable_states_set.add(s_state)
                issue_msg = f"Unreachable State (No Initial): State '{s_state.text_label}' considered unreachable as no initial state is defined."
                current_validation_issues.append((issue_msg, s_state))
                self._mark_item_as_problematic(s_state, "Unreachable (No Initial)")

        for state in states:
            if not state.is_final and state not in unreachable_states_set: 
                has_outgoing = any(t.start_item == state for t in transitions)
                if not has_outgoing:
                    is_superstate_with_content = False
                    if state.is_superstate and state.sub_fsm_data and state.sub_fsm_data.get('states'):
                        is_superstate_with_content = True 

                    if not is_superstate_with_content:
                        issue_msg = f"Dead-End State: Non-final state '{state.text_label}' has no outgoing transitions."
                        current_validation_issues.append((issue_msg, state))
                        self._mark_item_as_problematic(state, "Dead-End State")

        for t in transitions:
            if not t.start_item or not t.end_item:
                issue_msg = f"Invalid Transition: Transition '{t._compose_label_string()}' has a missing source or target."
                current_validation_issues.append((issue_msg, t))
                self._mark_item_as_problematic(t, "Invalid Source/Target")
            elif t.start_item not in states or t.end_item not in states: 
                issue_msg = f"Orphaned Transition: Transition '{t._compose_label_string()}' connects to non-existent states."
                current_validation_issues.append((issue_msg, t))
                self._mark_item_as_problematic(t, "Orphaned")

        self._validation_issues = current_validation_issues
        self.validation_issues_updated.emit(self._validation_issues)
        self.update() 

        if self._validation_issues:
            logger.info(f"Validation found {len(self._validation_issues)} issues (Trigger: {trigger_source}).")
        else:
            logger.info(f"Validation passed with no issues (Trigger: {trigger_source}).")

    def _get_state_at(self, pos: QPointF) -> GraphicsStateItem | None:
        """Helper to find the topmost GraphicsStateItem at a scene position, ignoring other item types."""
        items_under_cursor = self.items(pos)
        for item in items_under_cursor:
            if isinstance(item, GraphicsStateItem):
                return item
        return None

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        pos = event.scenePos()

        if event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            return

        # --- Refactored Mode-specific handling ---
        state_under_cursor = self._get_state_at(pos)

        # Transition creation (shortcut or dedicated mode)
        if (self.current_mode == "transition") or (event.modifiers() & Qt.AltModifier and state_under_cursor):
            if state_under_cursor:
                if event.modifiers() & Qt.AltModifier:
                    self._is_alt_dragging_transition = True
                self._handle_transition_click(state_under_cursor, pos)
            elif self.current_mode == "transition":
                # Clicked on empty space in transition mode
                self._cancel_transition_drawing()
            event.accept()
            return

        # Add State mode
        if self.current_mode == "state":
            grid_x = round(pos.x() / self.grid_size) * self.grid_size - 60
            grid_y = round(pos.y() / self.grid_size) * self.grid_size - 30
            self._add_item_interactive(QPointF(grid_x, grid_y), item_type="State")
            event.accept()
            return

        # Add Comment mode
        if self.current_mode == "comment":
            grid_x = round(pos.x() / self.grid_size) * self.grid_size
            grid_y = round(pos.y() / self.grid_size) * self.grid_size
            self._add_item_interactive(QPointF(grid_x, grid_y), item_type="Comment")
            event.accept()
            return

        # Default (Select) mode
        if self.current_mode == "select":
            items_at_pos = self.items(pos)
            top_item_at_pos = items_at_pos[0] if items_at_pos else None

            self._mouse_press_items_positions.clear()
            selected_items_list = self.selectedItems()

            # Handle clicking on an item to select it (if not already selected)
            if top_item_at_pos and top_item_at_pos.flags() & QGraphicsItem.ItemIsMovable and \
               not top_item_at_pos.isSelected() and not (event.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier)):
                self.clearSelection()
                top_item_at_pos.setSelected(True)
                selected_items_list = [top_item_at_pos]

            # Store positions of selected items for drag operation
            if not (isinstance(top_item_at_pos, GraphicsTransitionItem) and hasattr(top_item_at_pos, '_dragging_control_point') and top_item_at_pos._dragging_control_point):
                for item in selected_items_list:
                    if item.flags() & QGraphicsItem.ItemIsMovable:
                        self._mouse_press_items_positions[item] = item.pos()
            
            super().mousePressEvent(event)
            return

        # Fallback
        super().mousePressEvent(event)

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent):
        item = self.itemAt(event.scenePos(), self.views()[0].transform() if self.views() else QTransform())

        if item and isinstance(item, (GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem)):
            self._show_item_context_menu(item, event)
            event.accept()
        
        elif not item:
            self._show_scene_context_menu(event)
            event.accept()
        else:
            super().contextMenuEvent(event)
    
    def _show_item_context_menu(self, item: QGraphicsItem, event: QGraphicsSceneContextMenuEvent):
        
        menu = QMenu()
        if not isinstance(item, GraphicsTransitionItem):
             menu.addAction("Edit Name (F2)", item.start_inline_edit).setEnabled(hasattr(item, 'start_inline_edit'))
        menu.addAction(get_standard_icon(QStyle.SP_DialogApplyButton, "Edt"), "&Properties...", lambda: self.edit_item_properties(item))
        
        if self.parent_window and hasattr(self.parent_window, 'ai_chatbot_manager') and self.parent_window.ai_chatbot_manager.is_configured():
            explain_action = menu.addAction("Explain with AI...")
            explain_action.triggered.connect(lambda: self._explain_item_with_ai(item))
            
        menu.addSeparator()

        # --- NEW: Add breakpoint toggle ---
        if isinstance(item, GraphicsStateItem):
            if self.parent_window and self.parent_window.current_editor() and self.parent_window.current_editor().py_sim_active:
                bp_action = QAction("Toggle Breakpoint", menu, checkable=True)
                bp_action.setIcon(get_standard_icon(QStyle.SP_DialogYesButton, "BP"))
                if self.parent_window.current_editor().py_fsm_engine and item.text_label in self.parent_window.current_editor().py_fsm_engine.breakpoints['states']:
                     bp_action.setChecked(True)
                bp_action.triggered.connect(lambda checked: self.parent_window.on_toggle_state_breakpoint(item, checked))
                menu.addAction(bp_action)
            else:
                 menu.addAction("Toggle Breakpoint").setEnabled(False) # Show disabled if not in sim

        menu.addAction(get_standard_icon(QStyle.SP_TrashIcon, "Del"), "Delete", lambda: self.delete_selected_items())
        menu.exec_(event.screenPos())

    def _show_scene_context_menu(self, event):
        menu = QMenu()
        menu.addAction(get_standard_icon(QStyle.SP_FileDialogNewFolder, "St"), "Add State Here", lambda: self._add_item_interactive(event.scenePos(), "State"))
        menu.addAction(get_standard_icon(QStyle.SP_MessageBoxInformation, "Cm"), "Add Comment Here", lambda: self._add_item_interactive(event.scenePos(), "Comment"))
        
        if self.parent_window and hasattr(self.parent_window, 'ai_chatbot_manager') and self.parent_window.ai_chatbot_manager.is_configured():
            menu.addSeparator()
            menu.addAction(get_standard_icon(QStyle.SP_ArrowRight, "AIGen"), "Generate FSM from Description (AI)...", lambda: self.parent_window.ai_chat_ui_manager.on_ask_ai_to_generate_fsm())

        menu.exec_(event.screenPos())


    def _explain_item_with_ai(self, item):
        if not self.parent_window or not hasattr(self.parent_window, 'ai_chatbot_manager'):
            return
            
        item_data = item.get_data()
        item_type = ""
        if isinstance(item, GraphicsStateItem):
            item_type = "State"
            context_data = {
                "name": item_data.get("name"),
                "description": item_data.get("description"),
                "entry_action": item_data.get("entry_action"),
                "during_action": item_data.get("during_action"),
                "exit_action": item_data.get("exit_action"),
                "is_superstate": item_data.get("is_superstate"),
            }
        elif isinstance(item, GraphicsTransitionItem):
            item_type = "Transition"
            context_data = {
                "source": item_data.get("source"),
                "target": item_data.get("target"),
                "event": item_data.get("event"),
                "condition": item_data.get("condition"),
                "action": item_data.get("action"),
            }
        else:
            return 

        prompt = f"Please explain what this FSM {item_type} does based on its properties. Be concise and focus on its purpose within a state machine.\n\n```json\n{json.dumps(context_data, indent=2)}\n```"
        
        self.parent_window.ai_chat_ui_manager._append_to_chat_display("Diagram", f"Requesting explanation for {item_type}: '{item_data.get('name', item_data.get('event', '...'))}'")
        self.parent_window.ai_chatbot_manager.send_message(prompt)



    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        self._clear_dynamic_guidelines()

        if self.current_mode == "select" and event.buttons() & Qt.LeftButton and self._mouse_press_items_positions:
            if self.snap_to_objects_enabled and self._show_dynamic_snap_guidelines:
                dragged_items = list(self._mouse_press_items_positions.keys())
                if dragged_items:
                    primary_dragged_item = dragged_items[0]

                    original_item_press_pos = self._mouse_press_items_positions.get(primary_dragged_item)
                    original_mouse_press_scene_pos = event.buttonDownScenePos(Qt.LeftButton)
                    current_mouse_scene_pos = event.scenePos()
                    drag_vector = current_mouse_scene_pos - original_mouse_press_scene_pos

                    if original_item_press_pos is not None:
                        potential_item_origin = original_item_press_pos + drag_vector
                        potential_sbr = primary_dragged_item.boundingRect().translated(potential_item_origin)

                        snap_points_x = {
                            'left': potential_sbr.left(), 'center': potential_sbr.center().x(), 'right': potential_sbr.right()
                        }
                        snap_points_y = {
                            'top': potential_sbr.top(), 'center': potential_sbr.center().y(), 'bottom': potential_sbr.bottom()
                        }

                        visible_rect = self.views()[0].mapToScene(self.views()[0].viewport().rect()).boundingRect() if self.views() else self.sceneRect()

                        for other_item in self.items():
                            if other_item in dragged_items or not isinstance(other_item, (GraphicsStateItem, GraphicsCommentItem)):
                                continue
                            other_sbr = other_item.sceneBoundingRect()

                            other_align_x = [other_sbr.left(), other_sbr.center().x(), other_sbr.right()]
                            for drag_x in snap_points_x.values():
                                for static_x in other_align_x:
                                    if abs(drag_x - static_x) <= SNAP_THRESHOLD_PIXELS:
                                        line = QLineF(static_x, visible_rect.top(), static_x, visible_rect.bottom())
                                        if line not in self._vertical_snap_lines: self._vertical_snap_lines.append(line)
                                        break
                            other_align_y = [other_sbr.top(), other_sbr.center().y(), other_sbr.bottom()]
                            for drag_y in snap_points_y.values():
                                for static_y in other_align_y:
                                    if abs(drag_y - static_y) <= SNAP_THRESHOLD_PIXELS:
                                        line = QLineF(visible_rect.left(), static_y, visible_rect.right(), static_y)
                                        if line not in self._horizontal_snap_lines: self._horizontal_snap_lines.append(line)
                                        break
                        if self._horizontal_snap_lines or self._vertical_snap_lines:
                            self.update()

        elif (self.current_mode == "transition" or self._is_alt_dragging_transition) and self.transition_start_item:
            if self._temp_transition_line:
                center_start = self.transition_start_item.sceneBoundingRect().center()
                self._temp_transition_line.setLine(QLineF(center_start, event.scenePos()))

            new_hovered_target = self._get_state_at(event.scenePos())
            if new_hovered_target == self.transition_start_item:
                new_hovered_target = None  # Don't highlight self as target during drag
            
            if self.current_hovered_target_item != new_hovered_target:
                if self.current_hovered_target_item:
                    self.current_hovered_target_item.set_potential_transition_target_style(False)
                self.current_hovered_target_item = new_hovered_target
                if self.current_hovered_target_item:
                    self.current_hovered_target_item.set_potential_transition_target_style(True)


        super().mouseMoveEvent(event)


    def _calculate_object_snap_position(self, moving_item: QGraphicsItem, candidate_item_origin_pos: QPointF) -> QPointF:
        if not self.snap_to_objects_enabled:
            return candidate_item_origin_pos

        current_best_x = candidate_item_origin_pos.x()
        current_best_y = candidate_item_origin_pos.y()
        min_offset_x = SNAP_THRESHOLD_PIXELS + 1
        min_offset_y = SNAP_THRESHOLD_PIXELS + 1

        moving_item_br = moving_item.boundingRect()
        candidate_moving_sbr = moving_item_br.translated(candidate_item_origin_pos)

        moving_item_refs_x = {
            'left': candidate_moving_sbr.left(),
            'center': candidate_moving_sbr.center().x(),
            'right': candidate_moving_sbr.right()
        }
        moving_item_refs_y = {
            'top': candidate_moving_sbr.top(),
            'center': candidate_moving_sbr.center().y(),
            'bottom': candidate_moving_sbr.bottom()
        }

        for other_item in self.items():
            if other_item == moving_item or not isinstance(other_item, (GraphicsStateItem, GraphicsCommentItem)):
                continue

            other_sbr = other_item.sceneBoundingRect()

            other_item_snap_points_x = [other_sbr.left(), other_sbr.center().x(), other_sbr.right()]
            for moving_ref_name, moving_x_val in moving_item_refs_x.items():
                for other_x_val in other_item_snap_points_x:
                    diff_x = other_x_val - moving_x_val
                    if abs(diff_x) < min_offset_x:
                        min_offset_x = abs(diff_x)
                        current_best_x = candidate_item_origin_pos.x() + diff_x
                    elif abs(diff_x) == min_offset_x:
                        pass 

            other_item_snap_points_y = [other_sbr.top(), other_sbr.center().y(), other_sbr.bottom()]
            for moving_ref_name, moving_y_val in moving_item_refs_y.items():
                for other_y_val in other_item_snap_points_y:
                    diff_y = other_y_val - moving_y_val
                    if abs(diff_y) < min_offset_y:
                        min_offset_y = abs(diff_y)
                        current_best_y = candidate_item_origin_pos.y() + diff_y
                    elif abs(diff_y) == min_offset_y:
                        pass

        final_x = current_best_x if min_offset_x <= SNAP_THRESHOLD_PIXELS else candidate_item_origin_pos.x()
        final_y = current_best_y if min_offset_y <= SNAP_THRESHOLD_PIXELS else candidate_item_origin_pos.y()

        return QPointF(final_x, final_y)


    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        if self._is_alt_dragging_transition and self.transition_start_item and event.button() == Qt.LeftButton:
            target_item = self._get_state_at(event.scenePos())

            if target_item:
                # We have a valid start and end item, so finalize the transition
                self._handle_transition_click(target_item, event.scenePos())
            else:
                # Released on empty space, cancel the drag-transition
                self._cancel_transition_drawing()
            
            # Reset the flag regardless
            self._is_alt_dragging_transition = False
            event.accept()
            return
        
        if self.current_hovered_target_item:
            self.current_hovered_target_item.set_potential_transition_target_style(False)
            self.current_hovered_target_item = None
            
        super().mouseReleaseEvent(event) 
        if event.button() == Qt.LeftButton and self.current_mode == "select":
            if self._mouse_press_items_positions:
                moved_items_data_for_command = []

                for item, old_pos in self._mouse_press_items_positions.items():
                    current_item_pos_after_drag = item.pos()
                    final_snapped_pos = current_item_pos_after_drag

                    if self.snap_to_objects_enabled:
                        final_snapped_pos = self._calculate_object_snap_position(item, current_item_pos_after_drag)
                    if self.snap_to_grid_enabled:
                        grid_snapped_x = round(final_snapped_pos.x() / self.grid_size) * self.grid_size
                        grid_snapped_y = round(final_snapped_pos.y() / self.grid_size) * self.grid_size
                        final_snapped_pos = QPointF(grid_snapped_x, grid_snapped_y)

                    if (final_snapped_pos - old_pos).manhattanLength() > 0.1 :
                        item.setPos(final_snapped_pos) 
                        moved_items_data_for_command.append((item, old_pos, final_snapped_pos))
                    elif (current_item_pos_after_drag - old_pos).manhattanLength() > 0.1 and \
                         (final_snapped_pos - current_item_pos_after_drag).manhattanLength() < 0.1: 
                         moved_items_data_for_command.append((item, old_pos, current_item_pos_after_drag))


                if moved_items_data_for_command:
                    cmd = MoveItemsCommand(moved_items_data_for_command, "Move Items")
                    self.undo_stack.push(cmd)
                    self.set_dirty(True)
                    # self.run_all_validations("MoveItemsCommand_End")

                self._mouse_press_items_positions.clear()

        self._clear_dynamic_guidelines()

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent):
        items_at_pos = self.items(event.scenePos())
        item_to_edit = next((item for item in items_at_pos if isinstance(item, (GraphicsStateItem, GraphicsCommentItem, GraphicsTransitionItem))), None)

        if item_to_edit and hasattr(item_to_edit, '_is_editing_inline') and item_to_edit._is_editing_inline:
            event.accept()
            return

        if item_to_edit and isinstance(item_to_edit, (GraphicsStateItem, GraphicsCommentItem)):
            self.edit_item_properties(item_to_edit)
            event.accept()
            return
        elif item_to_edit and isinstance(item_to_edit, GraphicsTransitionItem):
            self.edit_item_properties(item_to_edit)
            event.accept()
            return

        super().mouseDoubleClickEvent(event)

    def _show_context_menu(self, item, global_pos): 
        menu = QMenu()
        edit_action = menu.addAction(get_standard_icon(QStyle.SP_DialogApplyButton, "Edt"), "Properties...")

        if isinstance(item, GraphicsStateItem) and item.is_superstate:
            pass

        delete_action = menu.addAction(get_standard_icon(QStyle.SP_TrashIcon, "Del"), "Delete")

        action = menu.exec_(global_pos)
        if action == edit_action:
            self.edit_item_properties(item)
        elif action == delete_action:
            if not item.isSelected():
                self.clearSelection()
                item.setSelected(True)
            self.delete_selected_items()

    def edit_item_properties(self, item):
        # --- FIX: Local import to break circular dependency ---
        from .dialogs import StatePropertiesDialog, TransitionPropertiesDialog, CommentPropertiesDialog

        dialog_executed_and_accepted = False
        new_props_from_dialog = None
        DialogType = None

        old_props = item.get_data() if hasattr(item, 'get_data') else {}
        if isinstance(item, GraphicsStateItem): DialogType = StatePropertiesDialog
        elif isinstance(item, GraphicsTransitionItem): DialogType = TransitionPropertiesDialog
        elif isinstance(item, GraphicsCommentItem): DialogType = CommentPropertiesDialog
        else: return

        dialog_parent = self.parent_window
        if not (self.parent_window and isinstance(self.parent_window, (QMainWindow, QDialog))):
            dialog_parent = self.views()[0] if self.views() else None

        if DialogType == StatePropertiesDialog:
            dialog = DialogType(self.settings_manager, self.custom_snippet_manager, parent=dialog_parent, current_properties=old_props, is_new_state=False, scene_ref=self)
        elif DialogType == TransitionPropertiesDialog:
            dialog = TransitionPropertiesDialog(self.custom_snippet_manager, parent=dialog_parent, current_properties=old_props)
        else: 
            dialog = DialogType(parent=dialog_parent, current_properties=old_props)


        if dialog.exec() == QDialog.Accepted:
            dialog_executed_and_accepted = True
            new_props_from_dialog = dialog.get_properties()

            if isinstance(item, GraphicsStateItem):
                current_new_name = new_props_from_dialog.get('name')
                existing_state_with_new_name = self.get_state_by_name(current_new_name)
                if current_new_name != old_props.get('name') and existing_state_with_new_name and existing_state_with_new_name != item:
                    QMessageBox.warning(dialog_parent, "Duplicate Name", f"A state with the name '{current_new_name}' already exists.")
                    return 

        if dialog_executed_and_accepted and new_props_from_dialog is not None:
            final_new_props = old_props.copy()
            final_new_props.update(new_props_from_dialog) 

            if final_new_props == old_props:
                self._log_to_parent("INFO", "Properties unchanged.")
                return

            cmd = EditItemPropertiesCommand(item, old_props, final_new_props, f"Edit {type(item).__name__} Properties")
            self.undo_stack.push(cmd) 

            item_name_for_log = final_new_props.get('name', final_new_props.get('event', final_new_props.get('text', 'Item')))
            self._log_to_parent("INFO", f"Properties updated for: {item_name_for_log}")
        
    def _add_item_interactive(self, pos: QPointF, item_type: str, name_prefix:str="Item", initial_data:dict=None):
        # --- FIX: Local import to break circular dependency ---
        from .dialogs import StatePropertiesDialog, CommentPropertiesDialog

        current_item = None
        initial_data = initial_data or {}
        is_initial_state_from_drag = initial_data.get('is_initial', False)
        is_final_state_from_drag = initial_data.get('is_final', False)

        dialog_parent = self.parent_window or (self.views()[0] if self.views() else None)

        if item_type == "State":
            i = 1
            base_name = name_prefix if name_prefix != "Item" else "State"
            while self.get_state_by_name(f"{base_name}{i}"):
                i += 1
            default_name = f"{base_name}{i}"

            initial_dialog_props = {
                'name': default_name,
                'is_initial': is_initial_state_from_drag,
                'is_final': is_final_state_from_drag,
                'color': initial_data.get('color', self.settings_manager.get("item_default_state_color")),
                'action_language': DEFAULT_EXECUTION_ENV,
                'entry_action':"", 'during_action':"", 'exit_action':"", 'description':"",
                'is_superstate': False, 'sub_fsm_data': {'states': [], 'transitions': [], 'comments': []},
                'shape_type': initial_data.get('shape_type', self.settings_manager.get("state_default_shape")),
                'font_family': initial_data.get('font_family', self.settings_manager.get("state_default_font_family")),
                'font_size': initial_data.get('font_size', self.settings_manager.get("state_default_font_size")),
                'font_bold': initial_data.get('font_bold', self.settings_manager.get("state_default_font_bold")),
                'font_italic': initial_data.get('font_italic', self.settings_manager.get("state_default_font_italic")),
                'border_style_str': initial_data.get('border_style_str', self.settings_manager.get("state_default_border_style_str")),
                'border_width': initial_data.get('border_width', self.settings_manager.get("state_default_border_width")),
                'icon_path': initial_data.get('icon_path', None)
            }
            props_dialog = StatePropertiesDialog(self.settings_manager, self.custom_snippet_manager, parent=dialog_parent, current_properties=initial_dialog_props, is_new_state=True, scene_ref=self)


            if props_dialog.exec() == QDialog.Accepted:
                final_props = props_dialog.get_properties()
                if self.get_state_by_name(final_props['name']) and final_props['name'] != default_name:
                    QMessageBox.warning(dialog_parent, "Duplicate Name", f"A state named '{final_props['name']}' already exists.")
                else:
                    current_item = GraphicsStateItem(
                        pos.x(), pos.y(), 120, 60, 
                        final_props['name'],
                        final_props['is_initial'], final_props['is_final'],
                        final_props.get('color'),
                        final_props.get('entry_action',""),
                        final_props.get('during_action',""),
                        final_props.get('exit_action',""),
                        final_props.get('description',""),
                        final_props.get('is_superstate', False),
                        final_props.get('sub_fsm_data', {'states':[], 'transitions':[], 'comments':[]}),
                        action_language=final_props.get('action_language', DEFAULT_EXECUTION_ENV),
                        shape_type=final_props.get('shape_type'),
                        font_family=final_props.get('font_family'),
                        font_size=final_props.get('font_size'),
                        font_bold=final_props.get('font_bold'),
                        font_italic=final_props.get('font_italic'),
                        border_style_qt=SettingsManager.STRING_TO_QT_PEN_STYLE.get(final_props.get('border_style_str', "Solid")),
                        custom_border_width=final_props.get('border_width'),
                        icon_path=final_props.get('icon_path')
                    )
                    if self.parent_window and hasattr(self.parent_window, 'connect_state_item_signals'):
                        self.parent_window.connect_state_item_signals(current_item)

            if self.current_mode == "state": 
                self.set_mode("select")
            if not current_item: return 

        elif item_type == "Comment":
            initial_text = initial_data.get('text', "Comment" if name_prefix == "Item" else name_prefix)
            initial_comment_props = {
                'text': initial_text,
                'font_family': initial_data.get('font_family', self.settings_manager.get("comment_default_font_family")),
                'font_size': initial_data.get('font_size', self.settings_manager.get("comment_default_font_size")),
                'font_italic': initial_data.get('font_italic', self.settings_manager.get("comment_default_font_italic"))
            }
            comment_props_dialog = CommentPropertiesDialog(dialog_parent, initial_comment_props)

            if comment_props_dialog.exec() == QDialog.Accepted:
                final_comment_props = comment_props_dialog.get_properties()
                if final_comment_props['text']: 
                     current_item = GraphicsCommentItem(
                         pos.x(), pos.y(), final_comment_props['text'],
                         font_family=final_comment_props.get('font_family'),
                         font_size=final_comment_props.get('font_size'),
                         font_italic=final_comment_props.get('font_italic')
                    )
                else: 
                    self.set_mode("select" if self.current_mode == "comment" else self.current_mode)
                    return
            else: 
                self.set_mode("select" if self.current_mode == "comment" else self.current_mode)
                return
        else:
            self._log_to_parent("WARNING", f"Unknown item type for addition: {item_type}")
            return

        if current_item:
            cmd = AddItemCommand(self, current_item, f"Add {item_type}")
            self.undo_stack.push(cmd) 
            log_name = getattr(current_item, 'text_label', None) or \
                       (getattr(current_item, 'toPlainText', lambda: "Item")() if isinstance(current_item, GraphicsCommentItem) else "Item")
            self._log_to_parent("INFO", f"Added {item_type}: {log_name} at ({pos.x():.0f},{pos.y():.0f})")
        
    def _cancel_transition_drawing(self):
        """Helper to reset all transition-drawing state variables."""
        if self.transition_start_item:
            self._log_to_parent("INFO", "Transition drawing cancelled.")
        
        if self.current_hovered_target_item:
            self.current_hovered_target_item.set_potential_transition_target_style(False)
            self.current_hovered_target_item = None
            
        if self._temp_transition_line:
            self.removeItem(self._temp_transition_line)
            self._temp_transition_line = None
            
        self.transition_start_item = None
        self._is_alt_dragging_transition = False
        self.set_mode("select")
        
    def _handle_transition_click(self, clicked_state_item: GraphicsStateItem, click_pos: QPointF):
        """Handles both start and end clicks for transition creation."""
        # This is the FIRST click, setting the source state
        if not self.transition_start_item:
            self.transition_start_item = clicked_state_item
            if not self._temp_transition_line:
                self._temp_transition_line = QGraphicsLineItem()
                pen = QPen(QColor(config.COLOR_ACCENT_PRIMARY), 1.8, Qt.DashLine)
                self._temp_transition_line.setPen(pen)
                self.addItem(self._temp_transition_line)
            
            center_start = self.transition_start_item.sceneBoundingRect().center()
            self._temp_transition_line.setLine(QLineF(center_start, click_pos))
            self._log_to_parent("INFO", f"Transition started from: {clicked_state_item.text_label}. Click target state.")
            
            # Highlight potential target under mouse immediately
            item_under_mouse = self._get_state_at(click_pos)
            if item_under_mouse and item_under_mouse != self.transition_start_item:
                self.current_hovered_target_item = item_under_mouse
                self.current_hovered_target_item.set_potential_transition_target_style(True)

        # This is the SECOND click, setting the target state and creating the transition
        else:
            target_item = clicked_state_item
            
            # --- FIX: Create transition INSTANTLY with default properties ---
            new_transition = GraphicsTransitionItem(
                self.transition_start_item, target_item
            )
            # Use default properties from settings
            new_transition.set_properties(
                color_hex=self.settings_manager.get("item_default_transition_color"),
                line_style_str_prop=self.settings_manager.get("transition_default_line_style_str"),
                line_width_prop=self.settings_manager.get("transition_default_line_width"),
                arrowhead_style_prop=self.settings_manager.get("transition_default_arrowhead_style"),
                label_font_family_prop=self.settings_manager.get("transition_default_font_family"),
                label_font_size_prop=self.settings_manager.get("transition_default_font_size")
            )

            cmd = AddItemCommand(self, new_transition, "Add Transition")
            self.undo_stack.push(cmd)
            self._log_to_parent("INFO", f"Added transition: {self.transition_start_item.text_label} -> {target_item.text_label}")
            
            # --- Finalize and reset state ---
            self._cancel_transition_drawing()
            self.set_mode("select")
            
            # Select the new transition for immediate editing in properties dock
            QTimer.singleShot(0, lambda: new_transition.setSelected(True))


    def keyPressEvent(self, event: QKeyEvent):
        if event.matches(QKeySequence.Copy):
            self.copy_selected_items()
            event.accept()
            return
        elif event.matches(QKeySequence.Paste):
            self.paste_items_from_clipboard()
            event.accept()
            return

        if event.key() == Qt.Key_F2:
            selected = self.selectedItems()
            if len(selected) == 1 and isinstance(selected[0], (GraphicsStateItem, GraphicsCommentItem)) \
               and selected[0].flags() & QGraphicsItem.ItemIsFocusable:
                if hasattr(selected[0], 'start_inline_edit') and not getattr(selected[0], '_is_editing_inline', False):
                    selected[0].start_inline_edit()
                    event.accept()
                    return

        if event.key() == Qt.Key_Delete or (event.key() == Qt.Key_Backspace and sys.platform != 'darwin'):
            if self.selectedItems():
                self.delete_selected_items()
                event.accept()
                return
        elif event.key() == Qt.Key_Escape:
            if self.current_hovered_target_item: # Clear hover highlight on Escape
                self.current_hovered_target_item.set_potential_transition_target_style(False)
                self.current_hovered_target_item = None

            active_editor_item = None
            for item in self.items(): 
                if hasattr(item, '_is_editing_inline') and item._is_editing_inline and \
                   hasattr(item, '_inline_editor_proxy') and item._inline_editor_proxy:
                    active_editor_item = item
                    break

            if active_editor_item: 
                editor_widget = active_editor_item._inline_editor_proxy.widget()
                if editor_widget:
                    active_editor_item._inline_edit_aborted = True
                    editor_widget.clearFocus() 
                event.accept()
                return

            if self.current_mode == "transition" and self.transition_start_item:
                self.transition_start_item = None 
                if self._temp_transition_line:
                    self.removeItem(self._temp_transition_line)
                    self._temp_transition_line = None
                self._log_to_parent("INFO", "Transition drawing cancelled by Escape.")
                self.set_mode("select") 
                event.accept()
                return
            elif self.current_mode != "select": 
                self.set_mode("select")
                event.accept()
                return
            else: 
                self.clearSelection()
                event.accept()
                return

        super().keyPressEvent(event)


    def delete_selected_items(self):
        selected = self.selectedItems()
        if not selected: return

        items_to_delete_with_related = set()
        for item in selected:
            items_to_delete_with_related.add(item)
            if isinstance(item, GraphicsStateItem): 
                for scene_item in self.items():
                    if isinstance(scene_item, GraphicsTransitionItem):
                        if scene_item.start_item == item or scene_item.end_item == item:
                            items_to_delete_with_related.add(scene_item)

        if items_to_delete_with_related:
            cmd = RemoveItemsCommand(self, list(items_to_delete_with_related), "Delete Items")
            self.undo_stack.push(cmd)
        
    def dragEnterEvent(self, event: QGraphicsSceneDragDropEvent):
        if event.mimeData().hasFormat("application/x-bsm-tool") or \
           event.mimeData().hasFormat(MIME_TYPE_BSM_TEMPLATE):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QGraphicsSceneDragDropEvent):
        if event.mimeData().hasFormat("application/x-bsm-tool") or \
           event.mimeData().hasFormat(MIME_TYPE_BSM_TEMPLATE):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QGraphicsSceneDragDropEvent):
        pos = event.scenePos()
        mime_data = event.mimeData()

        if mime_data.hasFormat(MIME_TYPE_BSM_TEMPLATE):
            template_json_str = mime_data.data(MIME_TYPE_BSM_TEMPLATE).data().decode('utf-8')
            try:
                template_data = json.loads(template_json_str)
                self._add_template_to_scene(template_data, pos)
                event.acceptProposedAction()
            except json.JSONDecodeError as e:
                self._log_to_parent("ERROR", f"Error parsing dropped FSM template: {e}")
                event.ignore()
            return

        elif mime_data.hasFormat("application/x-bsm-tool"):
            item_type_data_str = mime_data.text() 

            grid_x = round(pos.x() / self.grid_size) * self.grid_size
            grid_y = round(pos.y() / self.grid_size) * self.grid_size

            if "State" in item_type_data_str: 
                grid_x -= 60 
                grid_y -= 30 

            initial_props_for_add = {}
            actual_item_type_to_add = "Item" 
            name_prefix_for_add = "Item"

            if item_type_data_str == "State":
                actual_item_type_to_add = "State"; name_prefix_for_add = "State"
            elif item_type_data_str == "Initial State":
                actual_item_type_to_add = "State"; name_prefix_for_add = "Initial"; initial_props_for_add['is_initial'] = True
            elif item_type_data_str == "Final State":
                actual_item_type_to_add = "State"; name_prefix_for_add = "Final"; initial_props_for_add['is_final'] = True
            elif item_type_data_str == "Comment":
                actual_item_type_to_add = "Comment"; name_prefix_for_add = "Note"
            else:
                self._log_to_parent("WARNING", f"Unknown item type dropped: {item_type_data_str}")
                event.ignore(); return

            self._add_item_interactive(QPointF(grid_x, grid_y),
                                       item_type=actual_item_type_to_add,
                                       name_prefix=name_prefix_for_add,
                                       initial_data=initial_props_for_add)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def get_diagram_data(self):
        data = {'states': [], 'transitions': [], 'comments': []}
        for item in self.items():
            if isinstance(item, GraphicsStateItem):
                data['states'].append(item.get_data())
            elif isinstance(item, GraphicsTransitionItem):
                if item.start_item and item.end_item: 
                    data['transitions'].append(item.get_data())
                else:
                    self._log_to_parent("WARNING", f"Skipping save of orphaned/invalid transition: '{item._compose_label_string()}'.")
            elif isinstance(item, GraphicsCommentItem):
                data['comments'].append(item.get_data())
        return data

    def load_diagram_data(self, data):
        self.clear() 
        self._problematic_items.clear() 
        self._validation_issues = []
        self.set_dirty(False) 
        state_items_map = {}

        states_data = data.get('states', [])

        # --- FIX: AUTO-LAYOUT FOR POSITION-LESS DATA ---
        if states_data and not any('x' in s and 'y' in s for s in states_data if isinstance(s, dict)):
            logger.info("No positional data found in states; applying simple auto-layout for editor.")
            GRID_ITEMS_PER_ROW = 3
            SPACING_X = 180
            SPACING_Y = 120
            for i, state_data_item in enumerate(states_data):
                if isinstance(state_data_item, dict):
                    row = i // GRID_ITEMS_PER_ROW
                    col = i % GRID_ITEMS_PER_ROW
                    state_data_item['x'] = col * SPACING_X
                    state_data_item['y'] = row * SPACING_Y
        # --- END FIX ---

        for state_data in states_data:
            state_item = GraphicsStateItem(
                state_data['x'], state_data['y'],
                state_data.get('width', 120), state_data.get('height', 60),
                state_data['name'],
                state_data.get('is_initial', False), state_data.get('is_final', False),
                state_data.get('color', config.COLOR_ITEM_STATE_DEFAULT_BG), 
                state_data.get('entry_action',""), state_data.get('during_action',""),
                state_data.get('exit_action',""), state_data.get('description',""),
                state_data.get('is_superstate', False),
                state_data.get('sub_fsm_data', {'states':[], 'transitions':[], 'comments':[]}),
                action_language=state_data.get('action_language', DEFAULT_EXECUTION_ENV),
                shape_type=state_data.get('shape_type', self.settings_manager.get("state_default_shape")),
                font_family=state_data.get('font_family', self.settings_manager.get("state_default_font_family")),
                font_size=state_data.get('font_size', self.settings_manager.get("state_default_font_size")),
                font_bold=state_data.get('font_bold', self.settings_manager.get("state_default_font_bold")),
                font_italic=state_data.get('font_italic', self.settings_manager.get("state_default_font_italic")),
                border_style_qt=SettingsManager.STRING_TO_QT_PEN_STYLE.get(state_data.get('border_style_str', self.settings_manager.get("state_default_border_style_str"))), 
                custom_border_width=state_data.get('border_width', self.settings_manager.get("state_default_border_width")),
                icon_path=state_data.get('icon_path')
            )
            if self.parent_window and hasattr(self.parent_window, 'connect_state_item_signals'):
                self.parent_window.connect_state_item_signals(state_item)
            self.addItem(state_item)
            state_items_map[state_data['name']] = state_item

        for trans_data in data.get('transitions', []):
            src_item = state_items_map.get(trans_data['source'])
            tgt_item = state_items_map.get(trans_data['target'])
            if src_item and tgt_item:
                trans_item = GraphicsTransitionItem(
                    src_item, tgt_item,
                    event_str=trans_data.get('event',""), condition_str=trans_data.get('condition',""),
                    action_language=trans_data.get('action_language', DEFAULT_EXECUTION_ENV),
                    action_str=trans_data.get('action',""),
                    color=trans_data.get('color', config.COLOR_ITEM_TRANSITION_DEFAULT), 
                    description=trans_data.get('description',""),
                    line_style_qt=SettingsManager.STRING_TO_QT_PEN_STYLE.get(trans_data.get('line_style_str', self.settings_manager.get("transition_default_line_style_str"))),
                    custom_line_width=trans_data.get('line_width', self.settings_manager.get("transition_default_line_width")),
                    arrowhead_style=trans_data.get('arrowhead_style', self.settings_manager.get("transition_default_arrowhead_style")),
                    label_font_family=trans_data.get('label_font_family', self.settings_manager.get("transition_default_font_family")),
                    label_font_size=trans_data.get('label_font_size', self.settings_manager.get("transition_default_font_size"))
                )
                trans_item.set_control_point_offset(QPointF(trans_data.get('control_offset_x',0), trans_data.get('control_offset_y',0)))
                self.addItem(trans_item)
            else:
                label_info = f"{trans_data.get('event','')}{trans_data.get('condition','')}{trans_data.get('action','')}"
                self._log_to_parent("WARNING", f"Load Warning: Could not link transition '{label_info}' due to missing states: Source='{trans_data['source']}', Target='{trans_data['target']}'.")

        for comment_data in data.get('comments', []):
            comment_item = GraphicsCommentItem(
                comment_data['x'], comment_data['y'], comment_data.get('text', ""),
                font_family=comment_data.get('font_family', self.settings_manager.get("comment_default_font_family")),
                font_size=comment_data.get('font_size', self.settings_manager.get("comment_default_font_size")),
                font_italic=comment_data.get('font_italic', self.settings_manager.get("comment_default_font_italic"))
            )
            comment_item.setTextWidth(comment_data.get('width', 150))
            self.addItem(comment_item)

        self.set_dirty(False) 
        if self.undo_stack: self.undo_stack.clear()
        self.run_all_validations("LoadDiagramData") 
        self.scene_content_changed_for_find.emit()

    def copy_selected_items(self):
        """
        Gathers data from selected items, including transitions that are
        fully contained within the selection, and places it on the clipboard.
        """
        selected_items = self.selectedItems()
        if not selected_items:
            return

        items_to_copy_data = []
        selected_states_and_comments = {item for item in selected_items if isinstance(item, (GraphicsStateItem, GraphicsCommentItem))}
        
        # First, add all selected states and comments
        for item in selected_states_and_comments:
            item_data = item.get_data()
            item_type_str = "State" if isinstance(item, GraphicsStateItem) else "Comment"
            items_to_copy_data.append({
                "item_type": item_type_str,
                "data": item_data,
            })

        # Next, add selected transitions ONLY if both endpoints are also selected
        for item in selected_items:
            if isinstance(item, GraphicsTransitionItem):
                if item.start_item in selected_states_and_comments and item.end_item in selected_states_and_comments:
                    item_data = item.get_data()
                    items_to_copy_data.append({
                        "item_type": "Transition",
                        "data": item_data,
                    })

        if items_to_copy_data:
            clipboard = QApplication.clipboard()
            try:
                json_data_str = json.dumps(items_to_copy_data)
                mime_data_obj = QMimeData()
                mime_data_obj.setData(MIME_TYPE_BSM_ITEMS, json_data_str.encode('utf-8'))
                mime_data_obj.setText(f"{len(items_to_copy_data)} BSM items copied") 
                clipboard.setMimeData(mime_data_obj)
                self._log_to_parent("INFO", f"Copied {len(items_to_copy_data)} item(s) to clipboard.")
            except (json.JSONDecodeError, TypeError) as e:
                self._log_to_parent("ERROR", f"Error serializing items for copy: {e}")

    def paste_items_from_clipboard(self):
        """
        Pastes items from the clipboard onto the scene, handling states,
        comments, and the transitions between them.
        """
        clipboard = QApplication.clipboard()
        mime_data_clipboard = clipboard.mime_Data()

        if not mime_data_clipboard.hasFormat(MIME_TYPE_BSM_ITEMS):
            self._log_to_parent("DEBUG", "Paste: No BSM items found on clipboard.")
            return

        try:
            json_data_bytes = mime_data_clipboard.data(MIME_TYPE_BSM_ITEMS)
            items_to_paste_data = json.loads(json_data_bytes.data().decode('utf-8'))
        except (json.JSONDecodeError, TypeError) as e:
            self._log_to_parent("ERROR", f"Error deserializing items for paste: {e}")
            return

        if not items_to_paste_data:
            return

        self.undo_stack.beginMacro("Paste Items")

        pasted_states_map = {}  # Maps original state name to newly created state item instance
        pasted_graphic_items = []
        
        # Determine the top-left of the pasted content to position it correctly at the cursor
        min_x = float('inf')
        min_y = float('inf')
        for item_info in items_to_paste_data:
            if data := item_info.get("data"):
                min_x = min(min_x, data.get('x', float('inf')))
                min_y = min(min_y, data.get('y', float('inf')))

        drop_pos = QPointF(100, 100) # Default drop position
        if self.views():
            view = self.views()[0]
            drop_pos = view.mapToScene(view.mapFromGlobal(QCursor.pos()))

        offset = drop_pos - QPointF(min_x, min_y) if min_x != float('inf') else QPointF(self.grid_size, self.grid_size)

        # First pass: Create States and Comments to establish references
        for item_info in items_to_paste_data:
            item_type = item_info.get("item_type")
            data = item_info.get("data")
            if not item_type or not data: continue

            new_item = None
            new_pos = QPointF(data.get('x', 0), data.get('y', 0)) + offset
            new_pos.setX(round(new_pos.x() / self.grid_size) * self.grid_size)
            new_pos.setY(round(new_pos.y() / self.grid_size) * self.grid_size)

            if item_type == "State":
                original_name = data.get('name', "PastedState")
                new_name = self._generate_unique_state_name(original_name)
                
                new_item = GraphicsStateItem(
                    x=new_pos.x(), y=new_pos.y(), w=data.get('width', 120), h=data.get('height', 60),
                    text=new_name, is_initial=False, is_final=data.get('is_final', False),
                    color=data.get('color'), entry_action=data.get('entry_action'),
                    during_action=data.get('during_action'), exit_action=data.get('exit_action'),
                    description=data.get('description'), is_superstate=data.get('is_superstate'),
                    sub_fsm_data=json.loads(json.dumps(data.get('sub_fsm_data', {})))
                )
                if self.parent_window: self.parent_window.connect_state_item_signals(new_item)
                pasted_states_map[original_name] = new_item
            
            elif item_type == "Comment":
                new_item = GraphicsCommentItem(x=new_pos.x(), y=new_pos.y(), text=data.get('text'))
                new_item.setTextWidth(data.get('width', 150))
            
            if new_item:
                cmd = AddItemCommand(self, new_item, f"Paste {item_type}")
                self.undo_stack.push(cmd)
                pasted_graphic_items.append(new_item)

        # Second pass: Create Transitions using the mapped states
        for item_info in items_to_paste_data:
            if item_info.get("item_type") == "Transition":
                data = item_info.get("data")
                src_item = pasted_states_map.get(data.get('source'))
                tgt_item = pasted_states_map.get(data.get('target'))

                if src_item and tgt_item:
                    new_item = GraphicsTransitionItem(src_item, tgt_item, **data)
                    cmd = AddItemCommand(self, new_item, "Paste Transition")
                    self.undo_stack.push(cmd)
                    pasted_graphic_items.append(new_item)

        self.undo_stack.endMacro()

        if pasted_graphic_items:
            self.clearSelection()
            for gi in pasted_graphic_items: gi.setSelected(True)
            self._log_to_parent("INFO", f"Pasted {len(pasted_graphic_items)} item(s).")
            if self.views(): self.views()[0].ensureVisible(pasted_graphic_items[0].sceneBoundingRect(), 50, 50)
            self.scene_content_changed_for_find.emit()

    def _generate_unique_state_name(self, base_name: str) -> str:
        if not self.get_state_by_name(base_name):
            return base_name
        copy_match = re.match(r"^(.*?)_Copy(\d+)$", base_name)
        if copy_match:
            prefix = copy_match.group(1)
            num = int(copy_match.group(2))
            next_num = num + 1
            while self.get_state_by_name(f"{prefix}_Copy{next_num}"):
                next_num += 1
            return f"{prefix}_Copy{next_num}"
        num_suffix_match = re.match(r"^(.*?)(\d+)$", base_name)
        if num_suffix_match:
            prefix_base = num_suffix_match.group(1)
            num_base = int(num_suffix_match.group(2))
            if not prefix_base and base_name.isdigit():
                next_num_copy_for_digit = 1
                while self.get_state_by_name(f"{base_name}_Copy{next_num_copy_for_digit}"):
                    next_num_copy_for_digit += 1
                return f"{base_name}_Copy{next_num_copy_for_digit}"
            elif prefix_base: 
                next_num_base = num_base + 1
                while self.get_state_by_name(f"{prefix_base}{next_num_base}"):
                    next_num_base += 1
                return f"{prefix_base}{next_num_base}"
        
        next_num_copy = 1
        while self.get_state_by_name(f"{base_name}_Copy{next_num_copy}"):
            next_num_copy += 1
        return f"{base_name}_Copy{next_num_copy}"

    def _add_template_to_scene(self, template_data: dict, drop_pos: QPointF):
        if not isinstance(template_data, dict):
            self._log_to_parent("ERROR", "Invalid template data format.")
            return

        self.undo_stack.beginMacro(f"Add Template: {template_data.get('name', 'Unnamed Template')}")

        newly_created_scene_items = []
        state_items_map = {} 

        min_x_template = min((s.get('x', 0) for s in template_data.get('states', [])), default=0)
        min_y_template = min((s.get('y', 0) for s in template_data.get('states', [])), default=0)

        base_offset_x = drop_pos.x() - min_x_template
        base_offset_y = drop_pos.y() - min_y_template

        template_instance_suffix = ""
        if any(self.get_state_by_name(s_data.get('name', "State")) for s_data in template_data.get('states', [])):
            i = 1
            while any(self.get_state_by_name(f"{s_data.get('name', 'State')}_{i}") for s_data in template_data.get('states',[])):
                i += 1
            template_instance_suffix = f"_{i}"


        for state_data in template_data.get('states', []):
            original_name = state_data.get('name', "State") 
            unique_name_base = f"{original_name}{template_instance_suffix}"
            unique_name = self._generate_unique_state_name(unique_name_base)

            pos_x = base_offset_x + state_data.get('x', 0)
            pos_y = base_offset_y + state_data.get('y', 0)
            pos_x = round(pos_x / self.grid_size) * self.grid_size
            pos_y = round(pos_y / self.grid_size) * self.grid_size

            state_item = GraphicsStateItem(
                x=pos_x, y=pos_y,
                w=state_data.get('width', 120), h=state_data.get('height', 60),
                text=unique_name,
                is_initial=state_data.get('is_initial', False) if not self.items() else False, 
                is_final=state_data.get('is_final', False),
                color=state_data.get('color', config.COLOR_ITEM_STATE_DEFAULT_BG),
                action_language=state_data.get('action_language', DEFAULT_EXECUTION_ENV),
                entry_action=state_data.get('entry_action', ""),
                during_action=state_data.get('during_action', ""),
                exit_action=state_data.get('exit_action', ""),
                description=state_data.get('description', template_data.get('description', "") if state_data.get('is_initial', False) else ""),
                is_superstate=state_data.get('is_superstate', False),
                sub_fsm_data=json.loads(json.dumps(state_data.get('sub_fsm_data', {'states':[], 'transitions':[], 'comments':[]}))) ,
                shape_type=state_data.get('shape_type', self.settings_manager.get("state_default_shape")),
                font_family=state_data.get('font_family', self.settings_manager.get("state_default_font_family")),
                font_size=state_data.get('font_size', self.settings_manager.get("state_default_font_size")),
                font_bold=state_data.get('font_bold', self.settings_manager.get("state_default_font_bold")),
                font_italic=state_data.get('font_italic', self.settings_manager.get("state_default_font_italic")),
                border_style_qt=SettingsManager.STRING_TO_QT_PEN_STYLE.get(state_data.get('border_style_str', self.settings_manager.get("state_default_border_style_str"))),
                custom_border_width=state_data.get('border_width', self.settings_manager.get("state_default_border_width")),
                icon_path=state_data.get('icon_path')
            )
            if self.parent_window and hasattr(self.parent_window, 'connect_state_item_signals'):
                self.parent_window.connect_state_item_signals(state_item)

            cmd = AddItemCommand(self, state_item, f"Add State from Template: {unique_name}")
            self.undo_stack.push(cmd) 
            newly_created_scene_items.append(state_item)
            state_items_map[original_name] = state_item 

        for trans_data in template_data.get('transitions', []):
            src_original_name = trans_data.get('source')
            tgt_original_name = trans_data.get('target')

            src_item = state_items_map.get(src_original_name) 
            tgt_item = state_items_map.get(tgt_original_name)

            if src_item and tgt_item:
                trans_item = GraphicsTransitionItem(
                    src_item, tgt_item,
                    event_str=trans_data.get('event', ""),
                    condition_str=trans_data.get('condition', ""),
                    action_language=trans_data.get('action_language', DEFAULT_EXECUTION_ENV),
                    action_str=trans_data.get('action', ""),
                    color=trans_data.get('color', config.COLOR_ITEM_TRANSITION_DEFAULT),
                    description=trans_data.get('description', ""),
                    line_style_qt=SettingsManager.STRING_TO_QT_PEN_STYLE.get(trans_data.get('line_style_str', self.settings_manager.get("transition_default_line_style_str"))),
                    custom_line_width=trans_data.get('line_width', self.settings_manager.get("transition_default_line_width")),
                    arrowhead_style=trans_data.get('arrowhead_style', self.settings_manager.get("transition_default_arrowhead_style")),
                    label_font_family=trans_data.get('label_font_family', self.settings_manager.get("transition_default_font_family")),
                    label_font_size=trans_data.get('label_font_size', self.settings_manager.get("transition_default_font_size"))
                )
                trans_item.set_control_point_offset(QPointF(
                    trans_data.get('control_offset_x', 0),
                    trans_data.get('control_offset_y', 0)
                ))
                cmd = AddItemCommand(self, trans_item, f"Add Transition from Template")
                self.undo_stack.push(cmd) 
                newly_created_scene_items.append(trans_item)
            else:
                self._log_to_parent("WARNING", f"Template: Could not link transition. Missing state for '{src_original_name}' or '{tgt_original_name}'.")

        for comment_data in template_data.get('comments', []):
            pos_x = base_offset_x + comment_data.get('x', 0)
            pos_y = base_offset_y + comment_data.get('y', 0)
            pos_x = round(pos_x / self.grid_size) * self.grid_size
            pos_y = round(pos_y / self.grid_size) * self.grid_size

            comment_item = GraphicsCommentItem(
                x=pos_x, y=pos_y,
                text=comment_data.get('text', "Comment"),
                font_family=comment_data.get('font_family', self.settings_manager.get("comment_default_font_family")),
                font_size=comment_data.get('font_size', self.settings_manager.get("comment_default_font_size")),
                font_italic=comment_data.get('font_italic', self.settings_manager.get("comment_default_font_italic"))
            )
            comment_item.setTextWidth(comment_data.get('width', 150))
            cmd = AddItemCommand(self, comment_item, "Add Comment from Template")
            self.undo_stack.push(cmd) 
            newly_created_scene_items.append(comment_item)

        self.undo_stack.endMacro()

        if newly_created_scene_items:
            self.clearSelection()
            for item in newly_created_scene_items:
                item.setSelected(True)
            self._log_to_parent("INFO", f"Added {len(newly_created_scene_items)} items from template '{template_data.get('name', '')}'.")
            self.scene_content_changed_for_find.emit()
            if self.views() and newly_created_scene_items:
                combined_rect = QRectF()
                for i, item in enumerate(newly_created_scene_items):
                    if i == 0:
                        combined_rect = item.sceneBoundingRect()
                    else:
                        combined_rect = combined_rect.united(item.sceneBoundingRect())
                if not combined_rect.isEmpty():
                    self.views()[0].ensureVisible(combined_rect, 50, 50)


class ZoomableView(QGraphicsView):
    zoomChanged = pyqtSignal(float)

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag) 
        self.setViewportUpdateMode(QGraphicsView.BoundingRectViewportUpdate) 
        self.zoom_level_steps = 0 
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse) 
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter) 
        self._is_panning_with_space = False
        self._is_panning_with_mouse_button = False
        self._last_pan_point = QPoint()
        self._emit_current_zoom() 

    def _emit_current_zoom(self): 
        current_scale_factor = self.transform().m11() 
        self.zoomChanged.emit(current_scale_factor)

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.ControlModifier: 
            delta = event.angleDelta().y()
            factor = 1.12 if delta > 0 else 1 / 1.12
            new_zoom_level_steps = self.zoom_level_steps + (1 if delta > 0 else -1)

            min_zoom_level_steps = -15 
            max_zoom_level_steps = 15  

            if min_zoom_level_steps <= new_zoom_level_steps <= max_zoom_level_steps:
                self.scale(factor, factor)
                self.zoom_level_steps = new_zoom_level_steps
                self._emit_current_zoom() 
            event.accept()
        else:
            super().wheelEvent(event) 

    def zoom_in(self):
        factor = 1.12
        new_zoom_level_steps = self.zoom_level_steps + 1
        if new_zoom_level_steps <= 15: 
            self.scale(factor, factor)
            self.zoom_level_steps = new_zoom_level_steps
            self._emit_current_zoom()

    def zoom_out(self):
        factor = 1 / 1.12
        new_zoom_level_steps = self.zoom_level_steps - 1
        if new_zoom_level_steps >= -15: 
            self.scale(factor, factor)
            self.zoom_level_steps = new_zoom_level_steps
            self._emit_current_zoom()

    def reset_view_and_zoom(self):
        self.resetTransform() 
        self.zoom_level_steps = 0
        if self.scene():
            content_rect = self.scene().itemsBoundingRect()
            if not content_rect.isEmpty():
                self.centerOn(content_rect.center()) 
            elif self.scene().sceneRect(): 
                self.centerOn(self.scene().sceneRect().center())
        self._emit_current_zoom()

    def fitInView(self, rect: QRectF, aspectRadioMode: Qt.AspectRatioMode = Qt.IgnoreAspectRatio):
        super().fitInView(rect, aspectRadioMode)
        self._emit_current_zoom() 

    def setTransform(self, matrix: QTransform, combine: bool = False):
        super().setTransform(matrix, combine)
        self._emit_current_zoom() 


    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Space and not self._is_panning_with_space and not event.isAutoRepeat():
            self._is_panning_with_space = True
            self._last_pan_point = self.mapFromGlobal(QCursor.pos()) 
            self.setCursor(Qt.OpenHandCursor)
            event.accept()
        elif event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal: 
            self.zoom_in()
        elif event.key() == Qt.Key_Minus: 
            self.zoom_out()
        elif event.key() == Qt.Key_0 or event.key() == Qt.Key_Asterisk: 
            self.reset_view_and_zoom()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Space and self._is_panning_with_space and not event.isAutoRepeat():
            self._is_panning_with_space = False
            if not self._is_panning_with_mouse_button: 
                self._restore_cursor_to_scene_mode()
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MiddleButton or \
           (self._is_panning_with_space and event.button() == Qt.LeftButton):
            self._last_pan_point = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            self._is_panning_with_mouse_button = True 
            event.accept()
        else:
            self._is_panning_with_mouse_button = False
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_panning_with_mouse_button:
            delta_view = event.pos() - self._last_pan_point 
            self._last_pan_point = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta_view.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta_view.y())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._is_panning_with_mouse_button and \
           (event.button() == Qt.MiddleButton or (self._is_panning_with_space and event.button() == Qt.LeftButton)):
            self._is_panning_with_mouse_button = False
            if self._is_panning_with_space: 
                self.setCursor(Qt.OpenHandCursor)
            else: 
                self._restore_cursor_to_scene_mode()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _restore_cursor_to_scene_mode(self):
        current_scene_mode = self.scene().current_mode if self.scene() and hasattr(self.scene(), 'current_mode') else "select"
        if current_scene_mode == "select":
            self.setCursor(Qt.ArrowCursor)
        elif current_scene_mode in ["state", "comment"]:
            self.setCursor(Qt.CrossCursor)
        elif current_scene_mode == "transition":
            self.setCursor(Qt.PointingHandCursor) 
        else:
            self.setCursor(Qt.ArrowCursor) 

    def zoom_to_rect(self, target_rect: QRectF, padding_factor: float = 0.1):
        if target_rect.isNull() or not self.scene():
            return
        width_padding = target_rect.width() * padding_factor
        height_padding = target_rect.height() * padding_factor
        padded_rect = target_rect.adjusted(-width_padding, -height_padding, width_padding, height_padding)
        self.fitInView(padded_rect, Qt.KeepAspectRatio) 

    def zoom_to_selection(self):
        if not self.scene() or not self.scene().selectedItems():
            return
        selection_rect = QRectF()
        first_item = True
        for item in self.scene().selectedItems():
            if first_item:
                selection_rect = item.sceneBoundingRect()
                first_item = False
            else:
                selection_rect = selection_rect.united(item.sceneBoundingRect())
        if not selection_rect.isEmpty():
            self.zoom_to_rect(selection_rect)

    def fit_diagram_in_view(self):
        if not self.scene():
            return
        items_rect = self.scene().itemsBoundingRect()
        if not items_rect.isEmpty():
            self.zoom_to_rect(items_rect)
        else: 
            self.zoom_to_rect(self.scene().sceneRect())

# --- NEW MINIMAP VIEW CLASS ---
class MinimapView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_view = None
        self.setInteractive(True)
        self.setDragMode(QGraphicsView.NoDrag)
        self._is_dragging_viewport = False
        
        self._viewport_rect_item = QGraphicsRectItem()
        self._viewport_rect_item.setPen(QPen(QColor(255, 0, 0, 180), 2))
        self._viewport_rect_item.setBrush(QBrush(QColor(255, 0, 0, 40)))
        self._viewport_rect_item.setZValue(100)
        
        self.schematic_state_pen = QPen(Qt.NoPen)
        self.schematic_transition_pen = QPen(QColor(120, 144, 156, 180), 1.5)
        self.schematic_comment_brush = QBrush(QColor(255, 249, 196, 120))

    def setMainView(self, view: ZoomableView | None):
        if self.main_view:
            try:
                self.main_view.horizontalScrollBar().valueChanged.disconnect(self.update_viewport_rect)
                self.main_view.verticalScrollBar().valueChanged.disconnect(self.update_viewport_rect)
                if hasattr(self, '_resize_timer'):
                    self.main_view.removeEventFilter(self)
            except (TypeError, RuntimeError):
                logger.debug("Error disconnecting signals from old main_view.")

        self.main_view = view
        
        if self.main_view:
            self.main_view.horizontalScrollBar().valueChanged.connect(self.update_viewport_rect)
            self.main_view.verticalScrollBar().valueChanged.connect(self.update_viewport_rect)
            if not hasattr(self, '_resize_timer'):
                 self._resize_timer = QTimer(self)
                 self._resize_timer.setInterval(100)
                 self._resize_timer.setSingleShot(True)
                 self._resize_timer.timeout.connect(self.update_viewport_rect)
            self.main_view.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.main_view and event.type() == QEvent.Resize:
            if hasattr(self, '_resize_timer'):
                self._resize_timer.start()
        return super().eventFilter(obj, event)

    def update_viewport_rect(self):
        if sip.isdeleted(self) or sip.isdeleted(self._viewport_rect_item): return
        if not self.main_view or not self.scene():
            if self._viewport_rect_item.isVisible(): self._viewport_rect_item.hide()
            return
        if not self._viewport_rect_item.isVisible(): self._viewport_rect_item.show()
        visible_rect = self.main_view.mapToScene(self.main_view.viewport().rect()).boundingRect()
        self._viewport_rect_item.setRect(visible_rect)

    def mousePressEvent(self, event: QMouseEvent):
        if sip.isdeleted(self._viewport_rect_item):
            super().mousePressEvent(event)
            return
        if self._viewport_rect_item.isUnderMouse():
            self._is_dragging_viewport = True
            self.setCursor(Qt.ClosedHandCursor)
        elif self.main_view:
            self.main_view.centerOn(self.mapToScene(event.pos()))
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_dragging_viewport and self.main_view:
            self.main_view.centerOn(self.mapToScene(event.pos()))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._is_dragging_viewport = False
        self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

    def setScene(self, scene: QGraphicsScene | None):
        if sip.isdeleted(self) or sip.isdeleted(self._viewport_rect_item):
            logger.warning("MinimapView.setScene called on a deleted object. Aborting.")
            return

        if self.scene():
            try:
                self.scene().changed.disconnect(self._on_scene_changed)
            except (TypeError, RuntimeError): pass
        
        super().setScene(scene)

        if scene:
            if self._viewport_rect_item.scene() != scene:
                scene.addItem(self._viewport_rect_item)
            self._viewport_rect_item.show()
            scene.changed.connect(self._on_scene_changed)
            self._fit_contents()
            self.update_viewport_rect()
        elif self._viewport_rect_item:
            self._viewport_rect_item.hide()

    def drawBackground(self, painter: QPainter, rect: QRectF):
        super().drawBackground(painter, rect)
        if not self.scene(): return

        painter.setRenderHint(QPainter.Antialiasing, False)
        
        for item in self.scene().items():
            if isinstance(item, GraphicsStateItem):
                painter.setPen(self.schematic_state_pen)
                painter.setBrush(item.base_color)
                painter.drawRect(item.sceneBoundingRect())
            elif isinstance(item, GraphicsTransitionItem):
                if item.start_item and item.end_item:
                    painter.setPen(self.schematic_transition_pen)
                    p1 = item.start_item.sceneBoundingRect().center()
                    p2 = item.end_item.sceneBoundingRect().center()
                    painter.drawLine(p1, p2)
            elif isinstance(item, GraphicsCommentItem):
                painter.setPen(self.schematic_state_pen)
                painter.setBrush(self.schematic_comment_brush)
                painter.drawRect(item.sceneBoundingRect())

    def _on_scene_changed(self):
        if not hasattr(self, '_fit_timer'):
            self._fit_timer = QTimer(self)
            self._fit_timer.setSingleShot(True)
            self._fit_timer.setInterval(150)
            self._fit_timer.timeout.connect(self._fit_contents)
        self._fit_timer.start()

    def _fit_contents(self):
        if self.scene():
            content_rect = self.scene().itemsBoundingRect()
            if content_rect.isEmpty(): content_rect = self.scene().sceneRect()
            self.fitInView(content_rect, Qt.KeepAspectRatio)