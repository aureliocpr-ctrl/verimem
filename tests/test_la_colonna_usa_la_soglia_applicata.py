"""`withheld_despite_judge` confrontava 90 mentre il cancello ammette a 40 o 70.

IL DIFETTO, misurato sul corpus il 20/09 (snapshot in sola lettura, quarantinati):

    >= 90    la colonna di oggi                            293
    [70,90)  sopra OGNI cut, sotto la colonna: SENZA NOME    29   <- la zona cieca
    [40,70)  contested_band, categoria gia' dichiarata       99
    <  40    respinto da qualunque cut                      739
    (+ 1691 senza punteggio, mai giudicati: 293+29+99+739+1691 = 2851)

La colonna dice «un layer ha trattenuto NONOSTANTE il giudice». La soglia con
cui lo decide e' `_VERDETTO_VERO = 90.0`, ma il cancello ammette a
`resolve_write_threshold_for(backend)`: **40** con il CE locale, **70** con
claude. Fra la cut applicata e il 90 c'e' una fascia dove il giudice ha detto
si', il fatto e' trattenuto, e la colonna dice `False`.

⚠️ NON si abbassa il 90 a 40 e basta: `contested_band` ([40,70)) esiste e
dichiara una cosa diversa — «l'esito dipendeva dal minuto, non dal testo».
Fonderle cancellerebbe una distinzione che questo prodotto ha gia' pagato. Per
questo la cura ha DUE livelli:

  * dove il giudice e' NOTO (ricevuta, journal, MCP) si usa la cut di QUEL
    backend: e' l'unico posto dove «del giudice che ha giudicato» ha un
    referente;
  * nella vista sul corpus il giudice per-fatto non e' nella riga, quindi si usa
    la piu' ALTA delle due cut (70): sopra 70 il giudice ha detto si' con
    qualunque cut, quindi ogni riga elencata e' certa — lo stesso criterio con
    cui il codice usa 40 per la colonna opposta («il totale e' un limite
    inferiore, mai gonfiato»).

Il caso della prima cella e' quello di un pari, non mio:
`tests/test_una_unita_composta_e_una_cosa_sola.py:114-128` (T105), dove il
commento dichiara «il giudice qui APPROVA (89,4 contro un taglio di 40)».
"""
from __future__ import annotations

import pytest

from verimem.retirement_log import judged_true


def test_sopra_la_soglia_la_colonna_funzionava_GIA_e_deve_restare(tmp_path):
    """IL CONTROLLO POSITIVO dalla porta, e il RED che NON e' qui — misurato.

    Questa scrittura mi era stata indicata come il RED («89,4, oggi False»).
    Eseguita sul tronco `2fd9c34f` SENZA la cura, con `ENGRAM_BAND_LLM=0`::

        grounding_score        : 96.00531768798828    <- non 89,4
        withheld_despite_judge : True                 <- GIA' vero senza la cura
        strati                 : ['L4.2-grandezza']
        evidence_class         : cross_encoder · judge.backend: local

    Il «89,4» sta in un COMMENTO del banco di T105
    (`test_una_unita_composta_e_una_cosa_sola.py:123`) e descriveva quel caso in
    un altro momento: oggi il CE gli da' 96,005 — sopra 90, dove la colonna
    funzionava gia'. ⇒ **Questa cella non e' il RED: e' il controllo che la cura
    non rompa cio' che andava.** Se la cura la facesse cadere, avrei spostato il
    difetto invece di curarlo.

    ⚠️ E IL RED END-TO-END NELLA FASCIA NON STA IN UNA CELLA, di proposito.
    L'esemplare misurato e' della porta CLI (T155, tronco `1974476b`):
    `status=quarantined layers=['L4.1'] grounding_score=85.0
    withheld_despite_judge=False` — 85,0 e' dentro `[70,90)`. Ma quel caso e'
    esattamente quello che la richiesta della notazione scientifica CURA: metterlo
    qui lo renderebbe rosso il giorno che quella entra in main, cioe' creerebbe
    la giuntura fra due richieste che stasera ci e' costata due ore su altre due.
    La logica della fascia e' coperta dalle celle parametrizzate qui sotto, che
    senza la cura sono ROSSE (misurato: 7 failed).
    """
    from verimem.client import Memory

    fonte = "Perizia del 2026-09-01: il capannone 12 misura 400 mq."
    r = Memory(tmp_path / "m.db").add(
        "Il capannone 12 misura 400 metri cubi.", topic="prova/t171", source=fonte)
    strati = [w.get("layer") for w in (r.get("warnings") or [])]
    assert r.get("status") == "quarantined", (
        f"il caso non e' piu' trattenuto: status={r.get('status')} "
        f"g={r.get('grounding_score')} strati={strati}")
    assert "L4.2-grandezza" in strati, (
        f"trattenuto, ma non da chi doveva: strati={strati}")
    assert r.get("withheld_despite_judge") is True, (
        "la colonna ha SMESSO di dirlo su un caso sopra 90, dove funzionava "
        f"prima della cura (g={r.get('grounding_score')}): la cura ha spostato "
        "il difetto invece di curarlo")


@pytest.mark.parametrize("punteggio,backend,atteso", [
    (89.4, "local", True),      # il caso sopra: 89,4 >= 40
    (89.4, "claude", True),     # e anche con l'altra cut: 89,4 >= 70
    (55.0, "local", True),      # CONSEGUENZA DICHIARATA della cut 40
    (55.0, "claude", False),    # ...e la stessa cifra con l'altra cut: NO
    (20.0, "local", False),     # IL NEGATIVO: sotto ogni cut resta False
    (20.0, "claude", False),
])
def test_la_soglia_e_quella_del_giudice_che_ha_giudicato(punteggio, backend, atteso):
    """La cut non e' una: 40 col CE locale, 70 con claude. La colonna deve
    chiedere quella del backend che ha prodotto il punteggio, non una costante."""
    assert judged_true(punteggio, backend=backend) is atteso


def test_senza_backend_la_firma_resta_quella_di_prima():
    """RETROCOMPATIBILE: chi chiama con il solo punteggio ottiene il
    comportamento di oggi (soglia 90). Una firma che cambia sotto i piedi di
    quattro chiamanti e' un difetto, non una cura."""
    assert judged_true(96.0) is True
    assert judged_true(85.0) is False
    assert judged_true(None) is False


def test_un_punteggio_ASSENTE_non_e_mai_giudicato(tmp_path):
    """IL CONTROLLO CHE LA CURA NON DEVE ROMPERE: `None` non e' un verdetto, e
    i 1691 quarantinati senza punteggio non entrano in nessuna colonna."""
    assert judged_true(None, backend="local") is False
    assert judged_true(None, backend="claude") is False
