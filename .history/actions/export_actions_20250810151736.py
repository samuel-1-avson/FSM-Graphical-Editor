# fsm_designer_project/actions/export_actions.py
import logging
import os
from PyQt6.QtCore import QObject, pyqtSlot, QDir
from PyQt6.QtWidgets import QMessageBox, QFileDialog, QInputDialog, QLineEdit, QDialog, QVBoxLayout, QFormLayout, QComboBox, QGroupBox, QCheckBox, QDialogButtonBox
from ..utils.config import FILE_EXTENSION
from ..plugins.api import BsmExporterPlugin
from ..codegen.c_code_generator import generate_c_code_content, sanitize_c_identifier
from ..codegen.hdl_code_generator import generate_vhdl_content, generate_verilog_content, sanitize_vhdl_identifier, sanitize_verilog_identifier
from ..codegen.python_code_generator import generate_python_fsm_code, sanitize_python_identifier
from ..codegen.plantuml_exporter import generate_plantuml_text
from ..codegen.mermaid_exporter import generate_mermaid_text
from ..codegen.c_code_generator import generate_c_testbench_content
from ..services.matlab_integration import CodeGenConfig

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
        editor = self.mw.current_editor()
        if not editor or not editor.scene.items():
            QMessageBox.information(self.mw, "Empty Diagram", "Cannot generate code for an empty diagram.")
            return
            
        default_filename_base = "fsm_generated"
        if editor.file_path:
            default_filename_base = os.path.splitext(os.path.basename(editor.file_path))[0]
        
        output_dir = QFileDialog.getExistingDirectory(self.mw, "Select Output Directory for C/C++ Code", os.path.dirname(editor.file_path or QDir.homePath()))
        
        if output_dir:
            dialog = QDialog(self.mw)
            dialog.setWindowTitle("Generate C/C++ Code")
            layout = QFormLayout(dialog)
            filename_base_edit = QLineEdit(default_filename_base)
            layout.addRow("Base Filename:", filename_base_edit)
            impl_style_combo = QComboBox()
            impl_style_combo.addItems(["Switch-Case Statement", "State Table (Function Pointers)"])
            layout.addRow("Implementation Style:", impl_style_combo)
            options_group = QGroupBox("Options")
            options_layout = QVBoxLayout()
            include_comments_cb = QCheckBox("Include comments and original code")
            include_comments_cb.setChecked(True)
            options_layout.addWidget(include_comments_cb)
            options_group.setLayout(options_layout)
            layout.addRow(options_group)
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addRow(button_box)

            if dialog.exec():
                filename_base = filename_base_edit.text().strip()
                if not filename_base:
                    QMessageBox.warning(self.mw, "Invalid Filename", "Base filename cannot be empty.")
                    return
                
                generation_options = {
                    "implementation_style": impl_style_combo.currentText(),
                    "data_type": "int",
                    "include_comments": include_comments_cb.isChecked()
                }
                    
                diagram_data = editor.scene.get_diagram_data()
                try:
                    exported_files = generate_c_code_content(
                        diagram_data,
                        base_filename=filename_base, 
                        target_platform=generation_options['implementation_style'],
                        options=generation_options
                    )
                    
                    saved_paths = []
                    for fname, content in exported_files.items():
                        path = os.path.join(output_dir, fname)
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        saved_paths.append(path)

                    QMessageBox.information(self.mw, "C Code Generation Successful", f"Generated files:\n" + "\n".join(saved_paths))
                except Exception as e:
                    QMessageBox.critical(self.mw, "C Code Generation Error", f"Failed to generate C code: {e}")

    @pyqtSlot()
    def on_export_arduino(self):
        editor = self.mw.current_editor()
        if not editor or not editor.scene.items():
            QMessageBox.information(self.mw, "Empty Diagram", "Cannot generate an Arduino sketch for an empty diagram.")
            return

        default_filename_base = "fsm_generated"
        if editor.file_path:
            default_filename_base = os.path.splitext(os.path.basename(editor.file_path))[0]
        
        start_dir = os.path.dirname(editor.file_path) if editor.file_path else QDir.homePath()
        output_dir = QFileDialog.getExistingDirectory(self.mw, "Select Output Directory for Arduino Sketch", start_dir)
        
        if output_dir:
            sketch_name, ok = QInputDialog.getText(self.mw, "Arduino Sketch Name",
                                                   "Enter a name for the Arduino sketch (this will be the folder and .ino file name):",
                                                   QLineEdit.Normal, default_filename_base)
            if not (ok and sketch_name.strip()):
                return
            
            sketch_name = sketch_name.strip()
            if not sketch_name[0].isalpha() or not all(c.isalnum() or c == '_' for c in sketch_name):
                QMessageBox.warning(self.mw, "Invalid Sketch Name", "Arduino sketch name must start with a letter and contain only alphanumeric characters or underscores.")
                return
            
            sketch_dir_path = os.path.join(output_dir, sketch_name)
            try:
                os.makedirs(sketch_dir_path, exist_ok=True)
            except OSError as e:
                QMessageBox.critical(self.mw, "Directory Creation Error", f"Could not create sketch directory:\n{e}")
                return

            diagram_data = editor.scene.get_diagram_data()
            try:
                code_dict = generate_c_code_content(
                    diagram_data, sketch_name, 
                    target_platform="Arduino (.ino Sketch)"
                )
                with open(os.path.join(sketch_dir_path, f"{sketch_name}.h"), 'w', encoding='utf-8') as f:
                    f.write(code_dict['h'])
                with open(os.path.join(sketch_dir_path, f"{sketch_name}.ino"), 'w', encoding='utf-8') as f:
                    f.write(code_dict['c'])
                QMessageBox.information(self.mw, "Arduino Sketch Generated", f"Arduino sketch '{sketch_name}' created successfully in:\n{sketch_dir_path}")
            except Exception as e:
                QMessageBox.critical(self.mw, "Arduino Code Generation Error", f"Failed to generate Arduino code: {e}")
                logger.error(f"Error generating Arduino sketch: {e}", exc_info=True)

    @pyqtSlot()
    def on_export_python_fsm(self):
        editor = self.mw.current_editor()
        if not editor or not editor.scene.items():
            QMessageBox.information(self.mw, "Empty Diagram", "Cannot generate Python FSM for an empty diagram.")
            return
        
        default_classname_base = "MyFSM"
        if editor.file_path:
            base_name = os.path.splitext(os.path.basename(editor.file_path))[0]
            default_classname_base = "".join(word.capitalize() for word in base_name.replace('-', '_').split('_'))
        if not default_classname_base or not default_classname_base[0].isalpha():
            default_classname_base = "GeneratedFSM"

        class_name, ok = QInputDialog.getText(self.mw, "FSM Class Name",
                                              "Enter a name for the Python FSM class:",
                                              QLineEdit.Normal, default_classname_base)
        if not (ok and class_name.strip()):
            return

        class_name = class_name.strip()
        if not class_name[0].isalpha() or not class_name.replace('_', '').isalnum():
            QMessageBox.warning(self.mw, "Invalid Class Name", "Class name must start with a letter and contain only alphanumeric characters or underscores.")
            return

        sanitized_filename = f"{sanitize_python_identifier(class_name.lower())}.py"
        start_dir = os.path.dirname(editor.file_path) if editor.file_path else QDir.homePath()
        
        file_path, _ = QFileDialog.getSaveFileName(self.mw, "Save Python FSM File",
                                                   os.path.join(start_dir, sanitized_filename),
                                                   "Python Files (*.py)")
        if not file_path:
            return

        diagram_data = editor.scene.get_diagram_data()
        try:
            python_code = generate_python_fsm_code(diagram_data, class_name)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(python_code)
            QMessageBox.information(self.mw, "Python FSM Generation Successful", f"Generated file:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self.mw, "Python FSM Generation Error", f"Failed to generate Python FSM: {e}")
            logger.error(f"Error generating Python FSM: {e}", exc_info=True)

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
        editor = self.mw.current_editor()
        if not editor or not editor.scene.items():
            QMessageBox.information(self.mw, "Empty Diagram", "Cannot generate VHDL for an empty diagram.")
            return

        default_entity_name = "fsm_generated"
        if editor.file_path:
            base_name = os.path.splitext(os.path.basename(editor.file_path))[0]
            default_entity_name = sanitize_vhdl_identifier(base_name)
        
        entity_name, ok = QInputDialog.getText(self.mw, "VHDL Entity Name", "Enter a name for the VHDL entity:", QLineEdit.Normal, default_entity_name)
        if not (ok and entity_name.strip()): return
        entity_name = entity_name.strip()
        
        default_filename = f"{sanitize_vhdl_identifier(entity_name)}.vhd"
        start_dir = os.path.dirname(editor.file_path) if editor.file_path else QDir.homePath()
        
        file_path, _ = QFileDialog.getSaveFileName(self.mw, "Save VHDL File", os.path.join(start_dir, default_filename), "VHDL Files (*.vhd *.vhdl);;All Files (*)")
        if not file_path: return

        diagram_data = editor.scene.get_diagram_data()
        try:
            vhdl_code = generate_vhdl_content(diagram_data, entity_name)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(vhdl_code)
            QMessageBox.information(self.mw, "VHDL Export Successful", f"VHDL code exported to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self.mw, "VHDL Export Error", f"Failed to generate VHDL code: {e}")

    @pyqtSlot()
    def on_export_verilog(self):
        editor = self.mw.current_editor()
        if not editor or not editor.scene.items():
            QMessageBox.information(self.mw, "Empty Diagram", "Cannot generate Verilog for an empty diagram.")
            return

        default_module_name = "fsm_generated"
        if editor.file_path:
            base_name = os.path.splitext(os.path.basename(editor.file_path))[0]
            default_module_name = sanitize_verilog_identifier(base_name)
        
        module_name, ok = QInputDialog.getText(self.mw, "Verilog Module Name", "Enter a name for the Verilog module:", QLineEdit.Normal, default_module_name)
        if not (ok and module_name.strip()): return
        module_name = module_name.strip()
        
        default_filename = f"{sanitize_verilog_identifier(module_name)}.v"
        start_dir = os.path.dirname(editor.file_path) if editor.file_path else QDir.homePath()
        
        file_path, _ = QFileDialog.getSaveFileName(self.mw, "Save Verilog File", os.path.join(start_dir, default_filename), "Verilog Files (*.v *.sv);;All Files (*)")
        if not file_path: return

        diagram_data = editor.scene.get_diagram_data()
        try:
            verilog_code = generate_verilog_content(diagram_data, module_name)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(verilog_code)
            QMessageBox.information(self.mw, "Verilog Export Successful", f"Verilog code exported to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self.mw, "Verilog Export Error", f"Failed to generate Verilog code: {e}")

    @pyqtSlot()
    def on_generate_matlab_code(self):
        editor = self.mw.current_editor()
        if not editor or not editor.file_path:
            QMessageBox.warning(self.mw, "Save Required", "Please save the diagram file first.")
            return

        if editor.py_sim_active:
            QMessageBox.warning(self.mw, "Simulation Active", "Please stop any active simulation before code generation.")
            return

        if not self.mw.last_generated_model_path:
            QMessageBox.warning(self.mw, "Model Not Generated", "Please generate a Simulink model first (Code Export > Simulink Model...).")
            return

        model_path = self.mw.last_generated_model_path
        output_dir = os.path.dirname(model_path)
        
        self.mw._start_matlab_operation("Generating C++ Code")
        from ..services.matlab_integration import CodeGenConfig
        self.mw.matlab_connection.generate_code(model_path, config=CodeGenConfig(), output_dir=output_dir)

    @pyqtSlot()
    def on_export_c_testbench(self):
        editor = self.mw.current_editor()
        if not editor or not editor.scene.items():
            QMessageBox.information(self.mw, "Empty Diagram", "Cannot generate a testbench for an empty diagram.")
            return

        default_filename_base = "fsm_generated"
        if editor.file_path:
            default_filename_base = os.path.splitext(os.path.basename(editor.file_path))[0]
        
        fsm_name_c = sanitize_c_identifier(default_filename_base, "fsm_")
        default_test_filename = f"{fsm_name_c}_test.c"
        start_dir = os.path.dirname(editor.file_path) if editor.file_path else QDir.homePath()

        file_path, _ = QFileDialog.getSaveFileName(self.mw, "Save C Testbench File", os.path.join(start_dir, default_test_filename), "C Source Files (*.c);;All Files (*)")
        if not file_path:
            return

        diagram_data = editor.scene.get_diagram_data()
        try:
            testbench_code = generate_c_testbench_content(diagram_data, fsm_name_c)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(testbench_code)
            QMessageBox.information(self.mw, "Testbench Generation Successful", f"C testbench file generated successfully:\n{file_path}\n\nRemember to also export the main FSM C files to compile against it.")
        except Exception as e:
            QMessageBox.critical(self.mw, "Testbench Generation Error", f"Failed to generate testbench: {e}")