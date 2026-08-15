"""«any language» è una promessa, e questo banco le mette un numero.

Il README dichiara che il gate *«works with no llm and in **any language**»*, e
due righe sotto precisa l'onestà della misura: *«multilingual — measured
EN/IT/FR/ES»*. Le lingue che in casa hanno un banco sono **quindici**.

Quindici non è «any». Il 15/08 sei lingue che nessun banco toccava sono state
passate alla stessa matrice a tre colonne usata per le altre — stesso fatto in
memoria, stessa porta pubblica (`validate_claim`)::

    lingua           identico      valore diverso   NEGATO
    VI vietnamita    supported     contradicted     supported   ❌
    ID indonesiano   supported     contradicted     supported   ❌
    HE ebraico       supported     contradicted     supported   ❌
    EL greco         unknown  ❌    contradicted     unknown     ❌
    SW swahili       unknown  ❌    unknown     ❌    unknown     ❌
    UK ucraino       supported     contradicted     contradicted ✅

    ⇒ tre colonne su tre: 1 / 6

═══ ⚖️ COSA REGGE, ed è la parte che questo file protegge per prima ═══

**La colonna delle contraddizioni di valore funziona in cinque lingue su sei**,
comprese quattro che nessuno aveva mai provato. È **esattamente** la promessa
che il README dichiara di mantenere — *«it reliably catches value/numeric
contradictions»* — e la mantiene **fuori dalle quattro lingue in cui è stata
misurata**. Il prodotto è più solido di quanto la sua frase più larga faccia
sembrare, e più stretto di quella frase.

═══ 🔑 PERCHÉ I DIFETTI SONO REGISTRATI E NON CURATI ═══

Tre dei cinque sono lo stesso difetto curato lo stesso giorno per coreano,
hindi, turco e thai: il gate **conferma la frase negata**, perché `không`,
`tidak`, `אינו` non sono nella lista dei negatori.

⚠️ Ma aggiungerli è la cura che non scala, e il costo è misurato: per le quattro
lingue curate al mattino sono stati provati **dieci candidati** su frasi
affermative e **cinque scartati**, perché scattavano su «ciao», «chiodo»,
«barca», «voto», «cambiare». ⇒ Per ogni lingua serve qualcuno che distingua un
negatore da una parola che gli somiglia. **Con quindici coperte, una lista di
parole non arriverà mai a «any».**

⇒ Le decisioni possibili sono due, e non appartengono a un banco: cambiare il
**criterio** — la negazione riconosciuta semanticamente dall'embedder
multilingue, strada che il prodotto già usa per un altro controllo — oppure
cambiare la **frase**, dicendo quante lingue sono misurate. Questo file non
sceglie: **mette il numero sotto la promessa**, così la scelta si fa sui dati.

📌 L'ucraino passa **per una coincidenza**: il negatore russo `не` copre anche
la sua negazione. Nessuno l'aveva previsto, e una cosa che funziona per caso non
è coperta — per questo sta fra i casi verificati con una nota, non fra i meriti.

⚠️ LIMITE DI QUESTO BANCO: le frasi sono state scritte da chi l'ha compilato,
non prese da un corpus. Il pattern è identico per tutte — stesso fatto, stesso
numero, stessa negazione — quindi il confronto **fra** lingue regge; se una
frase risultasse innaturale a chi conosce quella lingua, quella riga va rifatta.
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
    def __init__(self, facts: list[_Fact]) -> None:
        self.semantic = type(
            "_S", (), {"search_facts": lambda _s, _q, **_k: facts})()


def _verdetto(in_memoria: str, claim: str) -> str:
    return validate_claim(_Agent([_Fact("f1", in_memoria)]), claim)["verdict"]


#: (lingua, affermativo, valore diverso, negato)
NUOVE = [
    ("VI", "Kho Verona chứa 480 pallet.",
           "Kho Verona chứa 380 pallet.",
           "Kho Verona không chứa 480 pallet."),
    ("ID", "Gudang Verona berisi 480 palet.",
           "Gudang Verona berisi 380 palet.",
           "Gudang Verona tidak berisi 480 palet."),
    ("HE", "מחסן ורונה מכיל 480 משטחים.",
           "מחסן ורונה מכיל 380 משטחים.",
           "מחסן ורונה אינו מכיל 480 משטחים."),
    ("EL", "Η αποθήκη της Βερόνα περιέχει 480 παλέτες.",
           "Η αποθήκη της Βερόνα περιέχει 380 παλέτες.",
           "Η αποθήκη της Βερόνα δεν περιέχει 480 παλέτες."),
    ("UK", "Склад у Вероні містить 480 палет.",
           "Склад у Вероні містить 380 палет.",
           "Склад у Вероні не містить 480 палет."),
    ("SW", "Ghala la Verona lina paleti 480.",
           "Ghala la Verona lina paleti 380.",
           "Ghala la Verona halina paleti 480."),
]
_IDS = [c[0] for c in NUOVE]


@pytest.mark.parametrize("lingua,affermativo,diverso,negato",
                         [c for c in NUOVE if c[0] != "SW"],
                         ids=[c[0] for c in NUOVE if c[0] != "SW"])
def test_LA_CONTRADDIZIONE_DI_VALORE_REGGE_FUORI_DALLE_LINGUE_MISURATE(
        lingua, affermativo, diverso, negato):
    """⚖️ LA PROMESSA CHE IL README DICHIARA, e che il prodotto mantiene.

    *«It reliably catches value/numeric contradictions»* — misurato su EN, IT,
    FR ed ES, e qui verificato su cinque lingue che nessuno aveva provato, in
    quattro alfabeti diversi. **Questo è il test che non deve mai diventare
    rosso**: se cade, è caduta la promessa centrale, non un'estensione.
    """
    assert _verdetto(affermativo, diverso) == "contradicted", (
        f"[{lingua}] un numero diverso dal fatto in memoria non è più una "
        f"contraddizione: è caduta la promessa che il README dichiara di "
        f"mantenere")


@pytest.mark.xfail(strict=True, reason=(
    "lo swahili non riceve alcun verdetto su nessuna delle tre colonne: "
    "fallisce prima, sul riconoscimento del soggetto"))
def test_anche_lo_swahili_vede_la_contraddizione_di_valore():
    """Il sesto caso, l'unico che perde anche la colonna sana."""
    a, b = NUOVE[5][1], NUOVE[5][2]
    assert _verdetto(a, b) == "contradicted"


