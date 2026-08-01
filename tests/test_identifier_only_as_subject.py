"""Tentativo FALSIFICATO: distinguere identificatore e valore dalla sintassi.

Il caso, trovato il 2026-07-29 da `benchmark/acceptance_is_it_actually_on.py` su
un flusso ordinario (aggiornare un runbook):

    Il servizio di fatturazione ascolta sulla porta 8443.
    Il servizio di fatturazione ascolta sulla porta 9443.

restano ENTRAMBI vivi e il recall li serve tutti e due. La causa è nota e
deliberata: `quantity_match._EVENT_INDEX_RE` elenca `port`/`porta` fra le parole
il cui numero IDENTIFICA invece di misurare, perché "issue 42" e "issue 88" sono
due cose diverse — regola nata da un caso misurato ("il fatto 3 ha 500 righe" vs
"il fatto 5 ha 200 righe": due soggetti, non un valore cambiato).

L'IPOTESI: il discriminante è strutturale. Il termine identifica quando è il
SOGGETTO ("il fatto 3 ha…") e misura quando è un COMPLEMENTO introdotto da
preposizione ("il servizio ascolta SULLA porta 8443"). Sembrava tenere insieme
entrambi i casi, e su 10 test mirati teneva.

IL CONTRO-ESEMPIO che l'ha uccisa, da un test già in suite:

    "In week 12 we shipped the gateway."
    "In week 13 we shipped the console."

"In" è una preposizione, quindi l'euristica leggeva "week 12" come complemento e
smetteva di distinguere due settimane — che sono due istanze in serie, non un
valore aggiornato. La preposizione separa la SINTASSI, non la natura del termine:
"in week 12" è un indice temporale, "sulla porta 8443" è un attributo.

Il cambiamento è stato REVOCATO (`git checkout`), non adattato aggiungendo "in"
a un'eccezione: restringere la lista ai casi che conoscevo avrebbe fatto passare
i test senza rendere la regola vera.

Il principio giusto è probabilmente tassonomico e non sintattico — `port` sta
nella lista sbagliata: non è un'istanza in serie come issue/week/sprint, è un
attributo di configurazione. Toglierlo è però una decisione di prodotto con il
suo rischio ("la porta 8443 è aperta" usa davvero la porta come soggetto) e
va misurata sul corpus prima di essere presa.

Quel che resta APERTO, e va detto per intero: due valori della stessa porta
convivono, il recall li serve entrambi, e lo scanner batch li vedrebbe
(`detect_numeric_clashes` li restituisce) mentre il write path no.
"""
from __future__ import annotations

import pytest


def test_the_measured_counterexample_that_killed_the_syntactic_rule():
    """Il test già in suite che la falsifica — qui perché la ragione resti
    attaccata al tentativo, non solo al file che lo conteneva."""
    from verimem.quantity_match import distinct_event_indices
    assert distinct_event_indices(
        "In week 12 we shipped the gateway.",
        "In week 13 we shipped the console.",
    ) is True, (
        "due settimane sono due istanze: se questo diventa False, qualcuno ha "
        "riprovato la regola sintattica che 'in' fa cadere"
    )


def test_the_original_case_the_identifier_list_exists_for():
    """L'altro lato: la regola che si vorrebbe rilassare serve davvero."""
    from verimem.quantity_match import distinct_event_indices
    assert distinct_event_indices(
        "Il fatto 3 ha 500 righe.",
        "Il fatto 5 ha 200 righe.",
    ) is True


@pytest.mark.xfail(
    reason="APERTO, non risolto: due valori della stessa porta convivono. La "
           "via sintattica è falsificata (vedi docstring); la via tassonomica "
           "— togliere `port` dalla lista degli identificatori — è una "
           "decisione di prodotto da misurare sul corpus, non da prendere di "
           "corsa. Marcato xfail e non silenziato.",
    strict=False,
)
def test_the_runbook_update_supersedes_instead_of_coexisting(tmp_path):
    from verimem.client import Memory
    m = Memory(path=tmp_path / "s.db")
    m.add("Il servizio di fatturazione ascolta sulla porta 8443.",
          topic="acc/porta",
          source="Runbook: il servizio ascolta sulla porta 8443.")
    m.add("Il servizio di fatturazione ascolta sulla porta 9443.",
          topic="acc/porta",
          source="Runbook aggiornato: la porta e ora 9443.")
    vivi = [f.proposition for f in m.semantic.all()
            if "ascolta" in f.proposition and not f.superseded_by]
    assert len(vivi) <= 1, f"due verita' vive sulla stessa porta: {vivi}"
