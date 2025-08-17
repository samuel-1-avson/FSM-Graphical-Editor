# fsm_designer_project/ui/widgets/minimap_view.py
import logging
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsRectItem, QGraphicsScene
)
from PyQt6.QtGui import (
    QMouseEvent, QPainter, QColor, QPen, QBrush
)
# --- FIX: Moved QGraphicsScene import to QtWidgets and removed it from QtCore ---
from PyQt6.QtCore import Qt, QTimer, QEvent, QRectF

# Import ZoomableView from its correct location
from ..graphics.graphics_scene import ZoomableView
# --- FIX: Import graphics items from the correct module ---
from ..graphics.graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem

logger = logging.getLogger(__name__)

class MinimapView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_view = None
        self.setInteractive(True)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self._is_dragging_viewport = False
        
        self._viewport_rect_item = QGraphicsRectItem()
        self._viewport_rect_item.setPen(QPen(QColor(255, 0, 0, 180), 2))
        self._viewport_rect_item.setBrush(QBrush(QColor(255, 0, 0, 40)))
        self._viewport_rect_item.setZValue(100)
        
        self.schematic_state_pen = QPen(Qt.PenStyle.NoPen)
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
        if obj == self.main_view and event.type() == QEvent.Type.Resize:
            if hasattr(self, '_resize_timer'):
                self._resize_timer.start()
        return super().eventFilter(obj, event)

    def update_viewport_rect(self):
        try:
            if not self.main_view or not self.scene():
                if self._viewport_rect_item.isVisible(): self._viewport_rect_item.hide()
                return
            if not self._viewport_rect_item.isVisible(): self._viewport_rect_item.show()
            visible_rect = self.main_view.mapToScene(self.main_view.viewport().rect()).boundingRect()
            self._viewport_rect_item.setRect(visible_rect)
        except RuntimeError: # Object might be deleted
            pass

    def mousePressEvent(self, event: QMouseEvent):
        try:
            if self._viewport_rect_item.isUnderMouse():
                self._is_dragging_viewport = True
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            elif self.main_view:
                self.main_view.centerOn(self.mapToScene(event.position().toPoint()))
        except RuntimeError: # Object might be deleted
            pass
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_dragging_viewport and self.main_view:
            try:
                self.main_view.centerOn(self.mapToScene(event.position().toPoint()))
            except RuntimeError: # Object might be deleted
                pass
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._is_dragging_viewport = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    def setScene(self, scene: QGraphicsScene | None):
        try:
            if self.scene():
                self.scene().changed.disconnect(self._on_scene_changed)
        except (TypeError, RuntimeError): pass
        
        super().setScene(scene)

        try:
            if scene:
                if self._viewport_rect_item.scene() != scene:
                    scene.addItem(self._viewport_rect_item)
                self._viewport_rect_item.show()
                scene.changed.connect(self._on_scene_changed)
                self._fit_contents()
                self.update_viewport_rect()
            elif self._viewport_rect_item:
                self._viewport_rect_item.hide()
        except RuntimeError: # Object might be deleted
            pass

    def drawBackground(self, painter: QPainter, rect: QRectF):
        super().drawBackground(painter, rect)
        if not self.scene(): return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        
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
        try:
            if self.scene():
                content_rect = self.scene().itemsBoundingRect()
                if content_rect.isEmpty(): content_rect = self.scene().sceneRect()
                self.fitInView(content_rect, Qt.AspectRatioMode.KeepAspectRatio)
        except RuntimeError: # Object might be deleted
            pass