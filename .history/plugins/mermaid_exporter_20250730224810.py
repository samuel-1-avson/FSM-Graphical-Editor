# fsm_designer_project/plugins/mermaid_exporter.py
from typing import Dict
from .api import BsmExporterPlugin

def generate_mermaid_text(diagram_data: Dict) -> str:
    """Generates Mermaid.js text from diagram data."""
    lines = ["stateDiagram-v2"]
    
    states = diagram_data.get('states', [])
    transitions = diagram_data.get('transitions', [])

    # Initial state
    initial_state = next((s['name'] for s in states if s.get('is_initial')), None)
    if initial_state:
        lines.append(f"    [*] --> {initial_state}")

    # State actions
    for state in states:
        name = state.get('name')
        if name:
            actions = []
            if state.get('entry_action'):
                actions.append(f"entry: {state['entry_action'].replace(chr(10), '; ')}")
            if state.get('during_action'):
                actions.append(f"during: {state['during_action'].replace(chr(10), '; ')}")
            if state.get('exit_action'):
                actions.append(f"exit: {state['exit_action'].replace(chr(10), '; ')}")
            
            if actions:
                lines.append(f"    {name} : {'<br>'.join(actions)}")

    # Transitions
    for t in transitions:
        source = t.get('source')
        target = t.get('target')
        label_parts = []
        if t.get('event'):
            label_parts.append(t['event'])
        if t.get('condition'):
            label_parts.append(f"[{t['condition']}]")
        if t.get('action'):
            label_parts.append(f"/{t['action']}")
        
        label = " ".join(label_parts)
        lines.append(f"    {source} --> {target} : {label}")
        
    return "\n".join(lines)


class MermaidExporter(BsmExporterPlugin):
    @property
    def name(self) -> str:
        return "Mermaid"

    @property
    def file_filter(self) -> str:
        return "Mermaid Files (*.mmd);;Markdown Files (*.md)"

    def export(self, diagram_data: dict, **kwargs) -> Dict[str, str]:
        content = generate_mermaid_text(diagram_data)
        base_filename = kwargs.get("base_filename", "fsm_diagram")
        return {f"{base_filename}.mmd": content}