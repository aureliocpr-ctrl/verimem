"""Dodici osservazioni indipendenti soppresse da un fatto che parlava d'altro.

IL CASO, sul corpus di produzione. Un fatto a `grounding_score` **99.98** —
«Su 31 documenti indicizzati in verimem 29 hanno source_id assoluto e 2 lo
hanno relativo» — ne ha superseduti **dodici**, tutti dello stesso topic e
nessuno dei quali lo contraddice:

    index_document · search-docs · recall_history · forward_chain
    trust_report · Memory.ignorance · facts_search · l1_completion_detector

Fra i dodici ce n'è uno a `gs` **98.49**, cioè ben verificato quanto il
vincitore. Non erano versioni vecchie di niente: erano misure diverse.

LA CATENA, letta dal DB e non ipotizzata. Le contraddizioni registrate per quei
dodici sono **36, tutte `boolean_clash`**, con similarity 0.83–0.91 — cioè fra
fatti *diversi*. E `detect_boolean_clashes` decideva così:

    flags = [(f, _has_negation(f.proposition)) for f in group]
    if a_neg == b_neg: continue          # polarità diversa ⇒ clash

Guardava se una frase **contiene** una negazione, non se le due **negano la
stessa cosa**. Basta che un fatto dica «quando is_new è False…» e l'altro no,
sullo stesso topic e sopra la soglia di coseno, perché diventino «in conflitto».

Poi `heal_contradictions` esegue: sopprime il lato a trust minore verso quello
maggiore, senza ri-validare il clash — il suo stesso docstring lo dichiara
(«Does NOT detect new contradictions… it only acts on what the detector already
found»). Da cui la proprietà peggiore di tutte: **più un fatto è ben
verificato, più ne ingoia**, perché è sempre lui il lato a trust maggiore.

LA CURA È UNA SOLA RIGA DI GIUDIZIO, e la parte importante è che non introduce
niente: `quantity_match.negation_conflict` fa già la domanda giusta, con le
guardie che qui mancavano — le due frasi devono condividere quasi tutte le
parole di contenuto (Jaccard ≥ 0.6, ≥2 condivise) **e** la parola nello scope
del negatore dev'essere condivisa. È la stessa unificazione fatta il 2026-08-04
su `_has_negation`, un piano più sopra: là si era unificato *cos'è un
negatore*, qui *cos'è un conflitto*.

MISURATA SUI DODICI CASI VERI PRIMA DI SCRIVERLA:

    clash secondo il metodo attuale    12/12
    clash secondo il metodo con guardie 0/12
"""
from __future__ import annotations

import time

import pytest

from verimem.contradiction import detect_boolean_clashes
from verimem.semantic import Fact

#: Il vincitore vero, dal corpus.
VINCITORE = (
    "Su 31 documenti indicizzati in verimem 29 hanno source_id assoluto "
    "e 2 lo hanno relativo, e dei due relativi uno solo e' risolvibile "
    "dalla cartella HippoAgent-verify mentre da un altro cwd non ne "
    "risolve nessuno")

#: Cinque dei dodici, TESTUALI dal corpus. Nessuno contraddice il
#: vincitore: parlano d'altro, e il coseno con lui sta fra 0.8194 e
#: 0.8677 — cioe' sopra la soglia di 0.75 che li faceva accoppiare.
INDIPENDENTI = [
    "In index_document di document_index.py, quando is_new e' False la "
    "funzione ritorna chunks_indexed 0 senza interrogare la tabella "
    "chunks",
    "verimem search-docs con la query 'dogfooding sola lettura handoff' "
    r"restituisce 5 hit tutti dal source docs\ROADMAP-v0.7.md",
    "Nella risposta di hippo_recall_history l'esca per ad518e85b39a "
    "riporta due blocchi DISPUTED unresolved con lo stesso record in "
    "conflitto",
    "La risposta JSON di hippo_recall_history contiene le sole chiavi "
    "context e n",
    "Il primo hit di hippo_recall_history per la query sull'esca "
    "contiene due marcatori DISPUTED conflicting record entrambi chiusi "
    "da unresolved",
]

#: Il verso opposto: contraddizioni di polarità VERE, che devono restare.
OPPOSTI_VERI = [
    ("Il farmaco riduce la mortalita dei pazienti.",
     "Il farmaco non riduce la mortalita dei pazienti."),
    ("La differenza fra i gruppi e statisticamente significativa.",
     "La differenza fra i gruppi non e statisticamente significativa."),
    ("The drug reduces patient mortality.",
     "The drug does not reduce patient mortality."),
]


