# documents/services/pdf_extractor.py

import fitz
import logging

logger = logging.getLogger(__name__)


class PDFExtractorService:

    @staticmethod
    def extract_text(file_field):

        file_field.open("rb")

        pdf_bytes = file_field.read()

        pdf = fitz.open(
            stream=pdf_bytes,
            filetype="pdf"
        )

        try:

            text = ""

            for page in pdf:
                text += page.get_text()

            return text

        finally:

            pdf.close()

            file_field.close()