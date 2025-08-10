# fsm_designer_project/plugins/python_code_exporter.py

import os
import logging
from typing import Dict

from .api import BsmExporterPlugin
# We import the original generator function, which now acts as a library helper
from ..codegen.python_code_generator import generate_python_fsm_code, sanitize_python_identifier

logger = logging.getLogger(__name__)

class PythonFSMExporter(BsmExporterPlugin):
    """A plugin to handle the export of a diagram to a Python FSM class."""

    @property
    def name(self) -> str:
        """The user-friendly name of the exporter for menus."""
        return "Python FSM Class"

    @property
    def file_filter(self) -> str:
        """The file filter for the save dialog."""
        return "Python Files (*.py)"

    def export(self, diagram_data: dict, **kwargs) -> Dict[str, str]:
        """
        Exports the FSM as a Python class file.

        This method expects 'class_name_base' in kwargs.
        It returns a dictionary mapping the suggested filename to its content.

        Args:
            diagram_data: The FSM diagram data dictionary.
            **kwargs: Must contain 'class_name_base' (str).

        Returns:
            A dictionary with a single entry: {filename: file_content}.
        """
        class_name_base = kwargs.get("class_name_base")
        if not class_name_base:
            raise ValueError("PythonFSMExporter requires 'class_name_base' in kwargs.")

        try:
            # The core logic is called from the (now) library module
            python_code = generate_python_fsm_code(diagram_data, class_name_base)
            
            # The plugin returns a dictionary of {filename: content}
            sanitized_filename = f"{sanitize_python_identifier(class_name_base.lower())}.py"
            
            return {sanitized_filename: python_code}
            
        except Exception as e:
            logger.error(f"Failed to generate Python FSM code for class '{class_name_base}': {e}", exc_info=True)
            # Re-raise the exception so the action handler can display it to the user
            raise