# bsm_designer_project/ai_providers/gemini.py
import logging
from typing import List, Dict

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import google.api_core.exceptions

from .base import AIProvider

logger = logging.getLogger(__name__)

class GeminiProvider(AIProvider):
    """AI Provider for Google Gemini models."""
    def __init__(self, model_name="gemini-1.5-flash-latest"):
        self.model_name = model_name
        self.client: genai.GenerativeModel | None = None
        self._api_key_set = False

    def get_name(self) -> str:
        return "Gemini (Google AI)"

    def is_configured(self) -> bool:
        return self.client is not None and self._api_key_set

    def configure(self, api_key: str) -> bool:
        if not api_key:
            self.client = None
            self._api_key_set = False
            return False
        try:
            genai.configure(api_key=api_key)
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            self.client = genai.GenerativeModel(self.model_name, safety_settings=safety_settings)
            self._api_key_set = True
            logger.info("GeminiProvider configured successfully.")
            return True
        except Exception as e:
            self.client = None
            self._api_key_set = False
            logger.error(f"Failed to configure GeminiProvider: {e}", exc_info=True)
            raise ConnectionRefusedError(f"Gemini API key validation failed: {e}")

    def generate_response(self, conversation_history: List[Dict], is_json_mode: bool) -> str:
        if not self.is_configured():
            raise PermissionError("Gemini provider is not configured.")

        generation_config = genai.types.GenerationConfig(temperature=0.7)
        if is_json_mode:
            generation_config.response_mime_type = "application/json"
            logger.info("GeminiProvider: Requesting JSON format.")

        try:
            response = self.client.generate_content(
                contents=conversation_history,
                generation_config=generation_config
            )

            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text
            
            # Handle cases where the response might be blocked
            finish_reason = response.candidates[0].finish_reason if response.candidates else "Unknown"
            raise ValueError(f"Gemini response was empty or blocked. Finish Reason: {finish_reason}")

        except (google.api_core.exceptions.PermissionDenied, google.auth.exceptions.RefreshError) as e:
            raise PermissionError(f"Gemini Authentication Error: {e}")
        except google.api_core.exceptions.ResourceExhausted as e:
            raise ConnectionAbortedError(f"Gemini Rate Limit Exceeded: {e}")
        except Exception as e:
            logger.error(f"GeminiProvider.generate_response error: {e}", exc_info=True)
            raise