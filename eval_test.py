import json, spacy
from spacy.training import Example

MODEL_PATH = r"C:\Leben\PDF_Transfer\ner_model"
TEST_PATH  = r"C:\Leben\PDF_Transfer\test.jsonl"

nlp = spacy.load(MODEL_PATH)

def iter_examples(jsonl_path):
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            it = json.loads(line)
            text = it["text"]
            # Labels-Feld robust auslesen (labels/label/entities)
            raw = it.get("labels") or it.get("label") or it.get("entities") or []
            spans = []
            for s in raw:
                if isinstance(s, dict):
                    start = s.get("start") or s.get("start_offset")
                    end   = s.get("end")   or s.get("end_offset")
                    label = s["label"]
                else:
                    start, end, label = s
                spans.append((int(start), int(end), label))
            # Example bauen (Reference = Gold, Pred wird von nlp.evaluate erzeugt)
            doc = nlp.make_doc(text)
            yield Example.from_dict(doc, {"entities": spans})

examples = list(iter_examples(TEST_PATH))
scores = nlp.evaluate(examples)  # <-- hier korrekt evaluieren

print("TEST F1:", round(scores["ents_f"], 3))
print("Per label:", {k: round(v["f"], 3) for k, v in scores["ents_per_type"].items()})
