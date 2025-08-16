# -*- coding: utf-8 -*-
"""
fix_json.py – robuste Bereinigung & Alignment deiner Doccano-JSONL-Annotationen
Ziele:
- Labelnamen vereinheitlichen
- Offsets auf Token-Grenzen alignen (spaCy char_span, alignment_mode="expand")
- Duplikate / leere / ungültige Spans entfernen
- Problemfälle protokollieren, statt sie still zu verwerfen
"""

import json
import io
import os
from collections import Counter

import spacy

# ----------------------------
# Pfade anpassen (oder via CLI/Runner setzen)
# ----------------------------
SRC = r"C:\Leben\PDF_Transfer\rechnungen_export\samuel6.jsonl"
DST = r"C:\Leben\PDF_Transfer\rechnungen_export\samuel6_fixed.jsonl"
LOG = r"C:\Leben\PDF_Transfer\rechnungen_export\samuel6_fix_report.txt"

# ----------------------------
# spaCy-Objekt (de – nur Tokenisierung)
# ----------------------------
# Blank-Deutsch reicht; wir brauchen nur saubere Token-Grenzen
nlp = spacy.blank("de")

# ----------------------------
# Label-Mapping (Kanonisierung)
# Wichtig: Deine Ziel-Labels
# ----------------------------
CANON = {
    "FIRMENNAME",
    "ADRESSE",
    "EMAIL",
    "RECHNUNGSEMPFÄNGER",
    "RECHNUNGSNUMMER",
    "RECHNUNGSDATUM",
    "KUNDENNUMMER",
    "BESTELLNUMMER",
    "LEISTUNGSDATUM",
    "ZAHLUNGSZIEL",
    "LEISTUNG",
    "ZWISCHENSUMME_NETTO",
    "UST_BETRAG",
    "UST_ID",
    "STEUERSATZ",
    "BRUTTOBETRAG",
    "WÄHRUNG",
    "ZAHLUNGSART",
    "IBAN",
    "BIC",
}

LABEL_MAP = {
    # deutsch
    "Firmenname": "FIRMENNAME",
    "Adresse": "ADRESSE",
    "E-Mail": "EMAIL", "Email": "EMAIL",
    "Empfänger": "RECHNUNGSEMPFÄNGER", "Rechnungsempfänger": "RECHNUNGSEMPFÄNGER",

    "Rechnungsnummer": "RECHNUNGSNUMMER",
    "Rechnungsdatum": "RECHNUNGSDATUM",

    "Kundennummer": "KUNDENNUMMER",
    "Kunden-ID": "KUNDENNUMMER",
    "Kundencode": "KUNDENNUMMER",
    "Kunden-Nr.": "KUNDENNUMMER",
    "Kundennr.": "KUNDENNUMMER",

    "Bestellnummer": "BESTELLNUMMER",
    "Belegnummer": "BESTELLNUMMER",
    "Buchungsnummer": "BESTELLNUMMER",
    "Referenz": "BESTELLNUMMER",
    "Referenz-Nr.": "BESTELLNUMMER",
    "PO": "BESTELLNUMMER",

    "Leistungsdatum": "LEISTUNGSDATUM",
    "Leistungszeit": "LEISTUNGSDATUM",
    "Leistungszeitraum": "LEISTUNGSDATUM",
    "Zeitraum der Leistung": "LEISTUNGSDATUM",
    "Erbrachte Leistung am": "LEISTUNGSDATUM",
    "Zeitpunkt Leistung": "LEISTUNGSDATUM",

    "Zahlungsziel": "ZAHLUNGSZIEL",

    "Leistung": "LEISTUNG",
    "Leistungsbeschreibung": "LEISTUNG",

    "Zwischensumme": "ZWISCHENSUMME_NETTO",
    "Zwischensumme (netto)": "ZWISCHENSUMME_NETTO",

    "USt-Betrag": "UST_BETRAG",

    "USt-Identifikationsnummer": "UST_ID",
    "USt-IdNr": "UST_ID",
    "UID-Nr.": "UST_ID",
    "VAT ID": "UST_ID",

    "Steuersatz": "STEUERSATZ",

    "Gesamtbetrag": "BRUTTOBETRAG",
    "Gesamtbetrag (brutto)": "BRUTTOBETRAG",
    "Gesamtsumme brutto": "BRUTTOBETRAG",

    "Waehrung": "WÄHRUNG", "Währung": "WÄHRUNG",

    "Zahlungsart": "ZAHLUNGSART",
    "Zahlweise": "ZAHLUNGSART",

    "IBAN": "IBAN",
    "BIC": "BIC",

    # englische Varianten für DE/AT-Mix
    "Invoice No": "RECHNUNGSNUMMER",
    "Invoice ID": "RECHNUNGSNUMMER",
    "Invoice Date": "RECHNUNGSDATUM",
    "Purchase Order": "BESTELLNUMMER",
    "PO Number": "BESTELLNUMMER",
    "Due Date": "ZAHLUNGSZIEL",
    "Service Date": "LEISTUNGSDATUM",
    "Subtotal": "ZWISCHENSUMME_NETTO",
    "VAT Amount": "UST_BETRAG",
    "VAT ID": "UST_ID",
    "Tax Rate": "STEUERSATZ",
    "Total": "BRUTTOBETRAG",
    "Currency": "WÄHRUNG",
    "Payment Method": "ZAHLUNGSART",
}

