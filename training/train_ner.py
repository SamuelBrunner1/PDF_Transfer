# -*- coding: utf-8 -*-
"""
train_ner.py – Training für dein NER-Modell mit deutschen Pretrained Embeddings
"""

import json
from pathlib import Path
import random
import numpy as np
import spacy
from spacy.training.example import Example
from spacy.util import minibatch, compounding, fix_random_seed

# -------------------- Pfade --------------------
BASE = Path(r"C:\Leben\PDF_Transfer")
train_path = BASE / "train.jsonl"
dev_path   = BASE / "dev.jsonl"
out_dir    = BASE / "ner_model"        # aktuelles Modell
best_dir   = BASE / "ner_model_best"   # bestes Dev-F1-Modell

# -------------------- Seeds fixen (Reproduzierbarkeit) --------------------
fix_random_seed(42)
random.seed(42)
np.random.seed(42)

# -------------------- Daten laden --------------------
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

# -------------------- NER-Pipeline --------------------
# Pretrained deutsches Modell laden
nlp = spacy.load("de_core_news_md")

# Alles außer den Vektoren entfernen
for pipe in list(nlp.pipe_names):
    if pipe != "tok2vec":
        nlp.remove_pipe(pipe)

# NER hinzufügen
ner = nlp.add_pipe("ner", last=True)

# Labels registrieren
for _, ann in train_data:
    for s, e, lbl in ann["entities"]:
        ner.add_label(lbl)

# Optimizer initialisieren
optimizer = nlp.begin_training()

# -------------------- Evaluation --------------------
def evaluate(nlp, data):
    tp = fp = fn = 0
    for text, ann in data:
        pred = nlp(text)
        pred_ents = {(ent.start_char, ent.end_char, ent.label_) for ent in pred.ents}
        gold_ents = {(s, e, lbl) for s, e, lbl in ann["entities"]}
        tp += len(pred_ents & gold_ents)
        fp += len(pred_ents - gold_ents)
        fn += len(gold_ents - pred_ents)
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec  = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1   = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    return prec, rec, f1, tp, fp, fn

# -------------------- Training --------------------
EPOCHS = 180  # ~10–15 Min auf CPU
best_f1 = -1.0

for epoch in range(1, EPOCHS + 1):
    random.shuffle(train_data)
    losses = {}

    # batch size wächst bis 48
    for batch in minibatch(train_data, size=compounding(4.0, 48.0, 1.5)):
        examples = []
        for text, ann in batch:
            doc = nlp.make_doc(text)
            examples.append(Example.from_dict(doc, ann))
        nlp.update(examples, drop=0.40, sgd=optimizer, losses=losses)  # Dropout leicht erhöht

    # Dev-Eval
    prec, rec, f1, tp, fp, fn = evaluate(nlp, dev_data)

    if epoch == 1 or epoch % 5 == 0:
        print(f"Epoche {epoch:03d} | Loss={losses.get('ner', 0):.1f} | Dev P={prec:.3f} R={rec:.3f} F1={f1:.3f}")

    # Best-Checkpoint sichern
    if f1 > best_f1:
        best_f1 = f1
        best_dir.mkdir(parents=True, exist_ok=True)
        nlp.to_disk(best_dir)

# -------------------- Modelle speichern --------------------
out_dir.mkdir(parents=True, exist_ok=True)
nlp.to_disk(out_dir)
print(f"Bestes Dev-F1: {best_f1:.3f} -> gespeichert in {best_dir}")
print(f"✅ Aktuelles Modell gespeichert nach: {out_dir}")
