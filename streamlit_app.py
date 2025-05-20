# streamlit_app.py
import streamlit as st
from datetime import datetime
from uuid import uuid4
import base64
import io
import qrcode
import random
from collections import Counter
import plotly.express as px
from wordcloud import WordCloud
import json
from github import Github, GithubException
import time
from db import SessionLocal, Response  # assicurati di importare il modello
# ----------------------------------------------------------------
# Database setup
# ----------------------------------------------------------------
import db
from db import SessionLocal, Response

# ----------------------------------------------------------------
# 1) Page config and DB init
# ----------------------------------------------------------------
st.set_page_config(
    page_title="EU AML Package",
    layout="wide"
)
# Initialize SQLite database (creates file and tables if needed)
db.init_db()

token     = st.secrets["github_token"]
repo_name = st.secrets["repo_name"]
app_url   = st.secrets["app_url"]
g = Github(token)
repo = g.get_repo(repo_name)

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

# ----------------------------------------------------------------
# 2) Read query params
# ----------------------------------------------------------------
params      = st.query_params
survey_mode = params.get("survey", ["0"])[0] == "1"
admin_mode  = params.get("admin",  ["0"])[0] == "1"

# ----------------------------------------------------------------
# 3) CSS for QR landing page
# ----------------------------------------------------------------
if not survey_mode and not admin_mode:
    st.markdown(
        """
        <style>
          [data-testid="stAppViewContainer"] [data-testid="stBlockContainer"] {
            max-width:700px !important;
            margin-left:auto !important;
            margin-right:auto !important;
          }
        </style>
        """,
        unsafe_allow_html=True
    )

# ----------------------------------------------------------------
# 4) Common CSS (top bar, form styles)
# ----------------------------------------------------------------
app_css = f"""
<style>
  /* Hide default header and sidebar */
  header {{ visibility: hidden; }}
  [data-testid="stHeader"], [data-testid="stSidebar"] {{ background-color: #00338D !important; }}

  /* Top bar */
  .top_bar {{
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
  }}
  .top_bar img {{ height: 60px; }}
  .logo-acora {{ height: 40px !important; margin-left:20px; }}

  /* Space below top bar */
  [data-testid="stBlockContainer"] {{ padding-top: 100px; }}

  /* Survey form styles */
  .form-container {{
    max-width: 900px !important;
    width: 90% !important;
    margin: 0 auto 40px auto;
  }}
  .form-container form[role="form"],
  .form-container form[role="form"] > div,
  .form-container form[role="form"] > div > div {{
    background: none !important;
    border: none !important;
    box-shadow: none !important;
  }}
  .form-container [data-testid="stRadio"],
  .form-container [data-testid="stMultiselect"] {{
    max-width: 900px !important;
    width: 90% !important;
  }}
</style>
"""
st.markdown(app_css, unsafe_allow_html=True)

