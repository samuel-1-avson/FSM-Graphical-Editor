# fsm_designer_project/ui/animation_manager.py
"""
Professional Animation Manager for FSM simulation with clean, minimal design
and intuitive visual feedback systems.
"""

import logging
from typing import Dict, List, Optional, Tuple, Callable
from PyQt6.sip import isdeleted as sip_isdeleted
from PyQt6.QtCore import (
    QObject, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, 
    QSequentialAnimationGroup, pyqtSlot, QTimer, QPointF, QRectF, 
    pyqtSignal, QVariantAnimation, QAbstractAnimation, Qt, pyqtProperty
)
from PyQt6.QtGui import QColor, QPen, QBrush, QFont, QPainterPath, QLinearGradient, QRadialGradient, QPainter
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsPathItem,
    QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QGraphicsItem,
    QGraphicsRectItem, QGraphicsLineItem, QGraphicsProxyWidget,
    QGraphicsObject, QStyleOptionGraphicsItem, QWidget
)
from enum import Enum
import math
import random

logger = logging.getLogger(__name__)


# Professional animatable graphics item
# Professional animatable graphics item
class ProfessionalAnimatableItem(QObject):
    """A professional QGraphicsObject for clean animations, inheriting from QGraphicsObject."""
    def __init__(self, rect: QRectF, shape_type='ellipse', parent: QGraphicsItem = None):
        super().__init__(parent)
        self._rect = rect
        self._shape_type = shape_type
        self._pen = QPen(Qt.PenStyle.NoPen)
        self._brush = QBrush(Qt.GlobalColor.transparent)
        self._border_radius = 0

    def boundingRect(self) -> QRectF:
        pen_width = self._pen.widthF()
        return self._rect.adjusted(-pen_width, -pen_width, pen_width, pen_width)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None):
        painter.setPen(self._pen)
        painter.setBrush(self._brush)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self._shape_type == 'ellipse':
            painter.drawEllipse(self._rect)
        elif self._shape_type == 'rectangle':
            if self._border_radius > 0:
                painter.drawRoundedRect(self._rect, self._border_radius, self._border_radius)
            else:
                painter.drawRect(self._rect)
        elif self._shape_type == 'line':
            painter.drawLine(self._rect.topLeft(), self._rect.bottomRight())

    def setPen(self, pen: QPen):
        if self._pen != pen:
            self.prepareGeometryChange()
            self._pen = pen
            self.update()

    def setBrush(self, brush: QBrush):
        if self._brush != brush:
            self._brush = brush
            self.update()
    
    def setBorderRadius(self, radius: float):
        self._border_radius = radius
        self.update()
    
    def pen(self) -> QPen:
        return self._pen

    def brush(self) -> QBrush:
        return self._brush


class AnimationType(Enum):
    STATE_ENTRY = "state_entry"
    STATE_EXIT = "state_exit"
    TRANSITION = "transition"
    INPUT_CONSUME = "input_consume"
    ERROR = "error"
    SUCCESS = "success"
    VARIABLE_CHANGE = "variable_change"
    ACTION_EXECUTE = "action_execute"
    CONDITION_EVALUATE = "condition_evaluate"
    BREAKPOINT_HIT = "breakpoint_hit"
    SIMULATION_STEP = "simulation_step"


class AnimationPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class AnimationManager(QObject):
    """
    Professional Animation Manager with clean, minimal design and intuitive feedback.
    This is the main manager class for all simulation animations.
    Features:
    - Monochrome color scheme with strategic accent colors
    - Subtle, purposeful animations
    - Clear visual hierarchy
    - Smooth, natural motion
    - Minimal cognitive load
    """
    
    # Signals for animation events
    animation_started = pyqtSignal(str, str)
    animation_finished = pyqtSignal(str, str)
    step_completed = pyqtSignal(int)
    
    def __init__(self, graphics_scene, main_window=None):
        super().__init__()
        self.graphics_scene = graphics_scene
        self.main_window = main_window
        
        # Core animation tracking
        self.active_animations = {}
        self.animation_queue = []
        self.temporary_items = {}
        
        # Graphics item mappings
        self.state_graphics_items = {}
        self.transition_graphics_items = {}
        self.variable_display_items = {}
        
        # Professional visual elements
        self.state_indicators = {}
        self.transition_flows = {}
        self.ui_elements = {}
        
        # Professional color palette - minimal and clean
        self.color_palette = {
            # Primary monochrome colors
            'primary_dark': QColor(24, 24, 27),        # Almost black
            'secondary_dark': QColor(39, 39, 42),      # Dark gray
            'neutral_medium': QColor(113, 113, 122),   # Medium gray
            'neutral_light': QColor(212, 212, 216),    # Light gray
            'background': QColor(248, 250, 252),       # Very light gray
            'white': QColor(255, 255, 255),            # Pure white
            
            # Strategic accent colors
            'accent_blue': QColor(59, 130, 246),       # Professional blue
            'accent_success': QColor(34, 197, 94),     # Success green
            'accent_warning': QColor(245, 158, 11),    # Warning amber
            'accent_error': QColor(239, 68, 68),       # Error red
            
            # State-specific colors
            'state_active': QColor(59, 130, 246, 40),  # Subtle blue highlight
            'state_inactive': QColor(113, 113, 122, 20), # Very subtle gray
            'transition_flow': QColor(59, 130, 246, 80), # Flow blue
            'input_highlight': QColor(34, 197, 94, 60),  # Input green
        }
        
        # Professional animation settings
        self.animation_settings = {
            'duration_fast': 200,      # Quick feedback
            'duration_normal': 400,    # Standard transitions
            'duration_slow': 600,      # Emphasis animations
            'easing_smooth': QEasingCurve.Type.OutCubic,  # <--- CORRECTED
            'easing_bounce': QEasingCurve.Type.OutBack,   # <--- CORRECTED
            'easing_linear': QEasingCurve.Type.Linear,    # <--- CORRECTED
        }
        
        # Typography settings
        self.typography = {
            'primary_font': QFont("Inter", 11, QFont.Weight.Normal),
            'secondary_font': QFont("Inter", 9, QFont.Weight.Normal),
            'code_font': QFont("JetBrains Mono", 9, QFont.Weight.Normal),
            'heading_font': QFont("Inter", 13, QFont.Weight.DemiBold),
        }
        
        # Performance and timing
        self.animation_id_counter = 0
        self.max_concurrent_animations = 8
        self.current_step = 0
        self.step_animation_groups = {}
        
        # Cleanup timer
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self.cleanup_finished_animations)
        self.cleanup_timer.start(1000)
        
        self._initialize_professional_ui()
    
    def _initialize_professional_ui(self):
        """Initialize professional UI elements and categories."""
        categories = [
            'state_indicators', 'transition_flows', 'input_feedback', 
            'status_messages', 'progress_indicators', 'tooltips'
        ]
        for category in categories:
            self.temporary_items[category] = []
    
    def register_graphics_items(self, state_items: Dict, transition_items: Dict):
        """Register graphics items with professional styling."""
        self.state_graphics_items.update(state_items)
        self.transition_graphics_items.update(transition_items)
        
        # Apply professional styling to existing items
        self._apply_professional_styling()
        
        logger.info(f"Registered {len(state_items)} states and {len(transition_items)} transitions with professional styling")
    
    def _apply_professional_styling(self):
        """Apply professional styling to registered graphics items."""
        # Style state items
        for state_name, item in self.state_graphics_items.items():
            if not sip_isdeleted(item):
                self._style_state_item(item)
        
        # Style transition items
        for transition_key, item in self.transition_graphics_items.items():
            if not sip_isdeleted(item):
                self._style_transition_item(item)
    
    def _style_state_item(self, item):
        """Apply professional styling to a state item."""
        if hasattr(item, 'setBrush'):
            # Clean white background with subtle border
            item.setBrush(QBrush(self.color_palette['white']))
        if hasattr(item, 'setPen'):
            # Minimal border
            item.setPen(QPen(self.color_palette['neutral_light'], 1.5))
    
    def _style_transition_item(self, item):
        """Apply professional styling to a transition item."""
        if hasattr(item, 'setPen'):
            # Clean, minimal transition lines
            item.setPen(QPen(self.color_palette['neutral_medium'], 1))
    
    def begin_simulation_step(self, step_number: int):
        """Begin a new simulation step with professional indicators."""
        self.current_step = step_number
        self.step_animation_groups[step_number] = QParallelAnimationGroup()
        
        # Create professional step indicator
        self._create_professional_step_indicator(step_number)
        
        logger.debug(f"Beginning simulation step: {step_number}")
    
    def commit_simulation_step(self):
        """Commit and execute step animations with smooth coordination."""
        if self.current_step in self.step_animation_groups:
            step_group = self.step_animation_groups[self.current_step]
            if step_group.animationCount() > 0:
                step_group.finished.connect(
                    lambda: self.step_completed.emit(self.current_step)
                )
                step_group.start()
                
                self.active_animations[f"step_{self.current_step}"] = {
                    'animation': step_group,
                    'type': AnimationType.SIMULATION_STEP,
                    'priority': AnimationPriority.HIGH
                }
    
    @pyqtSlot(str)
    def animate_state_entry(self, state_name: str):
        """Professional state entry animation with subtle highlighting."""
        if state_name not in self.state_graphics_items:
            return
        
        state_item = self.state_graphics_items[state_name]
        if sip_isdeleted(state_item):
            return
        
        animation_group = QParallelAnimationGroup()
        
        # Create professional state indicator
        indicator = self._create_professional_state_indicator(state_item, 'active')
        if indicator:
            indicator_anim = self._create_smooth_fade_in(indicator)
            animation_group.addAnimation(indicator_anim)
        
        # Subtle scale animation for feedback
        scale_anim = self._create_subtle_scale_animation(state_item)
        if scale_anim:
            animation_group.addAnimation(scale_anim)
        
        # Create clean status label
        status_label = self._create_professional_status_label(f"Entered: {state_name}", state_item)
        if status_label:
            label_anim = self._create_smooth_slide_in(status_label)
            animation_group.addAnimation(label_anim)
        
        self._execute_professional_animation(animation_group, f"state_entry_{state_name}")
        self.animation_started.emit(AnimationType.STATE_ENTRY.value, state_name)
    
    @pyqtSlot(str)
    def animate_state_exit(self, state_name: str):
        """Professional state exit animation with graceful transition."""
        if state_name not in self.state_graphics_items:
            return
        
        state_item = self.state_graphics_items[state_name]
        if sip_isdeleted(state_item):
            return
        
        # Fade existing indicator to inactive state
        if state_name in self.state_indicators:
            indicator = self.state_indicators[state_name]
            if not sip_isdeleted(indicator):
                exit_anim = self._create_smooth_fade_out(indicator)
                self._execute_professional_animation(exit_anim, f"state_exit_{state_name}")
        
        self.animation_started.emit(AnimationType.STATE_EXIT.value, state_name)
    
    @pyqtSlot(str, str, str)
    def animate_transition(self, from_state: str, to_state: str, event: str):
        """Professional transition animation with clean flow visualization."""
        animation_group = QParallelAnimationGroup()
        
        # Create professional flow line
        flow_line = self._create_professional_flow_line(from_state, to_state)
        if flow_line:
            flow_anim = self._create_flow_animation(flow_line)
            animation_group.addAnimation(flow_anim)
        
        # Create clean event label
        event_label = self._create_professional_event_label(event, from_state, to_state)
        if event_label:
            label_anim = self._create_smooth_fade_in(event_label)
            animation_group.addAnimation(label_anim)
        
        self._execute_professional_animation(animation_group, f"transition_{from_state}_{to_state}")
        self.animation_started.emit(AnimationType.TRANSITION.value, f"{from_state}->{to_state}")
    
    @pyqtSlot(str, int)
    def animate_input_symbol(self, symbol: str, position_index: int):
        """Professional input symbol animation with clean feedback."""
        # Create professional input indicator
        input_indicator = self._create_professional_input_indicator(symbol, position_index)
        if input_indicator:
            input_anim = self._create_input_consumption_sequence(input_indicator)
            self._execute_professional_animation(input_anim, f"input_{symbol}")
        
        self.animation_started.emit(AnimationType.INPUT_CONSUME.value, symbol)
    
    def animate_variable_change(self, variable_name: str, old_value: any, new_value: any):
        """Professional variable change animation with clean presentation."""
        var_display = self._create_professional_variable_display(variable_name, old_value, new_value)
        if var_display:
            var_anim = self._create_variable_update_animation(var_display)
            self._execute_professional_animation(var_anim, f"var_change_{variable_name}")
        
        self.animation_started.emit(AnimationType.VARIABLE_CHANGE.value, variable_name)
    
    def animate_condition_evaluation(self, condition: str, result: bool, state_name: str):
        """Professional condition evaluation with clear visual feedback."""
        condition_indicator = self._create_professional_condition_indicator(condition, result, state_name)
        if condition_indicator:
            condition_anim = self._create_smooth_fade_in(condition_indicator)
            self._execute_professional_animation(condition_anim, f"condition_{state_name}")
    
    def animate_action_execution(self, action_code: str, state_name: str):
        """Professional action execution animation."""
        if not action_code.strip():
            return
        
        action_indicator = self._create_professional_action_indicator(action_code, state_name)
        if action_indicator:
            action_anim = self._create_smooth_slide_in(action_indicator)
            self._execute_professional_animation(action_anim, f"action_{state_name}")
    
    def animate_error(self, state_name: str = None, message: str = ""):
        """Professional error animation with clear, non-intrusive feedback."""
        error_notification = self._create_professional_error_notification(message, state_name)
        if error_notification:
            error_anim = self._create_attention_animation(error_notification)
            self._execute_professional_animation(error_anim, "error_animation", AnimationPriority.CRITICAL)
        
        self.animation_started.emit(AnimationType.ERROR.value, state_name or "system")
    
    def animate_success(self, message: str = "Simulation Complete"):
        """Professional success animation with elegant celebration."""
        success_notification = self._create_professional_success_notification(message)
        if success_notification:
            success_anim = self._create_celebration_sequence(success_notification)
            self._execute_professional_animation(success_anim, "success_animation", AnimationPriority.HIGH)
        
        self.animation_started.emit(AnimationType.SUCCESS.value, "system")
    
    def animate_breakpoint_hit(self, state_name: str):
        """Professional breakpoint animation with clear attention-grabbing design."""
        if state_name not in self.state_graphics_items:
            return
        
        state_item = self.state_graphics_items[state_name]
        if sip_isdeleted(state_item):
            return
        
        breakpoint_indicator = self._create_professional_breakpoint_indicator(state_item)
        if breakpoint_indicator:
            bp_anim = self._create_attention_animation(breakpoint_indicator)
            self._execute_professional_animation(bp_anim, f"breakpoint_{state_name}", AnimationPriority.CRITICAL)
    
    # Professional UI creation methods
    def _create_professional_state_indicator(self, state_item, state_type='active'):
        """Create a professional state indicator."""
        if sip_isdeleted(state_item):
            return None
        
        rect = state_item.boundingRect()
        
        # Create subtle highlight ring
        indicator = ProfessionalAnimatableItem(rect.adjusted(-4, -4, 4, 4), 'ellipse')
        
        if state_type == 'active':
            color = self.color_palette['state_active']
            border_color = self.color_palette['accent_blue']
        else:
            color = self.color_palette['state_inactive']
            border_color = self.color_palette['neutral_medium']
        
        indicator.setBrush(QBrush(color))
        indicator.setPen(QPen(border_color, 2))
        indicator.setPos(state_item.pos())
        indicator.setZValue(state_item.zValue() - 1)
        indicator.setOpacity(0)
        
        if state_item.scene():
            state_item.scene().addItem(indicator)
            self.temporary_items['state_indicators'].append(indicator)
        
        return indicator
    
    def _create_professional_flow_line(self, from_state: str, to_state: str):
        """Create a professional transition flow line."""
        from_item = self.state_graphics_items.get(from_state)
        to_item = self.state_graphics_items.get(to_state)
        
        if not from_item or not to_item or sip_isdeleted(from_item) or sip_isdeleted(to_item):
            return None
        
        from_pos = from_item.pos() + from_item.boundingRect().center()
        to_pos = to_item.pos() + to_item.boundingRect().center()
        
        # Create clean, straight line with subtle curve
        path = QPainterPath()
        path.moveTo(from_pos)
        
        # Add subtle curve for visual interest
        mid_point = QPointF((from_pos.x() + to_pos.x()) / 2, (from_pos.y() + to_pos.y()) / 2 - 10)
        path.quadTo(mid_point, to_pos)
        
        # Create professional flow line
        flow_line = QGraphicsPathItem(path)
        flow_line.setPen(QPen(self.color_palette['transition_flow'], 3, Qt.SolidLine, Qt.RoundCap))
        flow_line.setOpacity(0)
        flow_line.setZValue(50)
        
        if from_item.scene():
            from_item.scene().addItem(flow_line)
            self.temporary_items['transition_flows'].append(flow_line)
        
        return flow_line
    
    def _create_professional_event_label(self, event: str, from_state: str, to_state: str):
        """Create a professional event label."""
        from_item = self.state_graphics_items.get(from_state)
        to_item = self.state_graphics_items.get(to_state)
        
        if not from_item or not to_item or sip_isdeleted(from_item) or sip_isdeleted(to_item):
            return None
        
        # Calculate midpoint
        from_pos = from_item.pos() + from_item.boundingRect().center()
        to_pos = to_item.pos() + to_item.boundingRect().center()
        mid_pos = QPointF((from_pos.x() + to_pos.x()) / 2, (from_pos.y() + to_pos.y()) / 2 - 25)
        
        # Create clean label
        label = QGraphicsTextItem(event)
        label.setFont(self.typography['secondary_font'])
        label.setDefaultTextColor(self.color_palette['primary_dark'])
        label.setPos(mid_pos)
        
        # Add clean background
        rect = label.boundingRect()
        background = ProfessionalAnimatableItem(rect.adjusted(-8, -4, 8, 4), 'rectangle')
        background.setBrush(QBrush(self.color_palette['white']))
        background.setPen(QPen(self.color_palette['neutral_light'], 1))
        background.setBorderRadius(6)
        background.setParentItem(label)
        background.setZValue(-1)
        
        label.setOpacity(0)
        label.setZValue(100)
        
        if from_item.scene():
            from_item.scene().addItem(label)
            self.temporary_items['status_messages'].append(label)
        
        return label
    
    def _create_professional_input_indicator(self, symbol: str, position_index: int):
        """Create a professional input symbol indicator."""
        if not self.graphics_scene:
            return None
        
        # Position in input area
        x_pos = 60 + position_index * 35
        y_pos = 30
        
        # Create clean input display
        container = ProfessionalAnimatableItem(QRectF(-15, -12, 30, 24), 'rectangle')
        container.setBrush(QBrush(self.color_palette['input_highlight']))
        container.setPen(QPen(self.color_palette['accent_success'], 2))
        container.setBorderRadius(8)
        container.setPos(x_pos, y_pos)
        container.setOpacity(0)
        container.setZValue(200)
        
        # Add symbol text
        symbol_text = QGraphicsTextItem(symbol)
        symbol_text.setFont(self.typography['code_font'])
        symbol_text.setDefaultTextColor(self.color_palette['primary_dark'])
        
        # Center text in container
        text_rect = symbol_text.boundingRect()
        text_pos = QPointF(-text_rect.width() / 2, -text_rect.height() / 2)
        symbol_text.setPos(text_pos)
        symbol_text.setParentItem(container)
        
        self.graphics_scene.addItem(container)
        self.temporary_items['input_feedback'].append(container)
        
        return container
    
    def _create_professional_variable_display(self, variable_name: str, old_value: any, new_value: any):
        """Create professional variable change display."""
        if not self.graphics_scene:
            return None
        
        # Position in variable panel
        y_offset = len(self.variable_display_items) * 32 + 80
        
        # Create clean variable panel
        panel = ProfessionalAnimatableItem(QRectF(0, 0, 250, 28), 'rectangle')
        panel.setBrush(QBrush(self.color_palette['white']))
        panel.setPen(QPen(self.color_palette['neutral_light'], 1))
        panel.setBorderRadius(6)
        panel.setPos(20, y_offset)
        panel.setOpacity(0)
        panel.setZValue(150)
        
        # Add variable text
        var_text = QGraphicsTextItem(f"{variable_name}: {old_value} → {new_value}")
        var_text.setFont(self.typography['code_font'])
        var_text.setDefaultTextColor(self.color_palette['primary_dark'])
        var_text.setPos(10, 4)
        var_text.setParentItem(panel)
        
        self.graphics_scene.addItem(panel)
        self.temporary_items['status_messages'].append(panel)
        self.variable_display_items[variable_name] = panel
        
        return panel
    
    def _create_professional_condition_indicator(self, condition: str, result: bool, state_name: str):
        """Create professional condition evaluation indicator."""
        state_item = self.state_graphics_items.get(state_name)
        if not state_item or sip_isdeleted(state_item):
            return None
        
        # Position near state
        state_pos = state_item.pos() + state_item.boundingRect().center()
        indicator_pos = QPointF(state_pos.x() + 70, state_pos.y() - 15)
        
        # Create clean indicator
        indicator = ProfessionalAnimatableItem(QRectF(0, 0, 120, 24), 'rectangle')
        
        if result:
            indicator.setBrush(QBrush(self.color_palette['accent_success'].lighter(180)))
            indicator.setPen(QPen(self.color_palette['accent_success'], 1))
            icon = "✓"
        else:
            indicator.setBrush(QBrush(self.color_palette['accent_error'].lighter(180)))
            indicator.setPen(QPen(self.color_palette['accent_error'], 1))
            icon = "✗"
        
        indicator.setBorderRadius(6)
        indicator.setPos(indicator_pos)
        indicator.setOpacity(0)
        indicator.setZValue(120)
        
        # Add condition text
        condition_text = QGraphicsTextItem(f"{icon} {condition[:15]}...")
        condition_text.setFont(self.typography['secondary_font'])
        condition_text.setDefaultTextColor(self.color_palette['primary_dark'])
        condition_text.setPos(6, 3)
        condition_text.setParentItem(indicator)
        
        if state_item.scene():
            state_item.scene().addItem(indicator)
            self.temporary_items['status_messages'].append(indicator)
        
        return indicator
    
    def _create_professional_action_indicator(self, action_code: str, state_name: str):
        """Create professional action execution indicator."""
        state_item = self.state_graphics_items.get(state_name)
        if not state_item or sip_isdeleted(state_item):
            return None
        
        # Position next to state
        state_pos = state_item.pos() + state_item.boundingRect().center()
        indicator_pos = QPointF(state_pos.x() + 80, state_pos.y() + 15)
        
        # Create clean action panel
        truncated_code = action_code[:25] + "..." if len(action_code) > 25 else action_code
        
        indicator = ProfessionalAnimatableItem(QRectF(0, 0, 200, 28), 'rectangle')
        indicator.setBrush(QBrush(self.color_palette['secondary_dark'].lighter(150)))
        indicator.setPen(QPen(self.color_palette['neutral_medium'], 1))
        indicator.setBorderRadius(6)
        indicator.setPos(indicator_pos)
        indicator.setOpacity(0)
        indicator.setZValue(130)
        
        # Add action text
        action_text = QGraphicsTextItem(f"⚡ {truncated_code}")
        action_text.setFont(self.typography['code_font'])
        action_text.setDefaultTextColor(self.color_palette['white'])
        action_text.setPos(8, 4)
        action_text.setParentItem(indicator)
        
        if state_item.scene():
            state_item.scene().addItem(indicator)
            self.temporary_items['status_messages'].append(indicator)
        
        return indicator
    
    def _create_professional_error_notification(self, message: str, state_name: str = None):
        """Create professional error notification."""
        if not self.graphics_scene:
            return None
        
        # Position at top-right of scene
        scene_rect = self.graphics_scene.sceneRect()
        notification_pos = QPointF(scene_rect.right() - 320, scene_rect.top() + 20)
        
        # Create clean error notification
        notification = ProfessionalAnimatableItem(QRectF(0, 0, 300, 60), 'rectangle')
        notification.setBrush(QBrush(self.color_palette['accent_error'].lighter(170)))
        notification.setPen(QPen(self.color_palette['accent_error'], 2))
        notification.setBorderRadius(8)
        notification.setPos(notification_pos)
        notification.setOpacity(0)
        notification.setZValue(300)
        
        # Add error text
        error_text = QGraphicsTextItem(f"⚠ Error: {message}")
        error_text.setFont(self.typography['primary_font'])
        error_text.setDefaultTextColor(self.color_palette['primary_dark'])
        error_text.setPos(15, 20)
        error_text.setParentItem(notification)
        
        self.graphics_scene.addItem(notification)
        self.temporary_items['status_messages'].append(notification)
        
        return notification
    
    def _create_professional_success_notification(self, message: str):
        """Create professional success notification."""
        if not self.graphics_scene:
            return None

    @pyqtSlot()
    def cleanup_finished_animations(self):
        """Periodically cleans up animations that have finished playing."""
        finished_keys = []
        for key, anim_data in self.active_animations.items():
            animation = anim_data.get('animation')
            # Check if the animation object exists and its state is Stopped
            if animation and animation.state() == QAbstractAnimation.State.Stopped:
                finished_keys.append(key)

        for key in finished_keys:
            # The animation object might be set to DeleteWhenStopped.
            # We just need to remove our reference to it.
            if key in self.active_animations:
                del self.active_animations[key]
                logger.debug(f"Cleaned up finished animation: {key}")