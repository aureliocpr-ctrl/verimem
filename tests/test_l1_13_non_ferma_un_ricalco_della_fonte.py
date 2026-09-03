"""`L1.13` non deve fermare un claim che RICALCA la fonte — EN e IT.

Reperto di ws7 (2026-08-28): su un verbale d'ufficio italiano il gate fermava
fatti VERI con la fonte al 99,9 perche' contenevano «fatta», «chiusa»,
«concluso». La causa non era la lista di parole: era che
`detect_unsupported_completion_claim` riceveva solo `proposition` e
`verified_by` e **non poteva sapere che il participio era nella fonte**.

I due criteri, e stanno insieme perche' da soli non dicono niente:
  - un claim il cui participio compare NELLA FONTE non e' una self-claim;
  - una self-claim SENZA fonte, o con una fonte che non la sostiene, resta
    fermata. Spegnere il layer non e' una cura.

Misurato prima della cura: 6 dei 7 casi di ws7 fermati, 6 self-claim su 6
fermati. Dopo: 0 su 7 e 6 su 6.

⚠️ AGGIORNATO IL 2026-09-03, e il titolo di questo file va letto con la
condizione che il 30/08 gli e' stata aggiunta sotto: L1.13 non ferma un ricalco
**di una fonte che il chiamante dichiara di terzi**. Se il chiamante non
dichiara nulla, chi scrive e' l'agente, la sua `source` puo' essere un'eco
della sua stessa frase (misurato 5 su 5) e il ricalco resta fermato. I test
diretti qui sotto non passano `provenance` e vedono percio' solo la prima
meta'; le celle di porta, in fondo, misurano tutte e due.
"""

from __future__ import annotations

import pytest

from verimem.l1_completion_detector import detect_unsupported_completion_claim

# ── il verbale italiano di ws7, e le sue frasi ───────────────────────────────
FONTE_IT = (
    "Verbale del cantiere. La consegna e' stata fatta il 28 marzo presso il "
    "magazzino centrale. La pratica e' stata chiusa il 28 marzo dall'ufficio "
    "protocollo. Il collaudo si e' concluso il 28 marzo alla presenza del "
    "direttore dei lavori. Il collaudo e' stato completato il 28 marzo."
)
RICALCHI_IT = [
    "La consegna e' stata fatta il 28 marzo.",
    "La pratica e' stata chiusa il 28 marzo.",
    "Il collaudo si e' concluso il 28 marzo.",
    "Il collaudo e' stato completato il 28 marzo.",
]

FONTE_EN = (
    "Site log. The delivery was completed on 28 March at the central "
    "warehouse. The case was closed on 28 March by the records office. "
    "Acceptance testing is done and the work is finished."
)
RICALCHI_EN = [
    "The delivery was completed on 28 March.",
    "The case was closed on 28 March.",
    "Acceptance testing is done.",
    "The work is finished.",
]

# ── le self-claim: devono restare fermate ────────────────────────────────────
SELFCLAIM_SENZA_FONTE = [
    "La migrazione e' completata e tutti i test passano.",
    "The migration is complete and all tests pass.",
    "Il lavoro e' stato completato.",
    "The task is done.",
]
FONTE_CHE_NON_SOSTIENE_IT = "Il cantiere ha ricevuto la visita dell'ispettore il 12 aprile."
FONTE_CHE_NON_SOSTIENE_EN = "The site received an inspection visit on 12 April."


@pytest.mark.parametrize("claim", RICALCHI_IT)
def test_it_il_ricalco_della_fonte_non_e_una_self_claim(claim):
    assert detect_unsupported_completion_claim(
        proposition=claim, verified_by=[], source=FONTE_IT) is None


@pytest.mark.parametrize("claim", RICALCHI_EN)
def test_en_il_ricalco_della_fonte_non_e_una_self_claim(claim):
    assert detect_unsupported_completion_claim(
        proposition=claim, verified_by=[], source=FONTE_EN) is None


