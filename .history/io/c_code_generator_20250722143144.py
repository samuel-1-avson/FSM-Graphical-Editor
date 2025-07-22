# fsm_designer_project/io/c_code_generator.py
import os
import re
import logging
import html
from jinja2 import Environment, FileSystemLoader, select_autoescape, StrictUndefined
from datetime import datetime
from PyQt5.QtCore import QDateTime

logger = logging.getLogger(__name__)

# This dictionary maps the platform string from the UI to the specific
# Jinja2 template files that should be used for generation (Switch-Case style).
PLATFORM_TEMPLATE_MAP = {
    "Generic C (Header/Source Pair)": ("fsm.c.j2", "fsm.h.j2"),
    "Arduino (.ino Sketch)": ("fsm_arduino.ino.j2", "fsm_arduino.h.j2"),
    "STM32 HAL (Snippet)": ("fsm_stm32_hal.c.j2", "fsm_stm32_hal.h.j2"),
}

# NEW: Define templates for the State Table implementation style.
TABLE_DRIVEN_TEMPLATE_MAP = {
    "Generic C (Header/Source Pair)": ("fsm_table.c.j2", "fsm_table.h.j2"),
    # Platform-specific table-driven templates can be added here in the future.
    # For now, other platforms will fall back to the generic C templates.
}

def sanitize_c_identifier(name_str: str, prefix_if_digit="s_") -> str:
    """Sanitizes a string to be a valid C identifier."""
    if not name_str:
        return f"{prefix_if_digit}Unnamed"
    
    sanitized = name_str.replace(' ', '_').replace('-', '_').replace('.', '_')
    sanitized = sanitized.replace(':', '_').replace('/', '_').replace('\\', '_')
    sanitized = sanitized.replace('(', '').replace(')', '').replace('[', '')
    sanitized = sanitized.replace(']', '').replace('{', '').replace('}', '')
    sanitized = sanitized.replace('"', '').replace("'", "")

    sanitized = "".join(c if c.isalnum() or c == '_' else '' for c in sanitized)
    
    c_keywords = {
        "auto", "break", "case", "char", "const", "continue", "default", "do",
        "double", "else", "enum", "extern", "float", "for", "goto", "if",
        "int", "long", "register", "return", "short", "signed", "sizeof", "static",
        "struct", "switch", "typedef", "union", "unsigned", "void", "volatile", "while",
        "class", "public", "private", "protected", "new", "delete", "this", "try", "catch", "throw",
        "namespace", "template", "typename", "virtual", "explicit", "operator"
    }
    if sanitized in c_keywords:
        sanitized = f"fsm_{sanitized}"

    if not sanitized:
         return f"{prefix_if_digit}SanitizedEmpty"
    if sanitized and sanitized[0].isdigit():
        sanitized = prefix_if_digit + sanitized
    
    return sanitized

def translate_action_to_c_stub_line(py_action_line: str, target_platform: str) -> str:
    """Translates a single line of Python-like action into a C-like stub with a TODO comment."""
    py_action_line = py_action_line.strip()
    if not py_action_line or py_action_line.startswith("#"):
        return ""

    if "Arduino" in target_platform:
        m_print = re.match(r"print\s*\((.*)\)$", py_action_line)
        if m_print: return f'    Serial.println({m_print.group(1).strip()});'
        m_set_high = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(1|True|HIGH)$", py_action_line, re.IGNORECASE)
        if m_set_high: return f"    digitalWrite({sanitize_c_identifier(m_set_high.group(1)).upper()}, HIGH); // TODO: Define pin"
        m_set_low = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(0|False|LOW)$", py_action_line, re.IGNORECASE)
        if m_set_low: return f"    digitalWrite({sanitize_c_identifier(m_set_low.group(1)).upper()}, LOW); // TODO: Define pin"
        m_delay = re.match(r"delay\s*\(\s*(\d+)\s*\)$", py_action_line)
        if m_delay: return f"    delay({m_delay.group(1)});"

    if "STM32" in target_platform:
        m_print = re.match(r"print\s*\((.*)\)$", py_action_line)
        if m_print: return f'    printf({m_print.group(1).strip()}); // TODO: Retarget printf'
        m_set_high = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(1|True|HIGH)$", py_action_line, re.IGNORECASE)
        if m_set_high: return f"    HAL_GPIO_WritePin({sanitize_c_identifier(m_set_high.group(1))}_GPIO_Port, {sanitize_c_identifier(m_set_high.group(1))}_Pin, GPIO_PIN_SET);"
        m_set_low = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(0|False|LOW)$", py_action_line, re.IGNORECASE)
        if m_set_low: return f"    HAL_GPIO_WritePin({sanitize_c_identifier(m_set_low.group(1))}_GPIO_Port, {sanitize_c_identifier(m_set_low.group(1))}_Pin, GPIO_PIN_RESET);"
        m_delay = re.match(r"delay\s*\(\s*(\d+)\s*\)$", py_action_line)
        if m_delay: return f"    HAL_Delay({m_delay.group(1)});"

    m_set_value = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(\d+)$", py_action_line)
    if m_set_value: return f"    {sanitize_c_identifier(m_set_value.group(1))} = {m_set_value.group(2)}; // TODO: Declare variable"
    m_func_call = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\s*\)$", py_action_line)
    if m_func_call: return f"    {sanitize_c_identifier(m_func_call.group(1))}(); // TODO: Implement function"

    return f"    // TODO: Manually translate this action: {html.escape(py_action_line)}"

