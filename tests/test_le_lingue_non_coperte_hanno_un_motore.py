"""Quando le liste non sanno leggere, decide il modello che parla cento lingue.

Il criterio dell'evoluzione e' costruito su liste di parole scritte a mano per
quattro lingue — articoli, preposizioni, connettivi, parole vuote — e gli
utenti sono in tutto il mondo. Dove le liste non arrivano il prodotto prima
DANNEGGIAVA (due fatti tedeschi scorrelati si ritiravano: i sostantivi
tedeschi sono maiuscoli, finivano tutti fra i nomi propri, e restavano come
«contenuto» solo l'articolo e la copula) e poi, con la guardia sulla densita'
di maiuscole, si e' messo a TACERE.

Tacere e' meglio che sbagliare e resta un servizio in meno. Il motore per
farlo davvero e' gia' installato e gia' in uso: `intfloat/multilingual-e5-base`,
768 dimensioni, e sul corpus di Aurelio TUTTI i 6972 fatti hanno gia'
l'embedding persistito in tabella. Confrontare due soggetti in tedesco, turco
o polacco e' un coseno fra due vettori — nessuna lista da scrivere.

LA SOGLIA E' MISURATA, NON SCELTA. Banco di dodici coppie scritte a mano in
lingue NON coperte (de, pt, pl, tr), meta' evoluzioni vere e meta'
osservazioni scorrelate:

    vere   0.9349 .. 0.9682     (Jahresplan 100 -> 200 Euro, Server 8 -> 16 Kerne,
                                 plano anual, Serwer, Sunucu)
    false  0.8121 .. 0.8674     (Graph/Quarantaene, Server/Repository, ...)

e tre casi DURI — stesso soggetto, grandezza DIVERSA, che non sono evoluzioni
e che il criterio lessicale non prende:

    0.8581  Der Korpus enthaelt 6682 Fakten. | ... mediane Laenge von 795 Zeichen.
    0.9117  Der Graph hat 8625 Knoten.       | ... eine Dichte von 0.42.
    0.9082  Il corpus contiene 6682 fatti.   | ... una mediana di 795 caratteri.

A 0.93 il banco si separa tutto: 6 vere sopra, 6 false sotto, 3 duri respinti.
Il margine e' STRETTO — 0.9349 la vera piu' bassa contro 0.9117 il duro piu'
alto, cioe' 0.023 — e va detto: non e' una separazione comoda, e' quel tanto
che basta sul banco che ho. Se un giorno una coppia vera scende sotto, la
soglia va rimisurata su un banco piu' grande, non abbassata.

QUESTO ESTENDE LA COPERTURA, NON RISOLVE IL CASO DURO. Due misure diverse
dello stesso soggetto restano il limite aperto — l'embedding le sbaglierebbe a
0.9117 come le sbaglia il lessicale — e per quelle serve sapere QUALE
grandezza si misura, che e' un'altra partita.

LE MISURE STANNO NEL TEST, IL MODELLO NO. La suite stubba l'embedding — in
CI il modello non c'e' e non deve esserci — quindi qui si inietta il valore
MISURATO di ogni coppia e si verifica che la logica lo usi bene: la soglia,
l'ordine dei rami, il fast-path che non paga un encode. I numeri si
riproducono con `scratchpad/banco_multilingue.py`, che il modello vero ce
l'ha; se un giorno cambiano, e' quello script a dirlo, non questo file.
"""
from __future__ import annotations

import pytest

import verimem.validate_claim as vc
from verimem.anti_confab_gate import _puo_essere_una_evoluzione

#: (vecchio, nuovo, similarita' MISURATA con multilingual-e5-base)
VERE_NON_COPERTE = [
    ("Der Jahresplan kostet 100 Euro.", "Der Jahresplan kostet 200 Euro.", 0.9682),
    ("Der Server hat 8 Kerne.", "Der Server hat 16 Kerne.", 0.9556),
    ("O plano anual custa 100 euros.", "O plano anual custa 200 euros.", 0.9559),
    ("Serwer ma 8 rdzeni.", "Serwer ma 16 rdzeni.", 0.9349),
    ("Sunucu 8 cekirdege sahiptir.", "Sunucu 16 cekirdege sahiptir.", 0.9568),
]

