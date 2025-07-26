import pandas as pd
import os

def write_to_excel(data, file_path="rechnungen.xlsx"):
    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
    else:
        df = pd.DataFrame([data])
    df.to_excel(file_path, index=False)
