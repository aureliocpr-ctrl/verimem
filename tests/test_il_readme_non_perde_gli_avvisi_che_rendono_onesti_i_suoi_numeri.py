"""README:123-127 e :712 — gli avvisi che rendono onesti i numeri della pagina.

Il README e' la pagina di PyPI. In piu' punti **dichiara i propri limiti invece di
nasconderli**, e questa e' la parte migliore del documento:

    riga 127   «the 2026-07-18 run had 0 numeric escapes … re-running the same
                command on 2026-08-25 reports 4 … **Run it yourself before
                trusting either number.**»
    riga 712   «The competitor column was measured against mem0 2.0.4 … **A newer
                mem0 may have fixed any of these — re-run the probe before
                quoting the row.**»

🔑 IL DIFETTO CHE QUESTO PRESIDIO PREVIENE — e non e' un difetto del prodotto, e'
una regressione EDITORIALE. Un avviso cosi' **sembra una debolezza**: chi ripulisce
la pagina per renderla piu' vendibile toglie prima quelli. Ma togliere l'avviso
**non toglie l'ambiguita'**: lascia due numeri discordanti senza la riga che dice
al lettore quale credere — cioe' peggiora la pagina fingendo di migliorarla.

⇒ Il presidio non chiede che i numeri siano d'accordo (non lo sono, ed e' un fatto
misurato che il README riporta). Chiede che **finche' l'ambiguita' c'e', ci sia
anche il suo avviso**. Se un giorno i due numeri vengono riconciliati davvero,
questo test lo dice e va riscritto — non passa in silenzio.

🆕 **TERZA COPPIA, aggiunta lo stesso giorno — README:703.** La riga
dell'astensione e' quella in cui il prodotto **si toglie da solo il numero da
vetrina**: pubblica un **1.000** e subito dopo scrive che *«un 1.000 da solo non
distingue "si astiene quando deve" da "si astiene sempre", quindi le due meta'
stanno insieme»*. E infatti porta anche l'altra meta' (0.20 contro 0.30 del
plain-RAG). ⇒ Un 1.000 citato **senza** la sua critica torna a essere marketing,
e il primo a poterlo fare siamo noi.

📌 Le coppie stanno in UNA tabella e non in tre test: quando ne trovo un'altra si
aggiunge una riga. **Zero copie** e' una casella della DoD, non uno stile.

Presidio: Product Owner, 12/09/2026, sul README di `origin/main`.
⚠️ LIMITE DICHIARATO: **non eseguito da chi lo ha scritto** (sono in sola lettura
oggi). Atteso: **5 passed** (3 coppie + la quarta registrata + il controllo).
"""

from __future__ import annotations

from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
README = RADICE / "README.md"

#: (nome, [frammenti dell'ambiguita'], avviso che DEVE accompagnarla)
COPPIE = [
    pytest.param(
        "README:123-127 — la matrice multilingue misurata due volte",
        ["the 2026-07-18 run had 0 numeric escapes", "on 2026-08-25 reports"],
        "Run it yourself before trusting either number",
        id="matrice-multilingue",
    ),
    pytest.param(
        "README:712 — la colonna del concorrente e la sua versione",
        ["The competitor column was measured against"],
        "re-run the probe before quoting the row",
        id="colonna-concorrente",
    ),
    pytest.param(
        "README:703 — l'astensione 1.000, e il prodotto che si toglie da solo il numero",
        ["1.000 across seven consecutive full e2e runs", "it abstains **0.20**"],
        "A 1.000 alone cannot distinguish",
        id="astensione-1000",
    ),
]


@pytest.mark.parametrize(("dove", "ambiguita", "avviso"), COPPIE)
def test_ogni_ambiguita_dichiarata_porta_ancora_il_suo_avviso(dove, ambiguita, avviso):
    testo = README.read_text(encoding="utf-8", errors="replace")

    presenti = [f for f in ambiguita if f in testo]

    # Controllo positivo: se l'ambiguita' non c'e' piu', questo test non sta
    # misurando niente e deve DIRLO. Puo' essere una buona notizia (i numeri sono
    # stati riconciliati) ma va guardata, non incassata in silenzio.
    assert presenti == ambiguita, (
        f"{dove}: la frase che questo presidio sorveglia non e' piu' nel README "
        f"(mancano {[f for f in ambiguita if f not in testo]}). Se i numeri sono "
        "stati riconciliati davvero, riscrivi il test; se la riga e' stata solo "
        "riformulata, aggiorna il frammento. **Non lasciarlo passare cosi'.**"
    )

    assert avviso in testo, (
        f"{dove}: l'ambiguita' e' ancora nella pagina ma l'avviso che la rende "
        f"onesta e' sparito ({avviso!r}). Togliere l'avviso non toglie "
        "l'ambiguita': lascia al lettore due numeri discordanti senza dirgli che "
        "lo sono. Se la pagina e' stata 'ripulita', questa e' la riga da rimettere."
    )


