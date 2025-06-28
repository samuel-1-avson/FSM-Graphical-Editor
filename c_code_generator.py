# bsm_designer_project/c_code_generator.py
import os
import re
import logging
import html
from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

def sanitize_c_identifier(name_str: str, prefix_if_digit="s_") -> str:
    """
    Sanitizes a string to be a valid C identifier.
    It replaces invalid characters, prefixes if it starts with a digit, and appends an underscore if it's a C keyword.
    """
    if not name_str:
        return f"{prefix_if_digit}Unnamed"
    
    # Replace spaces and common problematic characters with underscores
    sanitized = name_str.replace(' ', '_').replace('-', '_').replace('.', '_')
    sanitized = sanitized.replace(':', '_').replace('/', '_').replace('\\', '_')
    sanitized = sanitized.replace('(', '').replace(')', '').replace('[', '')
    sanitized = sanitized.replace(']', '').replace('{', '').replace('}', '')
    sanitized = sanitized.replace('"', '').replace("'", "")

    # Remove any remaining characters not alphanumeric or underscore
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

def translate_action_to_c_stub_line(py_action_line: str) -> str:
    """
    Translates a single line of Python-like action into a C-like stub with a TODO comment.
    This is a heuristic and aims to guide the user, not perform perfect translation.
    """
    py_action_line = py_action_line.strip()
    if not py_action_line or py_action_line.startswith("#"):
        return ""  # Ignore empty lines and Python comments in the stub body

    # Heuristics for common mechatronic actions
    m_set_high = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(1|True|HIGH)$", py_action_line, re.IGNORECASE)
    if m_set_high:
        var_name = sanitize_c_identifier(m_set_high.group(1))
        return f"    digitalWrite(PIN_FOR_{var_name.upper()}, HIGH); // TODO: Define PIN_FOR_{var_name.upper()}"

    m_set_low = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(0|False|LOW)$", py_action_line, re.IGNORECASE)
    if m_set_low:
        var_name = sanitize_c_identifier(m_set_low.group(1))
        return f"    digitalWrite(PIN_FOR_{var_name.upper()}, LOW);  // TODO: Define PIN_FOR_{var_name.upper()}"

    m_set_value = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(\d+)$", py_action_line)
    if m_set_value:
        var_name = sanitize_c_identifier(m_set_value.group(1))
        value = m_set_value.group(2)
        return f"    {var_name} = {value}; // TODO: Ensure '{var_name}' is declared (e.g., static int {var_name};)"

    m_func_call_simple = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\s*\)$", py_action_line)
    if m_func_call_simple:
        func_name = sanitize_c_identifier(m_func_call_simple.group(1))
        return f"    {func_name}(); // TODO: Implement function {func_name}()"
    
    m_print = re.match(r"print\s*\((.*)\)$", py_action_line)
    if m_print:
        inner_print = m_print.group(1).strip()
        m_fstring = re.match(r"f(['\"])(.*?)(\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\})(.*)\1", inner_print)
        if m_fstring:
            prefix, var_name, suffix = m_fstring.group(2), sanitize_c_identifier(m_fstring.group(4)), m_fstring.group(5)
            return f'    printf("{html.escape(prefix)}%d{html.escape(suffix)}\\n", {var_name}); // TODO: Verify type of {var_name}'
        elif inner_print.startswith("'") and inner_print.endswith("'") or inner_print.startswith('"') and inner_print.endswith('"'):
            return f'    printf("%s\\n", {inner_print});'
        else:
            return f'    printf("Value of {sanitize_c_identifier(inner_print)}: %d\\n", {sanitize_c_identifier(inner_print)}); // TODO: Verify type'

    return f"    // TODO: Manually translate this action: {html.escape(py_action_line)}"

def code_to_c_stub(code: str) -> list:
    """Helper function to be passed to Jinja2 for stub generation."""
    if not code:
        return []
    stub_lines = []
    for line in code.split('\n'):
        if line.strip():
            stub_lines.append(translate_action_to_c_stub_line(line.strip()))
    return [line for line in stub_lines if line] # Filter out empty results

