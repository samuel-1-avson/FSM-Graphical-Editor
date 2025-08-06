import logging
from collections import defaultdict
from PyQt6.QtCore import QObject, pyqtSlot

logger = logging.getLogger(__name__)

class SimulationDataLogger(QObject):
    """Captures and stores FSM simulation history for plotting and analysis."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logged_data = defaultdict(list)
        self.is_logging = False

    def start_logging(self):
        """Clears previous data and starts a new logging session."""
        self.logged_data.clear()
        self.is_logging = True
        logger.info("SimulationDataLogger: Started new logging session.")

    def stop_logging(self):
        """Stops the current logging session."""
        self.is_logging = False
        logger.info("SimulationDataLogger: Stopped logging session.")

    @pyqtSlot(int, dict)
    def on_tick_processed(self, tick: int, variables: dict):
        """Slot to receive and log data from the FSMSimulator."""
        if not self.is_logging:
            return

        for var_name, value in variables.items():
            # We can only plot numerical data
            if isinstance(value, (int, float, bool)):
                self.logged_data[var_name].append((tick, float(value)))

    def get_data_for_variable(self, var_name: str):
        """Returns the logged data for a specific variable."""
        return self.logged_data.get(var_name, [])