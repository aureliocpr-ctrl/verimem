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

═══ IL LIMITE DICHIARATO QUI È CADUTO LO STESSO GIORNO ═══

Questo file conteneva un guardiano che asseriva *«cinese e giapponese restano
scoperti»*, con la nota che se fosse diventato rosso avrebbe voluto dire che
qualcuno aveva risolto la segmentazione. È diventato rosso.

La diagnosi però reggeva, ed è la parte che valeva la pena scrivere: **non
mancava una regex, mancava la segmentazione**. Senza spazi il confronto cercava
`可用` fra i token della frase affermativa e lì c'era solo il blocco `服务可用`.
La cura sta in `content_tokens`, che ora emette i **bigrammi di caratteri**
delle sequenze CJK — unità confrontabili senza dizionario, come `8月10日` era
un criterio posizionale senza lista.

⚖️ **Un limite dichiarato è un debito, non un'assicurazione.** Averlo scritto
come test è servito a questo: il debito era esigibile, e il test ha detto
quando è stato pagato.
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


@pytest.mark.parametrize("lingua,affermativa,negativa", [
    ("ZH", "服务可用。", "服务不可用。"),
    ("JA", "サービスは利用できます。", "サービスは利用できません。"),
])
def test_la_negazione_vale_ANCHE_senza_spazi(lingua, affermativa, negativa):
    """⚠️ QUESTO TEST ERA IL GUARDIANO DI UN LIMITE, ED È DIVENTATO ROSSO.

    Stava qui scritto così: *«Se un giorno diventasse rosso, vorrebbe dire che
    qualcuno ha risolto la segmentazione CJK — e allora questo file va
    aggiornato insieme alla cura, non prima»*. È successo lo stesso giorno.
    Il limite non era «una regex da estendere» ma la segmentazione, e la cura
    è quella: `content_tokens` emette i **bigrammi di caratteri** delle sequenze
    CJK, che ritagliano unità confrontabili dove non ci sono spazi.

    📌 SERVIVANO DUE PEZZI, e il secondo si vede solo misurando. Con i bigrammi
    la guardia di stesso-soggetto restava sotto la soglia di Jaccard 0.6::

        rimosso il negatore CON uno spazio   -> J = 0.50   ancora bloccato
        rimosso il negatore SENZA spazio     -> J = 1.00   passa

    Perché `不` sta **dentro** la sequenza: sostituirlo con uno spazio la spezza
    e distrugge il bigramma di giunzione. Su tutte e sette le lingue il Jaccard
    misurato è ≥0.67, e sulla popolazione opposta 0.00.
    """
    r = lexical_conflict(affermativa, negativa)
    assert r is not None, f"[{lingua}] la negazione non produce conflitto"
    assert r[0] == "negation", f"[{lingua}] conflitto del tipo sbagliato: {r}"


def test_ALLA_PORTA_il_gate_vede_la_negazione_CJK():
    """⛔ IL LIVELLO A CUI SI MISURA DECIDE IL VERDETTO, e qui è già successo.

    La stessa cura, misurata sui due livelli nella stessa esecuzione:

    · su `numeric_conflict` il conflitto cinese passava da `None` a
      `('毫克', 11.0, 12.0)` — sembrava il risultato principale;
    · su `validate_claim`, **la porta che il prodotto usa**, quel caso era già
      `contradicted` anche a bigrammi spenti: il gate ci arrivava per un'altra
      strada. ⇒ Su quel path la cura non cambia nulla.

    Il guadagno vero è **questo**, ed è alla porta: A/B nella stessa esecuzione,
    `unknown` -> `contradicted` in cinese e giapponese. Un gate che non vede la
    negazione non è severo, è muto: accetta come non-contraddittorio l'esatto
    contrario di ciò che ha in memoria.

    ⚠️ La popolazione opposta è misurata insieme e resta `unknown`: tre coppie
    che parlano di cose diverse, nessun falso `contradicted`.
    """
    from dataclasses import dataclass, field

    from verimem.validate_claim import validate_claim

    @dataclass
    class _F:
        id: str
        proposition: str
        topic: str = "t"
        confidence: float = 0.9
        source_episodes: list = field(default_factory=list)

    class _Agent:
        def __init__(self, facts):
            self.semantic = type(
                "_S", (), {"search_facts": lambda _s, _q, **_k: facts})()

    def _verdetto(in_memoria: str, claim: str) -> str:
        return validate_claim(_Agent([_F("1", in_memoria)]), claim)["verdict"]

    assert _verdetto("服务可用。", "服务不可用。") == "contradicted"
    assert _verdetto("サービスは利用できます。", "サービスは利用できません。") == "contradicted"
    # ⚠️ e due frasi che parlano di cose diverse non diventano una contraddizione
    assert _verdetto("服务可用。", "维罗纳仓库有480个托盘。") != "contradicted"
    assert _verdetto("サービスは利用できます。", "キャッシュは30分後に期限切れです。") != "contradicted"
