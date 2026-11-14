# context_loader.py
# Loads default measurement context from YAML for BoQ generation fallback

import os
import yaml
import logging

logger = logging.getLogger(__name__)

_CONTEXT_CACHE = None


def load_measurement_context(path=None):
    """
    Load the measurement_context.yaml file.
    Returns a dict with default values for BoQ generation fallback.
    Cached after first load for performance.
    """
    global _CONTEXT_CACHE

    if _CONTEXT_CACHE is not None:
        return _CONTEXT_CACHE

    if path is None:
        base_path = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_path, "measurement_context.yaml")

    try:
        with open(path, "r") as f:
            context = yaml.safe_load(f)
        logger.info(f"Loaded measurement context from {path}")
        _CONTEXT_CACHE = context
        return context
    except FileNotFoundError:
        logger.warning(f"Measurement context file not found: {path}")
        return {}
    except Exception as exc:
        logger.error(f"Error loading measurement context: {exc}")
        return {}


def get_foundation_defaults():
    """Return foundation-specific default values."""
    context = load_measurement_context()
    return context.get("foundation", {})


def get_default_boq_items():
    """Return the full list of default BoQ items organized by section."""
    context = load_measurement_context()
    return context.get("boq_items", [])


def get_default_confidence():
    """Return default confidence score."""
    context = load_measurement_context()
    return context.get("default_confidence", 0.5)


def get_default_rate():
    """Return default rate when AI cannot determine one."""
    context = load_measurement_context()
    return context.get("default_rate", 0.0)