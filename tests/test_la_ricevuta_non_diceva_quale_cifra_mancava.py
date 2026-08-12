"""«quarantined id=f014eeafa03a topic=t» — e basta. Fermato, senza sapere perché.

IL DIFETTO, isolato da ws1 con la formulazione che lo rende curabile: *«non è un
gate severo — moat e L4.1 chiedono cose DIVERSE (la fonte sostiene il fatto? /
ogni cifra sta nella fonte?) e chi scrive MISURE li attiva entrambi. Cura più
piccola: dire QUALE cifra non ha trovato»*. Verificato da lui su 16 casi su 16.

MISURATO DALLA PORTA, prima di scrivere::

    il layer SA quale valore manca:   [(40.0, …)]
    l'SDK lo DICE:  reason «il claim afferma un valore che la fonte non
                    contiene: 40 pezzo», matched_text '40 pezzo', più un advice
    la CLI stampava: «quarantined id=f014eeafa03a topic=t»    ← e nient'altro

⇒ Il motivo esisteva già nel verdetto e non arrivava alla porta dell'umano.
Nulla da inventare: si stampa.

🔑 E LA RAGIONE PER CUI IL CASO SFUGGIVA sta nel come la ricevuta decideva cosa
dire: **guardava solo il punteggio**. Con moat 95,5 e taglio 40 il ramo «bocciato
dal giudice» non scatta — ma il fatto è quarantinato da ``L4.1``, che la ricevuta
non guardava affatto. Decidere in base al solo punteggio nasconde proprio il caso
in cui le due voci si contraddicono, cioè quello in cui l'utente ha più bisogno
di sapere chi ha parlato.

⚠️ UNDICESIMA VOLTA CHE IL BANCO MISURA SÉ STESSO, e vale la pena scriverlo: la
mia prima misura cercava ``getattr(r, "warnings")`` su un valore che è un
**dict**, e concludeva che il prodotto non dicesse niente. Il prodotto lo diceva.
Se avessi «curato» quella conclusione avrei aggiunto un messaggio che c'era già.
"""
from __future__ import annotations

import os
import subprocess
import sys

CLAIM = "L'ordine 77 conteneva 40 pezzi."
FONTE = "Verbale: e' stato consegnato l'ordine 77. Ha partecipato Bianchi."
VERO = "Il magazzino di Verona contiene 480 pallet."
FONTE_VERA = "Inventario: magazzino Verona, 480 pallet a scaffale."


def _remember(tmp_path, claim, source):
    # ⚠️ TUTTI E TRE gli alias, non due: il terzo verrebbe EREDITATO da
    # os.environ (la fixture autouse lo pinna a un'altra tmp) e i tre
    # disaccorderebbero. Il prodotto allora emette `RuntimeWarning: DATA_DIR
    # aliases disagree` proprio dentro l'output che gli assert qui sotto
    # leggono — rumore che maschera il motivo vero di un rosso.
    env = dict(os.environ, HIPPO_DATA_DIR=str(tmp_path),
               ENGRAM_DATA_DIR=str(tmp_path),
               VERIMEM_DATA_DIR=str(tmp_path))
    r = subprocess.run(
        [sys.executable, "-m", "verimem.cli", "remember", claim,
         "--topic", "t", "--source", source],
        capture_output=True, text=True, env=env, timeout=900)
    # ⚠️ `subprocess` puo' rendere `None` invece di stringa vuota su uno dei due
    # canali, e la somma esplode PRIMA di arrivare all'assert: in CI si legge
    # `TypeError: can only concatenate str (not "NoneType") to str` al posto del
    # motivo per cui il test e' rosso. Il difetto vero resta nascosto sotto.
    # 🔑 NON e' cosmesi difensiva: qui il fallimento del banco MASCHERA il
    # fallimento che il banco esiste per mostrare.
    return (r.stdout or "") + (r.stderr or "")


def test_la_ricevuta_dice_QUALE_valore_non_ha_trovato(tmp_path):
    """IL CUORE: chi viene fermato deve sapere perché. «quarantined id=…» da solo
    manda a indovinare, e il motivo era già calcolato."""
    out = _remember(tmp_path, CLAIM, FONTE)
    assert "quarantined" in out
    assert "40" in out, f"la cifra mancante non compare nella ricevuta:\n{out}"
    assert "L4.1" in out, "non si sa QUALE voce del gate ha parlato"


def test_la_ricevuta_dice_anche_COSA_FARE(tmp_path):
    """Un rifiuto senza rimedio è un muro. Il consiglio esisteva già nel
    verdetto: «correggi il valore, oppure passa la fonte che lo contiene»."""
    out = _remember(tmp_path, CLAIM, FONTE)
    assert "correggi" in out.lower() or "fonte che lo contiene" in out.lower()


def test_CONTROLLO_POSITIVO_un_fatto_ammesso_non_riceve_rumore(tmp_path):
    """⚠️ LA POPOLAZIONE OPPOSTA. Un avviso che compare anche quando tutto va
    bene è rumore: chi salva cento fatti veri leggerebbe cento spiegazioni di
    niente, e smetterebbe di leggerle proprio quando servono."""
    out = _remember(tmp_path, VERO, FONTE_VERA)
    assert "admitted" in out
    assert "L4.1" not in out
    assert "non contiene" not in out


def test_il_caso_che_sfuggiva_moat_a_favore_e_layer_contrario(tmp_path):
    """🔑 IL CASO CHE DÀ SENSO ALLA CURA: il giudice approva (95,5 su un taglio
    di 40) e il fatto è quarantinato lo stesso, da un controllo diverso.

    È il caso in cui le due voci del gate si contraddicono — quello che ws1 ha
    trovato in 16 casi su 16 fra i suoi quarantinati — e la ricevuta, decidendo
    cosa dire in base al solo punteggio, era proprio lì che taceva.
    """
    out = _remember(tmp_path, CLAIM, FONTE)
    assert "quarantined" in out
    # il punteggio del giudice è ALTO e il fatto è fermato lo stesso:
    # entrambe le informazioni devono raggiungere chi legge
    assert "L4.1" in out and "40" in out


# ── L'ALTRA VOCE: quella che era d'accordo ──────────────────────────────────
# Il gate ha DUE voci e chiedono cose diverse. La cura sopra fa dire quale ha
# bocciato; questa fa dire che l'altra aveva approvato.
#
# Un fatto respinto 1-a-1 non è un fatto respinto 2-a-0, e per chi scrive è la
# differenza fra «riformula la frase» e «hai sbagliato UN numero».

def test_la_ricevuta_dice_che_il_giudice_era_D_ACCORDO(tmp_path):
    """IL CUORE: il claim è fermato da un controllo di dettaglio, ma la fonte lo
    sostiene — grounding 94,6 su un taglio di 40. Chi legge deve saperlo,
    altrimenti riscrive tutta la frase quando bastava correggere una cifra."""
    out = _remember(tmp_path, CLAIM, FONTE)
    assert "quarantined" in out
    assert "giudice era d'accordo" in out or "giudice era d" in out
    assert "taglio" in out


def test_CONTROLLO_POSITIVO_il_fatto_ammesso_non_riceve_la_seconda_voce(tmp_path):
    """⚠️ LA POPOLAZIONE OPPOSTA: se il fatto passa, non c'è nessun disaccordo da
    spiegare. Due righe in più su ogni salvataggio riuscito sono rumore, e il
    rumore fa smettere di leggere proprio quando conta."""
    out = _remember(tmp_path, VERO, FONTE_VERA)
    assert "admitted" in out
    assert "giudice era d" not in out
