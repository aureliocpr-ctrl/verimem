"""«Il moat di Verimem è stato progettato da Google» → supported, conf 0.95.

IL CASO REALE, misurato sul corpus vivo il 2026-08-01 e non costruito a
tavolino: sette fatti citati come evidenza, che parlano di Google Ads, Google
Analytics e Search Console per verimem.com. Nessuno dice chi ha progettato il
moat. L'advice diceva «Claim coerente con la memoria.»

Su venti claim, dieci vere e dieci inventate coi nomi veri del corpus::

                      supported   unknown
    dieci VERE            2          8
    dieci INVENTATE       8          1      (+1 contradicted)

Il verdetto correlava col NUMERO DI NOMI PROPRI, non col contenuto: una
confabulazione che nomina due entita' note supera il gate di genericita' e
trova sempre fatti che le nominano entrambe, mentre un'affermazione vera sul
funzionamento del prodotto — un nome solo e parole comuni — viene scartata come
troppo generica. Una causa sola per entrambe le colonne.

QUESTO FILE ERA GIA' PREVISTO. `test_un_nome_non_si_trova_dentro_un_altra_parola`
chiudeva col criterio per riaprire: «se emerge un caso reale in cui `supported`
arriva con overlap di nomi legittimo ma senza asserzione, quello e' il
momento». Qui l'overlap e' legittimo — «Verimem» e «Google» ci sono davvero,
non per sottostringa — e l'asserzione manca.

E NON E' SEMANTICA NUOVA: il modulo applica la stessa disciplina in due casi su
tre (quantita' non confermate, claim generica), col commento che dichiara il
principio — name-overlap da solo non promuove, sarebbe «false reassurance».
Mancava il terzo.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from verimem.validate_claim import _parole_di_contenuto, _qualcuno_asserisce, validate_claim


@dataclass
class _F:
    id: str
    proposition: str
    topic: str = "t"
    confidence: float = 0.9
    source_episodes: list[str] = field(default_factory=list)


class _Sem:
    def __init__(self, facts):
        self._facts = facts

    def search_facts(self, query, *, limit=20, topic=None):
        return list(self._facts)


class _Agent:
    def __init__(self, facts):
        self.semantic = _Sem(facts)


#: I sette veri, accorciati alla parte che il gate leggeva.
_EVIDENZE_REALI = [
    _F("82f374792fdf", "2026-07-08 VERIFICATO EMPIRICO (WebSearch): "
       "verimem.com NON indicizzato sui motori. Cercando 'verimem' il sito "
       "non esce; escono altri VeriMem."),
    _F("e30ce9c80c60", "2026-07-06: Campagna Google Ads Verimem CREATA in "
       "bozza (account 556-933-6646), budget 5 euro/giorno."),
    _F("c7e2a4dabca4", "2026-07-06: Google Analytics 4 LIVE su verimem.com "
       "e capriello.com, stessa property GA4 di omnex."),
    _F("c148acacedc5", "Fatto 2026-07-05: siti live capriello.com e "
       "verimem.com. Google Search Console proprieta' verificata."),
]


def test_il_caso_reale_non_e_piu_supported():
    """Il cuore: gli stessi nomi, un'asserzione che nessuno fa."""
    agent = _Agent(_EVIDENZE_REALI)
    r = validate_claim(agent, "Il moat di Verimem è stato progettato da Google.")
    assert r["verdict"] == "unknown", (
        f"verdetto {r['verdict']!r} (conf {r['confidence']}): i fatti citati "
        "parlano di campagne pubblicitarie e analytics, e nessuno dice chi "
        "abbia progettato il moat")
    assert "nessuno asserisce" in r["advice"], r["advice"]
    assert r["evidence_facts"], (
        "i fatti che hanno portato qui vanno restituiti lo stesso: il "
        "soggetto E' noto, e all'utente serve sapere cosa la memoria ha su "
        "di lui")


