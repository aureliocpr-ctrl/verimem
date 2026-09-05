"""`search_facts` con `as_of`: il vincolo temporale va dove sta il dato.

DECISIONE DEL CTO (05/09 21:26, opzione A). Il reperto e' di ws2 e ws1 l'ha
confermato contro il proprio interesse: `search_facts` ordina per
`created_at DESC` e taglia a `limit`, quindi **chiedendo il passato i primi
`limit` sono per costruzione quelli che un filtro a valle scarta**. Nessun
fattore moltiplicativo chiude il buco: cresce col corpus.

Le tre strade e perche' questa:
  (A) il vincolo nella WHERE dello store            ← scelta
  (B) un cap sull'oversample     — un limite dichiarato e' un debito che paga
                                    qualcun altro
  (C) la porta che pagina        — una copia di cio' che lo store deve saper
                                    fare, e paga in query

⚠️ LA REGOLA E' QUELLA DI `recall_as_of`, NON UNA NUOVA: nato ≤ `when`, dove
«nato» e' `asserted_at` (il tempo dell'EVENTO) con `created_at` come ripiego —
la stessa che `temporal_context.recall_as_of` applica riga per riga::

    born = getattr(f, "asserted_at", None)
    born = float(born) if born is not None else float(
        getattr(f, "created_at", 0.0) or 0.0)
    if born > when: scarta

In SQL diventa `COALESCE(asserted_at, created_at) <= ?`. Due implementazioni
della stessa regola sono gia' due copie in attesa di divergere: questo file e'
il posto dove la divergenza diventa rossa.

⚠️ AI RITIRATI NON TOCCA: `superseded_at` non entra in questa WHERE. Un fatto
gia' superseduto a quella data resta affare del filtro a valle, che sa anche
distinguere «ritirato» da «non ancora nato» — due scarti diversi che qui
verrebbero confusi in uno.

PREDIZIONI DEPOSITATE PRIMA DI ESEGUIRE (2026-09-05 22:45):
  P1 — la fame ESISTE: con `limit` piccolo e nessun `as_of`, i fatti vecchi non
       compaiono, perche' i recenti occupano tutte le posizioni.
       ATTESA: VERDE gia' ora. E' il controllo positivo: se fosse rossa, lo
       store non sarebbe affamato e il resto del file non misurerebbe niente.
  P2 — con `as_of` fra i vecchi e i recenti, tornano i VECCHI.
       ATTESA: **ROSSA** — il parametro non esiste ancora.
  P3 — `as_of` guarda `asserted_at` prima di `created_at`: un fatto SCRITTO
       oggi ma ASSERITO nel passato deve tornare.
       ATTESA: ROSSA. E' la meta' della regola che una WHERE sul solo
       `created_at` sbaglierebbe in silenzio, ed e' il caso che distingue
       «quando l'abbiamo scritto» da «quando era vero».
  P4 — senza `as_of` nulla cambia per i chiamanti che gia' esistono.
       ATTESA: VERDE prima e dopo. `search_facts(` ha 9 chiamanti in
       `verimem/` (cli 1, client 5, mcp_server 2, semantic 1): il default
       `None` e' cio' che impedisce a questa cura di essere un cambio di API.

⚠️ NESSUN GIUDICE: i fatti si scrivono con `SemanticMemory.store`, che non
passa dal gate. Il file gira in pochi secondi e non contende la macchina a chi
sta misurando tempi.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from verimem.semantic import Fact, SemanticMemory  # noqa: E402

_PAROLA = "fornitore"
#: Un istante che sta FRA i vecchi e i recenti.
_CONFINE = 2_000_000_000.0        # 2033
_VECCHIO = 1_600_000_000.0        # 2020
_RECENTE = 2_100_000_000.0        # 2036


@pytest.fixture()
def store(tmp_path):
    """Otto fatti recenti e due vecchi, tutti con la stessa parola.

    Il rapporto conta: con `limit=3` i tre posti sono occupati dai recenti, che
    e' esattamente la condizione in cui un filtro a valle rende zero.
    """
    sm = SemanticMemory(tmp_path / "s.db")
    for i in range(8):
        sm.store(Fact(id=f"new{i}", proposition=f"il {_PAROLA} corrente e' Adyen {i}",
                      topic="pagamenti", created_at=_RECENTE + i))
    for i in range(2):
        sm.store(Fact(id=f"old{i}", proposition=f"il {_PAROLA} di allora era Stripe {i}",
                      topic="pagamenti", created_at=_VECCHIO + i))
    return sm


def _ids(facts):
    return {f.id for f in facts}


def test_P1_controllo_positivo_lo_store_e_affamato(store):
    """Senza `as_of` i vecchi non compaiono: la fame che la cura deve togliere.

    Se questa fosse verde per il motivo sbagliato — cioe' se i vecchi
    comparissero lo stesso — il rosso di P2 non proverebbe niente.
    """
    got = _ids(store.search_facts(_PAROLA, limit=3))
    assert len(got) == 3, f"lo store non ha reso 3 fatti: {got}"
    assert not (got & {"old0", "old1"}), (
        f"i vecchi compaiono gia' senza as_of ({got}): lo store non e' affamato "
        "e il resto di questo file non misura la fame")


def test_P2_chiedendo_il_passato_tornano_i_fatti_di_allora(store):
    """IL RED. `as_of` prima del taglio, non dopo."""
    got = _ids(store.search_facts(_PAROLA, limit=3, as_of=_CONFINE))
    assert got == {"old0", "old1"}, (
        f"chiedendo il passato lo store rende {got}: il filtro temporale non "
        "e' nella WHERE, quindi il taglio a `limit` avviene prima e i fatti di "
        "allora non hanno mai una posizione")


def test_P3_as_of_guarda_il_tempo_dell_evento_non_quello_della_scrittura(tmp_path):
    """Un fatto SCRITTO oggi ma ASSERITO ieri appartiene a ieri.

    E' la meta' della regola che una WHERE sul solo `created_at` sbaglierebbe
    in silenzio: il fatto tornerebbe assente a chi chiede il passato, pur
    essendo stato dichiarato vero allora.
    """
    sm = SemanticMemory(tmp_path / "s.db")
    f = Fact(id="tardivo", proposition=f"il {_PAROLA} di allora era Stripe",
             topic="pagamenti", created_at=_RECENTE)
    f.asserted_at = _VECCHIO          # detto allora, scritto oggi
    sm.store(f)
    # ⚠️ IL COMPAGNO CHE DEVE ESSERE ESCLUSO, e senza di lui questo test passa
    # per la ragione sbagliata: con un fatto solo nello store, `limit=5` lo
    # rende anche a filtro ASSENTE. Trovato falsificando (05/09 22:43): tolta
    # del tutto la clausola, P3 restava VERDE. Un test che non cade quando la
    # cura sparisce non e' un presidio, e' un'abitudine.
    sm.store(Fact(id="nato_dopo", proposition=f"il {_PAROLA} corrente e' Adyen",
                  topic="pagamenti", created_at=_RECENTE + 10))
    got = _ids(sm.search_facts(_PAROLA, limit=5, as_of=_CONFINE))
    assert got == {"tardivo"}, (
        f"as_of ha reso {got}: guarda `created_at` e non `asserted_at`, quindi "
        "un fatto asserito nel passato e scritto oggi risulta non ancora nato")


def test_P4_senza_as_of_i_chiamanti_di_oggi_non_cambiano(store):
    """Il default `None` e' cio' che rende questa cura non un cambio di API.

    `search_facts(` ha nove chiamanti in `verimem/`; nessuno passa `as_of`, e
    tutti devono vedere esattamente la risposta di prima.
    """
    assert _ids(store.search_facts(_PAROLA, limit=10)) == {
        f"new{i}" for i in range(8)} | {"old0", "old1"}
