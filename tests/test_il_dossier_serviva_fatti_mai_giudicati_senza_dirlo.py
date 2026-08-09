"""Il dossier di provenienza serviva fatti MAI GIUDICATI senza dichiararlo.

FINDING DI ws5, dogfooding da utente esterno, quattro casi::

    caso                    abstained   facts   grounding   esito
    1 vivo e verificato       False       1      99.855     corretto
    2 FUORI corpus            True        0      —          CORRETTO
    3 fatto ARCHIVIATO        False       1      99.855     SBAGLIATO
    4 grounding NULL          False       1      None       DISCUTIBILE

Questo file cura il **caso 4**. Un fatto scritto senza `source` ha
``grounding_score = None``, che significa **mai giudicato** — non «giudicato e
passato». Le istruzioni del server MCP lo dicono testuali: *«`null` means NEVER
JUDGED, not judged and failed — treat it as a claim, not a fact»*. E il dossier
lo serviva con ``abstained: False`` e nessun avviso.

🔑 LA DIAGNOSI È DI ws5, e la sua frase è la cosa migliore scritta stanotte:

    «Il pavimento misura la RILEVANZA. Il claim promette la FONDATEZZA.
     Sono due cose diverse, e la distanza fra le due è esattamente dove il
     prodotto sbaglia.»

⚠️ QUINDI NON SI TOCCA ``abstained``: quel campo è il verdetto sulla RILEVANZA
(«non ho niente di abbastanza vicino») e deve restare tale — su una domanda
fuori corpus funziona bene, con la sua ragione dichiarata. Si aggiunge il campo
che dice la FONDATEZZA, così le due grandezze smettono di essere confuse in un
verdetto solo.

📌 Il caso 3 — il gemello archiviato, che risponde DC-Sud a una domanda su
DC-Nord con grounding 99.855 — NON è curato qui, ed è il più grave. È lo stesso
fenomeno di `hidden_records` (S-007 ritirato → risponde S-025) ma la cura non
lo raggiunge per due motivi verificati: `hidden_records` è agganciato al RECALL
e non a `explain`, e comunque `codes_in` vuole sigla-trattino-CIFRE, mentre
«DC-Nord» ha lettere dopo il trattino. Lasciato a ws5 con una domanda aperta.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory


@pytest.fixture()
def mem(tmp_path):
    return Memory(str(tmp_path / "s.db"))


DOMANDA = "Quanti metri quadrati ha il magazzino centrale?"
FATTO = "Il magazzino centrale di Rovigo ha 4200 metri quadrati."


def test_un_fatto_mai_giudicato_viene_dichiarato(mem):
    """IL CUORE: scritto senza `source`, quindi il moat non ha mai girato.
    Il dato (`grounding_score: None`) c'era già; mancava il VERDETTO."""
    mem.add(FATTO, topic="az/mag")          # nessun source: mai giudicato
    rep = mem.explain(DOMANDA, k=3, min_relevance=0.0)
    assert rep.get("facts"), rep
    assert rep.get("ungrounded_facts") == 1, sorted(rep)
    assert rep.get("grounding_checked") is False, (
        "il dossier deve dire che la fondatezza NON è stata verificata")


def test_abstained_NON_cambia(mem):
    """IL PRESIDIO PRINCIPALE, ed è la diagnosi di ws5 messa in un test:
    `abstained` è il verdetto sulla RILEVANZA e resta quello. Se un giorno
    questo test cade, qualcuno ha fatto astenere il dossier per una ragione
    di fondatezza — e le due grandezze sono tornate confuse."""
    mem.add(FATTO, topic="az/mag")
    assert mem.explain(DOMANDA, k=3, min_relevance=0.0).get("abstained") is False


def test_una_domanda_fuori_corpus_si_astiene_ancora(mem):
    """L'ALTRO PRESIDIO: il caso 2 di ws5, l'unico dove il claim era VERO e
    funzionava bene. Non deve cambiare di una virgola."""
    mem.add(FATTO, topic="az/mag")
    rep = mem.explain("quale database usa il cluster di produzione", k=3,
                      min_relevance="auto")
    assert rep.get("abstained") is True
    assert not (rep.get("facts") or [])


def test_un_fatto_giudicato_non_viene_marcato(mem):
    """Il verso opposto: con una fonte che lo sostiene, il moat gira, il
    punteggio c'è e il dossier non dichiara nulla di anomalo."""
    mem.add(FATTO, topic="az/mag",
            source="Planimetria 2026: magazzino centrale di Rovigo, "
                   "superficie 4200 metri quadrati.")
    rep = mem.explain(DOMANDA, k=3, min_relevance=0.0)
    assert rep.get("facts"), rep
    assert rep.get("ungrounded_facts") == 0, rep.get("facts")
    assert rep.get("grounding_checked") is True


def test_trust_report_esiste_e_e_lo_stesso_dossier(mem):
    """IL NOME. ws5, che usa il prodotto da due giorni: «ho cercato
    trust_report, non l'ho trovato, e stavo per scrivervi che mancava».

    Le istruzioni del server MCP dicono `verimem_trust_report`, l'SDK ha
    `explain`, e nessuno dei due rimandava all'altro."""
    mem.add(FATTO, topic="az/mag")
    a = mem.trust_report(DOMANDA, k=3, min_relevance=0.0)
    b = mem.explain(DOMANDA, k=3, min_relevance=0.0)
    assert a.keys() == b.keys()
    assert a.get("abstained") == b.get("abstained")


def test_l_errore_nomina_il_metodo_CHIAMATO(mem):
    """⚠️ E NON È UN ALIAS SECCO, di proposito. `correct` è un alias di
    `update`, e chiamandolo con gli argomenti sbagliati l'errore dice
    «Memory.update() missing 1 required positional argument» — cioè nomina una
    funzione che chi scrive non ha mai chiamato, e la cerca invano nel proprio
    codice. Misurato stanotte su `correct`. Qui no."""
    with pytest.raises(TypeError, match="trust_report"):
        mem.trust_report()
