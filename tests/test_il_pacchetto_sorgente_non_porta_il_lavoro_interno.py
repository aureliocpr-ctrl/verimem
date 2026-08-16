"""Il pacchetto sorgente non porta fuori il materiale di lavoro del progetto.

Senza `MANIFEST.in` setuptools mette nell'sdist tutto l'albero, e l'albero
contiene ciò che serve a chi SVILUPPA, non a chi installa: appunti di misure,
identificativi di sessione, documenti sul rilascio. Misurati 2026-08-16 sul
pacchetto costruito da `main`: 328 occorrenze in 131 file, di cui 139 file sotto
`tests/` e 31 sotto `docs/`. Il pacchetto binario non li imbarcava già allora —
`[tool.setuptools.packages.find]` include solo i pacchetti veri — quindi i due
artefatti contenevano cose diverse senza che nessuna scelta lo avesse deciso.

Questo collaudo non ricostruisce l'sdist: sarebbe lento e legherebbe la suite a
`build`. Verifica invece la proprietà che il file deve mantenere nel tempo —
**ogni cartella di primo livello che contiene materiale interno deve essere
esclusa** — perché il modo in cui la cura si perde non è che qualcuno cancelli
`MANIFEST.in`: è che aggiunga una cartella nuova e nessuno se ne accorga.
"""
from __future__ import annotations

import re
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
MANIFEST = RADICE / "MANIFEST.in"

#: Ciò che non deve uscire dal progetto: gli identificativi di sessione con cui
#: il lavoro interno è annotato, e gli UUID.
#:
#: registro-esente: i pattern qui sotto sono il dato di prova del controllo, non
#: un'annotazione: senza, il collaudo non potrebbe cercare nulla.
_INTERNI = re.compile(r"\bws[1-8]\b|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}")

#: Le cartelle che il pacchetto sorgente deve contenere: senza queste non si
#: installa e non si compila da sorgente.
_INTOCCABILI = {"verimem", "engram", "hippoagent"}


def _cartelle_escluse() -> set[str]:
    """Le cartelle che MANIFEST.in tiene fuori dal pacchetto."""
    escluse = set()
    for riga in MANIFEST.read_text(encoding="utf-8").splitlines():
        riga = riga.strip()
        if riga.startswith("prune "):
            escluse.add(riga.split(None, 1)[1].strip().strip("/"))
    return escluse


def _cartelle_con_materiale_interno() -> dict[str, int]:
    """Le cartelle di primo livello che contengono annotazioni interne."""
    sporche: dict[str, int] = {}
    for cartella in RADICE.iterdir():
        if not cartella.is_dir() or cartella.name.startswith("."):
            continue
        if cartella.name in _INTOCCABILI:
            continue
        n = 0
        for f in cartella.rglob("*"):
            if f.is_file() and f.suffix in {".py", ".md", ".toml", ".yml", ".yaml", ".txt"}:
                n += len(_INTERNI.findall(f.read_text(encoding="utf-8", errors="replace")))
        if n:
            sporche[cartella.name] = n
    return sporche


def test_ogni_cartella_con_materiale_interno_e_esclusa_dal_pacchetto():
    """Una cartella nuova con appunti interni non deve poter entrare in silenzio."""
    escluse = _cartelle_escluse()
    dentro = {n: q for n, q in _cartelle_con_materiale_interno().items() if n not in escluse}
    assert not dentro, (
        f"queste cartelle contengono materiale di lavoro interno e MANIFEST.in non le esclude, "
        f"quindi finiscono nel pacchetto che gli utenti scaricano: {dentro}. "
        f"Aggiungere `prune <cartella>` a MANIFEST.in, oppure togliere le annotazioni interne "
        f"se la cartella deve viaggiare col pacchetto.")


def test_il_criterio_riconosce_una_cartella_non_esclusa():
    """Il controllo positivo: senza, «nessuna cartella dentro» sarebbe vero e vuoto."""
    escluse = _cartelle_escluse()
    sporche = _cartelle_con_materiale_interno()
    assert sporche, (
        "il criterio non trova materiale interno in NESSUNA cartella: o l'albero è cambiato "
        "profondamente, o il criterio ha smesso di riconoscerlo e il primo test è vuoto")
    assert sporche.keys() <= escluse, (
        f"invariante rotta: {sorted(sporche.keys() - escluse)} non sono escluse — "
        f"è la stessa cosa che dice il primo test, qui serve a provare che il criterio VEDE")


def test_le_cartelle_necessarie_non_sono_escluse():
    """Curare il difetto non deve rompere l'installazione: il pacchetto resta completo."""
    escluse = _cartelle_escluse()
    rotte = _INTOCCABILI & escluse
    assert not rotte, (
        f"MANIFEST.in esclude {sorted(rotte)}, che il pacchetto deve contenere: senza, "
        f"chi installa da sorgente non ottiene il codice")
