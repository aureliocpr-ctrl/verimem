"""«Il fornitore Verdi non era presente» cade a 1.38, e la fonte lo sostiene.

IL DIFETTO, misurato da ws5 su quattro lingue (8 negazioni vere su 12 rifiutate,
g fra 0.42 e 1.39) e riprodotto qui su un banco indipendente::

    fonte: «Erano presenti i fornitori Bianchi e Rossi. Saldati gli ordini 77 e
            78. L'ordine 91 resta in sospeso. Hanno firmato Neri e Gialli.»

    «Il fornitore Verdi non era presente.»          g=1.3852  quarantined
    «Il cliente Rossi non ha firmato.»              g=0.7737  quarantined
    «Il fornitore Neri non ha comunicato ritardi.»  g=0.4231  quarantined
    «L'ordine 91 non e' stato saldato.»             g=90.0    AMMESSA

🔑 E L'UNICA AMMESSA È QUELLA LA CUI ASSENZA LA FONTE *ENUNCIA* («resta in
sospeso»). Le altre chiedono di dedurre l'assenza da un elenco, e un
cross-encoder di entailment **non ha l'assunzione di mondo chiuso**: «Verdi non
era presente» non è implicato da un elenco che semplicemente non lo nomina.

È la tesi di ws5 vista dal terzo lato: *«il giudice misura la COMPATIBILITÀ, non
l'IMPLICAZIONE»*. Un dettaglio in più è compatibile e passa a 99; una negazione
è incompatibile con l'elenco e cade a 0.5. **Lo stesso buco, e il lato è sempre
l'ASSENZA.** L4.1 copre l'assenza nel claim; questa è l'assenza nella fonte.

⚠️ PERCHÉ NON SI CURA CON UNA SOGLIA: ws4 ha misurato che il 91,8% dei verdetti
del moat sta agli estremi (1324 su 1673 sopra 99). Non c'è un taglio che separi,
perché il problema non è dove si taglia — è che il giudice risponde a una
domanda diversa da quella che gli stiamo facendo.

⇒ LA CURA CHE SI PUÒ CONSEGNARE È UNA DICHIARAZIONE, non un verdetto. Il gate
non può decidere se quella negazione sia vera; può smettere di far sparire il
fatto **senza dire che il giudizio non era affidabile**. È la stessa forma di
``moat``, ``quarantined_by``, ``floor_applied_by``, ``ranking``,
``hidden_records`` — e non richiede la popolazione opposta, che per un veto
sarebbe indispensabile e qui non lo è: l'avviso è vero tanto per una negazione
vera quanto per una falsa.

📌 E LA GUARDIA ESISTEVA GIÀ, su un'altra superficie: ``negation_scope``
(2026-08-04) impedisce ai nove detector L1 di punire «questo NON funziona» —
*«un gate che punisce la smentita scoraggia esattamente la scrittura più
preziosa per una memoria verificata»*. Era applicata dove si raccolgono i
warning L1 (``anti_confab_gate:1138``) e mai al moat. Ennesima istanza della
classe ②: la cura c'era, mancava lo sweep.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory

VERBALE = ("Verbale dell'assemblea. Erano presenti i fornitori Bianchi e "
           "Rossi. Sono stati saldati gli ordini 77 e 78. L'ordine 91 resta "
           "in sospeso. Hanno firmato il registro Neri e Gialli.")


@pytest.fixture()
def mem(tmp_path):
    return Memory(str(tmp_path / "s.db"))


@pytest.mark.parametrize("i,claim", list(enumerate([
    "Il fornitore Verdi non era presente.",
    "Il cliente Rossi non ha firmato.",
    "Il fornitore Neri non ha comunicato ritardi.",
])))
def test_una_negazione_bocciata_dal_moat_viene_DICHIARATA(mem, i, claim):
    """IL CUORE. Non si pretende che il fatto entri — quello richiederebbe di
    sapere se la negazione è vera, e il giudice non può dirlo. Si pretende che
    la ricevuta dica **perché** il verdetto non è affidabile, invece di
    consegnare un punteggio di 1.38 come se fosse una misura."""
    r = mem.add(claim, topic=f"az/neg{i}", source=VERBALE)
    layers = [w.get("layer") for w in (r.get("warnings") or [])]
    assert "L4-negazione" in layers, (
        f"il fatto sparisce senza che nessuno dica che era una negazione "
        f"(g={r.get('grounding_score')}, layers={layers}): {claim}")


def test_l_avviso_dice_COSA_fare_non_solo_cosa_e_successo(mem):
    """Un avviso che non indica un'uscita è rumore. Qui l'uscita esiste ed è
    quella che la fonte stessa mostra: una fonte che ENUNCIA l'assenza viene
    giudicata bene (l'ordine 91, ammesso a 90)."""
    r = mem.add("Il fornitore Verdi non era presente.", topic="az/adv",
                source=VERBALE)
    testo = " ".join(str(w.get("advice", "")) for w in (r.get("warnings") or []))
    assert "fonte" in testo.lower(), r.get("warnings")


def test_CONTROLLO_POSITIVO_un_claim_AFFERMATIVO_non_riceve_l_avviso(mem):
    """⚠️ IL PRESIDIO. Se l'avviso comparisse su tutto, non direbbe niente —
    e le due misure qui sopra sarebbero soddisfatte anche da una riga che lo
    attacca a ogni write."""
    for i, claim in enumerate(["Erano presenti i fornitori Bianchi e Rossi.",
                               "Sono stati saldati gli ordini 77 e 78."]):
        r = mem.add(claim, topic=f"az/aff{i}", source=VERBALE)
        layers = [w.get("layer") for w in (r.get("warnings") or [])]
        assert "L4-negazione" not in layers, f"avviso spurio su: {claim}"


def test_una_negazione_che_il_moat_APPROVA_non_riceve_l_avviso(mem):
    """L'altro lato del presidio, ed è il caso che spiega il difetto: quando la
    fonte ENUNCIA l'assenza («l'ordine 91 resta in sospeso») il giudice sa
    valutarla — ammessa a 90 — e non c'è nessun limite da dichiarare.

    Se questo cadesse, l'avviso starebbe dicendo «non mi fido delle negazioni»
    invece di «non mi fido di QUESTO verdetto»."""
    r = mem.add("L'ordine 91 non e' stato saldato.", topic="az/enun",
                source=VERBALE)
    layers = [w.get("layer") for w in (r.get("warnings") or [])]
    assert r.get("status") != "quarantined", (
        f"regressione: era ammessa a 90 (g={r.get('grounding_score')})")
    assert "L4-negazione" not in layers, layers


def test_senza_fonte_non_c_e_nessun_verdetto_da_dichiarare(mem):
    """Senza source il moat non gira affatto: non c'è nessun giudizio
    inaffidabile da segnalare, e aggiungere l'avviso qui sarebbe rumore su
    ogni write negativo del corpus."""
    r = mem.add("Il fornitore Verdi non era presente.", topic="az/nosrc")
    layers = [w.get("layer") for w in (r.get("warnings") or [])]
    assert "L4-negazione" not in layers, layers
