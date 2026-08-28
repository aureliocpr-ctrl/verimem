r"""La negazione passa allo stesso modo su SDK e su CLI?

Il mio 46 su 108 della riga 12 e' misurato SOLO sulla porta SDK. @ws2 ha misurato che
sulla SUPERSESSIONE le porte divergono (su MCP i record coesistono, su SDK e CLI vengono
ritirati) e @lead-audit ha fatto di quella disparita' una cella di testa. Se le porte
divergono la', non ho ragione di assumere che convergano sulla NEGAZIONE: finora l'ho
assunto e non l'ho mai misurato.

C'e' un motivo tecnico in piu' per dubitarne: `verimem save` passa `meta_narrative=True`
(misurato da @ws8, `continuity.py:225`), che spegne `L1`. Sul percorso della negazione L1
non e' il layer che decide, ma il percorso NON e' lo stesso e va misurato invece che
dedotto.

RISULTATO (28/08 19:44) — LE DUE PORTE NON DIVERGONO SULLA NEGAZIONE:

  in-process, un solo processo:      SDK 5 su 6   ·   CLI 5 su 6
  a PROCESSI SEPARATI (il controllo): SDK 5 su 6   ·   CLI 5 su 6
  e non coincide solo il CONTEGGIO: coincide il CASO. `OMEGA` e' l'unico giudicato
  correttamente su ENTRAMBE le porte (SDK 0.46 quarantined · CLI quarantined), gli altri
  cinque sono ammessi su entrambe. **Sei soggetti su sei, stesso verdetto.**
  Controlli su ogni porta: A (la fonte sostiene) SDK 99.99 / CLI admitted · C (neutra)
  SDK 0.06 quarantined / CLI quarantined ⇒ entrambe le porte separano.

=> Il 46 su 108 della riga 12 NON e' un fatto della sola porta SDK: si estende alla CLI,
   che e' la porta con cui scriviamo (`verimem save`). E `meta_narrative=True`, che la CLI
   passa e che spegne `L1`, NON cambia l'esito su questa classe — coerente col fatto che
   qui a decidere e' il giudice, non un layer lessicale.
=> Per la cella di testa di F3 (@ws2, @lead-audit): la disparita' fra porte e' misurata
   sulla SUPERSESSIONE e **non si estende a questa classe di giudizio**. Le porte
   divergono dove divergono, non ovunque.

⚠️ DIFETTO DEL PRIMO BANCO, trovato leggendo l'output integrale invece di filtrarlo, e
   dichiarato: chiamando la CLI **in-process** il campo `surface` resta appiccicato —
   dopo la prima chiamata CLI anche i write SDK vengono registrati `surface=cli`
   (`topic=porte/sdk-1` con `surface=cli`). Il conteggio non ne risente (i topic sono
   distinti e i verdetti si leggono uno per uno), ma **il campo che dovrebbe dire da quale
   porta viene una scrittura mente**, e per questo il risultato e' stato ricontrollato a
   processi separati. 📌 E' materiale F3: se `surface` e' contaminabile in-process, chi lo
   usa per attribuire una scrittura a una porta puo' sbagliare.

CASO: il piu' netto della serie, cosi' una differenza si vede — schema «e' vuoto» con
200 parole di riempitivo, che su SDK da' 12 errori su 18.
SEI SOGGETTI, tre per lingua. Stessa fonte, stesso claim, stesso store, un processo.

CONTROLLI su OGNI porta, senza i quali il confronto non significa niente:
  A  la fonte SOSTIENE  -> deve restare alta
  C  la fonte e' NEUTRA -> deve restare al pavimento
Se una porta non separa nemmeno A da C, il confronto fra porte non dice nulla.

REGIME: store temporaneo isolato via `HIPPO_DATA_DIR` (⚠️ `ENGRAM_DATA_DIR` NON isola),
FUORI da pytest, un solo processo per entrambe le porte cosi' i modelli si caricano una
volta e la seconda porta non paga il cold start.

RIPRODUCI:  python docs/stato-reale/banchi/ws6-C7-la-negazione-sulle-due-porte.py
"""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
from pathlib import Path

