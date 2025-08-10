# fsm_designer_project/plugins/c_code_exporter.py
import json
from .api import BsmExporterPlugin
# --- MODIFIED: Import from the new codegen package ---
from ..codegen.c_code_generator import generate_c_code_content, generate_c_testbench_content

class CCodeExporter(BsmExporterPlugin):
    """A plugin to handle various C-based code exports."""
    
    @property
    def name(self) -> str:
        # This is a generic name for the plugin itself.
        # The menu items will be more specific.
        return "C/C++ Language Exporter"

    @property
    def file_filter(self) -> str:
        # A generic filter that can be used by the action handler.
        return "C Source Files (*.c);;Arduino Sketches (*.ino);;Header Files (*.h)"

    def export(self, diagram_data: dict, **kwargs) -> dict:
        """
        Exports C code. This method is now more versatile. It expects
        extra arguments via kwargs and returns a dictionary of
        {filename: content} for multi-file exports.
        """
        export_type = kwargs.get("export_type", "generic_c") # e.g., 'generic_c', 'arduino', 'testbench'
        base_filename = kwargs.get("base_filename", "fsm_generated")
        options = kwargs.get("generation_options", {})
        
        if export_type == "testbench":
            # Testbench generation returns a single file
            content = generate_c_testbench_content(diagram_data, base_filename)
            return {f"{base_filename}_test.c": content}
        
        # Determine the platform for the main code generator
        platform_map = {
            "arduino": "Arduino (.ino Sketch)",
            "stm32": "STM32 HAL (Snippet)",
            "generic_c": "Generic C (Header/Source Pair)"
        }
        target_platform = platform_map.get(export_type, "Generic C (Header/Source Pair)")

        # The core logic is still in the original function, which now acts as a library call
        content_dict = generate_c_code_content(
            diagram_data, base_filename, target_platform, options
        )
        
        # Adapt the output to a {filename: content} structure
        fsm_name_c = content_dict.get('fsm_name_c', base_filename) # Get the sanitized name
        c_ext = content_dict.get('c_ext', '.c')
        
        return {
            f"{fsm_name_c}.h": content_dict.get('h', ''),
            f"{fsm_name_c}{c_ext}": content_dict.get('c', '')
        }