@pytest.mark.parametrize("claim", SELFCLAIM_SENZA_FONTE)
def test_una_self_claim_senza_fonte_resta_fermata(claim):
    """Il criterio che rende la cura una cura e non uno spegnimento."""
    assert detect_unsupported_completion_claim(
        proposition=claim, verified_by=[], source=None) is not None


@pytest.mark.parametrize("claim,fonte", [
    ("Il collaudo e' stato completato.", FONTE_CHE_NON_SOSTIENE_IT),
    ("The delivery is complete.", FONTE_CHE_NON_SOSTIENE_EN),
])
def test_una_fonte_che_non_porta_il_participio_non_perdona(claim, fonte):
    """La fonte c'e' ma non contiene la parola: nessun perdono."""
    assert detect_unsupported_completion_claim(
        proposition=claim, verified_by=[], source=fonte) is not None


def test_senza_source_il_comportamento_e_quello_di_prima():
    """Il default `source=None` non cambia nessun chiamante esistente."""
    assert detect_unsupported_completion_claim(
        proposition="La consegna e' stata fatta il 28 marzo.",
        verified_by=[]) is not None


def test_il_confronto_ignora_le_maiuscole():
    """Una fonte che apre la frase con la maiuscola perdona lo stesso."""
    assert detect_unsupported_completion_claim(
        proposition="il lavoro e' stato completato",
        verified_by=[],
        source="Completato il 28 marzo, come da verbale.") is None


# ── LA PORTA, non solo il detector ───────────────────────────────────────────
#
# I test qui sopra chiamano il detector e gli passano `source` a mano: sono
# ciechi al modo in cui il difetto e' NATO. La causa non era dentro il
# detector — era che il gate lo chiamava SENZA `source`, e un presidio che
# guarda una porta sola e' verde per costruzione (classe nominata il
# 2026-08-28: «il presidio esiste, e' acceso, e guarda UNA PORTA SOLA»).
#
# Questi due passano da `run_validation_gate`, cioe' da dove il prodotto
# chiama: se qualcuno smettesse di inoltrare `source` lungo la catena
# `run_validation_gate` -> `_l1_warnings` -> detector, i test sopra
# resterebbero verdi e questi diventerebbero rossi.
#
# Girano senza `ground_write`: la famiglia L1 e' lessicale e non passa dal
# ramo del moat, quindi nessun modello viene caricato (misurato: stessi layer
# con e senza).

def _layer_alla_porta(claim: str, source: str | None,
                      writer_role: str | None = None) -> list[str]:
    """I layer che la PORTA accende. `writer_role` resta al default (`None`)
    per chi non lo passa: le celle scritte prima del 30/08 non cambiano.
    """
    from verimem.anti_confab_gate import run_validation_gate
    g = run_validation_gate(proposition=claim, verified_by=[], topic=None,
                            agent=None, source=source, writer_role=writer_role)
    return [str((w or {}).get("layer") or "")
            for w in (getattr(g, "warnings", None) or [])]


