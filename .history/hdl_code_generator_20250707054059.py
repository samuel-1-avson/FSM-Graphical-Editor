# fsm_designer_project/hdl_code_generator.py
import os
import re
import logging
from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

def sanitize_vhdl_identifier(name_str: str, prefix_if_digit="s_") -> str:
    """
    Sanitizes a string to be a valid VHDL identifier.
    It replaces invalid characters and prefixes if it starts with a non-alphabetic character.
    VHDL identifiers must start with a letter and contain only letters, digits, and underscores.
    """
    if not name_str:
        return f"{prefix_if_digit}unnamed"
    
    # Replace spaces and common problematic characters with underscores
    sanitized = name_str.replace(' ', '_').replace('-', '_').replace('.', '_')
    
    # Remove any remaining characters not alphanumeric or underscore
    sanitized = "".join(c if c.isalnum() or c == '_' else '' for c in sanitized)

    # VHDL keywords (not exhaustive, but covers common ones)
    vhdl_keywords = {
        "abs", "access", "after", "alias", "all", "and", "architecture", "array", "assert",
        "attribute", "begin", "block", "body", "buffer", "bus", "case", "component",
        "configuration", "constant", "disconnect", "downto", "else", "elsif", "end",
        "entity", "exit", "file", "for", "function", "generate", "generic", "group",
        "guarded", "if", "impure", "in", "inertial", "inout", "is", "label", "library",
        "linkage", "literal", "loop", "map", "mod", "nand", "new", "next", "nor", "not",
        "null", "of", "on", "open", "or", "others", "out", "package", "port", "postponed",
        "procedure", "process", "pure", "range", "record", "register", "reject", "rem",
        "report", "return", "rol", "ror", "select", "severity", "signal", "shared",
        "sla", "sll", "sra", "srl", "subtype", "then", "to", "transport", "type",
        "unaffected", "units", "until", "use", "variable", "wait", "when", "while",

        "with", "xnor", "xor"
    }

    if sanitized.lower() in vhdl_keywords:
        sanitized = f"{sanitized}_k"

    if not sanitized:
        return f"{prefix_if_digit}sanitized_empty"
    
    if not sanitized[0].isalpha():
        sanitized = prefix_if_digit + sanitized
    
    return sanitized

def generate_vhdl_content(diagram_data: dict, entity_name: str) -> str:
    """
    Generates VHDL code as a string from diagram data.
    """
    if not diagram_data.get('states'):
        raise ValueError("Cannot generate VHDL code: No states defined in the diagram.")
    
    # 1. Setup Jinja2 Environment
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    if not os.path.isdir(template_dir):
        raise FileNotFoundError(f"Jinja2 template directory not found at: {template_dir}")
        
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=select_autoescape(), trim_blocks=True, lstrip_blocks=True)

    # 2. Prepare Data Context for Template
    vhdl_entity_name = sanitize_vhdl_identifier(entity_name, "fsm_")
    
    # Collect all unique events and generate input signals for them
    unique_events = sorted(list(set(t['event'] for t in diagram_data.get('transitions', []) if t.get('event'))))
    event_signals = [sanitize_vhdl_identifier(f"event_{e}") for e in unique_events]

    # Collect all unique actions and generate output signals for them
    # This is a simplification; a real design might map actions to specific hardware.
    # Here, we create a 1-bit signal for each unique action text.
    action_texts = set()
    for state in diagram_data.get('states', []):
        if state.get('entry_action'): action_texts.add(state['entry_action'])
        if state.get('exit_action'): action_texts.add(state['exit_action'])
    for trans in diagram_data.get('transitions', []):
        if trans.get('action'): action_texts.add(trans['action'])
    action_signals = [sanitize_vhdl_identifier(f"action_{a}") for a in sorted(list(action_texts))]
    
    # --- Context for Jinja2 ---
    context = {
        "entity_name": vhdl_entity_name,
        "event_signals": event_signals,
        "action_signals": action_signals,
        "states": [],
        "initial_state_name": "s_init_error", # Fallback
    }

    # Process states
    state_map_by_name = {}
    initial_state_found = False
    for state_data in diagram_data.get('states', []):
        state_name = state_data['name']
        vhdl_state_name = sanitize_vhdl_identifier(f"s_{state_name}")
        state_map_by_name[state_name] = vhdl_state_name
        
        entry_actions = [sanitize_vhdl_identifier(f"action_{a}") for a in state_data.get('entry_action', '').split(';') if a.strip()]
        exit_actions = [sanitize_vhdl_identifier(f"action_{a}") for a in state_data.get('exit_action', '').split(';') if a.strip()]

        state_ctx = {
            "vhdl_name": vhdl_state_name,
            "original_name": state_name,
            "entry_actions": entry_actions,
            "exit_actions": exit_actions,
            "transitions": []
        }
        
        if state_data.get('is_initial') and not initial_state_found:
            context["initial_state_name"] = vhdl_state_name
            initial_state_found = True
        
        context['states'].append(state_ctx)

    if not initial_state_found and context['states']:
        context["initial_state_name"] = context['states'][0]['vhdl_name']

    # Process transitions and associate them with their source state
    for trans_data in diagram_data.get('transitions', []):
        src_name = trans_data.get('source')
        for state_ctx in context['states']:
            if state_ctx['original_name'] == src_name:
                event_name = trans_data.get('event')
                if not event_name:
                    logger.warning(f"Skipping VHDL transition from '{src_name}' as it has no event name.")
                    continue

                trans_actions = [sanitize_vhdl_identifier(f"action_{a}") for a in trans_data.get('action', '').split(';') if a.strip()]
                
                trans_ctx = {
                    "event_signal": sanitize_vhdl_identifier(f"event_{event_name}"),
                    "condition": trans_data.get('condition', 'true'), # Default to 'true' if no condition
                    "target_state": state_map_by_name.get(trans_data['target'], 's_error'),
                    "actions": trans_actions
                }
                state_ctx['transitions'].append(trans_ctx)
                break

    # 3. Render template
    template = env.get_template("fsm.vhd.j2")
    vhdl_code = template.render(context)
    
    return vhdl_code