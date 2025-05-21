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
import textwrap
import streamlit as st
import qrcode
import plotly.express as px
from wordcloud import WordCloud
from github import Github, GithubException

from db import init_db, SessionLocal, Response

# ----------------------------------------------------------------
# 1) Brand palette
# ----------------------------------------------------------------
PALETTE = [
    "#00338D",  # primary
    "#1E49E2",  # secondary
    "#0C233C",  # tertiary
    "#ACEAFF",  # accent light
    "#00B8F5",  # accent
    "#7210EA",  # highlight
    "#FD349C",  # pink
]

# ----------------------------------------------------------------
# 2) Page config and DB init
# ----------------------------------------------------------------
st.set_page_config(
    page_title="EU AML Package",
    layout="wide",
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
# 3) Read query params
# ----------------------------------------------------------------
params      = st.query_params
survey_mode = params.get("survey", ["0"])[0] == "1"
admin_mode  = params.get("admin",  ["0"])[0] == "1"

# ----------------------------------------------------------------
# 4) Global CSS (QR landing, top bar, form, theme)
# ----------------------------------------------------------------
st.markdown(
    f"""
    <style>
      /* QR landing: center container on landing page */
      [data-testid="stAppViewContainer"] [data-testid="stBlockContainer"] {{
        max-width:700px !important;
        margin-left:auto !important;
        margin-right:auto !important;
      }}

      /* Hide default header and sidebar background */
      header {{ visibility: hidden; }}
      [data-testid="stHeader"], [data-testid="stSidebar"] {{
        background-color: var(--primary, {PALETTE[0]}) !important;
      }}

      /* Top bar */
      .top_bar {{
        position: fixed;
        top: 0; left: 0;
        width: 100vw; height: 100px;
        background-color: var(--primary, {PALETTE[0]});
        display: flex; align-items: center;
        padding-left: 20px; z-index: 9999;
      }}
      .top_bar img {{ height: 60px; }}
      .logo-acora {{ height: 40px !important; margin-left:20px; }}

      /* Space below top bar */
      [data-testid="stBlockContainer"] {{ padding-top: 100px; }}

      /* Form container */
      .form-container {{
        max-width: 900px !important;
        width: 90%   !important;
        margin: 0 auto 40px auto;
      }}

      /* Buttons */
      [data-testid="stButton"] > button {{
        background-color: var(--primary, {PALETTE[0]}) !important;
        color: white !important;
        border-radius: 8px !important;
      }}

      /* Progress bar */
      .stProgress > div > div > div {{
        background-color: var(--secondary, {PALETTE[3]}) !important;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------
# 5) Top bar logos
# ----------------------------------------------------------------
logo_b64 = None
logo2_b64 = None
for asset, var_name in [("assets/immagine.png", "logo_b64"),
                        ("assets/acorà logo.png", "logo2_b64")]:
    try:
        with open(asset, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
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

    # Genera QR e base64
    qr = qrcode.make(survey_url)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    # Override CSS: container full-width, centratura QR & URL
    st.markdown(
        """
        <style>
          /* Solo qui: elimina il max-width di 700px */
          [data-testid="stAppViewContainer"] [data-testid="stBlockContainer"] {
            max-width: none !important;
            width: 100% !important;
          }
          .qr-container {
            text-align: center;
            margin: 0 auto;
            padding: 40px 0;
          }
          .qr-container img {
            width: 700px;
            max-width: 90vw;
            height: auto;
          }
          .survey-url {
            font-size: 48px;
            white-space: nowrap;
            margin-top: 20px;
          }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Output QR + URL
    st.markdown(
        f"""
        <div class="qr-container">
          <img src="data:image/png;base64,{qr_b64}" alt="QR code" />
          <div class="survey-url">{survey_url}</div>
          <div style="margin-top:10px;">
            <a href="{survey_url}" target="_blank">Apri il form</a>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.stop()


# ----------------------------------------------------------------
# 7) Survey Page (risposte sotto, non al lato)
# ----------------------------------------------------------------
if survey_mode and not admin_mode:
    st.title("EU AML Package")

    # Step 1 indicator
    st.progress(1/3)

    st.markdown("<div class='form-container'>", unsafe_allow_html=True)
    with st.form("survey"):
        # Section 1
        st.markdown("<div class='form-card'>", unsafe_allow_html=True)
        st.write("## 01. Adeguamento ad EU AML Package")

        # 1.
        st.write("**1. È stata già avviata una gap analysis su EU AML Package?**")
        gap_analysis = st.radio(
            label="",
            options=["Sì", "No"],
            key="gap_analysis",
            horizontal=False,
            label_visibility="collapsed",
            index=None
        )

        # 2.
        st.write("**2. Il Consiglio di Amministrazione è stato già informato dell’avvio dell’EU AML Package e delle imminenti novità normative in materia?**")
        board_inform = st.radio(
            label="",
            options=["Sì", "No"],
            key="board_inform",
            horizontal=False,
            label_visibility="collapsed",
            index=None
        )

        # 3.
        st.write("**3. È stato già stanziato del budget dedicato alle attività di adeguamento all’EU AML Package?**")
        budget = st.radio(
            label="",
            options=["Sì", "No"],
            key="budget",
            horizontal=False,
            label_visibility="collapsed",
            index=None
        )

        # 4.
        st.write("**4. Avete già avviato attività di adeguamento su requisiti specifici definiti dall’EU AML Package?**")
        adeguamento_specifico = st.radio(
            label="",
            options=["Sì", "No"],
            key="adeguamento_specifico",
            horizontal=False,
            label_visibility="collapsed",
            index=None
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # Step 2 indicator
        st.progress(2/3)

        # Section 2
        st.markdown("<div class='form-card'>", unsafe_allow_html=True)
        st.write("## 02. Principali impatti attesi dall'EU AML Package")
        impacts = st.multiselect(
            label="**1. Quali sono le principali preoccupazioni ed impatti attesi dal nuovo quadro normativo (selezionare fino a 3 opzioni)?**",
            options=[
                "Supervisione diretta", "Tempistiche di adeguamento", "Complessità del quadro normativo",
                "Implementazioni informatiche", "AML Governance", "Risk assessment", "Data model",
                "Know your customer", "Transaction monitoring", "Targeted financial sanctions",
                "Paesi terzi ad alto rischio", "Requisiti sulla titolarità effettiva",
                "Protezione e condivisione dei dati", "Outsourcing", "Misure amministrative e sanzioni",
                "Nessun impatto identificato al momento"
            ],
            max_selections=3,
            key="impacts"
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # Step 3 indicator
        st.progress(3/3)

        # Section 3
        st.markdown("<div class='form-card'>", unsafe_allow_html=True)
        st.write("## 03. Nuova governance AML")

        # 1.
        st.write("**1. Si è già provveduto a nominare l’AML Board Member?**")
        bm_yes_no = st.radio(
            label="",
            options=["Sì", "No"],
            key="bm_yes_no",
            horizontal=False,
            label_visibility="collapsed",
            index=None
        )

        # 2.
        st.write("**2. Quale soggetto è stato nominato (o si prevede di nominare) come AML Board Member?**")
        bm_nominee = st.radio(
            label="",
            options=[
                "Amministratore Delegato",
                "Altro membro esecutivo del Consiglio di Amministrazione",
                "Membro non esecutivo del Consiglio di Amministrazione (che diventa esecutivo a seguito della nomina)",
                "Non ancora definito"
            ],
            key="bm_nominee",
            horizontal=False,
            label_visibility="collapsed",
            index=None
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # Submit
        submit = st.form_submit_button("Invia")

    if submit:
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
st.title("EU AML Package")
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

sections = {
    "01. Adeguamento ad EU AML Package": {
        "yesno": [
            ("gap_analysis", "1. È stata già avviata una gap analysis su EU AML Package?"),
            ("board_inform", "2. Il Consiglio di Amministrazione è stato già informato dell’avvio dell’EU AML Package e delle imminenti novità normative in materia?"),
            ("budget", "3. È stato già stanziato del budget dedicato alle attività di adeguamento all’EU AML Package?"),
            ("adeguamento_specifico", "4. Avete già avviato attività di adeguamento su requisiti specifici definiti dall’EU AML Package?")
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

for section_title, content in sections.items():
    st.header(section_title)

    # --- Sì/No questions as treemap ---
    for key, question in content.get("yesno", []):
        counts = Counter(r.get(key) for r in responses if r.get(key) is not None)
        if counts:
            # 1) Ordina manualmente: "Sì" sempre primo
            items = sorted(counts.items(), key=lambda kv: kv[0], reverse=True)

            df = {
                "Risposta": [i[0] for i in items],
                "Conteggio": [i[1] for i in items]
            }

            # 2) Mappa colori
            color_map = {"Sì": PALETTE[4], "No": PALETTE[1]}

            # 3) Treemap a un livello
            fig = px.treemap(
                df,
                path=["Risposta"],
                values="Conteggio",
                color="Risposta",
                color_discrete_map=color_map
            )

            # 4) Disabilita sorting e azzera il bordo
            fig.data[0].sort = False
            fig.data[0].marker.line.width = 0

            # 5) Configura il testo
            fig.update_traces(
                hoverinfo="none",
                hovertemplate=None,
                textinfo="label+percent entry",
                textposition="middle center",
                textfont=dict(size=30, color="white")
            )
            fig.update_layout(margin=dict(t=10, l=10, r=10, b=10))

            st.subheader(question)
            st.plotly_chart(
                fig,
                use_container_width=True,
                key=f"treemap-{section_title}-{key}"
            )
        else:
            st.info(f"Nessuna risposta per '{question}'.")
        st.write("---")

    # --- Multiselect as WordCloud ---
    for key, question in content.get("multiselect", []):
        freqs = Counter(choice for r in responses for choice in r.get(key, []))
        if freqs:
            st.subheader(question)
            wc = WordCloud(
                width=1600, height=800, scale=4, background_color="white",
                color_func=lambda *args, **kwargs: random.choice(PALETTE),
                collocations=False,
                font_path="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                max_words=100
            ).generate_from_frequencies(freqs)
            st.image(wc.to_image(), use_container_width=True)
        else:
            st.info(f"Nessuna risposta per '{question}'.")
        st.write("---")

 

# --- Categorical as wrapped vertical bar chart ---
    for key, question in content.get("categorical", []):
        counts = Counter(r.get(key) for r in responses if r.get(key))
        if counts:
            st.subheader(question)
            # 1) DataFrame
            df = {"Opzione": list(counts.keys()), "Conteggio": list(counts.values())}

            # 2) Crea etichette con a capo ogni 15 caratteri circa
            wrapped_labels = [
                "<br>".join(textwrap.wrap(op, width=15))
                for op in df["Opzione"]
            ]

            # 3) Bar chart verticale
            fig = px.bar(
                df,
                x="Opzione",
                y="Conteggio"
            )
            fig.update_yaxes(
                tickformat=".0f",
                showgrid=False
            )

            # 4) Sostituisci ticktext e abilit a automargin
            fig.update_xaxes(
                ticktext=wrapped_labels,
                tickvals=df["Opzione"],
                tickfont=dict(size=18),
                automargin=True
            )

            # 5) Margini più alti in basso per le etichette  
            fig.update_layout(
                xaxis_title=None,
                yaxis_title=None,
                margin=dict(t=20, b=300, l=50, r=20),
                height=600
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Nessuna risposta per '{question}'.")
        st.write("---")
