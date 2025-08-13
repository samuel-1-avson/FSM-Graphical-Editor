# fsm_designer_project/ui/simulation/data_dictionary_widget.py

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, 
    QToolBar, QInputDialog, QMessageBox, QStyle
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import pyqtSlot, Qt
from ...managers.data_dictionary_manager import DataDictionaryManager
from ...utils import get_standard_icon

logger = logging.getLogger(__name__)

class DataDictionaryWidget(QWidget):
    """
    A widget for viewing and editing the project's data dictionary.
    Provides a table-based interface for defining variables, their types,
    and initial values.
    """
    def __init__(self, dictionary_manager: DataDictionaryManager, parent=None):
        super().__init__(parent)
        self.manager = dictionary_manager
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar for actions
        toolbar = QToolBar("Data Dictionary Tools")
        add_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_DialogApplyButton, "Add"), "Add Variable", self)
        remove_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_TrashIcon, "Remove"), "Remove Selected", self)
        toolbar.addAction(add_action)
        toolbar.addAction(remove_action)
        add_action.triggered.connect(self.on_add_variable)
        remove_action.triggered.connect(self.on_remove_variable)
        layout.addWidget(toolbar)

        # Table to display variables
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Name", "Initial Value", "Type"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.itemChanged.connect(self.on_item_changed)
        layout.addWidget(self.table)
        
        # --- FIX: REMOVE THIS LINE ---
        
        # --- END FIX ---
        self.populate_table()

    @pyqtSlot()
    def populate_table(self):
        """Reloads the table with data from the manager."""
        self.table.blockSignals(True)
        try:
            self.table.setRowCount(0) # Clear table before populating
            self.table.setRowCount(len(self.manager.variables))
            
            sorted_vars = sorted(self.manager.variables.items())

            for row, (name, props) in enumerate(sorted_vars):
                name_item = QTableWidgetItem(name)
                # Make the name column non-editable after creation
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 0, name_item)
                
                initial_value = props.get("initial_value", "")
                self.table.setItem(row, 1, QTableWidgetItem(str(initial_value)))
                
                # For type, we can use a combo box in the future for better UX
                type_str = props.get("type", "any")
                self.table.setItem(row, 2, QTableWidgetItem(type_str))
        finally:
            self.table.blockSignals(False)

    @pyqtSlot()
    def on_add_variable(self):
        """Opens a dialog to add a new variable to the dictionary."""
        var_name, ok = QInputDialog.getText(self, "Add New Variable", "Enter variable name:")
        if ok and var_name:
            var_name = var_name.strip()
            if var_name in self.manager.variables:
                QMessageBox.warning(self, "Variable Exists", f"A variable named '{var_name}' already exists.")
                return
            
            # Add to manager and save
            self.manager.variables[var_name] = {"initial_value": 0, "type": "int"}
            self.manager.save()
            # The populate_table slot will be called automatically via the signal
        elif ok:
            QMessageBox.warning(self, "Invalid Name", "Variable name cannot be empty.")
            
    @pyqtSlot()
    def on_remove_variable(self):
        """Removes the selected variable(s) from the dictionary."""
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select a variable to remove.")
            return

        rows_to_remove = sorted(list(set(item.row() for item in selected_items)), reverse=True)
        
        reply = QMessageBox.question(self, "Remove Variables", 
                                     f"Are you sure you want to remove {len(rows_to_remove)} variable(s)?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            for row in rows_to_remove:
                var_name = self.table.item(row, 0).text()
                if var_name in self.manager.variables:
                    del self.manager.variables[var_name]
            self.manager.save()
            # The populate_table slot will be called automatically via the signal

    @pyqtSlot(QTableWidgetItem)
    def on_item_changed(self, item: QTableWidgetItem):
        """Updates the manager when a table cell is edited."""
        row = item.row()
        col = item.column()
        
        name_item = self.table.item(row, 0)
        if not name_item:
            return # Should not happen if an item changed

        var_name = name_item.text()
        if var_name not in self.manager.variables:
            logger.warning(f"Data dictionary UI is out of sync. '{var_name}' not found in manager.")
            return

        # Update initial value
        if col == 1:
            self.manager.variables[var_name]["initial_value"] = item.text()
        # Update type
        elif col == 2:
            self.manager.variables[var_name]["type"] = item.text()
        
        # Save the changes
        self.manager.save()