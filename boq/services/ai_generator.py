# boq/services/ai_generator.py

import json
from openai import OpenAI

from django.conf import settings


class BoQAIGenerator:

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY
        )

    def generate(self, text: str):

        prompt = f"""
You are an expert Quantity Surveyor.

Read the following construction document.

Produce ONLY valid JSON.

Required schema:

{{
    "sections":[
        {{
            "name":"",
            "items":[
                {{
                    "item_no":"",
                    "description":"",
                    "unit":"",
                    "quantity":0,
                    "rate":0,
                    "confidence":0.0
                }}
            ]
        }}
    ]
}}

Document:

{text}
"""

        response = self.client.responses.create(
            model="gpt-5",
            input=prompt,
        )

        return json.loads(
            response.output_text
        )