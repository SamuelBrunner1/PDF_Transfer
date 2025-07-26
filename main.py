from pdf_reader import extract_text_from_pdf
from parser import parse_invoice
from excel_writer import write_to_excel
from ocr_reader import ocr_from_pdf

file_path = "Rechnung_001.pdf"

# 1. Versuche normalen PDF-Text
text = extract_text_from_pdf(file_path)

# 2. Wenn kein Text gefunden → OCR verwenden
if not text.strip():
    print("⚠ Kein Text gefunden. Verwende OCR...")
    text = ocr_from_pdf(file_path)

print("Extrahierter Text:\n", text)
data = parse_invoice(text)
print("Geparste Daten:\n", data)
write_to_excel(data)
print("✅ Erfolgreich in Excel gespeichert!")
