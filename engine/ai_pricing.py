# ai_pricing.py
import os
import re
import pandas as pd
from openai import OpenAI

# Initialize OpenAI client (for premium users; will safely fail if no key)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

def get_rate_from_ai(element, description, unit, location="local"):
    """
    Query GPT to suggest a unit rate for a BoQ item (if API key is available).
    """
    prompt = f"""
    You are a professional Quantity Surveyor familiar with {location} construction market rates.
    Provide a realistic unit rate for the following BoQ item:
    Element: {element}
    Description: {description}
    Unit: {unit}
    Output ONLY the number without currency symbol or extra text.
    """

    if not client.api_key:
        print("⚠️ No OpenAI API key provided. Using rate library only.")
        return None

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful QS assistant providing accurate construction unit rates."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        rate_str = response.choices[0].message.content.strip()
        rate_str = re.sub(r"[^\d.]", "", rate_str)
        return float(rate_str) if rate_str else None
    except Exception as e:
        print(f"AI pricing error: {e}")
        return None


# Cache to avoid reloading repeatedly
_RATE_LIBRARY = None
_RATE_LOCATION = None

def _load_rate_library(location="local"):
    """
    Load rate_library_<location>.csv if available,
    otherwise fallback to rate_library.csv.
    """
    global _RATE_LIBRARY, _RATE_LOCATION

    if _RATE_LOCATION == location and _RATE_LIBRARY is not None:
        return  # Already loaded

    base_path = os.getcwd()
    loc_file = os.path.join(base_path, f"rate_library_{location.lower()}.csv")
    default_file = os.path.join(base_path, "rate_library.csv")

    csv_path = loc_file if os.path.exists(loc_file) else default_file

    if not os.path.exists(csv_path):
        print(f"⚠️ No rate library found for {location}. Expected: {csv_path}")
        _RATE_LIBRARY = pd.DataFrame(columns=["Element", "Unit", "BaseRate"])
        _RATE_LOCATION = location
        return

    try:
        _RATE_LIBRARY = pd.read_csv(csv_path, comment="#").dropna(subset=["Element"])
        _RATE_LIBRARY["Element"] = _RATE_LIBRARY["Element"].str.strip().str.lower()
        _RATE_LIBRARY["Unit"] = _RATE_LIBRARY["Unit"].str.strip().str.lower()
        _RATE_LOCATION = location
        print(f"✅ Loaded rate library for {location}: {os.path.basename(csv_path)}")
    except Exception as e:
        print(f"⚠️ Error loading {csv_path}: {e}")
        _RATE_LIBRARY = pd.DataFrame(columns=["Element", "Unit", "BaseRate"])
        _RATE_LOCATION = location


def get_rate_from_library(element, description="", unit="", location="local"):
    """
    Look up a unit rate from the rate library (location-specific if available).
    """
    global _RATE_LIBRARY
    _load_rate_library(location)

    if _RATE_LIBRARY is None or _RATE_LIBRARY.empty:
        return None

    element_key = (element or "").strip().lower()
    unit_key = (unit or "").strip().lower()

    # Try exact element + unit match
    match = _RATE_LIBRARY[
        (_RATE_LIBRARY["Element"] == element_key) &
        (_RATE_LIBRARY["Unit"] == unit_key)
    ]

    # Fallback: element-only match
    if match.empty:
        match = _RATE_LIBRARY[_RATE_LIBRARY["Element"] == element_key]

    if not match.empty:
        try:
            return float(match.iloc[0]["BaseRate"])
        except ValueError:
            return None

    # Fuzzy fallback
    for _, row in _RATE_LIBRARY.iterrows():
        if element_key in row["Element"]:
            try:
                return float(row["Rate"])
            except ValueError:
                continue

    return None


if __name__ == "__main__":
    print("🔍 Testing multi-location rate lookup...\n")
    print("Kaduna - Blockwork (m²):", get_rate_from_library("Blockwork", unit="m²", location="Kaduna"))
    print("Abuja  - Painting (m²):", get_rate_from_library("Painting", unit="m²", location="Abuja"))
    print("Lagos  - Doors (No.):", get_rate_from_library("Doors", unit="No.", location="Lagos"))





    