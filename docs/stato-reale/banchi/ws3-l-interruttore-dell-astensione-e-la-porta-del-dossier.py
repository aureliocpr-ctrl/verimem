"""`ENGRAM_MIN_RELEVANCE` — «l'interruttore unico su OGNI superficie» — e la
porta che la guida raccomanda PER l'astensione.

DA DOVE VIENE. `relevance_floor.env_floor` si descrive cosi': *«The single
switch that turns "knows when it doesn't know" ON across every surface (SDK
`explain()`, console, gateway)»*, e piu' sotto **il file stesso racconta di
essersi gia' sbagliato una volta**: *«"Across every surface" was the intent and
for a year it was not the fact: this function had ONE caller in the product»*.
⇒ La classe e' nota. La domanda e' se sia CHIUSA.

LETTURA, prima di eseguire (`git grep min_relevance -- verimem/mcp_server.py`):

    hippo_facts_recall     (:13803)  _mr = args.get(...) or env_floor_if_set()
    hippo_recall_history   (:8145)   _mrh = args.get(...) or env_floor_if_set()
    hippo_trust_report     (:8183)   float(arguments.get("min_relevance", 0.0))

⇒ **La terza non legge l'ambiente.** E `trust_report.py` non lo legge per suo
conto (`min_relevance: float = 0.0` nella firma, nessun `env_floor`): il
controllo di lettura non e' caduto.

🔑 PERCHE' PROPRIO QUESTA PORTA CONTA. E' quella che la guida degli agenti
addita per sapere se lo store possa rispondere: *«To learn WHETHER the store
can answer at all, ask verimem_trust_report»*. L'interruttore che accende
«sa di non sapere» non raggiunge la porta del non-sapere.

⚖️ COSA NON STO DICENDO: che `trust_report` non si astenga. Si astiene per
un'ALTRA via — `ce_gate`, acceso di default dal 2026-07-29 su questa porta. La
divergenza e' sul PAVIMENTO: un operatore che alza `ENGRAM_MIN_RELEVANCE`
cambia due porte su tre e non lo sa da nessuna parte.

═══════════════════════════════════════════════════════════════════════════════
🔑 IL CONTROLLO CHE DEVE POTER FALLIRE: con l'ambiente impostato,
`hippo_facts_recall` DEVE riportare il pavimento. Se non lo riportasse nemmeno
lui, non ci sarebbe nessuna divergenza fra porte da misurare — ci sarebbe un
fenomeno diverso, e il banco non concluderebbe.
⚠️ LA POPOLAZIONE OPPOSTA: senza ambiente le due porte devono dire la STESSA
cosa. Se divergessero anche li', la causa non sarebbe l'ambiente.
═══════════════════════════════════════════════════════════════════════════════

REGIME: un processo, store TEMPORANEO, un fatto, porte MCP in-process, giudice
locale ASSENTE per costruzione (`ENGRAM_LOCAL_GATE_MODEL` su una dir vuota: nessuno
scaricamento). Lo store di Aurelio non e' toccato.

    python docs/stato-reale/banchi/ws3-l-interruttore-dell-astensione-e-la-porta-del-dossier.py
"""

from __future__ import annotations

import json
import subprocess
import sys

FATTO = "La penale del contratto Rossi e' 120 euro al giorno."
FONTE = "Contratto Rossi, articolo 7: penale di 120 euro al giorno di ritardo."
DOMANDA = "quanto e' la penale del contratto Rossi"
PAVIMENTO = "0.99"

FIGLIO = r'''
import asyncio, json, os, sys, tempfile
os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()
os.environ["ENGRAM_LOCAL_GATE_MODEL"] = tempfile.mkdtemp()   # giudice assente
os.environ.pop("ENGRAM_MIN_RELEVANCE", None)

from verimem import mcp_server

fatto, fonte, domanda, pavimento = sys.argv[1:5]

def chiama(nome, args):
    return json.loads(asyncio.run(mcp_server._call_tool_impl(nome, args))[0].text)

chiama("hippo_remember", {"proposition": fatto, "source": fonte, "topic": "pav/x"})

righe = []
for regime in ("ambiente NON impostato", f"ENGRAM_MIN_RELEVANCE={pavimento}"):
    if regime.startswith("ENGRAM"):
        os.environ["ENGRAM_MIN_RELEVANCE"] = pavimento
    for porta, args in (
            ("hippo_facts_recall", {"query": domanda, "k": 5}),
            ("hippo_trust_report", {"query": domanda, "k": 5})):
        try:
            d = chiama(porta, args)
            righe.append({"regime": regime, "porta": porta,
                          "pavimento_riportato": d.get("min_relevance"),
                          "n": len(d.get("results") or d.get("facts") or
                                   d.get("items") or []),
                          "astenuta": d.get("abstained")})
        except Exception as e:
            righe.append({"regime": regime, "porta": porta,
                          "pavimento_riportato": f"ERRORE {type(e).__name__}",
                          "n": -1, "astenuta": None})

print(json.dumps(righe, ensure_ascii=False, default=str))
'''