@pytest.mark.parametrize("lingua,affermativo,negato", [
    ("UK", NUOVE[4][1], NUOVE[4][3]),
    pytest.param("VI", NUOVE[0][1], NUOVE[0][3], marks=pytest.mark.xfail(
        strict=True, reason="«không» non è fra i negatori: il gate conferma la negazione")),
    pytest.param("ID", NUOVE[1][1], NUOVE[1][3], marks=pytest.mark.xfail(
        strict=True, reason="«tidak» non è fra i negatori: il gate conferma la negazione")),
    pytest.param("HE", NUOVE[2][1], NUOVE[2][3], marks=pytest.mark.xfail(
        strict=True, reason="«אינו» non è fra i negatori: il gate conferma la negazione")),
    ("EL", NUOVE[3][1], NUOVE[3][3]),
    ("SW", NUOVE[5][1], NUOVE[5][3]),
], ids=["UK", "VI", "ID", "HE", "EL", "SW"])
def test_il_gate_non_conferma_una_frase_negata(lingua, affermativo, negato):
    """Il difetto, registrato lingua per lingua invece che riassunto.

    📌 L'ucraino non è marcato perché **funziona**, e va detto perché funziona:
    il negatore russo `не` copre anche la sua negazione. È una coincidenza fra
    lingue imparentate, non una copertura decisa — se un domani quel negatore
    cambiasse forma, l'ucraino cadrebbe senza che nessuno lo abbia toccato.

    ⚠️ **GRECO E SWAHILI NON SONO MARCATI, E NON PERCHÉ FUNZIONINO.** La prima
    stesura di questo file li dava per attesi-in-fallimento, e la suite ha
    risposto con due XPASS: il loro verdetto è `unknown`, che **non è**
    `supported`, quindi soddisfano questo test alla lettera. Il loro difetto è
    un altro — non ricevono alcun verdetto — ed è registrato dove sta davvero,
    nel test sotto.
    🔑 Un banco che chiede «non confermare» non misura «rispondere»: marcare
    qui il loro fallimento avrebbe attribuito al gate un difetto nel posto
    sbagliato, e il posto sbagliato è dove le cure non arrivano.
    """
    v = _verdetto(affermativo, negato)
    assert v != "supported", (
        f"[{lingua}] in memoria c'è «{affermativo}» e il claim la nega, ma il "
        f"verdetto è «{v}»: il gate conferma il contrario di ciò che sa")


@pytest.mark.parametrize("lingua,affermativo", [
    ("VI", NUOVE[0][1]), ("ID", NUOVE[1][1]), ("HE", NUOVE[2][1]),
    ("UK", NUOVE[4][1]),
    pytest.param("EL", NUOVE[3][1], marks=pytest.mark.xfail(
        strict=True, reason="il greco non riceve verdetto sul claim identico")),
    pytest.param("SW", NUOVE[5][1], marks=pytest.mark.xfail(
        strict=True, reason="lo swahili non riceve verdetto sul claim identico")),
], ids=["VI", "ID", "HE", "UK", "EL", "SW"])
def test_il_claim_identico_al_fatto_riceve_un_verdetto(lingua, affermativo):
    """IL DIFETTO DI GRECO E SWAHILI, nel posto dove sta davvero.

    Il caso più facile che esista — il claim **identico** al fatto in memoria —
    deve dare `supported`. Greco e swahili danno `unknown`: non sbagliano, si
    astengono, e l'utente riceve «non so» su un fatto che la memoria contiene
    parola per parola.

    🔑 È lo stesso difetto che il thai aveva stamattina e che una cura scritta
    per il coreano ha risolto senza cercarlo. Greco e swahili però gli spazi
    ce li hanno: **la segmentazione non li riguarda**, quindi è un terzo caso
    ancora, e la sua causa non è misurata.
    """
    assert _verdetto(affermativo, affermativo) == "supported", (
        f"[{lingua}] il claim è identico al fatto in memoria e il gate non "
        f"riesce a confermarlo")


def test_IL_CONTO_DELLA_COPERTURA_e_quello_dichiarato():
    """⚠️ Il numero che questo file esiste per tenere fermo.

    Se un domani le lingue che passano tutte e tre le colonne diventassero più
    di una, **questo test diventa rosso** e chiede di aggiornare il numero nel
    docstring — e di rileggere la frase «any language» alla luce del nuovo
    conto. È il modo in cui una misura non invecchia in silenzio.
    """
    complete = [ling for ling, a, b, n in NUOVE
                if _verdetto(a, a) == "supported"
                and _verdetto(a, b) == "contradicted"
                and _verdetto(a, n) == "contradicted"]
    assert complete == ["UK"], (
        f"le lingue con tre colonne su tre erano ['UK'], ora sono {complete}: "
        f"aggiorna il conto nel docstring e rileggi «any language» col numero "
        f"nuovo")
