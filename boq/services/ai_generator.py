# boq/services/ai_generator.py

import json
import logging

from openai import OpenAI
from django.conf import settings

logger = logging.getLogger(__name__)


class BoQAIGenerator:

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY
        )

    def generate(self, text: str):

        SYSTEM_PROMPT = """
You are an expert Quantity Surveyor.

Your task is to convert construction documents into a structured Bill of Quantities.

Return ONLY valid JSON.

Do not include markdown.

Do not include explanations.

Do not wrap the JSON in code fences.

The JSON MUST follow exactly this schema:

{
    "sections":[
        {
            "name":"",
            "items":[
                {
                    "item_no":"",
                    "description":"",
                    "unit":"",
                    "quantity":0,
                    "rate":0,
                    "confidence":0.0
                }
            ]
        }
    ]
}
"""

        try:

            response = self.client.responses.create(
                model=settings.OPENAI_MODEL,
                input=[
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

            logger.info("OpenAI response:")
            logger.info(response.output_text)

        except Exception as exc:

            raise RuntimeError(
                f"OpenAI request failed: {exc}"
            ) from exc

        try:

            data = json.loads(
                response.output_text
            )

        except json.JSONDecodeError as exc:

            raise ValueError(
                "AI returned invalid JSON."
            ) from exc

        if "sections" not in data:

            raise ValueError(
                "AI response missing 'sections'."
            )

        return data       