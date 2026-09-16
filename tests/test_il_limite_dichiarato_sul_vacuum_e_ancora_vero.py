"""README:723-733 — «the string **remains readable** in the raw `.db` bytes, and
still does after `VACUUM`: SQLite's `secure_delete` is off by default».

IL CLAIM, testuale dal README pubblicato:

    **Deletion removes a fact from service, not from the file.**
    `Memory.forget(fact_id)` does what it says at the database level … But the
    string **remains readable in the raw `.db` bytes**, and still does after
    `VACUUM`: SQLite's `secure_delete` is off by default, so deleted pages are
    not overwritten. This is standard SQLite behaviour, not a bug in Verimem —
    but "forgotten" here means **no longer served**, not **no longer
    recoverable**.

QUESTO E' UN LIMITE DICHIARATO, non una promessa — ed e' scritto bene: dice il
comportamento, la causa, che non e' un difetto nostro, e la conseguenza pratica
(«If you hand the file to someone else … you hand over what you believed you had
deleted»).

⚠️ PERCHE' UN PRESIDIO SU UN LIMITE. Un limite dichiarato **puo' smettere di
essere vero**, e allora il README mente **al contrario**: dichiara all'utente un
pericolo che non corre piu'. Chi legge quella riga oggi prende decisioni — cifrare
il disco, non consegnare il file, distruggere la chiave — e continuerebbe a
prenderle per un limite superato. **Un limite curato e lasciato scritto costa
quanto una promessa non mantenuta**: manda l'utente a difendersi da un problema
che non ha piu'.

MISURATO L'11/09 **LEGGENDO** (sono una lettrice, divisione del post «START
11/09»): il prodotto imposta dodici tipi di `PRAGMA`

    PRAGMA table_info · journal_mode · busy_timeout · data_version ·
    synchronous · integrity_check · foreign_keys · wal_checkpoint · …

e **`secure_delete` non e' fra questi**, ne' nei `.py` ne' in `.sql/.toml/.cfg/.ini`.
Resta quindi al default di SQLite, che e' `off`: **il limite del README e' vero.**

⚠️ QUESTO FILE NON PROVA CHE LA STRINGA RESTI LEGGIBILE NEI BYTE. Quella e' una
misura, e per farla servirebbe scrivere, cancellare e rileggere un `.db` — cioe'
ESEGUIRE, che stasera non mi compete. Questo e' un CRICCHETTO su una condizione
NECESSARIA: se `secure_delete` venisse acceso, la riga del README andrebbe
riscritta, e questo test lo chiede. Il perimetro e' dichiarato per non farlo
sembrare piu' forte di quello che e'.

    Q per l'operatore, quando servira' la misura vera:
      scrivere un fatto con una stringa-sonda, `Memory.forget`, `VACUUM`,
      poi cercare la sonda nei byte del file.
      atteso: la sonda SI TROVA (il README dice che resta) · per: README:723-733

ws7 «Iris», 11/09/2026. Scritto in lettura, NON eseguito: `ruff check` e
`ast.parse` soltanto.
"""
from __future__ import annotations

import pathlib
import re

RADICE = pathlib.Path(__file__).resolve().parents[1]
PACCHETTO = RADICE / "verimem"

#: Il pragma che, se acceso, renderebbe FALSO il limite dichiarato dal README.
_SECURE_DELETE = re.compile(r"secure_delete", re.I)

#: Qualunque pragma: serve al controllo positivo, per provare che so leggerli.
_QUALUNQUE_PRAGMA = re.compile(r"PRAGMA\s+\w+", re.I)


def _sorgenti() -> list[pathlib.Path]:
    return sorted(PACCHETTO.rglob("*.py"))


def _testo_del_pacchetto() -> str:
    pezzi = []
    for f in _sorgenti():
        try:
            pezzi.append(f.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            pass
    return "\n".join(pezzi)


# ── IL CONTROLLO POSITIVO PER PRIMO ─────────────────────────────────────────


def test_CONTROLLO_so_leggere_i_pragma_del_prodotto():
    """Se non trovassi NESSUN pragma, «secure_delete non c'è» sarebbe verde
    perché sto guardando il posto sbagliato, non perché il pragma manca."""
    testo = _testo_del_pacchetto()
    assert len(_sorgenti()) > 50, f"solo {len(_sorgenti())} file letti sotto verimem/"
    trovati = set(m.group(0).lower().split()[-1] for m in _QUALUNQUE_PRAGMA.finditer(testo))
    assert len(trovati) >= 5, (
        f"trovati solo {len(trovati)} pragma diversi ({sorted(trovati)}): questo "
        "test sta guardando la cosa sbagliata, e il cricchetto sotto sarebbe "
        "verde per cecità."
    )
    assert "journal_mode" in trovati, (
        f"`journal_mode` non compare fra i pragma letti ({sorted(trovati)}): "
        "il prodotto lo imposta, quindi se non lo vedo non sto leggendo il codice."
    )


# ── IL CRICCHETTO ───────────────────────────────────────────────────────────


def test_il_limite_del_readme_sul_vacuum_e_ANCORA_vero():
    """README:723-733 — se `secure_delete` si accende, quella riga va riscritta.

    Non è un difetto da evitare: accendere `secure_delete` sarebbe un
    MIGLIORAMENTO per la privacy. Il cricchetto non lo vieta — chiede che, il
    giorno in cui succede, **il README smetta di dichiarare un limite superato**.
    """
    colpiti = [
        f"{f.relative_to(RADICE).as_posix()}:{n}"
        for f in _sorgenti()
        for n, riga in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1)
        if _SECURE_DELETE.search(riga)
    ]
    assert not colpiti, (
        f"il prodotto ora tocca `secure_delete` ({colpiti}), e README:723-733 "
        "dichiara all'utente che «SQLite's `secure_delete` is off by default, so "
        "deleted pages are not overwritten».\n"
        "Se il pragma è stato ACCESO, quel limite non è più vero e la riga va "
        "riscritta nello stesso commit: chi la legge oggi prende decisioni vere "
        "(cifrare il disco, non consegnare il file, distruggere la chiave) per "
        "difendersi da un pericolo che non correrebbe più.\n"
        "Se invece è nominato solo in un commento o in un test, aggiungi qui "
        "l'eccezione CON la ragione scritta."
    )
