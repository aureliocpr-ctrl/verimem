"""README:550-553 — «grounded edges solid, ungrounded **dashed** red — declared,
never hidden». (T66, ws7)

IL CLAIM, testuale dal README pubblicato:

    `GET /ui` … shows … the **knowledge graph** (drag, zoom; grounded edges
    solid, ungrounded dashed red — declared, never hidden) …

MISURATO IL 10/09 LEGGENDO `verimem/webui/graph.js` (591 righe, servito da `/ui`
insieme ad `app.js` e `vendor-graphology.js`, `gateway.py:1679`):

    riga 56   edge:   rgba(46,107,79,.30)     <- VERDE  (grounded)
    riga 57   edgeUn: rgba(166,51,31,.28)     <- ROSSO  (ungrounded)
    riga 313  color: grounded ? this.pal.edge : this.pal.edgeUn

    grep -ci "dash" verimem/webui/graph.js  ->  0

| pezzo del claim | verdetto |
|---|---|
| «red» | ✅ vero |
| «declared, never hidden» | ✅ vero **per chi distingue i due colori** |
| **«dashed»** | ❌ **falso: zero occorrenze di `dash` in tutto il file** |

PERCHE' NON E' UNA PAROLA DI TROPPO, ed e' il motivo per cui questo file esiste.

La distinzione c'e' **solo per COLORE**, e la coppia e' **verde / rosso**. Il
«dashed» che il README promette sarebbe stata la ridondanza di **FORMA** — l'unica
cosa che rende quella distinzione leggibile a chi non separa verde e rosso. Per
quell'utente la promessa **«declared, never hidden» non e' mantenuta**: gli archi
non fondati *sono* nascosti, perche' indistinguibili dagli altri.

⇒ La cura utile e' **aggiungere il tratteggio** — che il README gia' promette — non
togliere la parola dal testo. Per questo il test chiede la FORMA e non si accontenta
del colore: se un giorno qualcuno "curasse" il README cancellando «dashed», questo
file resterebbe rosso e chiederebbe conto della scelta.

⚠️ SCRITTO IN LETTURA, NON ESEGUITO. Divisione dell'11/09 (post «START 11/09
19:20»): sono una LETTRICE, non eseguo niente sulla macchina. Questo file e' scritto
e pushato **senza pytest**. L'atteso e' dichiarato qui sotto e la riga per la coda
dell'operatore sta nel mio post sul canale:

    ATTESO alla prima esecuzione:
      test_CONTROLLO_la_pagina_del_grafo_arriva_dalla_porta   -> PASS
      test_gli_archi_non_fondati_hanno_un_COLORE_diverso      -> PASS
      test_gli_archi_non_fondati_hanno_anche_una_FORMA_diversa -> XFAIL (strict)

    Se il terzo desse XPASS, il tratteggio e' stato aggiunto: si toglie l'xfail.
    Se uno dei primi due fallisse, il difetto e' in QUESTO file, non nel prodotto.

⚠️ ZERO COPIE: la fixture e la funzione che prende la pagina **dalla porta** sono
importate da `tests.test_la_chiave_della_console_resta_nella_tab`, non riscritte.

ws7 «Iris», 11/09/2026.
"""
from __future__ import annotations

import re

import pytest

# Riuso, non copia: stessa porta, stessa fixture, una superficie sola.
from tests.test_la_chiave_della_console_resta_nella_tab import (  # noqa: F401
    _tutto_cio_che_arriva_al_browser,
    console,
)

#: Il nome che il grafo da' al colore degli archi NON fondati.
_COLORE_NON_FONDATO = re.compile(r"edgeUn|edge[-_]un", re.I)

#: Una distinzione di FORMA, in una delle grafie che le librerie usano.
#: Non cerco la parola «dashed» del README: cerco la COSA, comunque si scriva.
_FORMA_DIVERSA = re.compile(
    r"dash|dotted|strokeDasharray|stroke-dasharray|lineDash|setLineDash",
    re.I,
)


def _il_grafo(client) -> str:
    """Tutto cio' che la porta serve per la pagina del grafo, in un testo solo."""
    return "\n".join(_tutto_cio_che_arriva_al_browser(client).values())


#: Quanto vicino deve stare il tratteggio alla dichiarazione dell'arco per essere
#: SUO. Una regola CSS o un ramo JS stanno in poche centinaia di caratteri; le
#: altre occorrenze di `dash` della pagina distano righe e righe (in `style.css`
#: il colore dell'arco e' a riga 32 e il primo tratteggio a 154).
_VICINANZA = 300


