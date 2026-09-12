"""README:610-615 — le tre porte, la «via sottile» e i 28 strumenti che dicono no.

IL CLAIM, testuale dal README pubblicato:

    With those set, the Python SDK (`open_memory()`), the CLI (`verimem remember`
    / `recall`), and the MCP tools (`hippo_remember` / `hippo_facts_recall` /
    `hippo_facts_search`) all route through the shared server … If the server is
    unreachable, each falls back to its own embedded store (fail-soft, never a
    crash).

LO STATO, verificato il 10/09 leggendo i presidi gia' in casa:

  SDK  `test_open_memory_falls_back_embedded_when_server_down`  test_remote_memory.py:155
  CLI  `test_cli_remember_and_recall_use_open_memory`           test_remote_memory.py:180
  MCP  `test_hippo_remember_falls_back_local_on_remote_error`   test_mcp_thin.py:266

Le tre porte del claim sono coperte. ⚠️ Ho creduto il contrario per un minuto:
`grep "^def test"` su `test_mcp_thin.py` rendeva **2** test su 279 righe, perche'
`async def test_…` comincia con `async`. Il conto vero e' **14**. Un vuoto da
criterio incompleto e' identico a un vuoto vero, e «2 test in 279 righe» era il
segnale da non ignorare.

QUINDI QUESTO FILE NON RIPETE QUEI TRE. Presidia la cosa che nessuno tiene ferma:
**la lista degli strumenti che in thin mode NON fanno fallback e RIFIUTANO.**

Il prodotto ha una regola deliberata, e la scrive (`mcp_server.py:244` e `:260`):

    «Every OTHER fact-reading tool still hits the LOCAL store — which, for a
    session that lives behind a shared server, is empty. Returning that as a
    normal answer reports "no facts" as if it were the complete corpus: a silent
    wrong answer, strictly worse than an error.»

    «A forget that silently forgets nothing is the most dangerous no-op here.
    Found by sweeping the mutating tools AFTER the first version of this guard
    covered only readers.»

Due cose da quel commento:
  ① il prodotto fa una cosa **migliore** di quella che il README promette. Letto
    alla lettera, «falls back to its own embedded store» descrive proprio il
    comportamento che il codice ha deciso di NON avere. Di solito il README
    promette piu' del prodotto; qui il prodotto fa piu' di quanto il README
    racconta, e una buona decisione di progetto resta invisibile all'utente.
  ② **quella lista e' gia' stata incompleta una volta**: la prima versione
    copriva solo i lettori. Una lista scritta a mano che ha gia' mancato un
    intero lato e' esattamente cio' che merita un cricchetto, non un ricordo.

ws7 «Iris», 10/09/2026. Misurato con:
`python -m pytest tests/test_la_via_sottile_copre_cio_che_il_readme_promette.py -q -p no:randomly`
"""
from __future__ import annotations

import re

import pytest

from verimem import mcp_server

#: I tre che il README nomina come instradati al server: DEVONO avere la via
#: sottile, cioe' NON stare in nessuna delle due liste di rifiuto.
README_HANNO_LA_VIA_SOTTILE = (
    "hippo_remember",
    "hippo_facts_recall",
    "hippo_facts_search",
)

#: Muta il CORPUS DEI FATTI: se un tool con questa forma non rifiuta in thin
#: mode, opera sullo store locale vuoto e riferisce un esito che nel corpus
#: condiviso non e' avvenuto.
#:
#: ⚠️ I CONFINI, e il posto dove quasi tutti li sbagliano DUE VOLTE.
#: ① la prima versione scriveva `merge` senza confini e prendeva
#:   `hippo_e-MERGE-nce_pipeline_status`, che e' di sola lettura: prendeva TROPPO.
#: ② la seconda scriveva `\bforget\b` e NON trovava `hippo_fact_forget`, perche'
#:   in regex `_` e' un carattere di parola e fra `_` e `f` non c'e' nessun
#:   confine: prendeva TROPPO POCO, e il controllo positivo l'ha visto subito.
#: Percio' il nome si NORMALIZZA (gli `_` diventano spazi) e poi si cercano i
#: verbi ai confini veri. Un `\b` scritto senza sapere che cosa conta come
#: parola e' un filtro che non filtra.
_MUTA = re.compile(
    r"\b(?:forget|supersede|merge|prune|decay|resolve|apply|priority|restore)\b",
    re.I,
)


def _a_parole(nome: str) -> str:
    return nome.replace("_", " ").replace("-", " ")

#: ⚠️ E IL NOME NON BASTA: quattro dei cinque «scoperti» della prima versione
#: erano miei, e la ragione era sempre la stessa — giudicavo dal NOME mentre la
#: DESCRIZIONE del tool diceva la verita' a chiare lettere:
#:
#:   hippo_decay_simulate            «read-only preview of decay-prune candidates»
#:   hippo_emergence_pipeline_status «aggregate observability snapshot … Read-only»
#:   hippo_apply_recommendations     promuove/ritira SKILL, non fatti
#:   hippo_forget                    cancella EPISODI (il prodotto li esclude apposta)
#:
#: E' la stessa lezione di sempre in casa: cercare un nome non discrimina, serve
#: la struttura. Qui la struttura e' il testo che il tool dichiara di se'.
_DICHIARA_SOLA_LETTURA = re.compile(r"read-only|read only|preview|snapshot|dry-run by default", re.I)

