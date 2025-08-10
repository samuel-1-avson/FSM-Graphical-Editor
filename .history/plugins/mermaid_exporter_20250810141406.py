# fsm_designer_project/plugins/mermaid_exporter.py
from typing import Dict
from .api import BsmExporterPlugin
# --- MODIFIED: Import from the new codegen package ---
from ..codegen.mermaid_exporter import generate_mermaid_text


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