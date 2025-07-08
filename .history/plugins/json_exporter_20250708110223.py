# fsm_designer_project/plugins/json_exporter.py
import json
from .api import BsmExporterPlugin

class JsonExporter(BsmExporterPlugin):
    @property
    def name(self) -> str:
        return "Raw Diagram JSON"

    @property
    def file_filter(self) -> str:
        return "JSON Files (*.json)"

    def export(self, diagram_data: dict) -> str:
        # Simply format the received dictionary into a pretty-printed JSON string.
        return json.dumps(diagram_data, indent=4, ensure_ascii=False)