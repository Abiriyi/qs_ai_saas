# context_loader.py
# Loads default measurement context from YAML for BoQ generation fallback
# Integrates with ai_pricing.py rate library for Nigerian Naira rates

import os
import yaml
import logging
from datetime import date

from qs_ai_project.ai_pricing import get_rate_from_library

logger = logging.getLogger(__name__)

_CONTEXT_CACHE = None


def load_measurement_context(path=None):
    """
    Load the measurement_context.yaml file.
    Returns a dict with default values for BoQ generation fallback.
    Cached after first load for performance.
    The 'date' field is added dynamically at load time (not hardcoded in YAML).
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

        # Add current date dynamically (not hardcoded in YAML)
        context["date"] = date.today().isoformat()

        logger.info(f"Loaded measurement context from {path} (date: {context['date']})")
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


def get_currency_symbol():
    """Return the currency symbol (₦ for Nigerian Naira)."""
    context = load_measurement_context()
    return context.get("currency_symbol", "₦")


def get_currency_code():
    """Return the currency code (NGN)."""
    context = load_measurement_context()
    return context.get("currency", "NGN")


def get_default_locations():
    """Return list of default Nigerian locations."""
    context = load_measurement_context()
    return context.get("default_locations", ["Kaduna", "Abuja", "Kano", "Lagos", "Port-Harcourt"])


def get_default_location():
    """Return the default location (first in list)."""
    context = load_measurement_context()
    return context.get("default_location", "Kaduna")


def get_rate_from_library_with_fallback(element, unit, location=None, description=""):
    """
    Get a rate from the rate library with fallback to YAML defaults.
    
    Priority:
    1. Rate library (ai_pricing.py) - Nigerian Naira rates from CSV
    2. YAML default values from measurement_context.yaml
    3. 0.0 if nothing found
    
    Args:
        element: The element name (e.g., "Excavation", "Concrete")
        unit: The unit of measurement (e.g., "m3", "m2", "item")
        location: Nigerian location (Kaduna, Abuja, Kano, Lagos, Port-Harcourt)
        description: Optional description for fuzzy matching
    
    Returns:
        float: The rate in Nigerian Naira (₦)
    """
    if location is None:
        location = get_default_location()

    # Try rate library first
    rate = get_rate_from_library(element, description=description, unit=unit, location=location)
    if rate is not None:
        logger.info(f"Rate library: {element} ({unit}) @ {location} = ₦{rate:,.2f}")
        return rate

    # Fallback: try to find matching item in YAML defaults
    default_items = get_default_boq_items()
    for section in default_items:
        for item in section.get("items", []):
            # Match by item number prefix (e.g., B.1 matches excavation)
            item_no = item.get("item_no", "")
            item_unit = item.get("unit", "").lower()
            item_desc = item.get("description", "").lower()
            element_lower = (element or "").lower()
            unit_lower = (unit or "").lower()
            desc_lower = (description or "").lower()

            # Match by item number prefix
            if item_no and element_lower and item_no.split(".")[0].lower() == element_lower.split(" ")[0]:
                if item_unit == unit_lower:
                    logger.info(f"YAML fallback: {item_no} ({unit}) @ {location} = ₦{item['rate']:,.2f}")
                    return item["rate"]

            # Match by description keywords
            if element_lower and element_lower in item_desc:
                if item_unit == unit_lower:
                    logger.info(f"YAML fallback (desc match): {item_no} ({unit}) @ {location} = ₦{item['rate']:,.2f}")
                    return item["rate"]

    # Last resort: return default rate
    default_rate = get_default_rate()
    logger.warning(f"No rate found for {element} ({unit}) @ {location}, using default: ₦{default_rate:,.2f}")
    return default_rate