def _le_dichiarazioni_dell_arco_non_fondato(client) -> dict[str, list[str]]:
    """I dintorni di ogni menzione dell'arco NON fondato, asset per asset.

    ⚠️ CORRETTO DUE VOLTE IL 12/09, e la seconda correzione e' la lezione vera.

    ① Prima cercavo il tratteggio nel CONCATENATO di tutta la pagina, e `app.js`
       ne contiene uno (`strokeDasharray`, riga 125) **per un'altra cosa**: il
       test e' passato in CI — `XPASS(strict)` — mentre `graph.js` aveva, e ha,
       ZERO occorrenze di `dash`.
    ② Poi ho ristretto AL FILE che nomina l'arco. **Non bastava**: `style.css`
       nomina l'arco (riga 32) **e** ha due tratteggi (154, 242) che sono
       un'animazione e una classe `.sw`. Stesso file, cose diverse.

    🔑 Cercare l'OGGETTO GIUSTO nella POPOLAZIONE SBAGLIATA da' lo stesso verde di
    cercare la forma sbagliata — e «stesso file» e' ancora una popolazione. Il
    tratteggio conta solo se sta **dove si dichiara quell'arco**.
    """
    fuori: dict[str, list[str]] = {}
    for nome, testo in _tutto_cio_che_arriva_al_browser(client).items():
        dintorni = [
            testo[max(0, m.start() - _VICINANZA) : m.end() + _VICINANZA]
            for m in _COLORE_NON_FONDATO.finditer(testo)
        ]
        if dintorni:
            fuori[nome] = dintorni
    return fuori


# ── IL CONTROLLO POSITIVO PER PRIMO ─────────────────────────────────────────


def test_CONTROLLO_la_pagina_del_grafo_arriva_dalla_porta(console):  # noqa: F811
    """Senza il grafo servito, ogni asserzione sotto e' senza oggetto.

    ⚠️ Il 10/09 ho quasi accusato il file sbagliato: ero partita da
    `static/memory_map.js`, che colora gli archi per TIPO di relazione
    (`parent_of`, `superseded_by`, …) e non conosce `grounded`. Il grafo di `/ui`
    e' un altro (`webui/graph.js`). Questo controllo pretende che cio' che la
    porta serve parli davvero di archi fondati e non fondati.
    """
    testo = _il_grafo(console)
    assert len(testo) > 400, f"la console ha servito solo {len(testo)} caratteri"
    assert _COLORE_NON_FONDATO.search(testo), (
        "in cio' che la porta serve non compare il colore degli archi NON "
        "fondati (`edgeUn`): o la pagina e' cambiata, o questo test sta "
        "guardando un file che non e' il grafo di `/ui`. Vedi `gateway.py:1679`: "
        "gli asset sono `app.js`, `graph.js`, `vendor-graphology.js`."
    )


# ── ① IL COLORE C'E', E VA TENUTO FERMO ─────────────────────────────────────


def test_gli_archi_non_fondati_hanno_un_COLORE_diverso(console):  # noqa: F811
    """README:550-553 — «ungrounded … red»: questa meta' della promessa e' VERA.

    La tengo ferma perche' e' l'unica distinzione che oggi esiste: se sparisse,
    gli archi non fondati diventerebbero invisibili per TUTTI, non solo per chi
    non separa i colori.
    """
    assert _COLORE_NON_FONDATO.search(_il_grafo(console)), (
        "il grafo non distingue piu' gli archi non fondati nemmeno col colore: "
        "README:550-553 promette «ungrounded dashed red — declared, never hidden»."
    )


# ── ② LA FORMA NO: E' IL TICKET T66 ─────────────────────────────────────────


