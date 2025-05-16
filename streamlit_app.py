import streamlit as st
from github import Github, GithubException
import json
import random
from datetime import datetime
import time
import qrcode
import io
import base64
import matplotlib.pyplot as plt
import plotly.express as px
from uuid import uuid4
from wordcloud import WordCloud

# --- Configurazione pagina ---
st.set_page_config(page_title="Questionario AML", layout="wide")

# --- Inserimento CSS e HTML per top bar fissa e form styling ---
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
  [data-testid="stHeader"], [data-testid="stSidebar"] {
    background-color: #00338D !important;
  }
  /* Top bar personalizzata */
  .top_bar {
    position: fixed;
    top: 0; left: 0; width: 100vw; height: 100px;
    background-color: #00338D;
    display: flex; align-items: center; padding-left: 20px;
    z-index: 9999;
  }
  .top_bar img { height: 60px; }
  /* Spazio per il contenuto sotto la barra */
  [data-testid="stBlockContainer"] { padding-top: 100px; }
  /* Wrapper personalizzato per il form */
  .form-container {
    max-width: 900px !important;
    width: 90% !important;
    margin: 0 auto 40px auto;
  }
  /* Rimuove sfondo, bordo e box-shadow interno del form */
  .form-container form {
    background: none !important;
    border: none !important;
    box-shadow: none !important;
    width: 100% !important;
  }
  /* Allarga i singoli widget dentro il form */
  .form-container [data-testid="stRadio"],
  .form-container [data-testid="stMultiselect"] {
    max-width: 900px !important;
    width: 90% !important;
  }
</style>
"""
st.markdown(app_css, unsafe_allow_html=True)

# Disegna top bar con logo
if logo_b64:
    st.markdown(
        f"<div class='top_bar'><img src='data:image/png;base64,{logo_b64}' alt='Logo' /></div>",
        unsafe_allow_html=True
    )

# --- Carica secrets e inizializza GitHub ---
token     = st.secrets["github_token"]
repo_name = st.secrets["repo_name"]
app_url   = st.secrets["app_url"]
g = Github(token)
repo = g.get_repo(repo_name)

# Funzione di retry per GitHub

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

# --- Gestione query params ---
params      = st.query_params
admin_mode  = params.get("admin", ["0"])[0] == "1"
survey_mode = params.get("survey", ["0"])[0] == "1"

# --- Pagina QR ---
if not admin_mode and not survey_mode:
    st.title("Accedi al Questionario")
    qr = qrcode.make(f"{app_url}?survey=1")
    buf = io.BytesIO(); qr.save(buf, format="PNG"); buf.seek(0)
    st.image(buf, caption="Scansiona per aprire il questionario", use_container_width=True)
    st.markdown(f"[Oppure clicca qui per il form]({app_url}?survey=1)")
    st.info("Scannerizza o clicca.")
    st.stop()

# --- Survey Page ---
if survey_mode and not admin_mode:
    st.title("Questionario AML")
    st.markdown("<div class='form-container'>", unsafe_allow_html=True)
    with st.form("survey"):
        st.write("## 1) Si è già provveduto a nominare l’AML Board Member?")
        bm_yes_no = st.radio("", ["Sì", "No"], horizontal=True)

        st.write("## 2) Quale soggetto è stato nominato (o si prevede di nominare) come AML Board Member?")
        bm_nominee = st.radio(
            "", [
                "Amministratore Delegato",
                "Altro membro esecutivo del Consiglio di Amministrazione",
                "Membro non esecutivo del Consiglio di Amministrazione (che diventa esecutivo a seguito della nomina)",
                "Altro (specificare nelle note)",
                "Non ancora definito"
            ]
        )
        bm_notes = None
        if bm_nominee == "Altro (specificare nelle note)":
            bm_notes = st.text_area("Specifica qui nelle note:")

        st.write("## 3) Principali preoccupazioni ed impatti - AML Package (max 3)")
        impacts = st.multiselect(
            "", [
                "Approccio della supervisione (nuove modalità di interazione)",
                "Poco tempo per conformarsi",
                "Implementazioni sui sistemi informatici",
                "Impatti sull’AML Governance",
                "Impatti su metodologie e modelli",
                "Impatti sui processi di Know Your Customer",
                "Altro (specificare nelle note)",
                "Nessun impatto identificato al momento",
                "Incertezza normativa e legame con locale",
                "Misure per High-net-worth individuals",
                "Estensione definizione PEPs",
                "Requisiti titolarità effettiva",
                "Aggiornamento adeguata verifica",
                "Modifiche Paesi Terzi Alto Rischio",
                "Targeted Financial sanctions",
                "Limite al contante",
                "Outsourcing",
                "Misure amministrative e sanzioni",
                "Impatti protezione dati",
                "Sottoposizione normativa AML"
            ], max_selections=3
        )

        submitted = st.form_submit_button("Invia")
        if submitted:
            st.info("Attendere…")
            record = {"bm_yes_no": bm_yes_no, "bm_nominee": bm_nominee, "bm_notes": bm_notes, "impacts": impacts}
            ts = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
            fname = f"responses/{ts}-{uuid4()}.json"
            payload = json.dumps(record, ensure_ascii=False, indent=2)
            try:
                create_file_with_retry(repo, fname, "Nuova risposta AML", payload)
                st.success("Risposte inviate")
            except GithubException:
                st.error("Errore nell'invio. Riprova più tardi.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- Admin Dashboard ---
st.title("Dashboard Risposte AML")
st.markdown(f"[Torna alla QR page]({app_url})")
st.write("---")

try:
    files = repo.get_contents("responses")
    data = [json.loads(repo.get_contents(f.path).decoded_content) for f in files]
except GithubException:
    st.info("Ancora nessuna risposta.")
    st.stop()

palette = ["#00338D", "#1E49E2", "#0C233C", "#ACEAFF", "#00B8F5", "#7210EA", "#FD349C"]

def random_color(word, font_size, position, orientation, random_state=None, **kwargs):
    return random.choice(palette)

# Istogrammi domande 1 e 2
for q_key, title, labels in [
    ("bm_yes_no", "1) AML Board Member nominato?", "Risposta"),
    ("bm_nominee", "2) Chi come AML Board Member?", "Soggetto")
]:
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
        st.info(f"Nessuna risposta per la domanda {q_key}.")
    st.write("---")

# Note extra per 'Altro'
notes_list = [r.get("bm_notes") for r in data if r.get("bm_notes")]
if notes_list:
    st.subheader("Note AML Board Member")
    for note in notes_list:
        st.write(f"- {note}")
    st.write("---")

# WordCloud Q3
freqs = {}
for r in data:
    for choice in r.get("impacts", []):
        freqs[choice] = freqs.get(choice, 0) + 1
if freqs:
    wc = WordCloud(width=800, height=400, background_color="white", color_func=random_color)
    wc.generate_from_frequencies(freqs)
    fig, ax = plt.subplots(figsize=(8, 4), dpi=200)
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    st.subheader("Principali preoccupazioni ed impatti - AML Package")
    st.pyplot(fig, use_container_width=True)
else:
    st.info("Nessuna risposta per le preoccupazioni/impatti.")
