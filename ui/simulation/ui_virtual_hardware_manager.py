import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QLabel, 
                             QSlider, QComboBox, QPushButton, QProgressBar, QFrame, QGridLayout,
                             QScrollArea, QSizePolicy, QSpacerItem)
from PyQt6.QtCore import Qt, pyqtSlot, QObject, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor
from ..widgets.virtual_hardware_widgets import (VirtualLedWidget, VirtualButtonWidget, 
                                                VirtualSliderWidget, VirtualGaugeWidget)
from ...utils.theme_config import theme_config
from ...utils import config
from ..graphics.graphics_items import GraphicsTransitionItem
from ...services.hardware_link_manager import HardwareLinkManager

logger = logging.getLogger(__name__)

class VirtualHardwareUIManager(QObject):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.mw = main_window
        self.virtual_leds = {}
        self.virtual_buttons = {}
        self.virtual_sliders = {}
        self.virtual_gauges = {}
        
        self.hardware_link_manager = HardwareLinkManager(main_window)
        self.hardware_link_manager.connectionStatusChanged.connect(self.on_connection_status_changed)
        self.hardware_link_manager.hardwareEventReceived.connect(self.on_hardware_event)
        self.hardware_link_manager.hardwareDataReceived.connect(self.on_hardware_data)
        # Keep existing behavior, also update our own UI when link is lost.
        self.hardware_link_manager.hardwareLinkLost.connect(self.mw.py_sim_ui_manager.on_hardware_link_lost)
        self.hardware_link_manager.hardwareLinkLost.connect(self.on_hardware_link_lost)
        
        # Connection indicator animation state
        self.status_timer = QTimer()
        self.status_timer.setInterval(80)  # smooth but not too frequent
        self.status_timer.timeout.connect(self.update_connection_indicator)
        self._connection_state = 'disconnected'  # 'disconnected' | 'connecting' | 'connected'
        self._pulse_t = 0.0
        self._pulse_dir = 1.0
        
        logger.info("VirtualHardwareUIManager initialized.")

    def _create_styled_group_box(self, title: str, icon_text: str = "") -> QGroupBox:
        group = QGroupBox(f"{icon_text} {title}" if icon_text else title)
        group.setStyleSheet("""
            QGroupBox {
                font-family: Arial;
                font-weight: bold;
                font-size: 12pt;
                border: 1px solid #555555;
                border-radius: 6px;
                margin-top: 10px;
                padding: 10px;
                background-color: #3a3a3a;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 6px;
                background-color: #3a3a3a;
            }
        """)
        return group

    def _create_separator_line(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("color: #555555;")
        return line

    def _create_status_indicator(self) -> QWidget:
        indicator_widget = QWidget()
        indicator_layout = QHBoxLayout(indicator_widget)
        indicator_layout.setContentsMargins(0, 0, 0, 0)
        
        self.status_dot = QLabel("●")
        self.status_dot.setToolTip("Connection status")
        self.status_dot.setAccessibleName("Connection Status Indicator")
        self.status_dot.setStyleSheet("color: #ff0000; font-size: 12px;")
        indicator_layout.addWidget(self.status_dot)
        indicator_layout.addStretch()
        
        return indicator_widget

    def _set_state(self, state: str, message: str = None):
        """
        Centralized connection state handler.
        state: 'disconnected' | 'connecting' | 'connected'
        """
        self._connection_state = state
        if message:
            self.connection_status_label.setText(f"Status: {message}")
        
        if state == 'connecting':
            self._pulse_t = 0.0
            self._pulse_dir = 1.0
            if not self.status_timer.isActive():
                self.status_timer.start()
            # Button communicates in-progress action
            self.connect_btn.setText("🔌 Connecting...")
            self.connect_btn.setChecked(True)
            self.connect_btn.setToolTip("Connecting... Click again to cancel")
            # Lock port selector while connecting
            self.port_combo.setEnabled(False)
            self.refresh_ports_btn.setEnabled(False)

        elif state == 'connected':
            self._pulse_t = 0.0
            self._pulse_dir = 1.0
            # Slow heartbeat to indicate link is alive
            if not self.status_timer.isActive():
                self.status_timer.start()
            self.connect_btn.setText("🔌 Disconnect")
            self.connect_btn.setChecked(True)
            self.connect_btn.setToolTip("Disconnect from hardware")
            # Remember last port if config supports it
            try:
                if hasattr(config, 'set'):
                    config.set('hardware.last_port', self.port_combo.currentText())
                elif hasattr(config, '__setitem__'):
                    config['hardware.last_port'] = self.port_combo.currentText()
                if hasattr(config, 'save'):
                    config.save()
            except Exception:
                pass

        elif state == 'disconnected':
            self.status_timer.stop()
            # Red static indicator
            self.status_dot.setStyleSheet("color: #ff3b3b; font-size: 12px;")
            self.connect_btn.setText("🔌 Connect")
            self.connect_btn.setChecked(False)
            self.connect_btn.setToolTip("Connect to selected serial port")
            # Unlock inputs
            self.port_combo.setEnabled(True)
            self.refresh_ports_btn.setEnabled(True)

    def _lerp_color(self, c1, c2, t: float) -> str:
        """Linear interpolate two RGB tuples, return hex string."""
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _set_status_dot_color(self, rgb_tuple):
        hex_color = f"#{rgb_tuple[0]:02x}{rgb_tuple[1]:02x}{rgb_tuple[2]:02x}"
        self.status_dot.setStyleSheet(f"color: {hex_color}; font-size: 12px;")

    def create_dock_widget_contents(self) -> QWidget:
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #2a2a2a; }")
        
        container_widget = QWidget()
        main_layout = QVBoxLayout(container_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # HIL Connection Group
        hil_group = self._create_styled_group_box("Hardware-in-the-Loop Connection", "🔗")
        hil_layout = QVBoxLayout(hil_group)
        
        config_frame = QFrame()
        config_frame.setStyleSheet("background-color: #4a4a4a; border-radius: 4px; padding: 6px;")
        config_layout = QGridLayout(config_frame)
        
        port_label = QLabel("Serial Port:")
        port_label.setStyleSheet("font-family: Arial; font-weight: bold; color: #cccccc;")
        config_layout.addWidget(port_label, 0, 0)
        
        self.port_combo = QComboBox()
        self.port_combo.setAccessibleName("Serial Port Selection")
        self.port_combo.setToolTip("Select a serial port for the hardware link")
        self.port_combo.setStyleSheet("""
            QComboBox {
                padding: 4px 8px;
                border: 1px solid #555555;
                border-radius: 4px;
                background-color: #2a2a2a;
                color: #ffffff;
                font-family: Arial;
            }
            QComboBox:hover { background-color: #333333; }
        """)
        config_layout.addWidget(self.port_combo, 0, 1)
        
        self.refresh_ports_btn = QPushButton("⟳ Refresh")
        self.refresh_ports_btn.setAccessibleName("Refresh Ports")
        self.refresh_ports_btn.setToolTip("Scan for available serial ports")
        self.refresh_ports_btn.setStyleSheet("""
            QPushButton {
                padding: 4px 10px;
                border: 1px solid #555555;
                border-radius: 4px;
                background-color: #404040;
                color: #ffffff;
                font-family: Arial;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #505050; }
        """)
        self.refresh_ports_btn.clicked.connect(self.on_refresh_ports)
        config_layout.addWidget(self.refresh_ports_btn, 0, 2)
        
        self.connect_btn = QPushButton("🔌 Connect")
        self.connect_btn.setCheckable(True)
        self.connect_btn.setAccessibleName("Connect Button")
        self.connect_btn.setToolTip("Connect to selected serial port")
        self.connect_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                border: 1px solid #555555;
                border-radius: 4px;
                background-color: #404040;
                color: #ffffff;
                font-family: Arial;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #505050; }
            QPushButton:checked { background-color: #2a4d2a; }
        """)
        self.connect_btn.clicked.connect(self.on_connect_toggle)
        config_layout.addWidget(self.connect_btn, 0, 3)
        
        hil_layout.addWidget(config_frame)
        
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        status_layout.addWidget(self._create_status_indicator())
        
        self.connection_status_label = QLabel("Status: Disconnected")
        self.connection_status_label.setAccessibleName("Connection Status Label")
        self.connection_status_label.setStyleSheet("font-family: Arial; color: #cccccc; font-weight: bold;")
        status_layout.addWidget(self.connection_status_label)
        status_layout.addStretch()
        hil_layout.addWidget(status_frame)
        main_layout.addWidget(hil_group)
        
        self.on_refresh_ports()

        main_layout.addWidget(self._create_separator_line())

        # I/O Sections
        io_container = QWidget()
        io_grid = QGridLayout(io_container)
        io_grid.setSpacing(10)

        # Digital Outputs (LEDs)
        led_group = self._create_styled_group_box("Digital Outputs", "💡")
        led_layout = QGridLayout(led_group)
        for i in range(4):
            led_key = f"LED{i}"
            led = VirtualLedWidget()
            led.setAccessibleName(f"LED {i}")
            led.setToolTip(f"Digital output indicator LED {i}")
            self.virtual_leds[led_key] = led
            led_frame = QFrame()
            led_frame.setStyleSheet("background-color: #4a4a4a; border-radius: 4px; padding: 4px;")
            led_frame_layout = QHBoxLayout(led_frame)
            led_label = QLabel(f"LED {i}:")
            led_label.setStyleSheet("font-family: Arial; color: #cccccc;")
            led_frame_layout.addWidget(led_label)
            led_frame_layout.addWidget(led)
            led_layout.addWidget(led_frame, i // 2, i % 2)
        io_grid.addWidget(led_group, 0, 0)

        # Digital Inputs (Buttons)
        button_group = self._create_styled_group_box("Digital Inputs", "🔘")
        button_layout = QGridLayout(button_group)
        for i in range(4):
            button_key = f"Button{i}"
            button = VirtualButtonWidget(f"Trigger B{i}")
            button.setAccessibleName(f"Virtual Button {i}")
            button.setToolTip(f"Trigger mapped hardware event from Button{i}")
            button.setStyleSheet("""
                QPushButton {
                    padding: 6px 10px;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    background-color: #404040;
                    color: #ffffff;
                    font-family: Arial;
                }
                QPushButton:hover { background-color: #505050; }
                QPushButton:pressed { background-color: #333333; }
            """)
            self.virtual_buttons[button_key] = button
            button.clicked.connect(lambda checked=False, bkey=button_key: self.on_virtual_button_clicked(bkey))
            button_layout.addWidget(button, i // 2, i % 2)
        io_grid.addWidget(button_group, 0, 1)

        # Analog Inputs (Sliders)
        slider_group = self._create_styled_group_box("Analog Inputs", "🎚️")
        slider_layout = QFormLayout(slider_group)
        for i in range(2):
            slider_key = f"Slider{i}"
            slider_container = QWidget()
            slider_container_layout = QHBoxLayout(slider_container)
            slider = VirtualSliderWidget(Qt.Orientation.Horizontal)
            slider.setRange(0, 1023)
            slider.setAccessibleName(f"Analog Input Slider A{i}")
            slider.setToolTip(f"Simulate analog input A{i} (0-1023)")
            slider.setStyleSheet("""
                QSlider::groove:horizontal {
                    height: 6px;
                    background: #4a4a4a;
                    border-radius: 3px;
                }
                QSlider::handle:horizontal {
                    background: #cccccc;
                    border: 1px solid #555555;
                    width: 12px;
                    margin: -3px 0;
                    border-radius: 6px;
                }
                QSlider::handle:horizontal:hover { background: #ffffff; }
            """)
            value_label = QLabel("0")
            value_label.setStyleSheet("font-family: Arial; color: #cccccc; padding: 2px;")
            slider.valueChanged.connect(lambda val, lbl=value_label: lbl.setText(str(val)))
            slider_container_layout.addWidget(slider)
            slider_container_layout.addWidget(value_label)
            self.virtual_sliders[slider_key] = slider
            slider_layout.addRow(f"A{i}:", slider_container)
        io_grid.addWidget(slider_group, 1, 0)

        # Analog Outputs (Gauges)
        gauge_group = self._create_styled_group_box("Analog Outputs", "📊")
        gauge_layout = QFormLayout(gauge_group)
        for i in range(2):
            gauge_key = f"Gauge{i}"
            gauge = VirtualGaugeWidget()
            gauge.setAccessibleName(f"Analog Output Gauge PWM {i}")
            gauge.setToolTip(f"Analog output PWM {i} level")
            gauge.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #555555;
                    border-radius: 4px;
                    background-color: #4a4a4a;
                    color: #ffffff;
                    font-family: Arial;
                }
                QProgressBar::chunk {
                    background-color: #cccccc;
                    border-radius: 3px;
                    margin: 0.5px;
                }
            """)
            self.virtual_gauges[gauge_key] = gauge
            gauge_layout.addRow(f"PWM {i}:", gauge)
        io_grid.addWidget(gauge_group, 1, 1)

        io_grid.setColumnStretch(0, 1)
        io_grid.setColumnStretch(1, 1)
        main_layout.addWidget(io_container)

        # Quick actions row (Reset I/O)
        actions_frame = QFrame()
        actions_frame.setStyleSheet("background-color: #3a3a3a; border: 1px solid #555555; border-radius: 4px; padding: 6px;")
        actions_layout = QHBoxLayout(actions_frame)
        actions_layout.addStretch()
        self.reset_io_btn = QPushButton("↺ Reset I/O")
        self.reset_io_btn.setAccessibleName("Reset IO Button")
        self.reset_io_btn.setToolTip("Reset sliders to 0 and gauges to 0%")
        self.reset_io_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                border: 1px solid #555555;
                border-radius: 4px;
                background-color: #404040;
                color: #ffffff;
                font-family: Arial;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #505050; }
        """)
        self.reset_io_btn.clicked.connect(self.on_reset_io_clicked)
        actions_layout.addWidget(self.reset_io_btn)
        main_layout.addWidget(actions_frame)

        main_layout.addStretch()

        # Disclaimer
        disclaimer_frame = QFrame()
        disclaimer_frame.setStyleSheet("background-color: #3a3a3a; border: 1px solid #555555; border-radius: 4px; padding: 6px;")
        disclaimer_layout = QHBoxLayout(disclaimer_frame)
        disclaimer_icon = QLabel("ℹ️")
        disclaimer_icon.setStyleSheet("font-size: 14px;")
        disclaimer_layout.addWidget(disclaimer_icon)
        disclaimer = QLabel("Connect hardware components via FSM Item Properties")
        disclaimer.setStyleSheet("font-family: Arial; color: #cccccc; font-style: italic;")
        disclaimer_layout.addWidget(disclaimer)
        main_layout.addWidget(disclaimer_frame)

        scroll_area.setWidget(container_widget)
        
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(scroll_area)
        
        return wrapper

    def update_connection_indicator(self):
        """
        Animate the status dot according to connection state.
        - connecting: amber pulse
        - connected: subtle green heartbeat
        - disconnected: timer stopped elsewhere, dot stays red
        """
        # Pulse parameter oscillates between 0 and 1
        self._pulse_t += 0.06 * self._pulse_dir
        if self._pulse_t >= 1.0:
            self._pulse_t = 1.0
            self._pulse_dir = -1.0
        elif self._pulse_t <= 0.0:
            self._pulse_t = 0.0
            self._pulse_dir = 1.0

        if self._connection_state == 'connecting':
            base = (192, 127, 0)   # amber base
            hi = (240, 180, 41)    # amber highlight
            hex_color = self._lerp_color(base, hi, self._pulse_t)
            self.status_dot.setStyleSheet(f"color: {hex_color}; font-size: 12px;")
        elif self._connection_state == 'connected':
            base = (42, 77, 42)    # dark green
            hi = (85, 170, 85)     # brighter green
            hex_color = self._lerp_color(base, hi, self._pulse_t * 0.65)  # subtle heartbeat
            self.status_dot.setStyleSheet(f"color: {hex_color}; font-size: 12px;")

    @pyqtSlot()
    def on_refresh_ports(self):
        try:
            ports = self.hardware_link_manager.list_available_ports()
        except Exception as e:
            logger.exception("Error listing ports: %s", e)
            ports = []

        # Optional: recall last used port if config supports it
        last_port = None
        try:
            if hasattr(config, 'get'):
                last_port = config.get('hardware.last_port', None)
            elif hasattr(config, '__getitem__'):
                last_port = config.get('hardware.last_port', None)
        except Exception:
            last_port = None

        current_selection = self.port_combo.currentText()
        self.port_combo.clear()
        if ports:
            self.port_combo.addItems(ports)
            # Prefer current, then last used
            if current_selection in ports:
                self.port_combo.setCurrentText(current_selection)
            elif last_port in ports:
                self.port_combo.setCurrentText(last_port)
            self.port_combo.setEnabled(True)
            self.connect_btn.setEnabled(True)
            self.port_combo.setToolTip("Select a serial port for the hardware link")
        else:
            # No ports available: disable and inform user
            self.port_combo.addItem("No ports found")
            self.port_combo.setEnabled(False)
            self.connect_btn.setEnabled(False)
            self.port_combo.setToolTip("No serial ports detected")

    @pyqtSlot(bool)
    def on_connect_toggle(self, checked: bool):
        if checked:
            port = self.port_combo.currentText()
            if not port or port == "No ports found":
                self.connect_btn.setChecked(False)
                return
            try:
                # Enter 'connecting' state immediately for responsive UX
                self._set_state('connecting', f"Connecting to {port}...")
                self.hardware_link_manager.connect_to_port(port)
            except Exception as e:
                logger.exception("Error initiating connection: %s", e)
                self._set_state('disconnected', "Disconnected")
        else:
            try:
                self.connection_status_label.setText("Status: Disconnecting...")
                self.connect_btn.setText("🔌 Disconnecting...")
                self.hardware_link_manager.disconnect_from_port()
            except Exception as e:
                logger.exception("Error initiating disconnect: %s", e)
                # Fall back to disconnected state
                self._set_state('disconnected', "Disconnected")

    @pyqtSlot(bool, str)
    def on_connection_status_changed(self, is_connected: bool, message: str):
        # Update label with message from backend
        self.connection_status_label.setText(f"Status: {message}")
        if is_connected:
            self._set_state('connected', message)
        else:
            self._set_state('disconnected', message)

    @pyqtSlot()
    def on_hardware_link_lost(self):
        # Ensure our UI reflects link loss immediately
        self._set_state('disconnected', "Link lost")

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
            logger.info(f"Hardware component '{component_key}' was activated, but it's not mapped to any transition's event.")

    def _set_led_widget_state(self, widget: QWidget, on: bool):
        """
        Try common APIs to set a LED state without knowing exact implementation.
        """
        try:
            if hasattr(widget, "set_on"):
                widget.set_on(on)
            elif hasattr(widget, "setChecked"):
                widget.setChecked(on)
            elif hasattr(widget, "setValue"):
                widget.setValue(100 if on else 0)
        except Exception as e:
            logger.debug("Could not set LED state: %s", e)

    @pyqtSlot(str, object)
    def on_hardware_data(self, component_name: str, value: object):
        editor = self.mw.current_editor()
        if not editor or not editor.py_fsm_engine or not editor.py_sim_active:
            return

        # reflect variables in engine
        try:
            editor.py_fsm_engine._variables[component_name] = value
        except Exception:
            pass
        
        # Synchronize sliders (analog inputs)
        if component_name in self.virtual_sliders:
            slider = self.virtual_sliders[component_name]
            slider.blockSignals(True)
            try:
                slider_val = int(value)
                slider_val = max(slider.minimum(), min(slider.maximum(), slider_val))
                slider.setValue(slider_val)
            except (ValueError, TypeError):
                logger.warning(f"Could not convert value '{value}' to integer for slider '{component_name}'.")
            finally:
                slider.blockSignals(False)
        
        # Synchronize gauges (analog outputs)
        if component_name in self.virtual_gauges:
            gauge = self.virtual_gauges[component_name]
            try:
                gauge_val = int(value)
                gauge_val = max(gauge.minimum(), min(gauge.maximum(), gauge_val))
                gauge.setValue(gauge_val)
            except (ValueError, TypeError):
                logger.warning(f"Could not convert value '{value}' for gauge '{component_name}'.")

        # Synchronize LEDs (digital outputs)
        if component_name in self.virtual_leds:
            led = self.virtual_leds[component_name]
            try:
                # interpret numbers/strings as boolean where possible
                if isinstance(value, str):
                    on = value.strip().lower() in ("1", "true", "on", "yes", "high")
                else:
                    on = bool(value)
                self._set_led_widget_state(led, on)
            except Exception as e:
                logger.debug("Error updating LED '%s': %s", component_name, e)

        # Update any dependent UI (kept from your original behavior)
        self.mw.py_sim_ui_manager.update_dock_ui_contents()
        
    @pyqtSlot()
    def on_send_serial_data(self):
        """Slot to handle sending data from the serial monitor UI."""
        main_window = self.mw
        if not hasattr(main_window, 'serial_input_edit'):
            return

        text_to_send = main_window.serial_input_edit.text()
        if text_to_send:
            self.hardware_link_manager.send_command(text_to_send)
            main_window.serial_input_edit.clear()

    @pyqtSlot()
    def on_reset_io_clicked(self):
        """Reset sliders to 0 and gauges to 0, leaving LEDs as-is (outputs)."""
        for key, slider in self.virtual_sliders.items():
            try:
                slider.blockSignals(True)
                slider.setValue(slider.minimum())
            finally:
                slider.blockSignals(False)

        for key, gauge in self.virtual_gauges.items():
            try:
                # Assuming minimum is 0; clamp just in case
                gauge.setValue(max(gauge.minimum(), 0))
            except Exception:
                pass