"""`ok` apre la ricevuta, vale sempre ``True``, e nessuna superficie lo diceva.

MISURATO ATTRAVERSO IL HANDLER `hippo_remember` il 2026-08-30 alle 21:39, store
temporaneo, tre popolazioni::

    caso                            ok      status        quarantined_by  gs
    ammesso (la fonte SOSTIENE)     True    model_claim   None            99.84
    quarantinato dal MOAT           True    quarantined   moat             0.56
    quarantinato da L1 (nudo)       True    quarantined   L1              null

⇒ **`ok` non distingue un fatto ammesso da uno trattenuto.** Nel codice e' una
costante letterale (`mcp_server.py:13532`, `"ok": True,`) senza commento, ed e'
il PRIMO campo della ricevuta.

⚠️ NON E' UN DIFETTO DI COMPORTAMENTO, ed e' la ragione per cui questo file non
tocca il valore: `ok` significa «la chiamata non e' fallita», che e' la
convenzione di un tool MCP. Cambiarlo romperebbe ogni chiamante.

🔑 IL DIFETTO E' CHE NESSUNA SUPERFICIE LO DICEVA. `agent_guide` — le istruzioni
che il server consegna agli agenti nella risposta `initialize` — spiega con cura
`status`, `grounding_score`, `moat`, e di `ok` non parlava affatto (zero
occorrenze prima del 2026-08-30). Un campo chiamato «ok», primo nella lista e
sempre vero, invita alla lettura sbagliata proprio dove il prodotto ha investito
di piu' per essere leggibile — e la lettura sbagliata e' seria: **un fatto
quarantinato E' memorizzato e tenuto FUORI dal recall di default**, quindi chi
si dirama su `ok` tratta «trattenuto» come «accettato».

📌 PERCHE' STAVOLTA TOCCO `agent_guide` avendo scelto DUE VOLTE oggi di non
farlo: le altre due volte era un NUMERO da ri-misurare (`:77`, i chunk orfani) —
lavoro di chi mantiene quella misura. Qui e' una lacuna sulla RICEVUTA, che e'
la superficie MCP: il perimetro di chi scrive questo test.
"""

from __future__ import annotations

from verimem import agent_guide


def _guida() -> str:
    """Il testo che il server consegna davvero, non una costante del test.

    ⚠️ I NOMI SI LEGGONO DAL MODULO, NON SI INDOVINANO. La prima stesura
    cercava ``AGENT_GUIDE`` / ``GUIDE`` / ``INSTRUCTIONS`` — nessuno dei tre
    esiste — e i quattro test cadevano tutti insieme su una guida CURATA: il
    difetto era nel misuratore, e i quattro rossi dicevano «non gliel'ho
    chiesto», non «la cura non c'e'».
    """
    nomi = [n for n in ("VERIMEM_AGENT_GUIDE", "AGENT_GUIDE_FULL")
            if isinstance(getattr(agent_guide, n, None), str)]
    assert nomi, (
        "agent_guide non espone piu' le costanti attese: "
        f"{[n for n in dir(agent_guide) if not n.startswith('__')]}")
    return "\n".join(getattr(agent_guide, n) for n in nomi)


def test_la_guida_nomina_il_campo_ok():
    """IL CUORE: prima del 30/08 la guida non lo nominava affatto."""
    testo = _guida()
    assert "`ok`" in testo, "la guida non nomina mai il campo `ok` della ricevuta"


def test_la_guida_dice_che_ok_non_e_il_verdetto():
    testo = _guida()
    assert "the CALL did not fail" in testo, testo[:600]


def test_la_guida_indirizza_ai_campi_che_rispondono():
    """Dire «non leggere ok» senza dire cosa leggere lascia il lettore dov'era."""
    testo = _guida()
    for campo in ("status", "moat", "quarantined_by"):
        assert campo in testo, f"la guida non indirizza a `{campo}`"


