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


@pytest.mark.xfail(
    strict=True,
    reason=(
        "T66 — APERTO, ws7 10/09, misurato leggendo. README:550-553 promette "
        "«ungrounded DASHED red» e in `verimem/webui/graph.js` ci sono ZERO "
        "occorrenze di `dash`: la distinzione e' SOLO di colore, e la coppia e' "
        "verde (rgba(46,107,79,.30)) / rosso (rgba(166,51,31,.28)).\n"
        "NON e' una parola di troppo: il tratteggio promesso sarebbe la "
        "ridondanza di FORMA, l'unica cosa che rende la distinzione leggibile a "
        "chi non separa verde e rosso. Per quell'utente «declared, never hidden» "
        "NON e' mantenuto — gli archi non fondati sono nascosti.\n"
        "LA CURA E' AGGIUNGERE IL TRATTEGGIO, non togliere la parola dal README: "
        "per questo il test chiede la forma e resterebbe rosso anche se il testo "
        "venisse 'curato' cancellando «dashed».\n"
        "`strict=True`: il giorno che il tratteggio c'e', questo passa e obbliga "
        "a togliere l'xfail."
    ),
)
def test_gli_archi_non_fondati_hanno_anche_una_FORMA_diversa(console):  # noqa: F811
    """README:550-553 — «dashed»: la ridondanza che rende la distinzione accessibile."""
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
    assert con_la_forma, (
        "il grafo distingue gli archi non fondati SOLO con il colore "
        f"(verde/rosso) e nessuna differenza di forma, in {sorted(dichiarazioni)}. "
        "README:550-553 promette «ungrounded **dashed** red — declared, never "
        "hidden»: senza il tratteggio, per chi non distingue verde e rosso quegli "
        "archi sono indistinguibili, cioe' nascosti.\n"
        "⚠️ Un tratteggio che stia altrove — in un altro asset, o nello stesso "
        "file ma a cento righe di distanza — NON conta: e' cosi' che questo test "
        "e' passato a vuoto il 12/09, due volte di fila."
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
