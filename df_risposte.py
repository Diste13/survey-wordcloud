import os
import glob
import json
import pandas as pd

# 1) Specifica il percorso alla cartella con i JSON
folder_path = r"C:\Users\francescodistefano\Downloads\risposte survey 29_05"

# 2) Trova tutti i file con estensione .json
json_files = glob.glob(os.path.join(folder_path, "*.json"))

# 3) Lista dove accumuleremo i dizionari “appiattiti”
rows = []

for filepath in json_files:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Trasforma l’array "impacts" in un’unica stringa separata da ; 
    if "impacts" in data and isinstance(data["impacts"], list):
        data["impacts"] = ";".join(data["impacts"])

    rows.append(data)

# 4) Crea un DataFrame Pandas a partire dalla lista di dizionari
df = pd.DataFrame(rows)

# 5) (Opzionale) Riordina o rinomina le colonne se serve, ad esempio:
# desired_order = ["gap_analysis", "board_inform", "budget", "adeguamento_specifico", "impacts", "bm_yes_no", "bm_nominee"]
# df = df[desired_order]

# 6) Scrivi su file Excel. Il file verrà creato nella stessa cartella di lavoro di esecuzione,
#    ma puoi cambiare il path in output_path come preferisci.
output_path = os.path.join(folder_path, "dataset_survey.xlsx")
df.to_excel(output_path, index=False, engine="openpyxl")

print(f"Fatto: ho salvato {len(df)} righe in '{output_path}'")
