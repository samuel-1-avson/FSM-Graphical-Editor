# fsm_designer_project/animation_manager.py
"""
Significantly Enhanced Animation Manager for FSM simulation with advanced visual effects,
synchronized timing, and rich feedback systems.
"""

import logging
from typing import Dict, List, Optional, Tuple, Callable
from PyQt5.QtCore import (
    QObject, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, 
    QSequentialAnimationGroup, pyqtSlot, QTimer, QPointF, QRectF, 
    pyqtSignal, QVariantAnimation, QAbstractAnimation, Qt, pyqtProperty
)
from PyQt5.QtGui import QColor, QPen, QBrush, QFont, QPainterPath, QLinearGradient, QRadialGradient, QPainter
from PyQt5.QtWidgets import (
    QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsPathItem,
    QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QGraphicsItem,
    QGraphicsRectItem, QGraphicsLineItem, QGraphicsProxyWidget,
    QGraphicsObject, QStyleOptionGraphicsItem, QWidget
)
import sip
from enum import Enum
import math
import random

logger = logging.getLogger(__name__)


# --- FIX: Helper class to make a QGraphicsItem animatable by inheriting QObject ---
class AnimatableEllipseItem(QGraphicsObject):
    """A QGraphicsObject that draws an ellipse, making it animatable."""
    def __init__(self, rect: QRectF, parent: QGraphicsItem = None):
        super().__init__(parent)
        self._rect = rect
        self._pen = QPen(Qt.NoPen)
        self._brush = QBrush(Qt.transparent)

    def boundingRect(self) -> QRectF:
        # Add a little padding to account for pen width if it's set
        pen_width = self._pen.widthF()
        return self._rect.adjusted(-pen_width, -pen_width, pen_width, pen_width)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None):
        painter.setPen(self._pen)
        painter.setBrush(self._brush)
        painter.drawEllipse(self._rect)

    # --- FIX: Add methods to control the appearance ---
    def setPen(self, pen: QPen):
        if self._pen != pen:
            self.prepareGeometryChange()
            self._pen = pen
            self.update()

    def setBrush(self, brush: QBrush):
        if self._brush != brush:
            self._brush = brush
            self.update()
    
    def pen(self) -> QPen:
        return self._pen

    def brush(self) -> QBrush:
        return self._brush
# --- END FIX ---


