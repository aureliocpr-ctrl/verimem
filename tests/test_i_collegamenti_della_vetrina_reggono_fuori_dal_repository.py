"""I collegamenti del README funzionano anche fuori dal repository.

Il README è la descrizione lunga del pacchetto: finisce sulla pagina pubblica,
dove un percorso relativo si risolve rispetto alla pagina del pacchetto e non
rispetto al repository. Undici collegamenti erano stati misurati come non
raggiungibili il 13 agosto, navigando la pagina pubblicata; oggi la stessa misura
ne trova cinque, perché il file è vivo e nel frattempo è cambiato.

Il difetto pesa più di quanto sembri perché si somma a un altro: le cartelle dei
documenti non viaggiano col wheel. Chi vuole verificare un'affermazione non può
né seguire il collegamento né aprire il file installato — le due vie sono chiuse
insieme, e una cura sola le riapre entrambe.

E va fatta **prima** di pubblicare: la pagina di una versione già pubblicata non
si corregge, si pubblica la successiva.

Due controlli, e il secondo è quello che serve davvero:

1. nessun collegamento relativo, perché fuori dal repository non risolve;
2. ogni collegamento al nostro repository punta a un percorso che **esiste**
   nell'albero — altrimenti si sostituisce un errore con un altro errore, che è
   il modo più facile di sembrare di aver curato qualcosa.

Il terzo test tiene onesti i primi due: su un testo che contiene un collegamento
relativo il criterio deve accorgersene, o riporterebbe «nessun problema» anche
se smettesse di guardare.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parent.parent
VETRINA = RADICE / "README.md"

#: Il repository come lo dichiara ``pyproject.toml``. Scritto qui perché il
#: collaudo deve poter dire *quale* repository, non solo «un URL assoluto».
REPOSITORY = "https://github.com/aureliocpr-ctrl/verimem"

_COLLEGAMENTO = re.compile(r"\[(?P<etichetta>[^\]]{0,80})\]\((?P<url>[^)\s]+)\)")


def _collegamenti(testo: str) -> list[tuple[str, str]]:
    return [(m.group("etichetta"), m.group("url")) for m in _COLLEGAMENTO.finditer(testo)]


def _relativi(testo: str) -> list[tuple[str, str]]:
    return [(e, u) for e, u in _collegamenti(testo)
            if not u.startswith(("http://", "https://", "#", "mailto:"))]


@pytest.fixture(scope="module")
def vetrina() -> str:
    return VETRINA.read_text(encoding="utf-8")


def test_nessun_collegamento_e_relativo(vetrina: str):
    """Fuori dal repository un percorso relativo non ha modo di risolvere."""
    relativi = _relativi(vetrina)
    assert not relativi, (
        "questi collegamenti danno pagina-non-trovata sulla pagina pubblica, "
        f"dove si risolvono rispetto al pacchetto e non al repository: {relativi}. "
        f"Cura: anteporre {REPOSITORY}/blob/main/ (o /tree/main/ per una cartella).")


def test_ogni_collegamento_al_repository_punta_a_qualcosa_che_esiste(vetrina: str):
    """Il controllo che impedisce di sostituire un errore con un altro errore."""
    rotti = []
    for etichetta, url in _collegamenti(vetrina):
        if not url.startswith(REPOSITORY):
            continue
        resto = url[len(REPOSITORY):].split("#")[0].strip("/")
        for prefisso in ("blob/main/", "tree/main/"):
            if resto.startswith(prefisso):
                percorso = RADICE / resto[len(prefisso):]
                if not percorso.exists():
                    rotti.append((etichetta, url))
    assert not rotti, (
        f"questi collegamenti puntano al nostro repository ma il percorso non "
        f"esiste nell'albero: {rotti}")


def test_il_criterio_riconosce_un_collegamento_relativo():
    """Il controllo positivo: senza questo, «nessun relativo» non significa nulla."""
    finto = "Vedi [le note](./NOTE.md) e [la pagina](https://example.org/x) e [qui](#sezione)."
    trovati = _relativi(finto)
    assert trovati == [("le note", "./NOTE.md")], (
        f"il criterio non separa un collegamento relativo da uno assoluto o da "
        f"un'àncora: ha trovato {trovati}")
