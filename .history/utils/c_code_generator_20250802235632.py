# fsm_designer_project/utils/c_code_generator.py
import re
from jinja2 import Environment, FileSystemLoader
import os
from typing import Dict, Any
from datetime import datetime
from ..assets.assets import MECHATRONICS_SNIPPETS

# Create a reverse map for easy lookup of user's intent from the code they entered
REVERSE_SNIPPET_MAP = {}
for lang, categories in MECHATRONICS_SNIPPETS.items():
    if lang == "Error": continue
    for category, snippets in categories.items():
        for name, code in snippets.items():
            REVERSE_SNIPPET_MAP[code.strip()] = {
                'lang': lang,
                'category': category,
                'name': name
            }

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
    env.globals['now'] = datetime.now

    template_map = {
        "Arduino (.ino Sketch)": ("fsm_arduino.ino.j2", "fsm_arduino.h.j2"),
        "Generic C (Header/Source Pair)": ("fsm.c.j2", "fsm.h.j2"),
        "State Table (Function Pointers)": ("fsm_table.c.j2", "fsm_table.h.j2"),
        "ESP-IDF (main.c Snippet)": ("fsm_espidf.c.j2", "fsm_espidf.h.j2"),
        "Pico SDK (main.c Snippet)": ("fsm_pico_sdk.c.j2", "fsm_pico_sdk.h.j2"),
        "STM32 HAL (Snippet)": ("fsm_stm32_hal.c.j2", "fsm_stm32_hal.h.j2")
    }
    
    c_template_name, h_template_name = template_map.get(target_platform, ("fsm.c.j2", "fsm.h.j2"))
    
    context = _prepare_template_context(diagram_data, fsm_name_c, target_platform, options)

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
    context = _prepare_template_context(diagram_data, fsm_name_c, "Generic C (Header/Source Pair)", {})
    return template.render(context)

