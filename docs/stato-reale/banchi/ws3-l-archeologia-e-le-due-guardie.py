"""`deep` promette di far riemergere i ricordi dormienti — e di NON far
riemergere quelli manomessi. Due meta' della stessa promessa.

LA PROMESSA, dallo schema di `hippo_facts_recall`::

    v14 ARCHAEOLOGY mode: lift the 45-day age-based hiding so dormant-but-true
    memories stay findable months/years later ('what did the client say in
    March?'). Integrity guards stay (future timestamp = tamper, valid_until
    hard-expire).

⇒ **Due affermazioni, e la seconda e' quella che rende la prima non banale.**
Un `deep` che facesse riemergere tutto sarebbe facile e sbagliato.

LETTURA PRIMA DI MISURARE — il numero «45» regge::

    semantic.py:1046  if ignore_age: return False     <- cio' che `deep` lifta
    semantic.py:1052  is_stale(age_days, half_life_days)
    semantic.py:877   _DEFAULT_HALF_LIFE_DAYS = 45.0
    freshness.py:27   is_stale(age, half_life, floor=0.5)
                      -> decay_factor(age, half_life) < floor

Con un decadimento a meta'-vita, a 45 giorni esatti il fattore vale 0.5, che
NON e' < 0.5: la soglia cade appena oltre i 45 giorni. Lo schema dice il vero.
E le due guardie d'integrita' stanno SOPRA il `return False` di `ignore_age`,
cioe' `deep` non puo' raggiungerle: la lettura dice che la seconda meta' della
promessa dovrebbe reggere. **Questo banco esiste per verificarlo, non per
assumerlo.**

═══════════════════════════════════════════════════════════════════════════════
🔑 IL CONTROLLO CHE DEVE POTER FALLIRE: un fatto NUOVO deve tornare in entrambi
i modi. Se lo store non rispondesse gia' cosi', ogni zero sarebbe illeggibile.
⚠️ E IL SECONDO CONTROLLO, che decide se il fenomeno esiste: **senza `deep` il
fatto vecchio NON deve tornare**. Se tornasse, non ci sarebbe nessun
nascondimento da liftare e `deep` non avrebbe niente da fare.
⚠️ LA POPOLAZIONE OPPOSTA — la meta' che rende seria l'altra: un fatto con
timestamp NEL FUTURO non deve tornare **nemmeno con `deep`**.
═══════════════════════════════════════════════════════════════════════════════

REGIME: un processo, store TEMPORANEO, SDK in-process, giudice locale assente.
Le date si spostano con un UPDATE su SQLite — sullo store TEMPORANEO di questo
banco, e i nomi di tabella e colonna si LEGGONO da `PRAGMA table_info` invece
di indovinarli (cinque volte in una notte il difetto era nel misuratore).
⚠️ DUE DATE, NON UNA: allo store `last_verified_at` nasce valorizzato e il
codice la preferisce a `created_at`. Spostando solo la seconda il fatto resta
giovane e il banco conclude «nessun nascondimento» — falso. Il banco si e'
fermato da solo prima di dirlo, perche' non era riuscito a spostare niente.
Lo store di Aurelio non e' toccato.

    python docs/stato-reale/banchi/ws3-l-archeologia-e-le-due-guardie.py
"""

from __future__ import annotations

import json
import subprocess
import sys

DOMANDA = "quanti metri quadrati ha il magazzino di Rovigo"

