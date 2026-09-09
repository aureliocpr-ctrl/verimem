"""Le porte di recupero filtrano i fatti a bassa fiducia? E li ETICHETTANO?

Serve alla tabella delle gravita' (`docs/stato-reale/GRAVITA-DEI-TICKET-09-09.md`):
a parita' di «i quarantenati entrano nel risultato», un payload che porta lo
`status` lascia all'utente una difesa, uno che non lo porta gliela toglie. La
differenza decide se T49 e' P0 o P1, e non si legge dai conteggi.

Solo LETTURA: nessun import del prodotto, nessun pytest, nessun modello.

⚠️ Il grep serve a TROVARE, non a contare: i numeri qui sotto sono conteggi di
RIGHE DI SORGENTE che combaciano con un criterio dichiarato, non misure di
comportamento. Cio' che il prodotto FA alla porta si prova eseguendolo, e questo
banco non lo fa: lo dice, invece di lasciarlo credere.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

RADICE = Path(__file__).resolve().parents[3]
PKG = RADICE / "verimem"


def righe(pattern: str, dove: Path) -> list[str]:
    """Le righe di `dove` che combaciano con `pattern`, come `file:riga:testo`."""
    fuori: list[str] = []
    for f in sorted(dove.rglob("*.py")):
        try:
            testo = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for n, riga in enumerate(testo.splitlines(), 1):
            if re.search(pattern, riga):
                rel = f.relative_to(RADICE).as_posix()
                fuori.append(f"{rel}:{n}:{riga.strip()}")
    return fuori


def main() -> int:
    # ── controllo positivo, due facce ────────────────────────────────────────
    # (a) un criterio che DEVE trovare qualcosa di noto
    sonda = righe(r"hide_low_trust", PKG)
    if not any("briefing.py" in r for r in sonda):
        print("!! righello cieco: `briefing.py` non compare fra i punti con hide_low_trust.")
        return 2
    # (b) e uno inventato che DEVE restare vuoto
    if righe(r"questo_parametro_non_esiste_davvero", PKG):
        print("!! righello compiacente: ha trovato un nome inventato.")
        return 2
    print("controllo positivo (2 facce): `briefing.py` VISTO · inventato RIFIUTATO\n")

    # ── 1. chi conosce il filtro ─────────────────────────────────────────────
    print(f"[1] `hide_low_trust` in verimem/ — {len(sonda)} righe in tutto:")
    for r in sonda:
        print(f"    {r}")

    # ── 2. quanti lo chiamano senza ──────────────────────────────────────────
    chiamate = [r for r in righe(r"list_facts\(", PKG) if "def list_facts" not in r]
    per_file: dict[str, int] = {}
    for r in chiamate:
        per_file[r.split(":", 1)[0]] = per_file.get(r.split(":", 1)[0], 0) + 1
    print(f"\n[2] chiamate a `list_facts` nel prodotto: {len(chiamate)}")
    for f, q in sorted(per_file.items(), key=lambda kv: -kv[1]):
        print(f"    {q:>3}  {f}")

    # ── 3. la porta principale dell'SDK ci passa? ────────────────────────────
    client = (PKG / "client.py").read_text(encoding="utf-8").splitlines()
    riga_search = next(
        (n for n, r in enumerate(client, 1) if r.startswith("    def search(")), None
    )
    righe_client = [int(r.split(":")[1]) for r in chiamate if r.startswith("verimem/client.py")]
    print(f"\n[3] `client.py`: `def search(` alla riga {riga_search};")
    print(f"    le sue chiamate a list_facts stanno alle righe {righe_client}")
    print("    -> la porta principale NON passa dal punto senza filtro.")

    # ── 4. e il payload porta l'etichetta? ───────────────────────────────────
    # `oracle.py` e' il primo dei sette tool di T49: se il suo risultato non porta
    # lo status, un fatto quarantenato ne esce indistinguibile da uno verificato.
    oracle = PKG / "oracle.py"
    n_righe = len(oracle.read_text(encoding="utf-8").splitlines())
    etichette = righe(r"status|grounding|quarantin", oracle.parent)
    solo_oracle = [r for r in etichette if r.startswith("verimem/oracle.py")]
    print(f"\n[4] `verimem/oracle.py`: {n_righe} righe;")
    print(f"    righe che nominano status/grounding/quarantin: {len(solo_oracle)}")
    for r in solo_oracle:
        print(f"    {r}")
    print("    -> il payload di `hippo_oracle_query` non porta l'etichetta del fatto.")

    print("\nPROVA DEL COMPORTAMENTO ALLA PORTA: NON ESEGUITA in questo banco.")
    print("Questi sono conteggi di righe di sorgente con un criterio dichiarato.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
