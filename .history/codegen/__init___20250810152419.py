# fsm_designer_project/codegen/__init__.py
"""
Initializes the 'codegen' package.

This package contains all modules related to generating code or text-based
representations of the FSM from the internal diagram data.
"""

from .c_code_generator import generate_c_code_content, generate_c_testbench_content, sanitize_c_identifier
from .hdl_code_generator import generate_vhdl_content, generate_verilog_content, sanitize_vhdl_identifier, sanitize_verilog_identifier
from .python_code_generator import generate_python_fsm_code, sanitize_python_identifier
from .fsm_importer import parse_plantuml, parse_mermaid
from .plantuml_exporter import generate_plantuml_text
from .mermaid_exporter import generate_mermaid_text

__all__ = [
    "generate_c_code_content",
    "generate_c_testbench_content",
    "sanitize_c_identifier",
    "generate_vhdl_content",
    "generate_verilog_content",
    "sanitize_vhdl_identifier",
    "sanitize_verilog_identifier",
    "generate_python_fsm_code",
    "sanitize_python_identifier",
    "parse_plantuml",
    "parse_mermaid",
    "generate_plantuml_text",
    "generate_mermaid_text",
]