"""«~250ms total»: un numero di prestazione nella descrizione di un tool, senza
dire su quale corpus.

LA PROMESSA, dalla descrizione di `hippo_dashboard_overview_v2`: *«Unified
dashboard: ONE call returns health metrics + orphan suggestions + per-project
freshness signals. **Drops 3-5 separate MCP calls to ~250ms total.** Pure-local.»*

SWEEP DELLA COPERTURA, fatto PRIMA di misurare (regola nata stanotte dopo aver
scambiato «non presidiato» per «non presidiato in questo file»):

    tests/test_dashboard_overview.py      presidia il CONTENUTO
    tests/test_dashboard_overview_v2.py   (sezioni, health, orphan, topology)
    ⇒ nessuna asserzione sul TEMPO, nessuna su «pure-local»: `time` compare
      solo per i timestamp dei fatti.

⇒ **Il contenuto e' presidiato, il numero no.** Ed e' il mio filone: *cio' che
il prodotto fa e cio' che dice di fare invecchiano a velocita' diverse*.

🔑 LA DOMANDA NON E' «250 e' vero?» — su uno store vuoto qualunque numero e'
facile. E' **«il numero dipende dal corpus, e la descrizione non dice quale?»**.
Se dipende, «~250ms» e' una misura senza il suo regime: vera dove e' stata
presa, muta altrove. Se non dipende, dice poco ma non inganna.

═══════════════════════════════════════════════════════════════════════════════
🔑 IL CONTROLLO CHE DEVE POTER FALLIRE: la chiamata deve RESTITUIRE le sue
sezioni. Cronometrare una risposta vuota misurerebbe il tempo di un no-op — e
la sezione c'e' o non c'e' si legge dalle CHIAVI, che il banco stampa.
⚠️ LA PRIMA CHIAMATA NON CONTA: paga il caricamento a freddo. Si misura a
caldo, con tre ripetizioni, e si riporta la MEDIANA — e la prima resta
stampata, perche' e' quella che paga un utente al primo uso.
═══════════════════════════════════════════════════════════════════════════════

REGIME: un processo, DUE store temporanei (uno vuoto, uno con 60 fatti — sopra
il pavimento dei 50 sotto il quale il retrieval prende un'altra strada),
giudice locale assente per costruzione. Una sola macchina, quindi i millisecondi
assoluti valgono per QUESTA macchina: cio' che si confronta e' il RAPPORTO fra
i due corpus, non il numero contro «250».
Lo store di Aurelio non e' toccato.

    python docs/stato-reale/banchi/ws3-un-numero-senza-il-corpus-su-cui-vale.py
"""

from __future__ import annotations

import json
import subprocess
import sys

PROMESSA_MS = 250.0

FIGLIO = r'''
import asyncio, json, os, statistics, sys, tempfile, time

os.environ["ENGRAM_LOCAL_GATE_MODEL"] = tempfile.mkdtemp()
os.environ.pop("ENGRAM_MIN_RELEVANCE", None)

def misura(n_fatti):
    os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()
    import importlib
    from verimem import mcp_server
    importlib.reload(mcp_server)

    def chiama(nome, args=None):
        return json.loads(asyncio.run(
            mcp_server._call_tool_impl(nome, args or {}))[0].text)

    for i in range(n_fatti):
        chiama("hippo_remember", {
            "proposition": f"Il magazzino K-{100 + i} di Rovigo ha {4000 + i} metri quadrati.",
            "source": f"Registro immobili, scheda K-{100 + i}: superficie {4000 + i} metri quadrati.",
            "topic": f"perf/{i % 7}"})

    t0 = time.perf_counter()
    primo = chiama("hippo_dashboard_overview_v2")
    freddo_ms = (time.perf_counter() - t0) * 1000.0

    caldi = []
    for _ in range(3):
        t = time.perf_counter()
        d = chiama("hippo_dashboard_overview_v2")
        caldi.append((time.perf_counter() - t) * 1000.0)

    return {"n_fatti": n_fatti, "freddo_ms": round(freddo_ms, 1),
            "mediana_ms": round(statistics.median(caldi), 1),
            "caldi_ms": [round(x, 1) for x in caldi],
            "chiavi": sorted(primo.keys())}

righe = [misura(0), misura(60)]
print(json.dumps(righe, ensure_ascii=False, default=str))
'''


def main() -> int:
    p = subprocess.run([sys.executable, "-c", FIGLIO],
                       capture_output=True, text=True, timeout=2400)
    if p.returncode != 0:
        print(f"  PROCESSO MORTO exit={p.returncode}: {p.stderr.strip()[-500:]}")
        return 1
    righe = json.loads(p.stdout.strip().splitlines()[-1])

    print(f"  {'corpus':<14} {'a freddo':>10} {'mediana a caldo':>17}   le tre misure")
    print("  " + "-" * 72)
    for r in righe:
        print(f"  {str(r['n_fatti']) + ' fatti':<14} {r['freddo_ms']:>9.1f}ms "
              f"{r['mediana_ms']:>16.1f}ms   {r['caldi_ms']}")

    vuoto, pieno = righe[0], righe[1]
    print(f"\n  [1] CONTROLLO — la chiamata restituisce le sue sezioni: "
          f"{len(pieno['chiavi'])} chiavi")
    print(f"      {pieno['chiavi']}")
    if len(pieno["chiavi"]) < 2:
        print("      CONTROLLO CADUTO: la risposta e' quasi vuota ⇒ starei")
        print("      cronometrando un no-op. NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    rapporto = (pieno["mediana_ms"] / vuoto["mediana_ms"]
                if vuoto["mediana_ms"] > 0 else float("inf"))
    print(f"     store vuoto  : mediana {vuoto['mediana_ms']:.1f} ms")
    print(f"     60 fatti     : mediana {pieno['mediana_ms']:.1f} ms")
    print(f"     rapporto     : {rapporto:.1f}x")

    if rapporto >= 2.0:
        print(f"\n     🔴 IL NUMERO DIPENDE DAL CORPUS ({rapporto:.1f}x fra due")
        print("     corpus entrambi PICCOLI) e la descrizione non dice su quale")
        print(f"     e' stato preso. «~{PROMESSA_MS:.0f}ms» e' una misura senza il")
        print("     suo regime: vera dove e' stata presa, muta altrove.")
    else:
        print(f"\n     🟢 il tempo NON dipende sensibilmente dal corpus "
              f"({rapporto:.1f}x): il numero dice poco ma non inganna.")

    sopra = [r for r in righe if r["mediana_ms"] > PROMESSA_MS]
    print(f"\n     rispetto a «~{PROMESSA_MS:.0f}ms»: "
          f"{len(sopra)} dei {len(righe)} corpus lo superano a caldo; "
          f"a FREDDO lo superano "
          f"{len([r for r in righe if r['freddo_ms'] > PROMESSA_MS])} su {len(righe)}.")
    print("     ⚠️ La prima chiamata e' quella che paga un utente al primo uso, e")
    print("     la descrizione non distingue fra il primo e i successivi.")

    print("\n  ⚠️ LIMITI: UNA macchina, due corpus entrambi piccoli, tre")
    print("     ripetizioni. I millisecondi assoluti NON sono confrontabili con")
    print("     quelli di chi ha scritto la descrizione: cio' che questo banco")
    print("     misura e' se il numero VARI col corpus, non se sia sbagliato.")
    print("     E NON verifica «Pure-local» (nessuna chiamata di rete), che e'")
    print("     l'altra affermazione senza presidio in quella descrizione.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
