# fsm_designer_project/utils/c_code_generator.py
import re
from jinja2 import Environment, FileSystemLoader
import os
from typing import Dict, Any

def sanitize_c_identifier(name: str, prefix: str = "s_") -> str:
    """Sanitizes a string to be a valid C identifier."""
    if not name:
        return f"{prefix}Unnamed"
    
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    
    c_keywords = {"auto", "break", "case", "char", "const", "continue", "default", "do", "double", "else", "enum",
                  "extern", "float", "for", "goto", "if", "int", "long", "register", "return", "short", "signed",
                  "sizeof", "static", "struct", "switch", "typedef", "union", "unsigned", "void", "volatile", "while"}

    if not sanitized:
        return f"{prefix}SanitizedEmpty"
    if sanitized in c_keywords:
        return f"fsm_{sanitized}"
    if not sanitized[0].isalpha() and sanitized[0] != '_':
        return f"{prefix}{sanitized}"
        
    return sanitized

def generate_c_code_content(diagram_data: Dict, fsm_name: str, target_platform: str, options: Dict = None) -> Dict[str, str]:
    """Generates C code content based on a target platform and options."""
    if not diagram_data.get('states'):
        raise ValueError("Cannot generate code: No states defined in diagram.")

    options = options or {}
    fsm_name_c = sanitize_c_identifier(fsm_name, "fsm_")
    
    templates_dir = os.path.join(os.path.dirname(__file__), '..', 'assets', 'templates')
    env = Environment(loader=FileSystemLoader(templates_dir), trim_blocks=True, lstrip_blocks=True)

    template_map = {
        "Arduino (.ino Sketch)": ("fsm_arduino.ino.j2", "fsm_arduino.h.j2"),
        "Generic C (Header/Source Pair)": ("fsm.c.j2", "fsm.h.j2"),
        "State Table (Function Pointers)": ("fsm_table.c.j2", "fsm_table.h.j2"),
        "ESP-IDF (main.c Snippet)": ("fsm_espidf.c.j2", "fsm_espidf.h.j2"),
        "Pico SDK (main.c Snippet)": ("fsm_pico_sdk.c.j2", "fsm_pico_sdk.h.j2"),
        "STM32 HAL (Snippet)": ("fsm_stm32_hal.c.j2", "fsm_stm32_hal.h.j2")
    }
    
    c_template_name, h_template_name = template_map.get(target_platform, ("fsm.c.j2", "fsm.h.j2"))
    
    context = _prepare_template_context(diagram_data, fsm_name_c, options)

    h_template = env.get_template(h_template_name)
    c_template = env.get_template(c_template_name)

    h_content = h_template.render(context)
    c_content = c_template.render(context)
    
    c_ext = ".ino" if target_platform == "Arduino (.ino Sketch)" else ".c"
    
    return {'h': h_content, 'c': c_content, 'fsm_name_c': fsm_name_c, 'c_ext': c_ext}

def generate_c_testbench_content(diagram_data: Dict, fsm_name_c: str) -> str:
    """Generates a C testbench file."""
    templates_dir = os.path.join(os.path.dirname(__file__), '..', 'assets', 'templates')
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template("testbench.c.j2")
    context = _prepare_template_context(diagram_data, fsm_name_c, {})
    return template.render(context)

def _prepare_template_context(diagram_data: Dict, fsm_name_c: str, options: Dict) -> Dict:
    """Prepares the context dictionary for Jinja2 rendering."""
    # This is a simplified context preparation. A full implementation would be more complex.
    initial_state = next((s for s in diagram_data['states'] if s.get('is_initial')), diagram_data['states'][0])
    
    context = {
        "fsm_name_c": fsm_name_c,
        "h_guard": f"FSM_{fsm_name_c.upper()}_H",
        "states": diagram_data['states'],
        "events": sorted(list(set(t['event'] for t in diagram_data['transitions'] if t.get('event')))),
        "initial_state_c_enum": f"STATE_{sanitize_c_identifier(initial_state['name']).upper()}",
        "action_functions": [],
        "action_prototypes": [],
        "options": options,
    }
    return context