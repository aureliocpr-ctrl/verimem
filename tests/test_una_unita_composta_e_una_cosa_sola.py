r"""T105 — «400 metri cubi» e «400 metri quadri» non sono lo stesso fatto.

IL DIFETTO, misurato il 19/09 e confermato dal censimento di un pari
(12 unita' composte su 16 troncate):

    extract_quantities('...400 metri cubi')    -> {('metro', 400.0), ...}
    extract_quantities('...400 metri quadri')  -> {('metro', 400.0), ...}

L'unita' e' «UNA parola dopo il numero» (`_QUANT_RE`, un solo gruppo
`([^\W\d_]+)`), quindi il qualificatore si perde e due GRANDEZZE diverse
arrivano al confronto identiche. Il contratto del modulo — «un valore DIVERSO
per la STESSA unita' normalizzata» — e' sano: e' la sua precondizione a essere
rotta a monte.

DUE FACCE, e la cura deve reggerle entrambe:
    italiano   «metri cubi»    -> si perde l'AGGETTIVO  (nome + aggettivo)
    inglese    «cubic meters»  -> si perde il SOSTANTIVO (aggettivo + nome)

COSA NON DEVE SUCCEDERE, ed e' meta' del banco: due SCRITTURE della stessa
grandezza («400 m²» e «400 mq») devono restare la stessa cosa, e una fonte con
un numero NUDO («superficie: 400») non deve accusare nessuno. Una cura che
fermi di piu' e' peggio del difetto: qui si downgrada un fatto vero.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import extract_quantities, numeric_conflict


def _unita(testo: str) -> set[str]:
    """Le unita' lette, senza i valori: e' il livello dove nasce il difetto."""
    return {u for u, _ in extract_quantities(testo)}


# ------------------------------------------------- il difetto, in due lingue

def test_metri_cubi_e_metri_quadri_NON_sono_la_stessa_unita():
    cubi = _unita("Il capannone 12 misura 400 metri cubi")
    quadri = _unita("Il capannone 12 misura 400 metri quadri")
    assert cubi != quadri, (
        "due grandezze diverse arrivano al confronto IDENTICHE: il "
        f"qualificatore si perde.\n  cubi={sorted(cubi)}  quadri={sorted(quadri)}")


def test_in_inglese_si_perde_il_SOSTANTIVO_invece_dell_aggettivo():
    """L'altro ordine: «cubic meters» contro «cubic inches».

    E qui l'errore che passa e' grande **61 024 volte** (1 m3 = 61 023,7 in3):
    non e' la FREQUENZA a rendere il caso grave — quella non l'ho misurata — e'
    la TAGLIA dello sbaglio che il gate lascia passare per un fatto coerente.
    """
    metri = _unita("The tank holds 400 cubic meters")
    pollici = _unita("The tank holds 400 cubic inches")
    assert metri != pollici, (
        f"metri={sorted(metri)}  pollici={sorted(pollici)}")


# ------------------------------------- le tre celle di @Iris, al livello giusto

def test_IRIS_1_stesso_numero_unita_diversa_e_un_conflitto():
    """La cella rossa del banco di @Iris, qui sulla superficie condivisa."""
    c = numeric_conflict("Il capannone 12 misura 400 metri cubi",
                         "Il capannone 12 misura 400 mq")
    assert c is not None, (
        "stesso soggetto, stessa cifra, grandezze diverse: non e' un conflitto")


def test_IRIS_2_CONTROLLO_lo_stesso_claim_della_fonte_non_e_un_conflitto():
    assert numeric_conflict("Il capannone 12 misura 400 metri quadri",
                            "Il capannone 12 misura 400 mq") is None


def test_IRIS_3_CONTROLLO_cifra_diversa_stessa_unita_resta_un_conflitto():
    c = numeric_conflict("Il capannone 12 misura 401 metri quadri",
                         "Il capannone 12 misura 400 metri quadri")
    assert c is not None, "il caso che il prodotto gia' prendeva non deve cadere"


# ----------------------------------------- i due negativi che mi preoccupano

@pytest.mark.parametrize("a,b", [
    ("Il capannone 12 misura 400 m²", "Il capannone 12 misura 400 mq"),
    ("Il capannone 12 misura 400 metri quadrati", "Il capannone 12 misura 400 mq"),
])
def test_NEGATIVO_due_SCRITTURE_della_stessa_grandezza_non_sono_un_conflitto(a, b):
    """Il caso che mi preoccupa piu' del difetto: una differenza di FORMA
    letta come differenza di GRANDEZZA downgrada un fatto vero."""
    assert numeric_conflict(a, b) is None, (
        f"«{a}» e «{b}» dicono la stessa cosa e il gate le accusa")


def test_NEGATIVO_un_numero_NUDO_nella_fonte_non_accusa_nessuno():
    """«superficie: 400» non dichiara un'unita': senza le DUE unita' non c'e'
    niente da confrontare, e accusare sarebbe inventare."""
    assert numeric_conflict("Il capannone 12 misura 400 mq",
                            "superficie del capannone 12: 400") is None


def test_ALLA_PORTA_il_claim_con_la_grandezza_sbagliata_non_passa(tmp_path):
    """IL LIVELLO CHE CONTA, e la cella che mancava alla prima versione.

    Le celle sopra misurano `numeric_conflict`, cioe' la superficie condivisa.
    Il banco di @Iris misurava la PORTA: scriveva davvero e leggeva la ricevuta
    («admitted 96.01»). Sono due livelli, e il 19/09 ho consegnato una PR con
    la funzione verde e la porta **immutata**: il difetto si vedeva ancora.

    ⚠️ Questa cella non e' un doppione: `valori_non_nella_fonte` confronta i
    VALORI e basta (`set[float]`), quindi «400» c'e' nella fonte e nessuno
    parla. L'unita' alla porta non la guardava nessuno.
    """
    from verimem.client import Memory

    fonte = "Perizia del 2026-09-01: il capannone 12 misura 400 mq."
    r = Memory(tmp_path / "m.db").add(
        "Il capannone 12 misura 400 metri cubi.", topic="prova/t105", source=fonte)
    strati = [w.get("layer") for w in (r.get("warnings") or [])]
    assert r.get("status") == "quarantined", (
        "stessa cifra, grandezza diversa: alla porta passa come un fatto "
        f"coerente.\n  status={r.get('status')}  g={r.get('grounding_score')}  "
        f"strati={strati}")
    #: ⚠️ E DEVE ESSERE TRATTENUTO DA QUESTO LAYER, non da un altro. Il
    #: giudice qui APPROVA (89,4 contro un taglio di 40): senza questa riga la
    #: cella resterebbe verde anche il giorno che a fermarlo fosse un
    #: punteggio basso, cioe' misurerebbe il verdetto giusto per la ragione
    #: sbagliata — e la cura che sta presidiando sarebbe gia' sparita.
    assert "L4.2-grandezza" in strati, (
        f"trattenuto, ma non da chi doveva: strati={strati}")


def test_STRETTA_l_euristica_delle_parole_resta_un_avviso():
    """LA META' CHE MISURA LA STRETTEZZA — e senza, «fermiamo tutto» passa.

    `L4.2` nasce dalle PAROLE attorno al numero e sui riformulati veri sbaglia
    1 volta su 5 (banco lingue: «300 pallet» contro «300 bancali»). La
    decisione del lead e' stretta: trattiene SOLO il caso che le UNITA'
    stabiliscono. Questa cella tiene i due gradi separati al livello dove la
    differenza e' scritta — il campo `certo` e l'insieme che vale il giudice —
    perche' alla porta il caso storico e' fermato dal giudice stesso (g=27,7) e
    una cella li' non distinguerebbe la mia cura dal suo verdetto.
    """
    from verimem.anti_confab_gate import LAYER_NUMERICI_COME_IL_GIUDICE
    from verimem.vicinato_del_valore import valori_riusati_da_altro_contesto

    #: ⚠️ LE FRASI VENGONO DAL BANCO CHE PRESIDIA `L4.2`, non dal commento del
    #: modulo: la prima versione di questa cella le aveva ricostruite a memoria
    #: («l'impianto ha 14 valvole» contro «l'impianto ha 14 operai») e la
    #: parola condivisa spegneva il rilevatore — il banco misurava il vuoto e
    #: me l'ha detto il suo stesso controllo.
    euristici = valori_riusati_da_altro_contesto(
        "Ci sono 14 valvole.",
        "Relazione: sono stati assunti 14 operai nel trimestre.")
    assert euristici, (
        "il caso storico di L4.2 non si accende piu': questo banco sta "
        "misurando il vuoto")
    assert not any(r.certo for r in euristici), (
        f"un verdetto delle sole parole si dichiara certo: {euristici}")

    certi = valori_riusati_da_altro_contesto(
        "Il capannone 12 misura 400 metri cubi.",
        "Perizia: il capannone 12 misura 400 mq.")
    assert certi and all(r.certo for r in certi), (
        f"le unita' dicono volume contro area e il caso non e' certo: {certi}")

    assert "L4.2" not in LAYER_NUMERICI_COME_IL_GIUDICE, (
        "l'euristica delle parole e' entrata fra i layer che trattengono: la "
        "cura non e' piu' stretta e paga il 20% dei riformulati veri")
    assert "L4.2-grandezza" in LAYER_NUMERICI_COME_IL_GIUDICE


def test_ALLA_PORTA_CONTROLLO_il_claim_giusto_resta_ammesso(tmp_path):
    """L'altra meta': senza, «fermiamo tutto» passerebbe."""
    from verimem.client import Memory

    fonte = "Perizia del 2026-09-01: il capannone 12 misura 400 mq."
    r = Memory(tmp_path / "m.db").add(
        "Il capannone 12 misura 400 metri quadri.", topic="prova/t105", source=fonte)
    assert r.get("status") != "quarantined", (
        f"il claim che RIPETE la fonte viene fermato: {r.get('status')}")
