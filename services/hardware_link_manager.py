# fsm_designer_project/services/hardware_link_manager.py
import logging
import serial
import serial.tools.list_ports
from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QTimer

logger = logging.getLogger(__name__)

class SerialWorker(QObject):
    """Worker for handling blocking serial port operations in a separate thread."""
    connectionStatus = pyqtSignal(bool, str)  # is_connected, message
    dataReceived = pyqtSignal(str)  # Raw data line from hardware
    dataSent = pyqtSignal(str)      # Raw data line sent to hardware
    finished = pyqtSignal()
    
    def __init__(self, port, baudrate=115200, parent=None):
        super().__init__(parent)
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self._is_running = True

    @pyqtSlot()
    def run(self):
        """Main worker loop."""
        logger.info(f"SerialWorker: Starting on port {self.port} at {self.baudrate} baud.")
        try:
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1)
            self.connectionStatus.emit(True, f"Successfully connected to {self.port}")
        except serial.SerialException as e:
            logger.error(f"SerialWorker: Failed to open port {self.port}: {e}")
            self.connectionStatus.emit(False, f"Error: {e}")
            self.finished.emit()
            return

        while self._is_running and self.serial_connection.is_open:
            try:
                if self.serial_connection.in_waiting > 0:
                    # Reading a line is the core operation
                    line = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        # Emit the raw line for parsing and for the monitor
                        self.dataReceived.emit(line)
            except serial.SerialException as e:
                logger.error(f"SerialWorker: Serial error on port {self.port}: {e}. Closing.")
                self.connectionStatus.emit(False, f"Device disconnected or error: {e}")
                self._is_running = False
            except Exception as e:
                logger.error(f"SerialWorker: Unexpected error in read loop: {e}", exc_info=True)
            QThread.msleep(20) # Small sleep to prevent busy-waiting

        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        logger.info(f"SerialWorker: Loop finished for port {self.port}.")
        self.finished.emit()

    @pyqtSlot(str)
    def write_data(self, data: str):
        """Writes a string of data to the serial port."""
        if self.serial_connection and self.serial_connection.is_open:
            try:
                # Ensure the command is newline-terminated
                if not data.endswith('\n'):
                    data += '\n'
                self.serial_connection.write(data.encode('utf-8'))
                self.dataSent.emit(data.strip()) # Emit the raw sent data
            except serial.SerialException as e:
                logger.error(f"SerialWorker: Write error on port {self.port}: {e}")
                self.connectionStatus.emit(False, f"Write error: {e}")
                self._is_running = False
            except Exception as e:
                logger.error(f"SerialWorker: Unexpected write error: {e}", exc_info=True)

    @pyqtSlot()
    def stop(self):
        """Signals the worker loop to stop."""
        logger.info("SerialWorker: stop() called.")
        self._is_running = False


