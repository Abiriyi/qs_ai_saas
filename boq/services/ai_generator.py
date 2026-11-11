# boq/services/ai_generator.py

import json
import logging

from openai import OpenAI
from django.conf import settings

logger = logging.getLogger(__name__)


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

    def generate(self, text: str):

        SYSTEM_PROMPT = """
You are an expert Quantity Surveyor.

Your task is to convert construction documents into a structured Bill of Quantities (BoQ) organized by TRADE SECTIONS, not by rooms.

Return ONLY valid JSON.
Do not include markdown.
Do not include explanations.
Do not wrap the JSON in code fences.

The JSON MUST follow exactly this schema:

{
    "sections":[
        {
            "name":"A. Preliminaries",
            "items":[
                {
                    "item_no":"1.1",
                    "description":"Mobilization and demobilization",
                    "unit":"item",
                    "quantity":1,
                    "rate":0,
                    "confidence":0.0
                }
            ]
        }
    ]
}

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
- Description should describe the WORK TRADE (e.g., "Excavation for foundation trenches", "Concrete blinding 50mm thick", "Floor tiles 400x400mm")
- Do NOT use room names as descriptions (e.g., do NOT write "Living Room" or "Kitchen")
- Instead write trade descriptions (e.g., "Floor screeding - Living Room", "Wall tiles - Kitchen")

EXTRACTION RULES:
- Extract REAL quantities and rates from the document text. Do NOT use zeros.
- If a quantity is not explicitly stated, estimate it from dimensions shown in the document.
- If a rate is not available, use your construction cost knowledge to provide a realistic market rate.
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

        return data
