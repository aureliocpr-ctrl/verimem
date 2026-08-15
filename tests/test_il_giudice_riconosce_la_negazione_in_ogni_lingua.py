"""La negazione riconosciuta dal giudice, non da una lista di parole.

Fino al 15/08 il verdetto di contraddizione passava **solo** da criteri
lessicali: una lista di negatori, una lingua per volta. Quella strada copriva
quindici lingue e non poteva coprirne di più, perché ogni lingua chiede a
qualcuno di distinguere una negazione da una parola che le somiglia — per il
coreano `안` scatta su «ciao», per l'hindi `मत` dentro «voto».

⚠️ **E il pezzo che risolve il caso generale era già nel prodotto, a un import
di distanza.** Il giudice del moat è un cross-encoder di entailment: separa un
fatto dalla sua negazione senza sapere nulla di quella lingua. Misurato il
15/08 su sedici lingue, punteggio del claim identico contro quello del negato::

    EN 96.31→1.46   IT 98.94→1.26   KO 99.95→1.85   VI 98.28→1.44
    ID 98.70→2.03   HE 99.98→8.64   EL 99.96→1.44   TH 99.97→2.94
    JA 99.85→2.07   ZH 99.58→1.31   AR 99.95→3.38   HI 99.89→1.42
    RU 99.85→1.34   UK 99.83→1.75          ⇒ 14 lingue su 16
    SW 99.19→99.32  TR 99.07→99.47         ⇒ i due che NON separa

⇒ **Copre vietnamita, indonesiano, ebraico, greco e thai, che la lista non
tocca.** E il turco, che il giudice sbaglia, la lista lo copre: le due strade
sono **complementari**, ed è l'architettura che il README già descrive — uno
screening lessicale economico prima, il controllo di entailment poi.

═══ ⚠️ IL GIUDICE DA SOLO NON BASTA, ed è il motivo della seconda condizione ═══

Il giudice dà **1.26** a una negazione e **1.69** a una frase su un argomento
completamente diverso: da solo **non li distingue**, e usarlo così farebbe
dichiarare «contraddizione» fra due fatti che non parlano della stessa cosa.

La guardia che li separa esiste già nel prodotto — la sovrapposizione dei
termini di contenuto — e misurata sulle tre popolazioni dà::

                        giudice   overlap   esito
    negazione (4 lingue)  1-9       1.00     contraddizione   ✅
    argomento diverso     1.69      0.00     nessuna          ✅
    parafrasi vera       98.10      0.75     nessuna          ✅
    dettaglio in più     99.81      1.00     nessuna          ✅

⇒ **Sette casi su sette**: il giudice separa la negazione dalla parafrasi,
l'overlap separa la negazione dall'argomento diverso. Serve che **entrambe** le
condizioni valgano.

📌 Questo banco **salta** dove il modello non è su disco, che è la condizione
normale in CI: il percorso lessicale resta il comportamento senza modello, e
quello ha già i suoi banchi.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from verimem.local_grounding import local_ce_available

pytestmark = pytest.mark.skipif(
    not local_ce_available(),
    reason="il giudice del moat non è su disco: questo banco misura il "
           "percorso semantico, che senza modello non gira. Il percorso "
           "lessicale ha i propri banchi ed è il comportamento di riserva.")


@dataclass
class _Fact:
    id: str
    proposition: str
    topic: str = "t"
    confidence: float = 0.9
    source_episodes: list = field(default_factory=list)


class _Agent:
    def __init__(self, facts: list[_Fact]) -> None:
        self.semantic = type(
            "_S", (), {"search_facts": lambda _s, _q, **_k: facts})()


def _verdetto(in_memoria: str, claim: str) -> str:
    from verimem.validate_claim import validate_claim
    return validate_claim(_Agent([_Fact("f1", in_memoria)]), claim)["verdict"]


#: Lingue che la lista dei negatori NON copre — è per queste che il giudice serve.
SCOPERTE = [
    ("VI", "Kho Verona chứa 480 pallet.",
           "Kho Verona không chứa 480 pallet."),
    ("ID", "Gudang Verona berisi 480 palet.",
           "Gudang Verona tidak berisi 480 palet."),
    ("HE", "מחסן ורונה מכיל 480 משטחים.",
           "מחסן ורונה אינו מכיל 480 משטחים."),
    ("EL", "Η αποθήκη της Βερόνα περιέχει 480 παλέτες.",
           "Η αποθήκη της Βερόνα δεν περιέχει 480 παλέτες."),
]


@pytest.mark.parametrize("lingua,affermativo,negato", SCOPERTE,
                         ids=[c[0] for c in SCOPERTE])
def test_il_gate_smentisce_la_negazione_in_lingue_senza_negatore(
        lingua, affermativo, negato):
    """Il cuore: lingue in cui nessun negatore è in lista, e il gate deve
    comunque smentire."""
    v = _verdetto(affermativo, negato)
    assert v != "supported", (
        f"[{lingua}] in memoria c'è «{affermativo}» e il claim la nega, ma il "
        f"verdetto è «{v}»: il giudice separa questa coppia di 91-98 punti, "
        f"quindi l'informazione c'era e non è stata usata")


@pytest.mark.parametrize("lingua,affermativo,negato", [
    c if c[0] != "EL" else pytest.param(*c, marks=pytest.mark.xfail(
        strict=True,
        reason="il greco non riceve verdetto sul claim identico: fallisce sul "
               "riconoscimento del soggetto, che è un percorso diverso da "
               "questa cura e resta aperto"))
    for c in SCOPERTE], ids=[c[0] for c in SCOPERTE])
def test_IL_CLAIM_IDENTICO_RESTA_SUPPORTED(lingua, affermativo, negato):
    """⚠️ La direzione che la cura non deve spegnere.

    Un criterio semantico troppo severo trasformerebbe in contraddizione
    qualunque differenza di forma. Il claim identico al fatto è il caso più
    facile che esista: se cade qui, il gate ha smesso di confermare.
    """
    assert _verdetto(affermativo, affermativo) == "supported", (
        f"[{lingua}] il claim è identico al fatto in memoria e non è più "
        f"supportato: la cura semantica è troppo severa")


@pytest.mark.parametrize("in_memoria,claim,atteso", [
    ("Il magazzino di Verona contiene 480 pallet.",
     "Ci sono 480 pallet nel magazzino di Verona.", "supported"),
    ("Il magazzino di Verona contiene 480 pallet, arrivati lunedì.",
     "Il magazzino di Verona contiene 480 pallet.", "supported"),
], ids=["parafrasi", "dettaglio-in-piu"])
def test_UNA_PARAFRASI_NON_E_UNA_CONTRADDIZIONE(in_memoria, claim, atteso):
    """⚠️⚠️ IL PRESIDIO CHE DECIDE SE LA CURA VALE.

    Il giudice dà 98,10 a una parafrasi vera e 99,81 a un fatto con un
    dettaglio in più: se una di queste diventasse «contraddetta», il gate
    comincerebbe a **respingere riformulazioni corrette** — un danno che
    somiglia alla prudenza e che nessuno andrebbe a cercare.
    """
    assert _verdetto(in_memoria, claim) == atteso


def test_UN_ARGOMENTO_DIVERSO_NON_E_UNA_CONTRADDIZIONE():
    """⚠️ L'altra metà della guardia, ed è la ragione della seconda condizione.

    Il giudice dà **1.69** a una frase su tutt'altro argomento — quasi lo
    stesso punteggio della negazione (**1.26**). Da solo direbbe
    «contraddizione» fra due fatti che non parlano della stessa cosa: è la
    sovrapposizione dei termini (0.00 contro 1.00) a separarli.
    """
    v = _verdetto("Il magazzino di Verona contiene 480 pallet.",
                  "La ricetta della carbonara richiede il guanciale.")
    assert v != "contradicted", (
        "due fatti su argomenti diversi sono stati dichiarati in "
        "contraddizione: la guardia dello stesso-soggetto non ha retto")
