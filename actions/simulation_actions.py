# fsm_designer_project/actions/simulation_actions.py
import logging
from PyQt6.QtCore import QObject, pyqtSlot
from PyQt6.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)

class SimulationActionHandler(QObject):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.mw = main_window

    @pyqtSlot()
    def on_start_python_simulation(self):
        # This is now handled by the PySimulationUIManager
        self.mw.py_sim_ui_manager.on_start_py_simulation()

    @pyqtSlot()
    def on_stop_python_simulation(self):
        # This is now handled by the PySimulationUIManager
        self.mw.py_sim_ui_manager.on_stop_py_simulation()

    @pyqtSlot()
    def on_reset_python_simulation(self):
        # This is now handled by the PySimulationUIManager
        self.mw.py_sim_ui_manager.on_reset_py_simulation()
    
    @pyqtSlot()
    def on_run_matlab_simulation(self):
        if not self.mw.last_generated_model_path:
            QMessageBox.warning(self.mw, "Simulink Model Required", "Please export the diagram to a Simulink model first (Code Export > Simulink Model...).")
            return

        self.mw._start_matlab_operation("Running Simulation")
        self.mw.matlab_connection.run_simulation(self.mw.last_generated_model_path)