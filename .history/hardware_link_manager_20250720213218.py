# fsm_designer_project/hardware_link_manager.py
import logging
import serial
import serial.tools.list_ports
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QTimer

logger = logging.getLogger(__name__)

class SerialWorker(QObject):
    """Worker for handling blocking serial port operations in a separate thread."""
    connectionStatus = pyqtSignal(bool, str)  # is_connected, message
    dataReceived = pyqtSignal(str)  # Raw data line from hardware
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
                        # Emit the raw line for potential debugging/monitoring
                        self.dataReceived.emit(line)
            except serial.SerialException as e:
                logger.error(f"SerialWorker: Serial error on port {self.port}: {e}. Closing.")
                self.connectionStatus.emit(False, f"Device disconnected or error: {e}")
                self._is_running = False
            except Exception as e:
                logger.error(f"SerialWorker: Unexpected error in read loop: {e}", exc_info=True)
                # Don't stop for unexpected errors, just log them
            QThread.msleep(20) # Small sleep to prevent busy-waiting

        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        logger.info(f"SerialWorker: Loop finished for port {self.port}.")
        self.finished.emit()

    @pyqtSlot()
    def stop(self):
        """Signals the worker loop to stop."""
        logger.info("SerialWorker: stop() called.")
        self._is_running = False


class HardwareLinkManager(QObject):
    """Manages the connection to physical hardware via a serial port."""
    connectionStatusChanged = pyqtSignal(bool, str) # is_connected, message
    hardwareEventReceived = pyqtSignal(str) # Emits the name of the component that triggered an event (e.g., "Button0")
    
    def __init__(self, main_window):
        super().__init__(main_window)
        self.mw = main_window
        self.worker: SerialWorker | None = None
        self.thread: QThread | None = None
        self.is_connected = False

    @staticmethod
    def list_available_ports() -> list[str]:
        """Returns a list of available serial port names."""
        ports = serial.tools.list_ports.comports()
        return sorted([port.device for port in ports])

    @pyqtSlot(str)
    def connect_to_port(self, port_name: str):
        if self.is_connected or self.thread:
            logger.warning("HardwareLinkManager: A connection is already active or in progress. Please disconnect first.")
            return

        logger.info(f"HardwareLinkManager: Attempting to connect to {port_name}...")
        self.thread = QThread()
        self.worker = SerialWorker(port=port_name)
        self.worker.moveToThread(self.thread)
        
        # Connect worker signals
        self.worker.connectionStatus.connect(self._on_worker_connection_status)
        self.worker.dataReceived.connect(self._parse_incoming_data)
        self.worker.finished.connect(self.on_worker_finished)

        # Start the thread and the worker's run loop
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    @pyqtSlot()
    def disconnect_from_port(self):
        if self.worker:
            self.worker.stop()
        # The on_worker_finished slot will handle cleanup.

    @pyqtSlot(str)
    def _parse_incoming_data(self, line: str):
        """Parses a line of data from the hardware and emits signals accordingly."""
        # Protocol: EVT:<COMPONENT_NAME>:<PAYLOAD>
        # Example:  EVT:Button0:PRESSED
        logger.debug(f"HIL RX: {line}")
        parts = line.split(':', 2)
        if len(parts) >= 2 and parts[0] == "EVT":
            component_name = parts[1]
            # payload = parts[2] if len(parts) > 2 else "" # Payload not used in this phase
            logger.info(f"Hardware event received from component: '{component_name}'")
            self.hardwareEventReceived.emit(component_name)
        # Future phases could handle "DATA:" prefixes here.

    @pyqtSlot(bool, str)
    def _on_worker_connection_status(self, connected: bool, message: str):
        self.is_connected = connected
        self.connectionStatusChanged.emit(connected, message)

    @pyqtSlot()
    def on_worker_finished(self):
        logger.info("HardwareLinkManager: Worker has finished. Cleaning up thread.")
        if self.thread:
            self.thread.quit()
            self.thread.wait(1000)
        self.thread = None
        self.worker = None
        # Ensure final status is disconnected
        if self.is_connected:
            self._on_worker_connection_status(False, "Disconnected.")