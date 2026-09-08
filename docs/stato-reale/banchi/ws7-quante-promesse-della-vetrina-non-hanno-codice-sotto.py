"""Quante promesse della vetrina nominano qualcosa che il codice non emette piu?

NASCE DA UN CASO SINGOLO, il 07/09: `CHANGELOG.md:32` e `README.md:339`
annunciano la coesistenza fra fonti distinte e la ricevuta `L3-fonti-distinte`;
la cura e' stata revertita il 06/09 alle 15:31 (`05c26887`) e nel codice quella
stringa sopravvive **solo in due commenti**. Il test che i suoi autori avevano
scritto, ripreso dal padre del revert ed eseguito sul tip, non si importa
nemmeno: `ImportError: cannot import name 'due_fonti_dichiarate_e_diverse'`.

LA DOMANDA CHE QUESTO BANCO PONE non e' quel caso, e' la sua CLASSE: **di tutti
gli identificatori che la vetrina nomina in backtick, quanti non esistono in
nessun ramo eseguibile?** Un utente che legge il README e cerca quel campo nella
ricevuta non lo trova, e non ha modo di sapere che il testo e' rimasto indietro.

⚠️ TRE LIMITI, dichiarati perche' il numero non venga letto per piu' di quel che e':

 1. **Presenza, non comportamento.** Trovare la stringa in un file .py non prova
    che il prodotto la emetta sulla porta che l'utente usa: prova solo che il
    codice la nomina. Il verso che conta e' l'altro: se **non** c'e', il prodotto
    non puo' emetterla — ed e' su quel verso che questo banco decide.
 2. **I commenti si escludono per riga**, con `lstrip().startswith('#')`. Una
    stringa dentro una **docstring** conta come presente: il banco e' quindi
    OTTIMISTA, e i casi che segnala sono un **minimo**, non il totale.
 3. **Solo cio' che sta in backtick.** Una promessa scritta in prosa non entra.

🔑 CONTROLLO POSITIVO, e deve poter smentire chi lo scrive: `as_of` DEVE
risultare presente (e' un parametro pubblico delle porte) e `L3-fonti-distinte`
DEVE risultare assente (e' il caso che ha dato origine al banco). Se il primo
cade, il banco sta misurando male e si ferma con EXIT=3 invece di stampare un
verdetto: un banco che non trova cio' che c'e' non e' verde, e' cieco.

⚠️ QUARTO LIMITE, TROVATO ALLA SECONDA ESECUZIONE E SU DI ME: il primo controllo
positivo era `grounding_score`, e il banco lo dava «non presente nella vetrina».
FALSO: il README lo nomina alla riga 13, dentro `grounding_score 99.97` — cioe'
un backtick che porta **il nome E il valore**, che il regex non cattura. Il
difetto era nel mio estrattore, non nel README. Se l'avessi consegnato sarebbe
diventato «la vetrina non nomina il campo che distingue un fatto giudicato»:
un allarme falso, con l'aria del reperto.

📊 ESITO DELLA PRIMA ESECUZIONE VALIDA, 07/09 sul tip 2b82497f, EXIT=1:
**4 candidati su 52, e uno solo e' una promessa senza codice.**
    L3-fonti-distinte   🔴 VERO — CHANGELOG.md:32, cura revertita da 05c26887
    pooled_auroc        fuori perimetro — vive in benchmark/epistemic_harness.py
    u1_mean_3runs       fuori perimetro — benchmark/results/e2e_crossuser_u2.json
    ce_v31              nome INTERNO: sta in docs/ricerca e in sei banchi di ws3
                        e ws4, in nessun file di codice o configurazione. Il
                        CHANGELOG **pubblico** lo usa senza spiegarlo (riga 117,
                        accanto a 97,21 contro 94,92): chi legge non ha modo di
                        sapere quale modello sia. Fastidio, non difetto.
⇒ **Il caso di ieri e' ISOLATO, non sistemico** — per quel che questo metodo puo'
vedere, e i quattro limiti qui sopra dicono quanto e' poco. Un verdetto utile e'
anche quello che non allarga il danno.

Uso:  python docs/stato-reale/banchi/ws7-quante-promesse-della-vetrina-non-hanno-codice-sotto.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[3]

# identificatori: `qualcosa_con_underscore`, `L3-fonti-distinte`, `judged`...
TOKEN = re.compile(r"`([A-Za-z_][A-Za-z0-9_.\-]{2,60})`")

# cio' che non e' un identificatore del prodotto: comandi, path, tipi, parole
RUMORE = {
    "pip", "python", "true", "false", "none", "null", "int", "str", "bool",
    "dict", "list", "float", "json", "yaml", "sqlite", "verimem", "hippo",
    "readme.md", "changelog.md", "pyproject.toml", "server.json", "state.md",
    "docs", "tests", "main", "note", "and", "or", "not", "the", "source",
}

#: ⚠️ EDIZIONE 2 DEL FILTRO, dopo la prima esecuzione: dei 17 candidati che il
#: filtro largo dava, **16 erano rumore** — nomi di file di benchmark
#: (`ann_scale_bench.json`), celle della CI (`ubuntu-latest`, `py3.13`), un tag
#: (`v0.7.0`), un documento (`BENCHMARKS.md`) e una PRAGMA di SQLite
#: (`secure_delete`, che il README cita proprio per dire che **noi non la
#: mettiamo** e la deve mettere l'utente). Verificati **a mano, uno per uno**:
#: senza quella lettura avrei consegnato 17 allarmi di cui 1 vero.
_ESTENSIONI = (".json", ".md", ".py", ".toml", ".txt", ".yml", ".yaml", ".cfg")
_CELLE_CI = ("ubuntu-latest", "macos-latest", "windows-latest")
_TERZI = ("secure_delete",)  # identificatori di librerie altrui, non nostri


def _e_nostro(t: str) -> bool:
    """Un identificatore che il PRODOTTO puo' emettere — non un file, non una
    cella di CI, non un tag, non il nome di una PRAGMA di SQLite."""
    b = t.lower()
    if b.endswith(_ESTENSIONI) or b in _CELLE_CI or b in _TERZI:
        return False
    if re.fullmatch(r"v?\d+\.\d+(\.\d+)?", b) or re.fullmatch(r"py\d\.\d+", b):
        return False
    return True


def _sezione_0_7_7(testo: str) -> str:
    """Solo la voce della release in lavorazione, non tutto lo storico."""
    inizio = testo.find("## [0.7.7]")
    if inizio < 0:
        return ""
    fine = testo.find("## [0.7.6]", inizio)
    return testo[inizio: fine if fine > 0 else len(testo)]


def _token_della_vetrina() -> dict[str, list[str]]:
    fonti = {
        "README.md": (RADICE / "README.md").read_text(encoding="utf-8"),
        "CHANGELOG.md [0.7.7]": _sezione_0_7_7(
            (RADICE / "CHANGELOG.md").read_text(encoding="utf-8")
        ),
    }
    out: dict[str, list[str]] = {}
    for dove, testo in fonti.items():
        for t in TOKEN.findall(testo):
            if t.lower() in RUMORE or t.lower().startswith("verimem"):
                continue
            # un identificatore, non una parola inglese qualsiasi
            if not ("_" in t or "-" in t or "." in t):
                continue
            if not _e_nostro(t):
                continue
            out.setdefault(t, [])
            if dove not in out[t]:
                out[t].append(dove)
    return out


def _righe_eseguibili() -> list[tuple[Path, int, str]]:
    righe: list[tuple[Path, int, str]] = []
    for p in (RADICE / "verimem").rglob("*.py"):
        try:
            for n, r in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if r.lstrip().startswith("#"):
                    continue
                righe.append((p, n, r))
        except Exception as exc:  # pragma: no cover
            print(f"  ! non letto {p}: {exc}")
    return righe


def main() -> int:
    promesse = _token_della_vetrina()
    righe = _righe_eseguibili()
    print(f"Vetrina: {len(promesse)} identificatori in backtick fra README e "
          f"CHANGELOG [0.7.7]")
    print(f"Codice:  {len(righe)} righe eseguibili in verimem/ "
          f"(escluse le righe di commento)\n")

    presenti: dict[str, str] = {}
    assenti: list[str] = []
    for t in sorted(promesse):
        dove = next((f"{p.relative_to(RADICE)}:{n}" for p, n, r in righe if t in r), None)
        if dove:
            presenti[t] = dove
        else:
            assenti.append(t)

    # --- il controllo che puo' smentirmi, PRIMA del verdetto ---
    vivo = "as_of"
    if vivo not in promesse:
        print(f"⛔ CONTROLLO POSITIVO NON APPLICABILE: `{vivo}` non compare in")
        print("   backtick nella vetrina, quindi il ramo che doveva smentirmi non")
        print("   e' stato nemmeno percorso. ⚠️ ALLA PRIMA ESECUZIONE, IL 07/09,")
        print("   QUESTO BANCO HA STAMPATO UN SEGNO DI SPUNTA VERDE PROPRIO QUI:")
        print("   il controllo passava perche' non veniva eseguito. Nessun verdetto.")
        return 3
    if vivo not in presenti:
        print(f"⛔ CONTROLLO POSITIVO FALLITO: `{vivo}` risulta assente dal codice.")
        print("   Il banco non trova cio' che c'e': e' cieco, non verde. Nessun verdetto.")
        return 3
    print(f"✅ controllo positivo: `{vivo}` trovato in {presenti.get(vivo, '—')}")
    caso = "L3-fonti-distinte"
    if caso in promesse:
        esito = "ASSENTE (atteso)" if caso in assenti else "PRESENTE — il banco NON riproduce il caso"
        print(f"🔬 caso che ha dato origine al banco: `{caso}` -> {esito}")
    print()

    print(f"🔴 SENZA CODICE SOTTO: {len(assenti)} su {len(promesse)}")
    for t in assenti:
        print(f"   `{t}`   — nominato in: {', '.join(promesse[t])}")
    return 0 if not assenti else 1


if __name__ == "__main__":
    sys.exit(main())
