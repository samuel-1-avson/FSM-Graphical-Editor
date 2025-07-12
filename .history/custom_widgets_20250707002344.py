# fsm_designer_project/custom_widgets.py

from PyQt5.QtWidgets import (
    QToolButton, QApplication, QWidget, QFrame, QVBoxLayout, QHBoxLayout,
    QLabel
)
from PyQt5.QtGui import QMouseEvent, QDrag, QPixmap, QPainter, QColor, QRegion
from PyQt5.QtCore import (
    Qt, QPoint, QMimeData, QSize, QPropertyAnimation, QEasingCurve
)
import json 
from .config import (
    COLOR_BACKGROUND_MEDIUM, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY
)


class CollapsibleSection(QFrame):
    """A collapsible section widget with smooth animation."""
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.is_collapsed = False
        self.init_ui(title)
        
    def init_ui(self, title):
        """Initialize the UI."""
        self.setFrameStyle(QFrame.NoFrame)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(1)
        
        # Header
        self.header = QToolButton()
        self.header.setText(title)
        self.header.setCheckable(True)
        self.header.setChecked(True)
        self.header.setStyleSheet(f"""
            QToolButton {{
                text-align: left;
                padding: 5px;
                background-color: {COLOR_BACKGROUND_MEDIUM};
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-radius: 3px;
                font-weight: bold;
                color: {COLOR_TEXT_PRIMARY};
            }}
        """)
        self.header.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.header.setArrowType(Qt.DownArrow)
        self.header.clicked.connect(self.toggle_collapsed)
        
        main_layout.addWidget(self.header)
        
        # Content area
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-top: none;
                border-bottom-left-radius: 3px;
                border-bottom-right-radius: 3px;
            }}
        """)
        
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.setSpacing(6)
        
        main_layout.addWidget(self.content_widget)
        
        # Animation
        self.animation = QPropertyAnimation(self.content_widget, b"maximumHeight")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        
    def add_widget(self, widget):
        """Add a widget to the content area."""
        self.content_layout.addWidget(widget)
        
    def add_layout(self, layout):
        """Add a layout to the content area."""
        self.content_layout.addLayout(layout)
        
    def toggle_collapsed(self, checked):
        """Toggle the collapsed state with animation."""
        self.is_collapsed = not checked
        
        if self.is_collapsed:
            self.header.setArrowType(Qt.RightArrow)
            self.animation.setStartValue(self.content_widget.sizeHint().height())
            self.animation.setEndValue(0)
        else:
            self.header.setArrowType(Qt.DownArrow)
            self.animation.setStartValue(0)
            self.animation.setEndValue(self.content_widget.sizeHint().height())
            
        self.animation.start()


class DraggableToolButton(QToolButton): 
    
    def __init__(self, text, mime_type, item_type_data_str, parent=None):
        super().__init__(parent)
        self.setText(text)
        self.mime_type = mime_type
        
        self.setObjectName("DraggableToolButton") 
        self.item_type_data_str = item_type_data_str
        self.setMinimumHeight(42) 
        self.setIconSize(QSize(24, 24)) 
        
        
        
        self.drag_start_position = QPoint()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if not (event.buttons() & Qt.LeftButton):
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setData(self.mime_type, self.item_type_data_str.encode('utf-8'))

        if self.mime_type == "application/x-bsm-template":
            try:
                template_obj = json.loads(self.item_type_data_str)
                mime_data.setText(f"FSM Template: {template_obj.get('name', 'Custom Template')}")
            except json.JSONDecodeError:
                mime_data.setText("FSM Template (Invalid JSON)")
        else:
            mime_data.setText(self.item_type_data_str)

        drag.setMimeData(mime_data)

        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.transparent)
        
        # Corrected renderFlags usage
        # QWidget.DrawChildren is a common flag for this purpose.
        # You can combine flags using the bitwise OR operator if needed, e.g.,
        # QWidget.DrawChildren | QWidget.IgnoreMask
        self.render(pixmap, QPoint(), QRegion(), QWidget.RenderFlags(QWidget.DrawChildren))


        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        painter.fillRect(pixmap.rect(), QColor(0, 0, 0, 150)) 
        painter.end()

        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        drag.exec_(Qt.CopyAction)