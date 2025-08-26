import spacy

nlp = spacy.load("de_core_news_md")

def extract_named_entities(text):
    doc = nlp(text)
    results = {
        "Vorname": None,
        "Nachname": None,
        "Ort": None,
        "E-Mail": None
    }

    for ent in doc.ents:
        if ent.label_ == "PER":
            parts = ent.text.split(" ")
            if len(parts) >= 2:
                results["Vorname"] = parts[0]
                results["Nachname"] = parts[-1]
        elif ent.label_ == "LOC":
            results["Ort"] = ent.text
        elif "@" in ent.text:
            results["E-Mail"] = ent.text

    return {k: v or "Nicht gefunden" for k, v in results.items()}
