"""ws1 — FETTA ①: le promesse SCRITTE di Verimem, ESEGUITE una per una.

Fonti delle promesse (verbatim, non parafrasate):
  PyPI   pyproject.toml `description`
  README README.md, intro + Features
  MCP    verimem/agent_guide.py::VERIMEM_AGENT_GUIDE — cio' che il prodotto
         stampa a OGNI client sul campo `instructions` dell'initialize

Regola del task: ogni riga ESEGUITA, non letta. Store ISOLATO, env PRIMA
dell'import (la regola misurata ieri: il path si risolve all'import).
"""
import os
import tempfile

TMP = tempfile.mkdtemp(prefix="ws1_promesse_")
os.environ["ENGRAM_DATA_DIR"] = TMP
os.environ["HIPPO_DATA_DIR"] = TMP
os.environ["VERIMEM_DATA_DIR"] = TMP
os.environ["ENGRAM_GROUNDING_WRITE"] = "1"

import sys  # noqa: E402
# DA DOVE stiamo misurando — la riga che mi mancava stamattina e che mi e'
# costata cinque errori (repo vs pacchetto vs processo vivo). Strumento di ws2.
import subprocess, sys as _s
try:
    _a = subprocess.run([_s.executable, "scripts/artefatto.py"], capture_output=True,
                        text=True, timeout=60).stdout.strip()
    print("ARTEFATTO:", _a or "(artefatto.py non ha risposto)")
except Exception as _e:
    import verimem as _v; print("ARTEFATTO: fallback ->", _v.__file__)

ESITI = []


def esito(pid, promessa, verdetto, prova):
    ESITI.append((pid, promessa, verdetto, prova))
    print(f"\n[{pid}] {verdetto}")
    print(f"    promessa: {promessa}")
    print(f"    prova   : {prova}")


# ─────────────────────────────────────────────────────────────────────────
# Le promesse delle `instructions` — la fonte piu' autorevole: e' cio' che il
# prodotto dice di se' a ogni agente che lo collega.
# ─────────────────────────────────────────────────────────────────────────
from verimem import Memory  # noqa: E402

m = Memory(os.path.join(TMP, "prove.db"))

# P16 «ALWAYS: a lexical screen on every write. Unsupported "it works /
#      verified / done" self-claims are quarantined, with no LLM call.»
r = m.add("La migrazione e' stata completata e funziona perfettamente.")
st = (r or {}).get("status") if isinstance(r, dict) else getattr(r, "status", None)
esito("P16", 'lexical screen SEMPRE: i vanti "funziona/verificato" quarantinati senza LLM',
      "VERO" if st == "quarantined" else f"DA GUARDARE (status={st})",
      f'm.add("...completata e funziona perfettamente") -> status={st}')

# P19 «WITHOUT a source: ... stored as an unverified `model_claim`.»
r2 = m.add("Il magazzino di Rovigo contiene 300 pallet.")
st2 = (r2 or {}).get("status") if isinstance(r2, dict) else getattr(r2, "status", None)
gs2 = (r2 or {}).get("grounding_score") if isinstance(r2, dict) else None
esito("P19", "senza source: il fatto entra come model_claim non verificato",
      "VERO" if st2 == "model_claim" else f"DA GUARDARE (status={st2})",
      f"m.add(senza source) -> status={st2} grounding={gs2}")

# P17 «WITH a `source`: ... admitted only if the source TEXT actually supports it»
r3 = m.add("Il deposito di Verona contiene 610 unita.",
           source="Inventario: il deposito di Verona contiene 610 unita.")
r4 = m.add("Il deposito di Bari contiene 900 unita.",
           source="Inventario: il deposito di Bari contiene 120 unita.")
st3 = (r3 or {}).get("status") if isinstance(r3, dict) else None
st4 = (r4 or {}).get("status") if isinstance(r4, dict) else None
g3 = (r3 or {}).get("grounding_score") if isinstance(r3, dict) else None
g4 = (r4 or {}).get("grounding_score") if isinstance(r4, dict) else None
ok17 = st3 != "quarantined" and st4 == "quarantined"
esito("P17", "con source: ammesso SOLO se la fonte lo sostiene",
      "VERO" if ok17 else f"DA GUARDARE (sostenuto={st3}, contraddetto={st4})",
      f"sostenuto -> {st3} gs={g3} | contraddetto -> {st4} gs={g4}")

# P18 «`verified_by` records WHO vouches ... and does NOT run this check»
r5 = m.add("Il deposito di Como contiene 999 unita.", verified_by=["actor:ws1"])
st5 = (r5 or {}).get("status") if isinstance(r5, dict) else None
g5 = (r5 or {}).get("grounding_score") if isinstance(r5, dict) else None
esito("P18", "verified_by NON fa girare il moat (registra CHI, non verifica)",
      "VERO" if g5 is None else f"DA GUARDARE (grounding={g5})",
      f"m.add(verified_by=['actor:ws1'], senza source) -> status={st5} grounding={g5}")

# P20 «QUARANTINED — stored, but kept OUT of default recall»
res = m.search("Bari unita")
ids = [getattr(x, "id", None) or (x.get("id") if isinstance(x, dict) else None) for x in (res or [])]
tornato = any(i == ((r4 or {}).get("id")) for i in ids)
esito("P20", "un fatto quarantinato resta STORED ma FUORI dal recall di default",
      "VERO" if not tornato else "FALSO: torna nel recall",
      f"m.search('Bari unita') -> {len(res or [])} risultati, il quarantinato "
      f"{'NON ' if not tornato else ''}compare")

# P23 «Every read carries `grounding_score` 0-100; `null` = NEVER JUDGED»
res2 = m.search("Verona unita")
campo = None
if res2:
    x = res2[0]
    campo = getattr(x, "grounding_score", None) if not isinstance(x, dict) else x.get("grounding_score")
esito("P23", "ogni lettura porta grounding_score (0-100, null = mai giudicato)",
      "VERO" if (res2 and campo is not None) else f"DA GUARDARE (campo={campo})",
      f"m.search('Verona unita')[0].grounding_score = {campo}")

# P8/README «revised through explicit supersession (never silent overwrites)»
m.add("Il deposito di Verona contiene 800 unita.",
      source="Nuovo inventario: il deposito di Verona contiene 800 unita.")
import sqlite3  # noqa: E402
from pathlib import Path  # noqa: E402
db = Path(TMP) / "prove.db"
if not db.exists():
    cand = list(Path(TMP).rglob("*.db"))
    db = cand[0] if cand else db
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
righe = con.execute("SELECT proposition, superseded_by, superseded_reason FROM facts "
                    "WHERE proposition LIKE '%Verona%' ORDER BY created_at").fetchall()
rit = sum(1 for _p, sb, _sr in righe if sb)
vivi = sum(1 for _p, sb, _sr in righe if not sb)
esito("P8", "revisione per supersessione ESPLICITA, mai sovrascrittura silenziosa",
      "VERO" if (rit >= 1 and vivi >= 1 and len(righe) >= 2) else
      f"DA GUARDARE (righe={len(righe)} ritirati={rit})",
      f"due valori per Verona -> {len(righe)} righe in tabella, {rit} ritirata(e), "
      f"{vivi} viva(e); il vecchio NON e' sparito")

print("\n" + "=" * 72)
print(f"{'ID':5} {'VERDETTO':28} promessa")
for pid, promessa, verdetto, _pr in ESITI:
    print(f"{pid:5} {verdetto:28} {promessa[:58]}")
print(f"\nstore isolato: {TMP}")
