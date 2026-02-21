# context_inference.py

def suggest_context(parsed_drawings):
    suggestions = {}

    if parsed_drawings.get("scale"):
        suggestions["scale"] = {
            "value": parsed_drawings["scale"],
            "confidence": 0.7,
            "source": "ai"
        }

    if parsed_drawings.get("section_height"):
        suggestions["storey_height"] = {
            "value": parsed_drawings["section_height"],
            "confidence": 0.65,
            "source": "ai"
        }

    return suggestions
