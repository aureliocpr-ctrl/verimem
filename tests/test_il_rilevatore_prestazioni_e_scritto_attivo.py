"""Il rilevatore L1.9 e' scritto in forma ATTIVA, le self-claim si scrivono PASSIVE.

Misurato il 2026-08-26 alle 20:00, `1bcf0d17`, fuori da pytest, store temporaneo,
`ENGRAM_L1_DOMAIN_PRECISION` non impostata (default ON):

    pattern     ATTIVA (come e' scritto)          PASSIVA (come si scrive)
    dimezza     TRATT L1.9                        passa -
    raddoppia   TRATT L1.9                        passa -
    ridotto     TRATT L1.9                        passa -
    volte       TRATT L1.9                        TRATT L1.9,L1.20
    ⇒ attiva 4/4 · passiva 1/4

Il pattern `italian_qualitative` in `l1_performance_detector.py:126` e' scritto
attivo-transitivo — «dimezza» seguito dall'articolo e dalla grandezza — e
intercetta «il commit dimezza la latenza». Ma chi si vanta scrive
«la latenza e' dimezzata».
L'unico caso che regge in tutte e due le forme e' «N volte piu' veloce», che e'
gia' copulativo per costruzione.

⚠️ NON e' un difetto italiano: «The latency is halved» e «The throughput is
doubled» passano allo stesso modo. Sulla matrice 6 grandezze x 2 lingue x
{assoluto, comparativo} i buchi sono 19 su 24 — **10 italiani e 9 inglesi**.

📖 Il commento a `l1_performance_detector.py:138-144` riporta una misura del
2026-08-03 che concludeva «ogni lingua copriva meta' del caso»: quella misura
usava una sola forma verbale, e per caso proprio l'unica immune al difetto.
Il presidio che gia' esisteva (`test_anti_confab_gate_l19_wire.py`) prova
«12s->1s game changer» e «10x faster baseline»: nessuna forma passiva.

Il controllo positivo — che la forma ATTIVA sia davvero trattenuta — sta DENTRO
questo banco e non e' xfail: se cade lui, questa misura non vale niente e gli
xfail qui sotto non misurano il prodotto ma il mio righello.
"""

from __future__ import annotations

import pathlib
import tempfile

import pytest

from verimem import Memory


@pytest.fixture()
def mem() -> Memory:
    return Memory(path=str(pathlib.Path(tempfile.mkdtemp()) / "perf.db"))


def _trattenuta(mem: Memory, frase: str) -> bool:
    return mem.add(frase, topic="prestazioni/prova").get("status") == "quarantined"


# ── IL CONTROLLO POSITIVO: se questo cade, gli xfail sotto non significano nulla
@pytest.mark.parametrize(
    "attiva",
    [
        "Il commit dimezza la latenza.",
        "La patch raddoppia il throughput.",
        "Il fix ha tagliato di un terzo la latenza.",
        "Il modulo e dieci volte piu veloce.",
    ],
)
def test_IL_RIGHELLO_la_forma_attiva_e_davvero_trattenuta(mem, attiva):
    assert _trattenuta(mem, attiva), (
        f"il controllo positivo e' caduto su {attiva!r}: L1.9 non intercetta "
        "nemmeno la forma che dichiara di coprire, quindi gli xfail di questo "
        "banco misurano il righello e non il prodotto"
    )


# ── IL DIFETTO: la forma in cui le self-claim si scrivono davvero
@pytest.mark.xfail(
    strict=True,
    reason="L1.9 e' scritto attivo-transitivo: la passiva non e' intercettata "
    "(misurato 2026-08-26, passiva 1/4 contro attiva 4/4)",
)
@pytest.mark.parametrize(
    "passiva",
    [
        "La latenza e dimezzata.",
        "Il throughput e raddoppiato.",
        "La latenza e stata tagliata di un terzo.",
    ],
)
def test_LA_FORMA_PASSIVA_dovrebbe_essere_trattenuta_come_l_attiva(mem, passiva):
    assert _trattenuta(mem, passiva)


# ── E il gemello inglese, perche' «e' un difetto italiano» sarebbe la diagnosi
#    comoda e i numeri dicono il contrario: 10 buchi IT contro 9 EN.
@pytest.mark.xfail(
    strict=True,
    reason="stesso difetto in inglese: la forma passiva non e' intercettata "
    "nemmeno li', quindi la cura non e' aggiungere italiano",
)
@pytest.mark.parametrize(
    "passive",
    ["The latency is halved.", "The throughput is doubled."],
)
def test_E_NON_E_UN_DIFETTO_ITALIANO_anche_l_inglese_passivo_passa(mem, passive):
    assert _trattenuta(mem, passive)
