# fsm_designer_project/ui/animation_manager.py
from __future__ import annotations

from typing import Dict, Tuple, Optional, List, Any

from PyQt6.QtCore import (
    QObject, QEasingCurve, QPropertyAnimation, QVariantAnimation, QPointF, QRectF, pyqtSlot, Qt
)
from PyQt6.QtWidgets import (
    QGraphicsScene, QGraphicsItem, QGraphicsEllipseItem, QGraphicsView, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QColor, QPen, QBrush, QPainterPath

try:
    from ..utils.theme_config import theme_config
except Exception:
    theme_config = None


def _theme_color(name: str, fallback: str) -> str:
    try:
        val = getattr(theme_config, name, None)
        return val if val else fallback
    except Exception:
        return fallback


class AnimationManager(QObject):
    """
    Central controller for canvas animations:
    - State entry: ripple + glow + bounce
    - Transition: dash highlight + moving token
    - Auto pan to active item
    - Reduce motion support
    """
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        # The scene and view are now set via methods after initialization
        self.graphics_scene: Optional[QGraphicsScene] = None
        self.graphics_view: Optional[QGraphicsView] = None
        
        # Registered items
        self._state_items: Dict[str, QGraphicsItem] = {}
        # key: (start, end, event) -> item
        self._transition_items: Dict[Tuple[str, str, str], QGraphicsItem] = {}

        # Config
        self.enabled: bool = True
        self.reduce_motion: bool = False
        self.auto_pan: bool = True
        self.max_active_animations: int = 12

        self.duration_state_ms: int = 450
        self.duration_transition_ms: int = 600
        self.duration_pan_ms: int = 350

        self.easing_state = QEasingCurve.Type.OutBack
        self.easing_transition = QEasingCurve.Type.InOutCubic
        self.easing_pan = QEasingCurve.Type.InOutCubic

        self.color_accent = QColor(_theme_color("COLOR_ACCENT_PRIMARY", "#2D6DD2"))
        self.color_glow = QColor(_theme_color("COLOR_ACCENT_SUCCESS", "#2E7D32"))
        self.color_warn = QColor(_theme_color("COLOR_ACCENT_WARNING", "#E7A600"))

        # Internals
        self._active_anims: List[QVariantAnimation | QPropertyAnimation] = []
        self._ephemeral_items: List[QGraphicsItem] = []

    # ---------- Scene and registration ----------
    def set_view(self, view: QGraphicsView):
        self.graphics_view = view

    def register_graphics_items(self, state_items_map: Dict[str, QGraphicsItem],
                                transition_items_map: Dict[Tuple[str, str, str], QGraphicsItem]):
        self._state_items = state_items_map or {}
        self._transition_items = transition_items_map or {}

    def clear_animations(self):
        for anim in list(self._active_anims):
            try:
                anim.stop()
            except Exception:
                pass
        self._active_anims.clear()

        for it in list(self._ephemeral_items):
            try:
                if it.scene():
                    it.scene().removeItem(it)
            except Exception:
                pass
        self._ephemeral_items.clear()

    # ---------- Public API ----------
    def animate_state_entry(self, state_name: str, pan_to_item: Optional[bool] = None):
        if not self.enabled:
            return
        item = self._state_items.get(state_name)
        if not item:
            return

        if pan_to_item is None:
            pan_to_item = self.auto_pan
        if pan_to_item:
            self._pan_view_to_item(item)

        if self.reduce_motion:
            self._flash_outline(item, self.color_glow, duration_ms=200)
            return

        self._ripple_ring(item, self.color_accent, duration_ms=self.duration_state_ms)
        self._glow_pulse(item, self.color_glow, duration_ms=self.duration_state_ms)
        self._bounce_scale(item, duration_ms=self.duration_state_ms)

    def animate_transition(self, start_state: str, end_state: str, event: Optional[str] = None):
        if not self.enabled:
            return
        # Prefer exact (start, end, event), fall back to any with same endpoints
        trans_item = None
        if event is not None:
            trans_item = self._transition_items.get((start_state, end_state, event))
        if trans_item is None:
            # fallback: try first matching start->end ignoring event
            for (s, e, ev), it in self._transition_items.items():
                if s == start_state and e == end_state:
                    trans_item = it
                    break
        if not trans_item:
            return

        if self.reduce_motion:
            self._flash_outline(trans_item, self.color_accent, duration_ms=180)
            return

        self._dash_highlight(trans_item, color=self.color_accent, duration_ms=self.duration_transition_ms)
        self._token_along_path(trans_item, color=self.color_accent, duration_ms=self.duration_transition_ms)

        # Pan to the middle of the transition path if enabled
        if self.auto_pan:
            br = trans_item.sceneBoundingRect()
            self._pan_view_to_rect(br)

    # ---------- Building blocks ----------
    def _ripple_ring(self, item: QGraphicsItem, color: QColor, duration_ms: int = 450):
        if not self._can_start_anim():
            return
        if not self.graphics_scene:
            self.graphics_scene = item.scene()
        br = item.sceneBoundingRect()
        center = br.center()
        max_r = max(br.width(), br.height()) * 0.9

        ring = QGraphicsEllipseItem()
        ring.setRect(center.x(), center.y(), 0, 0)
        pen = QPen(color)
        pen.setWidth(2)
        ring.setPen(pen)
        ring.setBrush(QBrush(Qt.GlobalColor.transparent))
        ring.setZValue(1e6)  # above everything
        self.graphics_scene.addItem(ring)
        self._ephemeral_items.append(ring)

        anim = QVariantAnimation(self)
        anim.setDuration(duration_ms)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(self.easing_state)
        def on_value(v):
            r = max_r * float(v)
            rect = QRectF(center.x()-r/2, center.y()-r/2, r, r)
            ring.setRect(rect)
            # fade out
            a = max(0, 180 - int(180 * float(v)))
            p = ring.pen()
            c = QColor(color); c.setAlpha(a)
            p.setColor(c)
            ring.setPen(p)
        anim.valueChanged.connect(on_value)
        anim.finished.connect(lambda: self._remove_item_safe(ring))
        self._start_anim(anim)

    def _glow_pulse(self, item: QGraphicsItem, color: QColor, duration_ms: int = 450):
        if not self._can_start_anim():
            return
        try:
            eff = QGraphicsDropShadowEffect()
            eff.setBlurRadius(0)
            eff.setOffset(0, 0)
            eff.setColor(QColor(color))
            item.setGraphicsEffect(eff)

            anim = QVariantAnimation(self)
            anim.setDuration(duration_ms)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(self.easing_state)

            def on_value(v):
                # soft in-out glow
                t = float(v)
                if t <= 0.5:
                    b = 40 + int(60 * (t / 0.5))
                else:
                    b = 100 - int(60 * ((t - 0.5) / 0.5))
                eff.setBlurRadius(b)

            def on_finished():
                try:
                    item.setGraphicsEffect(None)
                except Exception:
                    pass

            anim.valueChanged.connect(on_value)
            anim.finished.connect(on_finished)
            self._start_anim(anim)
        except Exception:
            # fallback to outline flash
            self._flash_outline(item, color, duration_ms=200)

    def _bounce_scale(self, item: QGraphicsItem, duration_ms: int = 400):
        if not self._can_start_anim():
            return
        # scale around center using item's transform
        anim = QVariantAnimation(self)
        anim.setDuration(duration_ms)
        anim.setStartValue(1.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(self.easing_state)

        # Keyframing manual curve: 1.0 -> 1.08 -> 1.0
        def on_value(v):
            t = float(v)
            s = 1.0 + 0.08 * (1.0 - abs(2*t - 1.0))  # peaked at t=0.5
            try:
                # Preserve existing transform translation by scaling around center
                br = item.boundingRect()
                item.setTransformOriginPoint(br.center())
                item.setScale(s)
            except Exception:
                pass

        def on_finished():
            try:
                item.setScale(1.0)
            except Exception:
                pass

        anim.valueChanged.connect(on_value)
        anim.finished.connect(on_finished)
        self._start_anim(anim)

    def _dash_highlight(self, item: QGraphicsItem, color: QColor, duration_ms: int = 600):
        if not self._can_start_anim():
            return
        # animate dash offset by mutating pen on the item (if it supports it)
        anim = QVariantAnimation(self)
        anim.setDuration(duration_ms)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(self.easing_transition)

        # Try to apply a dashed pen on the item temporarily
        # Not all items expose setPen; we attempt common patterns.
        original_pen = None
        try:
            if hasattr(item, "pen"):
                original_pen = item.pen()
            p = QPen(color)
            p.setWidth(2)
            p.setDashPattern([6, 6])
            if hasattr(item, "setPen"):
                item.setPen(p)
        except Exception:
            original_pen = None

        def on_value(v):
            try:
                if hasattr(item, "pen") and hasattr(item, "setPen"):
                    p = item.pen()
                    p.setDashOffset(12 * float(v))
                    item.setPen(p)
            except Exception:
                pass

        def on_finished():
            try:
                if original_pen is not None and hasattr(item, "setPen"):
                    item.setPen(original_pen)
            except Exception:
                pass

        anim.valueChanged.connect(on_value)
        anim.finished.connect(on_finished)
        self._start_anim(anim)

    def _token_along_path(self, item: QGraphicsItem, color: QColor, duration_ms: int = 600):
        if not self._can_start_anim():
            return
        path = None
        try:
            if hasattr(item, "path") and callable(getattr(item, "path")):
                path = item.path()
            elif hasattr(item, "shape") and callable(getattr(item, "shape")):
                path = item.shape()
        except Exception:
            path = None
        if not isinstance(path, QPainterPath) or path.isEmpty():
            return

        token = QGraphicsEllipseItem(-4, -4, 8, 8)
        token.setBrush(QBrush(color))
        token.setPen(QPen(Qt.GlobalColor.transparent))
        token.setZValue(1e6)
        self.graphics_scene.addItem(token)
        self._ephemeral_items.append(token)

        anim = QVariantAnimation(self)
        anim.setDuration(duration_ms)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(self.easing_transition)

        def on_value(v):
            t = float(v)
            # QPainterPath: pointAtPercent uses [0..1]
            try:
                pt = path.pointAtPercent(t)
                token.setPos(pt)
            except Exception:
                # best effort: remove if unsupported
                token.hide()

        anim.valueChanged.connect(on_value)
        anim.finished.connect(lambda: self._remove_item_safe(token))
        self._start_anim(anim)

    def _flash_outline(self, item: QGraphicsItem, color: QColor, duration_ms: int = 180):
        if not self._can_start_anim():
            return
        anim = QVariantAnimation(self)
        anim.setDuration(duration_ms)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        original_pen = None
        try:
            if hasattr(item, "pen"):
                original_pen = item.pen()
            if hasattr(item, "setPen"):
                p = QPen(color)
                p.setWidth(2)
                item.setPen(p)
        except Exception:
            original_pen = None

        def on_finished():
            try:
                if original_pen is not None and hasattr(item, "setPen"):
                    item.setPen(original_pen)
            except Exception:
                pass

        anim.finished.connect(on_finished)
        self._start_anim(anim)

    # ---------- View panning ----------
    def _pan_view_to_item(self, item: QGraphicsItem):
        if not self.graphics_view or not item:
            return
        self._pan_view_to_rect(item.sceneBoundingRect())

    def _pan_view_to_rect(self, rect: QRectF):
        if not self.graphics_view:
            return
        view = self.graphics_view
        if self.reduce_motion or self.duration_pan_ms <= 0:
            view.ensureVisible(rect, 60, 60)
            return

        # Animate scrollbars to center on rect center
        center = rect.center()
        # Map scene center to scrollbar target values
        hbar = view.horizontalScrollBar()
        vbar = view.verticalScrollBar()

        # Compute target by mapping scene point to view coords and then to bars
        # Simpler: call centerOn incrementally via animation progress
        anim = QVariantAnimation(self)
        anim.setDuration(self.duration_pan_ms)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(self.easing_pan)

        def on_value(v):
            try:
                view.centerOn(center)
            except Exception:
                pass

        anim.valueChanged.connect(on_value)
        self._start_anim(anim)

    # ---------- Helpers ----------
    def _remove_item_safe(self, it: QGraphicsItem):
        try:
            if it in self._ephemeral_items:
                self._ephemeral_items.remove(it)
            if it.scene():
                it.scene().removeItem(it)
        except Exception:
            pass

    def _start_anim(self, anim: QVariantAnimation | QPropertyAnimation):
        if len(self._active_anims) >= self.max_active_animations:
            # Gracefully skip new animation when under load
            return
        self._active_anims.append(anim)
        def _cleanup():
            try:
                self._active_anims.remove(anim)
            except ValueError:
                pass
        anim.finished.connect(_cleanup)
        anim.start()

    def _can_start_anim(self) -> bool:
        return self.enabled and (len(self._active_anims) < self.max_active_animations)

    # ---------- Optional knobs ----------
    def set_options(self, *, enabled: Optional[bool] = None, reduce_motion: Optional[bool] = None,
                    auto_pan: Optional[bool] = None, durations: Optional[dict] = None,
                    colors: Optional[dict] = None, easing: Optional[dict] = None,
                    max_active_animations: Optional[int] = None):
        if enabled is not None:
            self.enabled = enabled
        if reduce_motion is not None:
            self.reduce_motion = reduce_motion
        if auto_pan is not None:
            self.auto_pan = auto_pan
        if durations:
            self.duration_state_ms = int(durations.get("state", self.duration_state_ms))
            self.duration_transition_ms = int(durations.get("transition", self.duration_transition_ms))
            self.duration_pan_ms = int(durations.get("pan", self.duration_pan_ms))
        if colors:
            if "accent" in colors: self.color_accent = QColor(colors["accent"])
            if "glow" in colors: self.color_glow = QColor(colors["glow"])
            if "warn" in colors: self.color_warn = QColor(colors["warn"])
        if easing:
            self.easing_state = easing.get("state", self.easing_state)
            self.easing_transition = easing.get("transition", self.easing_transition)
            self.easing_pan = easing.get("pan", self.easing_pan)
        if max_active_animations is not None:
            self.max_active_animations = int(max_active_animations)