# fsm_designer_project/ui_virtual_hardware_manager.py

import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLabel, QSlider
from PyQt5.QtCore import Qt, pyqtSlot
from .virtual_hardware_widgets import VirtualLedWidget, VirtualButtonWidget, VirtualSliderWidget
from .config import COLOR_TEXT_SECONDARY, APP_FONT_SIZE_SMALL
from .graphics_items import GraphicsTransitionItem

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
            # --- FIX: Connect the signal to a slot ---
            button.clicked.connect(lambda checked=False, bkey=button_key: self.on_virtual_button_clicked(bkey))
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

    @pyqtSlot(str)
    def on_virtual_button_clicked(self, button_key: str):
        editor = self.mw.current_editor()
        if not editor or not editor.py_fsm_engine or not editor.py_sim_active:
            logger.warning(f"Virtual button '{button_key}' clicked, but simulation is not active.")
            return

        # Find which FSM transition this button is mapped to
        triggered_event = None
        for item in editor.scene.items():
            if isinstance(item, GraphicsTransitionItem) and item.get_data().get('hw_input_map') == button_key:
                triggered_event = item.get_data().get('event')
                if triggered_event:
                    self.mw.py_sim_ui_manager.append_to_action_log([f"Hardware input '{button_key}' triggered FSM event: '{triggered_event}'"])
                    # Use a custom argument to tell the trigger function this is from an external source
                    # so it doesn't try to read the value from the combobox/lineedit.
                    self.mw.py_sim_ui_manager.on_trigger_py_event(external_event_name=triggered_event)
                    return
        
        if not triggered_event:
             logger.info(f"Virtual button '{button_key}' was clicked, but it's not mapped to any transition event in the diagram.")