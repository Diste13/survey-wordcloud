from github import Github
from db import SessionLocal, init_db, Response
import json
import sys
import traceback

# 1) Inizializza il database
init_db()

# 2) Connetti a GitHub
g = Github(g)
repo = g.get_repo(r)

# 3) Recupera la lista di file JSON
files = repo.get_contents("responses")

# 4) Apri la sessione DB
session = SessionLocal()
skipped = 0

for f in files:
    raw = repo.get_contents(f.path).decoded_content
    try:
        r = json.loads(raw)
    except json.JSONDecodeError:
        print(f"[!] File non valido JSON, skip: {f.path}", file=sys.stderr)
        skipped += 1
        continue

    # 5) Estrai e valida i campi essenziali
    bm_yes_no  = r.get("bm_yes_no")
    bm_nominee = r.get("bm_nominee")
    impacts    = r.get("impacts")

    # Se mancano o sono None/empty → skip
    if not bm_yes_no or not bm_nominee or impacts is None:
        print(
            f"[!] Skipping {f.path}: "
            f"bm_yes_no={bm_yes_no!r}, bm_nominee={bm_nominee!r}, impacts={impacts!r}",
            file=sys.stderr
        )
        skipped += 1
        continue

    # 6) Prendi bm_notes (opzionale)
    bm_notes = r.get("bm_notes")

    # 7) Crea e aggiungi l’oggetto ORM
    resp = Response(
        bm_yes_no = bm_yes_no,
        bm_nominee= bm_nominee,
        bm_notes  = bm_notes,
        impacts   = impacts
    )
    session.add(resp)

# 8) Commit e gestione errori
try:
    session.commit()
    print(f"Migrazione completata, {skipped} file saltati.")
except Exception as e:
    print("Errore durante il commit:", e, file=sys.stderr)
    traceback.print_exc()
finally:
    session.close()
