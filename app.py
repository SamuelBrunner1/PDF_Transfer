import streamlit as st
import pandas as pd
from pdf_reader import extract_text_from_pdf
from ocr_reader import ocr_from_pdf
from parser import parse_invoice
from excel_writer import write_to_excel
import io

st.title("📄 PDF-Rechnungsanalysator")

# Session-State für Excel-Daten
if "data" not in st.session_state:
    st.session_state["data"] = []

# --- PDF Upload ---
st.header("1. PDF hochladen und analysieren")
pdf_file = st.file_uploader("Wähle eine PDF-Datei", type="pdf")

if pdf_file:
    # PDF speichern im Speicher
    temp_file = "temp.pdf"
    with open(temp_file, "wb") as f:
        f.write(pdf_file.read())

    # Extrahieren
    text = extract_text_from_pdf(temp_file)
    if not text.strip():
        st.warning("Kein Text gefunden, OCR wird verwendet...")
        text = ocr_from_pdf(temp_file)

    st.subheader("Extrahierter Text:")
    st.text(text)

    data = parse_invoice(text)
    st.subheader("Geparste Daten:")
    st.json(data)

    # In Session-State speichern
    st.session_state["data"].append(data)

# --- Excel Download ---
st.header("2. Excel-Datei generieren")
if st.session_state["data"]:
    df = pd.DataFrame(st.session_state["data"])
    st.dataframe(df)

    # Excel-Datei im Speicher erstellen
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    st.download_button(
        label="📥 Excel-Datei herunterladen",
        data=buffer,
        file_name="rechnungen.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
