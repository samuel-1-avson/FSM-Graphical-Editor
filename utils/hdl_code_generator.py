# fsm_designer_project/utils/hdl_code_generator.py
import re
from jinja2 import Environment, FileSystemLoader
import os
from datetime import datetime
from typing import Dict

def sanitize_vhdl_identifier(name: str) -> str:
    """Sanitizes a string to be a valid VHDL identifier."""
    if not name: return "unnamed_fsm"
    s = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    if not s or not s[0].isalpha():
        s = "fsm_" + s
    return s.lower()

def sanitize_verilog_identifier(name: str) -> str:
    """Sanitizes a string to be a valid Verilog identifier."""
    if not name: return "unnamed_fsm"
    s = re.sub(r'[^a-zA-Z0-9_$]', '_', name)
    if not s or not s[0].isalpha():
        s = "fsm_" + s
    return s

def generate_vhdl_content(diagram_data: Dict, entity_name: str) -> str:
    """Generates VHDL code from diagram data."""
    templates_dir = os.path.join(os.path.dirname(__file__), '..', 'assets', 'templates')
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template("fsm.vhd.j2")
    
    context = _prepare_hdl_context(diagram_data, entity_name, "vhdl")
    return template.render(context)

def generate_verilog_content(diagram_data: Dict, entity_name: str) -> str:
    """Generates Verilog code from diagram data."""
    templates_dir = os.path.join(os.path.dirname(__file__), '..', 'assets', 'templates')
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template("fsm.v.j2")

    context = _prepare_hdl_context(diagram_data, entity_name, "verilog")
    return template.render(context)

def _prepare_hdl_context(diagram_data: Dict, entity_name: str, lang: str) -> Dict:
    """Prepares the context for HDL templates."""
    initial_state = next((s for s in diagram_data['states'] if s.get('is_initial')), diagram_data['states'][0])
    sanitizer = sanitize_vhdl_identifier if lang == "vhdl" else sanitize_verilog_identifier
    
    # Process states for HDL naming conventions and link their transitions
    for state in diagram_data['states']:
        state['hdl_name'] = sanitizer(state['name'])
        state['original_name'] = state['name'] # Keep original name for comments
        state['transitions'] = [t for t in diagram_data['transitions'] if t['source'] == state['name']]

    # Gather all unique events and conditions to generate input ports
    input_signals = set()
    for trans in diagram_data['transitions']:
        # Sanitize the event name for use as a signal
        trans['event_signal'] = sanitizer(trans.get('event', 'transition_event'))
        input_signals.add(trans['event_signal'])
        
        # Sanitize identifiers found within the condition string
        if trans.get('condition'):
            variables = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', trans['condition'])
            for var in variables:
                # Avoid adding common language keywords or constants
                if var.lower() not in ['true', 'false', 'high', 'low', 'and', 'or', 'not', 'std_logic_vector', 'unsigned', 'signed', 'others', 'to_unsigned', 'reg', 'wire']:
                    input_signals.add(sanitizer(var))
        
        # Sanitize the target state name for use in the template
        target_state = next((s for s in diagram_data['states'] if s['name'] == trans['target']), None)
        if target_state:
            trans['target_state'] = sanitizer(target_state['name'])

    return {
        "entity_name": sanitizer(entity_name),
        "app_name": "BSM Designer",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "states": diagram_data['states'],
        "initial_state_name": sanitizer(initial_state['name']),
        "state_bits": max(1, (len(diagram_data['states']) - 1).bit_length()),
        "input_signals": sorted(list(input_signals)),
        "all_events_and_conditions": ", ".join(sorted(list(input_signals)))
    }