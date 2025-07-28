import pandas as pd
import os

def write_to_excel(data: dict, file_path="rechnungen.xlsx"):
    # Konvertiere Dictionary in DataFrame-Zeile
    new_row = pd.DataFrame([data])

    # Bestehende Datei einlesen oder neuen DataFrame erstellen
    if os.path.exists(file_path):
        try:
            df = pd.read_excel(file_path)
            df = pd.concat([df, new_row], ignore_index=True)
        except Exception as e:
            print(f"Fehler beim Lesen der Datei: {e}")
            df = new_row
    else:
        df = new_row

    df.to_excel(file_path, index=False)
