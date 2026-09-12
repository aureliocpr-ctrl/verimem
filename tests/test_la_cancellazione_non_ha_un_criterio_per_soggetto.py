"""README:735-737 — «deletion by subject does not exist anywhere».

IL CLAIM, testuale dal README pubblicato:

    - **deletion by subject does not exist anywhere.** "Forget everything about
      this person" is not a tenant scope: unless that person's facts happen to
      sit under their own `user_id`, you are back to one `fact_id` at a time.

E' VERO, verificato leggendo la superficie il 09/09: `hippo_forget_scope`
accetta `user_id`/`agent_id`/`run_id` (multi-tenancy, mem0-parity delete_all) e
nient'altro; l'SDK cancella per `fact_id`. Il README lo dice gia' con
precisione, compresa l'eccezione («unless … their own user_id»).

PERCHE' ALLORA UN TEST, SE IL CLAIM E' VERO.

Perche' e' una **dichiarazione di assenza**, ed e' la forma piu' facile da far
scadere in silenzio: il giorno che qualcuno aggiunge una cancellazione per
soggetto — magari per fare un favore all'utente — il README continua a dire che
non esiste, e chi ci ha fatto affidamento **sulla privacy** non lo scopre da
nessuna parte. Un limite dichiarato e' un debito, e questo lo paga il lettore.

⚠️ E un'assenza NON si prova contando le occorrenze di un nome: si prova
enumerando la superficie ed eseguendo. Cercare la stringa «subject» direbbe
zero anche il giorno in cui esiste `forget_about(person=…)`.

QUINDI QUESTO NON E' UN TEST, E' UN CRICCHETTO. Non tenta di dimostrare che
qualcosa non c'e' — fissa i criteri di cancellazione che oggi esistono e si
accende quando ne compare **uno nuovo**. Allora una persona decide: o il README
va riscritto, o la via nuova non deve esistere. Il test non sceglie: obbliga a
scegliere.

Superficie mappata il 09/09 (23:19-23:33), leggendo:
  SDK  `Memory.delete(fact_id, purge_history=, principal=)`  client.py:3891
       `Memory.forget` = alias di `delete`                   client.py:4153
       `Memory.forget_with_report(fact_id)`                  client.py:4155
  MCP  hippo_forget · hippo_fact_forget · hippo_fact_forget_with_undo ·
       hippo_forget_scope · hippo_forget_with_report
  CLI  `verimem facts forget` · `verimem facts undo`

⚠️ `forget` e' un ALIAS, non un `def`: un presidio che cercasse `def forget` non
lo troverebbe. Qui si CHIAMA la superficie, non si cerca il nome.

ws7 «Iris», 09/09/2026. Misurato con:
`python -m pytest tests/test_la_cancellazione_non_ha_un_criterio_per_soggetto.py -q -p no:randomly`
"""
from __future__ import annotations

import asyncio
import inspect
import re

import pytest

# I criteri con cui il prodotto DICHIARA di saper cancellare. Ogni nome qui
# dentro corrisponde a una riga del README: `fact_id` = «one fact_id at a
# time»; `user_id`/`agent_id`/`run_id` = il tenant scope che il README nomina
# per dire che NON e' un soggetto; `op_id` = la maniglia dell'undo.
CRITERI_DICHIARATI = {
    "fact_id", "fact_ids", "id", "ids",
    "user_id", "agent_id", "run_id",
    "op_id",
    # `episode_id`: aggiunto il 09/09 DOPO che il cricchetto si e' acceso su
    # `hippo_forget`. Classificato prima di spiegarlo: e' una cancellazione per
    # ID, non per soggetto («Delete one episode by id (privacy / GDPR)»), quindi
    # il difetto era nella lista, non nel prodotto. Ma il rosso non era inutile:
    # ha portato alla luce che quella porta non sta nella tabella per porta del
    # README (vedi il test in fondo).
    "episode_id",
}

