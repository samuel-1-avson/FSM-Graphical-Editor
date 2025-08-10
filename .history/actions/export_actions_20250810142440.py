# fsm_designer_project/actions/export_actions.py
import logging
import os
from PyQt6.QtCore import QObject, pyqtSlot, QDir
from PyQt6.QtWidgets import QMessageBox, QFileDialog, QInputDialog, QLineEdit
from ..utils.config import FILE_EXTENSION
from ..plugins.api import BsmExporterPlugin

logger = logging.getLogger(__name__)

class ExportActionHandler(QObject):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.mw = main_window

    @pyqtSlot()
    def on_export_simulink(self):
        editor = self.mw.current_editor()
        if not editor or not editor.file_path:
            QMessageBox.warning(self.mw, "Save Required", "Please save the diagram file before exporting to Simulink.")
            return

        if editor.py_sim_active:
            QMessageBox.warning(self.mw, "Simulation Active", "Please stop the Python simulation before exporting.")
            return

        output_dir = os.path.dirname(editor.file_path)
        base_name = os.path.splitext(os.path.basename(editor.file_path))[0]
        model_name = "".join(c if c.isalnum() or c=='_' else '_' for c in base_name)
        if not model_name or not model_name[0].isalpha():
            model_name = "FSM_Model_" + model_name

        diagram_data = editor.scene.get_diagram_data()
        if not diagram_data['states']:
            QMessageBox.information(self.mw, "Empty Diagram", "Cannot export an empty diagram.")
            return
        
        from ..core.fsm_parser import parse_diagram_to_ir
        fsm_model_ir = parse_diagram_to_ir(diagram_data)
        
        self.mw._start_matlab_operation(f"Exporting '{model_name}'")
        self.mw.matlab_connection.generate_simulink_model(
            fsm_model_ir,
            output_dir, 
            model_name
        )

    @pyqtSlot()
    def on_generate_c_code(self):
        # Implementation moved to file_actions.py as it creates new files
        self.mw.action_handler.file_handler.on_generate_c_code()

    @pyqtSlot()
    def on_export_arduino(self):
        # Implementation moved to file_actions.py as it creates new files
        self.mw.action_handler.file_handler.on_export_arduino()

    @pyqtSlot()
    def on_export_python_fsm(self):
        # Implementation moved to file_actions.py as it creates new files
        self.mw.action_handler.file_handler.on_export_python_fsm()

    @pyqtSlot()
    def on_export_plantuml(self):
        plantuml_plugin = next((p for p in self.mw.plugin_manager.exporter_plugins if "PlantUML" in p.name), None)
        if plantuml_plugin:
            self.mw.action_handler.file_handler.on_export_with_plugin(plantuml_plugin)
        else:
            QMessageBox.critical(self.mw, "Plugin Error", "PlantUML exporter plugin not found.")

    @pyqtSlot()
    def on_export_mermaid(self):
        mermaid_plugin = next((p for p in self.mw.plugin_manager.exporter_plugins if "Mermaid" in p.name), None)
        if mermaid_plugin:
            self.mw.action_handler.file_handler.on_export_with_plugin(mermaid_plugin)
        else:
            QMessageBox.critical(self.mw, "Plugin Error", "Mermaid exporter plugin not found.")

    @pyqtSlot()
    def on_export_vhdl(self):
        # Implementation moved to file_actions.py as it creates new files
        self.mw.action_handler.file_handler.on_export_vhdl()

    @pyqtSlot()
    def on_export_verilog(self):
        # Implementation moved to file_actions.py as it creates new files
        self.mw.action_handler.file_handler.on_export_verilog()

    @pyqtSlot()
    def on_generate_matlab_code(self):
        # Implementation moved to file_actions.py as it creates new files
        self.mw.action_handler.file_handler.on_generate_matlab_code()

    @pyqtSlot()
    def on_export_c_testbench(self):
        # Implementation moved to file_actions.py as it creates new files
        self.mw.action_handler.file_handler.on_export_c_testbench()