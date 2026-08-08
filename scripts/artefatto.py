"""Da QUALE artefatto sto misurando — una riga, prima di ogni verdetto.

    python scripts/artefatto.py

Zero dipendenze (nemmeno pytest) perché deve girare **anche dentro il venv di un
utente**, che è il posto in cui serve di più.

Perché esiste. Il 08/08 sette istanze hanno misurato Verimem importandolo dall'albero
di lavoro e hanno consegnato un documento che descriveva codice che nessun utente
possiede: il pacchetto pubblicato era la 0.7.0 del 22 luglio, 375 commit indietro, con
lo stesso numero di versione del repo. Da lì la regola: *ogni referto dichiari da quale
artefatto viene*.

Mancava l'altra metà, e l'abbiamo pagata lo stesso giorno. Un referto diceva «chi
installa ha il server MCP morto» (pacchetto: `mcp 2.0.0`, `AttributeError`); due
istanze hanno provato a falsificarlo rieseguendo **dal repo**, dove `mcp` è 1.26.0 e il
server parte, e hanno concluso «non si riproduce». Nessuna delle misure era sbagliata:
erano due artefatti.

⇒ **Anche ogni VERIFICA deve dichiarare l'artefatto, e deve usare lo stesso del
referto.** Una riesecuzione su un artefatto diverso non falsifica niente: produce un
secondo fatto, vero e non pertinente.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]


def riga_di_contesto() -> str:
    """`verimem X · mcp Y · da <pacchetto|albero> · git <sha> · <percorso>`."""
    import importlib.metadata as md

    def versione(nome: str) -> str:
        try:
            return md.version(nome)
        except Exception:  # noqa: BLE001 — l'assenza è essa stessa il dato
            return "assente"

    try:
        import verimem
        dove: Path | str = Path(verimem.__file__).parent
        # "site-packages" nel percorso = installato; altrimenti è un albero di lavoro.
        origine = ("pacchetto" if "site-packages" in str(dove)
                   else f"albero {Path(dove).parent.name}")
    except Exception:  # noqa: BLE001
        dove, origine = "?", "non importabile"

    def git(*a: str) -> str:
        try:
            return subprocess.run(["git", *a], cwd=RADICE, capture_output=True,
                                  text=True, timeout=30).stdout.strip()
        except Exception:  # noqa: BLE001 — fuori da un checkout è normale
            return ""

    # Lo SHA descrive l'albero, NON il pacchetto installato: mostrarlo accanto a
    # «da pacchetto» suggerirebbe che quel wheel venga da quel commit, ed è proprio
    # la confusione che questo strumento esiste per togliere.
    if origine == "pacchetto":
        coordinata = "git n/d (misuri il pacchetto, non l'albero)"
    else:
        sha = git("rev-parse", "--short", "HEAD") or "-"
        coordinata = f"git {sha}{' MODIFICATO' if git('status', '--porcelain') else ''}"
    return (f"verimem {versione('verimem')} · mcp {versione('mcp')} · da {origine} · "
            f"{coordinata} · {dove}")


if __name__ == "__main__":
    print(riga_di_contesto())
