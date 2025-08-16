import json
from pathlib import Path
import spacy
from spacy.training.example import Example
from spacy.util import minibatch

BASE = Path(r"C:\Leben\PDF_Transfer")
train_path = BASE / "train.jsonl"
dev_path   = BASE / "dev.jsonl"
out_dir    = BASE / "ner_model"

def load_jsonl(path: Path):
    data = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            text = item["text"]
            ents = [(int(s), int(e), str(lbl)) for s, e, lbl in item.get("label", [])]
            data.append((text, {"entities": ents}))
    return data

train_data = load_jsonl(train_path)
dev_data   = load_jsonl(dev_path)
print(f"Train: {len(train_data)} | Dev: {len(dev_data)}")

nlp = spacy.blank("de")          # leeres deutsches Modell
ner = nlp.add_pipe("ner")        # NER-Pipeline

# Labels registrieren
for _, ann in train_data:
    for s, e, lbl in ann["entities"]:
        ner.add_label(lbl)

optimizer = nlp.begin_training()

EPOCHS = 40
for epoch in range(1, EPOCHS+1):
    losses = {}
    batches = minibatch(train_data, size=8)
    for batch in batches:
        examples = []
        for text, ann in batch:
            doc = nlp.make_doc(text)
            examples.append(Example.from_dict(doc, ann))
        nlp.update(examples, drop=0.35, sgd=optimizer, losses=losses)
    if epoch == 1 or epoch % 5 == 0:
        print(f"Epoche {epoch:02d} | Verlust: {losses.get('ner', 0):.3f}")

# einfache Dev-Evaluierung
def evaluate(nlp, data):
    tp=fp=fn=0
    for text, ann in data:
        pred = nlp(text)
        pred_ents={(ent.start_char, ent.end_char, ent.label_) for ent in pred.ents}
        gold_ents={(s,e,lbl) for s,e,lbl in ann["entities"]}
        tp += len(pred_ents & gold_ents)
        fp += len(pred_ents - gold_ents)
        fn += len(gold_ents - pred_ents)
    prec = tp/(tp+fp) if (tp+fp)>0 else 0.0
    rec  = tp/(tp+fn) if (tp+fn)>0 else 0.0
    f1   = 2*prec*rec/(prec+rec) if (prec+rec)>0 else 0.0
    return prec, rec, f1, tp, fp, fn

prec, rec, f1, tp, fp, fn = evaluate(nlp, dev_data)
print(f"Dev: P={prec:.2f} R={rec:.2f} F1={f1:.2f} (TP={tp}, FP={fp}, FN={fn})")

out_dir.mkdir(parents=True, exist_ok=True)
nlp.to_disk(out_dir)
print(f"✅ Modell gespeichert: {out_dir}")
