# fsm_designer_project/ui/widgets/custom_widgets.py

from PyQt6.QtWidgets import (
    QToolButton, QApplication, QWidget, QFrame, QVBoxLayout, QHBoxLayout,
    QLabel, QCheckBox, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import (
    QMouseEvent, QDrag, QPixmap, QPainter, QColor, QRegion, QFont,
    QPaintEvent, QLinearGradient, QPen, QBrush, QIcon
)
from PyQt6.QtCore import (
    Qt, QPoint, QMimeData, QSize, QPropertyAnimation, QEasingCurve,
    pyqtSignal, QTimer, QRect, QParallelAnimationGroup, QAbstractAnimation
)
import json
import logging
from typing import Optional, Union, Any, Dict
# --- MODIFIED: Corrected import path ---
from ...utils.config import (
    COLOR_BACKGROUND_MEDIUM, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY,
    COLOR_DRAGGABLE_BUTTON_BG, COLOR_DRAGGABLE_BUTTON_BORDER,
    COLOR_DRAGGABLE_BUTTON_HOVER_BG, COLOR_DRAGGABLE_BUTTON_HOVER_BORDER,
    COLOR_DRAGGABLE_BUTTON_PRESSED_BG
)



class CollapsibleSection(QFrame):
    """
    A collapsible section widget with smooth animation and enhanced functionality.
    
    Features:
    - Smooth expand/collapse animations
    - Customizable styling
    - Support for filtering content
    - Memory of collapsed state
    - Enhanced visual feedback
    """
    
    # Signals
    collapsed_changed = pyqtSignal(bool)  # Emitted when collapse state changes
    content_changed = pyqtSignal()        # Emitted when content is modified
    
    def __init__(self, title: str, parent: Optional[QWidget] = None, 
                 collapsible: bool = True, start_collapsed: bool = False):
        """
        Initialize the CollapsibleSection.
        
        Args:
            title: The title text for the section
            parent: Parent widget
            collapsible: Whether the section can be collapsed
            start_collapsed: Whether to start in collapsed state
        """
        super().__init__(parent)
        self.title_text = title
        self.is_collapsed = start_collapsed
        self.is_collapsible = collapsible
        self.content_widgets = []  # Track added widgets for filtering
        
        self._init_ui(title)
        self._setup_animations()
        
        # Set initial state
        if start_collapsed:
            self.content_widget.setMaximumHeight(0)
            self.header.setArrowType(Qt.ArrowType.RightArrow)
        
    def _init_ui(self, title):
        """Initialize the user interface."""
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Header
        self._create_header(title)
        
        # Content widget
        self._create_content_widget()
        
    def _create_header(self, title):
        """Create the header with title and collapse button."""
        self.header = QToolButton(self)
        self.header.setText(title)
        self.header.setObjectName("CollapsibleSectionHeader")
        self.header.setCheckable(self.is_collapsible)
        self.header.setChecked(not self.is_collapsed)
        self.header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        if self.is_collapsible:
            self.header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            self.header.setArrowType(Qt.ArrowType.DownArrow if not self.is_collapsed else Qt.ArrowType.RightArrow)
            self.header.clicked.connect(self._toggle_collapsed)
        else:
            self.header.setEnabled(False)
        
        self.main_layout.addWidget(self.header)
        
    def _create_content_widget(self):
        """Create the content widget container."""
        self.content_widget = QWidget()
        self.content_widget.setObjectName("CollapsibleContentWidget")
        self.content_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.setSpacing(6)
        
        self.main_layout.addWidget(self.content_widget)
        
    def _setup_animations(self):
        """Setup the collapse/expand animations."""
        # Height animation
        self.height_animation = QPropertyAnimation(self.content_widget, b"maximumHeight")
        self.height_animation.setDuration(250)
        self.height_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        
        # Opacity animation for smoother effect
        self.opacity_effect = QGraphicsDropShadowEffect()
        self.opacity_effect.setColor(QColor(0, 0, 0, 0))
        self.opacity_effect.setBlurRadius(0)
        
        # Animation group for coordinated animations
        self.animation_group = QParallelAnimationGroup()
        self.animation_group.addAnimation(self.height_animation)
        
        # Connect animation finished signal
        self.animation_group.finished.connect(self._on_animation_finished)
        
    def _apply_styling(self):
        """Apply custom styling to the widget."""
        # This method is now obsolete as styling is handled globally.
        pass
        
    def add_widget(self, widget: QWidget, label: Optional[str] = None):
        """
        Add a widget to the content area.
        
        Args:
            widget: The widget to add
            label: Optional label text for the widget
        """
        if label:
            self.add_row(label, widget)
        else:
            # Handle special cases
            if isinstance(widget, QCheckBox):
                self._add_checkbox_widget(widget)
            else:
                self.content_layout.addWidget(widget)
                self.content_widgets.append((widget, None))
        
        self.content_changed.emit()
        
    def _add_checkbox_widget(self, checkbox: QCheckBox):
        """Add a checkbox widget with proper structure."""
        row_widget = QWidget()
        row_widget.setObjectName("propertyRow")
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        
        checkbox.setObjectName("propertyLabel")
        row_layout.addWidget(checkbox)
        row_layout.addStretch()  # Push checkbox to left
        
        self.content_layout.addWidget(row_widget)
        self.content_widgets.append((checkbox, checkbox.text()))
        
    def add_row(self, label_text: str, widget: QWidget):
        """
        Add a labeled row to the content area.
        
        Args:
            label_text: The label text
            widget: The widget to add
        """
        row_widget = QWidget()
        row_widget.setObjectName("propertyRow")
        
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        
        label_widget = QLabel(label_text)
        label_widget.setObjectName("propertyLabel")
        label_widget.setMinimumWidth(80)  # Consistent label width
        
        row_layout.addWidget(label_widget)
        row_layout.addWidget(widget, 1)
        
        self.content_layout.addWidget(row_widget)
        self.content_widgets.append((widget, label_text))
        
    def remove_widget(self, widget: QWidget):
        """Remove a widget from the content area."""
        # Find and remove from content_widgets list
        self.content_widgets = [(w, l) for w, l in self.content_widgets if w != widget]
        
        # Remove from layout
        widget.setParent(None)
        self.content_changed.emit()
        
    def clear_content(self):
        """Clear all content from the section."""
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.content_widgets.clear()
        self.content_changed.emit()
        
    def _toggle_collapsed(self, checked: bool):
        """Toggle the collapsed state with animation."""
        if not self.is_collapsible:
            return
            
        new_collapsed_state = not checked
        if new_collapsed_state == self.is_collapsed:
            return
            
        self.is_collapsed = new_collapsed_state
        
        if self.is_collapsed:
            self._collapse()
        else:
            self._expand()
            
        self.collapsed_changed.emit(self.is_collapsed)
        
    def _collapse(self):
        """Animate collapsing the section."""
        self.header.setArrowType(Qt.ArrowType.RightArrow)
        
        start_height = self.content_widget.height()
        self.height_animation.setStartValue(start_height)
        self.height_animation.setEndValue(0)
        
        self.animation_group.start()
        
    def _expand(self):
        """Animate expanding the section."""
        self.header.setArrowType(Qt.ArrowType.DownArrow)
        
        # Calculate content height
        self.content_widget.setMaximumHeight(16777215)  # Remove height constraint temporarily
        content_height = self.content_widget.sizeHint().height()
        
        self.height_animation.setStartValue(0)
        self.height_animation.setEndValue(content_height)
        
        self.animation_group.start()
        
    def _on_animation_finished(self):
        """Handle animation completion."""
        if not self.is_collapsed:
            # Remove height constraint when fully expanded
            self.content_widget.setMaximumHeight(16777215)
            
    def set_collapsed(self, collapsed: bool, animated: bool = True):
        """
        Programmatically set the collapsed state.
        
        Args:
            collapsed: Whether to collapse the section
            animated: Whether to animate the change
        """
        if collapsed == self.is_collapsed:
            return
            
        if not animated:
            # Stop any running animation
            if self.animation_group.state() == QAbstractAnimation.State.Running:
                self.animation_group.stop()
                
            self.is_collapsed = collapsed
            if collapsed:
                self.content_widget.setMaximumHeight(0)
                self.header.setArrowType(Qt.ArrowType.RightArrow)
                self.header.setChecked(False)
            else:
                self.content_widget.setMaximumHeight(16777215)
                self.header.setArrowType(Qt.ArrowType.DownArrow)
                self.header.setChecked(True)
            
            self.collapsed_changed.emit(self.is_collapsed)
        else:
            self.header.setChecked(not collapsed)
            
    def is_section_collapsed(self) -> bool:
        """Return whether the section is currently collapsed."""
        return self.is_collapsed
        
    def get_title(self) -> str:
        """Return the section title."""
        return self.title_text
        
    def set_title(self, title: str):
        """Set the section title."""
        self.title_text = title
        self.header.setText(title)
        
    def filter_content(self, search_text: str) -> bool:
        """
        Filter content based on search text.
        
        Args:
            search_text: Text to search for
            
        Returns:
            True if any content matches, False otherwise
        """
        if not search_text:
            self.setVisible(True)
            return True
            
        # Check title
        title_match = search_text.lower() in self.title_text.lower()
        
        # Check content widgets
        content_match = False
        for widget, label in self.content_widgets:
            if label and search_text.lower() in label.lower():
                content_match = True
                break
            elif hasattr(widget, 'text') and widget.text():
                if search_text.lower() in widget.text().lower():
                    content_match = True
                    break
                    
        has_match = title_match or content_match
        self.setVisible(has_match)
        
        return has_match


class DraggableToolButton(QToolButton):
    """
    Enhanced draggable tool button with improved visual feedback and functionality.
    
    Features:
    - Smooth drag initiation
    - Enhanced visual feedback
    - Better error handling
    - Customizable drag behavior
    - Support for different mime types
    """
    
    # Signals
    drag_started = pyqtSignal()
    drag_finished = pyqtSignal()
    
    def __init__(self, text: str, mime_type: str, item_type_data_str: str, 
                 parent: Optional[QWidget] = None, icon: Optional[QIcon] = None):
        """
        Initialize the DraggableToolButton.
        
        Args:
            text: Button text
            mime_type: MIME type for drag data
            item_type_data_str: Data to include in drag operation
            parent: Parent widget
            icon: Optional icon for the button
        """
        super().__init__(parent)
        
        # Properties
        self.setText(text)
        self.mime_type = mime_type
        self.item_type_data_str = item_type_data_str
        self.drag_start_position = QPoint()
        self.is_dragging = False
        
        # Setup button
        self._setup_button(icon)
        
        # Hover timer for delayed hover effects
        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self._on_hover_timeout)
        
    def _setup_button(self, icon: Optional[QIcon]):
        """Setup button properties."""
        self.setObjectName("DraggableToolButton")
        self.setMinimumHeight(42)
        self.setMinimumWidth(120)
        self.setIconSize(QSize(24, 24))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        if icon:
            self.setIcon(icon)
            self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        else:
            self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            
        # Enable mouse tracking for better hover effects
        self.setMouseTracking(True)
        
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()
            self.is_dragging = False
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move events for drag initiation."""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
            
        if self.is_dragging:
            return
            
        manhattan_length = (event.pos() - self.drag_start_position).manhattanLength()
        if manhattan_length < QApplication.startDragDistance():
            return
            
        self._start_drag(event)
        
    def _start_drag(self, event: QMouseEvent):
        """Initiate drag operation."""
        try:
            self.is_dragging = True
            self.drag_started.emit()
            
            drag = QDrag(self)
            mime_data = self._create_mime_data()
            drag.setMimeData(mime_data)
            
            # Create drag pixmap
            pixmap = self._create_drag_pixmap()
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.pos())
            
            # Execute drag
            drop_action = drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction, Qt.DropAction.CopyAction)
            
            self.drag_finished.emit()
            
        except Exception as e:
            logging.error(f"Error during drag operation: {e}")
        finally:
            self.is_dragging = False
            
    def _create_mime_data(self) -> QMimeData:
        """Create MIME data for the drag operation."""
        mime_data = QMimeData()
        
        try:
            # Set the primary data
            mime_data.setData(self.mime_type, self.item_type_data_str.encode('utf-8'))
            
            # Set text representation
            if self.mime_type == "application/x-bsm-template":
                try:
                    template_obj = json.loads(self.item_type_data_str)
                    display_text = f"FSM Template: {template_obj.get('name', 'Custom Template')}"
                except json.JSONDecodeError:
                    display_text = "FSM Template (Invalid JSON)"
                    logging.warning(f"Invalid JSON in template data: {self.item_type_data_str}")
            else:
                display_text = self.item_type_data_str
                
            mime_data.setText(display_text)
            
            # Add additional metadata
            metadata = {
                'source': 'DraggableToolButton',
                'button_text': self.text(),
                'mime_type': self.mime_type
            }
            mime_data.setData("application/x-button-metadata", 
                            json.dumps(metadata).encode('utf-8'))
            
        except Exception as e:
            logging.error(f"Error creating MIME data: {e}")
            # Fallback to simple text
            mime_data.setText(self.text())
            
        return mime_data
        
    def _create_drag_pixmap(self) -> QPixmap:
        """Create a pixmap for drag visualization."""
        try:
            # Create pixmap with better quality
            pixmap = QPixmap(self.size() * 2)  # Higher resolution
            pixmap.fill(Qt.GlobalColor.transparent)
            
            # Render the button
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.scale(2.0, 2.0)  # Scale for higher resolution
            
            # Render the button content
            self.render(painter, QPoint(), QRegion(), QWidget.RenderFlag.DrawChildren)
            
            # Apply transparency effect
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
            painter.fillRect(pixmap.rect(), QColor(0, 0, 0, 180))
            
            painter.end()
            
            return pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            
        except Exception as e:
            logging.error(f"Error creating drag pixmap: {e}")
            # Fallback to simple pixmap
            fallback_pixmap = QPixmap(self.size())
            fallback_pixmap.fill(QColor(100, 100, 100, 150))
            return fallback_pixmap
            
    def enterEvent(self, event):
        """Handle mouse enter events."""
        super().enterEvent(event)
        self.hover_timer.start(100)  # Slight delay for smoother interaction
        
    def leaveEvent(self, event):
        """Handle mouse leave events."""
        super().leaveEvent(event)
        self.hover_timer.stop()
        
    def _on_hover_timeout(self):
        """Handle hover timeout for enhanced effects."""
        # Could add additional hover effects here
        pass
        
    def set_drag_enabled(self, enabled: bool):
        """Enable or disable drag functionality."""
        self.setAcceptDrops(enabled)
        if not enabled:
            self.setStyleSheet(self.styleSheet() + "\nQToolButton { cursor: default; }")
        else:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            
    def get_drag_data(self) -> Dict[str, Any]:
        """Get drag data information."""
        return {
            'mime_type': self.mime_type,
            'data': self.item_type_data_str,
            'text': self.text()
        }