# fsm_designer_project/plugins/plantuml_importer.py
import logging
from typing import Dict, Optional

from .api import BsmImporterPlugin
# --- MODIFIED: Import from the new codegen package ---
from ..codegen.fsm_importer import parse_plantuml

logger = logging.getLogger(__name__)

class PlantUMLImporter(BsmImporterPlugin):
    """
    A plugin to import FSM diagrams from PlantUML text format.
    """
    @property
    def name(self) -> str:
        return "PlantUML Diagram"

    @property
    def file_filter(self) -> str:
        return "PlantUML Files (*.puml *.plantuml)"

    def import_data(self, file_content: str) -> Optional[Dict]:
        """
        Uses the existing parser to convert PlantUML text into diagram data.
        """
        try:
            # Reuse the existing parsing logic from the io module
            diagram_data = parse_plantuml(file_content)
            
            # The parser returns a valid dictionary even if empty,
            # so we check if it actually found anything.
            if not diagram_data.get('states') and not diagram_data.get('transitions'):
                logger.warning("PlantUML Importer: Parsing resulted in an empty diagram.")
                return None
            
            return diagram_data
        except Exception as e:
            # The calling ActionHandler will catch this and show a user-friendly error
            logger.error(f"Error during PlantUML parsing: {e}", exc_info=True)
            return None