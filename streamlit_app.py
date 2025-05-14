import streamlit as st
from github import Github
import json
import matplotlib.pyplot as plt
import plotly.express as px
from uuid import uuid4
from datetime import datetime
import qrcode
import io

# --- 1) Carica secrets ---
token     = st.secrets["github_token"]
repo_name = st.secrets["repo_name"]
app_url   = st.secrets["app_url"]  # es. "https://…streamlit.app"

# --- 2) Inizializza GitHub ---
g    = Github(token)
repo = g.get_repo(repo_name)

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
    st.markdown(f"[Oppure clicca qui per aprire il form]({app_url}?survey=1)")
    st.info("Quando gli utenti scannerizzano il QR o cliccano, vedranno solo il form.")
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
        # 1) Prepara il record
        record = {"q1": q1, "q2": q2}

        # 2) Genera filename unico in responses/
        ts    = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
        fname = f"responses/{ts}-{uuid4()}.json"

        # 3) Serializza e crea il file
        payload = json.dumps(record, ensure_ascii=False, indent=2)
        repo.create_file(fname, "Nuova risposta", payload)

        st.success("Grazie! La tua risposta è stata registrata.")

    st.stop()

# --- 6) ADMIN PAGE (dashboard) ---
st.title("Dashboard Risposte")
st.markdown(f"[Torna alla QR page]({app_url})")
st.write("---")

# 6a) Carica tutte le json in responses/
try:
    files = repo.get_contents("responses")
    data  = []
    for f in files:
        content = repo.get_contents(f.path)
        data.append(json.loads(content.decoded_content))
except:
    st.info("Ancora nessuna risposta.")
    st.stop()

# 6b) Grafico a barre per Q1 (risposte aperte)
open_resps = [r["q1"] for r in data if r.get("q1","").strip()]
if open_resps:
    # conta frequenze
    counts = {}
    for txt in open_resps:
        counts[txt] = counts.get(txt, 0) + 1
    # barplot con Plotly, senza titolo
    df1 = {
        "Risposta": list(counts.keys()),
        "Conteggio": list(counts.values())
    }
    fig1 = px.bar(df1, x="Risposta", y="Conteggio")
    fig1.update_layout(title_text="")  # rimuove il titolo
    st.plotly_chart(fig1, use_container_width=True)
else:
    st.info("Nessuna risposta aperta per Q1.")

st.write("---")

# 6b) Word-cloud per Q2 con palette personalizzata
import random
from wordcloud import WordCloud

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

# ricava le frequenze da tutti i record in data
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
    # NOTA: rimuovi o commenta qualsiasi st.subheader() qui se non vuoi un titolo
    st.pyplot(fig, use_container_width=True)
else:
    st.info("Nessuna risposta per la word-cloud.")
