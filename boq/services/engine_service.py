import sys
import os

# Get absolute path to /home/vboxcasi
CURRENT_DIR = os.path.dirname(__file__)
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../../../"))

# Add /home/vboxcasi to Python path
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Now this will work
from qs_ai_project.main import generate_boq_from_pdfs

def run_boq_generation(project):
    pdf_paths = [doc.file.path for doc in project.documents.all()]

    output_path = generate_boq_from_pdfs(
        pdf_files=pdf_paths,
        location=project.organization.name
    )

    return output_path


