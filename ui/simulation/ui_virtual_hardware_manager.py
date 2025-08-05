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
        self.virtual_leds = {}
        self.virtual_buttons = {}
        self.virtual_sliders = {}
        self.virtual_gauges = {}
        
        self.hardware_link_manager = HardwareLinkManager(main_window)
        self.hardware_link_manager.connectionStatusChanged.connect(self.on_connection_status_changed)
        self.hardware_link_manager.hardwareEventReceived.connect(self.on_hardware_event)
        self.hardware_link_manager.hardwareDataReceived.connect(self.on_hardware_data)
        self.hardware_link_manager.hardwareLinkLost.connect(self.mw.py_sim_ui_manager.on_hardware_link_lost)
        
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_connection_indicator)
        
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
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: #555555;")
        return line

    def _create_status_indicator(self) -> QWidget:
        indicator_widget = QWidget()
        indicator_layout = QHBoxLayout(indicator_widget)
        indicator_layout.setContentsMargins(0, 0, 0, 0)
        
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #ff0000; font-size: 12px;")
        indicator_layout.addWidget(self.status_dot)
        indicator_layout.addStretch()
        
        return indicator_widget

    def create_dock_widget_contents(self) -> QWidget:
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
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
        self.connection_status_label.setStyleSheet("font-family: Arial; color: #cccccc; font-weight: bold;")
        status_layout.addWidget(self.connection_status_label)
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
            slider = VirtualSliderWidget(Qt.Horizontal)
            slider.setRange(0, 1023)
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
                }
            """)
            self.virtual_gauges[gauge_key] = gauge
            gauge_layout.addRow(f"PWM {i}:", gauge)
        io_grid.addWidget(gauge_group, 1, 1)

        io_grid.setColumnStretch(0, 1)
        io_grid.setColumnStretch(1, 1)
        main_layout.addWidget(io_container)

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
        pass

    @pyqtSlot()
    def on_refresh_ports(self):
        ports = self.hardware_link_manager.list_available_ports()
        current_selection = self.port_combo.currentText()
        self.port_combo.clear()
        self.port_combo.addItems(ports)
        if current_selection in ports:
            self.port_combo.setCurrentText(current_selection)
        self.port_combo.setEnabled(bool(ports))
        self.connect_btn.setEnabled(bool(ports))

    @pyqtSlot(bool)
    def on_connect_toggle(self, checked: bool):
        if checked:
            port = self.port_combo.currentText()
            if port:
                self.hardware_link_manager.connect_to_port(port)
                self.port_combo.setEnabled(False)
                self.refresh_ports_btn.setEnabled(False)
                self.connect_btn.setText("🔌 Connecting...")
        else:
            self.hardware_link_manager.disconnect_from_port()
            self.connect_btn.setText("🔌 Disconnecting...")

    @pyqtSlot(bool, str)
    def on_connection_status_changed(self, is_connected: bool, message: str):
        self.connection_status_label.setText(f"Status: {message}")
        if is_connected:
            self.connect_btn.setText("🔌 Disconnect")
            self.connect_btn.setChecked(True)
            self.status_dot.setStyleSheet("color: #2a4d2a; font-size: 12px;")
        else:
            self.connect_btn.setText("🔌 Connect")
            self.connect_btn.setChecked(False)
            self.port_combo.setEnabled(True)
            self.refresh_ports_btn.setEnabled(True)
            self.status_dot.setStyleSheet("color: #ff0000; font-size: 12px;")

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

    @pyqtSlot(str, object)
    def on_hardware_data(self, component_name: str, value: object):
        editor = self.mw.current_editor()
        if not editor or not editor.py_fsm_engine or not editor.py_sim_active:
            return

        editor.py_fsm_engine._variables[component_name] = value
        
        if component_name in self.virtual_sliders:
            slider = self.virtual_sliders[component_name]
            slider.blockSignals(True)
            try:
                slider_val = int(value)
                if slider.minimum() <= slider_val <= slider.maximum():
                    slider.setValue(slider_val)
            except (ValueError, TypeError):
                logger.warning(f"Could not convert value '{value}' to integer for slider '{component_name}'.")
            finally:
                slider.blockSignals(False)
        
        if component_name in self.virtual_gauges:
            gauge = self.virtual_gauges[component_name]
            try:
                gauge_val = int(value)
                if gauge.minimum() <= gauge_val <= gauge.maximum():
                    gauge.setValue(gauge_val)
            except (ValueError, TypeError):
                logger.warning(f"Could not convert value '{value}' for gauge '{component_name}'.")

        self.mw.py_sim_ui_manager.update_dock_ui_contents()