FIGLIO = r'''
import json, os, sqlite3, sys, tempfile, time
os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()
os.environ["ENGRAM_LOCAL_GATE_MODEL"] = tempfile.mkdtemp()
os.environ.pop("ENGRAM_MIN_RELEVANCE", None)

from verimem.client import Memory

domanda = sys.argv[1]   # non usata: ogni fatto ha la sua
percorso = os.path.join(tempfile.mkdtemp(), "s.db")
m = Memory(percorso)

# ⚠️ UN SOGGETTO E UNA DOMANDA PER FATTO. La prima stesura scriveva tre
# proposizioni che differivano per UNA parola («magazzino nuovo/vecchio/futuro
# di Rovigo») e ne interrogava una sola: il richiamo ne restituiva UNO, e ogni
# cella era illeggibile. Tre soggetti distinti, tre domande distinte, tre celle
# indipendenti.
# Il quarto elemento e' il TOKEN UNIVOCO con cui si riconosce il fatto nella
# risposta. ⚠️ La stesura precedente lo DERIVAVA come «terza parola della
# proposizione» e otteneva «del», «di», «di»: preposizioni presenti in ogni
# testo ⇒ ogni cella dava un falso positivo, e il banco stava per pubblicare
# «la guardia anti-manomissione cade con `deep`» — un finding di SICUREZZA
# falso. Settima volta in una notte che il difetto sta nel misuratore, e la
# prima in cui avrebbe accusato il prodotto di qualcosa che non fa.
# 🔑 Il sospetto e' nato dal CONTRASTO con la lettura del sorgente: la guardia
# `base > now` precede `ignore_age` e non puo' essere scavalcata. Quando la
# misura contraddice una lettura netta, il primo indiziato e' la misura.
ETICHETTE = {
    "nuovo":   ("La penale del contratto Rossi e' 120 euro al giorno.",
                "Contratto Rossi, articolo 7: penale di 120 euro al giorno.",
                "quanto e' la penale del contratto Rossi", "Rossi"),
    "vecchio": ("Il magazzino di Vicenza ha 4200 metri quadrati.",
                "Registro immobili, scheda Vicenza: superficie 4200 metri quadrati.",
                "quanti metri quadrati ha il magazzino di Vicenza", "Vicenza"),
    "futuro":  ("La sede di Trento apre alle 9 del mattino.",
                "Regolamento sedi, Trento: apertura ore 9 del mattino.",
                "a che ora apre la sede di Trento", "Trento"),
}
ids = {}
for etichetta, (prop, fonte, _q, _tok) in ETICHETTE.items():
    fid = m.add(prop, source=fonte, topic="arch/mag")
    # `add()` restituisce un DICT con `id`: letto, non indovinato — la prima
    # stesura cercava una stringa o un attributo `.id` e non spostava nulla.
    ids[etichetta] = (fid.get("id") if isinstance(fid, dict)
                      else (fid if isinstance(fid, str)
                            else getattr(fid, "id", None)))

db = getattr(m.semantic, "db_path", percorso)
con = sqlite3.connect(db)
tabelle = [r[0] for r in con.execute(
    "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
tab = "facts" if "facts" in tabelle else (tabelle[0] if tabelle else None)
colonne = [r[1] for r in con.execute(f"PRAGMA table_info({tab})").fetchall()] if tab else []

ora = time.time()
spostati = {}
# 🔑 ENTRAMBE LE DATE. `_fact_is_stale` legge
# `base = last_verified_at if not None else created_at`, e allo store
# `last_verified_at` NASCE VALORIZZATO (uguale a `created_at`): spostare solo
# la seconda avrebbe lasciato il fatto giovane, e il banco avrebbe concluso
# «nessun nascondimento da liftare» — falso. Letto dallo store prima di agire.
if tab and "created_at" in colonne and "id" in colonne:
    quali = [c for c in ("created_at", "last_verified_at") if c in colonne]
    set_sql = ", ".join(f"{c}=?" for c in quali)
    for etichetta, delta in (("vecchio", -200 * 86400), ("futuro", +30 * 86400)):
        fid = ids.get(etichetta)
        if fid:
            con.execute(f"UPDATE {tab} SET {set_sql} WHERE id=?",
                        (*([ora + delta] * len(quali)), fid))
            spostati[etichetta] = delta / 86400.0
    con.commit()
con.close()

m2 = Memory(percorso)   # riaperto: nessuna cache in memoria di mezzo

def _testo(h):
    """⚠️ `search` restituisce dict con chiave `text`, NON oggetti con
    `.proposition`. La prima stesura chiedeva l'attributo e otteneva stringa
    vuota per ogni riga: tutte le celle a zero, controllo caduto. Sesta volta
    in una notte che il misuratore sbaglia la forma di cio' che legge —
    per questo la forma viene STAMPATA, non assunta."""
    f = h[0] if isinstance(h, (tuple, list)) else h
    if isinstance(f, dict):
        return str(f.get("text") or f.get("proposition") or "")
    return str(getattr(f, "proposition", None) or getattr(f, "text", "") or "")

FORMA = {}

def visti(deep):
    """Ogni fatto con la SUA domanda: la cella dice se QUEL fatto e' tornato."""
    fuori = []
    for etichetta, (_p, _f, q, token) in ETICHETTE.items():
        hits = m2.search(q, k=10, deep=deep)
        if hits and not FORMA:
            primo = hits[0]
            FORMA["tipo"] = type(primo).__name__
            FORMA["chiavi"] = (sorted(primo.keys())[:8] if isinstance(primo, dict)
                               else str(type(primo)))
        if any(token in _testo(h) for h in hits):
            fuori.append(etichetta)
    return sorted(fuori)

print(json.dumps({
    "tabella": tab, "colonne_chiave": [c for c in colonne if "at" in c or c == "id"],
    "spostati_giorni": spostati,
    "senza_deep": visti(False), "con_deep": visti(True), "forma": FORMA,
}, ensure_ascii=False, default=str))
'''


