import streamlit as st
from github import Github, GithubException
import json
import random
from datetime import datetime
import qrcode
import io
import base64
import time
import matplotlib.pyplot as plt
import plotly.express as px
from uuid import uuid4
from wordcloud import WordCloud

# --- Inserimento CSS e HTML per top bar fissa ---
# Carica logo e convertilo in base64
try:
    with open("assets/immagine.png", "rb") as img_file:
        logo_data = img_file.read()
    logo_b64 = base64.b64encode(logo_data).decode()
except FileNotFoundError:
    logo_b64 = None

app_css = """
<style>
  /* Nascondi header e sidebar default */
  header { visibility: hidden; }
  [data-testid="stHeader"],
  [data-testid="stSidebar"] {
    background-color: #00338D !important;
  }
  /* Variabili di tema */
  :root {
    --primary-color: #00338D;
    --secondary-background-color: #00338D;
    --primary-background-color: #00338D;
  }
  /* Top bar personalizzata */
  .top_bar {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100px;
    background-color: #00338D;
    display: flex;
    align-items: center;
    padding-left: 20px;
    z-index: 9999;
  }
  .top_bar img {
    height: 60px;
  }
  /* Spazio per il contenuto sotto la barra */
  [data-testid="stBlockContainer"] {
    padding-top: 100px;
  }
</style>
"""
st.markdown(app_css, unsafe_allow_html=True)

# Disegna top_bar con logo e titolo
if logo_b64:
    top_html = f"""
<div class="top_bar">
  <img src="data:image/png;base64,{logo_b64}" alt="Logo" />
</div>
"""
    st.markdown(top_html, unsafe_allow_html=True)

# --- 1) Carica secrets ---
token     = st.secrets["github_token"]
repo_name = st.secrets["repo_name"]
app_url   = st.secrets["app_url"]  # es. "https://…streamlit.app"

# --- 2) Inizializza GitHub ---
g = Github(token)
repo = g.get_repo(repo_name)

# --- Helper: create_file con retry per conflitti 409/422 ---
def create_file_with_retry(repo, path, message, content, max_tries=3, backoff=0.5):
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

# --- 4) Pagina QR ---
if not admin_mode and not survey_mode:
    st.title("Accedi al Questionario")
    qr = qrcode.make(f"{app_url}?survey=1")
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)
    st.image(buf, caption="Scansiona per aprire il questionario", use_container_width=True)
    st.markdown(f"[Oppure clicca qui per il form]({app_url}?survey=1)")
    st.info("Scannerizza o clicca.")
    st.stop()

# --- 5) Survey Page ---
if survey_mode and not admin_mode:
    st.title("Questionario")
    with st.form("survey"):
        q1 = st.radio("1) È stato nominato l'esponente responsabile antiriciclaggio?", ["Sì", "No"])
        q2 = st.radio("2) Se avete risposto Sì, chi avete nominato?", ["Amministratore Delegato", "Membro del CdA non esecutivo", "Altro"])
        q3 = st.multiselect(
            "3) Quali, tra i seguenti, ritieni possano essere più impattanti sull'operatività dell'intermediario? (max 3)",
            ["Governance dei gruppi", "Controllo costante", "Adeguata verifica", "Nuovi schemi di segnalazione alla UIF", "Altro"],
            max_selections=3
        )
        submitted = st.form_submit_button("Invia")
    if submitted:
        st.info("Attendere…")
        record = {"q1": q1, "q2": q2, "q3": q3}
        ts = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
        fname = f"responses/{ts}-{uuid4()}.json"
        payload = json.dumps(record, ensure_ascii=False, indent=2)
        try:
            create_file_with_retry(repo, fname, "Nuova risposta", payload)
            st.success("Risposte inviate")
        except GithubException:
            st.error("Errore nell'invio. Riprova più tardi.")
    st.stop()

# --- 6) Admin Dashboard ---
st.title("Dashboard Risposte")
st.markdown(f"[Torna alla QR page]({app_url})")
st.write("---")

# Carica risposte
try:
    files = repo.get_contents("responses")
    data = [json.loads(repo.get_contents(f.path).decoded_content) for f in files]
except GithubException:
    st.info("Ancora nessuna risposta.")
    st.stop()

# Palette wordcloud
palette = ["#00338D", "#1E49E2", "#0C233C", "#ACEAFF", "#00B8F5", "#7210EA", "#FD349C"]

def random_color(word, font_size, position, orientation, random_state=None, **kwargs):
    return random.choice(palette)

# Istogrammi Q1 e Q2
for idx, (q_key, title, labels) in enumerate([
    ("q1", "1) Esponente responsabile nominato?", "Risposta"),
    ("q2", "2) Chi avete nominato?", "Chi nominato")
]):
    counts = {}
    for r in data:
        ans = r.get(q_key, "").strip()
        if ans:
            counts[ans] = counts.get(ans, 0) + 1
    if counts:
        df = {labels: list(counts.keys()), "Conteggio": list(counts.values())}
        fig = px.bar(df, x=labels, y="Conteggio")
        st.subheader(title)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(f"Nessuna risposta per la Domanda {q_key[-1]}.")
    st.write("---")

# Wordcloud Q3
freqs_q3 = {}
for r in data:
    for choice in r.get("q3", []):
        freqs_q3[choice] = freqs_q3.get(choice, 0) + 1
if freqs_q3:
    wc = WordCloud(width=800, height=400, background_color="white", color_func=random_color)
    wc.generate_from_frequencies(freqs_q3)
    fig, ax = plt.subplots(figsize=(8, 4), dpi=200)
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    st.subheader("3) Punti più impattanti (Q3)")
    st.pyplot(fig, use_container_width=True)
else:
    st.info("Nessuna risposta per la Domanda 3.")
