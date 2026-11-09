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
