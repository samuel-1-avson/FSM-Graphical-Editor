# fsm_designer_project/virtual_hardware_widgets.py

from PyQt5.QtWidgets import QWidget, QPushButton, QSlider, QLabel, QProgressBar
from PyQt5.QtGui import QPainter, QColor, QBrush, QPixmap
from PyQt5.QtCore import Qt

class VirtualLedWidget(QLabel):
    """A simple widget that draws a colored circle to represent an LED by using a pixmap."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_on = False
        self.on_color = QColor(60, 255, 60)   # A bright green
        self.off_color = QColor(60, 100, 60)  # A dim dark green
        self.setFixedSize(24, 24)
        self.setToolTip("Virtual LED")
        self._update_pixmap() # Set initial state

    def setState(self, is_on: bool):
        """Sets the visual state of the LED (on or off)."""
        if self._is_on != is_on:
            self._is_on = is_on
            self._update_pixmap()  # Trigger a repaint to show the new color

    def _update_pixmap(self):
        """Paints the LED circle onto a QPixmap and sets it on the label."""
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        color = self.on_color if self._is_on else self.off_color
        
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        # Adjust rect to have a small margin
        painter.drawEllipse(self.rect().adjusted(2, 2, -2, -2))
        painter.end()
        
        self.setPixmap(pixmap)


# For now, we can use standard widgets and subclass them if needed later.
class VirtualButtonWidget(QPushButton):
    """A simple wrapper for QPushButton for semantic clarity."""
    pass

class VirtualSliderWidget(QSlider):
    """A simple wrapper for QSlider for semantic clarity."""
    pass

# --- NEW GAUGE WIDGET ---
class VirtualGaugeWidget(QProgressBar):
    """A progress bar styled to look like a simple horizontal gauge for analog output."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(0, 255) # Default 8-bit PWM range (e.g., analogWrite on Arduino)
        self.setValue(0)
        self.setTextVisible(True)
        self.setFormat("%v") # Show the numeric value
        self.setOrientation(Qt.Horizontal)
        self.setMinimumHeight(24)
        self.setToolTip("Virtual Analog Output (e.g., PWM)")
        # Style the progress bar to look like a gauge
        self.setStyleSheet("""
            QProgressBar {
                border: 1px solid #78909C;
                border-radius: 4px;
                background-color: #37474F;
                color: #ECEFF1;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                                  stop:0 #81C784, 
                                                  stop:0.5 #FFD54F, 
                                                  stop:1 #E57373);
                border-radius: 3px;
                margin: 0.5px;
            }
        """)
# --- END NEW ---