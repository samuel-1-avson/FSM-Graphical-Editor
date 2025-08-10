# fsm_designer_project/plugins/hdl_exporter.py

import os
import logging
from typing import Dict

from .api import BsmExporterPlugin
# Import the original generator functions
from ..utils.hdl_code_generator import (
    generate_vhdl_content, 
    generate_verilog_content, 
    sanitize_vhdl_identifier, 
    sanitize_verilog_identifier
)

logger = logging.getLogger(__name__)

class HDLExporter(BsmExporterPlugin):
    """A plugin to handle exports to Hardware Description Languages (VHDL/Verilog)."""

    @property
    def name(self) -> str:
        """Generic name for the plugin itself."""
        return "HDL Exporter (VHDL/Verilog)"

    @property
    def file_filter(self) -> str:
        """A comprehensive file filter for both languages."""
        return "VHDL Files (*.vhd *.vhdl);;Verilog Files (*.v *.sv)"

    def export(self, diagram_data: dict, **kwargs) -> Dict[str, str]:
        """
        Exports the FSM as VHDL or Verilog.

        This method expects 'export_type' ('vhdl' or 'verilog') and 
        'entity_name' (or 'module_name') in kwargs. It returns a 
        dictionary mapping the suggested filename to its content.

        Args:
            diagram_data: The FSM diagram data dictionary.
            **kwargs: Must contain 'export_type' (str) and 'entity_name' (str).

        Returns:
            A dictionary with a single entry: {filename: file_content}.
        """
        export_type = kwargs.get("export_type")
        entity_name = kwargs.get("entity_name") # Also used for module_name

        if not export_type or not entity_name:
            raise ValueError("HDLExporter requires 'export_type' and 'entity_name' in kwargs.")

        try:
            if export_type == "vhdl":
                hdl_code = generate_vhdl_content(diagram_data, entity_name)
                sanitized_filename = f"{sanitize_vhdl_identifier(entity_name)}.vhd"
                
            elif export_type == "verilog":
                hdl_code = generate_verilog_content(diagram_data, entity_name)
                sanitized_filename = f"{sanitize_verilog_identifier(entity_name)}.v"
                
            else:
                raise ValueError(f"Unknown HDL export type: '{export_type}'")

            return {sanitized_filename: hdl_code}

        except Exception as e:
            logger.error(f"Failed to generate {export_type.upper()} code for '{entity_name}': {e}", exc_info=True)
            raise