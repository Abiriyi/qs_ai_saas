# boq/services/ai_generator.py

import json
import logging

from openai import OpenAI
from django.conf import settings

from qs_ai_project.context_loader import (
    get_default_boq_items,
    get_default_confidence,
    get_currency_symbol,
    get_default_locations,
    get_default_location,
    get_rate_from_library_with_fallback,
)

logger = logging.getLogger(__name__)


def _build_default_lookup(default_items):
    """Build a lookup dict keyed by item_no from default boq items."""
    lookup = {}
    for section in default_items:
        for item in section.get("items", []):
            lookup[item["item_no"]] = item
    return lookup


def _apply_defaults(data, default_lookup):
    """
    Replace any AI-generated items with quantity <= 0 or rate <= 0
    with values from the default measurement context.
    """
    if not default_lookup:
        return data

    for section in data.get("sections", []):
        for item in section.get("items", []):
            item_no = item.get("item_no", "")
            default_item = default_lookup.get(item_no)

            if default_item is None:
                continue

            # Fix quantity if zero or missing
            try:
                qty = float(item.get("quantity", 0) or 0)
            except (TypeError, ValueError):
                qty = 0
            if qty <= 0:
                item["quantity"] = default_item.get("quantity", 0)
                item["unit"] = default_item.get("unit", item.get("unit", ""))
                logger.info(
                    f"Fallback: item {item_no} quantity set to default {item['quantity']}"
                )

            # Fix rate if zero or missing - try rate library first, then YAML default
            try:
                rate = float(item.get("rate", 0) or 0)
            except (TypeError, ValueError):
                rate = 0
            if rate <= 0:
                # Try rate library with element from item number prefix
                element_prefix = item_no.split(".")[0] if item_no else ""
                location = get_default_location()
                lib_rate = get_rate_from_library_with_fallback(
                    element=element_prefix,
                    unit=item.get("unit", ""),
                    location=location,
                    description=item.get("description", ""),
                )
                if lib_rate is not None and lib_rate > 0:
                    item["rate"] = lib_rate
                    logger.info(
                        f"Fallback: item {item_no} rate set from library to ₦{item['rate']:,.2f}"
                    )
                else:
                    item["rate"] = default_item.get("rate", 0)
                    logger.info(
                        f"Fallback: item {item_no} rate set to YAML default ₦{item['rate']:,.2f}"
                    )

            # Fix description if empty or looks like a room name
            desc = (item.get("description") or "").strip()
            room_keywords = ["living room", "kitchen", "bedroom", "bathroom",
                             "dining", "passage", "foyer", "store", "entrance"]
            if not desc or any(rk in desc.lower() for rk in room_keywords):
                item["description"] = default_item.get("description", item.get("description", ""))
                logger.info(
                    f"Fallback: item {item_no} description set to default"
                )

            # Fix confidence if zero or missing
            try:
                conf = float(item.get("confidence", 0) or 0)
            except (TypeError, ValueError):
                conf = 0
            if conf <= 0:
                item["confidence"] = default_item.get(
                    "confidence", get_default_confidence()
                )

    return data


