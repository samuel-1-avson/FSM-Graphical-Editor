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
                        except Exception:
                            # Catch import errors for libs like openai if not installed
                            logger.warning(f"Could not instantiate provider '{name}' from '{module_name}'. Library might be missing.")

            except Exception as e:
                logger.error(f"Error discovering provider in '{module_name}.py': {e}", exc_info=True)

_discover_providers()

def get_available_providers() -> dict[str, type[AIProvider]]:
    """Return a dictionary of available provider names to their classes."""
    return _providers

def get_provider_by_name(name: str) -> type[AIProvider] | None:
    """Return the provider class for a given name."""
    return _providers.get(name)