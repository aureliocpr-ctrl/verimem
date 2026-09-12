"""Il cricchetto sui nomi: il conteggio puo' SCENDERE, mai salire.

PERCHE' ESISTE, misurato il 12/09/2026. La pulizia dei documenti e' una
**fotografia, non uno stato**: mentre ripulivo 98 file, `docs/stato-reale/mappa/
mcp_server.md` e' arrivato su `main` **con due nomi dentro**, e nessuno se n'e'
accorto finche' non l'ho rimisurato a mano. ⇒ Senza un cricchetto, ogni PR che
tocca `docs/` puo' rialzare il conteggio in silenzio e il lavoro si consuma da se'.

COME FUNZIONA: un TETTO che scende. Non pretende zero — pretende che **non si
peggiori**. Quando una PR di pulizia entra, si abbassa la soglia nello stesso
commit: e' l'unico modo in cui questo numero puo' cambiare.

ESCLUSI, per decisione e con la ragione scritta:
  · `docs/**/banchi*/` — sono banchi, e i loro path assoluti sono CODICE
    eseguibile: mascherarli li romperebbe (78 righe su 80 sono `sys.path.insert`,
    `sqlite3.connect`). E' un ticket di codice, non di documentazione.
  · `00-ESAME.md` — contiene nomi usati come **DATI DI PROVA** («Corrado Ferri,
    job title is giardiniere»): sostituirli non anonimizza niente e **corrompe la
    misura** su cui il giudice e' stato valutato.

⚠️ LIMITE DICHIARATO: **non eseguito da chi lo ha scritto** (sola lettura oggi).
Atteso: **2 passed**.
"""

from __future__ import annotations

import re
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
DOCUMENTI = RADICE / "docs"

#: I nomi umani delle istanze, nelle due grafie. CASE-SENSITIVE di proposito:
#: ignorare il caso riscrive le parole italiane che li contengono («caldo»
#: contiene «aldo», e una sostituzione cieca ne rompe 35 in un file solo).
_BASE = ["Marie", "Giano", "Galileo", "Nadia", "Tara", "Aldo", "Iris", "Corrado"]
_NOMI = _BASE + [n.upper() for n in _BASE]
#: Confini espliciti, NON `\b`: `\b` non morde sulle caporali «Iris» (multibyte).
_NP = r"[^0-9A-Za-zÀ-ÿ_]"
_PAT = re.compile("|".join(f"(?:^|{_NP}){n}(?:{_NP}|$)" for n in _NOMI))

#: 🔒 IL TETTO, misurato su `origin/main`.
#: **Si abbassa soltanto**, nello stesso commit della pulizia che lo consente.
#: Se stai per ALZARLO, fermati: e' il difetto che questo file esiste per vedere.
#:
#:   86  su `b96f4088`, il 12/09 alle 18:15
#:    6  su `8acff799`, dopo il merge della PR di pulizia (12/09, 19:15)
#:        — nella sola `docs/stato-reale/` sono passati da 81 a 1, e quell'1 e'
#:          `00-ESAME.md`, escluso qui perche' i suoi nomi sono DATI DI PROVA.
#:          I 6 che restano stanno fuori da `stato-reale/` (`ricerca/`,
#:          `mondo-esterno/`): erano fuori dal perimetro di quella pulizia.
TETTO = 6


def _e_un_banco(f: Path) -> bool:
    """I banchi stanno in `banchi/`, `banchi-04/`, `banchi-ws2/`…

    ⚠️ Il 12/09 un filtro scritto `"/banchi/" in path` ne prendeva UNA cartella su
    tre, e tre file di banco stavano per entrare in una cura che li escludeva: la
    stessa forma d'errore del righello, stavolta nel filtro che protegge.
    """
    return any(p.startswith("banchi") for p in f.parts)


def _documenti_da_guardare() -> list[Path]:
    return [
        f
        for f in sorted(DOCUMENTI.rglob("*.md"))
        if not _e_un_banco(f) and f.name != "00-ESAME.md"
    ]


def _con_un_nome() -> list[str]:
    fuori = []
    for f in _documenti_da_guardare():
        try:
            if _PAT.search(f.read_text(encoding="utf-8", errors="replace")):
                fuori.append(f.relative_to(RADICE).as_posix())
        except OSError:
            continue
    return fuori


def test_il_conteggio_dei_nomi_nei_documenti_non_e_salito():
    trovati = _con_un_nome()
    assert len(trovati) <= TETTO, (
        f"i documenti con un nome di istanza sono {len(trovati)}, il tetto e' "
        f"{TETTO}: **qualcuno e' risalito**. Non alzare il numero — guarda quali "
        f"file sono nuovi rispetto all'ultima pulizia e sostituisci il nome col "
        f"ruolo (QA, Porte, Piattaforma, Ricerca, ML, Dati, Release, Product "
        f"Owner). Il 12/09 e' successo mentre la pulizia era in corso: un file "
        f"e' arrivato su main con due nomi e nessuno se n'e' accorto.\n"
        f"Elenco: {trovati[:10]}{' …' if len(trovati) > 10 else ''}"
    )
    if len(trovati) < TETTO:
        print(  # noqa: T201
            f"\n[cricchetto] i documenti con un nome sono {len(trovati)}, sotto il "
            f"tetto di {TETTO}: **abbassa TETTO a {len(trovati)}** nello stesso "
            "commit, o il cricchetto protegge meno di quanto potrebbe."
        )


def test_CONTROLLO_il_righello_vede_un_nome_e_non_vede_una_parola_che_lo_contiene():
    """Senza questo, un tetto rispettato puo' voler dire che il righello e' cieco."""
    assert _PAT.search("la misura di Tara dice"), "non vede un nome in chiaro"
    assert _PAT.search("«Iris» ha scritto"), "non vede un nome fra caporali"
    assert _PAT.search("@ws1 MARIE falsifica"), "non vede la forma gridata"
    assert not _PAT.search("la taratura del giudice"), "si accende su «taratura»"
    assert not _PAT.search("il CALDO di agosto"), "si accende su «CALDO»"
    assert not _PAT.search("banchi/ws7-porte.py"), "si accende su una sigla in un path"
