# bsm_designer_project/ai_providers/groq.py
import logging
from typing import List, Dict

try:
    import groq
except ImportError:
    groq = None

from .base import AIProvider

logger = logging.getLogger(__name__)

class GroqProvider(AIProvider):
    """AI Provider for models on Groq (e.g., Llama3), using OpenAI-compatible API."""
    def __init__(self, model_name="llama3-70b-8192"):
        if groq is None:
            raise ImportError("The 'groq' library is not installed. Please `pip install groq`.")
        self.model_name = model_name
        self.client: groq.Groq | None = None

    def get_name(self) -> str:
        return "Groq (Llama3)"

    def is_configured(self) -> bool:
        return self.client is not None