# Parametri che NON sono criteri di selezione: modificano il COME, non il CHE
# COSA. Un `dry_run` in piu' non tocca la promessa del README.
NON_SONO_CRITERI = {
    "dry_run", "purge_history", "principal", "reason", "confirm", "force",
    "limit", "offset", "hard", "cascade", "note", "ttl_seconds", "undoable",
}

_CANCELLA = re.compile(r"forget|delete|purge|erase|wipe", re.I)


def _tool_di_cancellazione():
    """I tool MCP che cancellano, presi dalla superficie che il server espone.

    Usa `_list_tools_unfiltered`, la stessa via di sette test gia' in casa
    (test_la_quarantena_dice_perche, test_le_etichette_epistemiche_sono_
    collegate, …): una seconda enumerazione divergerebbe dalla prima.
    """
    from verimem import mcp_server

    tutti = asyncio.run(mcp_server._list_tools_unfiltered())
    return [x for x in tutti if _CANCELLA.search(x.name) and "undo" not in x.name]


def _criteri_di(tool) -> set[str]:
    """I nomi con cui quel tool sceglie CHE COSA cancellare."""
    schema = getattr(tool, "inputSchema", None) or {}
    proprieta = set((schema.get("properties") or {}).keys())
    return proprieta - NON_SONO_CRITERI


# ── IL CRICCHETTO ───────────────────────────────────────────────────────────


def test_nessuna_via_di_cancellazione_sceglie_per_SOGGETTO():
    """README:735-737: si cancella per id o per tenant, mai per «persona»."""
    trovati: dict[str, set[str]] = {}
    for tool in _tool_di_cancellazione():
        nuovi = _criteri_di(tool) - CRITERI_DICHIARATI
        if nuovi:
            trovati[tool.name] = nuovi

    assert not trovati, (
        "README:735-737 dichiara che «deletion by subject does not exist "
        "anywhere», e una via di cancellazione ha un criterio che il README non "
        f"conosce: {trovati}.\n"
        "Non e' automaticamente un difetto — puo' essere una capacita' nuova e "
        "voluta. Ma allora la riga del README e' diventata FALSA e va riscritta "
        "nello stesso commit, oppure il criterio nuovo non deve esistere.\n"
        "Se il criterio e' una leva e non una selezione (un `dry_run`), va "
        "aggiunto a NON_SONO_CRITERI qui sopra, con la ragione scritta."
    )


# ── E L'SDK, CHIAMATO E NON CERCATO ─────────────────────────────────────────


def test_la_porta_SDK_cancella_per_fact_id_e_forget_e_un_ALIAS():
    """`Memory.forget` esiste ed e' `delete`; il suo criterio e' un id.

    ⚠️ `forget` non ha un `def`: e' `forget = delete` (client.py:4153). Un
    presidio che cercasse `def forget` nel sorgente direbbe «non esiste» —
    la stessa forma per cui cercare un nome non basta quando c'e' un alias.
    Qui si guarda l'oggetto, non il testo.
    """
    from verimem.client import Memory

    assert Memory.forget is Memory.delete, (
        "`Memory.forget` non e' piu' un alias di `delete`: se sono diventate "
        "due implementazioni, divergeranno — il commento a client.py:4150 lo "
        "dice gia' («Alias e non reimplementazioni … due implementazioni della "
        "stessa operazione divergono»)."
    )

    parametri = set(inspect.signature(Memory.delete).parameters) - {"self"}
    selezione = parametri - NON_SONO_CRITERI
    assert selezione == {"fact_id"}, (
        f"la porta SDK sceglie che cosa cancellare con {selezione}, e il README "
        "alla 735-737 promette «one fact_id at a time»."
    )


# ── I CONTROLLI POSITIVI: due facce, e la seconda puo' smentirmi ────────────