def test_una_claim_che_la_memoria_sostiene_DAVVERO_resta_supported():
    """La controprova, senza la quale la cura sarebbe solo mutismo."""
    agent = _Agent(_EVIDENZE_REALI)
    r = validate_claim(
        agent, "Una campagna Google Ads per Verimem è stata creata in bozza.")
    assert r["verdict"] == "supported", (
        f"verdetto {r['verdict']!r}: il fatto e30ce9c80c60 lo dice con queste "
        "parole, e declassarlo renderebbe il gate muto invece che prudente")


def test_i_nomi_non_contano_come_asserzione():
    """L'unita' sotto il verdetto: cosa conta come «dire qualcosa».

    I nomi dicono DI COSA si parla. Se contassero anche come asserzione, il
    controllo sarebbe una tautologia — sono gli stessi nomi che hanno portato
    il fatto fra i candidati.
    """
    parole = _parole_di_contenuto("Il moat di Verimem è stato progettato da Google.")
    assert "verimem" not in parole and "google" not in parole, parole
    assert {"moat", "progettato"} <= parole, parole


def test_un_dominio_e_un_nome_non_un_predicato():
    """La falla che il banco ha rivelato PRIMA che la cura fosse scritta.

    Senza questa riga «verimem.com» entra fra le parole che portano
    l'asserzione coi suoi due pezzi, e «verimem» e «com» si trovano in mezzo
    corpus: qualunque cosa si affermi su un sito risulterebbe asserita da
    qualcuno. Era l'unico motivo per cui una claim del banco sopravviveva —
    cioe' il controllo funzionava, su quel caso, per la ragione sbagliata.
    """
    parole = _parole_di_contenuto("verimem.com è ospitato da Oracle Cloud.")
    assert "com" not in parole and "verimem" not in parole, parole
    assert "ospitato" in parole, parole


def test_senza_predicato_da_cercare_non_si_nega_nulla():
    """Il caso limite: una claim di soli nomi non ha un'asserzione da
    verificare, e questo controllo non deve inventarne una. Chi decide li' e'
    il gate di genericita', che esiste gia'."""
    assert _qualcuno_asserisce("Verimem Google", _EVIDENZE_REALI) is True


def test_IL_COSTO_dichiarato_una_verita_detta_con_altre_parole():
    """Il perimetro, scritto perche' e' un costo vero e non un dettaglio.

    Il controllo e' lessicale: una claim VERA scritta con parole diverse da
    quelle del fatto scende a `unknown`. Qui «il monitoraggio è attivo» contro
    un fatto che dice «Analytics 4 LIVE» — stessa cosa, nessuna parola in
    comune.

    Sta scritto in un test invece che in un commento perche' il giorno in cui
    qualcuno lo migliora questo test FALLISCE, ed e' il momento giusto per
    riscriverlo. E' la direzione che il prodotto promette: dire «non lo so» di
    una cosa vera costa all'utente un controllo, dire «coerente con la
    memoria» di una falsa gli costa la fiducia in tutto il resto.

    DUE NOMI e non uno, e l'advice controllato: la prima stesura usava una
    claim con «Google» soltanto, che resta `unknown` anche a controllo spento
    — la manda li' il gate di genericita'. Passava dichiarando di misurare una
    cosa che non misurava.
    """
    agent = _Agent(_EVIDENZE_REALI)
    r = validate_claim(
        agent, "Su verimem.com Google Analytics fa un monitoraggio attivo.")
    assert r["verdict"] == "unknown", (
        "questa claim VERA ora passa: se e' per una finezza in piu' nel "
        "controllo, ottimo — aggiorna questo test e dichiara il nuovo "
        "perimetro")
    assert "nessuno asserisce" in r["advice"], (
        f"unknown, ma non per il controllo di asserzione: {r['advice']!r} — "
        "questo test misurerebbe il gate sbagliato")
