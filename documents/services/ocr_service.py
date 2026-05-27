import pytesseract

from PIL import Image


class OCRService:

    @staticmethod
    def extract_text_from_image(image_path):

        image = Image.open(image_path)

        return pytesseract.image_to_string(image)