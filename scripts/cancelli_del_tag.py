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


def espandi_sha(sha: str) -> str | None:
    """Lo sha ABBREVIATO va espanso PRIMA di interrogare l'API, o si legge un
    verde inesistente al contrario.

    `head_sha=` dell'API di GitHub vuole i 40 caratteri: con uno sha corto NON
    da' errore, restituisce una LISTA VUOTA. Misurato il 2026-09-04 su questo
    stesso repository e sullo stesso commit:

        gh run list --commit 04911425                    -> 0
        gh run list --commit 049114259e5123516d76ee...   -> 3

    Il cancello della CI concludeva percio' «NESSUN run» su un commit che ne
    aveva tre, uno dei quali verde 9/9. Qui l'errore cadeva dal lato prudente —
    un cancello aperto per sbaglio si nota — ma resta un misuratore che mente:
    chi copia lo sha da `git log --oneline` lo copia SEMPRE corto.
    """
    out, code = sh("git", "rev-parse", "--verify", f"{sha}^{{commit}}")
    return out if code == 0 and len(out) == 40 else None


def leggi(rel: str, sha: str) -> str | None:
    """Legge un file DAL COMMIT, non dall'albero di lavoro.

    Prima queste letture erano `(RADICE / rel).read_text()`, e `--sha` governava
    soltanto l'interrogazione alla CI: il comando diceva «i cancelli sono
    chiusi» misurando i file che avevo sotto mano, non quelli del commit che si
    stava per taggare. Provato il 2026-09-04, stesso `--sha`, due alberi:

        albero integro   -> OK  CHANGELOG ha la voce [0.7.6]   171 righe
        voce rimossa     -> NO  CHANGELOG ha la voce [0.7.6]   assente

    Due verdetti diversi per lo STESSO commit: la firma di un misuratore che
    misura un'altra cosa. E il caso pericoloso non e' teorico — il registro
    dello smoke nasce DOPO il commit che si tagga, quindi girando i cancelli dal
    ramo che lo contiene il cancello «smoke» si sarebbe chiuso su una prova
    assente dal tag.
    """
    out, code = sh("git", "show", f"{sha}:{rel}")
    return out if code == 0 else None


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


def versione_di_record(sha: str) -> str | None:
    t = leggi("pyproject.toml", sha)
    if t is None:
        return None
    m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', t)
    return m.group(1) if m else None


def c_versioni(e: Esito, pv: str, sha: str) -> None:
    """Le superfici che dichiarano la versione devono dire la STESSA cosa.

    `server.json` e' la quinta e la piu' recente: il 2026-09-02 diceva 0.7.2
    mentre le altre quattro dicevano 0.7.6, e il presidio non la guardava.
    """
    superfici: list[tuple[str, str | None]] = [("pyproject.toml", pv)]
    t = leggi("verimem/__init__.py", sha) or ""
    m = re.search(r'__version__\s*=\s*"([^"]+)"', t)
    superfici.append(("verimem/__init__.py", m.group(1) if m else None))
    t = leggi(".claude-plugin/plugin.json", sha)
    superfici.append((".claude-plugin/plugin.json",
                      json.loads(t).get("version") if t else None))
    # Una superficie ASSENTE non deve sparire in silenzio.
    # Provato il 2026-09-04 sul commit 039e0455, che precede l'introduzione di
    # server.json: il cancello stampava «OK le superfici di versione concordano»
    # e non una parola sulle due superfici mancanti. Un'assenza si legge come un
    # verde — la stessa forma per cui server.json, appena nato, resto' fuori dal
    # presidio e il 2026-09-02 dichiarava 0.7.2 mentre le altre dicevano 0.7.6.
    # Qui l'assenza APRE il cancello: si tagga il presente, e nel presente
    # queste cinque superfici esistono tutte.
    for atteso in ("verimem/__init__.py", ".claude-plugin/plugin.json",
                   "server.json", "STATE.md"):
        if leggi(atteso, sha) is None:
            e.cancello(f"superficie {atteso}", False,
                       f"assente dal commit {sha[:8]}: non e' concorde, e' sparita")
    t = leggi("server.json", sha)
    if t is not None:
        sj = json.loads(t)
        superfici.append(("server.json", sj.get("version")))
        for i, pkg in enumerate(sj.get("packages", [])):
            if "version" in pkg:
                superfici.append((f"server.json packages[{i}]", pkg["version"]))
    t = leggi("STATE.md", sha)
    if t is not None:
        m = re.search(r"(?m)^\|\s*Release\s*\|\s*v?([0-9][0-9.]*)", t)
        superfici.append(("STATE.md riga Release", m.group(1) if m else None))

    diverse = {v for _, v in superfici if v is not None} - {pv}
    for nome, v in superfici:
        if v is None:
            e.cancello(f"versione in {nome}", None, "non letta")
    # Il CONTEGGIO va stampato: e' l'unico modo perche' una superficie nuova e
    # non presidiata si veda. Se domani il numero scende, qualcosa e' sparito.
    e.cancello("le superfici di versione concordano", not diverse,
               f"pyproject={pv}, {len(superfici)} superfici confrontate"
               + (f" ma {', '.join(sorted(diverse))} altrove" if diverse else ""))


