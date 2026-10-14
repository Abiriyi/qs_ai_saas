# parse_section.py
import re
import pdfplumber

DEFAULT_CEILING_HEIGHT_M = 3.3
DEFAULT_FOUNDATION_DEPTH_M = 1.0
DEFAULT_SLAB_THICKNESS_M = 0.15


def parse_section(pdf_path, verbose=False):
    """
    Parse building section PDF for key dimensional data:
      - Floor-to-floor height (for ceiling finishes, walls, etc.)
      - Foundation depth
      - Slab thickness

    Returns: list of BoQ-style entries (for Substructure + Finishes)
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = "\n".join([page.extract_text() or "" for page in pdf.pages])
    except Exception as e:
        print(f"⚠️ Could not read {pdf_path}: {e}")
        return []

    boq_entries = []

    # --- Detect ceiling height ---
    height_matches = re.findall(r"(\d+(?:\.\d+)?)\s*m", full_text)
    ceiling_height = DEFAULT_CEILING_HEIGHT_M
    if height_matches:
        ceiling_height = max(map(float, height_matches))
    if verbose:
        print(f"🧱 Ceiling height detected: {ceiling_height:.2f} m")

    boq_entries.append({
        "Room": "ALL",
        "Element": "Ceiling Finish",
        "Description": f"Ceiling finish at approx. {ceiling_height:.2f} m high",
        "Unit": "m²",
        "Quantity": 0,
        "WorkSection": "Finishes"
    })

    # --- Detect foundation depth ---
    foundation_depth = DEFAULT_FOUNDATION_DEPTH_M
    if "foundation" in full_text.lower():
        m = re.search(r"(\d+(?:\.\d+)?)\s*m\s*deep", full_text.lower())
        if m:
            foundation_depth = float(m.group(1))
    if verbose:
        print(f"🧱 Foundation depth detected: {foundation_depth:.2f} m")

    boq_entries.append({
        "Room": "ALL",
        "Element": "Foundations",
        "Description": f"Mass concrete foundations {foundation_depth:.2f} m deep",
        "Unit": "m³",
        "Quantity": 0,
        "WorkSection": "Substructure Works"
    })

    # --- Detect slab thickness ---
    slab_thickness = DEFAULT_SLAB_THICKNESS_M
    m = re.search(r"(\d+)\s*mm\s*(?:thick)?\s*(?:slab|floor)", full_text.lower())
    if m:
        slab_thickness = int(m.group(1)) / 1000.0
    if verbose:
        print(f"🧱 Slab thickness detected: {slab_thickness:.3f} m")

    boq_entries.append({
        "Room": "ALL",
        "Element": "Ground Floor Slab",
        "Description": f"Reinforced concrete ground floor slab {slab_thickness:.3f} m thick",
        "Unit": "m²",
        "Quantity": 0,
        "WorkSection": "Substructure Works"
    })

    # Optional: add DPC / wall up to DPC
    boq_entries.append({
        "Room": "ALL",
        "Element": "Damp Proof Course",
        "Description": "DPC layer between foundation and wall base",
        "Unit": "m",
        "Quantity": 0,
        "WorkSection": "Substructure Works"
    })

    return boq_entries

