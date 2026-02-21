# parse_floorplan.py
from math import hypot
from collections import defaultdict

EXCLUDE_TERMS = ["residential", "development"]

def _estimate_perimeter_from_area(area):
    if area <= 0:
        return 0.0
    # assume rectangular shape with aspect ratio ~1.5 (L = 1.5 * W)
    width = (area / 1.5) ** 0.5
    length = 1.5 * width
    return round(2 * (length + width), 2)

def build_boq_entries(parsed_data, default_height=3.0):
    """
    Convert parsed_data from pdf_parser.extract_pdf_text into BoQ entries.
    Output entries: list of dicts with keys: Room, Element, Description, Unit, Quantity
    """
    rooms_tokens = parsed_data.get("rooms", []) or []
    dims = parsed_data.get("heights", []) or []
    openings = parsed_data.get("openings", []) or []

    # Build room objects with defaults
    rooms = []
    for r in rooms_tokens:
        rooms.append({
            "Room": r.get("Room") or "Unknown",
            "x": r.get("x") or 0,
            "y": r.get("y") or 0,
            "Page": r.get("Page") or 1,
            "Area": r.get("Area") or 0.0,
            "Perimeter": r.get("Perimeter") or 0.0,
            "Height": default_height
        })

    # Attach detected dimension tokens (Area/Length/Width) to nearest room on same page
    for d in dims:
        if d.get("Area"):
            # find nearest room by vertical proximity on same page
            best = None
            best_dist = float("inf")
            for rm in rooms:
                if rm.get("Page") != d.get("Page"):
                    continue
                # use vertical distance to match dims printed near room
                dist = abs(rm.get("y", 0) - (d.get("Length", rm.get("y", 0))))
                if dist < best_dist:
                    best_dist = dist
                    best = rm
            if best:
                best["Area"] = d.get("Area")
                if not best.get("Perimeter"):
                    best["Perimeter"] = _estimate_perimeter_from_area(d.get("Area"))


        if d.get("Height"):
            # assign ceiling height to rooms on same page
            for rm in rooms:
                if rm.get("Page") == d.get("Page"):
                    rm["Height"] = d.get("Height")

    # Assign openings to nearest rooms (same page preferred)
    openings_by_room = defaultdict(list)
    for op in openings:
        # find candidate rooms on same page
        candidates = [r for r in rooms if r.get("Page") == op.get("page")]
        if not candidates:
            candidates = rooms
        if not candidates:
            continue
        # nearest by euclidean distance
        best = min(candidates, key=lambda rm: hypot((rm.get("x", 0) - op.get("x", 0)), (rm.get("y", 0) - op.get("y", 0))))
        openings_by_room[best["Room"]].append(op)

    boq_entries = []

    for room in rooms:
        name = room.get("Room")
        if any(t in name.lower() for t in EXCLUDE_TERMS):
            continue

        area = float(room.get("Area") or 0)
        perimeter = float(room.get("Perimeter") or 0)
        height = float(room.get("Height") or default_height)

        # if only perimeter present, estimate area
        if area == 0 and perimeter > 0:
            side = perimeter / 4.0
            area = round(side * side, 2)

        # Floor finish
        if area > 0:
            boq_entries.append({
                "Room": name,
                "Element": "Floor Finish",
                "Description": f"Floor finish (tiles) to {name}",
                "Unit": "m2",
                "Quantity": round(area, 2)
            })

        # Wall finishes (net of openings)
        opening_area = 0.0
        for op in openings_by_room.get(name, []):
            w = op.get("width_m") or 0
            h = op.get("height_m") or 0
            cnt = op.get("count") or 1
            if w and h:
                opening_area += w * h * cnt
            else:
                # sensible defaults: windows ~1.2x1.5, doors ~0.9x2.1
                if (op.get("tag") or "").upper().startswith("W"):
                    opening_area += 1.2 * 1.5 * cnt
                else:
                    opening_area += 0.9 * 2.1 * cnt

        wall_area_gross = perimeter * height if perimeter and height else 0
        wall_area_net = max(round(wall_area_gross - opening_area, 2), 0)
        if wall_area_net > 0:
            boq_entries.append({
                "Room": name,
                "Element": "Wall Finish",
                "Description": f"Wall finish (plaster/paint) to walls in {name} (net of openings)",
                "Unit": "m2",
                "Quantity": wall_area_net
            })

        # Skirting
        if perimeter > 0:
            boq_entries.append({
                "Room": name,
                "Element": "Skirting",
                "Description": f"Skirting to {name}",
                "Unit": "m",
                "Quantity": round(perimeter, 2)
            })

        # Ceiling finishes
        if area > 0:
            boq_entries.append({
                "Room": name,
                "Element": "Ceiling Finish",
                "Description": f"Ceiling finish to {name}",
                "Unit": "m2",
                "Quantity": round(area, 2)
            })

        # Windows & Doors counted
        for op in openings_by_room.get(name, []):
            tag = op.get("tag", "")
            cnt = op.get("count") or 1
            typ = "Windows" if tag.upper().startswith("W") else "Doors" if tag.upper().startswith("D") else "Openings"
            boq_entries.append({
                "Room": name,
                "Element": typ,
                "Description": f"{tag} in {name} ({cnt} no.)",
                "Unit": "No.",
                "Quantity": cnt
            })

        # Heuristic substructure: small footing volume based on perimeter
        if perimeter > 0:
            # assume strip footings width 0.6m and depth 0.5m distributed half to this room
            footing_vol = round(perimeter * 0.6 * 0.5 / 2.0, 3)
            if footing_vol > 0:
                boq_entries.append({
                    "Room": name,
                    "Element": "Excavation",
                    "Description": f"Excavation for strip footings adjacent to {name}",
                    "Unit": "m3",
                    "Quantity": footing_vol
                })

    return boq_entries





