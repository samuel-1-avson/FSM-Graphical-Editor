# fsm_designer_project/animation_manager.py

import logging
from PyQt5.QtCore import QObject, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, pyqtSlot
from PyQt5.QtGui import QColor, QPen
from PyQt5.QtWidgets import QGraphicsEllipseItem
import sip

from .graphics_items import GraphicsStateItem, GraphicsTransitionItem
from .config import COLOR_ACCENT_SECONDARY
from.graphics_items import TransitionPulseItem

logger = logging.getLogger(__name__)

class AnimationManager(QObject):
    """Manages all visual animations on the FSM canvas."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.mw = main_window
        self.active_animations = []

    def cleanup_finished_animations(self):
        """Removes finished animations from the active list."""
        self.active_animations = [anim for anim in self.active_animations if anim.state() == QPropertyAnimation.Running]

    @pyqtSlot(GraphicsStateItem)
    def animate_state_entry(self, state_item: GraphicsStateItem):
        """
        Triggers a 'pulse' or 'glow' animation on a state item when it becomes active.
        """
        if not state_item or not hasattr(state_item, 'shadow_effect'):
            return

        if sip.isdeleted(state_item.shadow_effect):
            return

        glow_anim = QPropertyAnimation(state_item.shadow_effect, b"color")
        glow_anim.setDuration(400)
        glow_anim.setLoopCount(2) # Pulse twice
        
        start_color = QColor(state_item.shadow_effect.color())
        glow_color = QColor(COLOR_ACCENT_SECONDARY).lighter(120)
        glow_color.setAlpha(200)

        glow_anim.setKeyValueAt(0, start_color)
        glow_anim.setKeyValueAt(0.5, glow_color)
        glow_anim.setKeyValueAt(1, start_color)
        glow_anim.setEasingCurve(QEasingCurve.InOutQuad)
        
        glow_anim.finished.connect(self.cleanup_finished_animations)
        self.active_animations.append(glow_anim)
        glow_anim.start()
        logger.debug(f"Started entry animation for state '{state_item.text_label}'")


    @pyqtSlot(GraphicsStateItem, GraphicsStateItem, str)
    def animate_transition(self, source_item: GraphicsStateItem, target_item: GraphicsStateItem, event: str):
        """
        Finds the corresponding transition item on the scene and triggers its animation.
        """
        if not source_item or not target_item:
            return
            
        if sip.isdeleted(source_item):
             return
             
        transition_to_animate = None
        # Find the specific transition in the scene that matches the event
        for item in source_item.scene().items():
            if isinstance(item, GraphicsTransitionItem):
                if (item.start_item == source_item and
                    item.end_item == target_item and
                    item.event_str == event):
                    transition_to_animate = item
                    break
        
        if transition_to_animate and hasattr(transition_to_animate, 'start_pulse_animation'):
            transition_to_animate.start_pulse_animation()
            logger.debug(f"Started animation for transition from '{source_item.text_label}' to '{target_item.text_label}'")
        else:
            logger.warning(f"Could not find a visual transition to animate for: {source_item.text_label} -> {target_item.text_label} on event '{event}'")