# enhanced_animation_manager.py
"""
Significantly Enhanced Animation Manager for FSM simulation with advanced visual effects,
synchronized timing, and rich feedback systems.
"""

import logging
from typing import Dict, List, Optional, Tuple, Callable
from PyQt5.QtCore import (QObject, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, 
                          QSequentialAnimationGroup, pyqtSlot, QTimer, QPointF, QRectF, 
                          pyqtSignal, QVariantAnimation, QAbstractAnimation)
from PyQt5.QtGui import QColor, QPen, QBrush, QFont, QPainterPath, QLinearGradient, QRadialGradient
from PyQt5.QtWidgets import (QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsPathItem,
                            QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QGraphicsItem,
                            QGraphicsRectItem, QGraphicsLineItem, QGraphicsProxyWidget)
import sip
from enum import Enum
import math
import random

logger = logging.getLogger(__name__)

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

class EnhancedAnimationManager(QObject):
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
        ring = QGraphicsEllipseItem(rect.adjusted(-15, -15, 15, 15))
        
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
        highlight = QGraphicsEllipseItem(rect.adjusted(-8, -8, 8, 8))
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
            
            particle = QGraphicsEllipseItem(-2, -2, 4, 4)
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
        flow_count = self.