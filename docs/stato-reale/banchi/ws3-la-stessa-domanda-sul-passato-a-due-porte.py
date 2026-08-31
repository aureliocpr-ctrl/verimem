"""«bi-temporal history»: la stessa domanda sul passato, in linguaggio naturale,
a due superfici.

DA DOVE VIENE. Riga ③ della matrice promessa x porta (@ws7, `LANT-130`),
provata a pezzi **sull'SDK**. Su MCP, il censimento degli schemi:

    as_of nello schema     hippo_trust_report        1 porta su 4
    as_of ASSENTE          hippo_facts_recall · hippo_facts_search
                           hippo_recall_history

🔑 E IL ROUTING AUTOMATICO — quello che trasforma una domanda in italiano sul
passato in una interrogazione temporale — e' collegato **solo sull'SDK**:

    client.py:1119   as_of = extract_as_of(query)      (search)
    client.py:1824   as_of = extract_as_of(query)      (explain)
    mcp_server:8206  wants_history(_q)                 (solo la STORIA, non l'as-of)

⇒ `recall_with_history` **accetta** `as_of` (e ha un ramo intero con le
etichette `[as of <data>]`), ma l'handler MCP non glielo passa e lo schema non
lo espone: la capacita' c'e' e non e' collegata a quella porta.

🚨 QUESTO BANCO NON E' RIUSCITO A ESIBIRE LA DIVERGENZA, e le tre ragioni sono
TUTTE MIE. Le scrivo perche' sono la RICETTA DI REGIME per chi ci riprovera':

  ① due scritture a 0,4 s di distanza OGGI non sono separabili da una data in
     parole ⇒ retrodatarle e' obbligatorio;
  ② retrodatare di mesi rende i fatti DORMIENTI (soglia ~45 giorni) e il
     richiamo non restituisce piu' niente, ne' passato ne' presente ⇒ serve
     `deep=True` su ENTRAMBE le superfici;
  ③ «a marzo» NON ancora un punto temporale, e non e' un difetto:
     `extract_as_of` riconosce SOLO forme con giorno E anno (ISO,
     «Month D, YYYY», «D Month YYYY») e il suo docstring lo dichiara —
     *«Pure, conservativa: nessuna ancora inventata»*. ⚠️ E i mesi ITALIANI ci
     sono (aggiunti il 2026-08-06): la classe «liste monolingue» qui e' gia'
     curata, l'ho verificata invece di supporla.

⇒ Per misurare davvero servono: due ere separate da MESI · `deep=True` · una
domanda che ancori GIORNO E ANNO. Chi lo rifara' parta da qui.

📌 COSA RESTA, ed e' LETTURA verificata, non misura: `as_of` e' nello schema di
UNA porta MCP su quattro, e `extract_as_of` compare solo in `client.py` (SDK).
La divergenza e' plausibile e NON dimostrata da questo banco — chiamarla
misurata sarebbe la cosa che passo la notte a non fare.

═══════════════════════════════════════════════════════════════════════════════
🔑 IL CONTROLLO CHE DEVE POTER FALLIRE: sull'SDK la domanda temporale deve
riportare il valore VECCHIO. Se non lo facesse, il routing non funziona nemmeno
li' e non c'e' nessuna divergenza da misurare — sarebbe un'altra storia.
⚠️ LA POPOLAZIONE OPPOSTA: una domanda al PRESENTE deve dare il valore NUOVO su
entrambe. Se una porta desse sempre il vecchio, non starei misurando il routing
ma un guasto del richiamo.
⚠️ IL CRITERIO SONO GLI ID, presi dalle ricevute di scrittura.
═══════════════════════════════════════════════════════════════════════════════

REGIME: un processo, store TEMPORANEO (entrambi gli alias), giudice locale
assente. Lo store di Aurelio non e' toccato.

    python docs/stato-reale/banchi/ws3-la-stessa-domanda-sul-passato-a-due-porte.py
"""

from __future__ import annotations

import json
import subprocess
import sys

