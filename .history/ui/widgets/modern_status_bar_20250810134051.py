# fsm_designer_project/ui/widgets/modern_status_bar.py
"""
Modern status bar with enhanced visuals and information display.
"""

from PyQt6.QtWidgets import (
    QStatusBar, QWidget, QHBoxLayout, QLabel, QProgressBar,
    QToolButton, QFrame, QVBoxLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QIcon, QPalette, QColor, QPixmap, QPainter, QBrush
from ...codegen import config
from ...codegen.config import (
    COLOR_ACCENT_PRIMARY, COLOR_BACKGROUND_LIGHT, COLOR_TEXT_PRIMARY,
    COLOR_BORDER_LIGHT, COLOR_TEXT_SECONDARY, COLOR_BACKGROUND_APP,
    COLOR_ACCENT_SUCCESS, COLOR_ACCENT_WARNING, COLOR_ACCENT_ERROR
)
import psutil # Ensure psutil is imported
from ...codegen.logging_setup import logger
class StatusIndicator(QWidget):
    """Animated status indicator with icon and text."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.status_type = "info"
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)
        
        # Icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(16, 16)
        layout.addWidget(self.icon_label)
        
        # Text
        self.text_label = QLabel()
        layout.addWidget(self.text_label)
        
        # Set initial style
        self.set_status("Ready", "info")
        
    def set_status(self, text, status_type="info"):
        """Set the status with appropriate styling."""
        self.status_type = status_type
        self.text_label.setText(text)
        
        colors = {
            "info": COLOR_ACCENT_PRIMARY,
            "success": COLOR_ACCENT_SUCCESS,
            "warning": COLOR_ACCENT_WARNING,
            "error": COLOR_ACCENT_ERROR
        }
        
        color = colors.get(status_type, COLOR_ACCENT_PRIMARY)
        bg_color = QColor(color).lighter(190)
        luminance = bg_color.lightnessF()
        text_color = config.COLOR_TEXT_PRIMARY if luminance > 0.5 else config.COLOR_TEXT_ON_ACCENT
        
        # Create status icon
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(color)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()
        
        self.icon_label.setPixmap(pixmap)
        self.text_label.setStyleSheet(f"color: {text_color};")
        
        # Animate appearance
        self.setAutoFillBackground(True)
        self.setStyleSheet(f"background-color: {bg_color.name()}; border: 1px solid {color}; border-radius: 4px;")
        
        # Fade animation
        self.effect = self.graphicsEffect()
        if not self.effect:
            from PyQt6.QtWidgets import QGraphicsOpacityEffect
            self.effect = QGraphicsOpacityEffect()
            self.setGraphicsEffect(self.effect)
            
        self.fade_animation = QPropertyAnimation(self.effect, b"opacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()


class ModernStatusBar(QStatusBar):
    """Enhanced status bar with modern styling and features."""
    
    # Signals
    coordinatesClicked = pyqtSignal()
    zoomClicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.setup_timers()
        
    def init_ui(self):
        """Initialize the UI."""
        # Main styling is now handled by the application's global stylesheet
        
        # Left side - status indicator
        self.status_indicator = StatusIndicator()
        self.addWidget(self.status_indicator)
        
        # Add stretcher
        empty = QWidget()
        empty.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.addWidget(empty, 1)
        
        # Right side widgets
        self.create_info_widgets()
        
    def create_info_widgets(self):
        """Create information display widgets."""
        # Container for right-side widgets
        right_container = QWidget()
        right_layout = QHBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 10, 0)
        right_layout.setSpacing(15)
        
        # Coordinates display
        self.coords_widget = self.create_info_item("Coordinates:", "0, 0")
        self.coords_widget.mousePressEvent = lambda e: self.coordinatesClicked.emit()
        self.coords_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        right_layout.addWidget(self.coords_widget)
        
        # Zoom display
        self.zoom_widget = self.create_info_item("Zoom:", "100%")
        self.zoom_widget.mousePressEvent = lambda e: self.zoomClicked.emit()
        self.zoom_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        right_layout.addWidget(self.zoom_widget)
        
        # Selection info
        self.selection_widget = self.create_info_item("Selection:", "None")
        right_layout.addWidget(self.selection_widget)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setObjectName("StatusBarSeparator")
        right_layout.addWidget(separator)
        
        # Performance info
        self.performance_widget = self.create_performance_widget()
        right_layout.addWidget(self.performance_widget)
        
        self.addPermanentWidget(right_container)
        
    def create_info_item(self, label_text, value_text):
        """Create a styled info display item."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        
        label = QLabel(label_text)
        
        value = QLabel(value_text)
        value.setObjectName("value")
        
        layout.addWidget(label)
        layout.addWidget(value)
        
        return widget
        
    def create_performance_widget(self):
        """Create performance monitoring widget."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # CPU indicator
        self.cpu_label = QLabel("CPU:")
        
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setRange(0, 100)
        self.cpu_bar.setValue(0)
        self.cpu_bar.setFixedWidth(60)
        self.cpu_bar.setFixedHeight(12)
        self.cpu_bar.setTextVisible(False)
        
        # Memory indicator
        self.mem_label = QLabel("MEM:")
        
        self.mem_bar = QProgressBar()
        self.mem_bar.setRange(0, 100)
        self.mem_bar.setValue(0)
        self.mem_bar.setFixedWidth(60)
        self.mem_bar.setFixedHeight(12)
        self.mem_bar.setTextVisible(False)
        
        layout.addWidget(self.cpu_label)
        layout.addWidget(self.cpu_bar)
        layout.addWidget(self.mem_label)
        layout.addWidget(self.mem_bar)
        
        return widget
        
    def setup_timers(self):
        """Setup update timers."""
        # Performance update timer
        self.perf_timer = QTimer()
        self.perf_timer.timeout.connect(self.update_performance)
        self.perf_timer.start(2000)  # Update every 2 seconds
        
    def update_performance(self):
        """Update performance indicators."""
        try:
            # --- FIX: Wrap in try-except to handle potential OS errors ---
            try:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                self.cpu_bar.setValue(int(cpu_percent))
            
                if cpu_percent > 80: color = COLOR_ACCENT_ERROR
                elif cpu_percent > 60: color = COLOR_ACCENT_WARNING
                else: color = COLOR_ACCENT_SUCCESS
                
                self.cpu_bar.setStyleSheet(f"""
                    QProgressBar::chunk {{
                        background-color: {color}; border-radius: 5px;
                    }}
                """)
            
                mem_percent = psutil.virtual_memory().percent
                self.mem_bar.setValue(int(mem_percent))
            except (ImportError, psutil.Error) as e:
                # psutil not available or failed
                self.perf_timer.stop()
                self.performance_widget.hide()
                logger.warning(f"Stopping status bar performance monitor due to error: {e}")
            # --- END FIX ---
            
        except (ImportError, psutil.Error) as e:
            # psutil not available or failed
            self.perf_timer.stop()
            self.performance_widget.hide()
            logger.warning(f"Stopping status bar performance monitor due to error: {e}")
            
    def set_status(self, message, status_type="info", duration=3000):
        """Set status message with type and optional auto-hide."""
        self.status_indicator.set_status(message, status_type)
        
        if duration > 0:
            QTimer.singleShot(duration, lambda: self.status_indicator.set_status("Ready", "info"))
            
    def update_coordinates(self, x, y):
        """Update coordinate display."""
        value_label = self.coords_widget.findChild(QLabel, "value")
        if value_label:
            value_label.setText(f"{int(x)}, {int(y)}")
            
    def update_zoom(self, zoom_percent):
        """Update zoom display."""
        value_label = self.zoom_widget.findChild(QLabel, "value")
        if value_label:
            value_label.setText(f"{zoom_percent}%")
            
    def update_selection(self, selection_text):
        """Update selection display."""
        value_label = self.selection_widget.findChild(QLabel, "value")
        if value_label:
            # Truncate if too long
            if len(selection_text) > 20:
                selection_text = selection_text[:17] + "..."
            value_label.setText(selection_text)
            
    def show_progress(self, text="Processing...", indeterminate=True):
        """Show a progress indicator in the status bar."""
        # Create progress widget if needed
        if not hasattr(self, 'progress_widget'):
            self.progress_widget = QWidget()
            progress_layout = QHBoxLayout(self.progress_widget)
            progress_layout.setContentsMargins(8, 4, 8, 4)
            
            self.progress_label = QLabel(text)
            self.progress_bar = QProgressBar()
            self.progress_bar.setFixedWidth(150)
            self.progress_bar.setFixedHeight(12)
            
            progress_layout.addWidget(self.progress_label)
            progress_layout.addWidget(self.progress_bar)
            
        self.progress_label.setText(text)
        
        if indeterminate:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
            
        self.addWidget(self.progress_widget)
        self.progress_widget.show()
        
    def hide_progress(self):
        """Hide the progress indicator."""
        if hasattr(self, 'progress_widget'):
            self.removeWidget(self.progress_widget)
            self.progress_widget.hide()
            
    def set_progress(self, value):
        """Set progress bar value (0-100)."""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(value)