def c_changelog(e: Esito, pv: str, sha: str) -> None:
    testo = leggi("CHANGELOG.md", sha)
    if testo is None:
        e.cancello(f"CHANGELOG ha la voce [{pv}]", None, "CHANGELOG.md non e' in questo commit")
        return
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
                   "--jq", '[.workflow_runs[] | {n:.run_number, s:.status, c:.conclusion, i:.id}]')
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
        # I job si contano sul run VINCENTE, non su `.workflow_runs[0]`.
        # Prima era `[0]`, cioe' il piu' RECENTE: finche' c'e' un run solo i due
        # coincidono — sul candidato 04911425 ce n'e' uno e il 9/9 era giusto —
        # ma basta un re-run, o un run ancora in corso sullo stesso commit,
        # perche' il numero stampato («#3097») e il numero contato vengano da
        # due run DIVERSI, presentati come una misura sola.
        # ⚠️ Questo difetto NON e' stato osservato: sui run di questo repository
        # non esiste oggi un commit con un verde e un piu' recente non verde.
        # E' una cura preventiva, e va letta per quello che e'.
        idv = vinc[0]["i"]
        out3, code3 = sh("gh", "api", f"repos/:owner/:repo/actions/runs/{idv}/jobs",
                         "--jq", '[.jobs[].conclusion] | {tot:length, ok:(map(select(.=="success"))|length)}')
        if code3 == 0:
            d = json.loads(out3)
            e.cancello("tutti i job del run sono success",
                       d["tot"] == d["ok"] and d["tot"] > 0,
                       f"{d['ok']}/{d['tot']} del run #{vinc[0]['n']} (id {idv})")


def c_manifesti(e: Esito) -> None:
    banco = RADICE / "scripts" / "controlla_manifesti_distribuzione.py"
    if not banco.exists():
        e.cancello("manifesti di distribuzione", None, "banco assente")
        return
    _, code = sh(sys.executable, str(banco))
    e.cancello("manifesti + prova di proprieta' PyPI", code == 0, f"EXIT={code}")