def main() -> int:
    p = subprocess.run([sys.executable, "-c", FIGLIO, DOMANDA],
                       capture_output=True, text=True, timeout=2400)
    if p.returncode != 0:
        print(f"  PROCESSO MORTO exit={p.returncode}: {p.stderr.strip()[-500:]}")
        return 1
    d = json.loads(p.stdout.strip().splitlines()[-1])

    print(f"  tabella LETTA: {d['tabella']} · colonne temporali: "
          f"{d['colonne_chiave']}")
    print(f"  date spostate (giorni): {d['spostati_giorni'] or 'NESSUNA'}")
    print(f"  forma di un esito (LETTA): {d.get('forma') or 'nessun esito'}")
    if not d["spostati_giorni"]:
        print("\n  NESSUN VERDETTO: non sono riuscito a spostare le date, quindi")
        print("  non esiste nessun fatto «vecchio» e il banco misurerebbe altro.")
        return 1

    senza, con = d["senza_deep"], d["con_deep"]
    print(f"\n  senza deep : {senza}")
    print(f"  con deep   : {con}")

    print(f"\n  [1] CONTROLLO — il fatto NUOVO torna in entrambi i modi: "
          f"{'SI' if 'nuovo' in senza and 'nuovo' in con else 'NO'}")
    if not ("nuovo" in senza and "nuovo" in con):
        print("      CONTROLLO CADUTO: lo store non risponde nemmeno sul fatto")
        print("      recente ⇒ ogni assenza qui sotto e' illeggibile.")
        print("      NESSUN VERDETTO.")
        return 1

    print(f"  [2] IL FENOMENO ESISTE — senza `deep` il VECCHIO (200 giorni) e' "
          f"nascosto: {'SI' if 'vecchio' not in senza else 'NO'}")
    if "vecchio" in senza:
        print("      Nessun nascondimento da liftare ⇒ `deep` non ha niente da")
        print("      fare su questo store. NESSUN VERDETTO sull'archeologia.")
        return 1

    print("\n  ══ VERDETTO ══")
    if "vecchio" in con:
        print("     🟢 PRIMA META': `deep` fa riemergere il dormiente (200")
        print("     giorni) che senza non tornava.")
    else:
        print("     🔴 PRIMA META' CADUTA: il fatto vecchio non torna nemmeno")
        print("     con `deep` — la promessa «findable months later» non regge.")

    if "futuro" in con:
        print("     🔴 SECONDA META' CADUTA: un fatto con timestamp NEL FUTURO")
        print("     torna con `deep`. La descrizione promette che le guardie")
        print("     d'integrita' restino («future timestamp = tamper»): `deep`")
        print("     starebbe liftando piu' dell'eta'.")
    else:
        print("     🟢 SECONDA META': il timestamp futuro resta fuori ANCHE con")
        print("     `deep` — l'archeologia lifta l'eta', non l'integrita'.")
        print("     ⚠️ E' questa meta' a rendere la prima non banale.")

    print("\n  ⚠️ LIMITI: tre fatti, una domanda, uno store nuovo, date spostate")
    print("     a mano. NON misura `valid_until` (l'altra guardia nominata), ne'")
    print("     il comportamento vicino alla soglia: 200 giorni e' ben oltre, e")
    print("     un fatto di 46 giorni non e' provato qui.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
