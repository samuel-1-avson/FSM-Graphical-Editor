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

        # --- NEW: Convert standard history to Gemini format ---
        gemini_history = []
        for msg in conversation_history:
            role = msg.get("role")
            content = msg.get("content", "")
            
            # Gemini uses 'model' for the assistant's role. It doesn't officially support 'system' in the same way,
            # but we can often prepend it as the first 'user' message with instructions, or hope the model infers it.
            # For multi-turn chat, we map 'assistant' to 'model'. System messages should ideally be handled by the caller.
            if role == "assistant":
                role = "model"
            
            # Gemini expects 'parts' to be a list, and content to be non-empty.
            if content and role in ["user", "model"]:
                gemini_history.append({"role": role, "parts": [{"text": content}]})
            elif role == "system" and content:
                 # Gemini API prefers system instructions not be part of the main `contents` history.
                 # Often they are passed as a separate parameter, but here we can prepend it
                 # as the first user message for context. Let's adapt based on `generate_content` docs.
                 # The `genai.GenerativeModel` can take a `system_instruction` at init.
                 # Since we don't do that here, we will just format it as a normal message.
                 # A more robust solution would handle this better. For now, we'll just pass it.
                 # A simpler conversion is just to map the role and content.
                 gemini_history.append({"role": "user", "parts": [{"text": f"SYSTEM PROMPT: {content}"}]})


        generation_config = genai.types.GenerationConfig(temperature=0.7)
        if is_json_mode:
            generation_config.response_mime_type = "application/json"
            logger.info("GeminiProvider: Requesting JSON format.")

        try:
            # The generate_content 'contents' param expects an iterable of Content objects (role, parts).
            # The list of dicts we created is compatible.
            response = self.client.generate_content(
                contents=gemini_history,
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