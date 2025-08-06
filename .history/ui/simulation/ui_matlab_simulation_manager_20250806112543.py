# fsm_designer_project/ui/simulation/ui_matlab_simulation_manager.py

import os
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import pyqtSlot, QObject, Qt

# Import the necessary data classes and enums for type hinting
from ...managers.matlab_simulation_manager import MatlabSimulationManager, SimulationState, SimulationData

logger = logging.getLogger(__name__)

class MatlabSimulationUIManager(QObject):
    """
    Manages the UI dock for displaying MATLAB/Simulink simulation results.
    This includes plots and data tables streamed from the simulation.
    """
    def __init__(self, main_window):
        super().__init__(main_window)
        self.mw = main_window
        self.plot_label: QLabel | None = None
        self.data_table: QTableWidget | None = None
        self.tabs: QTabWidget | None = None
        self.plot_widget: QWidget | None = None

    def create_dock_widget_contents(self) -> QWidget:
        """Creates the main widget and its contents to be placed in the dock."""
        container_widget = QWidget()
        layout = QVBoxLayout(container_widget)
        layout.setContentsMargins(4, 4, 4, 4)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # --- Plot Tab ---
        self.plot_widget = QWidget()
        plot_layout = QVBoxLayout(self.plot_widget)
        self.plot_label = QLabel("Run a Simulink simulation to see the output plot here.")
        self.plot_label.setScaledContents(True)
        self.plot_label.setAlignment(Qt.AlignCenter)
        plot_layout.addWidget(self.plot_label)
        self.tabs.addTab(self.plot_widget, "📊 Plot")

        # --- Data Tab ---
        data_widget = QWidget()
        data_layout = QVBoxLayout(data_widget)
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(2)
        self.data_table.setHorizontalHeaderLabels(["Variable", "Final Value"])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.data_table.setEditTriggers(QTableWidget.NoEditTriggers)
        data_layout.addWidget(self.data_table)
        self.tabs.addTab(data_widget, "🔢 Data")

        self._connect_signals()
        
        return container_widget

    def _connect_signals(self):
        """Connects to the signals from the core MatlabSimulationManager."""
        if self.mw.matlab_sim_manager:
            self.mw.matlab_sim_manager.simulation_plot_ready.connect(self.on_plot_ready)
            self.mw.matlab_sim_manager.simulation_data_updated.connect(self.on_data_updated)
            self.mw.matlab_sim_manager.simulation_state_changed.connect(self.on_sim_state_changed)
            self.mw.matlab_sim_manager.simulation_completed.connect(self.on_simulation_completed)
            
        else:
            logger.error("MatlabSimulationUIManager could not find matlab_sim_manager on MainWindow to connect signals.")

    @pyqtSlot(str)
    def on_plot_ready(self, image_path: str):
        """Displays the generated plot image when the simulation is complete."""
        if self.plot_label and os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            self.plot_label.setPixmap(pixmap)
            if self.tabs and self.plot_widget:
                self.tabs.setCurrentWidget(self.plot_widget)
        elif self.plot_label:
            self.plot_label.setText("Plot generated, but file not found at:\n" + image_path)
            logger.warning(f"Plot image file not found at path: {image_path}")

    @pyqtSlot(SimulationData)
    def on_data_updated(self, data: SimulationData):
        """
        Updates the data table with live values from the simulation.
        (Note: This might be too slow for very fast simulations, but is good for moderate speeds)
        """
        if not self.data_table:
            return
            
        self.data_table.setRowCount(len(data.variables))
        for i, (key, value) in enumerate(data.variables.items()):
            self.data_table.setItem(i, 0, QTableWidgetItem(str(key)))
            # Display a summary for large data arrays
            if isinstance(value, list) and len(value) > 10:
                val_str = f"Array (size: {len(value)})"
            else:
                val_str = str(value)
            self.data_table.setItem(i, 1, QTableWidgetItem(val_str))

    @pyqtSlot(SimulationState, str)
    def on_sim_state_changed(self, state: SimulationState, message: str):
        """Clears the UI when a new simulation starts."""
        if state == SimulationState.LOADING or state == SimulationState.RUNNING:
            if self.plot_label:
                self.plot_label.setText("Simulation in progress...")
            if self.data_table:
                self.data_table.setRowCount(0)
    
    @pyqtSlot(bool, str, dict)
    def on_simulation_completed(self, success: bool, message: str, final_data: dict):
        """Updates the table with final workspace data upon completion."""
        if success and self.data_table:
            workspace_vars = final_data.get('workspace_variables', {})
            self.data_table.clearContents()
            self.data_table.setRowCount(len(workspace_vars))
            self.data_table.setHorizontalHeaderLabels(["Variable", "Final Value / Size"])

            for i, (key, value) in enumerate(workspace_vars.items()):
                self.data_table.setItem(i, 0, QTableWidgetItem(str(key)))
                # Display a summary for large data arrays
                if isinstance(value, list) and len(value) > 10:
                    val_str = f"Array (size: {len(value)})"
                else:
                    val_str = str(value)
                self.data_table.setItem(i, 1, QTableWidgetItem(val_str))
            
            if self.tabs:
                self.tabs.setCurrentWidget(self.data_table.parentWidget())