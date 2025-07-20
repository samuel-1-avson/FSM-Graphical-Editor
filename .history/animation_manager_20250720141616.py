# enhanced_animation_manager.py
"""
Enhanced Animation Manager that provides rich visual animations for FSM simulation,
building upon your existing animation framework.
"""

import logging
from typing import Dict, List, Optional, Tuple
from PyQt5.QtCore import (QObject, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, 
                          QSequentialAnimationGroup, pyqtSlot, QTimer, QPointF, QRectF)
from PyQt5.QtGui import QColor, QPen, QBrush, QFont, QPainterPath
from PyQt5.QtWidgets import (QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsPathItem,
                            QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QGraphicsItem)
import sip
from enum import Enum

logger = logging.getLogger(__name__)

class AnimationType(Enum):
    STATE_ENTRY = "state_entry"
    STATE_EXIT = "state_exit"
    TRANSITION = "transition"
    INPUT_CONSUME = "input_consume"
    ERROR = "error"
    SUCCESS = "success"

class AnimationManager(QObject):
    """
    Enhanced animation manager that provides comprehensive visual feedback
    for FSM simulation with rich effects and customizable animations.
    """
    
    def __init__(self, graphics_scene, main_window=None):
        super().__init__()
        self.graphics_scene = graphics_scene
        self.main_window = main_window
        
        # Animation tracking
        self.active_animations = []
        self.animation_groups = {}
        
        # Visual elements
        self.temporary_items = []  # Items to be cleaned up
        self.state_highlights = {}  # state_name -> highlight_item
        self.transition_pulses = {}  # transition_id -> pulse_item
        
        # Graphics item mappings
        self.state_graphics_items = {}  # state_name -> graphics_item
        self.transition_graphics_items = {}  # (from, to, event) -> graphics_item
        
        # Animation settings
        self.animation_duration = 800
        self.pulse_duration = 400
        self.fade_duration = 300
        self.move_duration = 600
        
        # Colors and styles
        self.colors = {
            'current_state': QColor(255, 215, 0, 180),     # Gold
            'previous_state': QColor(200, 200, 200, 100),   # Gray
            'transition_active': QColor(0, 255, 0, 150),    # Green
            'transition_path': QColor(255, 165, 0, 200),    # Orange
            'input_symbol': QColor(100, 149, 237, 200),     # Cornflower blue
            'error': QColor(255, 69, 0, 180),               # Red-orange
            'success': QColor(50, 205, 50, 180),            # Lime green
            'breakpoint': QColor(255, 0, 0, 150),           # Red
        }
        
        # Cleanup timer
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self.cleanup_finished_animations)
        self.cleanup_timer.start(1000)  # Cleanup every second
    
    def register_graphics_items(self, state_items: Dict, transition_items: Dict):
        """Register graphics items for animation."""
        self.state_graphics_items.update(state_items)
        self.transition_graphics_items.update(transition_items)
        logger.debug(f"Registered {len(state_items)} states and {len(transition_items)} transitions")
    
    def cleanup_finished_animations(self):
        """Clean up finished animations and temporary items."""
        # Remove finished animations
        self.active_animations = [
            anim for anim in self.active_animations 
            if anim.state() == QPropertyAnimation.Running
        ]
        
        # Remove temporary items that are no longer needed
        items_to_remove = []
        for item in self.temporary_items:
            if not sip.isdeleted(item) and hasattr(item, '_cleanup_time'):
                if hasattr(item, '_animation_finished') and item._animation_finished:
                    items_to_remove.append(item)
        
        for item in items_to_remove:
            if not sip.isdeleted(item) and item.scene():
                item.scene().removeItem(item)
            self.temporary_items.remove(item)
    
    @pyqtSlot(str)
    def animate_state_entry(self, state_name: str):
        """Animate entering a state with glow and pulse effects."""
        if state_name not in self.state_graphics_items:
            logger.warning(f"No graphics item found for state: {state_name}")
            return
        
        state_item = self.state_graphics_items[state_name]
        if sip.isdeleted(state_item):
            return
        
        # Remove any existing highlight
        if state_name in self.state_highlights:
            old_highlight = self.state_highlights[state_name]
            if not sip.isdeleted(old_highlight) and old_highlight.scene():
                old_highlight.scene().removeItem(old_highlight)
        
        # Create highlight effect
        highlight = self._create_state_highlight(state_item, self.colors['current_state'])
        if highlight:
            self.state_highlights[state_name] = highlight
            
            # Animate highlight appearance
            self._animate_highlight_entry(highlight)
        
        # Add glow effect to original item
        self._add_glow_effect(state_item, self.colors['current_state'])
        
        # Create pulse animation
        self._create_pulse_animation(state_item)
        
        logger.debug(f"Animated entry for state: {state_name}")
    
    @pyqtSlot(str)
    def animate_state_exit(self, state_name: str):
        """Animate exiting a state."""
        if state_name not in self.state_graphics_items:
            return
        
        state_item = self.state_graphics_items[state_name]
        if sip.isdeleted(state_item):
            return
        
        # Change highlight to "previous state" color
        if state_name in self.state_highlights:
            highlight = self.state_highlights[state_name]
            if not sip.isdeleted(highlight):
                self._animate_color_change(highlight, self.colors['previous_state'])
        
        # Remove glow effect gradually
        self._remove_glow_effect(state_item)
        
        logger.debug(f"Animated exit for state: {state_name}")
    
    @pyqtSlot(str, str, str)
    def animate_transition(self, from_state: str, to_state: str, event: str):
        """Animate a transition between states."""
        # Find the transition graphics item
        transition_key = (from_state, to_state, event)
        transition_item = self.transition_graphics_items.get(transition_key)
        
        if not transition_item or sip.isdeleted(transition_item):
            # Create a temporary visual transition
            self._create_temporary_transition_animation(from_state, to_state, event)
            return
        
        # Animate the existing transition item
        self._animate_transition_pulse(transition_item)
        
        # Create moving particle effect along the transition
        self._create_transition_particle_effect(from_state, to_state)
        
        logger.debug(f"Animated transition: {from_state} -> {to_state} on {event}")
    
    @pyqtSlot(str, int)
    def animate_input_symbol(self, symbol: str, position_index: int):
        """Animate the consumption of an input symbol."""
        # Create a floating text item for the input symbol
        text_item = QGraphicsTextItem(symbol)
        text_item.setFont(QFont("Arial", 16, QFont.Bold))
        text_item.setDefaultTextColor(self.colors['input_symbol'])
        
        # Position it at the top of the scene
        scene_rect = self.graphics_scene.sceneRect()
        start_pos = QPointF(scene_rect.left() + 50 + position_index * 30, scene_rect.top() + 20)
        text_item.setPos(start_pos)
        
        # Add glow effect
        glow_effect = QGraphicsDropShadowEffect()
        glow_effect.setBlurRadius(15)
        glow_effect.setColor(self.colors['input_symbol'])
        glow_effect.setOffset(0, 0)
        text_item.setGraphicsEffect(glow_effect)
        
        self.graphics_scene.addItem(text_item)
        self.temporary_items.append(text_item)
        
        # Create animation sequence
        animation_group = QSequentialAnimationGroup()
        
        # 1. Pulse in
        pulse_in = QPropertyAnimation(text_item, b"scale")
        pulse_in.setDuration(200)
        pulse_in.setStartValue(0.5)
        pulse_in.setEndValue(1.2)
        pulse_in.setEasingCurve(QEasingCurve.OutElastic)
        
        # 2. Hold
        hold = QPropertyAnimation(text_item, b"scale")
        hold.setDuration(300)
        hold.setStartValue(1.2)
        hold.setEndValue(1.0)
        
        # 3. Fade and move down
        fade_move = QParallelAnimationGroup()
        
        opacity_anim = QPropertyAnimation(text_item, b"opacity")
        opacity_anim.setDuration(self.fade_duration)
        opacity_anim.setStartValue(1.0)
        opacity_anim.setEndValue(0.0)
        
        move_anim = QPropertyAnimation(text_item, b"pos")
        move_anim.setDuration(self.fade_duration)
        move_anim.setStartValue(start_pos)
        move_anim.setEndValue(start_pos + QPointF(0, 50))
        move_anim.setEasingCurve(QEasingCurve.InQuad)
        
        fade_move.addAnimation(opacity_anim)
        fade_move.addAnimation(move_anim)
        
        # Combine animations
        animation_group.addAnimation(pulse_in)
        animation_group.addAnimation(hold)
        animation_group.addAnimation(fade_move)
        
        # Mark for cleanup when finished
        text_item._animation_finished = False
        animation_group.finished.connect(lambda: setattr(text_item, '_animation_finished', True))
        
        animation_group.start()
        self.active_animations.append(animation_group)
        
        logger.debug(f"Animated input symbol: {symbol}")
    
    def animate_error(self, state_name: str = None, message: str = ""):
        """Animate an error condition."""
        if state_name and state_name in self.state_graphics_items:
            state_item = self.state_graphics_items[state_name]
            if not sip.isdeleted(state_item):
                # Create red pulsing effect
                self._create_error_pulse(state_item)
        
        # Show error message as floating text
        if message:
            self._show_floating_message(message, self.colors['error'])
    
    def animate_success(self, message: str = "Simulation Complete"):
        """Animate successful completion."""
        self._show_floating_message(message, self.colors['success'], duration=2000)
        
        # Add sparkle effect to the scene
        self._create_success_sparkles()
    
    def animate_breakpoint_hit(self, state_name: str):
        """Animate a breakpoint being hit."""
        if state_name not in self.state_graphics_items:
            return
        
        state_item = self.state_graphics_items[state_name]
        if sip.isdeleted(state_item):
            return
        
        # Create breakpoint indicator
        self._create_breakpoint_indicator(state_item)
        
        logger.debug(f"Animated breakpoint hit at state: {state_name}")
    
    def _create_state_highlight(self, state_item, color: QColor):
        """Create a highlight effect around a state item."""
        if sip.isdeleted(state_item):
            return None
        
        # Get the bounding rect of the state item
        rect = state_item.boundingRect()
        
        # Create highlight ellipse slightly larger
        highlight = QGraphicsEllipseItem(rect.adjusted(-5, -5, 5, 5))
        highlight.setBrush(QBrush(color))
        highlight.setPen(QPen(color.darker(120), 2))
        highlight.setPos(state_item.pos())
        highlight.setZValue(state_item.zValue() - 1)  # Behind the state
        
        # Add to scene
        if state_item.scene():
            state_item.scene().addItem(highlight)
            self.temporary_items.append(highlight)
        
        return highlight
    
    def _animate_highlight_entry(self, highlight_item):
        """Animate the appearance of a highlight."""
        if sip.isdeleted(highlight_item):
            return
        
        # Start invisible and scale from small
        highlight_item.setOpacity(0)
        highlight_item.setScale(0.5)
        
        # Animate to full visibility and size
        opacity_anim = QPropertyAnimation(highlight_item, b"opacity")
        opacity_anim.setDuration(self.fade_duration)
        opacity_anim.setStartValue(0)
        opacity_anim.setEndValue(0.7)
        
        scale_anim = QPropertyAnimation(highlight_item, b"scale")
        scale_anim.setDuration(self.fade_duration)
        scale_anim.setStartValue(0.5)
        scale_anim.setEndValue(1.0)
        scale_anim.setEasingCurve(QEasingCurve.OutBack)
        
        anim_group = QParallelAnimationGroup()
        anim_group.addAnimation(opacity_anim)
        anim_group.addAnimation(scale_anim)
        
        anim_group.start()
        self.active_animations.append(anim_group)
    
    def _add_glow_effect(self, item, color: QColor):
        """Add a glow effect to an item."""
        if sip.isdeleted(item):
            return
        
        glow_effect = QGraphicsDropShadowEffect()
        glow_effect.setBlurRadius(20)
        glow_effect.setColor(color)
        glow_effect.setOffset(0, 0)
        item.setGraphicsEffect(glow_effect)
    
    def _remove_glow_effect(self, item):
        """Remove glow effect from an item."""
        if sip.isdeleted(item):
            return
        
        # Fade out the glow effect
        current_effect = item.graphicsEffect()
        if current_effect:
            opacity_effect = QGraphicsOpacityEffect()
            opacity_effect.setOpacity(1.0)
            item.setGraphicsEffect(opacity_effect)
            
            fade_anim = QPropertyAnimation(opacity_effect, b"opacity")
            fade_anim.setDuration(self.fade_duration)
            fade_anim.setStartValue(1.0)
            fade_anim.setEndValue(0.0)
            fade_anim.finished.connect(lambda: item.setGraphicsEffect(None))
            fade_anim.start()
            
            self.active_animations.append(fade_anim)
    
    def _create_pulse_animation(self, item):
        """Create a pulse animation for an item."""
        if sip.isdeleted(item):
            return
        
        pulse_anim = QPropertyAnimation(item, b"scale")
        pulse_anim.setDuration(self.pulse_duration)
        pulse_anim.setStartValue(1.0)
        pulse_anim.setKeyValueAt(0.5, 1.1)
        pulse_anim.setEndValue(1.0)
        pulse_anim.setEasingCurve(QEasingCurve.InOutSine)
        pulse_anim.setLoopCount(2)  # Pulse twice
        
        pulse_anim.start()
        self.active_animations.append(pulse_anim)
    
    def _animate_color_change(self, item, new_color: QColor):
        """Animate changing the color of an item."""
        if sip.isdeleted(item):
            return
        
        # Create a custom animation for color transition
        color_anim = QPropertyAnimation(item, b"opacity")
        color_anim.setDuration(self.fade_duration)
        color_anim.setStartValue(0.7)
        color_anim.setEndValue(0.4)
        
        # Change the brush color immediately and fade
        if hasattr(item, 'setBrush'):
            item.setBrush(QBrush(new_color))
        
        color_anim.start()
        self.active_animations.append(color_anim)
    
    def _animate_transition_pulse(self, transition_item):
        """Animate a pulse effect on a transition."""
        if sip.isdeleted(transition_item):
            return
        
        # Store original pen
        original_pen = transition_item.pen()
        
        # Create pulsing pen animation
        pulse_pen = QPen(self.colors['transition_active'], original_pen.width() * 2)
        transition_item.setPen(pulse_pen)
        
        # Animate pen width back to normal
        width_anim = QPropertyAnimation(transition_item, b"opacity")
        width_anim.setDuration(self.pulse_duration)
        width_anim.setStartValue(1.0)
        width_anim.setEndValue(0.8)
        width_anim.finished.connect(lambda: transition_item.setPen(original_pen))
        
        width_anim.start()
        self.active_animations.append(width_anim)
    
    def _create_temporary_transition_animation(self, from_state: str, to_state: str, event: str):
        """Create a temporary visual transition when no graphics item exists."""
        from_item = self.state_graphics_items.get(from_state)
        to_item = self.state_graphics_items.get(to_state)
        
        if not from_item or not to_item or sip.isdeleted(from_item) or sip.isdeleted(to_item):
            return
        
        # Create a temporary path from source to destination
        path = QPainterPath()
        from_pos = from_item.pos() + from_item.boundingRect().center()
        to_pos = to_item.pos() + to_item.boundingRect().center()
        
        path.moveTo(from_pos)
        
        # Create a curved path
        control_point = QPointF(
            (from_pos.x() + to_pos.x()) / 2,
            min(from_pos.y(), to_pos.y()) - 50
        )
        path.quadTo(control_point, to_pos)
        
        # Create path item
        path_item = QGraphicsPathItem(path)
        path_item.setPen(QPen(self.colors['transition_path'], 3))
        path_item.setOpacity(0)
        
        self.graphics_scene.addItem(path_item)
        self.temporary_items.append(path_item)
        
        # Animate path appearance and disappearance
        self._animate_temporary_path(path_item)
        
        # Create event label
        self._create_event_label(event, control_point)
    
    def _animate_temporary_path(self, path_item):
        """Animate a temporary path."""
        if sip.isdeleted(path_item):
            return
        
        # Fade in
        fade_in = QPropertyAnimation(path_item, b"opacity")
        fade_in.setDuration(200)
        fade_in.setStartValue(0)
        fade_in.setEndValue(0.8)
        
        # Hold
        hold = QPropertyAnimation(path_item, b"opacity")
        hold.setDuration(400)
        hold.setStartValue(0.8)
        hold.setEndValue(0.8)
        
        # Fade out
        fade_out = QPropertyAnimation(path_item, b"opacity")
        fade_out.setDuration(300)
        fade_out.setStartValue(0.8)
        fade_out.setEndValue(0)
        
        # Sequential animation
        seq_anim = QSequentialAnimationGroup()
        seq_anim.addAnimation(fade_in)
        seq_anim.addAnimation(hold)
        seq_anim.addAnimation(fade_out)
        
        path_item._animation_finished = False
        seq_anim.finished.connect(lambda: setattr(path_item, '_animation_finished', True))
        
        seq_anim.start()
        self.active_animations.append(seq_anim)
    
    def _create_event_label(self, event: str, position: QPointF):
        """Create a floating event label."""
        label = QGraphicsTextItem(event)
        label.setFont(QFont("Arial", 12, QFont.Bold))
        label.setDefaultTextColor(self.colors['transition_path'])
        label.setPos(position - QPointF(len(event) * 3, 10))
        
        # Add background
        bg_rect = label.boundingRect().adjusted(-5, -2, 5, 2)
        bg_item = QGraphicsEllipseItem(bg_rect)
        bg_item.setBrush(QBrush(QColor(255, 255, 255, 200)))
        bg_item.setPen(QPen(self.colors['transition_path'], 1))
        bg_item.setPos(label.pos())
        bg_item.setZValue(label.zValue() - 1)
        
        self.graphics_scene.addItem(bg_item)
        self.graphics_scene.addItem(label)
        self.temporary_items.extend([bg_item, label])
        
        # Animate label
        self._animate_floating_label(label, bg_item)
    
    def _animate_floating_label(self, label, background):
        """Animate a floating label."""
        # Animate both items together
        items = [label, background]
        
        for item in items:
            if sip.isdeleted(item):
                continue
                
            # Scale animation
            scale_anim = QPropertyAnimation(item, b"scale")
            scale_anim.setDuration(600)
            scale_anim.setStartValue(0.5)
            scale_anim.setKeyValueAt(0.3, 1.2)
            scale_anim.setEndValue(0.8)
            scale_anim.setEasingCurve(QEasingCurve.OutElastic)
            
            # Opacity animation
            opacity_anim = QPropertyAnimation(item, b"opacity")
            opacity_anim.setDuration(800)
            opacity_anim.setStartValue(0)
            opacity_anim.setKeyValueAt(0.2, 1.0)
            opacity_anim.setKeyValueAt(0.8, 1.0)
            opacity_anim.setEndValue(0)
            
            # Combine animations
            item_anim = QParallelAnimationGroup()
            item_anim.addAnimation(scale_anim)
            item_anim.addAnimation(opacity_anim)
            
            item._animation_finished = False
            item_anim.finished.connect(lambda i=item: setattr(i, '_animation_finished', True))
            
            item_anim.start()
            self.active_animations.append(item_anim)
    
    def _create_transition_particle_effect(self, from_state: str, to_state: str):
        """Create moving particles along a transition."""
        from_item = self.state_graphics_items.get(from_state)
        to_item = self.state_graphics_items.get(to_state)
        
        if not from_item or not to_item or sip.isdeleted(from_item) or sip.isdeleted(to_item):
            return
        
        from_pos = from_item.pos() + from_item.boundingRect().center()
        to_pos = to_item.pos() + to_item.boundingRect().center()
        
        # Create multiple particles
        for i in range(3):
            particle = QGraphicsEllipseItem(-3, -3, 6, 6)
            particle.setBrush(QBrush(self.colors['transition_active']))
            particle.setPen(QPen(self.colors['transition_active'].lighter(150), 1))
            particle.setPos(from_pos)
            
            self.graphics_scene.addItem(particle)
            self.temporary_items.append(particle)
            
            # Animate particle movement
            self._animate_particle_movement(particle, from_pos, to_pos, i * 100)
    
    def _animate_particle_movement(self, particle, start_pos: QPointF, end_pos: QPointF, delay: int):
        """Animate a single particle movement."""
        if sip.isdeleted(particle):
            return
        
        # Create movement animation
        move_anim = QPropertyAnimation(particle, b"pos")
        move_anim.setDuration(self.move_duration)
        move_anim.setStartValue(start_pos)
        move_anim.setEndValue(end_pos)
        move_anim.setEasingCurve(QEasingCurve.OutQuad)
        
        # Fade animation
        fade_anim = QPropertyAnimation(particle, b"opacity")
        fade_anim.setDuration(self.move_duration)
        fade_anim.setStartValue(1.0)
        fade_anim.setEndValue(0.0)
        
        # Combine animations
        particle_anim = QParallelAnimationGroup()
        particle_anim.addAnimation(move_anim)
        particle_anim.addAnimation(fade_anim)
        
        # Add delay if specified
        if delay > 0:
            QTimer.singleShot(delay, particle_anim.start)
        else:
            particle_anim.start()
        
        particle._animation_finished = False
        particle_anim.finished.connect(lambda: setattr(particle, '_animation_finished', True))
        
        self.active_animations.append(particle_anim)
    
    def _create_error_pulse(self, state_item):
        """Create an error pulse effect."""
        if sip.isdeleted(state_item):
            return
        
        # Create error overlay
        rect = state_item.boundingRect()
        error_overlay = QGraphicsEllipseItem(rect.adjusted(-2, -2, 2, 2))
        error_overlay.setBrush(QBrush(self.colors['error']))
        error_overlay.setPen(QPen(self.colors['error'].darker(150), 2))
        error_overlay.setPos(state_item.pos())
        error_overlay.setZValue(state_item.zValue() + 1)
        
        self.graphics_scene.addItem(error_overlay)
        self.temporary_items.append(error_overlay)
        
        # Create pulsing animation
        pulse_anim = QPropertyAnimation(error_overlay, b"scale")
        pulse_anim.setDuration(300)
        pulse_anim.setStartValue(1.0)
        pulse_anim.setKeyValueAt(0.5, 1.3)
        pulse_anim.setEndValue(1.0)
        pulse_anim.setLoopCount(4)  # Pulse 4 times
        
        # Fade out animation
        fade_anim = QPropertyAnimation(error_overlay, b"opacity")
        fade_anim.setDuration(1200)
        fade_anim.setStartValue(0.8)
        fade_anim.setEndValue(0.0)
        
        # Sequential animation
        error_seq = QSequentialAnimationGroup()
        error_seq.addAnimation(pulse_anim)
        error_seq.addAnimation(fade_anim)
        
        error_overlay._animation_finished = False
        error_seq.finished.connect(lambda: setattr(error_overlay, '_animation_finished', True))
        
        error_seq.start()
        self.active_animations.append(error_seq)
    
    def _show_floating_message(self, message: str, color: QColor, duration: int = 1500):
        """Show a floating message in the center of the scene."""
        scene_rect = self.graphics_scene.sceneRect()
        center = scene_rect.center()
        
        # Create message text
        text_item = QGraphicsTextItem(message)
        text_item.setFont(QFont("Arial", 18, QFont.Bold))
        text_item.setDefaultTextColor(color)
        
        # Center the text
        text_rect = text_item.boundingRect()
        text_item.setPos(center - text_rect.center())
        
        # Create background
        bg_rect = text_rect.adjusted(-15, -10, 15, 10)
        bg_item = QGraphicsEllipseItem(bg_rect)
        bg_item.setBrush(QBrush(QColor(0, 0, 0, 150)))
        bg_item.setPen(QPen(color, 2))
        bg_item.setPos(text_item.pos())
        bg_item.setZValue(text_item.zValue() - 1)
        
        self.graphics_scene.addItem(bg_item)
        self.graphics_scene.addItem(text_item)
        self.temporary_items.extend([bg_item, text_item])
        
        # Animate message
        for item in [bg_item, text_item]:
            # Scale in
            scale_in = QPropertyAnimation(item, b"scale")
            scale_in.setDuration(300)
            scale_in.setStartValue(0.2)
            scale_in.setEndValue(1.0)
            scale_in.setEasingCurve(QEasingCurve.OutBack)
            
            # Hold
            hold = QPropertyAnimation(item, b"scale")
            hold.setDuration(duration - 600)
            hold.setStartValue(1.0)
            hold.setEndValue(1.0)
            
            # Scale out
            scale_out = QPropertyAnimation(item, b"scale")
            scale_out.setDuration(300)
            scale_out.setStartValue(1.0)
            scale_out.setEndValue(0.2)
            scale_out.setEasingCurve(QEasingCurve.InBack)
            
            # Combine animations
            seq_anim = QSequentialAnimationGroup()
            seq_anim.addAnimation(scale_in)
            seq_anim.addAnimation(hold)
            seq_anim.addAnimation(scale_out)
            
            item._animation_finished = False
            seq_anim.finished.connect(lambda i=item: setattr(i, '_animation_finished', True))
            
            seq_anim.start()
            self.active_animations.append(seq_anim)
    
    def _create_success_sparkles(self):
        """Create sparkle effects for success animation."""
        scene_rect = self.graphics_scene.sceneRect()
        
        # Create multiple sparkle particles
        for i in range(10):
            sparkle = QGraphicsEllipseItem(-2, -2, 4, 4)
            sparkle.setBrush(QBrush(self.colors['success']))
            sparkle.setPen(QPen(self.colors['success'].lighter(200), 1))
            
            # Random position around the scene
            import random
            x = random.uniform(scene_rect.left() + 50, scene_rect.right() - 50)
            y = random.uniform(scene_rect.top() + 50, scene_rect.bottom() - 50)
            sparkle.setPos(x, y)
            
            self.graphics_scene.addItem(sparkle)
            self.temporary_items.append(sparkle)
            
            # Animate sparkle
            self._animate_sparkle(sparkle, random.randint(0, 500))
    
    def _animate_sparkle(self, sparkle, delay: int):
        """Animate a single sparkle."""
        if sip.isdeleted(sparkle):
            return
        
        # Scale animation
        scale_anim = QPropertyAnimation(sparkle, b"scale")
        scale_anim.setDuration(800)
        scale_anim.setStartValue(0.1)
        scale_anim.setKeyValueAt(0.3, 2.0)
        scale_anim.setKeyValueAt(0.7, 1.5)
        scale_anim.setEndValue(0.1)
        scale_anim.setEasingCurve(QEasingCurve.OutBounce)
        
        # Opacity animation
        opacity_anim = QPropertyAnimation(sparkle, b"opacity")
        opacity_anim.setDuration(800)
        opacity_anim.setStartValue(0)
        opacity_anim.setKeyValueAt(0.2, 1.0)
        opacity_anim.setKeyValueAt(0.8, 1.0)
        opacity_anim.setEndValue(0)
        
        # Combine animations
        sparkle_anim = QParallelAnimationGroup()
        sparkle_anim.addAnimation(scale_anim)
        sparkle_anim.addAnimation(opacity_anim)
        
        sparkle._animation_finished = False
        sparkle_anim.finished.connect(lambda: setattr(sparkle, '_animation_finished', True))
        
        # Add delay
        if delay > 0:
            QTimer.singleShot(delay, sparkle_anim.start)
        else:
            sparkle_anim.start()
        
        self.active_animations.append(sparkle_anim)
    
    def _create_breakpoint_indicator(self, state_item):
        """Create a breakpoint indicator."""
        if sip.isdeleted(state_item):
            return
        
        # Create breakpoint symbol (octagon)
        symbol = QGraphicsEllipseItem(-8, -8, 16, 16)
        symbol.setBrush(QBrush(self.colors['breakpoint']))
        symbol.setPen(QPen(QColor(255, 255, 255), 2))
        
        # Position at top-right of state
        state_rect = state_item.boundingRect()
        symbol.setPos(state_item.pos() + QPointF(state_rect.width() - 8, 8))
        symbol.setZValue(state_item.zValue() + 2)
        
        self.graphics_scene.addItem(symbol)
        self.temporary_items.append(symbol)
        
        # Create pulsing animation
        pulse = QPropertyAnimation(symbol, b"scale")
        pulse.setDuration(600)
        pulse.setStartValue(1.0)
        pulse.setKeyValueAt(0.5, 1.4)
        pulse.setEndValue(1.0)
        pulse.setLoopCount(-1)  # Infinite loop
        pulse.setEasingCurve(QEasingCurve.InOutSine)
        
        pulse.start()
        self.active_animations.append(pulse)
        
        # Store for later removal
        symbol._is_breakpoint = True
    
    def clear_animations(self):
        """Clear all active animations and temporary items."""
        # Stop all active animations
        for animation in self.active_animations:
            if animation.state() == QPropertyAnimation.Running:
                animation.stop()
        
        self.active_animations.clear()
        
        # Remove all temporary items
        for item in self.temporary_items[:]:
            if not sip.isdeleted(item) and item.scene():
                item.scene().removeItem(item)
        
        self.temporary_items.clear()
        
        # Clear highlights
        for highlight in self.state_highlights.values():
            if not sip.isdeleted(highlight) and highlight.scene():
                highlight.scene().removeItem(highlight)
        
        self.state_highlights.clear()
        self.transition_pulses.clear()
        
        logger.debug("Cleared all animations and temporary items")
    
    def set_animation_speed(self, speed_factor: float):
        """Set animation speed (1.0 = normal, 0.5 = half speed, 2.0 = double speed)."""
        speed_factor = max(0.1, min(5.0, speed_factor))  # Clamp between 0.1 and 5.0
        
        self.animation_duration = int(800 / speed_factor)
        self.pulse_duration = int(400 / speed_factor)
        self.fade_duration = int(300 / speed_factor)
        self.move_duration = int(600 / speed_factor)
        
        logger.debug(f"Animation speed set to {speed_factor}x")
    
    def get_animation_settings(self) -> Dict:
        """Get current animation settings."""
        return {
            'animation_duration': self.animation_duration,
            'pulse_duration': self.pulse_duration,
            'fade_duration': self.fade_duration,
            'move_duration': self.move_duration,
            'colors': {name: color.name() for name, color in self.colors.items()},
            'active_animations_count': len(self.active_animations),
            'temporary_items_count': len(self.temporary_items)
        }