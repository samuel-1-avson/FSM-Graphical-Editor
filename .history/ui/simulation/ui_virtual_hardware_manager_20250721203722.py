# fsm_designer_project/ui/simulation/ui_virtual_hardware_manager.py

import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLabel, 
                             QSlider, QComboBox, QPushButton, QHBoxLayout, QProgressBar)
from PyQt5.QtCore import Qt, pyqtSlot, QObject
from ..widgets.virtual_hardware_widgets import (VirtualLedWidget, VirtualButtonWidget, 
                                                VirtualSliderWidget, VirtualGaugeWidget)
from ...utils.config import (COLOR_TEXT_SECONDARY, APP_FONT_SIZE_SMALL, COLOR_ACCENT_SUCCESS, 
                     COLOR_ACCENT_ERROR)
from ..graphics.graphics_items import GraphicsTransitionItem
from ...core.hardware_link_manager import HardwareLinkManager

logger = logging.getLogger(__name__)

class VirtualHardwareUIManager(QObject):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.mw = main_window
        # Dictionaries to hold references to the created widgets for later access
        self.virtual_leds = {}
        self.virtual_buttons = {}
        self.virtual_sliders = {}
        self.virtual_gauges = {}
        
        # Instantiate the link manager
        self.hardware_link_manager = HardwareLinkManager(main_window)
        self.hardware_link_manager.connectionStatusChanged.connect(self.on_connection_status_changed)
        self.hardware_link_manager.hardwareEventReceived.connect(self.on_hardware_event)
        self.hardware_link_manager.hardwareDataReceived.connect(self.on_hardware_data)
        self.hardware_link_manager.hardwareLinkLost.connect(self.mw.py_sim_ui_manager.on_hardware_link_lost)
        
        logger.info("VirtualHardwareUIManager initialized.")

    def create_dock_widget_contents(self) -> QWidget:
        """Creates the main widget and its contents to be placed in the dock."""
        container_widget = QWidget()
        main_layout = QVBoxLayout(container_widget)
        main_layout.setSpacing(10)

        # --- HIL Connection Group ---
        hil_group = QGroupBox("Hardware-in-the-Loop (HIL) Connection")
        hil_layout = QVBoxLayout(hil_group)
        
        connection_layout = QHBoxLayout()
        connection_layout.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        self.port_combo.setToolTip("Select the serial port for your microcontroller.")
        connection_layout.addWidget(self.port_combo, 1)

        self.refresh_ports_btn = QPushButton("Refresh")
        self.refresh_ports_btn.clicked.connect(self.on_refresh_ports)
        connection_layout.addWidget(self.refresh_ports_btn)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setCheckable(True)
        self.connect_btn.clicked.connect(self.on_connect_toggle)
        connection_layout.addWidget(self.connect_btn)
        
        hil_layout.addLayout(connection_layout)
        
        self.connection_status_label = QLabel("Status: Disconnected")
        self.connection_status_label.setStyleSheet(f"font-size: {APP_FONT_SIZE_SMALL}; color: {COLOR_TEXT_SECONDARY}; padding-left: 5px;")
        hil_layout.addWidget(self.connection_status_label)
        
        main_layout.addWidget(hil_group)
        self.on_refresh_ports() # Initial population of ports

        # --- Create a group for Digital Outputs (LEDs) ---
        led_group = QGroupBox("Digital Outputs")
        led_layout = QFormLayout(led_group)
        led_layout.setSpacing(8)
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
        for i in range(4):
            button_key = f"Button{i}"
            button = VirtualButtonWidget(f"Trigger B{i}")
            self.virtual_buttons[button_key] = button
            button_layout.addWidget(button)
            button.clicked.connect(lambda checked=False, bkey=button_key: self.on_virtual_button_clicked(bkey))
        main_layout.addWidget(button_group)

        # --- Create a group for Analog Inputs (Sliders) ---
        slider_group = QGroupBox("Analog Inputs")
        slider_layout = QFormLayout(slider_group)
        for i in range(2):
            slider_key = f"Slider{i}"
            slider = VirtualSliderWidget(Qt.Horizontal) 
            slider.setRange(0, 1023) # Match 10-bit ADC
            self.virtual_sliders[slider_key] = slider
            slider_layout.addRow(f"A{i}:", slider)
        main_layout.addWidget(slider_group)

        # --- NEW: Create a group for Analog Outputs (Gauges) ---
        gauge_group = QGroupBox("Analog Outputs")
        gauge_layout = QFormLayout(gauge_group)
        for i in range(2):
            gauge_key = f"Gauge{i}"
            gauge = VirtualGaugeWidget()
            self.virtual_gauges[gauge_key] = gauge
            gauge_layout.addRow(f"PWM {i}:", gauge)
        main_layout.addWidget(gauge_group)
        # --- END NEW ---

        main_layout.addStretch()

        disclaimer = QLabel("<i>Connect these components via Item Properties.</i>")
        disclaimer.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {APP_FONT_SIZE_SMALL};")
        disclaimer.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(disclaimer)
        
        return container_widget

    @pyqtSlot()
    def on_refresh_ports(self):
        """Refreshes the list of available serial ports."""
        ports = self.hardware_link_manager.list_available_ports()
        current_selection = self.port_combo.currentText()
        self.port_combo.clear()
        self.port_combo.addItems(ports)
        if current_selection in ports:
            self.port_combo.setCurrentText(current_selection)

        if not ports:
            self.port_combo.addItem("No ports found")
            self.port_combo.setEnabled(False)
            self.connect_btn.setEnabled(False)
        else:
            self.port_combo.setEnabled(True)
            self.connect_btn.setEnabled(True)

    @pyqtSlot(bool)
    def on_connect_toggle(self, checked: bool):
        """Handles the Connect/Disconnect button clicks."""
        if checked:
            port = self.port_combo.currentText()
            if port and "No ports" not in port:
                self.hardware_link_manager.connect_to_port(port)
                self.port_combo.setEnabled(False)
                self.refresh_ports_btn.setEnabled(False)
            else:
                self.connect_btn.setChecked(False)
                self.connection_status_label.setText("Status: Please select a valid port.")
        else:
            self.hardware_link_manager.disconnect_from_port()

    @pyqtSlot(bool, str)
    def on_connection_status_changed(self, is_connected: bool, message: str):
        """Updates the UI based on the connection status from the manager."""
        self.connection_status_label.setText(f"Status: {message}")
        if is_connected:
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setChecked(True)
            self.connection_status_label.setStyleSheet(f"color: {COLOR_ACCENT_SUCCESS}; font-size: {APP_FONT_SIZE_SMALL};")
        else:
            self.connect_btn.setText("Connect")
            self.connect_btn.setChecked(False)
            self.port_combo.setEnabled(True)
            self.refresh_ports_btn.setEnabled(True)
            if "Error" in message or "Failed" in message:
                self.connection_status_label.setStyleSheet(f"color: {COLOR_ACCENT_ERROR}; font-size: {APP_FONT_SIZE_SMALL};")
            else:
                self.connection_status_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {APP_FONT_SIZE_SMALL};")

    @pyqtSlot(str)
    def on_virtual_button_clicked(self, button_key: str):
        logger.info(f"Virtual button '{button_key}' clicked, simulating hardware event.")
        self.on_hardware_event(button_key)

    @pyqtSlot(str)
    def on_hardware_event(self, component_key: str):
        editor = self.mw.current_editor()
        if not editor or not editor.py_fsm_engine or not editor.py_sim_active:
            logger.warning(f"Hardware event from '{component_key}' ignored: simulation is not active.")
            return

        triggered_event = None
        for item in editor.scene.items():
            if isinstance(item, GraphicsTransitionItem):
                item_data = item.get_data()
                if item_data.get('hw_input_map') == component_key:
                    triggered_event = item_data.get('event')
                    if triggered_event:
                        self.mw.py_sim_ui_manager.append_to_action_log(
                            [f"Hardware input '{component_key}' triggered FSM event: '{triggered_event}'"]
                        )
                        self.mw.py_sim_ui_manager.on_trigger_py_event(external_event_name=triggered_event)
                        return
        
        if not triggered_event:
             logger.info(f"Hardware component '{component_key}' was activated, but it's not mapped to any transition's event in the current diagram.")

    @pyqtSlot(str, object)
    def on_hardware_data(self, component_name: str, value: object):
        """
        Receives data from a hardware component and updates the FSM simulator's
        variable context.
        """
        editor = self.mw.current_editor()
        if not editor or not editor.py_fsm_engine or not editor.py_sim_active:
            return

        # Directly update the variable in the simulator's context.
        editor.py_fsm_engine._variables[component_name] = value
        
        # Mirror the physical sensor's value on the virtual UI component if it exists.
        if component_name in self.virtual_sliders:
            slider = self.virtual_sliders[component_name]
            slider.blockSignals(True)
            try:
                # Ensure value is within the slider's range before setting
                slider_val = int(value)
                if slider.minimum() <= slider_val <= slider.maximum():
                    slider.setValue(slider_val)
                else:
                    logger.warning(f"Received value {slider_val} for '{component_name}' is outside slider range ({slider.minimum()}-{slider.maximum()}).")
            except (ValueError, TypeError):
                 logger.warning(f"Could not convert received value '{value}' to an integer for slider '{component_name}'.")
            finally:
                slider.blockSignals(False)
        
        if component_name in self.virtual_gauges:
            gauge = self.virtual_gauges[component_name]
            try:
                gauge_val = int(value)
                if gauge.minimum() <= gauge_val <= gauge.maximum():
                    gauge.setValue(gauge_val)
            except (ValueError, TypeError):
                logger.warning(f"Could not convert received value '{value}' for gauge '{component_name}'.")

        # Trigger a refresh of the variables table in the simulation UI
        self.mw.py_sim_ui_manager.update_dock_ui_contents()