# ----------------------------------------------------------------
# 5) Top bar logos
# ----------------------------------------------------------------
logo_b64 = None
logo2_b64 = None
for asset, var_name in [("assets/immagine.png", "logo_b64"),
                        ("assets/acorà logo.png", "logo2_b64")]:
    try:
        with open(asset, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode()
        if var_name == "logo_b64":
            logo_b64 = b64
        else:
            logo2_b64 = b64
    except FileNotFoundError:
        pass

if logo_b64 or logo2_b64:
    imgs_html = ""
    if logo_b64:
        imgs_html += f"<img src='data:image/png;base64,{logo_b64}' alt='Logo'/>"
    if logo2_b64:
        imgs_html += f"<img class='logo-acora' src='data:image/png;base64,{logo2_b64}' alt='Acorà Logo'/>"
    st.markdown(f"<div class='top_bar'>{imgs_html}</div>", unsafe_allow_html=True)

# ----------------------------------------------------------------
# 6) QR Landing Page
# ----------------------------------------------------------------
app_url = st.secrets.get("app_url", "")
if not survey_mode and not admin_mode:
    st.title("EU AML Package")
    survey_url = f"{app_url}?survey=1"
    # Generate QR
    qr = qrcode.make(survey_url)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.image(buf, caption="Scansiona per aprire il questionario", width=800)
    st.markdown(f"[Oppure clicca qui per il form]({survey_url})")
    st.info(survey_url)
    st.stop()

# ----------------------------------------------------------------
# 7) Survey Page
# ----------------------------------------------------------------
from db import SessionLocal, Response
import json

if survey_mode and not admin_mode:
    st.title("EU AML Package")
    st.markdown("<div class='form-container'>", unsafe_allow_html=True)
    with st.form("survey"):
        # — Domanda 1 —
        st.write("## 1) Si è già provveduto a nominare l’AML Board Member?")
        bm_yes_no = st.radio(
            " ",
            ["Sì", "No"],
            horizontal=True,
            label_visibility="collapsed",
            index=None
        )

        # — Domanda 2 —
        st.write("## 2) Quale soggetto è stato nominato come AML Board Member?")
        bm_nominee = st.radio(
            " ",
            [
                "Amministratore Delegato",
                "Altro membro esecutivo del Consiglio di Amministrazione",
                "Membro non esecutivo del Consiglio di Amministrazione (che diventa esecutivo a seguito della nomina)",
                "Non ancora definito"
            ],
            label_visibility="collapsed",
            index=None
        )


        # — Domanda 3 —
        st.write("## 3) Principali preoccupazioni ed impatti - AML Package (max 3)")
        impacts = st.multiselect(
            " ",
            [
                "Approccio della supervisione (nuove modalità di interazione)",
                "Poco tempo per conformarsi",
                "Implementazioni sui sistemi informatici",
                "Impatti sull’AML Governance",
                "Impatti su metodologie e modelli",
                "Impatti sui processi di Know Your Customer",
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
            ],
            max_selections=3,
            label_visibility="collapsed"
        )

        if st.form_submit_button("Invia"):
            st.info("Attendere…")
            record = {
                "bm_yes_no": bm_yes_no,
                "bm_nominee": bm_nominee,
                "impacts": impacts
            }
            ts = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
            fname = f"responses/{ts}-{uuid4()}.json"
            payload = json.dumps(record, ensure_ascii=False, indent=2)

            try:
                # 1) Pusha su GitHub
                create_file_with_retry(repo, fname, "Nuova risposta EU AML Package", payload)

                # 2) Salva in SQLite (campo JSON nativo)
                session = SessionLocal()
                new_resp = Response(
                    bm_yes_no=bm_yes_no,
                    bm_nominee=bm_nominee,
                    impacts=impacts          # lista Python, no json.dumps
                )
                session.add(new_resp)
                session.commit()
                session.close()

                st.success("Risposte inviate e registrate")
            except GithubException:
                st.error("Errore nell'invio su GitHub. Riprova più tardi.")
            except Exception as e:
                st.error(f"Errore nel salvataggio nel DB: {e}")

    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ----------------------------------------------------------------
# 8) Admin Dashboard
# ----------------------------------------------------------------
st.title("EU AML Package - Admin")
st.markdown(f"[Torna alla QR page]({app_url})")
st.write("---")

# Funzione senza caching

def load_responses():
    session = SessionLocal()
    try:
        rows = session.query(Response).order_by(Response.timestamp).all()
        return [
             {"bm_yes_no": r.bm_yes_no,
              "bm_nominee": r.bm_nominee,
              "impacts":   r.impacts}
            for r in rows
         ]
    finally:
         session.close()

# Load data
data = load_responses()
if not data:
    st.info("Ancora nessuna risposta.")
    st.stop()

# ----------------------------------------------------------------
# 9) Charts for Q1 & Q2
# ----------------------------------------------------------------
for q_key, title, label in [
    ("bm_yes_no", "1) EU AML Package - AML Board Member nominato?", "Risposta"),
    ("bm_nominee", "2) EU AML Package - Chi come AML Board Member?", "Soggetto")
]:
    counts = Counter(r[q_key] for r in data if r[q_key])
    if counts:
        df = {label: list(counts.keys()), "Conteggio": list(counts.values())}
        fig = px.bar(df, x=label, y="Conteggio")
        st.subheader(title)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(f"Nessuna risposta per la domanda {q_key}.")
    st.write("---")



# ----------------------------------------------------------------
# 10) WordCloud for Q3
# ----------------------------------------------------------------
freqs = Counter(choice for r in data for choice in r.get("impacts", []))
if freqs:
    palette = ["#00338D", "#1E49E2", "#0C233C", "#ACEAFF", "#00B8F5", "#7210EA", "#FD349C"]
    def random_color(word, font_size, position, orientation, random_state=None, **kwargs):
        return random.choice(palette)

    wc = WordCloud(
        width=1600,
        height=800,
        scale=4,
        background_color="white",
        color_func=random_color,
        collocations=False,
        font_path="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        max_words=100
    ).generate_from_frequencies(freqs)

    st.subheader("3) EU AML Package - Principali preoccupazioni ed impatti")
    st.image(wc.to_image(), use_container_width =True)
else:
    st.info("Nessuna risposta per le preoccupazioni/impatti.")