FIGLIO = r'''
import asyncio, json, os, tempfile, time
d = tempfile.mkdtemp()
os.environ["HIPPO_DATA_DIR"] = d
os.environ["ENGRAM_DATA_DIR"] = d
os.environ["ENGRAM_LOCAL_GATE_MODEL"] = tempfile.mkdtemp()
os.environ.pop("ENGRAM_MIN_RELEVANCE", None)

from verimem import mcp_server
from verimem.client import Memory

VECCHIO = "Il canone del contratto Bianchi e' 800 euro al mese."
NUOVO = "Il canone del contratto Bianchi e' 1200 euro al mese."
PASSATO = "quanto era il canone del contratto Bianchi a marzo"
PRESENTE = "quanto e' il canone del contratto Bianchi"

percorso = os.path.join(tempfile.mkdtemp(), "s.db")
m = Memory(percorso)
a = m.add(VECCHIO, source="Contratto Bianchi: canone 800 euro al mese.", topic="t/b")
time.sleep(0.4)
b = m.add(NUOVO, source="Contratto Bianchi, integrazione: canone 1200 euro al mese.",
          topic="t/b")
id_v = a.get("id") if isinstance(a, dict) else None
id_n = b.get("id") if isinstance(b, dict) else None

# 🔑 LE DUE ERE DEVONO ESSERE SEPARABILI DA UNA DATA IN PAROLE. La prima
# stesura scriveva i due fatti a 0,4 s di distanza OGGI e chiedeva «a marzo»:
# nessun istante espresso a parole puo' cadere fra loro, e infatti il CONTROLLO
# e' caduto — sull'SDK la domanda sul passato dava il NUOVO. Il difetto era il
# disegno del banco, non il prodotto. Qui il vecchio nasce a gennaio e il nuovo
# a giugno, cosi' «marzo» cade davvero in mezzo.
import sqlite3
_GEN = time.time() - 240 * 86400      # ~gennaio
_GIU = time.time() - 90 * 86400       # ~giugno
_db = getattr(m.semantic, "db_path", percorso)
_con = sqlite3.connect(_db)
_cols = [r[1] for r in _con.execute("PRAGMA table_info(facts)").fetchall()]
_quali = [c for c in ("created_at", "last_verified_at", "asserted_at") if c in _cols]
_set = ", ".join(f"{c}=?" for c in _quali)
for _fid, _t in ((id_v, _GEN), (id_n, _GIU)):
    _con.execute(f"UPDATE facts SET {_set} WHERE id=?", (*([_t] * len(_quali)), _fid))
_con.commit(); _con.close()
m = Memory(percorso)   # riaperto dopo lo spostamento delle date
try:
    f = m.semantic.get(id_v)
    sup = getattr(f, "superseded_by", None)
except Exception as e:
    sup = f"ERRORE {type(e).__name__}"

def testo_di(x):
    if isinstance(x, dict):
        return str(x.get("text") or x.get("proposition") or "")
    return str(x)

def sdk(q):
    # ⚠️ `deep=True` NON e' un dettaglio: retrodatare di mesi — l'unico modo
    # per separare due ere con una data in PAROLE — rende i fatti dormienti
    # (soglia ~45 giorni), e senza archeologia il richiamo non restituisce nulla,
    # ne' passato ne' presente. E' il conflitto di regime di questo banco, ed e'
    # dichiarato: la seconda stesura dava «niente» su TUTTE e sei le celle.
    return [testo_di(h[0] if isinstance(h, (tuple, list)) else h)
            for h in m.search(q, k=10, deep=True)]

# La porta MCP deve puntare allo STESSO store dell'SDK.
class _Ag:
    semantic = m.semantic
    memory = m
mcp_server._ag = lambda: _Ag()

def mcp(porta, q, chiave):
    r = json.loads(asyncio.run(mcp_server._call_tool_impl(
        porta, {"query": q, "k": 10, "deep": True}))[0].text)
    righe = r.get(chiave) or []
    return [testo_di(x) for x in righe]

def quale(testi):
    v = any("800 euro" in t for t in testi)
    n = any("1200 euro" in t for t in testi)
    return ("VECCHIO+NUOVO" if v and n else "VECCHIO" if v
            else "NUOVO" if n else "niente")

out = {"superseduto_da": str(sup), "id_vecchio": id_v, "id_nuovo": id_n,
       "celle": {}}
for etichetta, q in (("PASSATO", PASSATO), ("PRESENTE", PRESENTE)):
    out["celle"][f"SDK search · {etichetta}"] = quale(sdk(q))
    for porta, chiave in (("hippo_facts_recall", "items"),
                          ("hippo_recall_history", "context")):
        out["celle"][f"{porta} · {etichetta}"] = quale(mcp(porta, q, chiave))

print("OUT=" + json.dumps(out, ensure_ascii=False, default=str))
'''


