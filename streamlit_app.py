import streamlit as st
from github import Github
import json
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import qrcode
from PIL import Image
import io

# --- 1) Carica secrets di Streamlit ---
# Nel tuo GitHub repo le secret key (da configurare in Settings > Secrets su Streamlit Cloud) sono:
# github_token, repo_name, app_url
token     = st.secrets["github_token"]
repo_name = st.secrets["repo_name"]
app_url   = st.secrets["app_url"]

# --- 2) Inizializza client GitHub ---
g    = Github(token)
repo = g.get_repo(repo_name)
file_path = "responses.json"

# --- 3) Mostra QR code e link al form ---
qr = qrcode.make(app_url)
buf = io.BytesIO()
qr.save(buf, format="PNG")
buf.seek(0)
st.image(buf, caption="Scansiona per aprire il questionario", use_column_width=True)
st.markdown(f"[Oppure clicca qui per aprire il form]({app_url})")
st.write("---")

# --- 4) Definisci il form ---
with st.form("survey"):
    q1 = st.text_input("1) Dove lavori?")
    q2 = st.radio("2) Seleziona la tua opzione:",
                  options=["Opzione A", "Opzione B", "Opzione C", "Opzione D"])
    submitted = st.form_submit_button("Invia")

if submitted:
    # --- 5) Leggi o crea responses.json ---
    try:
        contents = repo.get_contents(file_path)
        data = json.loads(contents.decoded_content)
    except:
        data = []

    # --- 6) Aggiungi la risposta e fai commit ---
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

# --- 7) Recupera tutte le risposte per visualizzare risultati in tempo reale ---
try:
    contents = repo.get_contents(file_path)
    data = json.loads(contents.decoded_content)

    # 7a) Risposte aperte Q1
    open_resps = [r["q1"] for r in data if r.get("q1", "").strip()]
    if open_resps:
        st.subheader("Risposte aperte: Dove lavori?")
        st.write("\n".join(f"- {txt}" for txt in open_resps))
    else:
        st.info("Ancora nessuna risposta aperta per la Q1.")

    st.write("---")

    # 7b) Word cloud per Q2
    freqs = {}
    for r in data:
        freqs[r["q2"]] = freqs.get(r["q2"], 0) + 1

    if freqs:
        wc = WordCloud(width=400, height=200).generate_from_frequencies(freqs)
        fig, ax = plt.subplots(figsize=(6,3))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        st.subheader("Distribuzione delle risposte (Q2)")
        st.pyplot(fig)
    else:
        st.info("Nessuna risposta ancora per la word cloud.")
except Exception as e:
    st.warning("Dati non disponibili: " + str(e))
