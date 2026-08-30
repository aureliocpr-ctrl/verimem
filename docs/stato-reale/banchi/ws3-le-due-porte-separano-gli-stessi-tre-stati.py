"""Le due porte separano gli STESSI tre stati — e in un regime DIVERGONO.

DA DOVE VIENE. Il banco `ws3-il-campo-che-distingue-non-giudicato-da-giudicato`
ha verificato una promessa scritta nelle istruzioni del server MCP — «*it is
`grounding_score` that carries it — a number means a source was judged, `null`
means never judged*» — trovandola vera 3/3, **con un campo in piu'** (il layer
`L4-skipped` separa «*c'era una fonte non giudicata*» da «*fonte non ce n'era*»).

⚠️ Quel banco misurava **solo l'SDK**, e la promessa e' fatta **alle porte MCP**.
Verificarla dove non e' scritta e chiamarla verificata sarebbe misurare al
livello sbagliato.

⚠️ E C'E' UN PRECEDENTE CHE COSTA: il 29/08 il mio lettore cercava `warnings` su
una ricevuta MCP, che quella chiave **non ce l'ha** (`anti_confab_warnings`), e
ne usci' un meccanismo falso pubblicato e ritirato in 15 minuti. Da li' nasce
`_ricevuta.py`, che **SOLLEVA** invece di restituire una lista vuota. **Qui si
usa quello.**

═══════════════════════════════════════════════════════════════════════════════
🔴 IL BANCO E' ALLA SECONDA STESURA, E LA PRIMA AVEVA CONCLUSO IL FALSO.

La prima versione girava nel regime EREDITATO dalla macchina
(`HIPPO_ENCODE_DELEGATE_ONLY=1`) e stampava::

    mcp: firme (gs, L4-skipped) = ['0.56/False', '0.56/False', 'null/False']
                                                   → NON separa

Conclusione scritta: «*l'SDK separa i tre stati, MCP no ⇒ la promessa vale dove
non e' scritta e cade dove lo e'*». **Falso.** MCP non «non separava»: **non
aveva il terzo stato da separare**, perche' in delegate-only delega al daemon e
il giudizio arriva comunque. Una popolazione che **non contiene il caso** si
legge come «il caso non e' distinto».

🔑 *E' il rovescio di «una misura che non c'e' si legge come perfetta»: uno stato
che non si produce si legge come «non distinto».* Il regime va scelto per
**produrre gli stati che si vogliono separare**, non ereditato dall'ambiente.
═══════════════════════════════════════════════════════════════════════════════

DUE DOMANDE, e servono due regimi diversi:

    [A] REGIME PULITO — `HIPPO_ENCODE_DELEGATE_ONLY=0`: nessuna porta delega,
        quindi il giudice assente e' assente per entrambe e i tre stati
        ESISTONO su tutt'e due. ⇒ **ogni porta li separa leggendo campi?**
    [B] REGIME DELLA MACCHINA — `=1` con daemon vivo e modello locale assente:
        ⇒ **le due porte danno lo stesso verdetto?**

LA PREDIZIONE, scritta prima di eseguire: **[A] entrambe separano** (MCP deriva
l'esito dalla funzione unica dell'SDK, `esito_del_moat`, e il commento a
`mcp_server.py:13400` lo dichiara); **[B] divergono**, perche' l'inversione A/B
gia' fatta mostra che MCP ottiene il giudizio e l'SDK no, in **entrambi** gli
ordini — quindi non e' l'ordine, e' la porta.

CONDIZIONE DI FALSIFICAZIONE: se in [A] MCP non separa i tre stati, la promessa
cade **sulla porta dove e' scritta**, ed e' il reperto piu' grave del giro.

CONTROLLO CHE DEVE POTER FALLIRE: a giudice presente la fonte NEGA il claim
(«500 euro» contro «120 euro») ed **entrambe le porte devono quarantinare**. Se
una non lo facesse, misurerei una porta col moat spento.

⚠️ CONFONDENTE DICHIARATO, non eliminabile: le due porte **non sono nello stesso
regime** — `mcp_server._ag()` valorizza `semantic.repo_root`, `Memory()` lo
lascia `None` (misurato il 29/08). Si misura cosa dicono **cosi' come sono**.

REGIME: un processo per cella, store TEMPORANEO, `Memory()` senza path esplicito.
Il giudice locale si rende assente puntando `ENGRAM_LOCAL_GATE_MODEL` a una
cartella vuota — nessun download, ⛔ nessun `warmup`. Store di Aurelio intatto.

    python docs/stato-reale/banchi/ws3-le-due-porte-separano-gli-stessi-tre-stati.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ricevuta import RicevutaIlleggibile, strati  # noqa: E402

CLAIM = "La penale e' di 500 euro al giorno."
FONTE = "Il contratto fissa la penale in 120 euro al giorno."

FIGLIO = r'''
import asyncio, json, os, sys, tempfile
os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()
os.environ["HIPPO_ENCODE_DELEGATE_ONLY"] = sys.argv[1]   # il regime, ESPLICITO
if sys.argv[2] == "assente":
    os.environ["ENGRAM_LOCAL_GATE_MODEL"] = tempfile.mkdtemp()   # cartella VUOTA
claim, fonte, porta = sys.argv[3], sys.argv[4], sys.argv[5]

if porta == "sdk":
    from verimem.client import Memory
    kw = {"source": fonte} if fonte else {}
    r = Memory().add(claim, topic="porte/s", validate="full", **kw)
else:
    from verimem import mcp_server
    args = {"proposition": claim, "topic": "porte/m"}
    if fonte:
        args["source"] = fonte
    out = asyncio.run(mcp_server._call_tool_impl("hippo_remember", args))
    r = json.loads("\n".join(getattr(c, "text", "") for c in out))
print(json.dumps(r, default=str, ensure_ascii=False))
'''

#: (etichetta, giudice, fonte) — i tre stati che si vogliono separare
STATI: list[tuple[str, str, str]] = [
    ("giudicato", "presente", FONTE),
    ("fonte NON giudicata", "assente", FONTE),
    ("nessuna fonte", "presente", ""),
]
PORTE = ("sdk", "mcp")


def _cella(delegate: str, giudice: str, fonte: str, porta: str,
           dove: str) -> tuple[str, str, bool]:
    p = subprocess.run(
        [sys.executable, "-c", FIGLIO, delegate, giudice, CLAIM, fonte, porta],
        capture_output=True, text=True, timeout=1800)
    if p.returncode != 0:
        raise RuntimeError(f"processo morto exit={p.returncode}: "
                           f"{p.stderr.strip()[-120:]}")
    r = json.loads(p.stdout.strip().splitlines()[-1])
    lay = strati(r, dove=dove)            # SOLLEVA se la ricevuta e' ignota
    gs = r.get("grounding_score")
    return (str(r.get("status")),
            "null" if gs is None else f"{float(gs):.2f}",
            any("L4-skipped" in x for x in lay))


def main() -> int:
    print("  PROMESSA (istruzioni MCP): `grounding_score` porta la separazione")
    print("  fra giudicato e non giudicato; `status` no.\n")

    # ── [A] regime PULITO: nessuna porta delega, i tre stati esistono ────────
    print("  [A] REGIME PULITO — HIPPO_ENCODE_DELEGATE_ONLY=0 (nessuno delega)")
    print(f"      {'stato':<22} {'porta':<5} {'status':<13} {'gs':<7} L4-skipped")
    print("      " + "-" * 62)
    letto: dict[tuple[str, str], tuple[str, str, bool]] = {}
    for etichetta, giudice, fonte in STATI:
        for porta in PORTE:
            try:
                s = _cella("0", giudice, fonte, porta, f"A/{etichetta}/{porta}")
            except (RicevutaIlleggibile, RuntimeError) as e:
                print(f"      {etichetta:<22} {porta:<5} FALLITA: {e}")
                return 1
            letto[(etichetta, porta)] = s
            print(f"      {etichetta if porta == 'sdk' else '':<22} {porta:<5} "
                  f"{s[0]:<13} {s[1]:<7} {'SI' if s[2] else 'no'}")

    print("\n      CONTROLLO — a giudice presente la fonte che NEGA quarantina:")
    ctrl = {p: letto[("giudicato", p)][0] == "quarantined" for p in PORTE}
    print("        " + " · ".join(f"{p} {'SI' if v else 'NO'}"
                                   for p, v in ctrl.items()))
    if not all(ctrl.values()):
        print("        CONTROLLO CADUTO: una porta non ferma una fonte che nega")
        print("        ⇒ misuro un moat spento. NESSUN VERDETTO.")
        return 1

    separa = {}
    for porta in PORTE:
        firme = {e: letto[(e, porta)][1:] for e, _, _ in STATI}
        separa[porta] = len(set(firme.values())) == len(STATI)
        print(f"      {porta}: firme (gs, L4-skipped) = "
              f"{[f'{a}/{b}' for a, b in firme.values()]} → "
              f"{'SEPARA' if separa[porta] else 'NON separa'}")

    # ── [B] regime della macchina: le due porte divergono? ──────────────────
    print("\n  [B] REGIME DELLA MACCHINA — DELEGATE_ONLY=1, modello locale ASSENTE")
    print(f"      {'porta':<5} {'status':<13} {'gs':<7} L4-skipped")
    print("      " + "-" * 40)
    b: dict[str, tuple[str, str, bool]] = {}
    for porta in PORTE:
        try:
            b[porta] = _cella("1", "assente", FONTE, porta, f"B/{porta}")
        except (RicevutaIlleggibile, RuntimeError) as e:
            print(f"      {porta:<5} FALLITA: {e}")
            return 1
        print(f"      {porta:<5} {b[porta][0]:<13} {b[porta][1]:<7} "
              f"{'SI' if b[porta][2] else 'no'}")

    print("\n  ══ VERDETTO ══")
    if all(separa.values()):
        print("     [A] 🟢 ENTRAMBE le porte separano i tre stati leggendo SOLO")
        print("     campi. La promessa vale anche dove e' SCRITTA.")
    elif separa["sdk"] and not separa["mcp"]:
        print("     [A] 🔴 MCP non separa i tre stati e l'SDK si': la promessa")
        print("     cade sulla porta dove e' scritta. Reperto grave.")
    else:
        print("     [A] 🔴 Nemmeno l'SDK separa in questo regime: rivedere il")
        print("     banco precedente prima di dire qualunque cosa.")

    if b["sdk"] != b["mcp"]:
        print("\n     [B] 🔴 LE DUE PORTE DIVERGONO con il modello locale assente")
        print("     e il daemon vivo: **MCP delega e ottiene il verdetto del")
        print("     moat, l'SDK no e ammette il claim non giudicato** — un claim")
        print("     che la sua fonte NEGA.")
        print("     ⚠️ NON e' l'ordine: verificato invertendo A e B, l'esito NON")
        print("     si scambia (MCP giudica per primo o per secondo, l'SDK mai).")
        print("     ⚠️ NON e' un difetto nascosto: il fail-open dell'SDK e'")
        print("     DICHIARATO (README:64) e la ricevuta lo scrive. Cio' che non")
        print("     e' dichiarato e' che MCP lo EVITI delegando ⇒ la stessa")
        print("     installazione da' due garanzie diverse secondo la porta, e")
        print("     chi legge il README non se lo aspetta.")
    else:
        print("\n     [B] 🟢 Le due porte danno lo stesso verdetto anche qui.")

    print("\n  ⚠️ LIMITI: un claim, una fonte, italiano. Le due porte NON sono")
    print("     nello stesso regime (`_ag()` valorizza `repo_root`, `Memory()`")
    print("     no). E [B] dipende da un daemon VIVO: senza, l'asimmetria")
    print("     sparisce — non e' una proprieta' del codice ma della macchina.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
