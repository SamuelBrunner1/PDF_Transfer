from PIL import Image
import pytesseract
import fitz  # PyMuPDF

# Pfad zur Tesseract-Installation (anpassen, falls anders installiert)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def ocr_from_pdf(file_path):
    text = ""
    doc = fitz.open(file_path)
    for page in doc:
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        text += pytesseract.image_to_string(img, lang="deu")  # OCR in Deutsch
    return text
