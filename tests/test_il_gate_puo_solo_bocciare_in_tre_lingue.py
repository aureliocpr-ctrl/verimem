"""Il gate conferma in quattro lingue su sette e boccia in tutte e sette.

⚠️ QUESTO È IL DIFETTO PEGGIORE CHE UN GATE DI VERIFICA POSSA AVERE, e non
perché sbagli: perché TACE. Misurato alla porta pubblica (`validate_claim`, non
una funzione interna) con il claim **identico** al fatto in memoria — il caso
più facile che esista, quello che deve dare «supportato» sempre::

    EN  supported      IT  supported      FR  supported      ES  supported
    RU  unknown  ❌     ZH  unknown  ❌     JA  unknown  ❌

E l'altra popolazione, misurata insieme, funziona in tutte e sette: la stessa
frase negata dà `contradicted` anche in russo, cinese e giapponese.

⇒ **ASIMMETRIA: dove il gate non sa confermare, sa ancora bocciare.** In tre
lingue del perimetro dichiarato un fatto vero, con la sua source, non viene mai
promosso — e l'utente non riceve un errore, riceve «non so». Il servizio manca
in silenzio, che è il modo in cui un limite sopravvive per mesi.

═══ LA CAUSA È UNA RIGA, ED È IN `validate_claim` ═══

Il ciclo che popola `supporting` (`validate_claim.py:578`) aggancia i fatti con
`_subj_overlap(claim_caps, f.proposition)` e scarta tutto ciò che sta sotto la
soglia. `_subj_overlap` però restituisce **0.0 quando `claim_caps` è vuoto**, e
`claim_caps` viene da `_CAPS_RE = \\b([A-Z][a-zA-Z]{2,})\\b`, cioè dalle
maiuscole **latine ASCII**. Misura del massimo possibile — la frase confrontata
con SE STESSA::

    EN/IT/FR/ES   _subj_overlap = 1.00
    RU            _subj_overlap = 0.00      (Склад, Вероне: maiuscole non ASCII)
    ZH / JA       _subj_overlap = 0.00      (non esistono maiuscole)

Il russo dimostra che **non è la segmentazione**: ha gli spazi, ha le
maiuscole, e cade lo stesso. `content_tokens` sulle stesse sette frasi dà
4/4/4/4/4/8/18 token. ⇒ Il segnale c'è, non è collegato al verdetto.

═══ 🔑 IL PRINCIPIO DELLA CURA È GIÀ SCRITTO DUE VOLTE NELLO STESSO FILE ═══

Non è un'idea nuova, ed è la ragione per cui questa cura è a basso rischio:
`validate_claim.py:601` lo enuncia per il passo numerico — *«quando l'aggancio
sui caps non può funzionare, ci si aggancia al CONTESTO CONDIVISO e si cerca il
conflitto sul valore»* — e `anti_confab_gate.py:524` lo applica al write path
con `leggibile_a_maiuscole`: *«SE IL CRITERIO NON SA LEGGERE LA FRASE, NON
DECIDE»*. Perfino `leggibile_a_maiuscole` **è definita in `validate_claim.py`**
e usata solo dall'altro modulo.

⇒ Il presidio esiste, sta in questo file, e questo file non lo chiama. La
conferma è rimasta appesa alle maiuscole mentre tutto il resto se ne staccava.

═══ ⚠️ PERCHÉ NON BASTA «ALLARGARE» — la popolazione opposta ═══

`supported` è il verdetto che dà FALSA RASSICURAZIONE, e il file lo circonda di
tre presidi messi lì dopo casi veri (`suppress_support`, `lexical_only`,
`non_asserita` — quest'ultimo nato perché *«sul corpus vivo erano otto
confabulazioni su dieci a ricevere supported»*). Una cura che promuove in tre
lingue nuove deve lasciare in piedi tutti e tre, e i test qui sotto misurano
**entrambe** le popolazioni nella stessa esecuzione: quattro casi che devono
diventare `supported` e cinque che devono restare `unknown`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from verimem.validate_claim import validate_claim


@dataclass
class _Fact:
    id: str
    proposition: str
    topic: str = "t"
    confidence: float = 0.9
    source_episodes: list = field(default_factory=list)


class _Agent:
    """Store minimo: restituisce i fatti dati, senza filtrare per query.

    Il retrieval NON è l'oggetto di questo file — il difetto sta nel verdetto,
    a valle. Passare i fatti direttamente isola la variabile.
    """

    def __init__(self, facts: list[_Fact]) -> None:
        self.semantic = type(
            "_S", (), {"search_facts": lambda _s, _q, **_k: facts})()


def _verdetto(in_memoria: str, claim: str) -> str:
    return validate_claim(_Agent([_Fact("f1", in_memoria)]), claim)["verdict"]


#: (lingua, frase). Lo stesso fatto nelle sette lingue del perimetro.
IDENTICHE = [
    ("EN", "The Verona warehouse contains 480 pallets."),
    ("IT", "Il magazzino di Verona contiene 480 pallet."),
    ("FR", "L'entrepot de Verone contient 480 palettes."),
    ("ES", "El almacen de Verona contiene 480 palets."),
    ("RU", "Склад в Вероне содержит 480 паллет."),
    ("ZH", "维罗纳仓库有480个托盘。"),
    ("JA", "ヴェローナの倉庫には480パレットあります。"),
]


@pytest.mark.parametrize("lingua,frase", IDENTICHE, ids=[c[0] for c in IDENTICHE])
def test_il_claim_IDENTICO_al_fatto_in_memoria_e_supportato(lingua, frase):
    """Il cuore, e il caso più facile che esista: il claim È il fatto.

    Le quattro lingue latine sono qui insieme alle tre scoperte perché una cura
    che aggancia i fatti in un modo nuovo può cambiare il verdetto dove oggi è
    giusto — ed è successo abbastanza volte in questa casa da presidiarlo
    invece di sperarci.
    """
    assert _verdetto(frase, frase) == "supported", (
        f"[{lingua}] il gate non conferma un claim identico al fatto in memoria")


@pytest.mark.parametrize("lingua,memoria,claim", [
    ("RU", "Сервис доступен.", "Сервис не доступен."),
    ("ZH", "服务可用。", "服务不可用。"),
    ("JA", "サービスは利用できます。", "サービスは利用できません。"),
])
def test_l_altra_popolazione_bocciare_continua_a_funzionare(lingua, memoria, claim):
    """⚠️ IL VERSO CHE OGGI FUNZIONA, e che la cura non deve spegnere.

    È il controllo che rende leggibile il difetto: il gate in queste tre lingue
    non è *muto*, è **asimmetrico**. Se una cura per la conferma facesse cadere
    la bocciatura, avremmo scambiato un difetto con uno peggiore.
    """
    assert _verdetto(memoria, claim) == "contradicted", (
        f"[{lingua}] la contraddizione non è più vista")


@pytest.mark.parametrize("caso,memoria,claim", [
    ("ZH soggetto diverso", "维罗纳仓库有480个托盘。", "服务器有320个连接。"),
    ("JA soggetto diverso", "ヴェローナの倉庫には480パレットあります。",
                            "キャッシュは30分後に期限切れです。"),
    ("RU soggetto diverso", "Склад в Вероне содержит 480 паллет.",
                            "Кэш истекает через 30 минут."),
    ("ZH stessa unità valore diverso non confermato",
     "维罗纳仓库有480个托盘。", "维罗纳仓库有480个托盘和12个货架。"),
])
def test_LA_POPOLAZIONE_OPPOSTA_non_diventa_supported(caso, memoria, claim):
    """⚠️⚠️ IL PRESIDIO CHE DECIDE SE LA CURA VALE.

    `supported` è l'unico verdetto che può fare danno affermando: dice
    all'agente «vai tranquillo» su una cosa che la memoria non sostiene. Un
    aggancio più largo che promuovesse anche questi casi non estenderebbe la
    copertura, la simulerebbe — e i tre presidi del file (`suppress_support`,
    `lexical_only`, `non_asserita`) esistono esattamente per questo.

    L'ultimo caso è il più insidioso: stesso soggetto, stessa quantità vera, ma
    il claim ne asserisce **una in più** che nessun fatto enuncia.
    """
    assert _verdetto(memoria, claim) != "supported", (
        f"[{caso}] falsa rassicurazione: promosso a supported")