# (The rest of the file's classes remain the same until AnimationManager)

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
    Significantly enhanced animation manager with advanced visual effects,
    synchronized timing, performance optimization, and rich feedback systems.
    """
    
    # Signals for animation events
    animation_started = pyqtSignal(str, str)  # animation_type, target
    animation_finished = pyqtSignal(str, str)  # animation_type, target
    step_completed = pyqtSignal(int)  # step_number
    
    def __init__(self, graphics_scene, main_window=None):
        super().__init__()
        self.graphics_scene = graphics_scene
        self.main_window = main_window
        
        # Core animation tracking
        self.active_animations = {}  # animation_id -> animation_info
        self.animation_queue = []  # Queue for sequential animations
        self.temporary_items = {}  # category -> [items]
        
        # Graphics item mappings
        self.state_graphics_items = {}  # state_name -> graphics_item
        self.transition_graphics_items = {}  # (from, to, event) -> graphics_item
        self.variable_display_items = {}  # variable_name -> display_item
        
        # Enhanced visual elements
        self.state_highlights = {}  # state_name -> highlight_effects
        self.transition_pulses = {}  # transition_id -> pulse_effects
        self.floating_elements = {}  # element_id -> floating_item
        self.particle_systems = {}  # system_id -> particle_list
        
        # Animation settings with adaptive performance
        self.base_settings = {
            'animation_duration': 800,
            'pulse_duration': 400,
            'fade_duration': 300,
            'move_duration': 600,
            'particle_count': 5,
            'sparkle_count': 12,
        }
        self.current_settings = self.base_settings.copy()
        self.performance_mode = 'high'  # 'low', 'medium', 'high'
        
        # Advanced color schemes
        self.color_schemes = {
            'classic': {
                'current_state': QColor(255, 215, 0, 180),     # Gold
                'previous_state': QColor(200, 200, 200, 100),   # Gray
                'transition_active': QColor(0, 255, 0, 150),    # Green
                'transition_path': QColor(255, 165, 0, 200),    # Orange
                'input_symbol': QColor(100, 149, 237, 200),     # Cornflower blue
                'error': QColor(255, 69, 0, 180),               # Red-orange
                'success': QColor(50, 205, 50, 180),            # Lime green
                'breakpoint': QColor(255, 0, 0, 150),           # Red
                'variable_change': QColor(138, 43, 226, 150),   # Blue violet
                'action_execute': QColor(255, 20, 147, 150),    # Deep pink
                'condition_true': QColor(124, 252, 0, 150),     # Lawn green
                'condition_false': QColor(255, 99, 71, 150),    # Tomato
            },
            'dark': {
                'current_state': QColor(255, 223, 0, 200),      # Brighter gold
                'previous_state': QColor(128, 128, 128, 120),   # Medium gray
                'transition_active': QColor(0, 255, 127, 180),  # Spring green
                'transition_path': QColor(255, 140, 0, 220),    # Dark orange
                'input_symbol': QColor(135, 206, 250, 200),     # Light sky blue
                'error': QColor(255, 69, 0, 200),               # Brighter red-orange
                'success': QColor(50, 255, 50, 200),            # Brighter lime
                'breakpoint': QColor(255, 20, 20, 180),         # Bright red
                'variable_change': QColor(147, 112, 219, 180),  # Medium purple
                'action_execute': QColor(255, 105, 180, 180),   # Hot pink
                'condition_true': QColor(50, 255, 50, 180),     # Bright green
                'condition_false': QColor(255, 69, 0, 180),     # Red orange
            }
        }
        self.current_colors = self.color_schemes['classic']
        
        # Performance and timing management
        self.animation_id_counter = 0
        self.max_concurrent_animations = 10
        self.frame_budget_ms = 16  # Target 60 FPS
        
        # Step synchronization
        self.current_step = 0
        self.step_animation_groups = {}  # step -> animation_group
        self.step_timer = QTimer()
        self.step_timer.timeout.connect(self._process_step_queue)
        
        # Cleanup and optimization
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self.cleanup_finished_animations)
        self.cleanup_timer.start(500)  # More frequent cleanup
        
        # Performance monitoring
        self.performance_metrics = {
            'total_animations': 0,
            'active_count': 0,
            'average_duration': 0,
            'dropped_frames': 0
        }
        
        self._initialize_temporary_categories()
    
    def _initialize_temporary_categories(self):
        """Initialize categories for temporary items organization."""
        categories = [
            'highlights', 'particles', 'labels', 'effects', 
            'transitions', 'sparkles', 'indicators', 'messages'
        ]
        for category in categories:
            self.temporary_items[category] = []
    
    def set_performance_mode(self, mode: str):
        """Set performance mode to adjust animation quality and quantity."""
        performance_modes = {
            'low': {
                'animation_duration': 400,
                'pulse_duration': 200,
                'fade_duration': 150,
                'move_duration': 300,
                'particle_count': 2,
                'sparkle_count': 5,
                'max_concurrent': 5
            },
            'medium': {
                'animation_duration': 600,
                'pulse_duration': 300,
                'fade_duration': 225,
                'move_duration': 450,
                'particle_count': 3,
                'sparkle_count': 8,
                'max_concurrent': 7
            },
            'high': self.base_settings.copy()
        }
        
        if mode in performance_modes:
            self.performance_mode = mode
            self.current_settings = performance_modes[mode]
            if 'max_concurrent' in self.current_settings:
                self.max_concurrent_animations = self.current_settings['max_concurrent']
            logger.info(f"Performance mode set to: {mode}")
    
    def set_color_scheme(self, scheme_name: str):
        """Change the color scheme for animations."""
        if scheme_name in self.color_schemes:
            self.current_colors = self.color_schemes[scheme_name]
            logger.info(f"Color scheme changed to: {scheme_name}")
    
    def register_graphics_items(self, state_items: Dict, transition_items: Dict):
        """Register graphics items for animation with enhanced tracking."""
        self.state_graphics_items.update(state_items)
        self.transition_graphics_items.update(transition_items)
        
        # Pre-calculate item properties for performance
        for state_name, item in state_items.items():
            if not sip.isdeleted(item):
                item._animation_center = item.pos() + item.boundingRect().center()
                item._animation_bounds = item.boundingRect()
        
        logger.info(f"Registered {len(state_items)} states and {len(transition_items)} transitions")
    
    def begin_simulation_step(self, step_number: int):
        """Begin a new simulation step with synchronized animations."""
        self.current_step = step_number
        self.step_animation_groups[step_number] = QParallelAnimationGroup()
        
        # Create step indicator
        self._create_step_indicator(step_number)
        
        logger.debug(f"Beginning simulation step: {step_number}")
    
    def commit_simulation_step(self):
        """Commit and start all animations for the current step."""
        if self.current_step in self.step_animation_groups:
            step_group = self.step_animation_groups[self.current_step]
            if step_group.animationCount() > 0:
                step_group.finished.connect(
                    lambda: self.step_completed.emit(self.current_step)
                )
                step_group.start()
                
                animation_info = {
                    'id': f"step_{self.current_step}",
                    'type': AnimationType.SIMULATION_STEP,
                    'priority': AnimationPriority.HIGH,
                    'animation': step_group,
                    'target': f"step_{self.current_step}"
                }
                self.active_animations[animation_info['id']] = animation_info
                
        logger.debug(f"Committed simulation step: {self.current_step}")
    
    @pyqtSlot(str)
    def animate_state_entry(self, state_name: str):
        """Enhanced state entry animation with multiple effect layers."""
        if state_name not in self.state_graphics_items:
            logger.warning(f"No graphics item found for state: {state_name}")
            return
        
        state_item = self.state_graphics_items[state_name]
        if sip.isdeleted(state_item):
            return
        
        animation_group = QParallelAnimationGroup()
        
        # Layer 1: Background glow ring
        glow_ring = self._create_enhanced_glow_ring(state_item)
        if glow_ring:
            glow_anim = self._create_glow_ring_animation(glow_ring)
            animation_group.addAnimation(glow_anim)
        
        # Layer 2: Pulsing highlight
        highlight = self._create_enhanced_state_highlight(state_item, self.current_colors['current_state'])
        if highlight:
            self.state_highlights[state_name] = highlight
            highlight_anim = self._create_highlight_entry_animation(highlight)
            animation_group.addAnimation(highlight_anim)
        
        # Layer 3: Particle burst
        if self.performance_mode in ['medium', 'high']:
            particles = self._create_entry_particle_burst(state_item)
            for particle in particles:
                particle_anim = self._create_particle_animation(particle)
                animation_group.addAnimation(particle_anim)
        
        # Layer 4: State label enhancement
        self._enhance_state_label(state_item, state_name)
        
        # Add to current step or execute immediately
        if self.current_step in self.step_animation_groups:
            self.step_animation_groups[self.current_step].addAnimation(animation_group)
        else:
            self._execute_animation_group(animation_group, f"state_entry_{state_name}")
        
        self.animation_started.emit(AnimationType.STATE_ENTRY.value, state_name)
        logger.debug(f"Enhanced state entry animation for: {state_name}")
    
    @pyqtSlot(str)
    def animate_state_exit(self, state_name: str):
        """Enhanced state exit animation with graceful transitions."""
        if state_name not in self.state_graphics_items:
            return
        
        state_item = self.state_graphics_items[state_name]
        if sip.isdeleted(state_item):
            return
        
        animation_group = QParallelAnimationGroup()
        
        # Fade existing highlight to "previous state" appearance
        if state_name in self.state_highlights:
            highlight = self.state_highlights[state_name]
            if not sip.isdeleted(highlight):
                exit_anim = self._create_state_exit_animation(highlight)
                animation_group.addAnimation(exit_anim)
        
        # Create exit particle effect
        if self.performance_mode == 'high':
            exit_particles = self._create_exit_particle_effect(state_item)
            for particle in exit_particles:
                particle_anim = self._create_particle_fade_animation(particle)
                animation_group.addAnimation(particle_anim)
        
        # Dim state label
        self._dim_state_label(state_item, state_name)
        
        if self.current_step in self.step_animation_groups:
            self.step_animation_groups[self.current_step].addAnimation(animation_group)
        else:
            self._execute_animation_group(animation_group, f"state_exit_{state_name}")
        
        self.animation_started.emit(AnimationType.STATE_EXIT.value, state_name)
        logger.debug(f"Enhanced state exit animation for: {state_name}")
    
    @pyqtSlot(str, str, str)
    def animate_transition(self, from_state: str, to_state: str, event: str):
        """Enhanced transition animation with flowing energy effects."""
        animation_group = QParallelAnimationGroup()
        
        # Find or create transition path
        transition_key = (from_state, to_state, event)
        transition_item = self.transition_graphics_items.get(transition_key)
        
        if transition_item and not sip.isdeleted(transition_item):
            # Animate existing transition
            pulse_anim = self._create_enhanced_transition_pulse(transition_item)
            animation_group.addAnimation(pulse_anim)
        else:
            # Create temporary transition visualization
            temp_transition = self._create_enhanced_temporary_transition(from_state, to_state, event)
            if temp_transition:
                temp_anim = self._create_temporary_transition_animation(temp_transition)
                animation_group.addAnimation(temp_anim)
        
        # Create energy flow particles
        if self.performance_mode in ['medium', 'high']:
            flow_particles = self._create_energy_flow_particles(from_state, to_state)
            for particle_group in flow_particles:
                flow_anim = self._create_energy_flow_animation(particle_group)
                animation_group.addAnimation(flow_anim)
        
        # Create event label with enhanced styling
        event_label = self._create_enhanced_event_label(event, from_state, to_state)
        if event_label:
            label_anim = self._create_event_label_animation(event_label)
            animation_group.addAnimation(label_anim)
        
        if self.current_step in self.step_animation_groups:
            self.step_animation_groups[self.current_step].addAnimation(animation_group)
        else:
            self._execute_animation_group(animation_group, f"transition_{from_state}_{to_state}")
        
        self.animation_started.emit(AnimationType.TRANSITION.value, f"{from_state}->{to_state}")
        logger.debug(f"Enhanced transition animation: {from_state} -> {to_state} on {event}")
    
    @pyqtSlot(str, int)
    def animate_input_symbol(self, symbol: str, position_index: int):
        """Enhanced input symbol animation with rich visual feedback."""
        animation_group = QParallelAnimationGroup()
        
        # Create stylized input symbol
        symbol_display = self._create_enhanced_input_symbol(symbol, position_index)
        if symbol_display:
            # Multi-phase animation: appear -> highlight -> consume -> disappear
            symbol_anim = self._create_input_symbol_sequence(symbol_display)
            animation_group.addAnimation(symbol_anim)
        
        # Create consumption particles
        if self.performance_mode in ['medium', 'high']:
            consumption_particles = self._create_consumption_particles(position_index)
            for particle in consumption_particles:
                particle_anim = self._create_consumption_particle_animation(particle)
                animation_group.addAnimation(particle_anim)
        
        if self.current_step in self.step_animation_groups:
            self.step_animation_groups[self.current_step].addAnimation(animation_group)
        else:
            self._execute_animation_group(animation_group, f"input_{symbol}")
        
        self.animation_started.emit(AnimationType.INPUT_CONSUME.value, symbol)
        logger.debug(f"Enhanced input symbol animation: {symbol}")
    
    def animate_variable_change(self, variable_name: str, old_value: any, new_value: any):
        """Animate variable changes with visual indicators."""
        animation_group = QParallelAnimationGroup()
        
        # Create or update variable display
        var_display = self._create_variable_display(variable_name, old_value, new_value)
        if var_display:
            var_anim = self._create_variable_change_animation(var_display)
            animation_group.addAnimation(var_anim)
        
        # Create change indicator particles
        if self.performance_mode == 'high':
            change_particles = self._create_variable_change_particles(variable_name)
            for particle in change_particles:
                particle_anim = self._create_particle_animation(particle)
                animation_group.addAnimation(particle_anim)
        
        if self.current_step in self.step_animation_groups:
            self.step_animation_groups[self.current_step].addAnimation(animation_group)
        else:
            self._execute_animation_group(animation_group, f"var_change_{variable_name}")
        
        self.animation_started.emit(AnimationType.VARIABLE_CHANGE.value, variable_name)
        logger.debug(f"Variable change animation: {variable_name} = {new_value}")
    
    def animate_condition_evaluation(self, condition: str, result: bool, state_name: str):
        """Animate condition evaluation with visual feedback."""
        animation_group = QParallelAnimationGroup()
        
        color = self.current_colors['condition_true'] if result else self.current_colors['condition_false']
        
        # Create condition indicator
        condition_indicator = self._create_condition_indicator(condition, result, state_name)
        if condition_indicator:
            indicator_anim = self._create_condition_indicator_animation(condition_indicator)
            animation_group.addAnimation(indicator_anim)
        
        if self.current_step in self.step_animation_groups:
            self.step_animation_groups[self.current_step].addAnimation(animation_group)
        else:
            self._execute_animation_group(animation_group, f"condition_{state_name}")
        
        self.animation_started.emit(AnimationType.CONDITION_EVALUATE.value, f"{state_name}_{result}")
    
    def animate_action_execution(self, action_code: str, state_name: str):
        """Animate action execution with code visualization."""
        if not action_code.strip():
            return
        
        animation_group = QParallelAnimationGroup()
        
        # Create action indicator
        action_indicator = self._create_action_indicator(action_code, state_name)
        if action_indicator:
            action_anim = self._create_action_execution_animation(action_indicator)
            animation_group.addAnimation(action_anim)
        
        if self.current_step in self.step_animation_groups:
            self.step_animation_groups[self.current_step].addAnimation(animation_group)
        else:
            self._execute_animation_group(animation_group, f"action_{state_name}")
        
        self.animation_started.emit(AnimationType.ACTION_EXECUTE.value, state_name)
    
    def animate_error(self, state_name: str = None, message: str = ""):
        """Enhanced error animation with dramatic visual effects."""
        animation_group = QParallelAnimationGroup()
        
        if state_name and state_name in self.state_graphics_items:
            state_item = self.state_graphics_items[state_name]
            if not sip.isdeleted(state_item):
                # Create intensive error effects
                error_effects = self._create_intensive_error_effects(state_item)
                for effect in error_effects:
                    error_anim = self._create_error_effect_animation(effect)
                    animation_group.addAnimation(error_anim)
        
        # Enhanced error message
        if message:
            error_message = self._create_enhanced_error_message(message)
            if error_message:
                message_anim = self._create_error_message_animation(error_message)
                animation_group.addAnimation(message_anim)
        
        self._execute_animation_group(animation_group, "error_animation", priority=AnimationPriority.CRITICAL)
        self.animation_started.emit(AnimationType.ERROR.value, state_name or "system")
    
    def animate_success(self, message: str = "Simulation Complete"):
        """Enhanced success animation with celebration effects."""
        animation_group = QParallelAnimationGroup()
        
        # Create success message
        success_message = self._create_enhanced_success_message(message)
        if success_message:
            message_anim = self._create_success_message_animation(success_message)
            animation_group.addAnimation(message_anim)
        
        # Create celebration effects
        if self.performance_mode in ['medium', 'high']:
            celebration_effects = self._create_celebration_effects()
            for effect_group in celebration_effects:
                effect_anim = self._create_celebration_animation(effect_group)
                animation_group.addAnimation(effect_anim)
        
        self._execute_animation_group(animation_group, "success_animation", priority=AnimationPriority.HIGH)
        self.animation_started.emit(AnimationType.SUCCESS.value, "system")
    
    def animate_breakpoint_hit(self, state_name: str):
        """Enhanced breakpoint animation with attention-grabbing effects."""
        if state_name not in self.state_graphics_items:
            return
        
        state_item = self.state_graphics_items[state_name]
        if sip.isdeleted(state_item):
            return
        
        animation_group = QParallelAnimationGroup()
        
        # Create breakpoint effects
        breakpoint_effects = self._create_enhanced_breakpoint_effects(state_item)
        for effect in breakpoint_effects:
            bp_anim = self._create_breakpoint_animation(effect)
            animation_group.addAnimation(bp_anim)
        
        self._execute_animation_group(animation_group, f"breakpoint_{state_name}", priority=AnimationPriority.CRITICAL)
        self.animation_started.emit(AnimationType.BREAKPOINT_HIT.value, state_name)
        logger.debug(f"Enhanced breakpoint animation for: {state_name}")
    
    # Enhanced creation methods
    def _create_enhanced_glow_ring(self, state_item):
        """Create an enhanced glow ring around a state."""
        if sip.isdeleted(state_item):
            return None
        
        rect = state_item.boundingRect()
        ring = AnimatableEllipseItem(rect.adjusted(-15, -15, 15, 15))
        
        # Create gradient glow
        gradient = QRadialGradient(rect.center(), rect.width() / 2 + 15)
        gradient.setColorAt(0, QColor(self.current_colors['current_state']).darker(150))
        gradient.setColorAt(0.7, self.current_colors['current_state'])
        gradient.setColorAt(1, QColor(self.current_colors['current_state']).lighter(200))
        
        ring.setBrush(QBrush(gradient))
        ring.setPen(QPen(Qt.NoPen))
        ring.setPos(state_item.pos())
        ring.setZValue(state_item.zValue() - 2)
        ring.setOpacity(0)
        
        if state_item.scene():
            state_item.scene().addItem(ring)
            self.temporary_items['effects'].append(ring)
        
        return ring
    
    def _create_enhanced_state_highlight(self, state_item, color: QColor):
        """Create an enhanced state highlight with multiple layers."""
        if sip.isdeleted(state_item):
            return None
        
        rect = state_item.boundingRect()
        
        # Main highlight
        highlight = AnimatableEllipseItem(rect.adjusted(-8, -8, 8, 8))
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, color.lighter(120))
        gradient.setColorAt(0.5, color)
        gradient.setColorAt(1, color.darker(120))
        
        highlight.setBrush(QBrush(gradient))
        highlight.setPen(QPen(color.lighter(150), 3))
        highlight.setPos(state_item.pos())
        highlight.setZValue(state_item.zValue() - 1)
        
        if state_item.scene():
            state_item.scene().addItem(highlight)
            self.temporary_items['highlights'].append(highlight)
        
        return highlight
    
    def _create_entry_particle_burst(self, state_item):
        """Create a burst of particles for state entry."""
        if sip.isdeleted(state_item):
            return []
        
        particles = []
        center = state_item.pos() + state_item.boundingRect().center()
        particle_count = self.current_settings['particle_count']
        
        for i in range(particle_count):
            angle = (2 * math.pi * i) / particle_count
            distance = 30
            
            particle = AnimatableEllipseItem(QRectF(-2, -2, 4, 4))
            particle.setBrush(QBrush(self.current_colors['current_state'].lighter(150)))
            particle.setPen(QPen(self.current_colors['current_state'], 1))
            particle.setPos(center)
            
            # Calculate target position
            target_x = center.x() + math.cos(angle) * distance
            target_y = center.y() + math.sin(angle) * distance
            particle._target_pos = QPointF(target_x, target_y)
            
            if state_item.scene():
                state_item.scene().addItem(particle)
                self.temporary_items['particles'].append(particle)
                particles.append(particle)
        
        return particles
    
    def _create_enhanced_temporary_transition(self, from_state: str, to_state: str, event: str):
        """Create an enhanced temporary transition visualization."""
        from_item = self.state_graphics_items.get(from_state)
        to_item = self.state_graphics_items.get(to_state)
        
        if not from_item or not to_item or sip.isdeleted(from_item) or sip.isdeleted(to_item):
            return None
        
        from_pos = from_item.pos() + from_item.boundingRect().center()
        to_pos = to_item.pos() + to_item.boundingRect().center()
        
        # Create enhanced curved path
        path = QPainterPath()
        path.moveTo(from_pos)
        
        # Calculate control points for smooth curve
        dx = to_pos.x() - from_pos.x()
        dy = to_pos.y() - from_pos.y()
        
        control1 = QPointF(from_pos.x() + dx * 0.3, from_pos.y() - abs(dx) * 0.3)
        control2 = QPointF(to_pos.x() - dx * 0.3, to_pos.y() - abs(dx) * 0.3)
        
        path.cubicTo(control1, control2, to_pos)
        
        # Create gradient pen
        gradient = QLinearGradient(from_pos, to_pos)
        gradient.setColorAt(0, self.current_colors['transition_path'])
        gradient.setColorAt(0.5, self.current_colors['transition_active'])
        gradient.setColorAt(1, self.current_colors['transition_path'])
        
        path_item = QGraphicsPathItem(path)
        path_item.setPen(QPen(QBrush(gradient), 4))
        path_item.setOpacity(0)
        
        if from_item.scene():
            from_item.scene().addItem(path_item)
            self.temporary_items['transitions'].append(path_item)
        
        return path_item
    
    def _create_energy_flow_particles(self, from_state: str, to_state: str):
        """Create energy flow particles for transitions."""
        from_item = self.state_graphics_items.get(from_state)
        to_item = self.state_graphics_items.get(to_state)
        
        if not from_item or not to_item or sip.isdeleted(from_item) or sip.isdeleted(to_item):
            return []
        
        from_pos = from_item.pos() + from_item.boundingRect().center()
        to_pos = to_item.pos() + to_item.boundingRect().center()
        
        particle_groups = []
        flow_count = self.current_settings.get('particle_count', 3)
        
        for i in range(flow_count):
            particle_group = []
            
            # Create particle trail
            for j in range(3):  # 3 particles per group
                particle = AnimatableEllipseItem(QRectF(-1.5, -1.5, 3, 3))
                
                # Gradient color based on position in trail
                alpha = 255 - (j * 80)
                color = QColor(self.current_colors['transition_active'])
                color.setAlpha(alpha)
                
                particle.setBrush(QBrush(color))
                particle.setPen(QPen(color.lighter(150), 1))
                particle.setPos(from_pos)
                
                # Calculate staggered timing
                particle._delay = i * 50 + j * 30
                particle._target_pos = to_pos
                
                if from_item.scene():
                    from_item.scene().addItem(particle)
                    self.temporary_items['particles'].append(particle)
                    particle_group.append(particle)
            
            if particle_group:
                particle_groups.append(particle_group)
        
        return particle_groups
    
    def _create_enhanced_event_label(self, event: str, from_state: str, to_state: str):
        """Create an enhanced event label with styling."""
        from_item = self.state_graphics_items.get(from_state)
        to_item = self.state_graphics_items.get(to_state)
        
        if not from_item or not to_item or sip.isdeleted(from_item) or sip.isdeleted(to_item):
            return None
        
        # Calculate midpoint
        from_pos = from_item.pos() + from_item.boundingRect().center()
        to_pos = to_item.pos() + to_item.boundingRect().center()
        mid_pos = QPointF((from_pos.x() + to_pos.x()) / 2, (from_pos.y() + to_pos.y()) / 2 - 20)
        
        # Create text item with enhanced styling
        label = QGraphicsTextItem(event)
        font = QFont("Arial", 11, QFont.Bold)
        label.setFont(font)
        label.setDefaultTextColor(self.current_colors['input_symbol'])
        label.setPos(mid_pos)
        
        # Add background rectangle
        rect = label.boundingRect()
        background = QGraphicsRectItem(rect.adjusted(-5, -2, 5, 2))
        background.setBrush(QBrush(QColor(255, 255, 255, 200)))
        background.setPen(QPen(self.current_colors['input_symbol'], 2))
        background.setParentItem(label)
        background.setZValue(-1)
        
        # Add drop shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(2, 2)
        label.setGraphicsEffect(shadow)
        
        label.setOpacity(0)
        label.setZValue(100)
        
        if from_item.scene():
            from_item.scene().addItem(label)
            self.temporary_items['labels'].append(label)
        
        return label
    
    def _create_enhanced_input_symbol(self, symbol: str, position_index: int):
        """Create an enhanced input symbol visualization."""
        if not self.graphics_scene:
            return None
        
        # Position based on index
        x_pos = 50 + position_index * 40
        y_pos = 50
        
        # Create symbol display with enhanced styling
        symbol_item = QGraphicsTextItem(symbol)
        font = QFont("Courier", 14, QFont.Bold)
        symbol_item.setFont(font)
        symbol_item.setDefaultTextColor(self.current_colors['input_symbol'])
        symbol_item.setPos(x_pos, y_pos)
        
        # Add circular background
        rect = symbol_item.boundingRect()
        circle = QGraphicsEllipseItem(rect.adjusted(-8, -4, 8, 4))
        
        # Create gradient background
        gradient = QRadialGradient(rect.center(), rect.width() / 2 + 8)
        gradient.setColorAt(0, QColor(255, 255, 255, 220))
        gradient.setColorAt(0.7, self.current_colors['input_symbol'].lighter(180))
        gradient.setColorAt(1, self.current_colors['input_symbol'])
        
        circle.setBrush(QBrush(gradient))
        circle.setPen(QPen(self.current_colors['input_symbol'].darker(120), 2))
        circle.setParentItem(symbol_item)
        circle.setZValue(-1)
        
        # Add glow effect
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(15)
        glow.setColor(self.current_colors['input_symbol'])
        glow.setOffset(0, 0)
        symbol_item.setGraphicsEffect(glow)
        
        symbol_item.setOpacity(0)
        symbol_item.setScale(0.5)
        symbol_item.setZValue(200)
        
        self.graphics_scene.addItem(symbol_item)
        self.temporary_items['labels'].append(symbol_item)
        
        return symbol_item
    
    def _create_consumption_particles(self, position_index: int):
        """Create particles for input consumption effect."""
        particles = []
        center_x = 50 + position_index * 40
        center_y = 50
        center = QPointF(center_x, center_y)
        
        particle_count = min(8, self.current_settings['sparkle_count'])
        
        for i in range(particle_count):
            angle = (2 * math.pi * i) / particle_count
            
            particle = AnimatableEllipseItem(QRectF(-1, -1, 2, 2))
            particle.setBrush(QBrush(self.current_colors['input_symbol'].lighter(150)))
            particle.setPen(QPen(self.current_colors['input_symbol'], 1))
            particle.setPos(center)
            
            # Calculate dispersal target
            distance = 25 + random.uniform(-5, 15)
            target_x = center_x + math.cos(angle) * distance
            target_y = center_y + math.sin(angle) * distance
            particle._target_pos = QPointF(target_x, target_y)
            
            if self.graphics_scene:
                self.graphics_scene.addItem(particle)
                self.temporary_items['particles'].append(particle)
                particles.append(particle)
        
        return particles
    
    def _create_variable_display(self, variable_name: str, old_value: any, new_value: any):
        """Create or update variable display with change visualization."""
        if not self.graphics_scene:
            return None
        
        # Position in variable display area
        y_offset = len(self.variable_display_items) * 30 + 100
        
        # Create display item
        display_text = f"{variable_name}: {old_value} → {new_value}"
        var_display = QGraphicsTextItem(display_text)
        
        font = QFont("Consolas", 10, QFont.Bold)
        var_display.setFont(font)
        var_display.setDefaultTextColor(self.current_colors['variable_change'])
        var_display.setPos(20, y_offset)
        
        # Add background panel
        rect = var_display.boundingRect()
        panel = QGraphicsRectItem(rect.adjusted(-5, -2, 5, 2))
        
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, QColor(255, 255, 255, 200))
        gradient.setColorAt(1, QColor(240, 240, 240, 200))
        
        panel.setBrush(QBrush(gradient))
        panel.setPen(QPen(self.current_colors['variable_change'], 1))
        panel.setParentItem(var_display)
        panel.setZValue(-1)
        
        var_display.setOpacity(0)
        var_display.setZValue(150)
        
        self.graphics_scene.addItem(var_display)
        self.temporary_items['labels'].append(var_display)
        self.variable_display_items[variable_name] = var_display
        
        return var_display
    
    def _create_variable_change_particles(self, variable_name: str):
        """Create particles for variable change visualization."""
        particles = []
        
        if variable_name not in self.variable_display_items:
            return particles
        
        display_item = self.variable_display_items[variable_name]
        if sip.isdeleted(display_item):
            return particles
        
        center = display_item.pos() + display_item.boundingRect().center()
        
        for i in range(6):
            particle = AnimatableEllipseItem(QRectF(-1.5, -1.5, 3, 3))
            particle.setBrush(QBrush(self.current_colors['variable_change']))
            particle.setPen(QPen(self.current_colors['variable_change'].lighter(150), 1))
            particle.setPos(center)
            
            # Random dispersal
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(15, 30)
            target_x = center.x() + math.cos(angle) * distance
            target_y = center.y() + math.sin(angle) * distance
            particle._target_pos = QPointF(target_x, target_y)
            
            if self.graphics_scene:
                self.graphics_scene.addItem(particle)
                self.temporary_items['particles'].append(particle)
                particles.append(particle)
        
        return particles
    
    def _create_condition_indicator(self, condition: str, result: bool, state_name: str):
        """Create condition evaluation indicator."""
        state_item = self.state_graphics_items.get(state_name)
        if not state_item or sip.isdeleted(state_item):
            return None
        
        # Position above the state
        state_pos = state_item.pos() + state_item.boundingRect().center()
        indicator_pos = QPointF(state_pos.x(), state_pos.y() - 40)
        
        # Create indicator text
        result_text = "✓" if result else "✗"
        indicator_text = f"{result_text} {condition[:20]}..."
        
        indicator = QGraphicsTextItem(indicator_text)
        font = QFont("Arial", 9, QFont.Bold)
        indicator.setFont(font)
        
        color = self.current_colors['condition_true'] if result else self.current_colors['condition_false']
        indicator.setDefaultTextColor(color)
        indicator.setPos(indicator_pos)
        
        # Add background
        rect = indicator.boundingRect()
        background = QGraphicsRectItem(rect.adjusted(-3, -1, 3, 1))
        background.setBrush(QBrush(QColor(255, 255, 255, 180)))
        background.setPen(QPen(color, 1))
        background.setParentItem(indicator)
        background.setZValue(-1)
        
        indicator.setOpacity(0)
        indicator.setZValue(120)
        
        if state_item.scene():
            state_item.scene().addItem(indicator)
            self.temporary_items['indicators'].append(indicator)
        
        return indicator
    
    def _create_action_indicator(self, action_code: str, state_name: str):
        """Create action execution indicator."""
        state_item = self.state_graphics_items.get(state_name)
        if not state_item or sip.isdeleted(state_item):
            return None
        
        # Position next to the state
        state_pos = state_item.pos() + state_item.boundingRect().center()
        indicator_pos = QPointF(state_pos.x() + 60, state_pos.y())
        
        # Truncate long action code
        display_code = action_code[:30] + "..." if len(action_code) > 30 else action_code
        
        indicator = QGraphicsTextItem(f"⚡ {display_code}")
        font = QFont("Courier", 8, QFont.Bold)
        indicator.setFont(font)
        indicator.setDefaultTextColor(self.current_colors['action_execute'])
        indicator.setPos(indicator_pos)
        
        # Add code-style background
        rect = indicator.boundingRect()
        background = QGraphicsRectItem(rect.adjusted(-4, -2, 4, 2))
        background.setBrush(QBrush(QColor(40, 40, 40, 200)))
        background.setPen(QPen(self.current_colors['action_execute'], 1))
        background.setParentItem(indicator)
        background.setZValue(-1)
        
        indicator.setOpacity(0)
        indicator.setZValue(130)
        
        if state_item.scene():
            state_item.scene().addItem(indicator)
            self.temporary_items['indicators'].append(indicator)
        
        return indicator
    
    def _create_intensive_error_effects(self, state_item):
        """Create intensive error effects for dramatic feedback."""
        if sip.isdeleted(state_item):
            return []
        
        effects = []
        rect = state_item.boundingRect()
        center = state_item.pos() + rect.center()
        
        # Error ring
        error_ring = AnimatableEllipseItem(rect.adjusted(-20, -20, 20, 20))
        error_ring.setPen(QPen(self.current_colors['error'], 5))
        error_ring.setBrush(QBrush(Qt.NoBrush))
        error_ring.setPos(state_item.pos())
        error_ring.setZValue(state_item.zValue() + 1)
        error_ring.setOpacity(0)
        
        if state_item.scene():
            state_item.scene().addItem(error_ring)
            self.temporary_items['effects'].append(error_ring)
            effects.append(error_ring)
        
        # Error sparks
        for i in range(8):
            angle = (2 * math.pi * i) / 8
            spark = QGraphicsLineItem(0, 0, 15, 0)
            spark.setPen(QPen(self.current_colors['error'], 3))
            spark.setPos(center)
            spark.setRotation(math.degrees(angle))
            spark.setZValue(state_item.zValue() + 2)
            spark.setOpacity(0)
            
            if state_item.scene():
                state_item.scene().addItem(spark)
                self.temporary_items['effects'].append(spark)
                effects.append(spark)
        
        return effects
    
    def _create_enhanced_error_message(self, message: str):
        """Create enhanced error message display."""
        if not self.graphics_scene:
            return None
        
        # Center of scene
        scene_rect = self.graphics_scene.sceneRect()
        center = scene_rect.center()
        
        error_msg = QGraphicsTextItem(f"⚠ ERROR: {message}")
        font = QFont("Arial", 16, QFont.Bold)
        error_msg.setFont(font)
        error_msg.setDefaultTextColor(QColor(255, 255, 255))
        
        # Position at center
        msg_rect = error_msg.boundingRect()
        error_msg.setPos(center.x() - msg_rect.width() / 2, center.y() - msg_rect.height() / 2)
        
        # Add dramatic background
        background = QGraphicsRectItem(msg_rect.adjusted(-15, -10, 15, 10))
        
        gradient = QRadialGradient(msg_rect.center(), msg_rect.width() / 2)
        gradient.setColorAt(0, self.current_colors['error'])
        gradient.setColorAt(1, self.current_colors['error'].darker(150))
        
        background.setBrush(QBrush(gradient))
        background.setPen(QPen(QColor(255, 0, 0), 3))
        background.setParentItem(error_msg)
        background.setZValue(-1)
        
        # Add pulsing glow
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(20)
        glow.setColor(self.current_colors['error'])
        glow.setOffset(0, 0)
        error_msg.setGraphicsEffect(glow)
        
        error_msg.setOpacity(0)
        error_msg.setZValue(300)
        
        self.graphics_scene.addItem(error_msg)
        self.temporary_items['messages'].append(error_msg)
        
        return error_msg
    
    def _create_enhanced_success_message(self, message: str):
        """Create enhanced success message with celebration."""
        if not self.graphics_scene:
            return None
        
        scene_rect = self.graphics_scene.sceneRect()
        center = scene_rect.center()
        
        success_msg = QGraphicsTextItem(f"🎉 {message}")
        font = QFont("Arial", 18, QFont.Bold)
        success_msg.setFont(font)
        success_msg.setDefaultTextColor(QColor(255, 255, 255))
        
        # Position at center
        msg_rect = success_msg.boundingRect()
        success_msg.setPos(center.x() - msg_rect.width() / 2, center.y() - msg_rect.height() / 2)
        
        # Add celebration background
        background = QGraphicsRectItem(msg_rect.adjusted(-20, -15, 20, 15))
        
        gradient = QLinearGradient(msg_rect.topLeft(), msg_rect.bottomRight())
        gradient.setColorAt(0, self.current_colors['success'])
        gradient.setColorAt(0.5, self.current_colors['success'].lighter(120))
        gradient.setColorAt(1, self.current_colors['success'])
        
        background.setBrush(QBrush(gradient))
        background.setPen(QPen(self.current_colors['success'].lighter(150), 3))
        background.setParentItem(success_msg)
        background.setZValue(-1)
        
        # Add celebratory glow
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(25)
        glow.setColor(self.current_colors['success'])
        glow.setOffset(0, 0)
        success_msg.setGraphicsEffect(glow)
        
        success_msg.setOpacity(0)
        success_msg.setZValue(300)
        
        self.graphics_scene.addItem(success_msg)
        self.temporary_items['messages'].append(success_msg)
        
        return success_msg
    
    def _create_celebration_effects(self):
        """Create celebration particle effects."""
        if not self.graphics_scene:
            return []
        
        effects = []
        scene_rect = self.graphics_scene.sceneRect()
        
        # Create confetti particles
        confetti_count = min(20, self.current_settings['sparkle_count'] * 2)
        
        for i in range(confetti_count):
            confetti = QGraphicsRectItem(-2, -1, 4, 2)
            
            # Random colors
            colors = [
                self.current_colors['success'],
                self.current_colors['current_state'],
                self.current_colors['transition_active'],
                QColor(255, 215, 0),  # Gold
                QColor(255, 20, 147), # Deep pink
            ]
            color = random.choice(colors)
            confetti.setBrush(QBrush(color))
            confetti.setPen(QPen(color.lighter(120), 1))
            
            # Random starting position (top of scene)
            start_x = random.uniform(scene_rect.left(), scene_rect.right())
            start_y = scene_rect.top() - 20
            confetti.setPos(start_x, start_y)
            
            # Random target (bottom of scene)
            target_x = start_x + random.uniform(-50, 50)
            target_y = scene_rect.bottom() + 20
            confetti._target_pos = QPointF(target_x, target_y)
            
            # Random rotation
            confetti.setRotation(random.uniform(0, 360))
            confetti._rotation_speed = random.uniform(-180, 180)
            
            confetti.setZValue(250)
            
            self.graphics_scene.addItem(confetti)
            self.temporary_items['particles'].append(confetti)
            effects.append([confetti])  # Each confetti in its own group
        
        return effects
    
    def _create_enhanced_breakpoint_effects(self, state_item):
        """Create enhanced breakpoint effects."""
        if sip.isdeleted(state_item):
            return []
        
        effects = []
        rect = state_item.boundingRect()
        
        # Breakpoint indicator ring
        bp_ring = AnimatableEllipseItem(rect.adjusted(-12, -12, 12, 12))
        bp_ring.setPen(QPen(self.current_colors['breakpoint'], 4))
        bp_ring.setBrush(QBrush(Qt.NoBrush))
        bp_ring.setPos(state_item.pos())
        bp_ring.setZValue(state_item.zValue() + 1)
        
        if state_item.scene():
            state_item.scene().addItem(bp_ring)
            self.temporary_items['effects'].append(bp_ring)
            effects.append(bp_ring)
        
        # Breakpoint symbol
        bp_symbol = QGraphicsTextItem("⏸")
        font = QFont("Arial", 20, QFont.Bold)
        bp_symbol.setFont(font)
        bp_symbol.setDefaultTextColor(self.current_colors['breakpoint'])
        
        # Position above state
        state_center = state_item.pos() + rect.center()
        symbol_rect = bp_symbol.boundingRect()
        bp_symbol.setPos(state_center.x() - symbol_rect.width() / 2, state_center.y() - 35)
        bp_symbol.setZValue(state_item.zValue() + 2)
        
        if state_item.scene():
            state_item.scene().addItem(bp_symbol)
            self.temporary_items['indicators'].append(bp_symbol)
            effects.append(bp_symbol)
        
        return effects
    
    def _create_step_indicator(self, step_number: int):
        """Create step number indicator."""
        if not self.graphics_scene:
            return
        
        step_text = QGraphicsTextItem(f"Step: {step_number}")
        font = QFont("Arial", 12, QFont.Bold)
        step_text.setFont(font)
        step_text.setDefaultTextColor(QColor(100, 100, 100))
        step_text.setPos(10, 10)
        step_text.setZValue(200)
        
        # Remove previous step indicator
        for item in self.temporary_items.get('indicators', []):
            if not sip.isdeleted(item) and hasattr(item, '_is_step_indicator'):
                item.scene().removeItem(item)
                self.temporary_items['indicators'].remove(item)
        
        step_text._is_step_indicator = True
        self.graphics_scene.addItem(step_text)
        self.temporary_items['indicators'].append(step_text)
    
    # --- START OF FIX: ADDING MISSING METHODS ---

    def _process_step_queue(self):
        """Placeholder method to process queued animation steps."""
        logger.debug("AnimationManager._process_step_queue called (placeholder).")
        pass

    def clear_animations(self):
        """Stops all active animations and clears temporary items."""
        logger.info("Clearing all active animations and temporary items.")
        # Stop all running animations
        for anim_info in list(self.active_animations.values()):
            if anim_info['animation'].state() == QAbstractAnimation.Running:
                anim_info['animation'].stop()
        self.active_animations.clear()

        # Remove all temporary graphics items from the scene
        for category, items in self.temporary_items.items():
            for item in items:
                if not sip.isdeleted(item) and item.scene():
                    item.scene().removeItem(item)
            items.clear()
        
        self.step_animation_groups.clear()
        self.current_step = 0

    def cleanup_finished_animations(self):
        """Removes references to finished animations and schedules the animation objects for deletion."""
        finished_keys = []
        for key, info in self.active_animations.items():
            # Check if the python wrapper points to a deleted C++ object or if the animation is stopped
            if sip.isdeleted(info['animation']) or info['animation'].state() == QAbstractAnimation.Stopped:
                finished_keys.append(key)

        for key in finished_keys:
            if key in self.active_animations:
                info = self.active_animations.pop(key) # Atomically get the item and remove it
                anim_obj = info.get('animation')
                if anim_obj and not sip.isdeleted(anim_obj):
                    anim_obj.deleteLater() # Safely schedule for deletion

    def _cleanup_item(self, item):
        """Safely removes a temporary graphics item from the scene."""
        if item and not sip.isdeleted(item) and item.scene():
            item.scene().removeItem(item)
            for category_items in self.temporary_items.values():
                if item in category_items:
                    category_items.remove(item)
                    break

    def _execute_animation_group(self, group, group_name, priority=AnimationPriority.NORMAL):
        """Executes a parallel animation group and tracks it."""
        if group.animationCount() == 0:
            return

        self.animation_id_counter += 1
        anim_id = f"{group_name}_{self.animation_id_counter}"
        
        animation_info = {
            'id': anim_id,
            'type': group_name,
            'priority': priority,
            'animation': group,
            'target': group_name
        }
        self.active_animations[anim_id] = animation_info
        # --- FIX: Remove DeleteWhenStopped to allow manual cleanup ---
        group.start()

    def _enhance_state_label(self, state_item, state_name):
        logger.debug(f"Enhancing label for state: {state_name} (placeholder)")
        pass

    def _dim_state_label(self, state_item, state_name):
        logger.debug(f"Dimming label for state: {state_name} (placeholder)")
        pass

    def _create_highlight_entry_animation(self, item):
        anim = QPropertyAnimation(item, b"opacity")
        anim.setDuration(self.current_settings['fade_duration'])
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        return anim

    def _create_particle_animation(self, particle):
        group = QParallelAnimationGroup()
        pos_anim = QPropertyAnimation(particle, b"pos")
        pos_anim.setDuration(self.current_settings['move_duration'])
        pos_anim.setStartValue(particle.pos())
        pos_anim.setEndValue(particle._target_pos)
        pos_anim.setEasingCurve(QEasingCurve.OutQuad)

        fade_anim = QPropertyAnimation(particle, b"opacity")
        fade_anim.setDuration(self.current_settings['move_duration'])
        fade_anim.setStartValue(1.0)
        fade_anim.setEndValue(0.0)
        
        group.addAnimation(pos_anim)
        group.addAnimation(fade_anim)
        group.finished.connect(lambda: self._cleanup_item(particle))
        return group
    
    def _create_state_exit_animation(self, highlight_item):
        anim = QPropertyAnimation(highlight_item, b"opacity")
        anim.setDuration(self.current_settings['fade_duration'])
        anim.setStartValue(1)
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.InCubic)
        anim.finished.connect(lambda: self._cleanup_item(highlight_item))
        return anim

    def _create_exit_particle_effect(self, state_item):
        return self._create_entry_particle_burst(state_item)

    def _create_particle_fade_animation(self, particle):
        return self._create_particle_animation(particle)

    def _create_enhanced_transition_pulse(self, transition_item):
        return QPropertyAnimation() # Placeholder

    def _create_temporary_transition_animation(self, item):
        anim = QPropertyAnimation(item, b"opacity")
        anim.setDuration(self.current_settings['animation_duration'])
        anim.setStartValue(0.8)
        anim.setEndValue(0)
        anim.finished.connect(lambda: self._cleanup_item(item))
        return anim

    def _create_energy_flow_animation(self, particle_group):
        return QParallelAnimationGroup() # Placeholder

    def _create_event_label_animation(self, label_item):
        return self._create_glow_ring_animation(label_item)

    def _create_input_symbol_sequence(self, item):
        return self._create_glow_ring_animation(item)

    def _create_consumption_particle_animation(self, particle):
        return self._create_particle_animation(particle)

    def _create_variable_change_animation(self, item):
        return self._create_glow_ring_animation(item)

    def _create_condition_indicator_animation(self, item):
        return self._create_glow_ring_animation(item)

    def _create_action_execution_animation(self, item):
        return self._create_glow_ring_animation(item)

    def _create_error_effect_animation(self, item):
        return self._create_glow_ring_animation(item)

    def _create_error_message_animation(self, item):
        return self._create_glow_ring_animation(item)

    def _create_success_message_animation(self, item):
        return self._create_glow_ring_animation(item)

    def _create_celebration_animation(self, item_group):
        return QParallelAnimationGroup() # Placeholder

    def _create_breakpoint_animation(self, item):
        return self._create_glow_ring_animation(item)
    
    # --- END OF FIX ---

    # Animation creation methods
    def _create_glow_ring_animation(self, ring_item):
        """Create glow ring animation sequence."""
        if not ring_item or sip.isdeleted(ring_item):
            return None
        
        sequence = QSequentialAnimationGroup()
        
        # Fade in
        fade_in = QPropertyAnimation(ring_item, b"opacity")
        fade_in.setDuration(self.current_settings['fade_duration'])
        fade_in.setStartValue(0)
        fade_in.setEndValue(0.8)
        fade_in.setEasingCurve(QEasingCurve.OutCubic)
        
        # Pulse
        pulse = QPropertyAnimation(ring_item, b"opacity")
        pulse.setDuration(self.current_settings['pulse_duration'])
        pulse.setStartValue(0.8)
        pulse.setEndValue(0.3)
        pulse.setEasingCurve(QEasingCurve.InOutSine)
        pulse.setLoopCount(2)
        
        # Fade out
        fade_out = QPropertyAnimation(ring_item, b"opacity")
        fade_out.setDuration(self.current_settings['fade_duration'])
        fade_out.setStartValue(0.3)
        fade_out.setEndValue(0)
        fade_out.setEasingCurve(QEasingCurve.InCubic)
        
        sequence.addAnimation(fade_in)
        sequence.addAnimation(pulse)
        sequence.addAnimation(fade_out)
        
        # Cleanup on finish
        sequence.finished.connect(lambda: self._cleanup_item(ring_item))
        
        return sequence