def generate_c_code_files(diagram_data: dict, output_dir: str, base_filename: str) -> tuple[str, str]:
    """
    Generates C header and source files for the FSM using Jinja2 templates.
    """
    if not diagram_data.get('states'):
        raise ValueError("Cannot generate code: No states defined in the diagram.")
    
    # 1. Setup Jinja2 Environment
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    if not os.path.isdir(template_dir):
        raise FileNotFoundError(f"Jinja2 template directory not found at: {template_dir}")
        
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=select_autoescape(), trim_blocks=True, lstrip_blocks=True)
    env.globals['code_to_c_stub'] = code_to_c_stub # Make helper function available in template

    # 2. Prepare Data Context for Templates
    fsm_name_c = sanitize_c_identifier(base_filename, "fsm_")
    
    context = {
        "fsm_name_c": fsm_name_c, "h_guard": f"{fsm_name_c.upper()}_H",
        "states": [], "events": [], "action_prototypes": set(), "action_functions": [],
        "initial_state_c_enum": "/* ERROR: No initial state defined */ (FSM_State_t)0",
        "initial_state_entry_func": None
    }
    
    states_data = diagram_data.get('states', [])
    transitions_data = diagram_data.get('transitions', [])
    
    # Process states
    state_map_by_name = {}
    for state_data in states_data:
        state_ctx = {
            "name": state_data['name'], "c_name": sanitize_c_identifier(state_data['name']),
            "is_initial": state_data.get('is_initial', False),
            "transitions": [],
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

    # Default to first state if no initial state is explicitly set
    if context["initial_state_entry_func"] is None and context['states']:
        first_state = context['states'][0]
        context["initial_state_c_enum"] = f"STATE_{first_state['c_name'].upper()}"
        if first_state['entry_action_func']:
             context["initial_state_entry_func"] = first_state['entry_action_func']


    # Process transitions
    unique_events = sorted(list(set(t['event'] for t in transitions_data if t.get('event'))))
    context['events'] = [{"c_name": sanitize_c_identifier(event)} for event in unique_events]
    
    for trans_data in sorted(transitions_data, key=lambda t: t.get('priority', 0), reverse=True): # Higher priority first
        src_state_ctx = state_map_by_name.get(trans_data.get('source'))
        if not src_state_ctx or not trans_data.get('event'): continue

        trans_ctx = {"target_c_name": sanitize_c_identifier(trans_data['target']), "condition_str": trans_data.get('condition', ""), "action_func": None}
        trans_ctx['event'] = {'c_name': sanitize_c_identifier(trans_data['event'])}

        if action_code := trans_data.get('action', "").strip():
            func_name = sanitize_c_identifier(f"action_trans_{src_state_ctx['c_name']}_to_{trans_ctx['target_c_name']}_{trans_ctx['event']['c_name']}")
            func_sig = f"void {func_name}(void)"
            trans_ctx['action_func'] = func_name
            context["action_prototypes"].add(func_sig)
            context["action_functions"].append((func_sig, action_code, f"Source: Transition '{src_state_ctx['name']}' -> '{trans_data['target']}'"))

        src_state_ctx['transitions'].append(trans_ctx)

    # Finalize context data
    context["action_prototypes"] = sorted(list(context["action_prototypes"]))
    # To avoid duplicate function stubs if names clash after sanitization
    seen_sigs = set()
    context["action_functions"] = [x for x in context["action_functions"] if x[0] not in seen_sigs and not seen_sigs.add(x[0])]

    # 3. Render templates
    try:
        h_template = env.get_template("fsm.h.j2")
        c_template = env.get_template("fsm.c.j2")
        h_code = h_template.render(context)
        c_code = c_template.render(context)
    except Exception as e:
        logger.error(f"Jinja2 template rendering failed: {e}", exc_info=True)
        raise

    # 4. Write files
    h_file_path = os.path.join(output_dir, f"{fsm_name_c}.h")
    c_file_path = os.path.join(output_dir, f"{fsm_name_c}.c")
    try:
        with open(h_file_path, 'w', encoding='utf-8') as f:
            f.write(h_code)
        with open(c_file_path, 'w', encoding='utf-8') as f:
            f.write(c_code)
        logger.info(f"Generated C code files: {h_file_path}, {c_file_path}")
        return c_file_path, h_file_path
    except IOError as e:
        logger.error(f"IOError writing C code files: {e}", exc_info=True)
        raise