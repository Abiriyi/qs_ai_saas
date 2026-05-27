import fitz


class PDFExtractorService:

    @staticmethod
    def extract_text(file_path):

        document = fitz.open(file_path)

        extracted_text = []

        for page in document:

            extracted_text.append(
                page.get_text()
            )

        return "\n".join(extracted_text)