#: Su che cosa agisce: se non e' il corpus dei FATTI, la deny-list non lo riguarda
#: (il prodotto lo dice per gli episodi: «the server serves facts, not episodes,
#: so for those the local store IS the right answer»).
_NON_E_IL_CORPUS_DEI_FATTI = re.compile(r"\b(?:episode|episodes|skill|skills|dream|dreams)\b", re.I)

#: APERTI E NOTI: un difetto gia' registrato non deve rendere CIECO il cricchetto
#: su tutti gli altri. Sta qui, con il suo ticket, ed e' sorvegliato dal test in
#: fondo con `xfail(strict=True)`: quando la cura arriva, quello passa e obbliga a
#: togliere sia l'xfail sia questa riga. Un elenco che cresce senza ticket sarebbe
#: il modo elegante di spegnere il presidio.
APERTI_NOTI = {
    # ws7, 10/09: muta i fatti e non e' in _THIN_UNSUPPORTED_WRITES.
    # Stessa famiglia di T58. Owner della porta: ws2.
    "hippo_quarantine_restore",
}

#: ESCLUSI per NOME, e ognuno con la sua ragione — non un elenco di comodo.
_FUORI_PERIMETRO = {
    # Il prodotto li esclude DELIBERATAMENTE e lo scrive.
    "episode", "episodes",
    # Le skill non sono il corpus dei fatti.
    "skill", "skills",
    # Sono l'ANTIDOTO al no-op silenzioso, non una mutazione del corpus.
    "undo",
    # Governano il ciclo dei sogni/consolidamento locale, non i fatti serviti.
    "dream",
}


def _tutti_i_tool():
    import asyncio

    return list(asyncio.run(mcp_server._list_tools_unfiltered()))


def _tutti_i_nomi() -> set[str]:
    return {x.name for x in _tutti_i_tool()}


def _muta_il_corpus_dei_fatti(nome: str, descrizione: str = "") -> bool:
    """Tre filtri, e i primi due li ha guadagnati un rosso mio.

    ① il nome porta un verbo di mutazione, ai confini di parola;
    ② la descrizione NON dichiara di essere di sola lettura;
    ③ l'oggetto sono i FATTI, non episodi/skill/sogni.
    """
    if not _MUTA.search(_a_parole(nome)):
        return False
    if any(p in _a_parole(nome).lower().split() for p in _FUORI_PERIMETRO):
        return False
    if _DICHIARA_SOLA_LETTURA.search(descrizione):
        return False
    return not _NON_E_IL_CORPUS_DEI_FATTI.search(descrizione)


# ── IL CONTROLLO POSITIVO PER PRIMO ─────────────────────────────────────────


def test_CONTROLLO_le_due_liste_esistono_e_NON_sono_vuote():
    """Un cricchetto su una lista vuota e' verde per costruzione."""
    letture = mcp_server._THIN_UNSUPPORTED_READS
    scritture = mcp_server._THIN_UNSUPPORTED_WRITES
    assert len(letture) >= 10, f"solo {len(letture)} letture nella deny-list"
    assert len(scritture) >= 10, f"solo {len(scritture)} scritture nella deny-list"
    assert "hippo_facts_recent" in letture
    assert "hippo_fact_forget" in scritture


# ── ① I TRE DEL README HANNO LA VIA SOTTILE ─────────────────────────────────


@pytest.mark.parametrize("nome", README_HANNO_LA_VIA_SOTTILE)
def test_i_tre_strumenti_che_il_readme_nomina_delegano_davvero(nome):
    """README:611-613 li nomina come instradati al server: non devono rifiutare."""
    assert nome in _tutti_i_nomi(), f"{nome} non e' piu' uno strumento esposto"
    assert nome not in mcp_server._THIN_UNSUPPORTED_READS, (
        f"{nome} e' finito fra le letture che rifiutano, ma il README lo nomina "
        "fra quelli che passano dal server condiviso e ricadono sullo store "
        "locale. O torna la via sottile, o la riga 611-613 va riscritta."
    )
    assert nome not in mcp_server._THIN_UNSUPPORTED_WRITES, (
        f"{nome} e' finito fra le scritture che rifiutano: vedi sopra."
    )


# ── ② IL CRICCHETTO: LO SWEEP CHE LA PRIMA VERSIONE NON AVEVA ──────────────


