FIELD_PATTERNS = {
    "Rechnungsnummer": r"Rechnungsnummer[:\s]*([A-Z0-9\-\/]+)",
    "Rechnungsdatum": r"(?:Rechnungs-?datum|Datum)[:\s]*(\d{2}\.\d{2}\.\d{4})",
    "Datum": r"(?:Rechnungs-?datum|Datum)[:\s]*(\d{2}\.\d{2}\.\d{4})",

    "Betrag (€)": r"(?:Gesamtbetrag(?:\s*\(.*?\))?|Betrag|Summe|Rechnungsbetrag|Brutto)[:\s]*(?:EUR|€)?\s*([\d.,]+)",
    "Umsatzsteuer": r"(?:USt\.?|Umsatzsteuer)\s*(?:\(\d+%?\))?[:\s]*(?:EUR|€)?\s*([\d.,]+)",

    "Zahlungsziel": r"Zahlungsziel[:\s]*(\d{2}\.\d{2}\.\d{4})",
    "Zahlungsart": r"Zahlungsart[:\s]*([A-Za-zäöüÄÖÜß ]+)",
    "Bestellnummer": r"(?:Bestellnummer|Best\.?-?Nr\.?)[:\s]*([A-Z0-9\-\/]+)",
    "Artikelnummer": r"(?:Artikelnummer|Art\.?-?Nr\.?)[:\s]*([A-Z0-9\-]+)",

    "UID": r"UID[:\s]*([A-Z]{2}[A-Z0-9]+)",
    "Kundennummer": r"Kundennummer[:\s]*([A-Z0-9\-]+)",
    "IBAN": r"IBAN[:\s]*([A-Z]{2}\d{2}(?:[ ]?\d{4}){4,5})",
    "BIC": r"BIC[:\s]*([A-Z0-9]{8,11})",

    "Name": r"Name[:\s]*([A-ZÄÖÜa-zäöüß\- ]+)",
    "Vorname": r"Vorname[:\s]*([A-ZÄÖÜa-zäöüß\-]+)",
    "Nachname": r"Nachname[:\s]*([A-ZÄÖÜa-zäöüß\-]+)",
    "Firmenname": r"(?:Firma|Unternehmen|Lieferant|Steuerberatung)[:\s]*([A-ZÄÖÜa-zäöüß0-9 &\-]+)",

    "Adresse": r"(?:Adresse|Anschrift)[:\s]*([\wäöüÄÖÜß\s.,\-]+)",
    "PLZ": r"(?:PLZ|Postleitzahl)[:\s]*(\d{4,5})",
    "Ort": r"(?:Ort|Stadt)[:\s]*([A-ZÄÖÜa-zäöüß\- ]+)",
    "Land": r"Land[:\s]*([A-ZÄÖÜa-zäöüß ]+)",
    "E-Mail": r"(?:E-?Mail)[:\s]*([\w\.-]+@[\w\.-]+\.\w+)",
    "Telefonnummer": r"(?:Tel\.?|Telefon)[:\s]*([\d\/ +()-]{7,})",

    "Lieferdatum": r"(?:Lieferdatum|Leistungsdatum)[:\s]*(\d{2}\.\d{2}\.\d{4})",

    # ✨ Neue optionale Felder, falls du sie brauchst:
    "Zwischensumme": r"Zwischensumme\s*(?:\(.*?\))?[:\s]*(?:EUR|€)?\s*([\d.,]+)",
    "Skonto": r"Skonto[:\s]*(?:EUR|€)?\s*([\d.,]+)",
    "Zahlbar bis": r"(?:Zahlbar bis|Fälligkeitsdatum)[:\s]*(\d{2}\.\d{2}\.\d{4})"
}