# ── ⚠️ LA QUARTA AMBIGUITA': DICHIARATA, MA SENZA IL SUO AVVISO ─────────
#
# README:165 ha la STESSA forma della 127 — lo stesso comando che a un mese di
# distanza da' un numero diverso — ma non porta l'invito a rieseguire:
#
#   riga 127  «the 2026-07-18 run had 0 numeric escapes … on 2026-08-25 reports 4»
#             + «Run it yourself before trusting either number»            ✅
#   riga 165  «1.8% was the 2026-07-18 run; the same command today reports 5.4%»
#             + (niente)                                                   ❌
#
# 🔑 Non e' una svista di stile: sono DUE misure diverse, dallo stesso giorno di
# riferimento, che il README stesso dichiara instabili. Un lettore che incontra la
# 165 senza l'avviso non sa che quel numero **si muove**, e la 127 gli ha appena
# insegnato che da noi lo si dice.
#
# ⚙️ REGISTRATO, non preteso (regola del 12/09: un test misura e resta). La cura e'
# sei parole sulla riga 165 — e quando arrivano, questo test cade e va GIRATO.

_AMBIGUITA_SENZA_AVVISO = 1  # misurato il 12/09: la 165, e solo lei


def test_quante_ambiguita_dichiarate_restano_senza_il_loro_avviso():
    testo = README.read_text(encoding="utf-8", errors="replace")

    la_165_dichiara = (
        "1.8% was the 2026-07-18 run" in testo
        and "the same command today reports 5.4%" in testo
    )
    assert la_165_dichiara, (
        "README:165 non dichiara piu' che lo stesso comando ha dato 1.8% e 5.4%: "
        "se i due numeri sono stati riconciliati e' una buona notizia, ma va "
        "guardata — non lasciarla passare aggiornando il test."
    )

    # ⚠️ Il suo avviso, se arriva, starà ACCANTO alla frase — non da qualche parte
    # nella pagina: la 127 ne ha gia' uno, e cercarlo in tutto il testo lo
    # troverebbe sempre. E' la lezione di oggi: l'oggetto si cerca dove vive.
    i = testo.index("1.8% was the 2026-07-18 run")
    dintorni = testo[max(0, i - 400) : i + 400]
    INVITI = ("run it yourself", "re-run", "rerun", "reproduce it", "before trusting")
    senza = 0 if any(x in dintorni.lower() for x in INVITI) else 1

    assert senza == _AMBIGUITA_SENZA_AVVISO, (
        f"le ambiguita' dichiarate senza il loro avviso sono {senza}, misurate "
        f"{_AMBIGUITA_SENZA_AVVISO} il 12/09.\n"
        "🟢 Se sono DIMINUITE, la riga 165 ha ricevuto il suo «run it yourself» ⇒ "
        "spostala fra le COPPIE qui sopra e porta questo numero a zero.\n"
        "🔴 Se sono AUMENTATE, un altro numero instabile e' entrato nel README "
        "senza dire che si muove."
    )


def test_CONTROLLO_il_righello_della_prossimita_trova_un_invito_quando_c_e():
    """Il test sopra cerca un'ASSENZA: senza questo, passerebbe anche cieco.

    La riga 127 ha l'invito e sta nella stessa pagina: se il righello non lo
    trova li', il suo «nessun invito» sulla 165 non vuol dire niente.
    """
    testo = README.read_text(encoding="utf-8", errors="replace")
    j = testo.index("the 2026-07-18 run had 0 numeric escapes")
    dintorni = testo[max(0, j - 400) : j + 400].lower()
    INVITI = ("run it yourself", "re-run", "rerun", "reproduce it", "before trusting")
    assert any(x in dintorni for x in INVITI), (
        "il righello non trova l'invito a rieseguire accanto a README:127, dove "
        "c'e': da qui in poi il suo «la 165 non ce l'ha» non e' una misura."
    )