def main() -> int:
    p = subprocess.run([sys.executable, "-c", FIGLIO],
                       capture_output=True, text=True, timeout=1800)
    if p.returncode != 0:
        print(f"  PROCESSO MORTO exit={p.returncode}: {p.stderr.strip()[-450:]}")
        return 1
    d = json.loads([r for r in p.stdout.strip().splitlines()
                    if r.startswith("OUT=")][-1][4:])
    celle = d["celle"]

    print(f"  il vecchio risulta superseduto da: {d['superseduto_da']}")
    print(f"\n  {'cella':<40} risposta")
    print("  " + "-" * 66)
    for k, v in celle.items():
        print(f"  {k:<40} {v}")

    if d["superseduto_da"] in ("None", "", "null"):
        print("\n  ⚠️ PREMESSA CADUTA: le due versioni convivono, non c'e' un")
        print("  passato da ricostruire. NESSUN VERDETTO.")
        return 1

    sdk_passato = celle.get("SDK search · PASSATO", "")
    print(f"\n  [1] CONTROLLO — sull'SDK la domanda sul PASSATO riporta il "
          f"vecchio: {sdk_passato}")
    if "VECCHIO" not in sdk_passato:
        print("      CONTROLLO CADUTO: il routing temporale non funziona nemmeno")
        print("      sull'SDK ⇒ non c'e' divergenza da misurare. NESSUN VERDETTO.")
        return 1

    presente_ok = all("NUOVO" in celle.get(f"{s} · PRESENTE", "")
                      for s in ("SDK search", "hippo_facts_recall"))
    print(f"  [2] POPOLAZIONE OPPOSTA — al PRESENTE entrambe danno il nuovo: "
          f"{'SI' if presente_ok else 'NO'}")
    if not presente_ok:
        print("      Non sto misurando il routing ma il richiamo. NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    mcp_passato = [v for k, v in celle.items()
                   if k.startswith("hippo_") and k.endswith("PASSATO")]
    if all("VECCHIO" not in v for v in mcp_passato):
        print("     🔴 LA STESSA DOMANDA, DUE RISPOSTE: sull'SDK il passato si")
        print(f"     ricostruisce ({sdk_passato}); sulle porte MCP no ({mcp_passato}).")
        print("     ⇒ Un agente che chiede del passato IN PAROLE lo ottiene")
        print("     dall'SDK e non dalla superficie dichiarata PRIMARIA per gli")
        print("     agenti. Il parametro esplicito esiste su UNA porta su quattro")
        print("     (`hippo_trust_report`), e il routing automatico su NESSUNA.")
    else:
        print("     🟢 anche su MCP la domanda sul passato riporta il vecchio: la")
        print("     lettura del codice era incompleta.")

    print("\n  ⚠️ LIMITI: un fatto e la sua revisione, due domande, una lingua.")
    print("     NON misura `hippo_trust_report` col parametro `as_of` ESPLICITO —")
    print("     quello l'ho gia' misurato e REGGE (tre celle, `92f73123`): qui si")
    print("     misura solo cosa ottiene chi NON sa di doverlo passare.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