def _fatti(*props) -> list[Fact]:
    """Con l'EMBEDDING vero, altrimenti il test non misura niente.

    `detect_boolean_clashes` scarta le coppie sotto `similarity_threshold`
    (0.75), e `_cosine` RI-CODIFICA le proposizioni invece di leggere un
    campo — il Fact pubblico non porta i byte. Quindi il coseno dipende solo
    dal TESTO, e i testi qui sotto sono quelli veri del corpus: accorciandoli
    il coseno scende sotto la soglia e il test passerebbe senza aver misurato
    niente. (Prima versione di questo file: i cinque indipendenti passavano
    gia', e non perche' la cura ci fosse.)
    """
    return [Fact(id=f"f{i}", proposition=p, topic="handoff/consegna",
                 confidence=0.9, source_episodes=[], created_at=time.time())
            for i, p in enumerate(props)]


@pytest.fixture(autouse=True)
def coseno_del_corpus(monkeypatch):
    """Il coseno che queste frasi hanno DAVVERO, fissato a mano.

    ⚠️ SENZA QUESTO IL FILE NON MISURA NIENTE, e la ragione vale ben oltre.
    Il conftest della suite impone ``HIPPO_OFFLINE=1``, quindi sotto pytest
    l'embedder è un sostituto: sulle STESSE due frasi il coseno vale **0.1974**
    dentro pytest e **0.8265** fuori. La soglia ``similarity_threshold=0.75``
    di ``detect_boolean_clashes`` non viene perciò MAI esercitata sul
    comportamento reale — nessuna coppia ci arriva sopra, e ogni test del
    rilevatore passa senza aver giudicato niente.

    È il motivo per cui la suite non poteva accorgersi del guasto che questo
    file documenta: per costruzione non lo vede. Stessa trappola già
    incontrata due volte qui dentro (``ENGRAM_RECALL_RERANK=0`` sul rerank,
    ``ENGRAM_ENCODE_SERVICE=0`` sul daemon) — un interruttore globale del
    conftest che fa passare i test senza eseguire il codice in esame.

    Si fissa quindi il coseno al valore MISURATO sul corpus di produzione
    (0.83; la fascia reale dei dodici è 0.8194–0.8677), così il test giudica
    la LOGICA del clash — che è deterministica — invece di dipendere da un
    modello che sotto pytest non c'è.
    """
    monkeypatch.setattr("verimem.contradiction._cosine", lambda a, b: 0.83)


@pytest.mark.parametrize("indipendente", INDIPENDENTI)
def test_un_fatto_che_parla_d_altro_non_e_una_contraddizione(indipendente):
    """Il cuore: erano 12 su 12 a essere segnalati, e nessuno lo era."""
    clash = detect_boolean_clashes(_fatti(VINCITORE, indipendente))
    assert not clash, (
        f"segnalato un conflitto di polarita' fra due fatti che parlano di "
        f"cose diverse:\n  A: {VINCITORE[:70]}\n  B: {indipendente[:70]}")


@pytest.mark.parametrize("a,b", OPPOSTI_VERI)
def test_le_contraddizioni_VERE_restano_rilevate(a, b):
    """IL VERSO CHE RENDE LA CURA ONESTA. Restringere fino a non segnalare
    piu' niente spegnerebbe il rilevatore invece di correggerlo — e un
    rilevatore spento e' un guasto muto, la categoria peggiore di questo
    progetto."""
    assert detect_boolean_clashes(_fatti(a, b)), (
        f"la contraddizione fra «{a[:44]}» e «{b[:44]}» non viene piu' vista")


def test_un_solo_vincitore_non_puo_ingoiare_tutto_il_topic():
    """La forma del guasto sul corpus: un fatto contro i dodici insieme. Con
    la guardia nessuno di quei dodici viene messo in conflitto con lui."""
    clash = detect_boolean_clashes(_fatti(VINCITORE, *INDIPENDENTI))
    coinvolti = {c.fact_a_id for c in clash} | {c.fact_b_id for c in clash}
    assert not coinvolti, (
        f"{len(coinvolti)} fatti messi in conflitto con un vincitore che non "
        f"li contraddice: e' il clustering che sbaglia, non il contenuto")


def test_la_stessa_polarita_non_e_mai_un_clash():
    """Presidio del comportamento originale: due frasi entrambe negative, o
    entrambe affermative, non sono un conflitto di polarita' per quanto si
    somiglino."""
    assert not detect_boolean_clashes(_fatti(
        "Il farmaco non riduce la mortalita dei pazienti.",
        "Il farmaco non riduce la mortalita dei pazienti anziani."))
