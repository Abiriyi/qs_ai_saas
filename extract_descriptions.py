#!/usr/bin/env python3
"""Extract descriptions from boq_template.csv to enrich measurement_context.yaml"""

import csv
from collections import defaultdict

CSV_PATH = 'notes/boq_template.csv'

SECTION_MAP = {
    'DEMOLITIONS': 'B. Excavation & Earthworks',
    'ALTERATIONS, REPAIRS AND CONSERVATION': 'D. Masonry Works',
    'OFF-SITE MANUFACTURED MATERIALS': 'C. Concrete Works',
    'CRIB WALLS': 'B. Excavation & Earthworks',
    'MASONRY': 'D. Masonry Works',
    'STRUCTURAL STEELWORK': 'C. Concrete Works',
    'WINDOWS, SCREENS & LIGHTS': 'G. Joinery Works',
    'DOORS, SHUTTERS AND HATCHES': 'G. Joinery Works',
    'STAIRS, WALKWAYS AND BALUSTRADES': 'G. Joinery Works',
    'FLOOR, WALL, CEILING & ROOF FINISHINGS': 'F. Flooring Works',
    'INSULATION, FIRE STOPPING & FIRE PROTECTION': 'E. Roofing Works',
    'FURNITURE, FITTINGS AND EQUIPMENT': 'J. Painting & Decorating',
    'BUILDERS WORK IN CONNECTION WITH MECHANICAL': 'I. Electrical Works',
}

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
    if not col0 and col1:
        for known_section in SECTION_MAP.keys():
            if known_section.upper() in col1.upper():
                current_section = col1
                break
    if col0 and '.' in col0 and col1 and len(col1) > 5:
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
    mapped = SECTION_MAP.get(section, 'Unknown')
    print(f"\n### {section} -> {mapped} ({len(items)} items)")
    for item in items[:30]:
        desc = item['description'].replace('"', '\\"')
        print(f'- item_no: "{item["item_no"]}"')
        print(f'  description: "{desc}"')
        print(f'  unit: "item"')
        print(f'  quantity: 1')
        print(f'  rate: 0.00')
    if len(items) > 30:
        print(f'  # ... ({len(items) - 30} more items)')