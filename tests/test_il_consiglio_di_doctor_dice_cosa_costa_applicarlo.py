"""Il consiglio di `trust-rank-coverage` chiedeva una cura che PEGGIORA.

IL REPERTO E' DI @ws6, misurato il 2026-08-30 alle 21:55 sullo store di sviluppo
in sola lettura, e questo file lo porta dove la gente lo legge — dentro il
consiglio stesso.

`doctor` segnalava (correttamente) che alcuni fatti vivi hanno uno `status`
senza rango di fiducia, e concludeva: *«normalise those statuses, or add them to
`_STATUS_RANK`»*. La riga finale era gia' onesta — *«until then nothing is lost,
only left for human judgement»* — ma **il consiglio non diceva cosa costa
seguirlo**.

    contraddizioni registrate 93622 · irrisolte 93263 = 99,6%
    campione di 4000 coppie irrisolte, righello Jaccard:
      numeric_clash  3193 coppie   93,7% sotto 0,15   mediana 0,039
      boolean_clash   807 coppie   99,1% sotto 0,15   mediana 0,031
    ⇒ due fatti «in contraddizione» condividono il 4% delle parole
    ⇒ normalizzare renderebbe ritirabili 998 fatti DISTINTI

⚠️ E la memoria di casa lo diceva gia', da un'altra strada: *«otto criteri su
otto caduti per separare catalogo da conflitto; contraddizioni registrate ~95%
rumore»*. ⇒ **Il mancato rango non e' una lacuna: e' cio' che oggi PROTEGGE quei
fatti dal ritiro automatico.**

🔑 LA FORMA DEL DIFETTO, ed e' quella di tutta la giornata: una superficie che
DICE il vero e OMETTE la conseguenza. Il segnale e' esatto (quei fatti esistono
davvero); il rimedio invitava a spegnere una protezione, e chi lo legge non
aveva modo di saperlo.

⚠️ IL NUMERO E' DI UN CORPUS, NON DEL PRODOTTO, e per questo il testo nuovo
porta **la data, la popolazione e il campione** e dice esplicitamente *«your
corpus may differ; run the same check on it»*. Un numero di casa spacciato per
proprieta' generale sarebbe lo stesso difetto in un'altra forma.
"""

from __future__ import annotations

import inspect

from verimem import doctor as _doctor


def _sorgente_del_consiglio() -> str:
    """Il modulo intero: il consiglio e' costruito inline nel check."""
    return inspect.getsource(_doctor)


def test_il_consiglio_avverte_prima_di_normalizzare():
    """IL CUORE: chi legge deve sapere che sta per spegnere una protezione."""
    testo = _sorgente_del_consiglio()
    assert "MEASURE BEFORE YOU NORMALISE" in testo, (
        "il consiglio non avverte che normalizzare rende quei fatti "
        "auto-ritirabili")


def test_il_consiglio_porta_la_misura_con_la_sua_data():
    """Un avvertimento senza numero e' un'opinione."""
    testo = _sorgente_del_consiglio()
    assert "2026-08-30" in testo, "l'avvertimento non porta la data della misura"
    assert "93.7%" in testo and "99.1%" in testo, testo[:200]
    assert "4000 sampled" in testo, "manca la popolazione campionata"


def test_il_consiglio_dichiara_che_il_numero_e_di_UN_corpus():
    """⚠️ LA META' CHE EVITA DI RIPETERE IL DIFETTO IN UN'ALTRA FORMA: un numero
    di casa presentato come proprieta' del prodotto sarebbe una promessa non
    misurata sul corpus di chi legge."""
    testo = _sorgente_del_consiglio()
    assert "corpus may differ" in testo, testo[:200]


def test_resta_la_riga_che_dice_che_nulla_e_perso():
    """⚠️ LA POPOLAZIONE OPPOSTA: rendere il consiglio piu' prudente non deve
    trasformarlo in un allarme. Lo stato attuale NON perde nulla, e la riga che
    lo dice c'era prima e deve restare."""
    testo = _sorgente_del_consiglio()
    assert "nothing is lost" in testo, testo[:200]