def code_to_c_stub(code: str, target_platform: str) -> list:
    if not code: return []
    return [line for line in (translate_action_to_c_stub_line(l.strip(), target_platform) for l in code.split('\n')) if line]

def generate_c_testbench_content(diagram_data: dict, fsm_name_c: str) -> str:
    """
    Generates the C testbench source file content as a string.
    """
    if not diagram_data.get('states'):
        raise ValueError("Cannot generate testbench: No states defined in the diagram.")

    # --- FIX: Correct the path to go up one level to find the 'templates' directory ---
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'templates')
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=select_autoescape(), trim_blocks=True, lstrip_blocks=True, undefined=StrictUndefined)
    
    context = {
        "fsm_name_c": fsm_name_c,
        "app_name": "BSM Designer", 
        "app_version": "2.0+",
        "timestamp": QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss"),
        "states": [], "events": [],
        "initial_state_c_enum": "/* ERROR: No initial state found */ (FSM_State_t)0",
    }

    initial_state_found = False
    for state_data in diagram_data.get('states', []):
        state_ctx = {
            "name": state_data.get('name'),
            "c_name": sanitize_c_identifier(state_data.get('name'))
        }
        context["states"].append(state_ctx)
        if state_data.get('is_initial') and not initial_state_found:
            context["initial_state_c_enum"] = f"STATE_{state_ctx['c_name'].upper()}"
            initial_state_found = True

    if not initial_state_found and context['states']:
        context["initial_state_c_enum"] = f"STATE_{sanitize_c_identifier(context['states'][0]['name']).upper()}"

    unique_events = sorted(list(set(t['event'] for t in diagram_data.get('transitions', []) if t.get('event'))))
    context['events'] = [{"c_name": sanitize_c_identifier(event)} for event in unique_events]

    template = env.get_template("testbench.c.j2")
    return template.render(context)


