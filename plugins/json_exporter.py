# fsm_designer_project/plugins/json_exporter.py
import json
from typing import Dict
from .api import BsmExporterPlugin

class JsonExporter(BsmExporterPlugin):
    @property
    def name(self) -> str:
        return "Raw Diagram JSON"

    @property
    def file_filter(self) -> str:
        return "JSON Files (*.json)"

    # --- FIX: Conform to the BsmExporterPlugin API specification ---
    def export(self, diagram_data: dict, **kwargs) -> Dict[str, str]:
        # Simply format the received dictionary into a pretty-printed JSON string.
        content = json.dumps(diagram_data, indent=4, ensure_ascii=False)
        base_filename = kwargs.get("base_filename", "fsm_diagram")
        return {f"{base_filename}.json": content}