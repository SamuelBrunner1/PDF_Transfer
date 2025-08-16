import spacy

# Modell laden
nlp = spacy.load(r"C:\Leben\PDF_Transfer\ner_model")

# Beispielsatz
text = "RNR: 9502 Datum: 25.10.2025 Betrag: 4281,00 EUR"

doc = nlp(text)
for ent in doc.ents:
    print(ent.text, ent.label_)
