"""«the CE is multilingual» era la GIUSTIFICAZIONE di un default, ed era falsa.

`local_ce_available()` decide se accendere il moat per chi non passa un llm, e
il suo docstring motivava quel default con «(the CE is multilingual)».
Misurato il 25/08 sul modello effettivamente caricato::

    model_type : deberta-v2
    vocab_size : 128100          (mDeBERTa multilingue ne ha ~251k)
    gate_config.json -> base_model: cross-encoder/nli-deberta-v3-base

Il giudice e' un DeBERTa-v3 INGLESE fine-tuned. La frase non era opinabile:
era falsa, e stava li' come motivo di una scelta di default — il tipo di
affermazione che non si corregge cancellandola, perche' cancellarla lascia il
default senza ragione scritta.

═══ E LA CONTRADDIZIONE CON RELEASE_GATE NON ESISTEVA ═══
Sembrava che due documenti di casa dicessero il contrario:

    RELEASE_GATE.md:42 (G10)   «NLI=DeBERTa-v3(EN), CE=ms-marco(EN)»
    local_grounding.py:391     «the CE is multilingual»

Non si contraddicono: nominano COMPONENTI DIVERSI con la stessa sigla. Nel
prodotto ci sono DUE cross-encoder —

    rerank del retrieval : cross-encoder/ms-marco-MiniLM-L-12-v2
                           (cross_encoder_rerank.py:16,35)
    giudice del moat     : cross-encoder/nli-deberta-v3-base
                           (benchmark/local_gate_finetune.py:218, gate_config)

G10 chiama «CE» il reranker e «NLI» il giudice; `local_grounding` chiama «CE»
il giudice. G10 aveva ragione da luglio e nessuno l'ha collegato al docstring.
⇒ 🔑 La classe e' «due nozioni diverse sotto lo stesso nome»: un documento non
si allinea all'altro finche' la sigla non e' disambiguata, o si propaga
l'errore invece di curarlo.

⛔ QUESTO PRESIDIO NON MISURA LA LINGUA. Non puo': la separazione del giudice
per lingua e' un fatto sul COMPORTAMENTO (grounding_gate.py:522-531 la misura
97-99 vs ~0.6 «in EN/IT/FR/ES alike»), il vocabolario e' un fatto sul MODELLO,
e i due non si implicano. Presidia una cosa sola e verificabile: che il
docstring nomini il modello che il repo dichiara di addestrare, cosi' che
cambiare il modello renda ROSSA l'affermazione invece di lasciarla invecchiare.
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

_RADICE = Path(__file__).resolve().parent.parent
_FINETUNE = _RADICE / "benchmark" / "local_gate_finetune.py"
_RERANK = _RADICE / "verimem" / "cross_encoder_rerank.py"


def _docstring() -> str:
    from verimem.local_grounding import local_ce_available
    return inspect.getdoc(local_ce_available) or ""


def _base_model_dichiarato() -> str:
    """Il base model che il REPO dichiara di addestrare — la fonte, non la mia
    memoria. Se qualcuno cambia questo default, il docstring diventa rosso."""
    src = _FINETUNE.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'--base-model["\']?,\s*default=["\']([^"\']+)["\']', src)
    if not m:
        pytest.fail(
            f"non trovo il default di --base-model in {_FINETUNE.name}: il "
            f"presidio ha perso la sua fonte e va riscritto, non aggirato")
    return m.group(1)


#: La frase falsa, come stava scritta.
_FALSA = "the ce is multilingual"


def test_il_docstring_AFFERMA_che_il_vocabolario_e_inglese():
    """IL CUORE, in POSITIVO — e la forma positiva non e' un dettaglio.

    🪞 La prima stesura di questo presidio vietava la stringa «the CE is
    multilingual» e basta. E' diventata ROSSA sulla cura CORRETTA, perche' il
    docstring nuovo CITA la frase vecchia per dire che era falsa::

        This docstring used to say "(the CE is multilingual)". That was FALSE…

    Un divieto di sottostringa non distingue USO da MENZIONE — che e'
    esattamente il difetto misurato del layer L1 di questo stesso prodotto
    (precisione ~40%, «un criterio lessicale non distingue uso da menzione»).
    Il mio misuratore ci e' cascato in cinque minuti mentre documentavo il
    difetto nel prodotto.
    ⇒ La cura NON e' stata togliere la citazione dal docstring — serve, dice
    cosa e' stato corretto. E' stato spostare il presidio in POSITIVO: si
    pretende l'affermazione VERA, che nessuna citazione puo' soddisfare per
    sbaglio, invece di vietare quella falsa, che ogni citazione viola.
    """
    d = _docstring().lower()
    assert "english" in d, (
        "il docstring non dice piu' che il giudice e' un modello inglese. "
        "Misurato sul modello caricato: vocab_size 128100, base "
        "cross-encoder/nli-deberta-v3-base.")
    assert "128100" in d or "vocab" in d, (
        "il docstring afferma la lingua senza portare il numero che la mostra: "
        "senza vocab_size resta un'opinione come quella che ha sostituito.")


def test_l_affermazione_falsa_torna_solo_come_CITAZIONE_marcata():
    """Il divieto resta, ma consapevole della menzione.

    ⛔ Criterio dichiaratamente SINTATTICO, e qui regge per una ragione
    locale, non generale: nel testo la frase compare una volta sola e dentro
    virgolette, subito dopo «used to say». Se un domani ricomparisse
    ASSERITA, non avrebbe ne' virgolette ne' quel marcatore.
    """
    d = _docstring().lower()
    n = d.count(_FALSA)
    if n == 0:
        return
    marcate = d.count(f'used to say "({_FALSA})"')
    assert n == marcate, (
        f"«{_FALSA}» compare {n} volte ma solo {marcate} come citazione "
        f"marcata: le altre sono affermazioni, e sono false sul modello "
        f"caricato (vocab_size 128100).")


def test_il_docstring_NOMINA_il_modello_che_il_repo_addestra():
    """Cancellare la frase falsa non basta: senza il nome del modello il
    lettore non ha modo di sapere QUALE dei due cross-encoder sia questo."""
    base = _base_model_dichiarato()
    corto = base.rsplit("/", 1)[-1]
    assert corto in _docstring(), (
        f"il docstring non nomina il modello del giudice ({corto}, da "
        f"{_FINETUNE.name}). Senza il nome, «CE» resta ambiguo fra il giudice "
        f"e il reranker ms-marco, che e' l'equivoco costato la falsa "
        f"contraddizione con RELEASE_GATE G10.")


def test_il_docstring_dice_ancora_PERCHE_il_default_e_acceso():
    """⚖️ L'ALTRO VERSO, e senza di esso la cura si aggira cancellando: la
    frase falsa motivava una scelta (moat ON per chi non passa un llm). Tolta
    la motivazione sbagliata, ne serve una giusta — non il vuoto."""
    d = _docstring().lower()
    assert "default" in d and ("no llm" in d or "injected llm" in d), (
        "il docstring non spiega piu' perche' il moat sia acceso di default "
        "per chi non passa un llm: la frase falsa e' stata rimossa senza "
        "sostituirla, e il default e' rimasto senza ragione scritta.")


def test_i_due_cross_encoder_restano_distinguibili():
    """La sigla «CE» nomina due componenti. Il presidio tiene fermo il fatto
    che siano DUE, cosi' che un domani nessuno li fonda per errore."""
    rer = _RERANK.read_text(encoding="utf-8", errors="replace")
    assert "ms-marco" in rer, (
        f"{_RERANK.name} non nomina piu' ms-marco: se il reranker e' cambiato, "
        f"la nota in RELEASE_GATE G10 e questo docstring vanno rivisti insieme.")
    assert _base_model_dichiarato() not in rer, (
        "il reranker e il giudice dichiarano lo STESSO modello: o e' una "
        "regressione, o i due componenti sono stati unificati e allora la "
        "distinzione spiegata qui sopra non vale piu'.")
