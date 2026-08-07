"""A una domanda senza risposta il recall risponde lo stesso, e il pavimento c'era.

IL DIFETTO, misurato da ws5 su un corpus aziendale controllato (24 fatti, 20
domande, due popolazioni)::

    15 domande RISPONDIBILI   primo posto giusto 14/15   <- il retrieval funziona
     5 domande IMPOSSIBILI    `recall` risponde **5 volte su 5**

    «Qual è il fatturato del 2025?»    -> «Gli interessi di mora sono al 4%»
    «Chi è l'amministratore delegato?» -> «Il responsabile qualità è Anna Ferri»
    «Quanti dipendenti ha l'azienda?»  -> «L'ordine 91 è ancora in lavorazione»

Risposte **peggiori del silenzio**: plausibili nella forma, scollegate nel
merito, e con ``grounding_score`` fino a 99.93 — cioè un agente che le riceve
vede un fatto verificato. Il prodotto dichiara «abstention over hallucination»,
e su questa porta non lo applicava.

🔑 IL MECCANISMO ESISTE ED È GIÀ USATO DA DUE SUPERFICI::

    trust_report(domanda impossibile) -> "abstained": true
        «nothing scored above the relevance floor for this query»
    explain(...)                      -> identico
    recall / search                   -> **nessun pavimento**

È l'asimmetria fra porte, di nuovo: la promessa è mantenuta su quella che quasi
nessuno apre.

⚠️ MA IL PAVIMENTO **NON** SI ACCENDE COME VETO, e il motivo è una misura mia
che contraddice quella di ws5 — ed è il valore della verifica incrociata::

    banco di ws5   rispondibili min 0.8757 · impossibili max 0.8290
                   pavimento 0.8689  -> DENTRO il margine, 0 falsi tagli
    banco mio      rispondibili min **0.8489** · impossibili max 0.8103
                   pavimento **0.8491** -> **SOPRA il minimo delle buone**

Sul mio banco il pavimento taglierebbe «in che stato è l'ordine 91», che una
risposta ce l'ha: **1 falso taglio su 5**, dove ws5 ne misurava zero. Il criterio
non è sbagliato — è che la sua taratura dipende dal corpus, e un veto costa un
fatto perso mentre un avviso costa un avviso.

⇒ Quindi `search` **DICHIARA** invece di tagliare: dice che nessun risultato
supera il pavimento, e chi legge decide. È la stessa forma di `nascosti`,
`trattenuto_da`, `moat`, `quarantined_by` — e la stessa regola che ho chiesto
alle altre sul censimento dei default: *trovare ≠ accendere*.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory

CORPUS = [
    ("Il magazzino di Verona contiene 480 unita.",
     "Inventario: il magazzino di Verona contiene 480 unita."),
    ("Gli interessi di mora sono pari al 4 per cento annuo.",
     "Contratto: interessi di mora al 4 per cento annuo."),
    ("Il responsabile della qualita' e' Anna Ferri.",
     "Organigramma: responsabile qualita' Anna Ferri."),
    ("L'ordine 91 e' ancora in lavorazione.",
     "Registro ordini: l'ordine 91 e' ancora in lavorazione."),
    ("L'ufficio legale ha sede a Roma.", "Sedi: l'ufficio legale ha sede a Roma."),
]


@pytest.fixture()
def mem(tmp_path):
    m = Memory(str(tmp_path / "s.db"))
    for p, f in CORPUS:
        m.add(p, topic="az/corp", source=f)
    return m


@pytest.mark.parametrize("domanda", [
    "qual e' il fatturato del 2025",
    "chi e' l'amministratore delegato",
    "quanti dipendenti ha l'azienda",
    "indirizzo email del servizio clienti",
])
def test_su_una_domanda_SENZA_risposta_il_recall_lo_DICE(mem, domanda):
    """IL CUORE: il corpus non contiene la risposta, e chi chiede deve saperlo.
    Non si asserisce che la lista sia vuota — il pavimento ha una taratura che
    dipende dal corpus e tagliare sarebbe un veto — ma che l'informazione ci
    sia."""
    hits = mem.search(domanda, k=3)
    assert getattr(hits, "sotto_il_pavimento", None), (
        f"«{domanda}» riceve risultati senza nessun segnale che siano tutti "
        f"sotto la soglia di rilevanza")


@pytest.mark.parametrize("domanda", [
    "quante unita ci sono nel magazzino di Verona",
    "quanto sono gli interessi di mora",
    "chi e' il responsabile della qualita'",
    "dove ha sede l'ufficio legale",
])
def test_CONTROLLO_POSITIVO_una_domanda_con_risposta_non_viene_segnalata(mem, domanda):
    """⚠️ IL PRESIDIO CHE VALE PIÙ DELLA CURA: se il segnale comparisse anche
    sulle domande buone, non direbbe niente e chi legge imparerebbe a
    ignorarlo — che è esattamente come si rende inutile un avviso."""
    hits = mem.search(domanda, k=3)
    assert hits, "il banco non risponde: rotto"
    assert not getattr(hits, "sotto_il_pavimento", None), (
        f"«{domanda}» segnalata come sotto il pavimento, ma la risposta c'è "
        f"(score {hits[0].get('score')})")


def test_i_RISULTATI_non_vengono_tagliati(mem):
    """⚠️ IL SECONDO PRESIDIO, e nasce da una misura che contraddice quella di
    ws5: sul mio banco il pavimento (0.8491) sta SOPRA il minimo delle domande
    rispondibili (0.8489), quindi come veto perderebbe un fatto vero.
    Dichiarare costa un avviso; tagliare costa una risposta."""
    hits = mem.search("qual e' il fatturato del 2025", k=3)
    assert len(hits) > 0, (
        "i risultati sono stati TAGLIATI: il pavimento è diventato un veto")


def test_il_segnale_porta_il_NUMERO_non_solo_il_flag(mem):
    """Chi integra deve poter decidere con la propria soglia: il punteggio
    migliore e il pavimento applicato, non un booleano opaco."""
    hits = mem.search("chi e' l'amministratore delegato", k=3)
    info = getattr(hits, "sotto_il_pavimento", None)
    assert isinstance(info, dict), info
    assert "pavimento" in info and "score_migliore" in info, info
    assert info["score_migliore"] < info["pavimento"]
