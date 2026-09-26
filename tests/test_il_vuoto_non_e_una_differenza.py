r"""T153 — «nessuna parola accanto» non è una parola DIVERSA: è l'assenza del
dato su cui `L4.2` decide.

IL CRITERIO DEL LAYER è «le parole di contenuto attorno al numero non si
sovrappongono fra claim e fonte». Se da un lato non c'è **nessuna** parola di
contenuto, non c'è niente da sovrapporre — e il layer accusa lo stesso.

TROVATO USANDO IL PRODOTTO, salvando un fatto vero dalla CLI:

    L4.2 — il claim riusa un numero della fonte riferendolo a un'altra
           grandezza: 1 qui e' «(nessuna parola accanto)», nella fonte
           «prima del numero: totali violazioni»; 6 qui e' «(nessuna parola
           accanto)», nella fonte «prima del numero: confronti famiglia file»

MISURA sullo store vero (sola lettura, 8787 fatti con uno span):

    L4.2 accusa                        1386
    ...e in questi UN LATO E' VUOTO     354      = 25,5% delle accuse

⚠️ LA GUARDIA C'ERA GIÀ, SU UN LATO SOLO. Il modulo salta i valori per cui la
FONTE non offre nessuna parola («valore assente: non è questo il criterio che
lo copre») e non fa lo stesso per il CLAIM. È la stessa domanda posta a due
lati e risposta una volta: la giuntura, non la logica.

⛔ E QUESTO NON RENDE `L4.2` PIÙ TIMIDO DOVE DECIDE DAVVERO: il caso in cui le
due UNITÀ nominano grandezze diverse (volume contro area) non passa dalle
parole, e la sua guardia — in arrivo con la richiesta di T105 — va messa
**PRIMA** di questa. Chi ribasa legga la nota nel modulo: se le grandezze sono
note e diverse, la differenza esiste anche senza parole accanto.
"""
from __future__ import annotations

from verimem.vicinato_del_valore import valori_riusati_da_altro_contesto

VUOTO = "(nessuna parola accanto)"

#: Il caso vissuto: il numero chiude la frase, la fonte ha parole attorno.
CLAIM_NUDO = ("I confronti di famiglia che leggono un layer sono 6, e le "
              "violazioni totali che il presidio riporta sono 1.")
FONTE_NUDA = ("violazioni totali: 1\nconfronti di famiglia nel file: 6")


def test_il_claim_senza_parole_accanto_NON_viene_accusato():
    riusati = valori_riusati_da_altro_contesto(CLAIM_NUDO, FONTE_NUDA)
    vuoti = [r for r in riusati if r.nel_claim == VUOTO or r.nella_fonte == VUOTO]
    assert not vuoti, (
        "il layer accusa un riuso dove il suo criterio non ha dati: da un "
        f"lato non c'e' nessuna parola di contenuto.\n  {vuoti}")


def test_CONTROLLO_POSITIVO_il_riuso_VERO_continua_a_scattare():
    """Le frasi vengono dal banco che presidia `L4.2`, non dalla mia memoria:
    senza questa cella la cura potrebbe spegnere il layer e sembrare riuscita."""
    assert valori_riusati_da_altro_contesto(
        "Ci sono 14 valvole.",
        "Relazione: sono stati assunti 14 operai nel trimestre."), (
        "il caso storico di L4.2 non si accende piu': la cura ha spento il "
        "layer invece di togliergli le accuse senza dati")


def test_CONTROLLO_POSITIVO_la_riformulazione_continua_a_tacere():
    assert not valori_riusati_da_altro_contesto(
        "Sono stati assunti 14 operai.",
        "Relazione: sono stati assunti 14 operai nel trimestre.")


