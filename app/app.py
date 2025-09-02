# app/app.py
import streamlit as st
import pandas as pd
import io
import re
import datetime
from datetime import date
import sys, os
from pathlib import Path

# Optional: shadcn-ui (falls installiert). Sonst fällt die App später auf st.button zurück.
try:
    import streamlit_shadcn_ui as ui
    HAS_SHADCN = True
except Exception:
    HAS_SHADCN = False

import spacy

# --- Projekt-Root in den Pfad aufnehmen (wenn nötig) ---
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# --- Utils importieren ---
from utils.pdf_reader import extract_text_from_pdf
from utils.ocr_reader import ocr_from_pdf
from utils.patterns import FIELD_PATTERNS
# Optional: Validierung
try:
    from validation import validate_fields
except Exception:
    validate_fields = None





# --- Projekt-Root in den Pfad aufnehmen (wenn nötig) ---
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# --- Utils importieren ---
from utils.pdf_reader import extract_text_from_pdf
from utils.ocr_reader import ocr_from_pdf
from utils.patterns import FIELD_PATTERNS
# Optional: Validierung
try:
    from validation import validate_fields
except Exception:
    validate_fields = None

# --- NER-Modell laden ---
def load_ner_model():
    """
    Lädt dein trainiertes spaCy-Modell aus models/.
    Bevorzugt 'ner_model_best', fällt zurück auf 'ner_model'.
    """
    try:
        return spacy.load(os.path.join(ROOT, "models", "ner_model_best"))
    except Exception:
        try:
            return spacy.load(os.path.join(ROOT, "models", "ner_model"))
        except Exception:
            return None

nlp = load_ner_model()
if nlp is None:
    st.error("❌ Konnte das NER-Modell nicht laden. Lege einen Ordner 'models/ner_model_best' oder 'models/ner_model' ab.")

# --- CSS laden ---
def inject_css():
    here = Path(__file__).parent
    candidate_files = [
        here / "style.css",
        here.parent / "style.css",
        Path(ROOT) / "style.css",
    ]
    for p in candidate_files:
        if p.exists():
            css = p.read_text(encoding="utf-8")
            st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
            return

inject_css()

inject_css()

# ---------------------- Session-State init & Quota ----------------------
FREE_QUOTA = 5
MAX_FILESIZE_MB = 5

if "data" not in st.session_state:
    st.session_state["data"] = []
if "used_quota" not in st.session_state:
    st.session_state["used_quota"] = 0
if "quota_date" not in st.session_state or st.session_state["quota_date"] != date.today().isoformat():
    st.session_state["quota_date"] = date.today().isoformat()
    st.session_state["used_quota"] = 0

def quota_left() -> int:
    return max(0, FREE_QUOTA - st.session_state["used_quota"])

# ---------------------- Hero Header ----------------------
# ---------------------- Top-Bar ----------------------
st.markdown(f"""
<div class="topbar" style="border:none; padding:1.8rem 0 1.2rem; display:block; text-align:center;">
  <div class="brand" style="font-size:2.3rem; font-weight:750; letter-spacing:-0.4px; color:#E9EDF5;">
    PDF-Rechnungsanalysator
  </div>
  <div class="top-actions" style="margin-top:.45rem;">
    <span class="badge" style="background:#0F1420; border:1px solid #1F2535; color:#C9DAFF;">
      Uploads verfügbar: {quota_left()} von {FREE_QUOTA}
    </span>
  </div>
</div>
""", unsafe_allow_html=True)




# ---------------------- Feld-Mapping & Normalisierung ----------------------
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

def normalize_amount(s: str) -> str:
    if not s:
        return s
    s = s.strip().replace("€", "").replace("EUR", "").replace("eur", "").replace("\u00A0", " ")
    s = s.replace(" ", "").replace(".", "").replace(",", ".")
    m = re.search(r"[+-]?\d+(?:\.\d+)?", s)
    return m.group(0) if m else s

def normalize_date(s: str) -> str:
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

# ---------------------- Felder auswählen ----------------------
# ---------------------- Felder auswählen ----------------------
st.markdown("<h1>Felder auswählen</h1>", unsafe_allow_html=True)
st.markdown('<div class="muted">Wähle die Felder aus, die du extrahieren möchtest:</div>', unsafe_allow_html=True)

selected_fields = st.multiselect(
    " ",  # Label leer, Überschrift übernimmt
    options=list(FIELD_PATTERNS.keys()),
    default=["Rechnungsnummer", "Datum", "Betrag (€)"]
)

if selected_fields:
    st.markdown('<div class="muted">Aktive Extraktionsfelder</div>', unsafe_allow_html=True)
    st.write("• " + " • ".join(selected_fields))