def main() -> int:
    p = subprocess.run([sys.executable, "-c", FIGLIO,
                        FATTO, FONTE, DOMANDA, PAVIMENTO],
                       capture_output=True, text=True, timeout=2400)
    if p.returncode != 0:
        print(f"  PROCESSO MORTO exit={p.returncode}: {p.stderr.strip()[-400:]}")
        return 1
    righe = json.loads(p.stdout.strip().splitlines()[-1])

    print(f"  {'regime':<28} {'porta':<22} {'pavimento riportato':<22} n")
    print("  " + "-" * 82)
    for r in righe:
        print(f"  {r['regime']:<28} {r['porta']:<22} "
              f"{str(r['pavimento_riportato']):<22} {r['n']}")

    def _pav(regime_prefisso: str, porta: str):
        for r in righe:
            if r["regime"].startswith(regime_prefisso) and r["porta"] == porta:
                return r["pavimento_riportato"]
        return "?"

    rec_on = _pav("ENGRAM", "hippo_facts_recall")
    tr_on = _pav("ENGRAM", "hippo_trust_report")
    rec_off = _pav("ambiente", "hippo_facts_recall")
    tr_off = _pav("ambiente", "hippo_trust_report")

    def _senza_pavimento(v) -> bool:
        """`None` e `0.0` sono LO STESSO significato: nessun pavimento.

        ⚠️ PRIMA STESURA CADUTA QUI, e la lascio scritta: confrontavo le
        RAPPRESENTAZIONI (`rec_off != tr_off`) e il banco si e' fermato sulla
        sua stessa popolazione opposta dichiarando «le due porte divergono
        gia' senza ambiente» — leggendo `None` contro `0.0`. Il difetto era
        nel misuratore, non nel prodotto.
        📌 Reperto minore che resta: le due porte scrivono «nessun
        pavimento» in due modi diversi nella ricevuta.
        """
        try:
            return v is None or float(v) <= 0.0
        except (TypeError, ValueError):
            return False

    print(f"\n  [1] CONTROLLO — con l'ambiente, `facts_recall` riporta il "
          f"pavimento: {rec_on}")
    if not isinstance(rec_on, (int, float)) or float(rec_on or 0) <= 0:
        print("      CONTROLLO CADUTO: nemmeno la porta che LEGGE l'ambiente lo")
        print("      riporta ⇒ non c'e' divergenza fra porte da misurare qui.")
        print("      NESSUN VERDETTO.")
        return 1

    print(f"  [2] POPOLAZIONE OPPOSTA — senza ambiente: recall={rec_off} · "
          f"trust_report={tr_off}")
    if _senza_pavimento(rec_off) != _senza_pavimento(tr_off):
        print("      ⚠️ le due porte divergono GIA' senza ambiente: la causa")
        print("      non e' l'interruttore. NESSUN VERDETTO su di esso.")
        return 1

    print("\n  ══ VERDETTO ══")
    if not isinstance(tr_on, (int, float)) or float(tr_on or 0) <= 0:
        print(f"     🔴 L'INTERRUTTORE NON RAGGIUNGE `hippo_trust_report`: "
              f"pavimento {rec_on} su `facts_recall`, {tr_on} sul dossier.")
        print("     ⇒ Un operatore che alza ENGRAM_MIN_RELEVANCE cambia due")
        print("     porte MCP su tre, e la terza e' quella che la guida addita")
        print("     PER l'astensione. Il docstring di `env_floor` promette")
        print("     «across every surface» — e racconta di essersi gia'")
        print("     sbagliato una volta sulla stessa parola.")
    else:
        print(f"     🟢 entrambe le porte portano il pavimento ({tr_on}): la")
        print("     lettura del sorgente era incompleta.")

    print("\n  ⚠️ LIMITI: un fatto, una domanda, un valore di pavimento, giudice")
    print("     locale assente. NON misura se l'astensione di `trust_report`")
    print("     funzioni (quella passa da `ce_gate`, che qui non puo' girare):")
    print("     misura SOLO dove arriva l'interruttore.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