class BoQAIGenerator:

    def __init__(self):
        provider = getattr(settings, "AI_PROVIDER", "openai")

        if provider == "groq":
            api_key = getattr(settings, "GROQ_API_KEY", "")
            if not api_key:
                raise RuntimeError(
                    "AI_PROVIDER is 'groq' but GROQ_API_KEY is not set. "
                    "Get a free key at https://console.groq.com/ or set "
                    "AI_PROVIDER=openai."
                )
            self.client = OpenAI(
                base_url=getattr(
                    settings, "GROQ_BASE_URL", "https://api.groq.com/openai/v1"
                ),
                api_key=api_key,
            )
            self.model = getattr(settings, "GROQ_MODEL", "llama-3.1-8b-instant")
        else:
            api_key = getattr(settings, "OPENAI_API_KEY", "")
            if not api_key:
                raise RuntimeError(
                    "OPENAI_API_KEY is not set. Set AI_PROVIDER=groq with a "
                    "Groq key, or provide OPENAI_API_KEY."
                )
            self.client = OpenAI(api_key=api_key)
            self.model = getattr(settings, "OPENAI_MODEL", "gpt-4.1")

        # Load default measurement context for fallback
        self.default_lookup = _build_default_lookup(get_default_boq_items())
        self.currency_symbol = get_currency_symbol()
        self.currency_code = get_currency_code()
        self.default_locations = get_default_locations()
        self.default_location = get_default_location()
        if self.default_lookup:
            logger.info(
                f"Loaded {len(self.default_lookup)} default BoQ items for fallback"
            )
        logger.info(
            f"Currency: {self.currency_symbol} ({self.currency_code}), "
            f"Default location: {self.default_location}"
        )

    def generate(self, text: str):

        SYSTEM_PROMPT = f"""
You are an expert Quantity Surveyor working in Nigeria.

Your task is to convert construction documents into a structured Bill of Quantities (BoQ) organized by TRADE SECTIONS, not by rooms.

Return ONLY valid JSON.
Do not include markdown.
Do not include explanations.
Do not wrap the JSON in code fences.

The JSON MUST follow exactly this schema:

{{
    "sections":[
        {{
            "name":"A. Preliminaries",
            "items":[
                {{
                    "item_no":"A.1",
                    "description":"Mobilization and demobilization of plant and equipment",
                    "unit":"item",
                    "quantity":1,
                    "rate":500000,
                    "confidence":0.8
                }}
            ]
        }}
    ]
}}

TRADE SECTIONS (use these section names, organized by trade):
- A. Preliminaries (mobilization, site setup, scaffolding, insurance)
- B. Excavation & Earthworks (trench excavation, backfilling, disposal, compaction)
- C. Concrete Works (blinding, structural concrete, formwork, reinforcement)
- D. Masonry Works (blockwork, plastering, rendering, pointing)
- E. Roofing Works (roof structure, roofing sheets/tiles, gutters, downpipes)
- F. Flooring Works (floor screed, floor tiles, skirting)
- G. Joinery Works (doors, windows, cabinets, wardrobes)
- H. Plumbing & Drainage (water supply, drainage, sanitary ware, septic tank)
- I. Electrical Works (wiring, switches, sockets, lighting, distribution board)
- J. Painting & Decorating (undercoat, gloss, emulsion, exterior paint)
- K. External Works (paving, fencing, landscaping, driveway)

ITEM RULES:
- Group items under the appropriate TRADE SECTION, not by room name
- Each section should have a letter prefix (A, B, C, etc.) followed by a period
- Item numbers should follow the format: SectionLetter.ItemNumber (e.g., C.1, C.2, C.3)
- Description should describe the WORK TRADE with materials specification (e.g., "Excavation for foundation trenches (footings), average depth 1.0m, width 0.69m", "Concrete blinding 50mm thick under floor slab, mix ratio 1:3:6 cement:sand:stones")
- Do NOT use room names as descriptions (e.g., do NOT write "Living Room" or "Kitchen")
- Instead write trade descriptions with specifications (e.g., "Floor screeding 50mm thick - Living Room", "Wall tiles 400x400mm - Kitchen", "Concrete strip footing 450x300mm, mix 1:2:4")
- Include material specifications where relevant: concrete mix ratios, excavation depth, blockwork thickness, plastering coats, paint coats, etc.
- All rates must be in Nigerian Naira (₦). Use realistic Nigerian market rates.
- Default locations: Kaduna, Abuja, Kano, Lagos, Port-Harcourt

EXTRACTION RULES:
- Extract REAL quantities and rates from the document text. Do NOT use zeros.
- If a quantity is not explicitly stated, estimate it from dimensions shown in the document.
- If a rate is not available, use your construction cost knowledge to provide a realistic Nigerian market rate in Naira.
- The quantity must be greater than 0 for every item.
- Use standard construction units like "sq m", "sq ft", "m", "m3", "kg", "item", "no", "lm".
- Confidence should reflect how certain you are about the extracted values (0.0 to 1.0).
"""

        try:

            # Use chat.completions (supported by both OpenAI and Groq).
            # Groq does not support the newer /responses endpoint.
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": text,
                    },
                ],
            )

            content = response.choices[0].message.content
            logger.info("AI response:")
            logger.info(content)

        except Exception as exc:

            raise RuntimeError(
                f"AI request failed: {exc}"
            ) from exc

        try:

            data = json.loads(content)

        except json.JSONDecodeError as exc:

            raise ValueError(
                "AI returned invalid JSON."
            ) from exc

        if "sections" not in data:

            raise ValueError(
                "AI response missing 'sections'."
            )

        # Apply fallback defaults for any items with zero/missing values
        data = _apply_defaults(data, self.default_lookup)

        return data
