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

class EnhancedAnimationManager(QObject):
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