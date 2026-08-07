"""L4.1 quarantinava i referti di misura perché la fonte perdeva i propri numeri.

IL DIFETTO, e la popolazione l'ha isolata ws4 («21 fatti che nessun presidio
spiega»): dei quarantinati di agosto con grounding **sopra 90** — cioè che il
moat APPROVA — 20 su 21 portano ``L4.1`` e/o ``L4.2``. Sono referti di misura
puliti, numerici, con fonte::

    «Dei 1805 fatti superseduti nel corpus 1463 hanno ragione autohook…»  g=99.98
    «Il join copre 25 dei 34 quarantinati gs>90: 15 con layers L4.1+L4.2»  g=99.98
    «La data in cifre compare in 6 dei 34 quarantinati e in 84 dei 1774…»  g=99.97

🔑 L'ULTIMO È IL REFERTO CHE MISURA IL GATE, quarantinato dal gate.

LA CAUSA È UN'ASIMMETRIA FRA CLAIM E FONTE::

    CLAIM  «Dei 1805 fatti superseduti…»   -> 1805 estratto (ha l'unità «fatti»)
    FONTE  «superseded totali      1805»   -> **niente**: numero a fine riga,
                                              nessuna unità, e ``YEAR_RE`` lo
                                              scarta come ANNO

Lo stesso numero è visibile da un lato e invisibile dall'altro, quindi L4.1
conclude «la fonte non contiene 1805» — e ha ragione su ciò che *vede*.

    YEAR_RE.fullmatch("1805") -> True      YEAR_RE.fullmatch("1463") -> False
    YEAR_RE.fullmatch("1774") -> True      YEAR_RE.fullmatch("825")  -> False

⇒ **Un conteggio a quattro cifre nell'intervallo degli anni è indistinguibile da
un anno, e sparisce.** Nei referti di misura i conteggi grandi sono la norma, e
le fonti sono output di script — tabelle, `chiave=valore`, colonne — dove il
numero sta a fine riga senza unità. È la forma in cui si scrivono le prove.

⚠️ L'ESCLUSIONE DEGLI ANNI È GIUSTA, MA SOLO SUL CLAIM. Nel claim serve: «il
contratto scade nel 2027» non è una quantità inventata, e il percorso delle date
è un altro. Nella FONTE no: la fonte è materiale grezzo da cui si cerca conferma,
e scartarne i numeri non protegge da niente — **fabbrica falsi positivi**.

📌 PERCHÉ NON UNA SOGLIA SUL GROUNDING, che era la mia prima idea: l'ho
falsificata prima di scriverla. Il caso che ha motivato L4.1 — «l'ordine 77
conteneva 40 pezzi», inventato — il moat lo ammetteva a **97-99**. Una soglia a
90 avrebbe riaperto esattamente il buco che L4.1 esiste per chiudere.
"""
from __future__ import annotations

import pytest

from verimem.valore_non_nella_fonte import valori_non_nella_fonte

#: Una fonte come sono le fonti vere: l'output di uno script.
FONTE_TABELLA = (
    "  superseded_reason=autohook-snapshot daily collapse   1463\n"
    "  superseded totali                                    1805\n"
    "  ammessi di controllo                                 1774"
)


@pytest.mark.parametrize("claim", [
    "Dei 1805 fatti superseduti nel corpus 1463 hanno ragione autohook-snapshot.",
    "I fatti superseduti sono 1805 e gli ammessi di controllo 1774.",
    "Il collasso autohook riguarda 1463 dei 1805 superseduti.",
])
def test_un_referto_i_cui_numeri_STANNO_nella_fonte_passa(claim):
    """IL CUORE: ogni numero del claim è nella tabella. Che stia a fine riga,
    dopo un `=` o senza unità è una questione di FORMATO, non di verità."""
    assenti = valori_non_nella_fonte(claim, FONTE_TABELLA)
    assert not assenti, (
        f"segnalati come assenti {[v.valore for v in assenti]}, ma la fonte li "
        f"contiene: sono numeri persi dall'estrattore, non inventati dal claim")


@pytest.mark.parametrize("claim,fonte", [
    # ⚠️ LA POPOLAZIONE OPPOSTA, ed è quella che ha motivato L4.1: il moat
    # ammetteva questi a 97-99, ed è il buco che il criterio esiste per chiudere.
    ("L'ordine 77 conteneva 40 pezzi.",
     "Verbale: e' stato consegnato l'ordine 77. Ha partecipato Bianchi."),
    ("Il fornitore Bianchi ha partecipato per 45 minuti.",
     "Verbale: ha partecipato il fornitore Bianchi alla riunione."),
    # un conteggio a quattro cifre VERAMENTE inventato deve restare fermato
    ("I fatti superseduti sono 1900.", FONTE_TABELLA),
    ("Gli ammessi di controllo sono 2026.", FONTE_TABELLA),
])
def test_un_numero_DAVVERO_assente_resta_fermato(claim, fonte):
    """⚠️ IL PRESIDIO CHE RENDE CONSEGNABILE LA CURA. `1900` e `2026` sono
    proprio i valori che `YEAR_RE` riconosce come anni: se la cura li lasciasse
    passare, avrei chiuso il falso positivo aprendo il buco vero."""
    assert valori_non_nella_fonte(claim, fonte), f"ammesso: «{claim}»"


def test_un_ANNO_nel_claim_non_diventa_una_quantita():
    """L'esclusione degli anni resta dove serve — sul CLAIM. «Il contratto
    scade nel 2027» non è un dettaglio numerico inventato, e il percorso delle
    date è un altro: se questo cadesse, ogni fatto che nomina un anno
    diventerebbe un candidato quarantena."""
    fonte = "Contratto quadro con Ferrero, rinnovo automatico salvo disdetta."
    assert not valori_non_nella_fonte("Il contratto scade nel 2027.", fonte)


def test_la_fonte_TIENE_gli_anni_perche_le_servono_a_confermare():
    """L'altro lato dell'asimmetria: un claim che parla del 2027 e una fonte
    che dice 2027 devono combaciare. Se la fonte scartasse gli anni, il claim
    con l'unità li estrarrebbe e il confronto fallirebbe."""
    assert not valori_non_nella_fonte(
        "La scadenza e' fissata al 2027.",
        "Registro contratti: scadenza      2027")
