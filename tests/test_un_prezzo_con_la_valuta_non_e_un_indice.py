"""Un prezzo scritto con la valuta non e' un indice di evento.

LA PROMESSA, README righe 186-192: «write "the plan costs 100 €" then "…150 €" (same
source) and recall returns **only the current one**, the old `superseded_by` the new».

COSA VEDEVA L'UTENTE (25/09, job di accettazione dal wheel, windows, riga 1; rifatto sul
codice di main a3658f99 in tre forme di «stessa fonte»): tutte e due le scritture
ammesse, il livello «L3-coexistence: a contradiction was found but both facts are kept»,
nessun ritiro, e la ricerca che serve 100 € e 150 €. Con «euros» scritto in lettere la
stessa coppia si ritira.

LA CAUSA. La regola posizionale di `event_indices` legge «una parola seguita da un numero
NUDO» come un indice («message 0», «issue 42»), e il numero e' nudo quando
`extract_quantities` non gli trova un'unita'. Il simbolo della valuta non e' fra le sue
unita': «costs 150 €» diventava l'indice («costs», 150), la coppia «due record diversi»
(`_entita_diverse` → `_record_numerati_diversi` → `distinct_event_indices`), e la
coesistenza toglieva il ritiro. Un numero accanto a un simbolo o a un codice di valuta
misura un prezzo, come «45 ms»: non indicizza niente.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import distinct_event_indices, event_indices

#: lo stesso prezzo che cambia, con la valuta in ognuna delle sue posizioni
PREZZI = [
    ("The plan costs 100 € per month.", "The plan costs 150 € per month."),
    ("The plan costs 100€ per month.", "The plan costs 150€ per month."),
    ("The plan costs €100 per month.", "The plan costs €150 per month."),
    ("The plan costs 100 $ per month.", "The plan costs 150 $ per month."),
    ("The plan costs $100 per month.", "The plan costs $150 per month."),
    ("The plan costs 100 £ per month.", "The plan costs 150 £ per month."),
    ("The plan costs £100 per month.", "The plan costs £150 per month."),
    ("The plan costs EUR 100 per month.", "The plan costs EUR 150 per month."),
    ("The plan costs 100 EUR per month.", "The plan costs 150 EUR per month."),
    ("The plan costs USD 100 per month.", "The plan costs USD 150 per month."),
    ("Il piano costa 100 € al mese.", "Il piano costa 150 € al mese."),
    ("Il piano costa 99,90 € al mese.", "Il piano costa 149,90 € al mese."),
]

#: la popolazione opposta: numeri che indicizzano davvero, e che devono restare indici
INDICI_VERI = [
    ("issue 42 is open", "issue 43 is open"),
    ("On day 4 the run failed.", "On day 5 the run failed."),
    ("The bot sends message 0 to the queue.", "The bot sends message 1 to the queue."),
    ("La porta 8080 e' aperta.", "La porta 8081 e' aperta."),
]


@pytest.mark.parametrize("a, b", PREZZI)
def test_un_prezzo_con_la_valuta_non_e_un_indice(a, b):
    assert not distinct_event_indices(a, b), (
        f"due prezzi letti come record diversi: {event_indices(a)} / {event_indices(b)}")


@pytest.mark.parametrize("a, b", INDICI_VERI)
def test_CONTROLLO_gli_indici_veri_restano_indici(a, b):
    assert distinct_event_indices(a, b), (
        f"due record diversi letti come lo stesso: {event_indices(a)} / {event_indices(b)}")


# --- ALLA PORTA DELL'SDK: la riga 1 del tabellone, dal codice ------------------------

_FONTE = ["pricing-page"]


def _due_prezzi(tmp_path, vecchio, nuovo, con_testo):
    from verimem import Memory
    mem = Memory(path=tmp_path / "sem" / "sem.db")
    kw = {"verified_by": _FONTE}
    r1 = mem.add(vecchio, topic="pricing", **kw, **({"source": vecchio} if con_testo else {}))
    r2 = mem.add(nuovo, topic="pricing", **kw, **({"source": nuovo} if con_testo else {}))
    serviti = [h["text"] for h in mem.search("how much does the plan cost", k=10)]
    return mem, r1, r2, serviti


@pytest.mark.parametrize("con_testo", [False, True],
                         ids=["identita_della_fonte", "identita_e_testo_della_fonte"])
def test_la_riga_1_dal_codice_il_prezzo_aggiornato_ritira_il_vecchio(tmp_path, con_testo):
    """Le due forme di «stessa fonte» della suite: l'identita' in `verified_by` (il banco
    del README, benchmark/evolution_moat_vs_mem0.py) e l'identita' con il testo."""
    vecchio, nuovo = "The plan costs 100 € per month.", "The plan costs 150 € per month."
    mem, r1, r2, serviti = _due_prezzi(tmp_path, vecchio, nuovo, con_testo)
    assert r2.get("status") != "quarantined", r2
    assert mem.semantic.get(r1["id"]).superseded_by == r2["id"], (
        f"lo stesso piano, 100 € poi 150 € dalla stessa fonte, e il vecchio non e' "
        f"ritirato; avvisi del nuovo: {r2.get('warnings')}")
    assert nuovo in serviti and vecchio not in serviti, serviti


@pytest.mark.parametrize("con_testo", [False, True],
                         ids=["identita_della_fonte", "identita_e_testo_della_fonte"])
def test_CONTROLLO_con_euros_in_lettere_il_vecchio_si_ritira_gia(tmp_path, con_testo):
    """Il controllo positivo della scena: con la valuta in lettere il ritiro avviene
    anche prima della cura. Se questa cella cade, la scena non ritira niente e la
    cella qui sopra misurerebbe a vuoto."""
    vecchio = "The plan costs 100 euros per month."
    nuovo = "The plan costs 150 euros per month."
    mem, r1, r2, serviti = _due_prezzi(tmp_path, vecchio, nuovo, con_testo)
    assert mem.semantic.get(r1["id"]).superseded_by == r2["id"], r2.get("warnings")
    assert nuovo in serviti and vecchio not in serviti, serviti