def test_ogni_strumento_che_MUTA_i_fatti_rifiuta_in_thin_mode():
    """Il difetto che il prodotto ha gia' pagato una volta, reso meccanico.

    Il commento a `mcp_server.py:260` dice che la prima versione della guardia
    copriva solo i lettori e che le mutazioni sono state trovate «sweeping the
    mutating tools AFTER». Uno sweep fatto a mano una volta protegge fino alla
    prossima aggiunta: questo lo rifa' a ogni esecuzione.
    """
    scoperti = sorted(
        x.name for x in _tutti_i_tool()
        if _muta_il_corpus_dei_fatti(x.name, getattr(x, "description", "") or "")
        and x.name not in mcp_server._THIN_UNSUPPORTED_WRITES
        and x.name not in mcp_server._THIN_UNSUPPORTED_READS
        and x.name not in APERTI_NOTI
    )
    assert not scoperti, (
        "strumenti che mutano il corpus dei fatti e NON rifiutano in thin mode: "
        f"{scoperti}.\n"
        "In thin mode agirebbero sullo store LOCALE (vuoto per una sessione che "
        "vive dietro un server condiviso) e riferirebbero un esito — «removed», "
        "«merged», «superseded» — che nel corpus condiviso non e' avvenuto. E' il "
        "no-op silenzioso che `mcp_server.py:260` descrive.\n"
        "Se uno di questi e' fuori perimetro per una ragione vera (gli episodi lo "
        "sono, e il prodotto lo dichiara), va in `_FUORI_PERIMETRO` CON la ragione "
        "scritta accanto — non tolto in silenzio."
    )


# ── E IL CONTROLLO CHE PUO' SMENTIRMI ───────────────────────────────────────


@pytest.mark.parametrize(
    "nome, descrizione, deve_accendersi",
    [
        # — deve accendersi —
        ("hippo_fact_forget", "Delete a fact by id.", True),
        ("hippo_facts_merge", "Merge two facts into one.", True),
        ("hippo_fact_supersede_chain", "Supersede a whole chain.", True),
        # — non deve, e questi QUATTRO sono i rossi che il righello mi ha dato
        #   contro il 10/09: quattro «scoperti» su cinque erano suoi. Restano
        #   qui perche' un controllo positivo che non porta gli errori veri e'
        #   una lista di casi comodi.
        ("hippo_decay_simulate",
         "read-only preview of decay-prune candidates.", False),
        ("hippo_emergence_pipeline_status",
         "aggregate observability snapshot of the pipeline. Read-only.", False),
        ("hippo_apply_recommendations",
         "apply skill_health recommendations: promotes/retires skills.", False),
        ("hippo_forget", "Delete one episode by id (privacy / GDPR).", False),
        # — e i due di sempre —
        ("hippo_facts_search", "Search facts.", False),
        ("hippo_undo_destructive_op", "Undo a destructive op by op_id.", False),
    ],
)
def test_CONTROLLO_il_riconoscitore_separa_chi_MUTA_da_chi_no(nome, descrizione, deve_accendersi):
    """Senza questa faccia, «nessuno scoperto» direbbe solo che la regex e' cieca.

    E il caso `hippo_episode_pin` c'e' apposta per potermi smentire: se il
    riconoscitore si accendesse su tutto cio' che sembra scrivere, il cricchetto
    sopra chiederebbe di mettere in deny-list cose che il prodotto ha
    deliberatamente lasciato fuori — sarebbe rumore travestito da presidio.
    """
    acceso = _muta_il_corpus_dei_fatti(nome, descrizione)
    assert acceso is deve_accendersi, (
        f"su `{nome}` il riconoscitore "
        f"{'doveva' if deve_accendersi else 'non doveva'} accendersi"
    )


# ── IL REPERTO CHE IL CRICCHETTO HA ISOLATO ─────────────────────────────────


@pytest.mark.xfail(
    strict=True,
    reason=(
        "APERTO — ws7, 10/09. `hippo_quarantine_restore` muta il corpus dei fatti "
        "(«un-quarantine `fact_id` back into live recall») e NON sta in "
        "`_THIN_UNSUPPORTED_WRITES`. Il dispatcher (mcp_server.py:7939) rifiuta "
        "SOLO i nomi che stanno in una delle due liste, quindi in thin mode questo "
        "prosegue, agisce sullo store LOCALE e rende {ok, restored, fact_id}: "
        "l'utente crede di aver salvato un fatto ingiustamente bloccato mentre nel "
        "corpus condiviso resta quarantenato. E' testualmente il danno che il "
        "prodotto descrive tre righe piu' giu': «MUTATE the LOCAL store, leaving "
        "the shared corpus untouched while reporting an outcome as if it had "
        "changed».\n"
        "STESSA FAMIGLIA DI T58 (`facts restore` abortito esce 0): un ripristino "
        "che dichiara successo senza aver ripristinato. Due porte, una classe.\n"
        "NON lo curo qui: la cura e' una riga in `_THIN_UNSUPPORTED_WRITES` e "
        "appartiene a chi possiede la porta (ws2 Giano, che ha gia' T49 e T58). "
        "`strict=True`: il giorno che la riga c'e', questo passa e obbliga a "
        "togliere l'xfail."
    ),
)
def test_quarantine_restore_rifiuta_in_thin_mode():
    """La riga che manca alla deny-list delle scritture."""
    assert "hippo_quarantine_restore" in mcp_server._THIN_UNSUPPORTED_WRITES
