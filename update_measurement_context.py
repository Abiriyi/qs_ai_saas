#!/usr/bin/env python3
"""Merge CSV descriptions into measurement_context.yaml"""

import csv
import yaml
from collections import defaultdict

CSV_PATH = 'notes/boq_template.csv'
YAML_PATH = '/home/ubuntu/projects/qs_ai_saas/qs_ai_project/measurement_context.yaml'

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

# Read CSV
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
                current_section = known_section
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

# Read existing YAML
with open(YAML_PATH, 'r') as f:
    context = yaml.safe_load(f)

# Build existing item numbers per section to avoid duplicates
existing_items = {}
for section_item in context.get('boq_items', []):
    section_name = section_item['section']
    existing_items.setdefault(section_name, set())
    for item in section_item.get('items', []):
        existing_items[section_name].add(item['item_no'])

# Add new items from CSV (limit to 20 per section to keep YAML manageable)
for section, items in sorted(items_by_section.items()):
    mapped = SECTION_MAP.get(section)
    if mapped is None:
        continue
    
    # Find or create section
    existing_section = None
    for s in context['boq_items']:
        if s['section'] == mapped:
            existing_section = s
            break
    
    if existing_section is None:
        existing_section = {'section': mapped, 'items': []}
        context['boq_items'].append(existing_section)
    
    existing_nums = existing_items.get(mapped, set())
    added = 0
    for item in items:
        if item['item_no'] not in existing_nums and added < 20:
            existing_section['items'].append({
                'item_no': item['item_no'],
                'description': item['description'],
                'unit': 'item',
                'quantity': 1,
                'rate': 0.00,
            })
            existing_nums.add(item['item_no'])
            added += 1

# Write back
with open(YAML_PATH, 'w') as f:
    yaml.dump(context, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

print(f"\nUpdated {YAML_PATH}")
print(f"Total sections: {len(context['boq_items'])}")
for s in context['boq_items']:
    print(f"  {s['section']}: {len(s['items'])} items")