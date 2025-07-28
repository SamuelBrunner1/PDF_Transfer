import streamlit as st
import pandas as pd
import io
import re

from pdf_reader import extract_text_from_pdf
from ocr_reader import ocr_from_pdf
from patterns import FIELD_PATTERNS
from nlp_extractor import extract_named_entities  # Falls du NLP nutzt

# CSS laden
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("📄 PDF-Rechnungsanalysator (Dark Mode)")

# Session-State
if "data" not in st.session_state:
    st.session_state["data"] = []
if "custom_fields" not in st.session_state:
    st.session_state["custom_fields"] = []

# --- Auswahl der Standard-Felder ---
st.header("🔍 Wähle Felder zur Extraktion")
selected_fields = st.multiselect(
    "Standard-Felder auswählen:",
    options=list(FIELD_PATTERNS.keys()),
    default=["Rechnungsnummer", "Datum", "Betrag (€)"]
)

# --- Eigene Felder ---
st.header("➕ Eigene Felder hinzufügen")
with st.form("custom_field_form"):
    field_name = st.text_input("Feldname (z. B. Verwendungszweck)")
    submitted = st.form_submit_button("Feld hinzufügen")
    if submitted and field_name:
        if field_name in FIELD_PATTERNS:
            if field_name not in st.session_state["custom_fields"]:
                st.session_state["custom_fields"].append(field_name)
            st.success(f"Feld '{field_name}' hinzugefügt!")
        else:
            st.error("Unbekannter Feldname. Bitte wähle aus den unterstützten Feldern.")

# --- Aktive Extraktionsfelder ---
if selected_fields or st.session_state["custom_fields"]:
    st.subheader("✅ Aktive Extraktionsfelder")
    for field in selected_fields + st.session_state["custom_fields"]:
        pattern = FIELD_PATTERNS.get(field, "-/-")
        st.write(f"✔ {field} → `{pattern}`")

# --- PDF-Upload ---
st.header("📂 PDF-Dateien hochladen und analysieren")
pdf_files = st.file_uploader(
    "Lade eine oder mehrere PDFs hoch", type="pdf", accept_multiple_files=True
)

if pdf_files and st.button("Analyse starten"):
    st.session_state["data"] = []  # ✅ Session-Daten zurücksetzen

    for pdf_file in pdf_files:
        pdf_bytes = pdf_file.read()
        text = extract_text_from_pdf(io.BytesIO(pdf_bytes))

        if not text.strip():
            st.warning(f"OCR wird verwendet für {pdf_file.name}...")
            text = ocr_from_pdf(io.BytesIO(pdf_bytes))

        st.subheader(f"📑 {pdf_file.name}")
        st.text(text)

        # --- Parsing ---
        parsed_data = {}
        for field in selected_fields + st.session_state["custom_fields"]:
            pattern = FIELD_PATTERNS.get(field)
            if pattern:
                match = re.search(pattern, text)
                parsed_data[field] = match.group(1) if match else "Nicht gefunden"
            else:
                parsed_data[field] = "Nicht definiert"

        # ✅ Nur speichern, wenn sinnvolle Daten vorhanden sind
        if any(val != "Nicht gefunden" for val in parsed_data.values()):
            st.session_state["data"].append(parsed_data)
            st.success(f"Erfolgreich extrahiert aus: {pdf_file.name}")
        else:
            st.warning(f"Keine passenden Daten in {pdf_file.name} gefunden.")

        st.json(parsed_data)

# --- Excel-Download ---
if st.session_state["data"]:
    st.header("📥 Ergebnisse als Excel-Datei")
    df = pd.DataFrame(st.session_state["data"])
    st.dataframe(df)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)

    st.download_button(
        label="📥 Excel-Datei herunterladen",
        data=buffer,
        file_name="extraktion.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
