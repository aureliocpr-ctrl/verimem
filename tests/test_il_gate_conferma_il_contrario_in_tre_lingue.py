"""In coreano, hindi e turco il gate conferma una frase NEGATA.

Il presidio gemello — `test_il_gate_puo_solo_bocciare_in_tre_lingue` — ha
misurato e poi fatto curare l'asimmetria opposta: in russo, cinese e giapponese
il gate non sapeva **confermare** e sapeva ancora **bocciare**. Restava muto,
che è grave.

⚠️ **Questa è la faccia peggiore.** Non tace: dice di sì. Con lo stesso fatto in
memoria, alla stessa porta pubblica (`validate_claim`), misurato il 15/08::

    lingua   identico       valore diverso   NEGATO
    EN       supported      contradicted     contradicted     ← riferimento
    KO       supported      contradicted     **supported**  ❌
    HI       supported      contradicted     **supported**  ❌
    TR       supported      contradicted     **supported**  ❌
    AR       supported      contradicted     contradicted     ← funziona
    TH       unknown ❌      contradicted     unknown ❌       ← altro difetto

⇒ «Il magazzino di Verona **non** contiene 480 pallet» viene dato per coerente
col fatto che ne contiene 480. **Un fatto e la sua negazione ricevono lo stesso
verdetto positivo**, ed è il modo in cui un gate di verifica smette di essere un
gate: non manca il servizio, viene servito il contrario.

═══ AMPIEZZA, prima che qualcuno la gonfi ═══

**Tre lingue su cinque provate**, e le altre due si comportano diversamente fra
loro: l'arabo funziona in tutte e tre le colonne, il thai fallisce **prima**, sul
riconoscimento del soggetto, e resta `unknown` — un difetto diverso, che questo
file non copre. La colonna del valore numerico regge **ovunque**: è la promessa
che il README dichiara di mantenere (*«value/numeric contradictions»*) e la
mantiene anche qui.

═══ LA CAUSA, misurata alla porta interna ═══

`quantity_match._has_negator` — la superficie unica dei negatori dal 04/08 —
non riconosce quelle lingue::

    EN «does not contain»          True
    AR «لا يحتوي»                   True
    KO «없습니다»                    False  ❌
    TH «ไม่มี»                       False  ❌
    HI «नहीं हैं»                     False  ❌
    TR «yok»                        False  ❌

⚠️ E la popolazione opposta è **pulita**: sulle stesse frasi in forma
affermativa restituisce `False` in tutte, cioè oggi non ci sono falsi positivi
da proteggere. È l'unica buona notizia, ed è anche il vincolo della cura.

═══ ⚠️ PERCHÉ NON CURO, e perché il modo di curare conta più della cura ═══

Aggiungere parole per lingua è la cura ovvia ed è **la classe che in questa casa
è caduta sei volte in una notte** (`valore_non_nella_fonte` la dichiara fra i
propri limiti per lo stesso motivo). Il pericolo è preciso: un negatore scritto
male scatta su frasi affermative, e allora il gate comincia a **bocciare fatti
veri** — un danno peggiore di quello che si stava curando, e più difficile da
notare, perché un rifiuto sembra sempre prudenza.

⇒ Servono, per ogni lingua aggiunta, i casi affermativi che **non** devono
scattare — a maggior ragione dove il negatore è un morfema breve dentro altre
parole. Quella lista non si scrive a memoria: si prende dalla lingua.

Questo file registra il difetto e **blinda le due colonne che oggi funzionano**,
perché una cura mal fatta le romperebbe per prima.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from verimem.quantity_match import _has_negator
from verimem.validate_claim import validate_claim


@dataclass
class _Fact:
    id: str
    proposition: str
    topic: str = "t"
    confidence: float = 0.9
    source_episodes: list = field(default_factory=list)


class _Agent:
    """Store minimo — stesso del presidio gemello: isola il verdetto dal recupero."""

    def __init__(self, facts: list[_Fact]) -> None:
        self.semantic = type(
            "_S", (), {"search_facts": lambda _s, _q, **_k: facts})()


def _verdetto(in_memoria: str, claim: str) -> str:
    return validate_claim(_Agent([_Fact("f1", in_memoria)]), claim)["verdict"]


#: (lingua, affermativo, valore diverso, negato)
LINGUE = [
    ("EN", "The Verona warehouse contains 480 pallets.",
           "The Verona warehouse contains 380 pallets.",
           "The Verona warehouse does not contain 480 pallets."),
    ("KO", "베로나 창고에는 480개의 팔레트가 있습니다.",
           "베로나 창고에는 380개의 팔레트가 있습니다.",
           "베로나 창고에는 480개의 팔레트가 없습니다."),
    ("HI", "वेरोना गोदाम में 480 पैलेट हैं।",
           "वेरोना गोदाम में 380 पैलेट हैं।",
           "वेरोना गोदाम में 480 पैलेट नहीं हैं।"),
    ("TR", "Verona deposunda 480 palet var.",
           "Verona deposunda 380 palet var.",
           "Verona deposunda 480 palet yok."),
    ("AR", "يحتوي مستودع فيرونا على 480 منصة نقالة.",
           "يحتوي مستودع فيرونا على 380 منصة نقالة.",
           "لا يحتوي مستودع فيرونا على 480 منصة نقالة."),
]
_IDS = [c[0] for c in LINGUE]


@pytest.mark.parametrize("lingua,affermativo,diverso,negato", LINGUE, ids=_IDS)
def test_LA_CONTRADDIZIONE_DI_VALORE_REGGE_OVUNQUE(lingua, affermativo, diverso,
                                                   negato):
    """⚠️ PRIMA DI TUTTO: la colonna che oggi funziona in tutte e cinque.

    È la promessa che il README dichiara esplicitamente di mantenere — le
    contraddizioni di valore — e una cura sui negatori non deve toccarla. Se
    questo diventa rosso, si è rotto ciò che il prodotto promette per curare
    ciò che non promette.
    """
    assert _verdetto(affermativo, diverso) == "contradicted", (
        f"[{lingua}] un numero diverso dal fatto in memoria non è più una "
        f"contraddizione: era la colonna sana")


@pytest.mark.parametrize("lingua,affermativo,diverso,negato", LINGUE, ids=_IDS)
def test_IL_NEGATORE_NON_SCATTA_SULLE_AFFERMATIVE(lingua, affermativo, diverso,
                                                  negato):
    """⚠️⚠️ IL PRESIDIO CHE DECIDE SE LA CURA VALE.

    Oggi `_has_negator` è pulito su tutte le frasi affermative: zero falsi
    positivi. Chi aggiungerà i negatori di queste lingue passa **di qui**, e
    questo test è la ragione per cui la cura non può essere una lista buttata
    dentro: un negatore che scatta su una frase affermativa fa **bocciare un
    fatto vero**, che è peggio del difetto registrato sotto — e passa
    inosservato, perché un rifiuto somiglia sempre alla prudenza.
    """
    assert not _has_negator(affermativo), (
        f"[{lingua}] «{affermativo}» è affermativa e il rilevatore di negazione "
        f"scatta: una cura ha introdotto un negatore troppo largo, e adesso il "
        f"gate boccia fatti veri")


@pytest.mark.parametrize("lingua,frase,coperta", [
    ("EN", "The Verona warehouse does not contain 480 pallets.", True),
    ("AR", "لا يحتوي مستودع فيرونا على 480 منصة نقالة.", True),
    pytest.param("KO", "베로나 창고에는 480개의 팔레트가 없습니다.", True,
                 marks=pytest.mark.xfail(strict=True, reason="없습니다 non è fra i negatori")),
    pytest.param("HI", "वेरोना गोदाम में 480 पैलेट नहीं हैं।", True,
                 marks=pytest.mark.xfail(strict=True, reason="नहीं non è fra i negatori")),
    pytest.param("TR", "Verona deposunda 480 palet yok.", True,
                 marks=pytest.mark.xfail(strict=True, reason="yok non è fra i negatori")),
    pytest.param("TH", "คลังสินค้าเวโรนาไม่มี 480 พาเลท", True,
                 marks=pytest.mark.xfail(strict=True, reason="ไม่มี non è fra i negatori")),
], ids=["EN", "AR", "KO", "HI", "TR", "TH"])
def test_una_frase_negata_e_riconosciuta_come_negata(lingua, frase, coperta):
    """La causa, alla porta interna: la lista dei negatori."""
    assert _has_negator(frase) is coperta, (
        f"[{lingua}] «{frase}» contiene una negazione e `_has_negator` non la "
        f"vede: il confronto a valle tratterà la frase come se affermasse")


@pytest.mark.parametrize("lingua,affermativo,negato", [
    ("EN", LINGUE[0][1], LINGUE[0][3]),
    ("AR", LINGUE[4][1], LINGUE[4][3]),
    pytest.param("KO", LINGUE[1][1], LINGUE[1][3],
                 marks=pytest.mark.xfail(strict=True, reason="il gate risponde supported alla negazione")),
    pytest.param("HI", LINGUE[2][1], LINGUE[2][3],
                 marks=pytest.mark.xfail(strict=True, reason="il gate risponde supported alla negazione")),
    pytest.param("TR", LINGUE[3][1], LINGUE[3][3],
                 marks=pytest.mark.xfail(strict=True, reason="il gate risponde supported alla negazione")),
], ids=["EN", "AR", "KO", "HI", "TR"])
def test_il_gate_non_conferma_una_frase_negata(lingua, affermativo, negato):
    """Il cuore, alla porta pubblica: un fatto e la sua negazione non possono
    ricevere lo stesso verdetto positivo."""
    v = _verdetto(affermativo, negato)
    assert v != "supported", (
        f"[{lingua}] in memoria c'è «{affermativo}» e il claim «{negato}» la "
        f"nega, ma il verdetto è «{v}»: il gate conferma il contrario di ciò "
        f"che sa")