# ⚖️ CHI SCRIVE decide, e queste due celle sono la stessa domanda nei due versi.
#
# Le due celle qui sotto chiedevano che il ricalco NON accendesse L1.13 alla
# porta CON GLI ARGOMENTI DI DEFAULT, e dal 30/08 sono rosse. Non e' la porta
# ad essersi rotta: e' la GUARDIA ANTI-ECO di quel giorno (votata 3/3) a dire
# che quando parla l'agente la sua `source` non e' una testimonianza ma un'eco,
# e `classify_provenance(None, [])` vale `agent_claim` — misurato, non deve.
# Quindi con gli argomenti di default il perdono NON si applica, ed e' voluto.
#
# Misurato il 2026-09-03 alle 18:49 sul worktree a `5de26d9b`, stesso claim,
# stessa fonte, al variare del solo `writer_role`:
#
#     writer_role         provenienza        ricalco    self-claim
#     None                agent_claim        FERMA      FERMA
#     agent_inference     agent_claim        FERMA      FERMA
#     user                user_input         perdona    FERMA
#     external_content    external_content   perdona    FERMA
#     document            external_content   perdona    FERMA
#     document_ingest     external_content   perdona    FERMA
#     system_hook         trusted_hook       perdona    FERMA
#     trusted_hook        trusted_hook       perdona    FERMA
#
# ⇒ il ruolo e' un discriminante che funziona nei due versi E NON E' UN
# INTERRUTTORE: nessun ruolo fa passare la self-claim. Le tre celle qui sotto
# fissano le tre righe che contano, e la terza e' il controllo che deve
# accendersi se qualcuno trasformasse il ruolo in una leva per spegnere L1.13.
#
# ⛔ IL DEBITO CHE QUESTA CELLA NON CHIUDE, e va detto qui perche' verde non
# significa risolto: la strada del perdono e' raggiungibile solo DICHIARANDO il
# ruolo, e nessuna delle due superfici lo dichiara da sola (SDK `None`, MCP
# `"agent_inference"`: entrambe -> `agent_claim`). Sul corpus vivo, contato in
# sola lettura il 2026-09-03, i fatti con `writer_role='external_content'` sono
# **0 su 17.411** (`user` 10.844, `agent_inference` 6.144, `system_hook` 421,
# `trusted_hook` 2). La cura del 28/08 esiste e funziona: non la percorre
# nessuno. ⚠️ E quella colonna NON dice cosa ha visto il gate — per un write
# `meta_narrative` il client la riscrive a `'user'` DOPO il gate, che aveva
# ricevuto `None`: e' un conteggio di cio' che e' scritto nel fatto, non di cio'
# che e' stato giudicato.

@pytest.mark.parametrize("claim,fonte", [
    (RICALCHI_IT[0], FONTE_IT),
    (RICALCHI_EN[0], FONTE_EN),
])
def test_alla_porta_il_ricalco_e_fermato_se_a_scriverlo_e_l_agente(claim, fonte):
    """Il verso della guardia anti-eco: senza ruolo dichiarato, si ferma."""
    assert [x for x in _layer_alla_porta(claim, fonte) if x.startswith("L1.13")]


@pytest.mark.parametrize("claim,fonte", [
    (RICALCHI_IT[0], FONTE_IT),
    (RICALCHI_EN[0], FONTE_EN),
])
def test_alla_porta_il_ricalco_e_perdonato_se_la_fonte_e_dichiarata_terza(claim, fonte):
    """Il verso della cura del 28/08 — ed e' QUESTA a sorvegliare la catena.

    Se qualcuno smettesse di inoltrare `source` lungo
    `run_validation_gate` -> `_l1_warnings` -> detector, il participio non
    sarebbe piu' trovabile nella fonte, il perdono non scatterebbe e questa
    cella diventerebbe rossa mentre i test diretti qui sopra resterebbero
    verdi. E' la ragione per cui la cella di porta esiste.
    """
    assert not [x for x in _layer_alla_porta(claim, fonte,
                                             writer_role="external_content")
                if x.startswith("L1.13")]


@pytest.mark.parametrize("ruolo", [None, "agent_inference", "user",
                                   "external_content", "document",
                                   "document_ingest", "system_hook",
                                   "trusted_hook"])
def test_alla_porta_il_ruolo_non_e_un_interruttore_per_l1_13(ruolo):
    """Il controllo che DEVE accendersi: nessun ruolo fa passare la self-claim.

    Senza questa cella la precedente sarebbe soddisfacibile spegnendo il layer.
    """
    assert [x for x in _layer_alla_porta(SELFCLAIM_SENZA_FONTE[0], None,
                                         writer_role=ruolo)
            if x.startswith("L1.13")], f"il ruolo {ruolo!r} spegne L1.13"


@pytest.mark.parametrize("claim", [SELFCLAIM_SENZA_FONTE[0],
                                   SELFCLAIM_SENZA_FONTE[1]])
def test_alla_porta_la_self_claim_accende_ancora_l1_13(claim):
    assert [x for x in _layer_alla_porta(claim, None)
            if x.startswith("L1.13")]