def test_CONTROLLO_l_enumeratore_VEDE_le_cinque_vie_note():
    """Se questo cade, il cricchetto sopra e' verde perche' e' CIECO.

    Un elenco vuoto soddisfa «nessun criterio sconosciuto» alla perfezione.
    """
    nomi = {x.name for x in _tool_di_cancellazione()}
    attesi = {
        "hippo_forget",
        "hippo_fact_forget",
        "hippo_forget_scope",
        "hippo_forget_with_report",
    }
    mancanti = attesi - nomi
    assert not mancanti, (
        f"l'enumeratore non vede {mancanti}: il cricchetto sarebbe verde per "
        f"cecita'. Ne ha visti {len(nomi)}: {sorted(nomi)}"
    )


@pytest.mark.parametrize(
    "proprieta, deve_accendersi",
    [
        ({"fact_id": {}}, False),                    # la via che esiste
        ({"user_id": {}, "dry_run": {}}, False),     # il tenant scope + una leva
        ({"subject": {}}, True),                     # ← la cancellazione per soggetto
        ({"person_name": {}}, True),                 # ← lo stesso con un altro nome
        ({"about_entity": {}}, True),                # ← e con un terzo
    ],
)
def test_CONTROLLO_il_riconoscitore_PRENDE_un_criterio_per_soggetto(proprieta, deve_accendersi):
    """La faccia che puo' smentirmi: saprebbe accorgersene, se ci fosse?

    Senza questo, «nessun criterio sconosciuto» potrebbe voler dire soltanto
    che `_criteri_di` non guarda dove crede di guardare. Qui gli si mette
    davanti una cancellazione per soggetto — quella che il README giura non
    esistere — e si pretende che la veda.
    """

    class _ToolFinto:
        name = "hippo_forget_qualcosa"
        inputSchema = {"type": "object", "properties": proprieta}

    sconosciuti = _criteri_di(_ToolFinto()) - CRITERI_DICHIARATI
    assert bool(sconosciuti) is deve_accendersi, (
        f"con le proprieta' {set(proprieta)} il riconoscitore "
        f"{'doveva' if deve_accendersi else 'non doveva'} accendersi, "
        f"e ha reso {sconosciuti}"
    )


# ── E IL DIFETTO CHE IL CRICCHETTO HA PORTATO A GALLA ───────────────────────


README_PORTE_ELENCATE = {
    "Memory.forget", "Memory.delete",
    "hippo_fact_forget",
    "verimem facts forget",
    "hippo_fact_forget_with_undo",
    "hippo_forget_scope",
}


@pytest.mark.xfail(
    strict=True,
    reason=(
        "APERTO — ws7, 09/09. La tabella per porta del README (righe 745-751) si "
        "presenta come completa: «What deletion looks like depends on which door "
        "you use, so here it is per door», «Five doors delete». Ne elenca cinque, "
        "e il server ne espone almeno due che non ci sono: `hippo_forget` (che "
        "cancella un EPISODIO: «Delete one episode by id (privacy / GDPR)») e "
        "`hippo_forget_with_report`. Il paragrafo dichiara di esistere proprio "
        "per la cancellazione GDPR — «an agent memory is exactly where personal "
        "data ends up» — quindi una porta non censita e' un buco nella promessa "
        "che quel paragrafo fa. NON curo la tabella qui: aggiungere due righe "
        "senza MISURARE dove resta il testo dopo quelle due porte metterebbe una "
        "riga non misurata in una tabella che dichiara misure, che e' il difetto "
        "denunciato. La cura e' la misura, e va fatta con l'owner della porta. "
        "`strict=True`: il giorno che la tabella e' completa questo test PASSA e "
        "il rosso strict obbliga a togliere l'xfail invece di lasciarlo marcire."
    ),
)
def test_la_tabella_per_porta_del_readme_elenca_TUTTE_le_porte():
    """README:743-751 — «here it is per door» dev'essere per OGNI porta."""
    esposte = {x.name for x in _tool_di_cancellazione()}
    non_censite = esposte - README_PORTE_ELENCATE
    assert not non_censite, (
        "porte di cancellazione che il prodotto espone e che la tabella del "
        f"README non elenca: {sorted(non_censite)}"
    )