def test_la_guida_distingue_le_due_porte_dei_fatti():
    """«The fact doors … DO NOT abstain» era vero per UNA delle due.

    Misurato il 2026-08-30 alle 23:51, un fatto nello store::

        query                 facts_search        facts_recall
        coperta dallo store   1 hit, score 0.0    1 hit, score 0.857
        mai sentita           0 hits              1 hit, score 0.757

    ⇒ `facts_recall` PROVA l'avvertimento (0.757 su una domanda mai sentita,
    quasi quanto quella coperta). `facts_search` e' LESSICALE: zero parole in
    comune, zero righe. ⚠️ E la lettura sbagliata e' l'OPPOSTO di quella che la
    guida teme: chi vede `[]` da `facts_search` e ricorda che «le porte dei
    fatti non si astengono» conclude che lo store non sappia nulla.

    ⚠️ CONTROLLO che regge nella misura: sulla domanda COPERTA rispondono
    entrambe — nessuna delle due porte e' rotta.
    """
    testo = _guida()
    assert "facts_search` is LEXICAL" in testo or "LEXICAL" in testo, testo[:400]
    assert "0.757" in testo, "manca il numero che prova l'avvertimento"


def test_la_guida_nomina_il_campo_dell_astensione():
    """La promessa dell'astensione c'era, il CAMPO che la porta no.

    Per `grounding_score` la guida nomina il campo esplicitamente — *«it is
    `grounding_score` that carries it»* — e per l'astensione diceva solo che il
    tool «ABSTAINS», lasciando al lettore di indovinare dove leggerlo.
    Misurato il 2026-08-30 alle 23:45, un fatto nello store::

        domanda NEL corpus     abstained: False
        domanda FUORI corpus   abstained: True

    ⇒ La promessa REGGE e il campo esiste: mancava che la guida lo dicesse.
    """
    testo = _guida()
    assert "`abstained`" in testo, testo[:600]


def test_la_guida_dice_DOVE_si_leggono_i_quarantinati():
    """«kept OUT of DEFAULT recall» prometteva un modo non-default e non lo diceva.

    Chi legge quella riga cerca l'argomento che allarga la ricerca, e nella
    stessa guida ne trova due che SEMBRANO quello. Misurato il 2026-08-31 alle
    00:58, uno store con un fatto quarantinato::

        include_legacy=true              0 righe
        min_status=legacy_unverified     0 righe
        verimem_quarantine_log           1 riga, con `reason` e `layers`

    ⇒ I due argomenti riguardano `legacy_unverified`, che e' un ALTRO stato: la
    porta esiste, ma e' un TOOL diverso. 🔑 Una promessa implicita — quel
    «default» — manda a cercare quanto una esplicita, e sbagliare porta qui
    costa piu' che altrove: chi non trova il fatto conclude che non sia stato
    memorizzato, cioe' l'opposto di quello che la riga sopra gli ha appena
    detto.

    ⚠️ Il misuratore ha sbagliato chiave anche qui (quinta volta nella
    stessa notte): il log non porta `entries`/`items`/`rows` ma `quarantined`,
    e la prima lettura dava 0. Le chiavi si LEGGONO.
    """
    testo = _guida()
    assert "quarantine_log" in testo, testo[:600]
    assert "DIFFERENT TOOL" in testo or "different tool" in testo, testo[:600]


def test_la_guida_non_lascia_credere_che_un_argomento_basti():
    """⚠️ LA META' CHE TIENE ONESTA L'ALTRA: nominare la porta giusta senza
    dire che i due argomenti vicini NON servono lascia il lettore a provarli —
    ed e' il percorso che ho fatto io misurando."""
    testo = _guida()
    assert "include_legacy" in testo and "min_status" in testo, testo[:600]


def test_la_guida_dice_che_un_quarantinato_e_memorizzato():
    """⚠️ LA META' CHE RENDE SERIA L'ALTRA: se un quarantinato sparisse, leggere
    `ok` sarebbe innocuo. E' perche' resta MEMORIZZATO e fuori dal recall che la
    lettura sbagliata costa."""
    testo = _guida()
    assert "STORED and kept OUT of default recall" in testo, testo[:600]