def _prepare_template_context(diagram_data: Dict, fsm_name_c: str, target_platform: str, options: Dict) -> Dict:
    """Prepares the context dictionary for Jinja2 rendering."""
    platform_to_snippet_lang = {
        "Arduino (.ino Sketch)": "Arduino (C++)",
        "Generic C (Header/Source Pair)": "C (Generic Embedded)",
        "State Table (Function Pointers)": "C (Generic Embedded)",
        "ESP-IDF (main.c Snippet)": "C (Generic Embedded)",
        "Pico SDK (main.c Snippet)": "C (Generic Embedded)",
        "STM32 HAL (Snippet)": "C (Generic Embedded)"
    }
    target_lang = platform_to_snippet_lang.get(target_platform, "C (Generic Embedded)")

    def code_to_c_stub(py_like_code: str) -> list[str]:
        if not py_like_code:
            return ["    // No action defined"]
        stub_lines = []
        target_actions = MECHATRONICS_SNIPPETS.get(target_lang, {}).get('actions', {})

        for line in py_like_code.split('\n'):
            line = line.strip()
            if not line: continue
            
            intent_info = REVERSE_SNIPPET_MAP.get(line)
            if intent_info and intent_info['name'] in target_actions:
                stub_lines.append(f"    {target_actions[intent_info['name']]}")
                continue
            
            print_match = re.match(r"print\((.*)\)", line)
            if print_match:
                arg = print_match.group(1).strip()
                if arg.startswith(('f"', "f'")):
                    format_str = re.sub(r'\{([^}]+)\}', '%d', arg[2:-1]) # Assume %d for stub
                    variables = ", " + ", ".join(re.findall(r'\{([^}]+)\}', arg[2:-1]))
                    stub_lines.append(f'    printf("{format_str}\\n"{variables});')
                else:
                    stub_lines.append(f'    printf({arg.replace("'", '"')}"\\n");')
                continue

            inc_match = re.match(r"(\w+)\s*=\s*\1\s*\+\s*1", line)
            if inc_match:
                stub_lines.append(f"    {inc_match.group(1)}++;")
                continue
            
            assign_match = re.match(r"(\w+)\s*=\s*(.*)", line)
            if assign_match and not any(k in assign_match.group(1) for k in ['==', '!=', '>', '<']):
                value = assign_match.group(2).strip()
                if not value.endswith(';'): value += ';'
                stub_lines.append(f"    {assign_match.group(1)} = {value}")
                continue

            stub_lines.append(f'    // TODO: Implement logic for: {line}')
        return stub_lines if stub_lines else ["    // TODO: Implement logic"]

    for state in diagram_data['states']:
        state['c_name'] = sanitize_c_identifier(state['name'], prefix="s_")

    initial_state = next((s for s in diagram_data['states'] if s.get('is_initial')), diagram_data['states'][0])

    events = sorted(list(set(t['event'] for t in diagram_data.get('transitions', []) if t.get('event'))))
    events_list = [{'name': e, 'c_name': sanitize_c_identifier(e, 'evt_')} for e in events]

    action_functions = {}
    condition_functions = {}

    def add_func(func_map, func_name, code, source_info, return_type, args="void"):
        if func_name and code:
            signature = f"{return_type} {func_name}({args})"
            func_map[func_name] = (signature, code, source_info)

    for state in diagram_data['states']:
        state_c_name = state['c_name']
        state['entry_action_func'] = f"on_entry_{state_c_name}" if state.get('entry_action') else None
        add_func(action_functions, state['entry_action_func'], state.get('entry_action'), f"Entry action for '{state['name']}'", "void")
        state['during_action_func'] = f"on_during_{state_c_name}" if state.get('during_action') else None
        add_func(action_functions, state['during_action_func'], state.get('during_action'), f"During action for '{state['name']}'", "void")
        state['exit_action_func'] = f"on_exit_{state_c_name}" if state.get('exit_action') else None
        add_func(action_functions, state['exit_action_func'], state.get('exit_action'), f"Exit action for '{state['name']}'", "void")
        
        state['transitions'] = []
        for t in diagram_data.get('transitions', []):
            if t.get('source') == state['name']:
                target_state = next((s for s in diagram_data['states'] if s['name'] == t['target']), None)
                if target_state:
                    t_copy = t.copy()
                    t_copy['target_c_name'] = target_state['c_name']
                    t_copy['event'] = {'c_name': sanitize_c_identifier(t.get('event', ''), 'evt_')}
                    
                    t_copy['action_func'] = f"on_trans_{state_c_name}_to_{target_state['c_name']}" if t.get('action') else None
                    add_func(action_functions, t_copy['action_func'], t.get('action'), f"Action for '{state['name']}->{target_state['name']}'", "void")
                    
                    t_copy['condition_str'] = t.get('condition', '')
                    t_copy['condition_func'] = f"check_cond_{state_c_name}_to_{target_state['c_name']}" if t.get('condition') else None
                    add_func(condition_functions, t_copy['condition_func'], t.get('condition'), f"Condition for '{state['name']}->{target_state['name']}'", "bool")
                    
                    state['transitions'].append(t_copy)

    initial_state_entry_func = f"on_entry_{initial_state['c_name']}" if initial_state.get('entry_action') else None

    context = {
        "fsm_name_c": fsm_name_c,
        "h_guard": f"FSM_{fsm_name_c.upper()}_H",
        "states": diagram_data['states'],
        "events": events_list,
        "initial_state_c_enum": f"STATE_{initial_state['c_name'].upper()}",
        "initial_state_entry_func": initial_state_entry_func,
        "action_functions": list(action_functions.values()),
        "condition_functions": list(condition_functions.values()),
        "action_prototypes": [sig + ";" for sig, _, _ in action_functions.values()],
        "condition_prototypes": [sig + ";" for sig, _, _ in condition_functions.values()],
        "state_enum_type": "int8_t",
        "event_enum_type": "int8_t",
        "options": options,
        "code_to_c_stub": code_to_c_stub,
        "app_name": "BSM Designer", "app_version": "2.0.0", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return context