# -*- coding: utf-8 -*-
"""ACCENSIONE in modalita' AVVISO nel MIO processo — e perche' NON e' «un'ora di
uso reale», che va detto prima del numero.

IL VIA C'E' (@lead-audit 19:24: «nei TUOI soli processi: SI, subito»). Ma
`ENGRAM_CAPABILITY_GATE` e' una variabile PER PROCESSO, e **le chiamate vere ai
tool `hippo_*` passano dal server MCP, che e' un processo SEPARATO e CONDIVISO**:
accenderla qui NON intercetta il mio traffico reale. Un'ora di attesa
produrrebbe zero righe e la chiameremmo «misura».

⇒ QUESTO BANCO MISURA CIO' CHE SI PUO' MISURARE DAVVERO SENZA TOCCARE NESSUNO:
il CONTENUTO della riga di avviso — «quale tool, con quali parametri» — che e'
esattamente cio' che ieri non sapevamo (nel journal gli argomenti sono un hash).
Il VOLUME e' gia' noto e non serve riprodurlo: 898/1451 = 61,9% delle chiamate,
112,2 righe/ora attiva, picco 534 (W7-133).

COSA FA: accende `warn` in QUESTO processo, passa dal gate i 12 tool sconosciuti
piu' chiamati del journal con gli argomenti che quei tool dichiarano di
accettare, e legge il file di audit prodotto.

CONTROLLI CHE DEVONO ACCENDERSI:
  ① nessuna chiamata deve essere BLOCCATA (fail-open: e' il senso di «avviso»)
  ② ogni tool sconosciuto deve produrre una riga con `outcome=cap_deny`
  ③ la riga deve portare `arg_keys` — la cura di oggi
  ④ e NON deve portare i valori: metto un valore-sentinella e lo cerco nel file
"""
import io
import json
import os
import tempfile

TMP = tempfile.mkdtemp(prefix="ws4_warn_")
LOG = os.path.join(TMP, "audit.log")
os.environ["HIPPO_MCP_AUDIT_LOG"] = LOG
os.environ["ENGRAM_CAPABILITY_GATE"] = "warn"

from verimem.mcp_server import _capability_gate  # noqa: E402
from verimem.tool_registry import REGISTRY  # noqa: E402

SENTINELLA = "VALORE-SENTINELLA-9d3f"
CHIAMATE = [
    ("hippo_recall_history", {"query": SENTINELLA, "k": 5}),
    ("hippo_facts_list", {"limit": 20, "offset": 0}),
    ("hippo_trust_report", {"answer": SENTINELLA}),
    ("hippo_consolidate", {"max_episodes": 50}),
    ("hippo_validate_claim", {"claim": SENTINELLA, "threshold": 0.6}),
    ("hippo_facts_recent", {"limit": 10}),
    ("hippo_skill_retire", {"skill_id": "abc123"}),
    ("hippo_search", {"query": SENTINELLA}),
    ("hippo_contradictions_scan", {"similarity_threshold": 0.75}),
    ("hippo_facts_find_conflicting", {"limit": 25}),
    ("hippo_episode_list", {"limit": 10, "offset": 0}),
    ("hippo_contradictions_list", {"only_unresolved": True}),
]

print(f"  modalita': {os.environ['ENGRAM_CAPABILITY_GATE']} · log: {LOG}")
print(f"  tool classificati nel registro: {len(REGISTRY._caps)}\n")

bloccate = []
for nome, args in CHIAMATE:
    ok, msg = _capability_gate(nome, args)
    if not ok:
        bloccate.append((nome, msg))

print(f"  ① chiamate BLOCCATE: {len(bloccate)}/{len(CHIAMATE)}"
      f"   {'ACCESO (fail-open)' if not bloccate else 'SPENTO: ha bloccato!'}")

righe = [json.loads(x) for x in io.open(LOG, encoding="utf-8").read().splitlines()
         if x.strip()] if os.path.exists(LOG) else []
deny = [r for r in righe if r.get("outcome") == "cap_deny"]
print(f"  ② righe di avviso scritte: {len(deny)}/{len(CHIAMATE)}"
      f"   {'ACCESO' if len(deny) == len(CHIAMATE) else 'da guardare'}")

con_chiavi = [r for r in deny if (r.get("detail") or {}).get("arg_keys")]
print(f"  ③ righe che dicono QUALI parametri: {len(con_chiavi)}/{len(deny)}"
      f"   {'ACCESO' if len(con_chiavi) == len(deny) else 'SPENTO'}")

testo = io.open(LOG, encoding="utf-8").read() if os.path.exists(LOG) else ""
print(f"  ④ il valore-sentinella e' finito nel log: {SENTINELLA in testo}"
      f"   {'ACCESO (non c e)' if SENTINELLA not in testo else 'SPENTO: FUGA DI DATI'}")

print("\n  == COSA DICE DAVVERO UNA RIGA DI AVVISO (le prime 4) ==")
for r in deny[:4]:
    print(f"    tool={r.get('tool')}")
    print(f"      arg_keys={(r.get('detail') or {}).get('arg_keys')}")
    print(f"      outcome={r.get('outcome')} · error={str(r.get('error'))[:78]}")

print(f"\n  peso: {len(testo)} byte per {len(deny)} righe"
      f" = {len(testo)/max(1,len(deny)):.0f} byte/riga")
print(f"  ⇒ al ritmo misurato (112,2 righe/ora attiva):"
      f" {112.2*len(testo)/max(1,len(deny))/1024:.1f} KB/ora attiva")
