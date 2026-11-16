#!/usr/bin/env python
"""Extract descriptions from boq_template.csv to enrich measurement_context.yaml"""

import csv
from collections import defaultdict

CSV_PATH = 'notes/boq_template.csv'

# Map BESMM4 section names to our trade-based sections
SECTION_MAP = {
    'DEMOLITIONS': 'B. Excavation & Earthworks',
    'ALTERATIONS, REPAIRS AND CONSERVATION': 'D. Masonry Works',
    'OFF-SITE MANUFACTURED MATERIALS, COMPONENTS OR BUILDINGS': 'C. Concrete Works',
    'CRIB WALLS, GABIONS & REINFORCED EARTH': 'B. Excavation & Earthworks',
    'MASONRY': 'D. Masonry Works',
    'STRUCTURAL STEELWORK': 'C. Concrete Works',
    'WINDOWS, SCREENS & LIGHTS': 'G. Joinery Works',
    'DOORS, SHUTTERS AND HATCHES': 'G. Joinery Works',
    'STAIRS, WALKWAYS AND BALUSTRADES': 'G. Joinery Works',
    'FLOOR, WALL, CEILING & ROOF FINISHINGS': 'F. Flooring Works',
    'INSULATION, FIRE STOPPING & FIRE PROTECTION': 'E. Roofing Works',
    'FURNITURE, FITTINGS AND EQUIPMENT': 'J. Painting & Decorating',
    'BUILDERS WORK IN CONNECTION WITH MECHANICAL, ELECTRICAL & TRANSPORTATION INSTALLATIONS': 'I. Electrical Works',
}

# Skip terms that are not actual item descriptions
SKIP_TERMS = [
    'SECTION PREAMBLES', 'SECTION PREAMBL', 'DRAWINGS THAT MUST',
    'MANDATORY INFOMATION', 'MADATORY INFOMATION', 'MINIMUM INFORMATION',
    'COMPONENT', 'MANDATORY INFORMATION', 'OFF-SITE MANUFACTURED',
    'OFF-SITE MANUFACTURED MATERIALS', 'COMPONENTS OR BUILDINGS',
]

with open(CSV_PATH, 'r') as f:
    reader = csv.reader(f)
    rows = list(reader)

items_by_section = defaultdict(list)
current_section = None

for row in rows:
    if len(row) < 2:
        continue
    
    col0 = row[0].strip() if row[0] else ''
    col1 = row[1].strip() if row[1] else ''
    
    # Detect section header: col0 empty, col1 has section name
    if not col0 and col1:
        for known_section in SECTION_MAP.keys():
            if known_section.upper() in col1.upper():
                current_section = col1
                break
    
    # Extract items: rows with item numbers (contain dots) and descriptions in col1
    if col0 and '.' in col0 and col1 and len(col1) > 5:
        # Skip sub-section headers
        if any(term in col1.upper() for term in SKIP_TERMS):
            continue
        if len(col1) < 10:
            continue
        items_by_section[current_section or 'Unknown'].append({
            'item_no': col0,
            'description': col1,
        })

# Print summary
print(f"Total sections found: {len(items_by_section)}")
for section, items in sorted(items_by_section.items()):
    mapped = SECTION_MAP.get(section, 'UNMAPPED')
    print(f"\n=== {section} -> {mapped} ({len(items)} items) ===")
    for item in items[:15]:
        print(f"  {item['item_no']}: {item['description'][:120]}")
    if len(items) > 15:
        print(f"  ... ({len(items)} total)")
