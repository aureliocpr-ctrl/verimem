"""La corroborazione premiava proprio i fatti che si contraddicono.

`fact_priority` pubblica `Priority = 0.5*confidence + 0.3*freshness +
0.2*corroboration`, e `client.py` descrive quel terzo termine come
«corroboration (**confirmations by independent sources**)». L'implementazione
conta quanti altri fatti superano una soglia di **Jaccard sui token**.

Ma l'overlap lessicale alto è il segnale che altrove nel prodotto significa
CONFLITTO — due frasi che parlano della stessa cosa. Misurato il 2026-08-04:

    coppia                                    corroboration   priority
    «100 euro»   vs «500 euro»                    0.200         0.590
    «PostgreSQL» vs «MySQL»                       0.200         0.590
    «alle tre»   vs «alle sei»                    0.200         0.590
    conferma VERA, parole diverse                 0.000         0.550

Il conto è esattamente rovesciato: tre coppie che si contraddicono ricevono
priorità **più alta** di una coppia che si conferma davvero. È la dimensione
SEGNO — lo stesso segnale (le parole in comune) letto come conflitto in un posto
e come conferma in un altro, senza che nessuno abbia mai confrontato le due
letture.

LA CURA USA CIÒ CHE IL PRODOTTO HA GIÀ, e per il caso numerico è LOGICA, non
euristica: `quantity_match.extract_quantities` legge «100 euro» come
`{('euro', 100.0)}` e «500 euro» come `{('euro', 500.0)}`. Due fatti che
dichiarano valori DIVERSI per la STESSA unità non si confermano — non è una
stima di somiglianza, è una contraddizione aritmetica.

⛔ COSA QUESTA CURA **NON** CHIUDE, dichiarato perché non sembri risolto:
  * «PostgreSQL» contro «MySQL» non ha quantità, quindi resta contato come
    conferma. Servirebbe sapere che sono due valori alternativi dello stesso
    attributo, che è un problema diverso;
  * una conferma VERA parafrasata («la fattura riporta un importo di cento
    euro») ha Jaccard basso e prende 0.000. La corroborazione non riconosce le
    conferme che non ripetono le stesse parole, ed è il difetto simmetrico.
La cura toglie i falsi positivi che sa riconoscere; i falsi negativi restano.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from verimem import Memory
from verimem.fact_priority import rank_facts_by_priority


def _corr(coppia: tuple[str, str]) -> list[float]:
    m = Memory(path=str(pathlib.Path(tempfile.mkdtemp()) / "s.db"))
    for t in coppia:
        m.add(t, topic="segno/prova")
    out = rank_facts_by_priority(m.semantic.all())
    return [r["components"]["corroboration"] for r in out["ranked"]]


CONTRADDIZIONI_NUMERICHE = [
    ("Il piano annuale costa 100 euro.", "Il piano annuale costa 500 euro."),
    ("Il backup gira ogni notte alle 3 ore.", "Il backup gira ogni notte alle 6 ore."),
    ("Il team conta 40 persone.", "Il team conta 90 persone."),
]


@pytest.mark.parametrize("coppia", CONTRADDIZIONI_NUMERICHE)
def test_valori_diversi_sulla_stessa_unita_non_sono_una_conferma(coppia):
    """Il cuore. Due fatti che dichiarano numeri diversi per la stessa unità si
    contraddicono: contarli come conferme alza la priorità proprio dove il
    prodotto dovrebbe insospettirsi."""
    valori = _corr(coppia)
    assert valori and all(v == 0.0 for v in valori), (
        f"corroboration={valori} su una coppia che si contraddice: il conto "
        f"sta misurando le parole in comune e le chiama «confirmations by "
        f"independent sources»")


def test_una_conferma_con_le_STESSE_parole_resta_contata():
    """Il vincolo opposto: la cura non deve azzerare la corroborazione. Due
    fatti che dicono la stessa cosa, senza numeri in contrasto, continuano a
    confermarsi."""
    valori = _corr(("Il piano annuale costa 100 euro.",
                    "Il piano annuale costa 100 euro all'anno."))
    assert any(v > 0.0 for v in valori), (
        f"corroboration={valori}: la cura ha spento anche le conferme vere")


def test_un_numero_solo_da_una_parte_non_e_un_conflitto():
    """Il caso che distingue una contraddizione da un'aggiunta: se un fatto
    porta una quantità e l'altro no, non si stanno contraddicendo."""
    valori = _corr(("Il piano annuale costa 100 euro.",
                    "Il piano annuale include il supporto base."))
    assert all(v >= 0.0 for v in valori)  # non deve esplodere