FALSE_NON_COPERTE = [
    ("Der Graph hat 8625 Knoten.", "Die Quarantaene haelt 528 Fakten zurueck.", 0.8315),
    ("Der Server hat 8 Kerne.", "Das Repository hat 113 Commits.", 0.8414),
    ("O grafo tem 8625 nos.", "A quarentena retem 528 fatos.", 0.8674),
    ("Serwer ma 8 rdzeni.", "Repozytorium ma 113 commitow.", 0.8121),
    ("Sunucu 8 cekirdege sahiptir.", "Depo 113 commit iceriyor.", 0.8126),
]


@pytest.fixture()
def con_similarita(monkeypatch):
    """Inietta la misura reale al posto dell'encode, che la suite stubba."""
    def _con(valore: float):
        monkeypatch.setattr(vc, "similarita_semantica",
                            lambda a, b: valore)
    return _con


@pytest.mark.parametrize("vecchio,nuovo,sim", VERE_NON_COPERTE,
                         ids=[a[:30] for a, _, _ in VERE_NON_COPERTE])
def test_un_aggiornamento_in_una_lingua_non_coperta_viene_riconosciuto(
        vecchio, nuovo, sim, con_similarita):
    """Il servizio che prima non c'era: senza il motore queste restavano due
    fatti separati per sempre, perche' la guardia sulla densita' taceva."""
    con_similarita(sim)
    assert _puo_essere_una_evoluzione(nuovo, vecchio) is True, (
        f"aggiornamento non riconosciuto a {sim}: {vecchio} -> {nuovo}")


@pytest.mark.parametrize("vecchio,nuovo,sim", FALSE_NON_COPERTE,
                         ids=[a[:30] for a, _, _ in FALSE_NON_COPERTE])
def test_due_osservazioni_scorrelate_restano_due(vecchio, nuovo, sim,
                                                 con_similarita):
    con_similarita(sim)
    assert _puo_essere_una_evoluzione(nuovo, vecchio) is False, (
        f"scorrelati dichiarati un aggiornamento a {sim}: {vecchio} | {nuovo}")


CASI_DURI = [
    ("Der Korpus enthaelt 6682 Fakten.",
     "Der Korpus hat eine mediane Laenge von 795 Zeichen.", 0.8581),
    ("Der Graph hat 8625 Knoten.",
     "Der Graph hat eine Dichte von 0.42.", 0.9117),
]


@pytest.mark.parametrize("vecchio,nuovo,sim", CASI_DURI,
                         ids=[a[:30] for a, _, _ in CASI_DURI])
def test_stesso_soggetto_grandezza_diversa_non_e_un_aggiornamento(
        vecchio, nuovo, sim, con_similarita):
    """Il caso duro, in una lingua non coperta. Passa per il MARGINE della
    soglia (0.9117 contro 0.93), non perche' il motore capisca che le due
    grandezze sono diverse: se un giorno cade, la causa e' questa e la cura
    non e' spostare la soglia."""
    con_similarita(sim)
    assert _puo_essere_una_evoluzione(nuovo, vecchio) is False


def test_le_lingue_coperte_NON_passano_dal_modello():
    """Il fast-path resta il fast-path: italiano e inglese decidono con le
    liste, senza pagare un encode. E' il comportamento su cui gira tutto il
    corpus, e questo test cade se qualcuno inverte l'ordine."""
    chiamate = []
    reale = vc.similarita_semantica
    vc.similarita_semantica = lambda a, b: (chiamate.append((a, b)),
                                            reale(a, b))[1]
    try:
        assert _puo_essere_una_evoluzione(
            "Il piano annuale costa 200 euro.",
            "Il piano annuale costa 100 euro.") is True
    finally:
        vc.similarita_semantica = reale
    assert not chiamate, (
        f"l'italiano e' passato dal modello: {chiamate}")
