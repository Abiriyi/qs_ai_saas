# pdf_parser.py
import pdfplumber
import re
from math import hypot

# Patterns
DIM_MM_PATTERN = re.compile(r"(\d{3,5})\s*[xX]\s*(\d{3,5})")           # e.g. 6000x4500 (mm)
DIM_M_PATTERN  = re.compile(r"(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)\s*m")  # e.g. 6.0 x 4.5 m
TAG_PATTERN    = re.compile(r"\b([WD]\d{1,4})\b", re.I)                 # W1, D2
HEIGHT_PATTERN = re.compile(r"(height|floor to ceiling|ceiling height)[:\s]*([\d\.]+)\s*(mm|m)?", re.I)

def _safe_get_center(w):
    try:
        x = (float(w.get("x0", 0)) + float(w.get("x1", 0))) / 2.0
        y = (float(w.get("top", 0)) + float(w.get("bottom", 0))) / 2.0
        return x, y
    except Exception:
        return 0.0, 0.0

def extract_pdf_text(pdf_path):
    """
    Parse a drawing PDF and return:
      {
        "rooms": [{"Room": name, "x": x, "y": y, "Page": page}],
        "heights": [{"Length": l, "Width": w, "Area": a, "Page": page} | {"Height": h, "Page": page}],
        "openings": [{"tag": "W1", "count":1, "width_m": 1.2, "height_m":1.5, "x":x, "y":y, "page":page}]
      }

    This uses token geometry to cluster likely room labels and to pick up dimension tokens.
    """
    rooms = []
    heights = []
    openings = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            try:
                words = page.extract_words(use_text_flow=True) or []
            except Exception:
                # fallback simple extraction
                words = page.extract_words() or []

            page_text = page.extract_text() or ""

            # 1) Openings: detect tags (W1, D2) among tokens and pick nearest size if any
            for w in words:
                txt = (w.get("text") or "").strip()
                if not txt:
                    continue
                mtag = TAG_PATTERN.match(txt)
                if mtag:
                    tag = mtag.group(1).upper()
                    cx, cy = _safe_get_center(w)

                    # search for a mm-size pattern in page text (first match)
                    mm = DIM_MM_PATTERN.search(page_text)
                    if mm:
                        try:
                            width_m = int(mm.group(1)) / 1000.0
                            height_m = int(mm.group(2)) / 1000.0
                        except Exception:
                            width_m = height_m = None
                    else:
                        width_m = height_m = None

                    openings.append({
                        "tag": tag,
                        "count": 1,
                        "width_m": width_m,
                        "height_m": height_m,
                        "x": cx,
                        "y": cy,
                        "page": page_no
                    })

            # 2) Room label clustering: take alphabetic tokens and cluster by proximity
            alpha_tokens = [w for w in words if re.match(r"^[A-Za-z]", (w.get("text") or ""))]
            clusters = []
            for token in alpha_tokens:
                tx = token.get("x0", 0)
                ty = token.get("top", 0)
                placed = False
                for c in clusters:
                    # use Euclidean distance threshold (tuned for typical drawing token spacing)
                    if hypot(c["cx"] - tx, c["cy"] - ty) < 80:   # <- tunable
                        c["words"].append(token)
                        # recompute centroid
                        c["cx"] = sum(float(w.get("x0", 0)) for w in c["words"]) / len(c["words"])
                        c["cy"] = sum(float(w.get("top", 0)) for w in c["words"]) / len(c["words"])
                        placed = True
                        break
                if not placed:
                    clusters.append({"words": [token], "cx": tx, "cy": ty})

            # build room labels from clusters (heuristic keywords)
            ROOM_KEYWORDS = r"\b(room|kitchen|bed|living|dining|store|wc|bath|toilet|hall|lounge|foyer|bedroom|master)\b"
            for c in clusters:
                label = " ".join(w.get("text", "") for w in c["words"]).strip()
                if len(label) < 3:
                    continue
                if re.search(ROOM_KEYWORDS, label, re.I):
                    rooms.append({
                        "Room": label,
                        "x": c["cx"],
                        "y": c["cy"],
                        "Page": page_no
                    })

            # 3) Dimension tokens (mm and m)
            for mm in DIM_MM_PATTERN.finditer(page_text):
                try:
                    l = int(mm.group(1)) / 1000.0
                    wv = int(mm.group(2)) / 1000.0
                    heights.append({"Length": round(l,3), "Width": round(wv,3), "Area": round(l*wv,3), "Page": page_no})
                except Exception:
                    continue

            for mm in DIM_M_PATTERN.finditer(page_text):
                try:
                    l = float(mm.group(1))
                    wv = float(mm.group(2))
                    heights.append({"Length": round(l,3), "Width": round(wv,3), "Area": round(l*wv,3), "Page": page_no})
                except Exception:
                    continue

            # 4) Ceiling height tokens
            for hm in HEIGHT_PATTERN.finditer(page_text):
                try:
                    val = float(hm.group(2))
                    unit = hm.group(3) or "mm"
                    h_m = val/1000.0 if unit.lower().startswith("mm") else val
                    heights.append({"Height": round(h_m,3), "Page": page_no, "raw": hm.group(0)})
                except Exception:
                    continue

    # Merge openings by tag so schedule and page tags don't duplicate
    merged_openings = {}
    for op in openings:
        tag = op.get("tag")
        if not tag:
            continue
        if tag not in merged_openings:
            merged_openings[tag] = dict(op)
        else:
            merged_openings[tag]["count"] = merged_openings[tag].get("count", 1) + op.get("count", 1)
            # preserve first seen sizes if missing later
            if merged_openings[tag].get("width_m") is None and op.get("width_m"):
                merged_openings[tag]["width_m"] = op.get("width_m")
            if merged_openings[tag].get("height_m") is None and op.get("height_m"):
                merged_openings[tag]["height_m"] = op.get("height_m")

    return {
        "rooms": rooms,
        "heights": heights,
        "openings": list(merged_openings.values())
    }








