import streamlit as st
from github import Github
import json
import matplotlib.pyplot as plt
import qrcode
import io
import plotly.express as px

# --- 1) Carica secrets ---
token = st.secrets["github_token"]
repo_name = st.secrets["repo_name"]
app_url = st.secrets["app_url"]  # es. "https://…streamlit.app"

# --- 2) Inizializza GitHub ---
g = Github(token)
repo = g.get_repo(repo_name)
fpath = "responses.json"

# --- 3) Leggi query params ---
params = st.query_params
admin_mode = params.get("admin", ["0"])[0] == "1"
survey_mode = params.get("survey", ["0"])[0] == "1"

# --- 4) QR PAGE (default) ---
if not admin_mode and not survey_mode:
    st.title("Accedi al Questionario")
    qr = qrcode.make(f"{app_url}?survey=1")
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)
    st.image(
        buf,
        caption="Scansiona per aprire il questionario",
        use_container_width=True
    )
    st.markdown(f"[Oppure clicca qui per aprire il form]({app_url}?survey=1)")
    st.info("Quando gli utenti scannerizzano il QR o cliccano, vedranno solo il form.")
    st.stop()

# --- 5) SURVEY PAGE (solo form) ---
if survey_mode and not admin_mode:
    st.title("Questionario")
    with st.form("survey"):
        q1 = st.text_input("1) Dove lavori?")
        q2 = st.radio(
            "2) Seleziona la tua opzione:",
            options=["Opzione A", "Opzione B", "Opzione C", "Opzione D"]
        )
        submitted = st.form_submit_button("Invia")
    if submitted:
        try:
            contents = repo.get_contents(fpath)
            data = json.loads(contents.decoded_content)
        except:
            data = []
        data.append({"q1": q1, "q2": q2})
        updated = json.dumps(data, ensure_ascii=False, indent=2)
        if "contents" in locals():
            repo.update_file(fpath, "Aggiorna survey", updated, contents.sha)
        else:
            repo.create_file(fpath, "Crea responses.json", updated)
        st.success("Grazie! La tua risposta è stata registrata.")
    st.stop()

# --- 6) ADMIN PAGE (dashboard) ---
st.title("Dashboard Risposte")
st.markdown(f"[Torna alla QR page]({app_url})")
st.write("---")

try:
    contents = repo.get_contents(fpath)
    data = json.loads(contents.decoded_content)
except:
    st.info("Ancora nessuna risposta.")
    st.stop()

# 6a) Risposte aperte Q1 come barplot con Plotly
open_resps = [r.get("q1", "").strip() for r in data if r.get("q1", "").strip()]
if open_resps:
    freqs_open = {}
    for resp in open_resps:
        freqs_open[resp] = freqs_open.get(resp, 0) + 1
    fig1 = px.bar(
        x=list(freqs_open.keys()),
        y=list(freqs_open.values()),
        labels={"x": "Dove lavori?", "y": "Numero di risposte"}
    )
    fig1.update_layout(xaxis_tickangle=45, title=None)
    st.subheader("Distribuzione delle risposte aperte")
    st.plotly_chart(fig1, use_container_width=True)
else:
    st.info("Nessuna risposta aperta per Q1.")

st.write("---")

# 6b) Word-cloud per Q2
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
    st.info("Nessuna risposta per la word-cloud.")
