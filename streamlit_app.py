import streamlit as st
from github import Github
import json
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# --- 1) Carica secrets di Streamlit ---
# Nel file .streamlit/secrets.toml (vedi passo 5) metterai:
# github_token = "..."
# repo_name    = "username/survey-wordcloud"

token    = st.secrets["github_token"]
repo_name= st.secrets["repo_name"]
g        = Github(token)
repo     = g.get_repo(repo_name)
file_path= "responses.json"

# --- 2) Definisci il form ---
with st.form("survey"):
    q1 = st.text_input("1) Dove lavori?")
    q2 = st.radio("2) Seleziona la tua opzione:", 
                  options=["Opzione A", "Opzione B", "Opzione C", "Opzione D"])
    submitted = st.form_submit_button("Invia")

if submitted:
    # --- 3) Leggi/esiste già responses.json? ---
    try:
        contents = repo.get_contents(file_path)
        data = json.loads(contents.decoded_content)
    except:
        data = []

    # --- 4) Aggiungi la risposta e fai commit ---
    data.append({"q1": q1, "q2": q2})
    updated = json.dumps(data, ensure_ascii=False, indent=2)
    if "contents" in locals():
        repo.update_file(file_path, 
                         "Aggiorna survey", 
                         updated, 
                         contents.sha)
    else:
        repo.create_file(file_path, 
                         "Crea responses.json", 
                         updated)

    st.success("Grazie! La tua risposta è stata registrata.")

# --- 5) Genera word cloud in tempo reale ---
# Leggi tutte le risposte
try:
    contents = repo.get_contents(file_path)
    data = json.loads(contents.decoded_content)
    # Conta frequenze per Q2
    freqs = {}
    for r in data:
        freqs[r["q2"]] = freqs.get(r["q2"], 0) + 1

    if freqs:
        wc = WordCloud(width=400, height=200).generate_from_frequencies(freqs)
        fig, ax = plt.subplots(figsize=(6,3))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        st.pyplot(fig)
    else:
        st.info("Nessuna risposta ancora per la word cloud.")
except Exception as e:
    st.warning("Word cloud non disponibile: " + str(e))
