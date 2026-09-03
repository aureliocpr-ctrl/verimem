"""I cancelli del tag, ESEGUIBILI — non una lista da spuntare a memoria.

═══ PERCHE' ESISTE ═══
Il piano delle versioni (docs/stato-reale/piano-versioni-2026-09-02.md) elenca i
cancelli della 0.7.2. Una lista in un documento la si legge e la si crede: il
2026-09-02 il gate del rilascio citava come prova un job che era rimasto
`skipped` per oltre 200 ore, e nessuno se n'era accorto perche' nessuno lo
ESEGUIVA. Questo file trasforma quella lista in un comando con un codice
d'uscita, cosi' «i cancelli sono chiusi» diventa una cosa che si misura.

    python scripts/cancelli_del_tag.py            # dice quali sono aperti
    python scripts/cancelli_del_tag.py --sha X    # sul commit che si vuole taggare

═══ COSA NON PROVA — leggerlo verde e concludere troppo e' il modo di ═══
═══ fabbricare la prossima riga scaduta del gate                      ═══
· NON esegue lo smoke da utente: quello richiede un wheel candidato e due
  macchine (WSL e Windows), e va fatto PRIMA del tag da persone diverse. Qui si
  controlla soltanto che sia stato DICHIARATO, con il suo esito e da chi.
· NON giudica il CONTENUTO del CHANGELOG: controlla che la voce della versione
  esista e non sia vuota. Che dica il vero lo decide chi legge, non un grep.
· NON verifica PyPI: il pacchetto non e' ancora pubblicato quando questo gira.

═══ L'ESITO ═══
  0  tutti i cancelli misurabili qui sono chiusi
  1  almeno uno e' aperto — la riga dice quale e cosa manca
  2  non ho potuto misurare (rete, git, file assenti): NON e' un verdetto
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]


def sh(*args: str) -> tuple[str, int]:
    p = subprocess.run(list(args), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=RADICE,
                       check=False, timeout=180)
    return p.stdout.strip(), p.returncode


class Esito:
    def __init__(self) -> None:
        self.aperti: list[str] = []
        self.non_misurati: list[str] = []

    def cancello(self, nome: str, ok: bool | None, dettaglio: str = "") -> None:
        if ok is None:
            print(f"  ?   {nome:<44} {dettaglio}")
            self.non_misurati.append(nome)
        elif ok:
            print(f"  OK  {nome:<44} {dettaglio}")
        else:
            print(f"  NO  {nome:<44} {dettaglio}")
            self.aperti.append(f"{nome}: {dettaglio}")


def versione_di_record() -> str | None:
    m = re.search(r'(?m)^version\s*=\s*"([^"]+)"',
                  (RADICE / "pyproject.toml").read_text(encoding="utf-8"))
    return m.group(1) if m else None


def c_versioni(e: Esito, pv: str) -> None:
    """Le superfici che dichiarano la versione devono dire la STESSA cosa.

    `server.json` e' la quinta e la piu' recente: il 2026-09-02 diceva 0.7.2
    mentre le altre quattro dicevano 0.7.6, e il presidio non la guardava.
    """
    superfici: list[tuple[str, str | None]] = [("pyproject.toml", pv)]
    m = re.search(r'__version__\s*=\s*"([^"]+)"',
                  (RADICE / "verimem" / "__init__.py").read_text(encoding="utf-8"))
    superfici.append(("verimem/__init__.py", m.group(1) if m else None))
    pj = json.loads((RADICE / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    superfici.append((".claude-plugin/plugin.json", pj.get("version")))
    sj_path = RADICE / "server.json"
    if sj_path.exists():
        sj = json.loads(sj_path.read_text(encoding="utf-8"))
        superfici.append(("server.json", sj.get("version")))
        for i, pkg in enumerate(sj.get("packages", [])):
            if "version" in pkg:
                superfici.append((f"server.json packages[{i}]", pkg["version"]))
    st = (RADICE / "STATE.md")
    if st.exists():
        m = re.search(r"(?m)^\|\s*Release\s*\|\s*v?([0-9][0-9.]*)", st.read_text(encoding="utf-8"))
        superfici.append(("STATE.md riga Release", m.group(1) if m else None))

    diverse = {v for _, v in superfici if v is not None} - {pv}
    for nome, v in superfici:
        if v is None:
            e.cancello(f"versione in {nome}", None, "non letta")
    e.cancello("le superfici di versione concordano", not diverse,
               f"pyproject={pv}" + (f" ma {', '.join(sorted(diverse))} altrove" if diverse else ""))


def c_changelog(e: Esito, pv: str) -> None:
    testo = (RADICE / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(rf"(?ms)^## \[{re.escape(pv)}\][^\n]*\n(.*?)(?=^## \[|\Z)", testo)
    corpo = (m.group(1).strip() if m else "")
    e.cancello(f"CHANGELOG ha la voce [{pv}]", bool(m),
               f"{len(corpo.splitlines())} righe" if m else "assente")
    if m:
        e.cancello("la voce non e' vuota", len(corpo) > 200, f"{len(corpo)} caratteri")


def c_ci(e: Esito, sha: str) -> None:
    """Il verde deve stare sul commit CHE SI TAGGA, non su un antenato."""
    out, code = sh("gh", "api",
                   f"repos/:owner/:repo/actions/workflows/ci.yml/runs?head_sha={sha}",
                   "--jq", '[.workflow_runs[] | {n:.run_number, s:.status, c:.conclusion}]')
    if code != 0:
        e.cancello("CI sul commit del tag", None, f"gh EXIT={code}")
        return
    runs = json.loads(out or "[]")
    if not runs:
        e.cancello("CI sul commit del tag", False,
                   f"NESSUN run su {sha[:8]} — «nessun run» non e' un verde")
        return
    vinc = [r for r in runs if r["s"] == "completed" and r["c"] == "success"]
    e.cancello("CI verde sul commit del tag", bool(vinc),
               f"#{vinc[0]['n']}" if vinc else f"{len(runs)} run, nessuno success")
    if vinc:
        out2, code2 = sh("gh", "api",
                         f"repos/:owner/:repo/actions/workflows/ci.yml/runs?head_sha={sha}",
                         "--jq", ".workflow_runs[0].id")
        if code2 == 0 and out2:
            out3, code3 = sh("gh", "api", f"repos/:owner/:repo/actions/runs/{out2}/jobs",
                             "--jq", '[.jobs[].conclusion] | {tot:length, ok:(map(select(.=="success"))|length)}')
            if code3 == 0:
                d = json.loads(out3)
                e.cancello("tutti i job del run sono success",
                           d["tot"] == d["ok"] and d["tot"] > 0, f"{d['ok']}/{d['tot']}")


def c_manifesti(e: Esito) -> None:
    banco = RADICE / "scripts" / "controlla_manifesti_distribuzione.py"
    if not banco.exists():
        e.cancello("manifesti di distribuzione", None, "banco assente")
        return
    _, code = sh(sys.executable, str(banco))
    e.cancello("manifesti + prova di proprieta' PyPI", code == 0, f"EXIT={code}")


def c_smoke(e: Esito, pv: str) -> None:
    """Non lo esegue: controlla che sia stato DICHIARATO, con esito e autore.

    Il piano lo vuole su DUE campi (WSL e Windows) e PRIMA del tag. Una
    dichiarazione che non nomina il campo non vale: e' proprio il caso in cui
    due macchine danno esiti diversi (misurato il 2026-09-02: moat MISSING su
    WSL e moat ON su Windows, stesso pacchetto).
    """
    reg = RADICE / "docs" / "stato-reale" / "SMOKE-PRE-TAG.md"
    if not reg.exists():
        e.cancello("smoke pre-tag dichiarato", False,
                   "manca docs/stato-reale/SMOKE-PRE-TAG.md")
        return
    t = reg.read_text(encoding="utf-8")
    blocco = re.search(rf"(?ms)^## {re.escape(pv)}\b(.*?)(?=^## |\Z)", t)
    if not blocco:
        e.cancello("smoke pre-tag dichiarato", False, f"nessun blocco per {pv}")
        return
    b = blocco.group(1).lower()
    for campo in ("windows", "wsl"):
        e.cancello(f"smoke dichiarato su {campo}", campo in b,
                   "presente" if campo in b else "assente")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sha", default=None, help="il commit che si vuole taggare (default: HEAD)")
    a = ap.parse_args()
    sha = a.sha
    if not sha:
        sha, code = sh("git", "rev-parse", "HEAD")
        if code != 0:
            print("  ⛔ non riesco a leggere HEAD"); return 2
    pv = versione_di_record()
    if not pv:
        print("  ⛔ non riesco a leggere la versione da pyproject.toml"); return 2

    print("=" * 74)
    print(f"  CANCELLI DEL TAG — versione {pv} · commit {sha[:8]}")
    print("=" * 74)
    e = Esito()
    c_versioni(e, pv)
    c_changelog(e, pv)
    c_manifesti(e)
    c_ci(e, sha)
    c_smoke(e, pv)

    print()
    if e.non_misurati:
        print(f"  ?  {len(e.non_misurati)} cancelli NON misurati: "
              f"{', '.join(e.non_misurati)}")
        print("     Non sono verdi: sono ignoti, ed e' una cosa diversa.")
    if e.aperti:
        print(f"  NO {len(e.aperti)} cancelli APERTI:")
        for x in e.aperti:
            print(f"       - {x}")
        return 1
    if e.non_misurati:
        return 2
    print("  OK  tutti i cancelli misurabili qui sono chiusi.")
    print("      Restano quelli che questo file NON prova: l'ESECUZIONE dello")
    print("      smoke (qui si legge solo la dichiarazione) e il MERITO del")
    print("      CHANGELOG. Chi tagga li ha visti di persona, o non li ha visti.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
