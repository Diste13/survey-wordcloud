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
app_url   = st.secrets["app_url"]   # es. "https://…streamlit.app"

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
        # Domanda 1
        q1 = st.radio(
            "1) È stato nominato l'esponente responsabile antiriciclaggio?",
            options=["Sì", "No"]
        )
        # Domanda 2
        q2 = st.radio(
            "2) Se avete risposto Sì, chi avete nominato?",
            options=[
                "Amministratore Delegato",
                "Membro del CdA non esecutivo",
                "Altro"
            ]
        )
        # Domanda 3
        q3 = st.multiselect(
            "3) Quali, tra i seguenti, ritieni possano essere più impattanti sull'operatività dell'intermediario? (max 3)",
            options=[
                "Governance dei gruppi",
                "Controllo costante",
                "Adeguata verifica",
                "Nuovi schemi di segnalazione alla UIF",
                "Altro"
            ],
            max_selections=3
        )
        submitted = st.form_submit_button("Invia")

    if submitted:
        st.info("Attendere…")
        record  = {"q1": q1, "q2": q2, "q3": q3}
        ts      = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
        fname   = f"responses/{ts}-{uuid4()}.json"
        payload = json.dumps(record, ensure_ascii=False, indent=2)

        try:
            create_file_with_retry(repo, fname, "Nuova risposta", payload)
            st.success("Risposte inviate")
        except GithubException:
            st.error("Non è stato possibile inviare la risposta. Riprova più tardi.")

    st.stop()

# --- 6) ADMIN DASHBOARD ---
st.title("Dashboard Risposte")
st.markdown(f"[Torna alla QR page]({app_url})")
st.write("---")

# Carica tutti i file JSON in responses/
try:
    files = repo.get_contents("responses")
    data  = [json.loads(repo.get_contents(f.path).decoded_content) for f in files]
except GithubException:
    st.info("Ancora nessuna risposta.")
    st.stop()

# Palette custom per wordcloud
palette = [
    "#00338D", "#1E49E2", "#0C233C",
    "#ACEAFF", "#00B8F5", "#7210EA", "#FD349C"
]
def random_color(word, font_size, position, orientation, random_state=None, **kwargs):
    return random.choice(palette)

# --- 6a) Istogramma Q1 ---
counts_q1 = {}
for r in data:
    ans = r.get("q1", "").strip()
    if ans:
        counts_q1[ans] = counts_q1.get(ans, 0) + 1

if counts_q1:
    df1 = {"Risposta": list(counts_q1.keys()), "Conteggio": list(counts_q1.values())}
    fig1 = px.bar(df1, x="Risposta", y="Conteggio")
    st.subheader("1) Esponente responsabile nominato?")
    st.plotly_chart(fig1, use_container_width=True)
else:
    st.info("Nessuna risposta per la Domanda 1.")

st.write("---")

# --- 6b) Istogramma Q2 ---
counts_q2 = {}
for r in data:
    ans = r.get("q2", "").strip()
    if ans:
        counts_q2[ans] = counts_q2.get(ans, 0) + 1

if counts_q2:
    df2 = {"Chi nominato": list(counts_q2.keys()), "Conteggio": list(counts_q2.values())}
    fig2 = px.bar(df2, x="Chi nominato", y="Conteggio")
    st.subheader("2) Chi avete nominato?")
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("Nessuna risposta per la Domanda 2.")

st.write("---")

# --- 6c) Word-cloud Q3 ---
freqs_q3 = {}
for r in data:
    for choice in r.get("q3", []):
        freqs_q3[choice] = freqs_q3.get(choice, 0) + 1

if freqs_q3:
    wc = WordCloud(
        width=800, height=400,
        background_color="white",
        color_func=random_color
    ).generate_from_frequencies(freqs_q3)

    fig, ax = plt.subplots(figsize=(8, 4), dpi=200)
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    st.subheader("3) Punti più impattanti (Q3)")
    st.pyplot(fig, use_container_width=True)
else:
    st.info("Nessuna risposta per la Domanda 3.")
