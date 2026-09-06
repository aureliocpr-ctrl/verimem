"""Una parola inglese in -ed («passed», «failed», «quarantined», «skipped») dentro
una frase ITALIANA e' un nome (l'esito di pytest, lo status del gate), non un
verbo finito: «…ha claim falso 1.18 ed esito quarantined» non deve dare il
pezzo nudo «Esito quarantined.» giudicato da solo.

Da dove viene (06/09, banco ws3-i-102-claim-caduti-etichettati-a-mano): fra i
102 claim caduti sotto il giudice nei 96 «crolli» di P-A, 17 avevano come UNICO
verbo finito una parola in -ed, e 14 record su 96 crollavano SOLO per questo:
senza la regola inglese il pezzo si fonde alla testa e non viene giudicato da
solo. La regola -ed resta per l'inglese: «The test failed and the build passed»
sono due claim. Il criterio: una parola in -ed fa da verbo finito solo se il
pezzo contiene almeno una parola-funzione inglese.
"""
from __future__ import annotations

import pytest

from verimem.atomic_claims import decomponi, ha_verbo_finito

ITALIANE_CON_ED = [
    # (scrittura, numero di claim atteso)
    pytest.param(
        "Nel banco di conferma il caso LUNGH IT+parola+EN uni ha claim falso 1.18 ed esito quarantined.", 1,
        marks=pytest.mark.xfail(strict=True, reason=(
            "SECONDO DIFETTO, trovato dalla cura: senza verbo il pezzo «esito quarantined» cade nel ramo del "
            "participio ellittico, perche' _RE_PARTICIPIO_INIZIALE legge «esito» come participio in -ito "
            "(es-ito) e gli presta l'ausiliare «ha» della testa: esce «…uni ha esito quarantined.», un pezzo "
            "con contesto ma ancora giudicato da solo. La cura sta nel participio, non nella regola -ed."))),
    ("Il fatto 2 con source ② ha grounding 38.2 ed e' quarantined.", 2),  # «e' quarantined»: copula, si spezza
    ("Il file dei test da 2 failed e 2 passed.", 1),
    ("Con la cura il file da 4 passed e senza la cura 3 failed e 1 passed.", 1),
    ("Il run riporta 12 failed e 62 skipped.", 1),
]
INGLESI = [
    ("The test failed and the build passed.", 2),
    ("The migration completed and the smoke test passed on windows.", 2),
]


@pytest.mark.parametrize("testo, attesi", ITALIANE_CON_ED)
def test_in_una_frase_italiana_la_parola_in_ed_non_fa_da_verbo(testo, attesi):
    claims = decomponi(testo)
    assert len(claims) == attesi, claims
    assert not any(c.split()[0].lower() in ("esito", "un", "e") and c.rstrip(".").split()[-1].endswith("ed") and len(c.split()) <= 2
                   for c in claims), claims


@pytest.mark.parametrize("testo, attesi", INGLESI)
def test_in_inglese_la_parola_in_ed_resta_un_verbo(testo, attesi):
    assert len(decomponi(testo)) == attesi, decomponi(testo)


@pytest.mark.parametrize("pezzo", ["Esito quarantined", "2 passed", "Un quarantined", "62 skipped"])
def test_un_pezzo_italiano_con_la_sola_parola_in_ed_non_ha_verbo_finito(pezzo):
    assert not ha_verbo_finito(pezzo), pezzo


@pytest.mark.parametrize("pezzo", ["the build passed", "it failed", "tests passed on windows"])
def test_un_pezzo_inglese_con_la_parola_in_ed_ha_verbo_finito(pezzo):
    assert ha_verbo_finito(pezzo), pezzo
