"""Quando l'oggetto della negazione non si trova, il flip non va concesso.

`negation_conflict` ha una guardia di precisione: la parola nello scope del
negatore dev'essere condivisa, o «complete, not blocked» flipperebbe «complete».
Quella guardia è scritta::

    if scoped and not scoped_shared:
        return None

⇒ **se `scoped` è vuoto non entra affatto**, e il confronto scivola al fallback
dichiarando un conflitto. Lo scope esce vuoto ogni volta che il negatore CHIUDE
la frase — le lingue SOV — o che la sua coda non è una parola riconoscibile.

Misurato prima della cura, con i negatori delle tre lingue attivati::

    negatori aggiunti, guardia di ieri   veri 7/7 · FALSI POSITIVI 2/6  (turco, hindi)
    + regola dei token esclusivi         veri 7/7 · FALSI POSITIVI 0/6

═══ 🔑 PERCHÉ NON SI CURA CERCANDO MEGLIO LO SCOPE ═══

Ci ho provato, ed è la ragione per cui questo file esiste. La prima cura cercava
*l'ultimo blocco di kanji prima della desinenza*: risolve il giapponese e lascia
scoperti turco, hindi e coreano, che di kanji non ne hanno. Un ripiego generico
sull'ultima parola dimezza i falsi ma ne perde uno vero (2/5 contro 3/5), e il
coreano è un caso ulteriore — è agglutinante, `않` è un morfema **dentro** la
parola, e «l'ultima parola prima del negatore» non è nemmeno definita.

⇒ «Dove sta l'oggetto della negazione» è una domanda che **dipende dalla
scrittura**, e ogni risposta copre una lingua per volta. La domanda che questo
file usa non ne dipende: **il lato negato porta contenuto che l'altro non
enuncia?** Se sì, il negatore parla anche di quello, e due frasi che non dicono
la stessa cosa non possono essere l'una la smentita dell'altra.

📌 I negatori di turco, coreano e hindi **non sono in `_NEGATOR_RE`**: senza di
loro il flip non esce e il difetto non si vede. È latente, e si accenderebbe il
giorno in cui qualcuno li aggiunge — per questo i test qui sotto **li attivano
loro stessi**: presidiano chi verrà, non lo stato di oggi.
"""
from __future__ import annotations

import re

import pytest

import verimem.quantity_match as Q

#: I negatori che oggi mancano. Solo forme non ambigue: `안` da solo significa
#: anche «dentro» e produrrebbe falsi positivi a raffica.
NEGATORI_ASSENTI = r"|\b(?:de[gğ]il|yok)\b|(?:않|없|아니)|नहीं"

#: Coppie che SI contraddicono: il flip deve uscire.
OPPOSTI = [
    ("inglese", "the system is signed", "the system is not signed"),
    ("italiano", "il farmaco riduce la mortalita", "il farmaco non riduce la mortalita"),
    ("russo", "система подписана", "система не подписана"),
    ("cinese", "系统已签名", "系统未签名"),
    ("giapponese", "システムは署名されました", "システムは署名されません"),
    ("turco", "sistemde hata var", "sistemde hata yok"),
    ("hindi", "सिस्टम हस्ताक्षरित है", "सिस्टम हस्ताक्षरित नहीं है"),
]

#: ⚠️ Coppie COMPATIBILI: il negatore riguarda qualcosa che l'altra frase non
#: dice. Nessuna è una contraddizione, e prima della cura due uscivano.
COMPATIBILI = [
    ("inglese", "the system is signed", "the system is signed but not encrypted"),
    ("italiano", "il compito e completo", "il compito e completo, non bloccato"),
    ("giapponese", "システムは署名されました",
     "システムは署名されましたが暗号化されていません"),
    ("cinese", "系统已签名", "系统已签名，未加密"),
    ("turco", "sistem imzalanmis", "sistem imzalanmis, sifreli degil"),
    ("hindi", "सिस्टम हस्ताक्षरित है",
     "सिस्टम हस्ताक्षरित है, एन्क्रिप्टेड नहीं है"),
]


@pytest.fixture
def negatori_completi(monkeypatch):
    """Accende i negatori che il prodotto non ha ancora.

    Senza questa fixture i casi turco e hindi passerebbero per la ragione
    sbagliata — nessun negatore riconosciuto, nessun flip, verde a vuoto.
    """
    monkeypatch.setattr(
        Q, "_NEGATOR_RE",
        re.compile(Q._NEGATOR_RE.pattern + NEGATORI_ASSENTI, re.IGNORECASE))


@pytest.mark.parametrize("lingua,a,b", COMPATIBILI)
def test_due_frasi_compatibili_non_sono_una_contraddizione(
        lingua, a, b, negatori_completi):
    """Il cuore. Turco e hindi qui fallivano: il loro negatore chiude la frase,
    lo scope usciva vuoto e la guardia non entrava in funzione."""
    assert Q.negation_conflict(a, b) is None, (
        f"[{lingua}] «{a}» e «{b}» non si contraddicono — la seconda aggiunge "
        f"un'informazione che la prima non dà — e vengono dichiarate in "
        f"conflitto. Un conflitto inesistente RITIRA un fatto vero, mentre uno "
        f"mancato lascia le cose come stanno: questo verso costa di più")


@pytest.mark.parametrize("lingua,a,b", OPPOSTI)
def test_LA_POPOLAZIONE_OPPOSTA_viene_ancora_vista(lingua, a, b, negatori_completi):
    """⚠️ Senza questo, la cura si «supera» spegnendo il rilevatore.

    La regola aggiunta è una CONDIZIONE DI RINUNCIA: più diventa larga, meno
    contraddizioni si vedono. Queste sette misurano che non abbia mangiato il
    lavoro che il layer deve fare.
    """
    assert Q.negation_conflict(a, b) is not None, (
        f"[{lingua}] «{a}» e «{b}» hanno polarità opposta sullo stesso "
        f"contenuto e il conflitto non viene più visto: la condizione di "
        f"rinuncia si è allargata troppo")


def test_SENZA_I_NEGATORI_NUOVI_le_due_lingue_non_dicono_nulla():
    """📌 Il limite dichiarato, e serve a non leggere i test sopra come una
    promessa che il prodotto oggi non fa.

    Turco e hindi non hanno il proprio negatore in `_NEGATOR_RE`: senza la
    fixture il flip non esce, né giusto né sbagliato. Se un domani questo test
    diventasse rosso vorrebbe dire che qualcuno **ha aggiunto quei negatori** —
    e allora i due test sopra smettono di presidiare un caso ipotetico e
    cominciano a presidiare il prodotto vero.
    """
    assert Q.negation_conflict("sistemde hata var", "sistemde hata yok") is None
    assert Q.negation_conflict("सिस्टम हस्ताक्षरित है",
                               "सिस्टम हस्ताक्षरित नहीं है") is None
