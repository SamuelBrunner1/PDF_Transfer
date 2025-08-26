import os, json, glob

SRC = r"C:\Leben\PDF_Transfer\text\15bessereRechnungen"  # TXT-Ordner
OUT = r"C:\Leben\PDF_Transfer\rechnungen_export\samuel8_with_label.jsonl"  # Ziel

os.makedirs(os.path.dirname(OUT), exist_ok=True)

n = 0
with open(OUT, "w", encoding="utf-8") as f:
    for p in sorted(glob.glob(os.path.join(SRC, "*.txt"))):
        with open(p, "r", encoding="utf-8") as fin:
            txt = fin.read().strip()
        if not txt:
            print("WARN: empty txt ->", p)
        f.write(json.dumps({"text": txt, "label": []}, ensure_ascii=False) + "\n")
        n += 1

print(f"OK: {OUT} (Zeilen: {n})")
