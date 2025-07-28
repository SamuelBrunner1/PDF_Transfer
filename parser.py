import re

def parse_text(text, rules):
    """
    rules: Liste von Dictionaries, z.B.:
        [{"field": "Rechnungsnummer", "pattern": "Rechnungsnummer[:\\s]*([A-Z0-9\\-\\/]+)"}]
    text: extrahierter Text aus PDF
    Rückgabe: Dictionary mit extrahierten Werten
    """
    result = {}
    for rule in rules:
        try:
            match = re.search(rule["pattern"], text)
            result[rule["field"]] = match.group(1) if match else None
        except Exception:
            result[rule["field"]] = None
    return result
