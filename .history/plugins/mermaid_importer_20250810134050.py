# fsm_designer_project/plugins/mermaid_importer.py

import logging
from typing import Dict, Optional

from .api import BsmImporterPlugin
# Import the original parsing function
from ..codegen.fsm_importer import parse_mermaid

logger = logging.getLogger(__name__)

class MermaidImporter(BsmImporterPlugin):
    """
    A plugin to import FSM diagrams from Mermaid.js text format.
    """
    @property
    def name(self) -> str:
        """The user-friendly name of the importer."""
        return "Mermaid Diagram"

    @property
    def file_filter(self) -> str:
        """The file filter for the open dialog."""
        return "Mermaid Files (*.mmd);;Markdown Files (*.md)"

    def import_data(self, file_content: str) -> Optional[Dict]:
        """
        Uses a parser to convert Mermaid text into standard diagram data.
        """
        try:
            # The core logic is handled by the parser.
            diagram_data = parse_mermaid(file_content)
            
            if not diagram_data or (not diagram_data.get('states') and not diagram_data.get('transitions')):
                logger.warning("Mermaid Importer: Parsing succeeded but resulted in an empty diagram.")
                return None
            
            logger.info("Successfully parsed Mermaid diagram content.")
            return diagram_data
            
        except Exception as e:
            logger.error(f"An error occurred during Mermaid parsing: {e}", exc_info=True)
            raise ValueError(f"Could not parse Mermaid file: {e}") from e