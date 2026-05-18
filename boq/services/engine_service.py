import sys
import os
from django.core.cache import cache
from core.cache import tenant_cache_key

# Get absolute path to /home/vboxcasi
CURRENT_DIR = os.path.dirname(__file__)
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../../../"))

# Add /home/vboxcasi to Python path
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Now this will work
from qs_ai_project.main import generate_boq_from_pdfs

def run_boq_generation(project):

    cache_key = tenant_cache_key(
        f"boq_engine:{project.id}"
    )

    cached = cache.get(cache_key)

    if cached:
        return cached

    data = expensive_pdf_ai_pipeline(project)

    cache.set(
        cache_key,
        data,
        timeout=3600
    )

    return data


