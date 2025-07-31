# fsm_designer_project/ui/simulation/ui_virtual_hardware_manager.py

import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QLabel, 
                             QSlider, QComboBox, QPushButton, QProgressBar, QFrame, QGridLayout,
                             QScrollArea, QSizePolicy, QSpacerItem)
from PyQt5.QtCore import Qt, pyqtSlot, QObject, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor
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
        
        # Status update timer for connection indicator
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_connection_indicator)
        
        logger.info("VirtualHardwareUIManager initialized.")

    def _create_styled_group_box(self, title: str, icon_text: str = "") -> QGroupBox:
        """Creates a styled group box with consistent appearance."""
        group = QGroupBox(f"{icon_text} {title}" if icon_text else title)
        group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: {int(APP_FONT_SIZE_SMALL.replace('pt', '')) + 1}pt;
                border: 2px solid #3a3a3a;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: rgba(255, 255, 255, 0.02);
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #ffffff;
                background-color: transparent;
            }}
        """)
        return group

    def _create_separator_line(self) -> QFrame:
        """Creates a horizontal separator line."""
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("QFrame { color: #555555; }")
        line.setFixedHeight(1)
        return line

    def _create_status_indicator(self) -> QWidget:
        """Creates a visual connection status indicator."""
        indicator_widget = QWidget()
        indicator_layout = QHBoxLayout(indicator_widget)
        indicator_layout.setContentsMargins(0, 0, 0, 0)
        
        self.status_dot = QLabel("●")
        self.status_dot.setFixedSize(12, 12)
        self.status_dot.setStyleSheet(f"color: {COLOR_ACCENT_ERROR}; font-size: 12px;")
        self.status_dot.setAlignment(Qt.AlignCenter)
        
        indicator_layout.addWidget(self.status_dot)
        indicator_layout.addStretch()
        
        return indicator_widget

    def create_dock_widget_contents(self) -> QWidget:
        """Creates the main widget and its contents to be placed in the dock."""
        # Main container with scroll area for better space management
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        container_widget = QWidget()
        main_layout = QVBoxLayout(container_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # --- Enhanced HIL Connection Group ---
        hil_group = self._create_styled_group_box("Hardware-in-the-Loop Connection", "🔗")
        hil_layout = QVBoxLayout(hil_group)
        hil_layout.setSpacing(12)
        
        # Connection configuration row
        config_frame = QFrame()
        config_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        config_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 6px;
                padding: 8px;
            }
        """)
        config_layout = QGridLayout(config_frame)
        config_layout.setSpacing(8)
        
        # Port selection
        port_label = QLabel("Serial Port:")
        port_label.setStyleSheet("font-weight: bold; color: #cccccc;")
        config_layout.addWidget(port_label, 0, 0)
        
        self.port_combo = QComboBox()
        self.port_combo.setToolTip("Select the serial port for your microcontroller")
        self.port_combo.setMinimumWidth(120)
        self.port_combo.setStyleSheet("""
            QComboBox {
                padding: 6px 10px;
                border: 1px solid #555555;
                border-radius: 4px;
                background-color: #2a2a2a;
                color: white;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
        """)
        config_layout.addWidget(self.port_combo, 0, 1)

        self.refresh_ports_btn = QPushButton("⟳ Refresh")
        self.refresh_ports_btn.clicked.connect(self.on_refresh_ports)
        self.refresh_ports_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                border: 1px solid #555555;
                border-radius: 4px;
                background-color: #404040;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #505050;
                border-color: #777777;
            }
            QPushButton:pressed {
                background-color: #303030;
            }
        """)
        config_layout.addWidget(self.refresh_ports_btn, 0, 2)

        self.connect_btn = QPushButton("🔌 Connect")
        self.connect_btn.setCheckable(True)
        self.connect_btn.clicked.connect(self.on_connect_toggle)
        self.connect_btn.setStyleSheet(f"""
            QPushButton {{
                padding: 8px 16px;
                border: 2px solid #555555;
                border-radius: 6px;
                background-color: #2a4d2a;
                color: white;
                font-weight: bold;
                font-size: {int(APP_FONT_SIZE_SMALL.replace('pt','')) + 1}pt;
            }}
            QPushButton:hover {{
                background-color: #345634;
                border-color: {COLOR_ACCENT_SUCCESS};
            }}
            QPushButton:checked {{
                background-color: {COLOR_ACCENT_SUCCESS};
                border-color: {COLOR_ACCENT_SUCCESS};
            }}
            QPushButton:pressed {{
                background-color: #1a3d1a;
            }}
        """)
        config_layout.addWidget(self.connect_btn, 0, 3)
        
        hil_layout.addWidget(config_frame)
        
        # Status display with indicator
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(10, 5, 10, 5)
        
        status_indicator = self._create_status_indicator()
        status_layout.addWidget(status_indicator)
        
        self.connection_status_label = QLabel("Status: Disconnected")
        self.connection_status_label.setStyleSheet(f"""
            font-size: {APP_FONT_SIZE_SMALL}px;
            color: {COLOR_TEXT_SECONDARY};
            font-weight: bold;
        """)
        status_layout.addWidget(self.connection_status_label)
        status_layout.addStretch()
        
        hil_layout.addWidget(status_frame)
        main_layout.addWidget(hil_group)
        
        self.on_refresh_ports()  # Initial population of ports

        # Add separator
        main_layout.addWidget(self._create_separator_line())

        # --- Enhanced I/O Sections in a Grid Layout ---
        io_container = QWidget()
        io_grid = QGridLayout(io_container)
        io_grid.setSpacing(15)

        # Digital Outputs (LEDs) - Top Left
        led_group = self._create_styled_group_box("Digital Outputs", "💡")
        led_layout = QGridLayout(led_group)
        led_layout.setSpacing(10)
        
        for i in range(4):
            led_key = f"LED{i}"
            led = VirtualLedWidget()
            self.virtual_leds[led_key] = led
            
            # Create a frame for each LED with label
            led_frame = QFrame()
            led_frame.setFrameStyle(QFrame.StyledPanel)
            led_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 255, 255, 0.03);
                    border-radius: 4px;
                    padding: 6px;
                }
            """)
            led_frame_layout = QHBoxLayout(led_frame)
            led_frame_layout.setContentsMargins(8, 4, 8, 4)
            
            led_label = QLabel(f"LED {i}:")
            led_label.setStyleSheet("font-weight: bold; color: #dddddd;")
            led_label.setMinimumWidth(50)
            
            led_frame_layout.addWidget(led_label)
            led_frame_layout.addWidget(led)
            led_frame_layout.addStretch()
            
            row, col = divmod(i, 2)
            led_layout.addWidget(led_frame, row, col)
        
        io_grid.addWidget(led_group, 0, 0)

        # Digital Inputs (Buttons) - Top Right
        button_group = self._create_styled_group_box("Digital Inputs", "🔘")
        button_layout = QGridLayout(button_group)
        button_layout.setSpacing(8)
        
        for i in range(4):
            button_key = f"Button{i}"
            button = VirtualButtonWidget(f"🔵 Trigger B{i}")
            button.setStyleSheet("""
                QPushButton {
                    padding: 8px 12px;
                    border: 2px solid #444444;
                    border-radius: 6px;
                    background-color: #333333;
                    color: white;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #404040;
                    border-color: #666666;
                }
                QPushButton:pressed {
                    background-color: #555555;
                    border-color: #888888;
                }
            """)
            self.virtual_buttons[button_key] = button
            button.clicked.connect(lambda checked=False, bkey=button_key: self.on_virtual_button_clicked(bkey))
            
            row, col = divmod(i, 2)
            button_layout.addWidget(button, row, col)
        
        io_grid.addWidget(button_group, 0, 1)

        # Analog Inputs (Sliders) - Bottom Left
        slider_group = self._create_styled_group_box("Analog Inputs", "🎚️")
        slider_layout = QFormLayout(slider_group)
        slider_layout.setSpacing(12)
        
        for i in range(2):
            slider_key = f"Slider{i}"
            
            # Create container for slider with value display
            slider_container = QWidget()
            slider_container_layout = QHBoxLayout(slider_container)
            slider_container_layout.setContentsMargins(0, 0, 0, 0)
            
            slider = VirtualSliderWidget(Qt.Horizontal)
            slider.setRange(0, 1023)  # Match 10-bit ADC
            slider.setStyleSheet("""
                QSlider::groove:horizontal {
                    border: 1px solid #444444;
                    height: 8px;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #2a2a2a, stop:1 #4a4a4a);
                    border-radius: 4px;
                }
                QSlider::handle:horizontal {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #66bb6a, stop:1 #4caf50);
                    border: 1px solid #2e7d32;
                    width: 18px;
                    margin: -5px 0;
                    border-radius: 9px;
                }
                QSlider::handle:horizontal:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #81c784, stop:1 #66bb6a);
                }
            """)
            
            # Value display label
            value_label = QLabel("0")
            value_label.setFixedWidth(40)
            value_label.setAlignment(Qt.AlignCenter)
            value_label.setStyleSheet("""
                QLabel {
                    border: 1px solid #555555;
                    border-radius: 3px;
                    background-color: #2a2a2a;
                    color: #4caf50;
                    font-weight: bold;
                    padding: 2px;
                }
            """)
            
            # Connect slider to update value label
            slider.valueChanged.connect(lambda val, lbl=value_label: lbl.setText(str(val)))
            
            slider_container_layout.addWidget(slider, 1)
            slider_container_layout.addWidget(value_label)
            
            self.virtual_sliders[slider_key] = slider
            slider_layout.addRow(f"A{i}:", slider_container)
        
        io_grid.addWidget(slider_group, 1, 0)

        # Analog Outputs (Gauges) - Bottom Right
        gauge_group = self._create_styled_group_box("Analog Outputs", "📊")
        gauge_layout = QFormLayout(gauge_group)
        gauge_layout.setSpacing(12)
        
        for i in range(2):
            gauge_key = f"Gauge{i}"
            
            # Create container for gauge with value display
            gauge_container = QWidget()
            gauge_container_layout = QVBoxLayout(gauge_container)
            gauge_container_layout.setContentsMargins(0, 0, 0, 0)
            
            gauge = VirtualGaugeWidget()
            gauge.setStyleSheet("""
                QProgressBar {
                    border: 2px solid #444444;
                    border-radius: 6px;
                    background-color: #2a2a2a;
                    text-align: center;
                    font-weight: bold;
                    color: white;
                }
                QProgressBar::chunk {
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #ff9800, stop:1 #ff5722);
                    border-radius: 4px;
                    margin: 0.5px;
                }
            """)
            
            gauge_container_layout.addWidget(gauge)
            
            self.virtual_gauges[gauge_key] = gauge
            gauge_layout.addRow(f"PWM {i}:", gauge_container)
        
        io_grid.addWidget(gauge_group, 1, 1)

        # Set column stretch to make sections equal width
        io_grid.setColumnStretch(0, 1)
        io_grid.setColumnStretch(1, 1)
        
        main_layout.addWidget(io_container)

        # Add flexible space
        main_layout.addStretch()

        # Enhanced disclaimer with better styling
        disclaimer_frame = QFrame()
        disclaimer_frame.setFrameStyle(QFrame.StyledPanel)
        disclaimer_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 165, 0, 0.1);
                border: 1px solid rgba(255, 165, 0, 0.3);
                border-radius: 6px;
                padding: 8px;
            }
        """)
        disclaimer_layout = QHBoxLayout(disclaimer_frame)
        
        disclaimer_icon = QLabel("ℹ️")
        disclaimer_icon.setStyleSheet("font-size: 16px;")
        disclaimer_layout.addWidget(disclaimer_icon)
        
        disclaimer = QLabel("Connect hardware components via FSM Item Properties")
        disclaimer.setStyleSheet(f"""
            color: {COLOR_TEXT_SECONDARY};
            font-size: {APP_FONT_SIZE_SMALL}px;
            font-style: italic;
            font-weight: bold;
        """)
        disclaimer_layout.addWidget(disclaimer)
        disclaimer_layout.addStretch()
        
        main_layout.addWidget(disclaimer_frame)
        
        # Set the container as the scroll area's widget
        scroll_area.setWidget(container_widget)
        
        # Return the scroll area as the main widget
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(scroll_area)
        
        return wrapper

    def update_connection_indicator(self):
        """Updates the connection status indicator with animation."""
        if hasattr(self, 'status_dot'):
            # This could be enhanced with blinking animation for connecting state
            pass

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
                self.connect_btn.setText("🔌 Connecting...")
            else:
                self.connect_btn.setChecked(False)
                self.connection_status_label.setText("Status: Please select a valid port.")
        else:
            self.hardware_link_manager.disconnect_from_port()
            self.connect_btn.setText("🔌 Disconnecting...")

    @pyqtSlot(bool, str)
    def on_connection_status_changed(self, is_connected: bool, message: str):
        """Updates the UI based on the connection status from the manager."""
        self.connection_status_label.setText(f"Status: {message}")
        
        if is_connected:
            self.connect_btn.setText("🔌 Disconnect")
            self.connect_btn.setChecked(True)
            self.status_dot.setStyleSheet(f"color: {COLOR_ACCENT_SUCCESS}; font-size: 12px;")
            self.connection_status_label.setStyleSheet(f"""
                color: {COLOR_ACCENT_SUCCESS};
                font-size: {APP_FONT_SIZE_SMALL}px;
                font-weight: bold;
            """)
        else:
            self.connect_btn.setText("🔌 Connect")
            self.connect_btn.setChecked(False)
            self.port_combo.setEnabled(True)
            self.refresh_ports_btn.setEnabled(True)
            
            if "Error" in message or "Failed" in message:
                self.status_dot.setStyleSheet(f"color: {COLOR_ACCENT_ERROR}; font-size: 12px;")
                self.connection_status_label.setStyleSheet(f"""
                    color: {COLOR_ACCENT_ERROR};
                    font-size: {APP_FONT_SIZE_SMALL}px;
                    font-weight: bold;
                """)
            else:
                self.status_dot.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
                self.connection_status_label.setStyleSheet(f"""
                    color: {COLOR_TEXT_SECONDARY};
                    font-size: {APP_FONT_SIZE_SMALL}px;
                    font-weight: bold;
                """)

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