def generate_c_code_content(diagram_data: dict, base_filename: str, target_platform: str, generation_options: dict | None = None) -> dict[str, str]:
    """
    Generates C header and source content as strings from diagram data for a specific platform.
    """
    if not diagram_data.get('states'):
        raise ValueError("Cannot generate code: No states defined in the diagram.")
    
    options = generation_options or {}
    
    # --- FIX: Correct the path to go up one level to find the 'templates' directory ---
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'templates')
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=select_autoescape(), trim_blocks=True, lstrip_blocks=True, undefined=StrictUndefined)
    env.globals['code_to_c_stub'] = lambda code: code_to_c_stub(code, target_platform)

    style = options.get("implementation_style", "Switch-Case Statement")
    if style == "State Table (Function Pointers)":
        c_template_name, h_template_name = TABLE_DRIVEN_TEMPLATE_MAP.get(target_platform, TABLE_DRIVEN_TEMPLATE_MAP["Generic C (Header/Source Pair)"])
        logger.info(f"Using State Table templates '{c_template_name}' and '{h_template_name}'.")
    else:
        c_template_name, h_template_name = PLATFORM_TEMPLATE_MAP.get(target_platform, PLATFORM_TEMPLATE_MAP["Generic C (Header/Source Pair)"])
        logger.info(f"Using Switch-Case templates '{c_template_name}' and '{h_template_name}'.")

    fsm_name_c = sanitize_c_identifier(base_filename, "fsm_")
    
    context = {
        "fsm_name_c": fsm_name_c, "h_guard": f"{fsm_name_c.upper()}_H",
        "states": [], "events": [], 
        "action_prototypes": set(), "condition_prototypes": set(),
        "action_functions": [], "condition_functions": [],
        "initial_state_c_enum": "/* ERROR: No initial state defined */ (FSM_State_t)0",
        "initial_state_entry_func": None, "now": datetime.now,
        "target_platform": target_platform,
        "options": options,
        "state_enum_type": options.get("data_type", "FSM_State_t"),
        "event_enum_type": options.get("data_type", "FSM_Event_t")
    }
    
    states_data = diagram_data.get('states', [])
    transitions_data = diagram_data.get('transitions', [])
    state_map_by_name = {}
    
    for state_data in states_data:
        state_ctx = {
            "name": state_data['name'], "c_name": sanitize_c_identifier(state_data['name']),
            "is_initial": state_data.get('is_initial', False), "transitions": [],
            "entry_action_func": None, "during_action_func": None, "exit_action_func": None
        }
        for action_type in ['entry_action', 'during_action', 'exit_action']:
            code = state_data.get(action_type, "").strip()
            if code:
                func_name = sanitize_c_identifier(f"{action_type}_{state_ctx['c_name']}")
                func_sig = f"void {func_name}(void)"
                state_ctx[f'{action_type}_func'] = func_name
                context["action_prototypes"].add(func_sig)
                context["action_functions"].append((func_sig, code, f"Source: {action_type} of state '{state_data['name']}'"))
        if state_ctx['is_initial']:
            context["initial_state_c_enum"] = f"STATE_{state_ctx['c_name'].upper()}"
            context["initial_state_entry_func"] = state_ctx['entry_action_func']
        context['states'].append(state_ctx)
        state_map_by_name[state_data['name']] = state_ctx

    if context["initial_state_entry_func"] is None and context['states']:
        first_state = context['states'][0]
        context["initial_state_c_enum"] = f"STATE_{first_state['c_name'].upper()}"
        if first_state['entry_action_func']:
             context["initial_state_entry_func"] = first_state['entry_action_func']
    
    unique_events = sorted(list(set(t['event'] for t in transitions_data if t.get('event'))))
    context['events'] = [{"c_name": sanitize_c_identifier(event)} for event in unique_events]
    
    for trans_data in sorted(transitions_data, key=lambda t: t.get('priority', 0), reverse=True):
        src_state_ctx = state_map_by_name.get(trans_data.get('source'))
        if not src_state_ctx or not trans_data.get('event'): continue
        
        trans_ctx = {
            "target_c_name": sanitize_c_identifier(trans_data['target']),
            "condition_str": trans_data.get('condition', ""),
            "action_func": None,
            "condition_func": None
        }
        trans_ctx['event'] = {'c_name': sanitize_c_identifier(trans_data['event'])}
        
        if action_code := trans_data.get('action', "").strip():
            func_name = sanitize_c_identifier(f"action_trans_{src_state_ctx['c_name']}_to_{trans_ctx['target_c_name']}_{trans_ctx['event']['c_name']}")
            func_sig = f"void {func_name}(void)"
            trans_ctx['action_func'] = func_name
            context["action_prototypes"].add(func_sig)
            context["action_functions"].append((func_sig, action_code, f"Source: Transition '{src_state_ctx['name']}' -> '{trans_data['target']}'"))

        if condition_code := trans_data.get('condition', "").strip():
            cond_func_name = sanitize_c_identifier(f"cond_trans_{src_state_ctx['c_name']}_to_{trans_ctx['target_c_name']}_{trans_ctx['event']['c_name']}")
            cond_func_sig = f"bool {cond_func_name}(void)" # Use bool for C99+
            trans_ctx['condition_func'] = cond_func_name
            context["condition_prototypes"].add(cond_func_sig)
            context["condition_functions"].append((cond_func_sig, f"return ({condition_code});", f"Source: Condition for transition '{src_state_ctx['name']}' -> '{trans_data['target']}'"))

        src_state_ctx['transitions'].append(trans_ctx)
    
    context["action_prototypes"] = sorted(list(context["action_prototypes"]))
    context["condition_prototypes"] = sorted(list(context["condition_prototypes"]))
    
    # Deduplicate functions
    seen_sigs = set()
    context["action_functions"] = [x for x in context["action_functions"] if x[0] not in seen_sigs and not seen_sigs.add(x[0])]
    context["condition_functions"] = [x for x in context["condition_functions"] if x[0] not in seen_sigs and not seen_sigs.add(x[0])]
    
    h_template = env.get_template(h_template_name)
    c_template = env.get_template(c_template_name)
    h_code = h_template.render(context)
    c_code = c_template.render(context)
    
    file_ext_c = ".ino" if target_platform == "Arduino (.ino Sketch)" else ".c"
    
    return {'h': h_code, 'c': c_code, 'c_ext': file_ext_c}

def generate_c_code_files(diagram_data: dict, output_dir: str, base_filename: str, target_platform: str, generation_options: dict | None = None) -> tuple[str, str]:
    """
    Generates C header and source files for the FSM using the correct platform templates.
    """
    try:
        content = generate_c_code_content(diagram_data, base_filename, target_platform, generation_options)
        
        h_code = content['h']
        c_code = content['c']
        c_ext = content['c_ext']
        
        fsm_name_c = sanitize_c_identifier(base_filename, "fsm_")
        
        h_file_path = os.path.join(output_dir, f"{fsm_name_c}.h")
        c_file_path = os.path.join(output_dir, f"{fsm_name_c}{c_ext}")
        
        with open(h_file_path, 'w', encoding='utf-8') as f:
            f.write(h_code)
        with open(c_file_path, 'w', encoding='utf-8') as f:
            f.write(c_code)
            
        logger.info(f"Generated platform-aware code files: {h_file_path}, {c_file_path}")
        return c_file_path, h_file_path
    except (ValueError, FileNotFoundError, IOError) as e:
        logger.error(f"Failed to generate C code files: {e}", exc_info=True)
        raise