def test_gli_archi_non_fondati_hanno_anche_una_FORMA_diversa(console):  # noqa: F811
    """README:550-553 — «dashed»: la ridondanza che rende la distinzione accessibile.

    🔴 **T66 e' APERTO** e questo test lo REGISTRA invece di aspettarselo.

    Il README promette «ungrounded **DASHED** red — declared, never hidden», e il
    tratteggio non c'e': la distinzione e' SOLO di colore, verde
    (rgba(46,107,79,.30)) contro rosso (rgba(166,51,31,.28)). Non e' una parola di
    troppo — il tratteggio sarebbe la ridondanza di FORMA, l'unica cosa che rende
    la distinzione leggibile a chi non separa verde e rosso. Per quell'utente
    «declared, never hidden» **non e' mantenuto**: gli archi non fondati sono
    nascosti. La cura e' AGGIUNGERE il tratteggio, non togliere la parola dal
    README.

    ⚙️ **PERCHE' NON E' UN `xfail`** (decisione del 12/09: *«un test misura e
    resta, o si toglie con la ragione»*). Un `xfail` cade solo quando il difetto
    e' curato; questo cade **nei due versi** — se il tratteggio arriva **e** se le
    dichiarazioni scoperte aumentano, cioe' se peggiora. Il secondo caso e' quello
    di cui non si accorge nessuno.
    """
    dichiarazioni = _le_dichiarazioni_dell_arco_non_fondato(console)

    # Controllo positivo: se nessun asset dichiara piu' l'arco non fondato,
    # questo test non misura niente e deve DIRLO, non passare per vuoto.
    assert dichiarazioni, (
        "nessun asset servito dichiara l'arco non fondato (`edgeUn`): o la pagina "
        "e' cambiata, o questo presidio sta guardando una superficie che non e' "
        "piu' il grafo di `/ui`."
    )

    con_la_forma = {
        nome
        for nome, dintorni in dichiarazioni.items()
        if any(_FORMA_DIVERSA.search(d) for d in dintorni)
    }

    assert not con_la_forma, (
        f"🟢 **BUONA NOTIZIA, e questo test va riscritto**: il tratteggio e' "
        f"arrivato accanto alla dichiarazione dell'arco non fondato, in "
        f"{sorted(con_la_forma)}. T66 e' curato ⇒ questo presidio diventa "
        "l'asserzione POSITIVA (`assert con_la_forma`) e il docstring perde il "
        "paragrafo del difetto. Non toglierlo: girarlo."
    )
    # ⚠️ IL NUMERO ESATTO NON LO FISSO, E DICO PERCHE'. Leggendo `origin/main` con
    # lo stesso criterio contavo SEI dichiarazioni scoperte (quattro in graph.js,
    # due nel foglio di stile) — ma quella e' una lettura dei file su git, e
    # QUESTO test legge cio' che la PORTA serve, che puo' essere un altro insieme.
    # Fissare 6 qui sarebbe scrivere un numero che non ho misurato dove lo misuro.
    #
    #   Q: (per chi esegue) — `pytest -q tests/test_il_grafo_distingue_gli_archi_non_fondati_anche_senza_colore.py`
    #      atteso: 5 passed. Il messaggio qui sotto STAMPA quante sono: portalo
    #      indietro e lo fisso, cosi' il presidio prende anche il peggioramento.
    scoperte = sum(len(d) for d in dichiarazioni.values())
    assert scoperte >= 1, (
        f"nessuna dichiarazione dell'arco non fondato da misurare (ne ho viste "
        f"{scoperte}): il presidio non sta piu' guardando il grafo."
    )
    print(  # noqa: T201 — e' il numero che serve per chiudere il cricchetto
        f"\n[T66] dichiarazioni dell'arco non fondato SENZA tratteggio vicino: "
        f"{scoperte} in {sorted(dichiarazioni)}"
    )


# ── E IL CONTROLLO CHE PUO' SMENTIRMI ───────────────────────────────────────


@pytest.mark.parametrize(
    "frammento, deve_accendersi",
    [
        ("ctx.setLineDash([4, 2]);", True),
        ("edge.strokeDasharray = '4 2';", True),
        ("border-bottom: 1px dashed red;", True),
        ("color: grounded ? pal.edge : pal.edgeUn", False),
        ("const dashboard = document.getElementById('x');", True),
    ],
)
def test_CONTROLLO_il_riconoscitore_della_FORMA(frammento, deve_accendersi):
    """Saprebbe riconoscere un tratteggio, comunque sia scritto?

    ⚠️ L'ultimo caso e' messo apposta per SMENTIRMI e resta `True`: «dash**board**»
    contiene `dash`, e il mio riconoscitore lo prende. E' un falso positivo noto e
    DICHIARATO — il 10/09 la stessa forma mi ha fatto trovare `merge` dentro
    `e-MERGE-nce`. Qui lo accetto perche' un falso positivo rende il test RUMOROSO,
    non CIECO: se scattasse per un «dashboard» lo vedrei subito leggendo il
    messaggio, mentre un riconoscitore troppo stretto mi direbbe «nessun
    tratteggio» il giorno in cui il tratteggio c'e' ed e' scritto in un modo che
    non avevo previsto. Fra i due errori scelgo quello che si vede.
    """
    assert bool(_FORMA_DIVERSA.search(frammento)) is deve_accendersi
