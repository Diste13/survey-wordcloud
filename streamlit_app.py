# streamlit_app.py
import os
import time
import base64
import io
import json
from uuid import uuid4
from datetime import datetime
from collections import Counter
import random

import streamlit as st
import qrcode
import plotly.express as px
from wordcloud import WordCloud
from github import Github, GithubException

from db import init_db, SessionLocal, Response

# ----------------------------------------------------------------
# 1) Page config and DB init
# ----------------------------------------------------------------

st.set_page_config(
    page_title="EU AML Package",
    layout="wide"
)
init_db()

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
        """, unsafe_allow_html=True
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
if not survey_mode and not admin_mode:
    st.title("EU AML Package")
    survey_url = f"{app_url}?survey=1"
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
if survey_mode and not admin_mode:
    st.title("EU AML Package")
    st.markdown("<div class='form-container'>", unsafe_allow_html=True)
    with st.form("survey"):
        # Sezione 01
        st.write("## 01. Adeguamento ad EU AML Package")
        gap_analysis = st.radio(
            "1. È stata già avviata una gap analysis su EU AML Package?",
            ["Sì", "No"], horizontal=True, index=None, label_visibility="collapsed"
        )
        board_inform = st.radio(
            "2. L’organo amministrativo è stato già coinvolto il Consiglio di Amministrazione per informarlo dell'avvio dell’AML Package e delle imminenti novità normative in materia?",
            ["Sì", "No"], horizontal=True, index=None, label_visibility="collapsed"
        )
        budget = st.radio(
            "3. È stato già stanziato del budget dedicato alle attività di adeguamento all’EU AML Package?",
            ["Sì", "No"], horizontal=True, index=None, label_visibility="collapsed"
        )
        adeguamento_specifico = st.radio(
            "4. Avete già avviato attività di adeguamento su requisiti specifici definiti dell’EU AML Package?",
            ["Sì", "No"], horizontal=True, index=None, label_visibility="collapsed"
        )

        # Sezione 02
        st.write("## 02. Principali impatti attesi da EU AML Package")
        impacts = st.multiselect(
            "1. Quali sono le principali preoccupazioni ed impatti attesi dal nuovo quadro normativo che verrà definito nel contesto dell’EU AML Package (selezionare fino a 3 opzioni)?",
            [
                "Supervisione diretta", "Tempistiche di adeguamento", "Complessità del quadro normativo",
                "Implementazioni informatiche", "AML Governance", "Risk assessment", "Data model",
                "Know your customer", "Transaction monitoring", "Targeted Financial sanctions",
                "Paesi terzi ad alto rischio", "Requisiti sulla titolarità effettiva",
                "Protezione e condivisione dei dati", "Outsourcing", "Misure amministrative e sanzioni",
                "Nessun impatto identificato al momento"
            ],
            max_selections=3,
            label_visibility="collapsed"
        )

        # Sezione 03
        st.write("## 03. Nuova governance AML")
        bm_yes_no = st.radio(
            "1. Si è già provveduto a nominare l’AML Board Member?",
            ["Sì", "No"], horizontal=True, index=None, label_visibility="collapsed"
        )
        bm_nominee = st.radio(
            "2. Quale soggetto è stato nominato (o si prevede di nominare) come AML Board Member?",
            [
                "Amministratore Delegato",
                "Altro membro esecutivo del Consiglio di Amministrazione",
                "Membro non esecutivo del Consiglio di Amministrazione (che diventa esecutivo a seguito della nomina)",
                "Non ancora definito"
            ],
            index=None, label_visibility="collapsed"
        )

        if st.form_submit_button("Invia"):
            st.info("Attendere…")
            record = {
                "gap_analysis": gap_analysis,
                "board_inform": board_inform,
                "budget": budget,
                "adeguamento_specifico": adeguamento_specifico,
                "impacts": impacts,
                "bm_yes_no": bm_yes_no,
                "bm_nominee": bm_nominee
            }
            ts = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
            fname = f"responses/{ts}-{uuid4()}.json"
            payload = json.dumps(record, ensure_ascii=False, indent=2)

            try:
                create_file_with_retry(repo, fname, "Nuova risposta EU AML Package", payload)
                session = SessionLocal()
                new_resp = Response(
                    gap_analysis=gap_analysis,
                    board_inform=board_inform,
                    budget=budget,
                    adeguamento_specifico=adeguamento_specifico,
                    impacts=impacts,
                    bm_yes_no=bm_yes_no,
                    bm_nominee=bm_nominee
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

def load_responses():
    session = SessionLocal()
    try:
        rows = session.query(Response).order_by(Response.timestamp).all()
        return [
            {
                "gap_analysis": r.gap_analysis,
                "board_inform": r.board_inform,
                "budget": r.budget,
                "adeguamento_specifico": r.adeguamento_specifico,
                "impacts": r.impacts,
                "bm_yes_no": r.bm_yes_no,
                "bm_nominee": r.bm_nominee
            }
            for r in rows
        ]
    finally:
        session.close()

responses = load_responses()
if not responses:
    st.info("Ancora nessuna risposta.")
    st.stop()

# Definizione delle sezioni e delle domande
sections = {
    "01. Adeguamento ad EU AML Package": {
        "yesno": [
            ("gap_analysis", "1. È stata già avviata una gap analysis su EU AML Package?"),
            ("board_inform", "2. L’organo amministrativo è stato già coinvolto il Consiglio di Amministrazione per informarlo dell'avvio dell’AML Package e delle imminenti novità normative in materia?"),
            ("budget", "3. È stato già stanziato del budget dedicato alle attività di adeguamento all’EU AML Package?"),
            ("adeguamento_specifico", "4. Avete già avviato attività di adeguamento su requisiti specifici definiti dell’EU AML Package?")
        ]
    },
    "02. Principali impatti attesi da EU AML Package": {
        "multiselect": [
            ("impacts", "1. Quali sono le principali preoccupazioni ed impatti attesi dal nuovo quadro normativo? (selezionare fino a 3 opzioni)")
        ]
    },
    "03. Nuova governance AML": {
        "yesno": [
            ("bm_yes_no", "1. Si è già provveduto a nominare l’AML Board Member?")
        ],
        "categorical": [
            ("bm_nominee", "2. Quale soggetto è stato nominato come AML Board Member?")
        ]
    }
}

# Rendering dashboard per sezione
for section_title, content in sections.items():
    st.header(section_title)

    # Sì/No questions
    for key, question in content.get("yesno", []):
        counts = Counter(r.get(key) for r in responses if r.get(key) is not None)
        if counts:
            df = {"Risposta": list(counts.keys()), "Conteggio": list(counts.values())}
            fig = px.treemap(df, path=[px.Constant(question), "Risposta"], values="Conteggio")
            fig.update_layout(margin=dict(t=40, l=25, r=25, b=25))
            st.subheader(question)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Nessuna risposta per '{question}'.")
        st.write("---")

    # Multi‐select question (WordCloud)
    for key, question in content.get("multiselect", []):
        freqs = Counter(choice for r in responses for choice in r.get(key, []))
        if freqs:
            st.subheader(question)
            palette = ["#00338D", "#1E49E2", "#0C233C", "#ACEAFF", "#00B8F5", "#7210EA", "#FD349C"]
            wc = WordCloud(
                width=1600, height=800, scale=4, background_color="white",
                color_func=lambda *args, **kwargs: random.choice(palette),
                collocations=False,
                font_path="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                max_words=100
            ).generate_from_frequencies(freqs)
            st.image(wc.to_image(), use_container_width=True)
        else:
            st.info(f"Nessuna risposta per '{question}'.")
        st.write("---")

    # Categorical / bar chart questions
    for key, question in content.get("categorical", []):
        counts = Counter(r.get(key) for r in responses if r.get(key))
        if counts:
            st.subheader(question)
            df = {"Opzione": list(counts.keys()), "Conteggio": list(counts.values())}
            fig = px.bar(df, x="Opzione", y="Conteggio")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Nessuna risposta per '{question}'.")
        st.write("---")