def test_L_ORDINE_delle_due_guardie_e_QUELLO_CHE_TIENE_LA_CURA():
    """La cella che presidia l'ordine — e il caso diretto NON ESISTE, misurato.

    Servirebbe un claim con unità NOTA e grandezza diversa e allo stesso tempo
    SENZA parole di contenuto accanto al numero: la guardia del vuoto lo
    salterebbe e quella delle unità lo trattiene. Misurato prima di scrivere:

        «400 mc»                -> dopo={'mc'} prima={}    una parola c'e'
        «Il volume: 400 mc»     -> dopo={'mc'} prima={'volume'}
        «400 m3»                -> l'estrattore non legge l'unita': ('', 400.0)

    **L'unità È una parola di contenuto**, quindi un claim con unità nota non è
    mai «senza parole accanto»: il caso diretto non è costruibile, e scrivere
    una cella su un caso impossibile sarebbe peggio che non averla.

    Si presidia allora il caso MINIMO — il claim porta SOLO l'unità — che oggi
    passa dalla guardia delle unità. Il giorno in cui `_intorno` smettesse di
    contare l'unità fra le parole di contenuto (un cambio in un'altra funzione,
    non qui) quel caso diventerebbe vuoto, e a tenerlo in piedi resterebbe solo
    l'ordine: **le unità prima del vuoto**.
    """
    from verimem.vicinato_del_valore import _intorno

    dopo, prima = _intorno("400 mc", 400.0)
    assert len(dopo | prima) == 1, (
        "il caso minimo non è più minimo: l'intorno del claim ha "
        f"{sorted(dopo | prima)}, e questa cella non presidia più l'ordine")
    riusati = valori_riusati_da_altro_contesto("400 mc", "superficie: 400 mq")
    assert riusati and all(r.certo for r in riusati), (
        "un claim che porta SOLO l'unità accanto al numero non viene più "
        f"trattenuto dalla guardia delle grandezze: {riusati}")


def test_L_ORDINE_PROVATO_forzando_il_vuoto_sul_solo_lato_claim(monkeypatch):
    """E qui l'ordine si prova davvero, su un caso COSTRUITO e dichiarato tale.

    La cella sopra presidia, non prova: con l'ordine invertito resterebbe verde,
    perché «400 mc» una parola ce l'ha. Il caso che separa i due ordini in
    natura non esiste, quindi lo si costruisce in laboratorio — si forza
    l'intorno vuoto **sul solo lato del claim**, lasciando intatto quello della
    fonte (se si azzerassero entrambi, a fermare tutto sarebbe la guardia del
    valore assente, che viene ancora prima, e la cella misurerebbe quella).

        claim senza parole accanto + unita' note di grandezza DIVERSA
          unita' PRIMA del vuoto  ->  trattenuto (certo)     <- l'ordine di oggi
          vuoto PRIMA delle unita' ->  saltato, cura persa

    ⚠️ Falsificata scambiando le due guardie nel modulo: questa cella cade e
    l'altra no. È l'unica del banco che distingue i due ordini.
    """
    import verimem.vicinato_del_valore as v

    claim, fonte = "400 mc", "la superficie del lotto e' 400 mq"
    vero = v._intorno
    monkeypatch.setattr(
        v, "_intorno",
        lambda testo, valore: (set(), set()) if testo == claim
        else vero(testo, valore))

    riusati = v.valori_riusati_da_altro_contesto(claim, fonte)
    assert riusati and all(r.certo for r in riusati), (
        "con il claim senza parole accanto il caso CERTO (volume contro area) "
        "non viene piu' trattenuto: la guardia del vuoto e' finita PRIMA di "
        f"quella delle unita', e la cura di T105 e' sparita in silenzio. {riusati}")


def test_la_guardia_e_SIMMETRICA_e_lo_dice():
    """L'altro lato della stessa domanda: quando è la FONTE a non avere parole
    accanto al numero, il modulo taceva già. Questa cella tiene le due metà
    insieme, così non si torna a rispondere una sola volta.
    """
    # fonte senza parole di contenuto attorno al valore
    assert not valori_riusati_da_altro_contesto(
        "Il magazzino contiene 300 bancali.", "300")
    # claim senza parole di contenuto attorno al valore
    assert not valori_riusati_da_altro_contesto(
        "300", "Il magazzino contiene 300 bancali.")
