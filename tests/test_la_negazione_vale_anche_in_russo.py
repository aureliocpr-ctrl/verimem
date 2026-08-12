"""«Сервис доступен» contro «Сервис **не** доступен»: nessun conflitto.

Il rilevatore di polarità confronta due frasi uguali di cui una porta un
negatore. Misurato il 12/08 sul perimetro delle sette lingue::

    EN / IT / FR / ES   conflitto rilevato ✅
    RU / ZH / JA        None — la negazione non esiste

⚠️ **È il layer che il 12/08 ha fermato un'inferenza sbagliata su un caso
vero**: una fonte diceva «**No** call had correct parameters» e chi la citava
ne aveva tratto il contrario. Un layer che salva in inglese e tace in russo non
è una protezione: è una protezione *per alcuni*.

═══ LA CAUSA ERA IN DUE PEZZI, E UNO ERA GIÀ STATO CURATO ═══

`_NEGATOR_RE` copriva già giapponese, cinese e arabo — esteso il 2026-08-04 da
un'altra istanza, con la nota che *«lasciarli fuori sarebbe coprire le lingue
con gli spazi invece che le lingue»*. Mancava il **russo**.

Ma il pezzo che nessuno aveva guardato è **una riga più sotto**: lo scope della
negazione si cercava con ``[a-zA-Z]{4,}``. ⇒ **Il negatore veniva riconosciuto
e ciò che negava no.** Metà del lavoro fatto due volte, metà mai.

🔑 Riconoscere una negazione non serve a niente se poi non si guarda che cosa
nega — e questa metà era invisibile proprio perché l'altra funzionava.

═══ ⚠️ IL LIMITE, misurato DOPO la cura ═══

Cinese e giapponese **restano scoperti**, ed è dichiarato invece che taciuto.
Lo scope adesso li estrae (`不可用` → `可用`), ma il confronto cerca quel token
fra quelli della frase affermativa, e lì non c'è nessun `可用`: c'è il blocco
`服务可用`, perché senza spazi non si ritagliano parole. In giapponese la
negazione è poi un **suffisso** (`利用できます` → `利用できません`), quindi l'oggetto
sta anche dalla parte sbagliata.

⇒ Non manca una regex: **manca la segmentazione** — lo stesso difetto che rende
`content_tokens` cieco in quelle due lingue.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import lexical_conflict

COPPIE_CURATE = [
    ("EN", "The service is available.", "The service is not available."),
    ("IT", "Il servizio e' disponibile.", "Il servizio non e' disponibile."),
    ("FR", "Le service est disponible.", "Le service n'est pas disponible."),
    ("ES", "El servicio esta disponible.", "El servicio no esta disponible."),
    ("RU", "Сервис доступен.", "Сервис не доступен."),
]


@pytest.mark.parametrize("lingua,affermativa,negativa", COPPIE_CURATE,
                         ids=[c[0] for c in COPPIE_CURATE])
def test_la_stessa_frase_negata_e_un_conflitto(lingua, affermativa, negativa):
    """Il cuore. Il russo è quello nuovo; gli altri quattro sono qui perché una
    cura che aggiunge una lingua può romperne una che funzionava."""
    r = lexical_conflict(affermativa, negativa)
    assert r is not None, f"[{lingua}] la negazione non produce conflitto"
    assert r[0] == "negation", f"[{lingua}] conflitto del tipo sbagliato: {r}"


@pytest.mark.parametrize("lingua,a,b", [
    ("EN", "The service is available.", "The service is available."),
    ("RU", "Сервис доступен.", "Сервис доступен."),
    ("ZH", "服务可用。", "服务可用。"),
    ("IT", "Il magazzino contiene 480 pallet.", "Il deposito ha 320 pallet."),
])
def test_CONTROLLO_NEGATIVO_senza_negazione_nessun_conflitto(lingua, a, b):
    """⚠️ LA POPOLAZIONE OPPOSTA. Un riconoscitore di negazioni troppo largo
    trasforma ogni coppia in una contraddizione — e un falso conflitto
    **retrocede un fatto vero**, che è il danno peggiore per una memoria
    verificata."""
    assert lexical_conflict(a, b) is None, f"[{lingua}] falso positivo"


def test_IL_LIMITE_cinese_e_giapponese_restano_scoperti():
    """⚠️ QUESTO TEST DOCUMENTA UN LIMITE, NON UNA CAPACITÀ.

    Se un giorno diventasse rosso, vorrebbe dire che qualcuno ha risolto la
    segmentazione CJK — e allora questo file va aggiornato insieme alla cura,
    non prima. È scritto perché il limite resti visibile: un difetto che non ha
    un test non è dichiarato, è solo ricordato da chi c'era.
    """
    assert lexical_conflict("服务可用。", "服务不可用。") is None
    assert lexical_conflict("サービスは利用できます。", "サービスは利用できません。") is None
