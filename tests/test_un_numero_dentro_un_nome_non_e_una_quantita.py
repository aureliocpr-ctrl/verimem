r"""T149 — il numero di una RICHIESTA non è una quantità del discorso.

IL DIFETTO, vissuto da un pari usando il prodotto per salvare le misure di una
sera: tre scritture su sette fermate da `L4.1`, e il numero contestato non era
una grandezza.

    claim «Sul tip 353b0a7e di #96 il banco rende 14 su 14.»
      estratto  [('', 14.0), ('', 96.0)]
      L4.1      ValoreAssente(valore=96.0, unita='', testo='96')
      e sulla scrittura vera: grounding_score=99.93  withheld_despite_judge=True

Il giudice era d'accordo al 99,93 e un controllo di dettaglio ha trattenuto lo
stesso, su un numero che **nomina** invece di **affermare**. Chi legge
«quarantined» riscrive la frase giusta.

⚠️ PERIMETRO STRETTO, E IL RESTO DEL TICKET RESTA APERTO DI PROPOSITO. Delle
tre forme che hanno fermato quel pari, questa è l'unica che si può chiudere
qui:

    #96                nomina una richiesta            -> QUESTA cura
    ENGRAM_BAND_LLM=0  il claim afferma una condizione che la fonte non
                       documenta: L4.1 dice una cosa VERA in modo illeggibile
                       -> la ricevuta, non il verdetto
    98.64 «ago»        un numero citato, sintatticamente identico a una
                       quantita' vera -> nessuna cura di forma lo prende

⛔ E LA CURA CHE NON SI FA, scritta qui perché non torni: «i numeri dopo `=`
non sono quantità». Le fonti di questo progetto sono piene di `EXIT=0`,
`passed=13159`, `grounding_score=100.0`; con quella regola un claim «EXIT=0»
contro una fonte «EXIT=1» **non verrebbe più colto**, e il layer che ha chiuso
l'allucinazione numerica diventerebbe cieco su un'intera classe di misure.
L'ultima cella di questo banco tiene quella porta chiusa.

RAGGIO, misurato sullo store prima della cura (18 277 fatti, sola lettura):
1339 proposizioni contengono `#<numero>`, in 1336 quel numero entra fra le
quantità, 505 sono quarantenate e **2** lo sono con `L4.1` fra i colpevoli —
entrambe con il giudice ≥ 90.
"""
from __future__ import annotations

from verimem.quantity_match import extract_quantities, numeric_conflict
from verimem.valore_non_nella_fonte import valori_non_nella_fonte

CLAIM = "Sul tip 353b0a7e di #96 il banco rende 14 su 14."
FONTE = "Il tip 353b0a7e rende 14 su 14."


def _valori(testo: str) -> set[float]:
    return {v for _, v in extract_quantities(testo)}


def test_il_numero_della_richiesta_NON_entra_fra_le_quantita():
    assert 96.0 not in _valori(CLAIM), (
        "«#96» nomina una richiesta e viene letto come una grandezza: "
        f"{sorted(_valori(CLAIM))}")


def test_CONTROLLO_POSITIVO_i_numeri_veri_della_stessa_frase_restano():
    """Senza questa cella la cura potrebbe spegnere l'intera frase e sembrare
    riuscita: il 14 è una quantità e deve restare."""
    assert 14.0 in _valori(CLAIM), (
        f"la cura ha portato via anche i numeri veri: {sorted(_valori(CLAIM))}")


def test_ALLA_FUNZIONE_L41_non_accusa_piu_il_numero_della_richiesta():
    assenti = valori_non_nella_fonte(CLAIM, FONTE)
    assert not assenti, (
        "il claim viene accusato di un valore che la fonte non contiene, e "
        f"quel valore e' il nome di una richiesta: {assenti}")


def test_CONTROLLO_POSITIVO_un_valore_DAVVERO_assente_viene_ancora_accusato():
    """L'altra metà: se questa cella tace, la cura ha spento il layer."""
    assenti = valori_non_nella_fonte(
        "Il capannone 12 misura 700 mq.", "Il capannone 12 misura 400 mq.")
    assert [a.valore for a in assenti] == [700.0], (
        f"L4.1 non vede piu' un numero assente dalla fonte: {assenti}")


def test_NEGATIVO_una_quantita_accanto_a_una_richiesta_resta_intera():
    """La forma che mi preoccupa più del difetto: la cura deve togliere il
    numero DELLA richiesta e lasciare la misura che gli sta accanto."""
    v = _valori("Nella richiesta #96 il capannone misura 400 mq.")
    assert 400.0 in v and 96.0 not in v, f"letto male: {sorted(v)}"


def test_NEGATIVO_il_conflitto_numerico_vero_continua_a_scattare():
    assert numeric_conflict("Il capannone misura 400 mq",
                            "Il capannone misura 500 mq") is not None


def test_IL_LIMITE_DICHIARATO_il_valore_di_una_manopola_resta_una_quantita():
    """⛔ LA PORTA CHE QUESTO BANCO TIENE CHIUSA, e non è un dettaglio.

    `EXIT=0` è il contenuto di mezza evidenza di questo progetto. Se un giorno
    qualcuno allarga la cura a «i numeri dopo `=` non contano» per chiudere il
    secondo caso del ticket, questa cella cade — ed è l'unico posto dove è
    scritto che quel silenzio costerebbe il confronto fra `EXIT=0` e `EXIT=1`.
    """
    assert 0.0 in _valori("Il comando rende EXIT=0."), (
        "il valore di una manopola non e' piu' una quantita': un claim "
        "«EXIT=0» contro una fonte «EXIT=1» adesso passa senza che nessuno "
        "dica niente")
    assert 13159.0 in _valori("Il runner rende passed=13159.")
