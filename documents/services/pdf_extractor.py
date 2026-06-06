from django.core.files.storage import default_storage
import fitz
import tempfile
import logging

logger = logging.getLogger(__name__)

class PDFExtractorService:

    @staticmethod
    def extract_text(uploaded_file):

        with tempfile.NamedTemporaryFile(
            delete=False
        ) as tmp:

            for chunk in uploaded_file.chunks():
                tmp.write(chunk)

            tmp_path = tmp.name

        pdf = fitz.open(tmp_path)

        text = ""

        for page in pdf:
            text += page.get_text()

        pdf.close()

        return text