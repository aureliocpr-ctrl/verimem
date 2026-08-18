"""`L4.2` decideva con due lati del numero e ne stampava uno solo.

Diagnosi di ws5, 18/08, letta al sorgente e verificata qui: la decisione in
`valori_riusati_da_altro_contesto` guarda ENTRAMBI i lati —

    if claim_dopo  & fonte_dopo:  continue   # stessa grandezza: riformulazione
    if claim_prima & fonte_prima: continue   # stesso identificativo

— ma il messaggio si costruiva col solo lato che SEGUE il numero. In italiano
quel token è spessissimo una congiunzione o una preposizione, e la ricevuta
diceva cose come::

    «0.3732 qui e' "ed", nella fonte "?"»
    «99.9588 qui e' "su", nella fonte "?"»

⇒ Chi legge vede metà dell'informazione con cui il layer ha deciso, e nel caso
peggiore due `?`: nessun appiglio per correggere.

⚠️ Ciò che questo file NON tocca, e va detto perché è il rischio opposto:
`L4.2` è un AVVISO deliberato, non un veto — la scelta è misurata e dichiarata
nella docstring di `vicinato_del_valore`. La cura è sulla RICEVUTA, non sul
criterio: il criterio è posizionale, regge in IT/EN/DE/FR/ES e ha i suoi falsi
positivi dichiarati. Cambiare il testo non sposta di una virgola chi viene
avvisato.

📌 Aperto lasciato da ws5 e non chiuso qui: `L4.2` compare in 149 casi su 537
(censimento ws4), ma quante di quelle 149 abbiano il vicinato vuoto o
funzionale non è misurato — serve SQL sul corpus.
"""
from __future__ import annotations

from verimem.vicinato_del_valore import valori_riusati_da_altro_contesto


def _riuso(claim: str, fonte: str):
    return valori_riusati_da_altro_contesto(claim, fonte)


def test_quando_dopo_il_numero_non_c_e_niente_si_mostra_il_lato_PRIMA():
    """Il caso: il numero chiude la frase, quindi il lato che segue è vuoto.
    Prima qui usciva «?»; ora esce ciò che sta prima, DICHIARANDO il lato."""
    fuori = _riuso("Il totale della riga 7 e' 42.",
                   "La colonna 42 elenca i reparti, e la riga 7 e' vuota.")
    if not fuori:
        import pytest
        pytest.skip("il criterio non segnala questa coppia: il banco misura il "
                    "TESTO del messaggio, non quando esce")
    testo = " ".join(f"{r.nel_claim}|{r.nella_fonte}" for r in fuori)
    assert "?" not in testo, (
        f"la ricevuta stampa ancora «?», cioe' niente su cui agire: {testo}")


def test_il_lato_precedente_si_annuncia_invece_di_confondersi():
    """⚠️ La cura sbagliata sarebbe stampare la parola precedente COME SE
    seguisse: «linea» senza dire da che parte sta rispetto al numero è ambiguo
    quanto «?». Il presidio è sul fatto che il lato venga dichiarato."""
    from verimem.vicinato_del_valore import _da_mostrare

    assert _da_mostrare(set(), {"riga"}) == "prima del numero: riga"
    assert _da_mostrare({"pallet"}, {"riga"}) == "pallet", (
        "quando il lato che segue c'e', deve restare quello: il precedente "
        "INTEGRA, non sostituisce")


def test_senza_nessuna_parola_accanto_lo_dice_invece_di_un_punto_interrogativo():
    """L'ultimo caso: nessuno dei due lati ha parole. «?» non è una diagnosi."""
    from verimem.vicinato_del_valore import _da_mostrare

    reso = _da_mostrare(set(), set())
    assert reso != "?" and "nessuna parola" in reso, reso


def test_la_riformulazione_normale_continua_a_NON_essere_segnalata():
    """⚠️⚠️ POPOLAZIONE OPPOSTA, ed è il vincolo che conta: questa cura tocca
    solo il TESTO. Se toccasse il criterio, una riformulazione legittima
    comincerebbe a essere avvisata — e `L4.2` avvisa già 149 volte su 537."""
    assert _riuso("Il magazzino contiene 480 pallet.",
                  "Il magazzino contiene 480 pallet di merce refrigerata.") == []