class HardwareLinkManager(QObject):
    """Manages the connection to physical hardware via a serial port."""
    connectionStatusChanged = pyqtSignal(bool, str)
    hardwareEventReceived = pyqtSignal(str)
    hardwareDataReceived = pyqtSignal(str, object)
    hardwareLinkLost = pyqtSignal()
    rawDataSent = pyqtSignal(str)
    rawDataReceived = pyqtSignal(str)
    
    def __init__(self, main_window):
        super().__init__(main_window)
        self.mw = main_window
        self.worker: SerialWorker | None = None
        self.thread: QThread | None = None
        self.is_connected = False
        
        self._user_initiated_disconnect = False
        self._last_connected_port: str | None = None
        self._reconnection_timer = QTimer(self)
        self._reconnection_timer.setInterval(3000)
        self._reconnection_timer.timeout.connect(self._attempt_reconnect)

    @staticmethod
    def list_available_ports() -> list[str]:
        """Returns a list of available serial port names."""
        ports = serial.tools.list_ports.comports()
        return sorted([port.device for port in ports])

    @pyqtSlot(str)
    def connect_to_port(self, port_name: str):
        if self.is_connected or self.thread:
            logger.warning("HardwareLinkManager: A connection is already active or in progress.")
            return

        self._user_initiated_disconnect = False
        self._reconnection_timer.stop()
        self._last_connected_port = port_name
        logger.info(f"HardwareLinkManager: Attempting to connect to {port_name}...")
        self.thread = QThread()
        self.worker = SerialWorker(port=port_name)
        self.worker.moveToThread(self.thread)
        
        # Connect worker signals
        self.worker.connectionStatus.connect(self._on_worker_connection_status)
        self.worker.dataReceived.connect(self._parse_incoming_data)
        self.worker.dataSent.connect(self.rawDataSent) # Pass raw sent data up
        self.worker.finished.connect(self.on_worker_finished)

        self.thread.started.connect(self.worker.run)
        self.thread.start()

    @pyqtSlot()
    def disconnect_from_port(self):
        self._user_initiated_disconnect = True
        self._reconnection_timer.stop()
        if self.worker:
            self.worker.stop()

    @pyqtSlot(str)
    def _parse_incoming_data(self, line: str):
        """Parses a line of data from the hardware and emits specific signals."""
        self.rawDataReceived.emit(line) # First, emit the raw data for the monitor
        
        logger.debug(f"HIL RX: {line}")
        parts = line.split(':', 2)
        if len(parts) < 2:
            return

        msg_type = parts[0]
        component_name = parts[1]

        if msg_type == "EVT":
            logger.info(f"Hardware event received from component: '{component_name}'")
            self.hardwareEventReceived.emit(component_name)
        
        elif msg_type == "DATA":
            if len(parts) < 3:
                logger.warning(f"Malformed DATA message received: '{line}'")
                return
            
            payload_str = parts[2]
            try:
                value = float(payload_str) if '.' in payload_str else int(payload_str)
                self.hardwareDataReceived.emit(component_name, value)
            except ValueError:
                logger.warning(f"Could not parse data payload '{payload_str}' for component '{component_name}' as a number.")

    @pyqtSlot(str)
    def send_command(self, command: str):
        if self.is_connected and self.worker:
            QTimer.singleShot(0, lambda: self.worker.write_data(command))
        else:
            logger.warning(f"Attempted to send command '{command}' while disconnected.")

    @pyqtSlot(bool, str)
    def _on_worker_connection_status(self, connected: bool, message: str):
        self.is_connected = connected
        self.connectionStatusChanged.emit(connected, message)

        if not connected:
            if not self._user_initiated_disconnect and self._last_connected_port:
                logger.warning(f"Hardware link lost unexpectedly on port {self._last_connected_port}. Starting reconnection attempts.")
                self.hardwareLinkLost.emit()
                if not self._reconnection_timer.isActive():
                    self._reconnection_timer.start()
            
    @pyqtSlot()
    def on_worker_finished(self):
        logger.info("HardwareLinkManager: Worker has finished. Cleaning up thread.")
        if self.thread:
            self.thread.quit()
            self.thread.wait(1000)
        self.thread = None
        self.worker = None
        if self.is_connected:
            self._on_worker_connection_status(False, "Disconnected.")
            
    @pyqtSlot()
    def _attempt_reconnect(self):
        if self.is_connected or self._user_initiated_disconnect or not self._last_connected_port:
            self._reconnection_timer.stop()
            return

        logger.debug(f"HIL: Attempting to reconnect to {self._last_connected_port}...")
        self.connectionStatusChanged.emit(False, f"Attempting to reconnect to {self._last_connected_port}...")

        available_ports = self.list_available_ports()
        if self._last_connected_port in available_ports:
            logger.info(f"HIL: Port {self._last_connected_port} is available again. Reconnecting.")
            self._reconnection_timer.stop()
            self.connect_to_port(self._last_connected_port)
        else:
            logger.debug(f"HIL: Port {self._last_connected_port} not found in available ports: {available_ports}")