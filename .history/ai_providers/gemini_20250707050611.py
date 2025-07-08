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
        self._system_instruction_cache = None # Cache to recreate model only when needed

    def get_name(self) -> str:
        return "Gemini (Google AI)"

    def is_configured(self) -> bool:
        return self._api_key_set

    def configure(self, api_key: str) -> bool:
        if not api_key:
            self.client = None
            self._api_key_set = False
            return False
        try:
            genai.configure(api_key=api_key)
            # A lightweight check to see if the key is valid by listing models
            next(genai.list_models())
            self._api_key_set = True
            logger.info("GeminiProvider configured and validated successfully.")
            return True
        except (google.api_core.exceptions.PermissionDenied, google.api_core.exceptions.Unauthenticated) as e:
            self.client = None
            self._api_key_set = False
            raise PermissionError(f"Gemini API key is invalid or permissions are insufficient: {e}")
        except Exception as e:
            self.client = None
            self._api_key_set = False
            logger.error(f"Failed to configure GeminiProvider: {e}", exc_info=True)
            raise ConnectionRefusedError(f"Gemini API key validation failed: {e}")

    def generate_response(self, conversation_history: List[Dict], is_json_mode: bool) -> str:
        if not self.is_configured():
            raise PermissionError("Gemini provider is not configured.")

        # Separate system prompt from the message history
        system_prompt = ""
        messages = []
        for msg in conversation_history:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            elif msg.get("content"):
                role = "model" if msg["role"] == "assistant" else msg["role"]
                # Gemini API expects a list of parts, here we just use one text part
                messages.append({"role": role, "parts": [msg["content"]]})

        # Re-create the model client only if the system instruction has changed
        if system_prompt != self._system_instruction_cache or self.client is None:
            self._system_instruction_cache = system_prompt
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            self.client = genai.GenerativeModel(
                self.model_name,
                safety_settings=safety_settings,
                system_instruction=self._system_instruction_cache
            )

        generation_config = genai.types.GenerationConfig(temperature=0.7)
        if is_json_mode:
            generation_config.response_mime_type = "application/json"
            logger.info("GeminiProvider: Requesting JSON format.")

        try:
            response = self.client.generate_content(
                contents=messages,
                generation_config=generation_config
            )

            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text
            
            # Handle blocked content
            finish_reason = response.candidates[0].finish_reason if response.candidates else "Unknown"
            if finish_reason == HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT:
                 raise ValueError("Response was blocked by the safety filter for dangerous content.")
            raise ValueError(f"Gemini response was empty. Finish Reason: {finish_reason}")

        except (google.api_core.exceptions.PermissionDenied, google.auth.exceptions.RefreshError) as e:
            raise PermissionError(f"Gemini Authentication Error: {e}")
        except google.api_core.exceptions.ResourceExhausted as e:
            raise ConnectionAbortedError(f"Gemini Rate Limit Exceeded: {e}")
        except Exception as e:
            logger.error(f"GeminiProvider.generate_response error: {e}", exc_info=True)
            raise