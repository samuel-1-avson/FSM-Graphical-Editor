# fsm_designer_project/ui_virtual_hardware_manager.py

import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFormLayout
from .virtual_hardware_widgets import VirtualLedWidget, VirtualButtonWidget, VirtualSliderWidget
from .config import COLOR_TEXT_SECONDARY, APP_FONT_SIZE_SMALL

logger = logging.getLogger(__name__)

class VirtualHardwareUIManager:
    def __init__(self, main_window):
        self.mw = main_window
        # Dictionaries to hold references to the created widgets for later access
        self.virtual_leds = {}
        self.virtual_buttons = {}
        self.virtual_sliders = {}
        logger.info("VirtualHardwareUIManager initialized.")

    def create_dock_widget_contents(self) -> QWidget:
        """Creates the main widget and its contents to be placed in the dock."""
        container_widget = QWidget()
        main_layout = QVBoxLayout(container_widget)
        main_layout.setSpacing(10)

        # --- Create a group for Digital Outputs (LEDs) ---
        led_group = QGroupBox("Digital Outputs")
        led_layout = QFormLayout(led_group)
        led_layout.setSpacing(8)
        # Create 4 LEDs as an example
        for i in range(4):
            led_key = f"LED{i}"
            led = VirtualLedWidget()
            self.virtual_leds[led_key] = led
            led_layout.addRow(f"LED {i}:", led)
        main_layout.addWidget(led_group)

        # --- Create a group for Digital Inputs (Buttons) ---
        button_group = QGroupBox("Digital Inputs")
        button_layout = QVBoxLayout(button_group)
        button_layout.setSpacing(6)
        # Create 4 buttons as an example
        for i in range(4):
            button_key = f"Button{i}"
            button = VirtualButtonWidget(f"Trigger B{i}")
            self.virtual_buttons[button_key] = button
            button_layout.addWidget(button)
        main_layout.addWidget(button_group)

        # --- Create a group for Analog Inputs (Sliders) ---
        slider_group = QGroupBox("Analog Inputs")
        slider_layout = QFormLayout(slider_group)
        # Create 2 sliders as an example
        for i in range(2):
            slider_key = f"Slider{i}"
            slider = VirtualSliderWidget(Qt.Horizontal)
            slider.setRange(0, 255) # e.g., for an 8-bit ADC
            self.virtual_sliders[slider_key] = slider
            slider_layout.addRow(f"A{i}:", slider)
        main_layout.addWidget(slider_group)

        main_layout.addStretch()

        disclaimer = QLabel("<i>Connect these components via Item Properties.</i>")
        disclaimer.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {APP_FONT_SIZE_SMALL};")
        disclaimer.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(disclaimer)
        
        return container_widget