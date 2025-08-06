# fsm_designer_project/ui/dialogs/new_project_dialog.py
import os
import re
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                             QPushButton, QDialogButtonBox, QHBoxLayout, QFileDialog)
from PyQt6.QtCore import QDir

class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New BSM Project")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.project_name_edit = QLineEdit("MyFSMProject")
        self.project_name_edit.textChanged.connect(self._update_main_diagram_name)
        form_layout.addRow("Project Name:", self.project_name_edit)

        self.location_edit = QLineEdit(QDir.homePath())
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_location)
        location_layout = QHBoxLayout()
        location_layout.addWidget(self.location_edit)
        location_layout.addWidget(browse_button)
        form_layout.addRow("Location:", location_layout)
        
        self.main_diagram_edit = QLineEdit("main_fsm.bsm")
        form_layout.addRow("Main Diagram File:", self.main_diagram_edit)

        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self._update_main_diagram_name(self.project_name_edit.text())

    def _update_main_diagram_name(self, text):
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', text).strip('_')
        if not safe_name:
            safe_name = "main"
        self.main_diagram_edit.setText(f"{safe_name.lower()}.bsm")

    def _browse_location(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Project Location", self.location_edit.text())
        if directory:
            self.location_edit.setText(directory)

    def get_project_details(self):
        return (
            self.project_name_edit.text().strip(),
            self.location_edit.text().strip(),
            self.main_diagram_edit.text().strip()
        )