import json, random, os, pathlib

src = r"C:\Leben\PDF_Transfer\rechnungen_export\samuel6_fixed.jsonl"
out_dir = r"C:\Leben\PDF_Transfer"
random.seed(42)

with open(src, "r", encoding="utf-8") as f:
    data = [json.loads(line) for line in f if line.strip()]

random.shuffle(data)

# 35 → 25/5/5
train, dev, test = data[:25], data[25:30], data[30:35]

for name, split in [("train.jsonl", train), ("dev.jsonl", dev), ("test.jsonl", test)]:
    p = os.path.join(out_dir, name)
    with open(p, "w", encoding="utf-8") as fo:
        for item in split:
            fo.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Wrote {len(split)} → {p}")