CASI = [
    ("IT", "Il registro ALFA elenca le misure del progetto.", "Il registro ALFA e' vuoto."),
    ("IT", "Il deposito DELTA contiene le forniture invernali.", "Il deposito DELTA e' vuoto."),
    ("IT", "Il collaudo EPSILON copre i moduli consegnati.", "Il collaudo EPSILON e' vuoto."),
    ("EN", "The GAMMA ledger lists the project measurements.", "The GAMMA ledger is empty."),
    ("EN", "The OMEGA warehouse holds the winter supplies.", "The OMEGA warehouse is empty."),
    ("EN", "The KAPPA review covers the delivered modules.", "The KAPPA review is empty."),
]


def main() -> None:
    repo = Path(__file__).resolve().parents[3]
    coda = " ".join((repo / "docs" / "BENCHMARKS.md").read_text(encoding="utf-8").split()[:200])

    from verimem.client import Memory
    from verimem.config import CONFIG
    print(f"store isolato: {CONFIG.semantic_db}")
    mem = Memory(str(CONFIG.semantic_db))
    for i in range(2):  # warm-up: i due caricamenti, buttati
        mem.add(f"Il registro WARMUP{i} elenca le misure.", topic="porte/warmup",
                source=f"Il registro WARMUP{i} elenca le misure.")

    def via_sdk(claim, src, topic):
        r = mem.add(claim, topic=topic, source=src) or {}
        return r.get("status", "?"), r.get("grounding_score")

    def via_cli(claim, src, topic):
        """La CLI vera, chiamata in-process: stesso comando che usiamo noi."""
        from verimem.cli import main as cli_main
        buf = io.StringIO()
        argv = sys.argv
        sys.argv = ["verimem", "save", claim, "--topic", topic, "--source", src]
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
                try:
                    cli_main()
                except SystemExit:
                    pass
        finally:
            sys.argv = argv
        out = buf.getvalue()
        st = "quarantined" if "quarantined" in out else ("admitted" if "admitted" in out else "?")
        return st, out

    conta = {"SDK": [0, 0], "CLI": [0, 0]}
    print(f"\n{'soggetto':<46} {'SDK':<22} {'CLI'}")
    for i, (ling, claim, nega) in enumerate(CASI):
        f_nega = f"{nega}\n\n{coda}"
        s_st, s_g = via_sdk(claim, f_nega, f"porte/sdk-{i}")
        c_st, c_out = via_cli(claim, f_nega, f"porte/cli-{i}")
        for porta, st in (("SDK", s_st), ("CLI", c_st)):
            conta[porta][0] += 1
            conta[porta][1] += 0 if st == "quarantined" else 1
        g = f"{s_g:.2f}" if isinstance(s_g, (int, float)) else str(s_g)
        print(f"{claim[:46]:<46} {s_st[:12]:<12} {g:>8}  {c_st}")
        if i == 0:  # l'output CLI INTEGRALE del primo caso: non si filtra la misura
            print("   --- output CLI integrale del primo caso ---")
            for r in c_out.splitlines():
                print(f"   | {r}")

    print("\n=== CONTROLLI, su ogni porta ===")
    claim, nega = CASI[0][1], CASI[0][2]
    for et, src in (("A sostiene", f"{claim}\n\n{coda}"), ("C neutra", coda)):
        s_st, s_g = via_sdk(claim, src, f"porte/ctrl-sdk-{et[0]}")
        c_st, _ = via_cli(claim, src, f"porte/ctrl-cli-{et[0]}")
        g = f"{s_g:.2f}" if isinstance(s_g, (int, float)) else str(s_g)
        print(f"   {et:<12} SDK {s_st[:12]:<12} {g:>8}   CLI {c_st}")

    print("\n=== NEGAZIONI AMMESSE PER ERRORE ===")
    for porta in ("SDK", "CLI"):
        n, bad = conta[porta]
        print(f"   {porta}: {bad} su {n}")


if __name__ == "__main__":
    main()
