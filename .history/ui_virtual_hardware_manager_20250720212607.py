# fsm_designer_project/ui_virtual_hardware_manager.py

import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLabel, QComboBox, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt, pyqtSlot
from .virtual_hardware_widgets import VirtualLedWidget, VirtualButtonWidget, VirtualSliderWidget
from .config import COLOR_TEXT_SECONDARY, APP_FONT_SIZE_SMALL, COLOR_ACCENT_SUCCESS, COLOR_ACCENT_ERROR
from .graphics_items import GraphicsTransitionItem
# --- NEW IMPORT ---
from .hardware_link_manager import HardwareLinkManager

logger = logging.getLogger(__name__)

class VirtualHardwareUIManager:
    def __init__(self, main_window):
        self.mw = main_window
        self.virtual_leds = {}
        self.virtual_buttons = {}
        self.virtual_sliders = {}
        
        # --- NEW: Instantiate the link manager ---
        self.hardware_link_manager = HardwareLinkManager(main_window)
        self.hardware_link_manager.connectionStatusChanged.connect(self.on_connection_status_changed)

        logger.info("VirtualHardwareUIManager initialized.")

    def create_dock_widget_contents(self) -> QWidget:
        """Creates the main widget and its contents to be placed in the dock."""
        container_widget = QWidget()
        main_layout = QVBoxLayout(container_widget)
        main_layout.setSpacing(10)

        # --- NEW: HIL Connection Group ---
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
        self.on_refresh_ports() # Initial population
        # --- END NEW ---
        
        # ... (rest of the method remains the same) ...
        led_group = QGroupBox("Digital Outputs")
        # ...
        main_layout.addWidget(led_group)
        button_group = QGroupBox("Digital Inputs")
        # ...
        main_layout.addWidget(button_group)
        slider_group = QGroupBox("Analog Inputs")
        # ...
        main_layout.addWidget(slider_group)
        main_layout.addStretch()
        disclaimer = QLabel("<i>Connect these components via Item Properties.</i>")
        # ...
        main_layout.addWidget(disclaimer)
        
        return container_widget

    # --- NEW SLOTS for HIL UI ---
    @pyqtSlot()
    def on_refresh_ports(self):
        """Refreshes the list of available serial ports."""
        ports = self.hardware_link_manager.list_available_ports()
        self.port_combo.clear()
        self.port_combo.addItems(ports)
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
        if checked: # User wants to connect
            port = self.port_combo.currentText()
            if port and "No ports" not in port:
                self.hardware_link_manager.connect_to_port(port)
                self.port_combo.setEnabled(False)
                self.refresh_ports_btn.setEnabled(False)
            else:
                self.connect_btn.setChecked(False) # Revert button state
                self.connection_status_label.setText("Status: Please select a valid port.")
        else: # User wants to disconnect
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
    # --- END NEW SLOTS ---

    @pyqtSlot(str)
    def on_virtual_button_clicked(self, button_key: str):
        # ... (this method remains unchanged for now, will be used in Phase 2) ...
        pass