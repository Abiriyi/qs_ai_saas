import sys
import os
# ✅ Clean import (Pylance-friendly)
from qs_ai_project.main import generate_boq_from_pdfs

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
PROJECT_ROOT = BASE_DIR  # workspace root

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def run_boq_generation(project):
    pdf_paths = [doc.file.path for doc in project.documents.all()]

    output_path = generate_boq_from_pdfs(
        pdf_files=pdf_paths,
        location=project.organization.name
    )

    return output_path


