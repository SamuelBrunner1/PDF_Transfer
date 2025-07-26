import streamlit as st
import pandas as pd
from pdf_reader import extract_text_from_pdf
from ocr_reader import ocr_from_pdf
from parser import parse_invoice
import io

# ✅ Apple-Style CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@400;500;600&display=swap');

    /* Global Background */
    html, body, [class*="css"] {
        font-family: 'SF Pro Display', sans-serif;
        background-color: #0e0e0e;  /* Dunkles Schwarz */
        color: #ffffff !important;
    }

    /* Titel Styling */
    h1 {
        font-size: 2.5rem !important;
        font-weight: 600 !important;
        color: #ffffff;
        text-align: center;
        margin-bottom: 1rem;
    }

    /* Header Styling */
    h2 {
        font-size: 1.4rem !important;
        font-weight: 500 !important;
        color: #f0f0f0;
        margin-top: 2rem;
        margin-bottom: 0.5rem;
    }

    /* Buttons Apple-Look */
    .stDownloadButton > button, .stButton > button {
        background-color: #007aff;
        color: white;
        border-radius: 12px;
        font-size: 1rem;
        font-weight: 500;
        padding: 0.8em 2em;
        border: none;
        transition: all 0.3s ease-in-out;
    }
    .stDownloadButton > button:hover, .stButton > button:hover {
        background-color: #005ecb;
    }

    /* Upload Box Styling */
    .stFileUploader {
        background-color: #1c1c1e;  /* Apple Dark Grau */
        border: 2px dashed #3a3a3c;
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        color: #ffffff;
    }

    /* DataFrame Dark Mode */
    .dataframe {
        background-color: #1c1c1e !important;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📄 PDF-Rechnungsanalysator (Dark Mode)")

# ✅ Session-State für Excel-Daten
if "data" not in st.session_state:
    st.session_state["data"] = []

# ✅ Mehrere PDFs hochladen
st.header("1. PDF-Dateien hochladen und analysieren")
pdf_files = st.file_uploader("Wähle eine oder mehrere PDF-Dateien", type="pdf", accept_multiple_files=True)

if pdf_files:
    for pdf_file in pdf_files:
        # Direkt aus Bytes arbeiten (kein lokales Speichern)
        pdf_bytes = pdf_file.read()

        # Text extrahieren
        text = extract_text_from_pdf(io.BytesIO(pdf_bytes))
        if not text.strip():
            st.warning(f"Kein Text in {pdf_file.name} gefunden, OCR wird verwendet...")
            text = ocr_from_pdf(io.BytesIO(pdf_bytes))

        st.subheader(f"Extrahierter Text aus {pdf_file.name}:")
        st.text(text)

        # Daten parsen
        data = parse_invoice(text)
        st.subheader("Geparste Daten:")
        st.json(data)

        # In Session-State speichern
        st.session_state["data"].append(data)

# ✅ Excel-Datei generieren und Download anbieten
st.header("2. Excel-Datei generieren")
if st.session_state["data"]:
    df = pd.DataFrame(st.session_state["data"])
    st.dataframe(df)

    # Excel-Datei im Speicher erstellen
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)

    st.download_button(
        label="📥 Excel-Datei herunterladen",
        data=buffer,
        file_name="rechnungen.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