def c_smoke(e: Esito, pv: str, sha: str) -> None:
    """Non lo esegue: controlla che sia stato DICHIARATO, con esito e autore.

    Il piano lo vuole su DUE campi (WSL e Windows) e PRIMA del tag. Una
    dichiarazione che non nomina il campo non vale: e' proprio il caso in cui
    due macchine danno esiti diversi (misurato il 2026-09-02: moat MISSING su
    WSL e moat ON su Windows, stesso pacchetto).
    """
    # ⚠️ QUESTO cancello, e solo questo, legge dall'ALBERO DI LAVORO e non dal
    # commit. Non e' una svista: lo smoke si esegue SUL WHEEL prodotto dal
    # commit, quindi il registro nasce per forza DOPO — nessun commit puo'
    # contenere la prova fatta su se stesso. Il tag conterra' il codice provato;
    # la prova sta nel commit successivo.
    # Il rischio che questo apre — un registro verde che parla di un ALTRO
    # pacchetto — non si chiude leggendo altrove: si chiude PRETENDENDO che il
    # registro nomini il commit di cui stiamo parlando. E' il cancello qui sotto.
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
    # I campi si cercano SOLO nel sotto-blocco che nomina questo commit, non in
    # tutta la voce della versione. Il registro contiene anche i candidati
    # superati — 0.7.6 ne ha gia' due — e ognuno porta la sua riga «windows …
    # EXIT=0»: cercando nell'intera voce, il cancello di windows si chiuderebbe
    # con la prova di un ALTRO pacchetto. Il buco l'ha aperto chi scrive (io,
    # aggiungendo il blocco storico) e non chi legge: e' il caso in cui il
    # registro migliora e il misuratore peggiora.
    # Lo sha si cerca nell'INTESTAZIONE del sotto-blocco, non nel suo corpo.
    # Cercarlo ovunque non regge: il blocco del candidato superato SPIEGA che il
    # commit da taggare e' un altro e cosi' lo nomina, e con la ricerca larga
    # risultava pertinente. Provato il 2026-09-04 togliendo la riga `windows`
    # del candidato: il cancello si chiudeva lo stesso, citando
    # «- **windows** — 2026-09-03 22:14» — la prova di un ALTRO pacchetto.
    # E' la forma gia' vista il 2026-09-03: un id cercato come sottostringa
    # dentro un testo che parla anche di altri id.
    sezioni = re.split(r"(?m)^(?=### )", blocco.group(1))
    # `or [""]`: re.split puo' restituire una prima sezione vuota quando il
    # blocco comincia direttamente con «### », e splitlines() di "" e' [].
    pertinenti = [s for s in sezioni if sha[:8] in (s.splitlines() or [""])[0]]
    e.cancello("il registro parla di QUESTO commit", bool(pertinenti),
               f"cita {sha[:8]}" if pertinenti
               else f"il blocco {pv} non nomina {sha[:8]}: parla di un altro pacchetto")
    if not pertinenti:
        return
    b = "\n".join(pertinenti)
    # ⚠️ NON basta che il campo sia NOMINATO. La prima versione di questo
    # cancello cercava la parola «windows» nel blocco, e un registro scritto in
    # anticipo — con i due campi elencati e nessun esito — l'avrebbe chiuso A
    # VUOTO. Trovato scrivendo il registro, cioe' PRIMA di usarlo: e' lo stesso
    # difetto che il gate del rilascio aveva il 02/09, un cancello soddisfatto
    # da una dichiarazione invece che da un fatto.
    # Per ogni campo servono TRE cose sulla stessa riga o subito sotto: il nome
    # del campo, un ESITO leggibile a macchina, e una DATA.
    ESITO = re.compile(r"EXIT=\d+|\bPASSATO\b|\bFALLITO\b|\bPASS\b|\bFAIL\b", re.I)
    DATA = re.compile(r"20\d\d-\d\d-\d\d")
    for campo in ("windows", "wsl"):
        righe = [ln for ln in b.splitlines() if campo.lower() in ln.lower()]
        if not righe:
            e.cancello(f"smoke su {campo}", False, "campo non nominato")
            continue
        con_esito = [ln for ln in righe if ESITO.search(ln)]
        con_data = [ln for ln in righe if DATA.search(ln)]
        e.cancello(f"smoke su {campo}: esito dichiarato", bool(con_esito),
                   con_esito[0].strip()[:44] if con_esito
                   else "nominato ma SENZA esito — una dichiarazione non e' una prova")
        e.cancello(f"smoke su {campo}: data dichiarata", bool(con_data),
                   "presente" if con_data else "senza data: non si sa su quale wheel")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sha", default=None, help="il commit che si vuole taggare (default: HEAD)")
    a = ap.parse_args()
    sha = a.sha or "HEAD"
    completo = espandi_sha(sha)
    if completo is None:
        print(f"  ⛔ non riesco a risolvere {sha} in un commit di questo repository")
        return 2
    sha = completo
    pv = versione_di_record(sha)
    if not pv:
        print(f"  ⛔ non riesco a leggere la versione da pyproject.toml in {sha[:8]}")
        return 2

    albero, _ = sh("git", "rev-parse", "HEAD")
    sporco = len(sh("git", "status", "--porcelain")[0].splitlines())
    print("=" * 74)
    print(f"  CANCELLI DEL TAG — versione {pv} · commit {sha}")
    print("=" * 74)
    # Da dove viene ogni numero: le superfici e il CHANGELOG dal COMMIT, il
    # registro dello smoke e i manifesti dall'ALBERO. Stampato perche' il
    # 2026-09-04 ho letto un verdetto credendo che riguardasse il commit mentre
    # riguardava i file che avevo sotto mano.
    print(f"  superfici e CHANGELOG: letti dal commit {sha[:8]}")
    print(f"  registro smoke e manifesti: letti dall'albero {albero[:8]}"
          + (f", con {sporco} file NON committati" if sporco else ", pulito"))
    print("-" * 74)
    e = Esito()
    c_versioni(e, pv, sha)
    c_changelog(e, pv, sha)
    c_manifesti(e)
    c_ci(e, sha)
    c_smoke(e, pv, sha)

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
