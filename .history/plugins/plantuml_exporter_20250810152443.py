# fsm_designer_project/plugins/plantuml_exporter.py
from typing import Dict
from .api import BsmExporterPlugin
from ..codegen.plantuml_exporter import generate_plantuml_text

class PlantUMLExporter(BsmExporterPlugin):
    @property
    def name(self) -> str:
        return "PlantUML"

    @property
    def file_filter(self) -> str:
        return "PlantUML Files (*.puml *.plantuml)"

    def export(self, diagram_data: dict, **kwargs) -> Dict[str, str]:
        content = generate_plantuml_text(diagram_data)
        base_filename = kwargs.get("base_filename", "fsm_diagram")
        return {f"{base_filename}.puml": content}