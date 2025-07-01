# bsm_designer_project/ai_providers/__init__.py
import os
import importlib
import inspect
import logging

from .base import AIProvider

logger = logging.getLogger(__name__)

_providers = {}

def _discover_providers():
    """Dynamically discover AIProvider subclasses in this directory."""
    if _providers:
        return
        
    current_dir = os.path.dirname(__file__)
    for filename in os.listdir(current_dir):
        if filename.endswith(".py") and not filename.startswith("_"):
            module_name = filename[:-3]
            try:
                module = importlib.import_module(f".{module_name}", package=__name__)
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, AIProvider) and obj is not AIProvider:
                        try:
                            instance = obj()
                            provider_name = instance.get_name()
                            _providers[provider_name] = obj
                            logger.info(f"Discovered AI Provider: '{provider_name}'")
                        except ImportError as e:
                            logger.warning(f"Could not instantiate provider '{name}' from '{module_name}'. Library might be missing: {e.name}")
                        except Exception as e:
                            logger.error(f"Error instantiating provider '{name}': {e}", exc_info=True)
            except ImportError as e:
                logger.warning(f"Could not import module '{module_name}.py'. Required library might be missing: {e.name}")
            except Exception as e:
                logger.error(f"Error discovering provider in '{module_name}.py': {e}", exc_info=True)

_discover_providers()

def get_available_providers() -> dict[str, type[AIProvider]]:
    """Return a dictionary of available provider names to their classes."""
    return _providers

def get_provider_by_name(name: str) -> type[AIProvider] | None:
    """Return the provider class for a given name."""
    return _providers.get(name)
--- END OF FILE fsm_designer_project/ai_providers/__init__.py ---
--- START OF FILE fsm_designer_project/ai_providers/anthropic.py ---
# bsm_designer_project/ai_providers/anthropic.py
import logging
from typing import List, Dict, Optional

try:
    import anthropic
except ImportError:
    anthropic = None

from .base import AIProvider

logger = logging.getLogger(__name__)

class AnthropicProvider(AIProvider):
    """AI Provider for Anthropic's Claude models."""

    def __init__(self, model_name="claude-3-5-sonnet-20240620"):
        if anthropic is None:
            raise ImportError("The 'anthropic' library is not installed. Please `pip install anthropic`.")
        self.model_name = model_name
        self.client: Optional[anthropic.Anthropic] = None

    def get_name(self) -> str:
        return "Anthropic (Claude)"

    def is_configured(self) -> bool:
        return self.client is not None

    def configure(self, api_key: str) -> bool:
        if not api_key:
            self.client = None
            return False
        try:
            self.client = anthropic.Anthropic(api_key=api_key)
            # Anthropic client doesn't have a lightweight check, assume valid if initialized
            logger.info("AnthropicProvider configured successfully.")
            return True
        except Exception as e:
            self.client = None
            logger.error(f"Failed to configure AnthropicProvider: {e}", exc_info=True)
            raise ConnectionRefusedError(f"Failed to initialize Anthropic client: {e}")

    def generate_response(self, conversation_history: List[Dict], is_json_mode: bool) -> str:
        if not self.is_configured():
            raise PermissionError("Anthropic provider is not configured.")

        # Separate system prompt from the message history
        system_prompt = ""
        messages = []
        for msg in conversation_history:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                messages.append(msg)

        # For JSON mode, Anthropic recommends adding a specific instruction at the end
        if is_json_mode:
            if messages and messages[-1]["role"] == "user":
                messages[-1]["content"] += "\n\nIMPORTANT: Respond with ONLY the valid JSON object requested. Do not include any other text, explanations, or markdown formatting."
            else:
                 messages.append({"role": "user", "content": "Please provide the response in a single, valid JSON object format."})

        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=4096,
                system=system_prompt if system_prompt else None,
                messages=messages
            )
            return response.content[0].text
        except anthropic.AuthenticationError as e:
            raise PermissionError(f"Anthropic Authentication Error: {e.message}")
        except anthropic.RateLimitError as e:
            raise ConnectionAbortedError(f"Anthropic Rate Limit Exceeded: {e.message}")
        except Exception as e:
            logger.error(f"AnthropicProvider.generate_response error: {e}", exc_info=True)
            raise