# Fallback: erkenne häufige, vom Tool abgeschnittene Kürzel (Prefix-Heuristik)
PREFIX_MAP = {
    "ZWISCHENSUMM": "ZWISCHENSUMME_NETTO",
    "RECHNUNGSNUM": "RECHNUNGSNUMMER",
    "RECHNUNGSDAT": "RECHNUNGSDATUM",
    "BESTELLNUMME": "BESTELLNUMMER",
}


def canon_label(lbl: str) -> str:
    if lbl in CANON:
        return lbl
    if lbl in LABEL_MAP:
        return LABEL_MAP[lbl]
    # Prefix-Heuristik
    for pref, target in PREFIX_MAP.items():
        if lbl.startswith(pref):
            return target
    return lbl  # unbekannt – bleibt wie ist, wird später validiert


def load_jsonl(path):
    with io.open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def detect_label_key(item):
    # Doccano kann "label" oder "labels" nutzen
    if "labels" in item:
        return "labels"
    if "label" in item:
        return "label"
    # spaCy-style?
    if "entities" in item:
        return "entities"
    # Fallback
    return "labels"


def align_spans(text, spans):
    """
    Nimmt [(start, end, label), ...], richtet auf Token-Grenzen aus.
    Gibt (fixed_spans, stats) zurück.
    """
    doc = nlp.make_doc(text)
    fixed = []
    stats = Counter()

    for s, e, lbl in spans:
        # Skip klar ungültige
        if s is None or e is None:
            stats["skip_none"] += 1
            continue
        if not (0 <= s < e <= len(text)):
            stats["skip_bounds"] += 1
            continue

        # Versuche expand (bevorzugt, stabil gegen W030)
        span = doc.char_span(s, e, alignment_mode="expand", label=lbl)
        if span is None:
            # fallback contract
            span = doc.char_span(s, e, alignment_mode="contract", label=lbl)
        if span is None:
            stats["skip_unaligned"] += 1
            continue

        new_s, new_e = span.start_char, span.end_char
        # Leere / whitespace-only?
        if not text[new_s:new_e].strip():
            stats["skip_empty"] += 1
            continue

        fixed.append((new_s, new_e, lbl))
        if (new_s, new_e) != (s, e):
            stats["adjusted"] += 1
        else:
            stats["kept"] += 1

    # Duplikate entfernen
    fixed = sorted(set(fixed), key=lambda x: (x[0], x[1], x[2]))
    return fixed, stats


def main(src=SRC, dst=DST, log_path=LOG):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    total = 0
    wrote = 0
    global_stats = Counter()
    problems = []

    with io.open(dst, "w", encoding="utf-8") as fout:
        for item in load_jsonl(src):
            total += 1

            text = item.get("text", "")
            key = detect_label_key(item)
            raw_spans = item.get(key, item.get("entities", []))

            # Doccano kann [start, end, label]-Listen oder dicts liefern → normalisieren:
            spans_norm = []
            for span in raw_spans:
                if isinstance(span, dict):
                    s = span.get("start") or span.get("start_offset")
                    e = span.get("end") or span.get("end_offset")
                    lbl = span.get("label")
                else:
                    # [start, end, label]
                    try:
                        s, e, lbl = span
                    except Exception:
                        continue
                # Label kanonisieren
                lbl = canon_label(str(lbl))
                spans_norm.append((int(s), int(e), lbl))

            # Nicht-kanonische Labels filtern/merken
            before = len(spans_norm)
            spans_norm = [t for t in spans_norm if t[2] in CANON]
            global_stats["unknown_label_dropped"] += (before - len(spans_norm))

            # Alignment
            fixed_spans, stats = align_spans(text, spans_norm)
            global_stats.update(stats)

            # Wenn nach Alignment alles weg wäre, behalten wir den Text ohne Labels (oder loggen als Problem)
            if not fixed_spans and spans_norm:
                problems.append({
                    "reason": "all_spans_dropped_after_alignment",
                    "text_head": text[:120].replace("\n", " "),
                    "count_before": len(spans_norm)
                })

            # Zurück in das ursprüngliche Key-Format (label/labels/entities)
            def to_out(span):
                s, e, l = span
                # Doccano-kompatibel: [start, end, label]
                return [s, e, l]

            out_item = dict(item)  # original Felder beibehalten
            out_item["text"] = text
            out_item[key] = [to_out(s) for s in fixed_spans]

            fout.write(json.dumps(out_item, ensure_ascii=False) + "\n")
            wrote += 1

    # Log schreiben
    with io.open(log_path, "w", encoding="utf-8") as lf:
        lf.write(f"fix_json report\n")
        lf.write(f"source: {src}\noutput: {dst}\n\n")
        lf.write(f"records_total: {total}\nrecords_written: {wrote}\n\n")
        for k, v in global_stats.items():
            lf.write(f"{k}: {v}\n")
        lf.write("\nProblems (truncated text shown):\n")
        for p in problems:
            lf.write(json.dumps(p, ensure_ascii=False) + "\n")

    print("✅ Fixed JSONL geschrieben nach:", DST)
    print("📝 Report:", LOG)
    print("📊 Stats:", dict(global_stats))


if __name__ == "__main__":
    main()
