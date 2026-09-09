"""R1 — le caselle della Definition of Done che una macchina PUO' controllare.

La DoD ha nove caselle. Questo script ne controlla **cinque** e dichiara le
altre quattro **NON MECCANICHE**, dicendo che cosa bisogna leggere per
chiuderle. Non le finge verdi: un gate che dice sempre «passa» e' il modo piu'
efficace di rendere una regola inutile mentre sembra applicata.

    ✅ meccanica       la macchina risponde si'/no con un comando
    👁️ NON MECCANICA   serve un occhio: lo script dice DOVE guardare

Uso:
    PYTHONPATH=. python scripts/dod.py                 # il ramo corrente contro origin/main
    PYTHONPATH=. python scripts/dod.py --base <ref>
    PYTHONPATH=. python scripts/dod.py --json

Esce 1 se una casella MECCANICA e' rossa. Le non meccaniche non fanno mai
fallire: farebbero fallire sempre, e in due giorni qualcuno toglierebbe il gate.

🪞 IL CONTROLLO POSITIVO, e come me l'ero scritto sbagliato. Avevo detto: «lo
provo sul commit che lo precede sul mio ramo (`b489a4d6`), che non tocca
nessun test». Provato: **tutto verde**, perche' quel commit non tocca nemmeno
il PRODOTTO e ogni casella si autoesclude. Un gate che assolve chi lo scrive
non ha mai fatto niente, e il mio primo controllo era proprio di quelli.

Il controllo che MORDE e' su un commit vero di `main` che cambia il prodotto
senza toccare un test — `0ffd5ef7` (cli.py, 19 righe, zero test):

    python scripts/dod.py --base 0ffd5ef7^ --head 0ffd5ef7
    🔴 RED alla porta          1 file di prodotto cambiati e ZERO test toccati
    🔴 riga della mappa        prodotto cambiato e nessuna riga aggiornata
    ✅ PR ≤ 300 righe          19 righe aggiunte in verimem/            EXIT=1

E lo stesso giro ha trovato un falso positivo MIO — vedi `_DATA` qui sotto.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field

#: cio' che conta come «prodotto»: le righe che cambiano il comportamento per
#: l'utente. `tests/`, `docs/` e `scripts/` non contano nel tetto di R6.
_PRODOTTO = re.compile(r"^verimem/.*\.py$")
_TEST = re.compile(r"^tests/.*\.py$")
_MAPPA = re.compile(r"^docs/stato-reale/mappa/.*\.md$")
#: Che cosa vale come ANCORAGGIO di un numero scritto in un commento. La v1
#: accettava solo l'ISO e ha bocciato `# (2b82497f, 07/09). test_nessun_numero…`
#: — che e' ancorato **due volte**, allo SHA e alla data all'italiana. Un
#: righello che boccia chi ha fatto la cosa giusta insegna a ignorarlo.
_DATA = re.compile(
    r"\b20\d{2}-\d{2}-\d{2}\b"          # 2026-09-09
    r"|\b\d{1,2}/\d{1,2}(/\d{2,4})?\b"  # 07/09, 07/09/2026
    r"|\b[0-9a-f]{7,40}\b"              # lo SHA del commit che l'ha misurato
)

TETTO_RIGHE = 300


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


@dataclass
class Casella:
    nome: str
    meccanica: bool
    esito: str | None = None          # "VERDE" | "ROSSO" | None (non meccanica)
    dettaglio: str = ""
    dove_guardare: str = ""
    righe: list[str] = field(default_factory=list)


def analizza(base: str, testa: str = "HEAD") -> list[Casella]:
    numstat = git("diff", "--numstat", f"{base}...{testa}")
    file_toccati, aggiunte_prodotto = [], 0
    for riga in numstat.splitlines():
        pezzi = riga.split("\t")
        if len(pezzi) != 3:
            continue
        piu_, _meno, nome = pezzi
        nome = nome.replace("\\", "/")
        file_toccati.append(nome)
        if _PRODOTTO.match(nome) and piu_.isdigit():
            aggiunte_prodotto += int(piu_)

    prodotto = [f for f in file_toccati if _PRODOTTO.match(f)]
    test = [f for f in file_toccati if _TEST.match(f)]
    mappa = [f for f in file_toccati if _MAPPA.match(f)]
    caselle: list[Casella] = []

    # ── 1. RED alla porta ─────────────────────────────────────────────────
    # Meccanica solo per meta': la macchina vede SE un test e' stato toccato,
    # non se quel test e' davvero rosso prima della cura. Il primo controllo
    # pero' morde gia': una cura senza un solo test toccato non ha un RED.
    c = Casella("RED alla porta (almeno un test toccato)", True)
    if not prodotto:
        c.esito, c.dettaglio = "VERDE", "nessun file di prodotto toccato: non serve"
    elif test:
        c.esito, c.dettaglio = "VERDE", f"{len(test)} file di test toccati"
        c.righe = test[:6]
    else:
        c.esito = "ROSSO"
        c.dettaglio = (f"{len(prodotto)} file di prodotto cambiati e ZERO test toccati")
        c.righe = prodotto[:6]
    caselle.append(c)

    # ── 2. la riga della mappa ────────────────────────────────────────────
    c = Casella("riga della mappa aggiornata", True)
    if not prodotto:
        c.esito, c.dettaglio = "VERDE", "nessun file di prodotto toccato"
    elif mappa:
        c.esito, c.dettaglio = "VERDE", f"{len(mappa)} documenti della mappa toccati"
    else:
        c.esito = "ROSSO"
        c.dettaglio = "prodotto cambiato e nessuna riga della mappa aggiornata"
        c.righe = prodotto[:6]
    caselle.append(c)

    # ── 3. il tetto di R6 ─────────────────────────────────────────────────
    c = Casella(f"PR ≤ {TETTO_RIGHE} righe di prodotto (R6)", True)
    c.esito = "VERDE" if aggiunte_prodotto <= TETTO_RIGHE else "ROSSO"
    c.dettaglio = (f"{aggiunte_prodotto} righe aggiunte in verimem/ "
                   f"(le cancellazioni non contano)")
    caselle.append(c)

    # ── 4. docstring con data ─────────────────────────────────────────────
    # Cerca una data ISO fra le righe AGGIUNTE dei file di prodotto: un numero
    # in un docstring senza data invecchia in silenzio (sei trovati nella mappa).
    c = Casella("i numeri nuovi nei docstring portano una data", True)
    if not prodotto:
        c.esito, c.dettaglio = "VERDE", "nessun file di prodotto toccato"
    else:
        diff = git("diff", f"{base}...{testa}", "--", *prodotto)
        aggiunte = [r[1:] for r in diff.splitlines()
                    if r.startswith("+") and not r.startswith("+++")]
        #: una riga «sospetta» = una riga di commento/docstring con una
        #: percentuale o una frazione dentro
        sospette = [r for r in aggiunte
                    if re.search(r"#|\"\"\"|'''", r) and re.search(r"\d+[.,]?\d*\s*%|\d+\s*/\s*\d+", r)]
        senza_data = [r.strip() for r in sospette if not _DATA.search(r)]
        if not sospette:
            c.esito, c.dettaglio = "VERDE", "nessun numero nuovo nei commenti"
        elif senza_data:
            c.esito = "ROSSO"
            c.dettaglio = f"{len(senza_data)} righe di commento con un numero e senza data"
            c.righe = senza_data[:4]
        else:
            c.esito, c.dettaglio = "VERDE", f"{len(sospette)} numeri nuovi, tutti con data"
    caselle.append(c)

    # ── 5. niente push su main ────────────────────────────────────────────
    c = Casella("il lavoro NON e' su main", True)
    ramo = git("rev-parse", "--abbrev-ref", "HEAD")
    c.esito = "ROSSO" if ramo in ("main", "master") else "VERDE"
    c.dettaglio = f"ramo corrente: {ramo}"
    caselle.append(c)

    # ── le quattro che una macchina non chiude ────────────────────────────
    caselle += [
        Casella("il RED era DAVVERO rosso prima della cura", False,
                dove_guardare="l'output del test PRIMA della cura, nel ticket. "
                              "Un test aggiunto insieme alla cura puo' essere nato verde."),
        Casella("claim del README collegato o tolto", False,
                dove_guardare="la riga del README che il cambiamento tocca "
                              "(`grep -n` sul concetto, non sul nome del modulo)."),
        Casella("revisore ≠ autore", False,
                dove_guardare="la PR: chi ha approvato non e' chi ha scritto."),
        Casella("fatto salvato con --source, e la ricevuta letta", False,
                dove_guardare="`verimem tip`: `admitted` o `quarantined`, "
                              "e il campo `moat` se torna `not run`."),
        Casella("zero copie nuove", False,
                dove_guardare="scripts/copie.py (R3, di @Corrado) quando esiste; "
                              "oggi si legge a mano."),
        Casella("CI verde sul tip", False,
                dove_guardare="`gh run list --branch <ramo>` — e i JOB uno per uno, "
                              "non solo il run."),
    ]
    return caselle


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--head", default="HEAD",
                    help="il ramo/commit da giudicare (per provare il gate su un caso noto)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    caselle = analizza(args.base, args.head)
    rosse = [c for c in caselle if c.esito == "ROSSO"]

    if args.json:
        print(json.dumps([{"casella": c.nome, "meccanica": c.meccanica,
                           "esito": c.esito, "dettaglio": c.dettaglio,
                           "dove_guardare": c.dove_guardare} for c in caselle],
                         indent=2, ensure_ascii=False))
        return 1 if rosse else 0

    ramo = args.head if args.head != "HEAD" else git("rev-parse", "--abbrev-ref", "HEAD")
    print(f"== DoD (R1) — ramo `{ramo}` contro `{args.base}` ==\n")
    for c in caselle:
        if not c.meccanica:
            continue
        segno = "✅" if c.esito == "VERDE" else "🔴"
        print(f"  {segno} {c.nome:44s} {c.dettaglio}")
        for r in c.righe:
            print(f"        · {r[:96]}")
    print("\n  -- che una macchina NON chiude: qui si legge --")
    for c in caselle:
        if c.meccanica:
            continue
        print(f"  👁️  {c.nome:44s} {c.dove_guardare}")

    print(f"\n  caselle meccaniche rosse: {len(rosse)}")
    return 1 if rosse else 0


if __name__ == "__main__":
    sys.exit(main())
