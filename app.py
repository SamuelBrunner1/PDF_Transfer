import streamlit as st
import pandas as pd
import io
import re
import spacy
import datetime

from pdf_reader import extract_text_from_pdf
from ocr_reader import ocr_from_pdf
from patterns import FIELD_PATTERNS

# Optional: Validierung
try:
    from validation import validate_fields
except Exception:
    validate_fields = None

# --- NER-Modell laden ---
try:
    nlp = spacy.load("ner_model")  # relativer Pfad zu deinem trainierten Modell
except Exception:
    nlp = None
    st.error("❌ Konnte das NER-Modell nicht laden. Bitte stelle sicher, dass der Ordner 'ner_model' existiert.")

# CSS laden (optional)
try:
    with open("style.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

st.title("📄 PDF-Rechnungsanalysator")

# Session-State initialisieren
if "data" not in st.session_state:
    st.session_state["data"] = []

# ---------------------- Utils: Normalisierung & Mapping ----------------------

def normalize_amount(s: str) -> str:
    """ 'EUR 2.160,00' -> '2160.00' (String, gut für Excel/Weiterverarbeitung) """
    if not s:
        return s
    s = s.strip()
    s = s.replace("€", "").replace("EUR", "").replace("eur", "")
    s = s.replace("\u00A0", " ")  # NBSP
    # Tausendertrennzeichen/Leerzeichen raus
    s = s.replace(" ", "")
    # Wenn Punkt als Tausendertrennzeichen und Komma als Dezimaltrenner vorkommt:
    # Entferne Punkte, ersetze Komma durch Punkt
    # (funktioniert auch für '2.160,00' -> '2160.00')
    s = s.replace(".", "").replace(",", ".")
    m = re.search(r"[+-]?\d+(?:\.\d+)?", s)
    return m.group(0) if m else s

def normalize_date(s: str) -> str:
    """ Versucht gängige deutsche Formate auf ISO (YYYY-MM-DD) zu bringen """
    if not s:
        return s
    s = s.strip().replace("\u00A0", " ")
    candidates = [
        "%d.%m.%Y", "%d.%m.%y",
        "%Y-%m-%d", "%Y.%m.%d",
    ]
    for fmt in candidates:
        try:
            return datetime.datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    # reiner Tag ohne 'am:' etc.?
    m = re.search(r"\b(\d{1,2}\.\d{1,2}\.\d{2,4})\b", s)
    if m:
        return normalize_date(m.group(1))
    return s

# Mapping: NER-Label -> Feldname in deiner UI/Excel
# Passen ggf. an deine exakten Spaltenbezeichnungen an!
NER_TO_FIELD = {
    "RECHNUNGSNUMMER": "Rechnungsnummer",
    "RECHNUNGSDATUM": "Datum",
    "LEISTUNGSDATUM": "Leistungsdatum",
    "ZAHLUNGSZIEL": "Zahlungsziel",
    "LEISTUNG": "Leistung",
    "ZWISCHENSUMME_NETTO": "Zwischensumme",
    "UST_BETRAG": "USt_Betrag",      # Falls dein Feld "UST_BETRAG" heißt
    "UST_ID": "UID",                  # In deiner Excel-Spalte evtl. "UID" / "USt-ID"
    "STEUERSATZ": "Steuersatz",
    "BRUTTOBETRAG": "Betrag (€)",     # Deine Excel-Spalte heißt so
    "WÄHRUNG": "Währung",
    "IBAN": "IBAN",
    "BIC": "BIC",
    "FIRMENNAME": "Firmenname",
    "ADRESSE": "Adresse",
    "EMAIL": "E-Mail",                # Falls deine Spalte "E-Mail" heißt
    "RECHNUNGSEMPFÄNGER": "Rechnungsempfänger",
    "KUNDENNUMMER": "Kundennummer",
    "BESTELLNUMMER": "Bestellnummer",
    # weitere Labels ggf. hier ergänzen
}

# Welche Felder sind "Beträge" bzw. "Daten" für Normalisierung?
AMOUNT_FIELDS = {"Betrag (€)", "Zwischensumme", "USt_Betrag"}
DATE_FIELDS   = {"Datum", "Leistungsdatum", "Zahlungsziel"}

# ---------------------- UI: Felder auswählen ----------------------

st.header("🔍 Felder auswählen")
selected_fields = st.multiselect(
    "Wähle die Felder aus, die du extrahieren möchtest:",
    options=list(FIELD_PATTERNS.keys()),
    default=["Rechnungsnummer", "Datum", "Betrag (€)"]
)

# Aktive Felder anzeigen
if selected_fields:
    st.subheader("✅ Aktive Extraktionsfelder")
    for field in selected_fields:
        st.markdown(f"✔ **{field}**")

# ---------------------- Upload & Analyse ----------------------

st.header("📂 PDF-Dateien hochladen")
pdf_files = st.file_uploader(
    "Wähle PDF-Dateien aus", type="pdf", accept_multiple_files=True
)

if pdf_files and st.button("Analyse starten"):
    st.session_state["data"] = []

    for pdf_file in pdf_files:
        pdf_bytes = pdf_file.read()
        text = extract_text_from_pdf(io.BytesIO(pdf_bytes))

        if not text.strip():
            st.warning(f"OCR wird verwendet für {pdf_file.name}...")
            text = ocr_from_pdf(io.BytesIO(pdf_bytes))

        st.subheader(f"📃 {pdf_file.name}")
        st.text(text)

        # --------- NER-Analyse & Mapping ----------
        ner_values = {}  # export_feld -> wert
        if nlp:
            doc = nlp(text)

            # 1) Anzeige (wie gehabt)
            ents = [(ent.label_, ent.text) for ent in doc.ents]
            if ents:
                st.markdown("### 🧠 KI-Erkannte Entitäten")
                for label, value in ents:
                    st.write(f"**{label}**: {value}")

            # 2) Mapping auf Export-Felder (erstes Vorkommen gewinnt)
            for ent in doc.ents:
                fld = NER_TO_FIELD.get(ent.label_)
                if not fld:
                    continue
                if fld in ner_values:
                    continue  # erstes Vorkommen behalten
                val = ent.text.strip()
                if fld in AMOUNT_FIELDS:
                    val = normalize_amount(val)
                elif fld in DATE_FIELDS:
                    val = normalize_date(val)
                ner_values[fld] = val

        # --------- Zusammenführen: NER priorisiert, Regex als Fallback ----------
        parsed_data = {}
        for field in selected_fields:
            # 1) NER hat Vorrang
            if field in ner_values and ner_values[field]:
                parsed_data[field] = ner_values[field]
                continue

            # 2) Regex-Fallback
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

        # --- Validierung (wenn vorhanden)
        if validate_fields:
            issues = validate_fields(parsed_data)
            if issues:
                st.warning("⚠ Mögliche Probleme erkannt:")
                for k, msg in issues.items():
                    st.text(f"{k}: {msg}")

        if any(val != "Nicht gefunden" for val in parsed_data.values()):
            st.session_state["data"].append(parsed_data)
            st.success(f"✅ Erfolgreich extrahiert aus: {pdf_file.name}")
        else:
            st.warning(f"❌ Keine passenden Daten in {pdf_file.name} gefunden.")

        # Debug-Ausgabe JSON (hilfreich zum Abgleich)
        st.json(parsed_data)

# ---------------------- Excel-Download ----------------------

if st.session_state["data"]:
    st.header("📊 Ergebnisse als Excel-Datei")
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
