import streamlit as st
from github import Github, GithubException
import json
import matplotlib.pyplot as plt
import plotly.express as px
from uuid import uuid4
from datetime import datetime
import qrcode
import io
import random
from wordcloud import WordCloud
import time

# --- 1) Carica secrets ---
token     = st.secrets["github_token"]
repo_name = st.secrets["repo_name"]
app_url   = st.secrets["app_url"]  # es. "https://…streamlit.app"

# --- 2) Inizializza GitHub ---
g    = Github(token)
repo = g.get_repo(repo_name)

# --- Helper: create_file con retry per evitare conflitti 409/422 ---
def create_file_with_retry(repo, path, message, content,
                           max_tries=3, backoff=0.5):
    for attempt in range(1, max_tries+1):
        try:
            return repo.create_file(path, message, content)
        except GithubException as e:
            if e.status in (409, 422) and attempt < max_tries:
                time.sleep(backoff * attempt)
                continue
            else:
                # rilancia solo alla fine, non in ogni retry
                raise

# --- 3) Leggi query params ---
params      = st.query_params
admin_mode  = params.get("admin", ["0"])[0] == "1"
survey_mode = params.get("survey", ["0"])[0] == "1"

# --- 4) QR PAGE (default) ---
if not admin_mode and not survey_mode:
    st.title("Accedi al Questionario")
    qr = qrcode.make(f"{app_url}?survey=1")
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)
    st.image(buf,
             caption="Scansiona per aprire il questionario",
             use_container_width=True)
    st.markdown(f"[Oppure clicca qui per il form]({app_url}?survey=1)")
    st.info("Scannerizza o clicca: vedranno solo il form.")
    st.stop()

# --- 5) SURVEY PAGE (solo form) ---
if survey_mode and not admin_mode:
    st.title("Questionario")

    with st.form("survey"):
        q1 = st.text_input("1) Dove lavori?")
        q2 = st.radio("2) Seleziona la tua opzione:",
                      options=["Opzione A", "Opzione B", "Opzione C", "Opzione D"])
        submitted = st.form_submit_button("Invia")

    if submitted:
        # Mostra subito il messaggio di attesa
        st.info("Attendere…")

        # Prepara record e filename unico
        record = {"q1": q1, "q2": q2}
        ts     = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
        fname  = f"responses/{ts}-{uuid4()}.json"
        payload = json.dumps(record, ensure_ascii=False, indent=2)

        # Crea il file con retry senza errori intermedi
        try:
            create_file_with_retry(repo, fname, "Nuova risposta", payload)
            st.success("Risposte inviate")
        except GithubException:
            # Se anche dopo i retry fallisce, avvisa l’utente
            st.error("Non è stato possibile inviare la risposta. Riprova più tardi.")

    st.stop()

# --- 6) ADMIN DASHBOARD ---
st.title("Dashboard Risposte")
st.markdown(f"[Torna alla QR page]({app_url})")
st.write("---")

# Carica tutti i file JSON nella cartella responses/
try:
    files = repo.get_contents("responses")
    data  = [json.loads(repo.get_contents(f.path).decoded_content) for f in files]
except:
    st.info("Ancora nessuna risposta.")
    st.stop()

# 6a) Bar chart (Plotly) per Q1
open_resps = [r["q1"] for r in data if r.get("q1","").strip()]
if open_resps:
    counts = {}
    for txt in open_resps:
        counts[txt] = counts.get(txt, 0) + 1
    df1 = {"Risposta": list(counts.keys()), "Conteggio": list(counts.values())}
    fig1 = px.bar(df1, x="Risposta", y="Conteggio")
    fig1.update_layout(title_text="")  # rimuove il titolo
    st.plotly_chart(fig1, use_container_width=True)
else:
    st.info("Nessuna risposta aperta per Q1.")

st.write("---")

# 6b) Word-cloud per Q2 con palette personalizzata
palette = [
    "#00338D",  # KPMG blue
    "#1E49E2",  # Cobalt Blue
    "#0C233C",  # Spectrum Blue
    "#ACEAFF",  # Light Blue
    "#00B8F5",  # Pacific Blue
    "#7210EA",  # Purple
    "#FD349C"   # Pink
]

def random_color(word, font_size, position, orientation, random_state=None, **kwargs):
    return random.choice(palette)

freqs = {}
for r in data:
    choice = r.get("q2", "").strip()
    if choice:
        freqs[choice] = freqs.get(choice, 0) + 1

if freqs:
    wc = WordCloud(
        width=800,
        height=400,
        background_color="white",
        color_func=random_color
    ).generate_from_frequencies(freqs)

    fig, ax = plt.subplots(figsize=(8, 4), dpi=200)
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    st.subheader("Distribuzione delle risposte (Q2)")
    st.pyplot(fig, use_container_width=True)
else:
    st.info("Nessuna risposta per la word-cloud.")

# Domanda 1) è stato nominato l'esponente responsabile antiric? risposta: sn -> istogramma
# Domanda 2) Chi avete nominato? risposta : amm del, membro del consiglio di amministrazione non esecutivo,altro -> istogramma
# Domanda 3) Con riferimento ai punti sottostanti quali ritieni che possano essere pi impattanti sull'operatività dell'intermediario?  risposte:Governance dei gruppi, controllo costante, adeguata verifica, nuovi schemi di segnalazione alla uif, altr (max tre) -> wordcloud