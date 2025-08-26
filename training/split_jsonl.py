import json, random, os, argparse

# -------------------------------
# Argumente definieren
# -------------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--src", required=True, help="Pfad zur JSONL-Datei (Doccano export, fixed)")
parser.add_argument("--out", default=r"C:\Leben\PDF_Transfer", help="Ausgabeordner")
parser.add_argument("--train_ratio", type=float, default=0.80, help="Anteil Training (z. B. 0.80 = 80%)")
parser.add_argument("--dev_ratio", type=float, default=0.15, help="Anteil Dev (z. B. 0.15 = 15%)")
parser.add_argument("--seed", type=int, default=42, help="Seed für Zufallsreihenfolge (Reproduzierbarkeit)")
args = parser.parse_args()

# -------------------------------
# Seed setzen → Splits reproduzierbar
# -------------------------------
random.seed(args.seed)

# -------------------------------
# JSONL-Daten laden
# -------------------------------
with open(args.src, "r", encoding="utf-8") as f:
    # jede Zeile ist ein JSON-Objekt, leere Zeilen werden ignoriert
    data = [json.loads(line) for line in f if line.strip()]

# -------------------------------
# Reihenfolge zufällig mischen
# -------------------------------
random.shuffle(data)

# -------------------------------
# Splitgrößen berechnen
# -------------------------------
n = len(data)
n_train = max(1, int(round(n * args.train_ratio)))  # Anzahl Trainings-Dokus
n_dev   = max(1, int(round(n * args.dev_ratio)))    # Anzahl Dev-Dokus

# Sicherstellen, dass immer etwas für Test übrig bleibt
if n_train + n_dev >= n:
    n_dev = max(1, n - n_train - 1)

# -------------------------------
# Aufteilen in Splits
# -------------------------------
train = data[:n_train]
dev   = data[n_train:n_train+n_dev]
test  = data[n_train+n_dev:]

# -------------------------------
# Splits speichern
# -------------------------------
for name, split in [("train.jsonl", train), ("dev.jsonl", dev), ("test.jsonl", test)]:
    p = os.path.join(args.out, name)
    with open(p, "w", encoding="utf-8") as fo:
        for item in split:
            fo.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Wrote {len(split):>3} → {p}")

# -------------------------------
# Kurze Übersicht ausgeben
# -------------------------------
print(f"Total: {len(data)} | Train: {len(train)} | Dev: {len(dev)} | Test: {len(test)}")
