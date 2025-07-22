# fsm_designer_project/io/hdl_code_generator.py
import os
import re
import logging
from jinja2 import Environment, FileSystemLoader, select_autoescape
from PyQt5.QtCore import QDateTime

logger = logging.getLogger(__name__)

def sanitize_vhdl_identifier(name_str: str, prefix_if_digit="s_") -> str:
    """Sanitizes a string to be a valid VHDL identifier."""
    if not name_str: return f"{prefix_if_digit}unnamed"
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name_str)
    VHDL_KEYWORDS = {"abs", "access", "after", "alias", "all", "and", "architecture", "array", "assert", "attribute", "begin", "block", "body", "buffer", "bus", "case", "component", "configuration", "constant", "disconnect", "downto", "else", "elsif", "end", "entity", "exit", "file", "for", "function", "generate", "generic", "group", "guarded", "if", "impure", "in", "inertial", "inout", "is", "label", "library", "linkage", "literal", "loop", "map", "mod", "nand", "new", "next", "nor", "not", "null", "of", "on", "open", "or", "others", "out", "package", "port", "postponed", "procedure", "process", "pure", "range", "record", "register", "reject", "rem", "report", "return", "rol", "ror", "select", "severity", "signal", "shared", "sla", "sll", "sra", "srl", "subtype", "then", "to", "transport", "type", "unaffected", "units", "until", "use", "variable", "wait", "when", "while", "with", "xnor", "xor"}
    if sanitized.lower() in VHDL_KEYWORDS: sanitized = f"{sanitized}_k"
    if not sanitized or sanitized[0].isdigit(): sanitized = prefix_if_digit + sanitized
    return sanitized

def sanitize_verilog_identifier(name_str: str, prefix_if_digit="s_") -> str:
    """Sanitizes a string to be a valid Verilog identifier."""
    if not name_str: return f"{prefix_if_digit}unnamed"
    sanitized = re.sub(r'[^a-zA-Z0-9_$]', '_', name_str) # Verilog allows $
    VERILOG_KEYWORDS = {"always", "if", "else", "case", "endcase", "module", "endmodule", "input", "output", "reg", "wire", "parameter", "localparam", "assign", "begin", "end"}
    if sanitized in VERILOG_KEYWORDS: sanitized = f"{sanitized}_"
    if not sanitized or sanitized[0].isdigit(): sanitized = prefix_if_digit + sanitized
    return sanitized

def _prepare_hdl_context(diagram_data: dict, entity_name: str, lang: str) -> dict:
    """Helper function to prepare the context dictionary for both VHDL and Verilog templates."""
    sanitizer = sanitize_verilog_identifier if lang == 'verilog' else sanitize_vhdl_identifier
    
    context = {
        "entity_name": sanitizer(entity_name, "fsm_"),
        "states": [],
        "initial_state_name": "s_error", # Fallback
        "timestamp": QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss"),
        "app_name": "BSM Designer"
    }

    states_data = diagram_data.get('states', [])
    transitions_data = diagram_data.get('transitions', [])
    state_map_by_name = {}
    initial_state_found = False

    # First pass: map all state names to their sanitized HDL names
    for state_data in states_data:
        original_name = state_data['name']
        hdl_name = sanitizer(f"s_{original_name}")
        state_map_by_name[original_name] = hdl_name

    # Second pass: build the context for each state
    for state_data in states_data:
        original_name = state_data['name']
        state_ctx = {
            "vhdl_name": state_map_by_name[original_name], # VHDL template uses this key
            "verilog_name": state_map_by_name[original_name], # Verilog template uses this key
            "original_name": original_name,
            "transitions": []
        }
        
        if state_data.get('is_initial') and not initial_state_found:
            context["initial_state_name"] = state_map_by_name[original_name]
            initial_state_found = True
        
        context['states'].append(state_ctx)

    if not initial_state_found and context['states']:
        context["initial_state_name"] = context['states'][0]['vhdl_name']

    # Third pass: build transition context for each state
    for trans_data in sorted(transitions_data, key=lambda t: t.get('priority', 0), reverse=True):
        src_name = trans_data.get('source')
        for state_ctx in context['states']:
            if state_ctx['original_name'] == src_name:
                event_name = trans_data.get('event')
                if not event_name:
                    logger.warning(f"Skipping HDL transition from '{src_name}' as it has no event name.")
                    continue

                trans_ctx = {
                    "event_signal": sanitizer(f"event_{event_name}"),
                    "condition": sanitizer(trans_data.get('condition', '')) if trans_data.get('condition') else None,
                    "target_state": state_map_by_name.get(trans_data['target'], 's_error')
                }
                state_ctx['transitions'].append(trans_ctx)
                break
    
    return context

def generate_vhdl_content(diagram_data: dict, entity_name: str) -> str:
    """Generates VHDL code as a string from diagram data."""
    if not diagram_data.get('states'): raise ValueError("No states defined.")
    # --- FIX: Correct the path to go up one level to find the 'templates' directory ---
    env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'templates')), autoescape=select_autoescape(), trim_blocks=True, lstrip_blocks=True)
    template = env.get_template("fsm.vhd.j2")
    context = _prepare_hdl_context(diagram_data, entity_name, 'vhdl')
    return template.render(context)

def generate_verilog_content(diagram_data: dict, module_name: str) -> str:
    """Generates Verilog code as a string from diagram data."""
    if not diagram_data.get('states'): raise ValueError("No states defined.")
    # --- FIX: Correct the path to go up one level to find the 'templates' directory ---
    env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'templates')), autoescape=select_autoescape(), trim_blocks=True, lstrip_blocks=True)
    template = env.get_template("fsm.v.j2")
    context = _prepare_hdl_context(diagram_data, module_name, 'verilog')
    num_states = len(context['states'])
    context['state_bits'] = max(1, (num_states - 1).bit_length()) if num_states > 0 else 1
    return template.render(context)