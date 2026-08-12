"""«Der Dienst ist NICHT verfügbar» riceveva `supported`. Per una ü.

⚠️ È IL DANNO PEGGIORE CHE UN GATE ANTI-CONFABULAZIONE POSSA FARE, ed è
peggio di tacere. Con «Der Dienst ist verfügbar.» in memoria, il claim che
dice l'ESATTO CONTRARIO non tornava `unknown` — tornava::

    verdict: "supported"      advice: "Claim coerente con la memoria."

Il gate non si asteneva: **affermava**, e affermava il falso. Un agente che
chiede «posso dire che il servizio non è disponibile?» riceveva un sì.

═══ LA CAUSA È UNA NORMALIZZAZIONE SU UN SOLO LATO DEL CONFRONTO ═══

Misurato, e tutto il resto funzionava::

    content_tokens("Der Dienst ist verfügbar.")  ->  {'dienst', 'verfugbar'}
    scope di «nicht»                             ->  {'verfügbar'}     ⇐ con la ü
    'verfügbar' in token(affermativa)            ->  False
    Jaccard fra le due frasi senza negatori      ->  2/2 = 1.00        ⇐ passava!

Il negatore tedesco era riconosciuto (`nicht`, `kein` sono in `_NEGATOR_RE`),
lo scope era giusto, il soggetto era lo stesso. `content_tokens` toglie i
diacritici — è una scelta scritta e motivata in `norm_unit`, «chi scrive città
e chi scrive citta misura la stessa grandezza» — e lo scope della negazione no.
**Due lati dello stesso confronto normalizzavano in modo diverso**, e il
conflitto cadeva su una lettera.

🔑 Gemello del difetto curato il 2026-08-12 sul russo, dove «il negatore era
multilingue e il suo OGGETTO no»: stessa funzione, stessa metà dimenticata.
Quella volta mancava l'alfabeto, questa la normalizzazione.

═══ 📌 PERCHÉ NESSUN BANCO L'AVEVA PRESO ═══

Italiano, spagnolo e polacco cadono nello stesso buco **e ne escono per caso**:
lo scope raccoglie DUE parole dopo il negatore, e ne basta una senza diacritici
perché il conflitto si produca lo stesso — «activo», «riuscita», «jest». Il
difetto si vede solo quando è la parola NEGATA a portare il segno.

I banchi delle sette lingue (mio) e dei caratteri difficili (di un'altra
istanza) scrivevano entrambi «disponible / available»: parole senza accenti,
scelte a mente invece che da un banco di casi duri. ⇒ Due misuratori, lo stesso
punto cieco, zero informazione.

⚠️ E il tedesco è la lingua che riceveva il verdetto PEGGIORE, non a caso: i
sostantivi maiuscoli danno un alto `_subj_overlap`, quindi il fatto entrava fra
i `supporting`; non trovando conflitti, il gate concludeva «coerente». In
francese e portoghese lo stesso difetto usciva come `unknown` — sbagliato ma
onesto. **Più il soggetto è riconoscibile, più il falso «sì» è sicuro di sé.**
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from verimem.quantity_match import lexical_conflict
from verimem.validate_claim import validate_claim


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
    return validate_claim(_Agent([_Fact("f1", in_memoria)]), claim)["verdict"]


#: (lingua, affermativa, negativa) — la parola NEGATA porta un diacritico.
CON_DIACRITICO = [
    ("DE", "Der Dienst ist verfügbar.", "Der Dienst ist nicht verfügbar."),
    ("FR", "La sauvegarde est terminée.", "La sauvegarde n'est pas terminée."),
    ("PT", "O serviço está disponível.", "O serviço não está disponível."),
    ("ES", "El servicio está activo.", "El servicio no está activo."),
    ("IT", "La verifica è riuscita.", "La verifica non è riuscita."),
    ("PL", "Usługa jest dostępna.", "Usługa nie jest dostępna."),
]


@pytest.mark.parametrize("lingua,affermativa,negativa", CON_DIACRITICO,
                         ids=[c[0] for c in CON_DIACRITICO])
def test_ALLA_PORTA_la_frase_negata_non_e_mai_supported(
        lingua, affermativa, negativa):
    """⚠️⚠️ L'ASSERZIONE CHE CONTA, e va misurata ALLA PORTA.

    Non «il conflitto viene visto» ma «il gate non dice di sì»: sono due cose
    diverse, e la seconda è quella che protegge chi usa il prodotto. Se un
    giorno il rilevatore lessicale cadesse, questo test deve restare rosso
    finché il verdetto non è almeno onesto.
    """
    assert _verdetto(affermativa, negativa) != "supported", (
        f"[{lingua}] il gate dichiara coerente una frase che dice il contrario")


@pytest.mark.parametrize("lingua,affermativa,negativa", CON_DIACRITICO,
                         ids=[c[0] for c in CON_DIACRITICO])
def test_e_il_conflitto_viene_visto(lingua, affermativa, negativa):
    """Il verso positivo: non basta che il gate taccia, deve accorgersene."""
    assert _verdetto(affermativa, negativa) == "contradicted", (
        f"[{lingua}] la contraddizione non è vista")


@pytest.mark.parametrize("lingua,a,b", [
    ("DE", "Der Dienst ist verfügbar.", "Das Lager enthält 480 Paletten."),
    ("FR", "La sauvegarde est terminée.", "Le cache expire après 30 minutes."),
    ("DE uguali", "Der Dienst ist verfügbar.", "Der Dienst ist verfügbar."),
    ("IT", "Il magazzino ha 480 pallet.", "Il servizio non e' disponibile."),
])
def test_LA_POPOLAZIONE_OPPOSTA_nessun_conflitto_inventato(lingua, a, b):
    """⚠️ Togliere i diacritici rende confrontabili più parole: il rischio
    speculare è che diventino confrontabili anche frasi che non c'entrano.
    Il terzo caso è la coppia identica — una frase non contraddice se stessa."""
    assert lexical_conflict(a, b) is None, f"[{lingua}] conflitto inventato"
