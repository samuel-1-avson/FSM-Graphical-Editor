import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QHBoxLayout, QPushButton, QListWidgetItem
from PyQt6.QtCore import pyqtSlot, Qt
from ...core.simulation_logger import SimulationDataLogger

class SimulationPlotWidget(QWidget):
    def __init__(self, data_logger: SimulationDataLogger, parent=None):
        super().__init__(parent)
        self.data_logger = data_logger
        self.plotted_variables = {}  # var_name -> plot_data_item

        self.setWindowTitle("Simulation Scope")
        main_layout = QHBoxLayout(self)

        # Plotting Area
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('bottom', 'Simulation Ticks')
        self.plot_widget.setLabel('left', 'Value')
        self.plot_widget.showGrid(x=True, y=True)
        main_layout.addWidget(self.plot_widget, 4)

        # Variable Selection Area
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        self.variable_list = QListWidget()
        self.variable_list.itemClicked.connect(self.on_variable_toggled)
        
        clear_button = QPushButton("Clear Plot")
        clear_button.clicked.connect(self.clear_all_plots)

        control_layout.addWidget(self.variable_list)
        control_layout.addWidget(clear_button)
        main_layout.addWidget(control_panel, 1)

    def update_variable_list(self, variables: dict):
        """Populates the list of plottable variables."""
        self.variable_list.clear()
        for var_name, value in variables.items():
            if isinstance(value, (int, float, bool)):
                item = QListWidgetItem(var_name, self.variable_list)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked if var_name in self.plotted_variables else Qt.Unchecked)

    @pyqtSlot(QListWidgetItem)
    def on_variable_toggled(self, item: QListWidgetItem):
        var_name = item.text()
        if item.checkState() == Qt.Checked:
            self.add_plot(var_name)
        else:
            self.remove_plot(var_name)

    def add_plot(self, var_name: str):
        if var_name in self.plotted_variables:
            return
        pen = pg.mkPen(color=(len(self.plotted_variables) % 9), width=2)
        plot_item = self.plot_widget.plot(name=var_name, pen=pen)
        self.plotted_variables[var_name] = plot_item
        self.update_plot_data()

    def remove_plot(self, var_name: str):
        if var_name in self.plotted_variables:
            plot_item = self.plotted_variables.pop(var_name)
            self.plot_widget.removeItem(plot_item)

    def clear_all_plots(self):
        for var_name in list(self.plotted_variables.keys()):
            self.remove_plot(var_name)
        # Uncheck all items in the list
        for i in range(self.variable_list.count()):
            self.variable_list.item(i).setCheckState(Qt.Unchecked)

    def update_plot_data(self):
        """Refreshes all plots with the latest data from the logger."""
        for var_name, plot_item in self.plotted_variables.items():
            data = self.data_logger.get_data_for_variable(var_name)
            if data:
                ticks, values = zip(*data)
                plot_item.setData(ticks, values)