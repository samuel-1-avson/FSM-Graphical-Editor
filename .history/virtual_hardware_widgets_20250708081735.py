# Example for fsm_designer_project/virtual_hardware_widgets.py

from PyQt5.QtWidgets import QWidget, QPushButton, QSlider
from PyQt5.QtGui import QPainter, QColor, QBrush
from PyQt5.QtCore import Qt, pyqtSignal

class VirtualLedWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_on = False
        self.on_color = QColor("lime")
        self.off_color = QColor("darkgreen").darker(150)
        self.setFixedSize(24, 24)

    def setState(self, is_on: bool):
        if self._is_on != is_on:
            self._is_on = is_on
            self.update() # Trigger a repaint

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color = self.on_color if self._is_on else self.off_color
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(self.rect().adjusted(2, 2, -2, -2))

class VirtualButtonWidget(QPushButton):
    # We can just use a standard QPushButton for this
    pass

class VirtualSliderWidget(QSlider):
    # We can use a standard QSlider for this
    pass