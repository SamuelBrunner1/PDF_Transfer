import re

def parse_invoice(text):
    return {
        "Rechnungsnummer": re.search(r"Rechnungsnummer[:\s]*([A-Z0-9\-\/]+)", text).group(1),
        "Datum": re.search(r"Datum[:\s]*([\d.]+)", text).group(1),
        "Betrag (€)": re.search(r"(?:Betrag|Gesamt|Summe)[:\s]*EUR\s*([\d.,]+)", text).group(1).replace(",", ".")
    }
