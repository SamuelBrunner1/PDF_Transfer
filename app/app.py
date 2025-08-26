import streamlit as st
import pandas as pd
import io
import re
import spacy
import datetime
import sys, os

# --- Pfad-Setup (damit utils/ importierbar ist) ---
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# --- Utils laden ---
from utils.pdf_reader import extract_text_from_pdf
from utils.ocr_reader import ocr_from_pdf
from utils.patterns import FIELD_PATTERNS

# Optional: Validierung
try:
    from validation import validate_fields
except Exception:
    validate_fields = None

# --- NER-Modell laden (relativ: models/ner_model) ---
try:
    nlp = spacy.load("models/ner_model")
except Exception:
    nlp = None
    st.error("❌ Konnte das NER-Modell nicht laden. Stelle sicher, dass 'models/ner_model' existiert.")

# --- Optionales CSS ---
try:
    with open("style.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

st.title("📄 PDF-Rechnungsanalysator")

# --- Session-State init ---
if "data" not in st.session_state:
    st.session_state["data"] = []
if "used_quota" not in st.session_state:
    st.session_state["used_quota"] = 0

# ---------------------- Normalisierung & Mapping ----------------------
def normalize_amount(s: str) -> str:
    """ 'EUR 2.160,00' -> '2160.00' """
    if not s:
        return s
    s = s.strip().replace("€", "").replace("EUR", "").replace("eur", "")
    s = s.replace("\u00A0", " ").replace(" ", "")
    s = s.replace(".", "").replace(",", ".")
    m = re.search(r"[+-]?\d+(?:\.\d+)?", s)
    return m.group(0) if m else s

def normalize_date(s: str) -> str:
    """ gängige deutsche Formate auf ISO (YYYY-MM-DD) """
    if not s:
        return s
    s = s.strip().replace("\u00A0", " ")
    fmts = ["%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%Y.%m.%d"]
    for fmt in fmts:
        try:
            return datetime.datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    m = re.search(r"\b(\d{1,2}\.\d{1,2}\.\d{2,4})\b", s)
    if m:
        return normalize_date(m.group(1))
    return s

# Mapping: NER-Label -> Spaltenname
NER_TO_FIELD = {
    "RECHNUNGSNUMMER": "Rechnungsnummer",
    "RECHNUNGSDATUM": "Datum",
    "LEISTUNGSDATUM": "Leistungsdatum",
    "ZAHLUNGSZIEL": "Zahlungsziel",
    "LEISTUNG": "Leistung",
    "ZWISCHENSUMME_NETTO": "Zwischensumme",
    "UST_BETRAG": "USt_Betrag",
    "UST_ID": "UID",
    "STEUERSATZ": "Steuersatz",
    "BRUTTOBETRAG": "Betrag (€)",
    "WÄHRUNG": "Währung",
    "IBAN": "IBAN",
    "BIC": "BIC",
    "FIRMENNAME": "Firmenname",
    "ADRESSE": "Adresse",
    "EMAIL": "E-Mail",
    "RECHNUNGSEMPFÄNGER": "Rechnungsempfänger",
    "KUNDENNUMMER": "Kundennummer",
    "BESTELLNUMMER": "Bestellnummer",
}

AMOUNT_FIELDS = {"Betrag (€)", "Zwischensumme", "USt_Betrag"}
DATE_FIELDS   = {"Datum", "Leistungsdatum", "Zahlungsziel"}

# ---------------------- Felder-Auswahl ----------------------
st.header("🔍 Felder auswählen")
selected_fields = st.multiselect(
    "Wähle die Felder aus, die du extrahieren möchtest:",
    options=list(FIELD_PATTERNS.keys()),
    default=["Rechnungsnummer", "Datum", "Betrag (€)"]
)

if selected_fields:
    st.caption("Aktive Felder: " + ", ".join(f"**{f}**" for f in selected_fields))

# ---------------------- Upload & Analyse ----------------------
FREE_QUOTA = 5          # max. gratis PDFs pro Session
MAX_FILESIZE_MB = 5     # Dateigrößenlimit

def quota_left() -> int:
    return max(0, FREE_QUOTA - st.session_state["used_quota"])

st.header("📂 PDF-Dateien hochladen")
st.caption(f"Du kannst noch **{quota_left()}** von {FREE_QUOTA} Gratis-PDFs hochladen.")

pdf_files = st.file_uploader(
    "Wähle PDF-Dateien aus", type="pdf", accept_multiple_files=True, key="uploader"
)

# Sanfte Bremse auf Quota
if pdf_files and len(pdf_files) > quota_left():
    st.warning(f"Nur {quota_left()} Datei(en) erlaubt. Auswahl wurde gekürzt.")
    pdf_files = pdf_files[:quota_left()]

if pdf_files and st.button("Analyse starten", type="primary", disabled=quota_left()==0):
    processed = 0
    rows_for_table = []

    for pdf_file in pdf_files:
        pdf_bytes = pdf_file.read()

        # Dateigröße prüfen
        if len(pdf_bytes) > MAX_FILESIZE_MB * 1024 * 1024:
            st.warning(f"{pdf_file.name}: Datei > {MAX_FILESIZE_MB} MB – übersprungen.")
            continue

        # Text extrahieren (kein Debug-Print!)
        text = extract_text_from_pdf(io.BytesIO(pdf_bytes)) or ""
        if not text.strip():
            st.info(f"OCR wird verwendet für {pdf_file.name}…")
            text = ocr_from_pdf(io.BytesIO(pdf_bytes)) or ""

        # --- NER (ohne Ausgabe) ---
        ner_values = {}
        if nlp:
            doc = nlp(text)
            for ent in doc.ents:
                fld = NER_TO_FIELD.get(ent.label_)
                if not fld or fld in ner_values:
                    continue
                val = ent.text.strip()
                if fld in AMOUNT_FIELDS:
                    val = normalize_amount(val)
                elif fld in DATE_FIELDS:
                    val = normalize_date(val)
                ner_values[fld] = val

        # --- Zusammenführen: NER > Regex (ohne Einzel-Ausgabe) ---
        parsed_data = {}
        for field in selected_fields:
            if field in ner_values and ner_values[field]:
                parsed_data[field] = ner_values[field]
            else:
                pattern = FIELD_PATTERNS.get(field)
                if pattern:
                    match = re.search(pattern, text)
                    val = match.group(1) if match else "Nicht gefunden"
                    if field in AMOUNT_FIELDS and val != "Nicht gefunden":
                        val = normalize_amount(val)
                    elif field in DATE_FIELDS and val != "Nicht gefunden":
                        val = normalize_date(val)
                    parsed_data[field] = val
                else:
                    parsed_data[field] = "Nicht definiert"

        # --- Validierung (nur kompakte Warnung, keine Detail-Listen) ---
        if validate_fields:
            issues = validate_fields(parsed_data)
            if issues:
                st.warning("⚠ Einige Felder wirken inkonsistent (Validierung).")

        if any(val != "Nicht gefunden" for val in parsed_data.values()):
            rows_for_table.append(parsed_data)
        processed += 1

    # Quota erhöhen
    st.session_state["used_quota"] += processed

    # Session-Daten aktualisieren (nur Tabelle/Download später zeigen)
    if rows_for_table:
        st.session_state["data"].extend(rows_for_table)

# ---------------------- Tabelle & Excel-Download ----------------------
if st.session_state["data"]:
    st.header("📊 Ergebnisse als Excel-Datei")
    df = pd.DataFrame(st.session_state["data"])
    st.dataframe(df, use_container_width=True)

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

# Hinweis bei erreichtem Limit
if quota_left() == 0:
    st.error("🎉 Gratislimit erreicht. Kontaktiere uns für einen Testzugang oder ein Upgrade!")
