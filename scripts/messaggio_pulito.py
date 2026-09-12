#!/usr/bin/env python3
r"""Il messaggio di un commit parla del prodotto, non della stanza in cui lavoriamo.

    python scripts/messaggio_pulito.py --file <path>   # un messaggio (hook commit-msg)
    python scripts/messaggio_pulito.py --range A..B    # i commit di una PR (CI)
    python scripts/messaggio_pulito.py --autotest      # prova che il controllo morde

QUATTRO REGOLE, e ognuna nasce da una cosa che il repository pubblico mostrava:

  1. AL MASSIMO 10 RIGHE non vuote. Un messaggio lungo racconta un'indagine; il
     posto dell'indagine sono i documenti sotto `docs/`, che restano leggibili
     anche quando il commit e' stato squashato via.
  2. NIENTE PERCORSI LOCALI (`C:\Users\...`, `/c/Users/...`, `D:\a\...`): dicono
     com'e' fatta la macchina di chi ha scritto, e a chi legge non servono.
  3. NIENTE NOMI UTENTE.
  4. NIENTE NOMI DI SESSIONE ne' ruoli interni: chi legge da fuori non sa chi
     siano, e il lavoro e' del progetto, non di una sigla.

MISURATO PRIMA DI SCRIVERLO, con QUESTO script, sugli ultimi 40 commit del ramo
principale (`--range d60cc326~40..d60cc326`, il 12/09/2026):

    oltre 10 righe    : 39
    nome di sessione  : 24
    nome utente       :  5
    percorso locale   :  2
    PULITI            :  0     <- zero su quaranta

I 24 sono nomi nel CORPO, non nel trailer di attribuzione, che e' escluso: 37
dei 40 portano un `Agent: <Nome>`, e restano leggibili da fuori come sigle senza
significato. Se la convenzione va cambiata e' una decisione del progetto, non di
questo script; qui la dichiaro perche' un controllo che non copre una cosa deve
dire QUALE.

=> Il controllo vale sui commit NUOVI. La storia resta com'e': riscriverla
costerebbe piu' di quanto valga, e un `git log` vecchio non e' una promessa
all'utente. L'hook ferma il prossimo; la CI ferma quelli di una PR.

COME SI CORREGGE un messaggio bocciato: il contenuto non si butta, si sposta.
Le righe in piu' vanno in `docs/stato-reale/` o nel corpo della PR; il commit
tiene la riga che dice *cosa cambia* e, se serve, due righe di come e' provato.

----------------------------------------------------------------------------
I TRAILER NON CONTANO, E IL PERCHE' E' LA PARTE CHE SI SBAGLIA.

Un trailer (`Agent:`, `Co-Authored-By:`, `Signed-off-by:`) e' un campo del
registro, non racconto: `Agent: <Nome>` e' la cura di un incidente vero, i
dieci commit non attribuibili del 13/08, ed e' scritto in `.githooks/prepare-commit-msg`.
Toglierlo riaprirebbe quell'incidente, quindi il conteggio delle righe e le tre
regole sul testo lo saltano.

⚠️ LA PRIMA VERSIONE DI QUESTO SCRIPT SALTAVA **OGNI** RIGA CHE SOMIGLIASSE A
UN TRAILER, in qualunque punto del messaggio. Il risultato, provato il
12/09/2026 prima di spedirlo:

    "Fix the parser\n\nNota: trovato da <sessione> in C:\Users\<utente>\x"
      -> PULITO

Un percorso locale e un nome di sessione, **tutt'e due invisibili**, e la via
d'uscita era scrivere una parola e due punti. Il mio autotest era 12 su 12
verde e non lo vedeva: dodici casi scelti da me, tutti diretti al bersaglio che
avevo in mente.

🔑 Ora si toglie **solo il blocco finale**, e solo se ogni sua riga e' un
trailer — che e' come lo intende git. Una riga in mezzo al corpo viene letta,
qualunque forma abbia.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

RIGHE_MASSIME = 10

PERCORSO = re.compile(r"([A-Za-z]:[\\/]Users[\\/]|/c/Users/|[A-Za-z]:[\\/]a[\\/]|/home/[a-z]+/)")
UTENTE = re.compile(r"\baurel(io)?(cpr)?(-ctrl)?\b", re.IGNORECASE)
SESSIONE = re.compile(
    r"\b(ws[1-8]|lead-audit|Corrado|Marie|Tara|Iris|Aldo|Giano|Galileo|Nadia)\b",
    re.IGNORECASE,
)
# ⚠️ UNA LISTA CHIUSA, non una forma. Vedi il docstring del modulo: con la
# regola sintattica (`^Parola:\s`) bastava scrivere `Nota:` per far sparire una
# riga dal controllo. Un'esenzione aperta a qualunque parola non e' un'esenzione,
# e' una via d'uscita. Qui ogni nome ammesso ha una ragione:
#   Agent           - l'attribuzione, cura dei 10 commit non attribuibili del 13/08
#   Co-Authored-By  - la riga che il progetto chiede in coda
#   gli altri       - trailer standard di git, che le piattaforme leggono
TRAILER_AMMESSI = ("Agent", "Co-Authored-By", "Signed-off-by", "Reviewed-by",
                   "Acked-by", "Tested-by", "Cc", "Fixes", "Closes", "Refs")
TRAILER = re.compile(r"^(?:" + "|".join(TRAILER_AMMESSI) + r"):\s", re.IGNORECASE)

# `git commit --verbose` incolla il diff in coda al messaggio, dopo questa riga.
# git lo taglia da se'; l'hook riceve il file PRIMA che lo faccia.
FORBICI = re.compile(r"^[#;!$%^&|:]?\s*-+\s*>8\s*-+\s*$", re.MULTILINE)


CANDIDATO_PERCORSO = re.compile(r"[A-Za-z0-9_.\-/]*/[A-Za-z0-9_.\-]*")


def _percorsi_del_repo(radice: str | None = None) -> frozenset[str]:
    """Ogni percorso tracciato, nell'indice E in HEAD.

    Serve anche HEAD perche' una RINOMINA si descrive citando il nome VECCHIO,
    che nell'indice non c'e' piu' ma in HEAD si'.

    Se git non risponde (non e' un repository, non e' installato) torna un
    insieme vuoto: il controllo diventa piu' SEVERO, non muto. Un misuratore
    che cade deve sbagliare contro chi lo usa, non a suo favore.
    """
    percorsi: set[str] = set()
    for comando in (["git", "ls-files"], ["git", "ls-tree", "-r", "--name-only", "HEAD"]):
        try:
            fatto = subprocess.run(comando, cwd=radice, capture_output=True,
                                   text=True, encoding="utf-8", errors="replace")
        except OSError:
            continue
        if fatto.returncode == 0:
            percorsi.update(r.strip() for r in fatto.stdout.splitlines() if r.strip())
    return frozenset(percorsi)


def _senza_percorsi_veri(testo: str, percorsi: frozenset[str]) -> str:
    """Il testo senza i percorsi CHE ESISTONO nel repository.

    ⚠️ 12/09, il difetto che questa funzione cura: 95 file su 775 in
    `docs/stato-reale/` portano un nome di sessione SOLO nel nome del file, e la
    squadra li sta rinominando. Un `git mv` si descrive citando i due percorsi,
    e i due percorsi contengono il nome —

        "docs/stato-reale/banchi/<nome>-porte-e-etichetta.py becomes ..."
          -> BOCCIATO: nome di sessione

    cioe' il cancello bocciava esattamente il lavoro che cura il difetto. Un
    nome dentro il nome di un file non e' un nome nel discorso: e' una
    citazione, e toglierla renderebbe il messaggio falso.

    🔑 IL CRITERIO E' L'ESISTENZA, non la forma. `<nome>/appunti` ha la forma di
    un percorso e non e' tracciato da nessuna parte: resta prosa, e resta
    bocciato. Cosi' l'esenzione non si ottiene scrivendo una barra.
    """
    if not percorsi:
        return testo

    def togli(trovato: re.Match[str]) -> str:
        pezzo = trovato.group(0).strip(".,;:()[]`\"'<>")
        if not pezzo or "/" not in pezzo:
            return trovato.group(0)
        if pezzo in percorsi:
            return " "
        # Una CARTELLA: non e' tracciata di per se', ma lo e' cio' che contiene.
        prefisso = pezzo.rstrip("/") + "/"
        if any(p.startswith(prefisso) for p in percorsi):
            return " "
        return trovato.group(0)

    return CANDIDATO_PERCORSO.sub(togli, testo)


def _senza_trailer(testo: str) -> str:
    """Il messaggio senza il blocco di trailer finale, come lo intende git.

    NON basta scartare ogni riga che somigli a un trailer: `Nota: ...` somiglia,
    sta nel corpo, e scartandola il controllo lo evade chiunque scriva una
    parola e due punti (provato, vedi il docstring del modulo).
    """
    blocchi = testo.replace("\r\n", "\n").rstrip().split("\n\n")
    if len(blocchi) < 2:
        return testo
    ultime = [r for r in blocchi[-1].splitlines() if r.strip()]
    if ultime and all(TRAILER.match(r) for r in ultime):
        return "\n\n".join(blocchi[:-1])
    return testo


def _come_lo_salva_git(testo: str) -> str:
    """Il messaggio come git lo scrivera' davvero: senza commenti ne' diff.

    L'hook `commit-msg` riceve `.git/COMMIT_EDITMSG` prima della pulizia, quindi
    con dentro le righe `# ...` che git mette e poi toglie. Contarle direbbe «22
    righe» a chi ne ha scritte due. La pulizia la fa `git stripspace`, che e'
    l'implementazione di git e non una mia imitazione: `core.commentChar` puo'
    non essere `#`, e indovinarlo sarebbe l'ennesimo righello che sbaglia.
    """
    testo = FORBICI.split(testo, maxsplit=1)[0]
    try:
        fatto = subprocess.run(
            ["git", "stripspace", "--strip-comments"],
            input=testo, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
    except OSError:
        return testo
    return fatto.stdout if fatto.returncode == 0 else testo


def controlla(testo: str, percorsi: frozenset[str] | None = None) -> list[str]:
    """Le violazioni di un messaggio, in chiaro. Lista vuota = pulito.

    `percorsi` sono i file tracciati, per riconoscere le CITAZIONI di percorso;
    se non lo si passa li chiede a git. L'autotest ne passa uno finto apposta:
    un banco che dipendesse dai file veri del repository misurerebbe la pulizia
    di oggi invece del criterio, e diventerebbe rosso al primo `git mv`.
    """
    if percorsi is None:
        percorsi = _percorsi_del_repo()
    corpo = _senza_trailer(testo.replace("\r\n", "\n"))
    righe_intere = [r for r in corpo.splitlines() if r.strip()]
    corpo = _senza_percorsi_veri(corpo, percorsi)
    problemi = []
    # ⚠️ Le righe si contano PRIMA della mascheratura: una riga fatta di solo
    # percorso diventerebbe vuota, e un messaggio di dodici righe ne
    # dichiarerebbe dieci. La mascheratura serve ai NOMI, non alla lunghezza.
    if len(righe_intere) > RIGHE_MASSIME:
        problemi.append(f"{len(righe_intere)} righe non vuote (il massimo e' {RIGHE_MASSIME})")
    for etichetta, regola in (("percorso locale", PERCORSO),
                              ("nome utente", UTENTE),
                              ("nome di sessione o ruolo interno", SESSIONE)):
        trovati = sorted({m.group(0) for m in regola.finditer(corpo)})
        if trovati:
            problemi.append(f"{etichetta}: {', '.join(trovati[:4])}")
    return problemi


def _messaggi_del_range(intervallo: str) -> list[tuple[str, str]]:
    out = subprocess.run(
        ["git", "log", "--format=%H%x00%B%x1e", intervallo],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if out.returncode != 0:
        raise SystemExit(f"git log {intervallo} non ha funzionato: {out.stderr.strip()[:120]}")
    coppie = []
    for blocco in out.stdout.split("\x1e"):
        if not blocco.strip():
            continue
        sha, _, corpo = blocco.strip().partition("\x00")
        coppie.append((sha[:8], corpo))
    if not coppie:
        # Un intervallo vuoto non e' una PR pulita: e' una misura che non c'e'.
        raise SystemExit(f"{intervallo} non contiene nessun commit: non ho misurato niente.")
    return coppie


def stampa(coppie: list[tuple[str, str]]) -> int:
    sporchi = 0
    for sha, testo in coppie:
        problemi = controlla(testo)
        prima = testo.strip().splitlines()[0][:52] if testo.strip() else "(vuoto)"
        if problemi:
            sporchi += 1
            print(f"  BOCCIATO {sha}  {prima}")
            for p in problemi:
                print(f"           - {p}")
        else:
            print(f"  ok       {sha}  {prima}")
    print()
    if sporchi:
        print(f"VERDETTO: ROSSO - {sporchi} messaggi su {len(coppie)} parlano della "
              "nostra stanza invece che del prodotto.")
        print("  Il contenuto non si butta, si sposta: le righe in piu' vanno in "
              "docs/stato-reale/ o nel corpo della PR.")
        return 1
    print(f"VERDETTO: VERDE - {len(coppie)} messaggi, nessuno da correggere.")
    return 0


# (nome, messaggio, ci aspettiamo che sia pulito)
CASI: list[tuple[str, str, bool]] = [
    ("una riga pulita", "Cap the scan at one place", True),
    ("dieci righe esatte", "Titolo\n" + "\n".join(f"riga {i}" for i in range(9)), True),
    ("undici righe", "Titolo\n" + "\n".join(f"riga {i}" for i in range(10)), False),
    ("percorso windows", "Fix\n\nvisto in C:\\Users\\tizio\\repo", False),
    ("percorso msys", "Fix\n\nvisto in /c/Users/tizio/repo", False),
    ("percorso del runner", "Fix\n\nD:\\a\\progetto\\progetto", False),
    ("nome utente", "Fix\n\nsegnalato da aureliocpr", False),
    ("sigla di sessione", "Fix\n\nrilievo di ws5", False),
    ("nome di sessione", "Fix\n\ntrovato da Marie", False),
    ("ruolo interno", "Fix\n\nchiesto da lead-audit", False),
    ("il trailer non conta", "Fix\n\nDue righe di spiegazione.\n"
                             "Co-Authored-By: Qualcuno <a@b.c>", True),
    ("il trailer di attribuzione non conta", "Fix the parser\n\nAgent: Corrado", True),
    ("parola che CONTIENE un nome", "Fix the marieterapia parser", True),
    # I quattro casi qui sotto NON li avevo previsti: li ha trovati la prova di
    # evasione del 12/09, contro la prima versione che era 12 su 12 verde.
    ("riga del corpo travestita da trailer",
     "Fix the parser\n\nNota: trovato da Marie in C:\\Users\\tizio\\x", False),
    ("due righe travestite da trailer",
     "Fix\n\nReported: ws5 says the port is wrong\nAltro: /c/Users/tizio/repo", False),
    ("trailer veri DOPO un corpo sporco",
     "Fix\n\nvisto da Tara\n\nAgent: Iris\nCo-Authored-By: Q <a@b.c>", False),
    ("un blocco finale misto NON e' un blocco di trailer",
     "Fix\n\nAgent: Iris\nma questa riga nomina ws5", False),
]

# Percorsi FINTI per i casi di citazione: se il banco leggesse i file veri
# misurerebbe la pulizia di oggi invece del criterio, e diventerebbe rosso al
# primo `git mv` — cioe' proprio quando la cura funziona.
PERCORSI_FINTI = frozenset({
    "docs/stato-reale/banchi/ws7-porte-e-etichetta.py",
    "docs/stato-reale/banchi-ws2/porte.py",
    "docs/stato-reale/ws8-corrado-notte-05-06-09.md",
})

CASI_CON_PERCORSI: list[tuple[str, str, bool]] = [
    ("una rinomina, citando il nome vecchio",
     "Rename the bench so its name carries a role\n\n"
     "docs/stato-reale/banchi/ws7-porte-e-etichetta.py becomes "
     "docs/stato-reale/banchi/porte-e-etichetta.py.", True),
    ("la citazione di un documento che esiste",
     "Link the postmortem from the README\n\n"
     "Adds a pointer to docs/stato-reale/ws8-corrado-notte-05-06-09.md.", True),
    ("una cartella tracciata",
     "Move the benches out of a per-session folder\n\n"
     "docs/stato-reale/banchi-ws2/ becomes docs/stato-reale/banchi/porte/.", True),
    # 🔑 I due che rendono l'esenzione un criterio e non una via d'uscita.
    ("una barra NON basta: il percorso non esiste",
     "Fix the parser\n\nvedi ws5/appunti per il dettaglio", False),
    ("un percorso inventato dentro una cartella vera",
     "Fix\n\nvedi docs/stato-reale/ws5-ha-sbagliato.md", False),
]


def autotest() -> int:
    """Il controllo positivo: deve bocciare cio' che deve e TACERE sul resto."""
    esiti = []
    coppie = ([(n, t, a, frozenset()) for n, t, a in CASI]
              + [(n, t, a, PERCORSI_FINTI) for n, t, a in CASI_CON_PERCORSI])
    for nome, testo, atteso_pulito, percorsi in coppie:
        problemi = controlla(testo, percorsi=percorsi)
        ok = (not problemi) == atteso_pulito
        esiti.append(ok)
        stato = "pulito" if not problemi else f"bocciato ({problemi[0][:44]})"
        print(f"  [{'OK ' if ok else 'ROSSO'}] {nome:38s} -> {stato}")

    # Il commento di git non e' una riga del messaggio: contarlo bocerebbe un
    # commit di due righe scritto nell'editor.
    con_commenti = ("Titolo vero\n\nCorpo vero.\n"
                    + "# Please enter the commit message for your changes.\n"
                      "# On branch principale\n" * 9)
    pulito = _come_lo_salva_git(con_commenti)
    ok_commenti = not controlla(pulito) and "# On branch" not in pulito
    esiti.append(ok_commenti)
    print(f"  [{'OK ' if ok_commenti else 'ROSSO'}] {'i commenti di git non contano':38s} -> "
          f"{len([r for r in pulito.splitlines() if r.strip()])} righe dopo la pulizia")

    print()
    if all(esiti):
        print(f"AUTOTEST VERDE: {len(esiti)} casi su {len(esiti)} - il controllo boccia "
              "cio' che deve e tace sul resto.")
        return 0
    print(f"AUTOTEST ROSSO: {esiti.count(False)} casi sbagliati su {len(esiti)}.")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--file", help="un messaggio da file (hook commit-msg)")
    parser.add_argument("--range", dest="intervallo", help="i commit di un intervallo git")
    parser.add_argument("--autotest", action="store_true")
    a = parser.parse_args(argv)
    if a.autotest:
        return autotest()
    if a.file:
        grezzo = pathlib.Path(a.file).read_text(encoding="utf-8", errors="replace")
        return stampa([("(in scrittura)", _come_lo_salva_git(grezzo))])
    if a.intervallo:
        return stampa(_messaggi_del_range(a.intervallo))
    parser.error("serve --file, --range o --autotest")
    return 2


if __name__ == "__main__":
    sys.exit(main())