st.markdown('<div style="height:1px; background:var(--border); opacity:.7; width:72%; margin:1.1rem auto;"></div>', unsafe_allow_html=True)

# ---------------------- Datenschutz ----------------------
# ---------------------- Datenschutz ----------------------
st.markdown("<h1>Datenschutz</h1>", unsafe_allow_html=True)
st.markdown(
    '<div class="muted">Ich bestätige: keine sensiblen personenbezogenen Daten. Dateien werden nur temporär verarbeitet</div>',
    unsafe_allow_html=True
)

agree = st.checkbox(
    "Ich bestätige: keine sensiblen personenbezogenen Daten. Dateien werden nur temporär verarbeitet und nicht gespeichert.",
    key="agree",
    value=True
)


if not agree:
    st.stop()



# ---------------------- Upload & Analyse ----------------------
st.markdown("<h1>PDF-Dateien hochladen</h1>", unsafe_allow_html=True)
st.caption(
    f"Verfügbar: {quota_left()} von {FREE_QUOTA} kostenlosen Analysen "
    f"(bereits genutzt: {st.session_state['used_quota']})."
)

pdf_files = st.file_uploader(
    " ", type="pdf", accept_multiple_files=True, key="uploader"
)

# Hinweis – tatsächliche Kappung erst beim Start
if pdf_files and len(pdf_files) > quota_left():
    st.warning(
        f"Es sind nur noch {quota_left()} Analysen frei. "
        f"Es werden die ersten {quota_left()} Datei(en) verarbeitet."
    )


# --- CTA: Analyse starten (zentriert, groß, auffällig) ---
st.markdown('<div class="cta-hero">', unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    start_clicked = st.button(
        "Analyse starten",
        key="start-analyze",
        disabled=(quota_left() == 0 or not pdf_files),
        use_container_width=True
    )
st.markdown('</div>', unsafe_allow_html=True)

if start_clicked:
    files_to_process = (pdf_files or [])[:quota_left()]
    processed = 0

    for pdf_file in files_to_process:
        pdf_bytes = pdf_file.read()
        # ... dein bestehender Code ...


        # Größenlimit
        if len(pdf_bytes) > MAX_FILESIZE_MB * 1024 * 1024:
            st.warning(f"{pdf_file.name}: Datei größer als {MAX_FILESIZE_MB} MB – übersprungen.")
            continue

        # Text beschaffen (PDF-Extraktion, ggf. OCR)
        text = extract_text_from_pdf(io.BytesIO(pdf_bytes)) or ""
        if not text.strip():
            text = ocr_from_pdf(io.BytesIO(pdf_bytes)) or ""

        # --- NER ---
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

        # --- Regex-Fallback für ausgewählte Felder ---
        parsed = {}
        for field in selected_fields:
            if field in ner_values and ner_values[field]:
                parsed[field] = ner_values[field]
            else:
                pattern = FIELD_PATTERNS.get(field)
                if pattern:
                    m = re.search(pattern, text)
                    val = m.group(1) if m else "Nicht gefunden"
                    if field in AMOUNT_FIELDS and val != "Nicht gefunden":
                        val = normalize_amount(val)
                    elif field in DATE_FIELDS and val != "Nicht gefunden":
                        val = normalize_date(val)
                    parsed[field] = val
                else:
                    parsed[field] = "Nicht definiert"

        # --- Validierung ---
        if validate_fields:
            issues = validate_fields(parsed)
            if issues:
                for k, msg in issues.items():
                    st.warning(f"{k}: {msg}")

        # Ergebnis speichern
        if any(val != "Nicht gefunden" for val in parsed.values()):
            st.session_state["data"].append(parsed)
            st.success(f"Daten extrahiert aus: {pdf_file.name}")
        else:
            st.warning(f"Keine relevanten Daten in {pdf_file.name} gefunden.")

        processed += 1

    # Quota erhöhen
    st.session_state["used_quota"] += processed



# ---------------------- Ergebnisse / Excel ----------------------
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

# Hinweis bei ausgeschöpfter Quota
if quota_left() == 0:
    st.error("🎉 Gratislimit erreicht. Kontaktiere uns für einen Testzugang oder ein Upgrade!")

# ---------------------- (Optional) Debug-Tools ----------------------
with st.expander("Debug (nur lokal sichtbar)"):
    st.write(f"Quota-Datum: {st.session_state['quota_date']}")
    st.write(f"Used quota: {st.session_state['used_quota']} / {FREE_QUOTA}")
    if st.button("Gratis-Kontingent zurücksetzen"):
        st.session_state["used_quota"] = 0
        st.session_state["quota_date"] = date.today().isoformat()
        st.rerun()


