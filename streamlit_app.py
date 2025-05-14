import streamlit as st
from github import Github
import json
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import qrcode
import io

# --- Carica secrets ---
token     = st.secrets["github_token"]
repo_name = st.secrets["repo_name"]
app_url   = st.secrets["app_url"]  # es. "https://…streamlit.app"

# --- Inizializza GitHub ---
g     = Github(token)
repo  = g.get_repo(repo_name)
fpath = "responses.json"

# --- Scopri se siamo in admin mode (solo con ?admin=1) ---
params     = st.experimental_get_query_params()
admin_mode = params.get("admin", ["0"])[0] == "1"

if not admin_mode:
    # ----- VIEW PUBBLICA: QR + form -----
    st.title("Questionario")
    # QR code per aprire il form
    qr = qrcode.make(app_url)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)
    st.image(buf, caption="Scansiona per aprire il questionario", use_column_width=True)
    st.markdown(f"[Oppure clicca qui per aprire il form]({app_url})")
    st.write("---")

    with st.form("survey"):
        q1 = st.text_input("1) Dove lavori?")
        q2 = st.radio("2) Seleziona la tua opzione:",
                      options=["Opzione A", "Opzione B", "Opzione C", "Opzione D"])
        submitted = st.form_submit_button("Invia")

    if submitted:
        # Leggi (o crea) responses.json
        try:
            contents = repo.get_contents(fpath)
            data     = json.loads(contents.decoded_content)
        except:
            data = []

        # Aggiungi e committa
        data.append({"q1": q1, "q2": q2})
        updated = json.dumps(data, ensure_ascii=False, indent=2)
        if "contents" in locals():
            repo.update_file(fpath, "Aggiorna survey", updated, contents.sha)
        else:
            repo.create_file(fpath, "Crea responses.json", updated)

        st.success("Grazie! La tua risposta è stata registrata.")

else:
    # ----- VIEW ADMIN: risultati -----
    st.title("Dashboard Risposte (Admin)")
    st.markdown(f"[Torna al form]({app_url})")
    st.write("---")

    # Leggi tutte le risposte
    try:
        contents = repo.get_contents(fpath)
        data     = json.loads(contents.decoded_content)
    except:
        st.info("Ancora nessuna risposta.")
        st.stop()

    # 1) Risposte aperte Q1
    open_resps = [r["q1"] for r in data if r.get("q1","").strip()]
    if open_resps:
        st.subheader("Risposte aperte: Dove lavori?")
        for txt in open_resps:
            st.write(f"- {txt}")
    else:
        st.info("Nessuna risposta aperta per Q1.")

    st.write("---")

    # 2) Word-cloud per Q2
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
