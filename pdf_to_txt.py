import os
from pdf_reader import extract_text_from_pdf
from ocr_reader import ocr_from_pdf

# Pfad zum PDF-Ordner
pdf_dir = r"C:\Leben\PDF_Transfer\Rechnungen\15bessereRechnungen"
txt_output_dir = r"C:\Leben\PDF_Transfer\text\15bessereRechnungen"


os.makedirs(txt_output_dir, exist_ok=True)

for filename in os.listdir(pdf_dir):
    if filename.lower().endswith(".pdf"):
        pdf_path = os.path.join(pdf_dir, filename)
        print(f"Verarbeite: {filename}")
        
        # Erst normalen Text-Extraktor probieren
        text = extract_text_from_pdf(pdf_path)
        
        # Wenn kein Text vorhanden → OCR
        if not text.strip():
            print("⚠ Kein Text gefunden – OCR wird verwendet.")
            text = ocr_from_pdf(pdf_path)
        
        # Speichern als TXT
        txt_filename = os.path.splitext(filename)[0] + ".txt"
        txt_path = os.path.join(txt_output_dir, txt_filename)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)
        
        print(f"✅ Gespeichert: {txt_path}")

print("Fertig! TXT-Dateien liegen in:", txt_output_dir)
