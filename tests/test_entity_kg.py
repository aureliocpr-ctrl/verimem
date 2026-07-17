"""P2.a — RED test per entity-centric knowledge graph (entities + aliases + facts).

Spec: docs/specs/p2-entity-centric-kg.md (commit 48678a2).

Scope P2.a (minimum viable):
- `engram/entity_kg.py` con `EntityStore` SQLite-backed
- 3 tabelle: entities, entity_aliases, entity_facts (subset additivo)
- Tool MCP `hippo_entity_get(name)` → {entity, facts[]}

Out-of-scope per P2.a (rimandato a P2.b/c):
- `entity_edges` con weight/predicate (P2.b)
- `hippo_ppr_retrieve` (P2.b — richiede networkx)
- `hippo_extract_entities` LLM-based OpenIE (P2.c)
- skill .md (P2.d, dopo che tutti i 4 tool sono pronti)

Test plan: SQLite reale in tmp_path (NO fake — lezione cycle #70:
fake troppo generoso = test inutile in produzione).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

# ---------- Unit tests sul modulo verimem.entity_kg ---------------------


def test_entity_store_create_and_get_by_name(tmp_path: Path) -> None:
    """RED: creazione entity + lookup per canonical_name."""
    from verimem.entity_kg import Entity, EntityStore

    store = EntityStore(db_path=tmp_path / "entity_kg.db")
    eid = store.store(Entity(canonical_name="Tonegawa", type="person"))
    assert eid, "store must return non-empty entity id"

    fetched = store.get_by_name("Tonegawa")
    assert fetched is not None
    assert fetched.canonical_name == "Tonegawa"
    assert fetched.type == "person"


def test_entity_lookup_case_insensitive(tmp_path: Path) -> None:
    """RED: lookup deve essere case-insensitive (cerca 'tonegawa' trova 'Tonegawa')."""
    from verimem.entity_kg import Entity, EntityStore

    store = EntityStore(db_path=tmp_path / "entity_kg.db")
    store.store(Entity(canonical_name="Tonegawa", type="person"))

    assert store.get_by_name("tonegawa") is not None
    assert store.get_by_name("TONEGAWA") is not None


def test_entity_alias_lookup(tmp_path: Path) -> None:
    """RED: lookup di un alias ritorna l'entity canonica.

    'S. Tonegawa' è alias di 'Tonegawa' — get_by_name("S. Tonegawa")
    deve trovare la stessa entity.
    """
    from verimem.entity_kg import Entity, EntityStore

    store = EntityStore(db_path=tmp_path / "entity_kg.db")
    eid = store.store(Entity(canonical_name="Tonegawa", type="person"))
    store.add_alias(eid, "S. Tonegawa")

    fetched = store.get_by_name("S. Tonegawa")
    assert fetched is not None
    assert fetched.id == eid
    assert fetched.canonical_name == "Tonegawa"


def test_entity_link_fact_and_retrieve(tmp_path: Path) -> None:
    """RED: link fact a entity + facts_for_entity ritorna la lista."""
    from verimem.entity_kg import Entity, EntityStore

    store = EntityStore(db_path=tmp_path / "entity_kg.db")
    eid = store.store(Entity(canonical_name="Tonegawa", type="person"))
    store.link_fact("f_tonegawa_1987", eid)
    store.link_fact("f_tonegawa_engram_2014", eid)

    fact_ids = store.facts_for_entity(eid)
    assert set(fact_ids) == {"f_tonegawa_1987", "f_tonegawa_engram_2014"}


def test_entity_link_fact_idempotent(tmp_path: Path) -> None:
    """RED: link due volte lo stesso (fact_id, entity_id) NON deve duplicare."""
    from verimem.entity_kg import Entity, EntityStore

    store = EntityStore(db_path=tmp_path / "entity_kg.db")
    eid = store.store(Entity(canonical_name="Tonegawa"))
    store.link_fact("f_dup", eid)
    store.link_fact("f_dup", eid)  # duplicate insert

    assert store.facts_for_entity(eid) == ["f_dup"]


def test_entity_store_returns_existing_on_duplicate_name(
    tmp_path: Path,
) -> None:
    """RED: store di entity con stesso canonical_name (case-insensitive)
    deve restituire l'id esistente, non duplicare."""
    from verimem.entity_kg import Entity, EntityStore

    store = EntityStore(db_path=tmp_path / "entity_kg.db")
    eid1 = store.store(Entity(canonical_name="Tonegawa", type="person"))
    eid2 = store.store(Entity(canonical_name="tonegawa", type="person"))

    assert eid1 == eid2, "duplicate canonical_name must dedupe"


# ---------- MCP tool integration ----------------------------------------


class _FakeAgent:
    """Fake agent espone solo .entity_kg (e .semantic minimal per audit hook)."""

    def __init__(self, entity_kg, semantic=None) -> None:
        self.entity_kg = entity_kg
        # alcuni handler MCP toccano a.semantic anche se non rilevante qui;
        # forniamo uno stub innocuo (con search_facts → [] default).
        self.semantic = semantic or _NoopSemantic()


class _NoopSemantic:
    def search_facts(self, query: str, *, limit: int = 20,
                     topic: str | None = None):
        return []


@pytest.fixture
def fake_agent_with_entity_kg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    """Build a fake agent with a real EntityStore (SQLite in tmp_path)."""
    from verimem import mcp_server
    from verimem.entity_kg import Entity, EntityStore

    store = EntityStore(db_path=tmp_path / "entity_kg.db")
    eid = store.store(Entity(canonical_name="Tonegawa", type="person"))
    store.add_alias(eid, "S. Tonegawa")
    store.link_fact("f_tonegawa_1987", eid)

    a = _FakeAgent(entity_kg=store)
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    return a, eid


async def _invoke_tool(
    name: str, arguments: dict[str, Any] | None = None,
) -> list[str]:
    from mcp.types import CallToolRequest, CallToolRequestParams

    from verimem import mcp_server

    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments or {}),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    return [c.text for c in payload.content if hasattr(c, "text")]


@pytest.mark.asyncio
async def test_hippo_entity_get_tool_listed(
    fake_agent_with_entity_kg,
) -> None:
    """RED: tool hippo_entity_get deve apparire nella lista MCP."""
    from mcp.types import ListToolsRequest, PaginatedRequestParams

    from verimem import mcp_server

    handler = mcp_server.server.request_handlers[ListToolsRequest]
    req = ListToolsRequest(
        method="tools/list", params=PaginatedRequestParams(),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    names = {tool.name for tool in payload.tools}
    assert "hippo_entity_get" in names


@pytest.mark.asyncio
async def test_hippo_entity_get_by_canonical_name(
    fake_agent_with_entity_kg,
) -> None:
    """RED: tool MCP ritorna entity + facts per canonical_name."""
    _, eid = fake_agent_with_entity_kg
    blocks = await _invoke_tool(
        "hippo_entity_get", {"name": "Tonegawa"},
    )
    assert blocks
    payload = json.loads(blocks[0])
    assert payload["entity"] is not None
    assert payload["entity"]["id"] == eid
    assert payload["entity"]["canonical_name"] == "Tonegawa"
    assert "f_tonegawa_1987" in payload["facts"]


@pytest.mark.asyncio
async def test_hippo_entity_get_by_alias(fake_agent_with_entity_kg) -> None:
    """RED: tool MCP risolve alias → stessa entity."""
    _, eid = fake_agent_with_entity_kg
    blocks = await _invoke_tool(
        "hippo_entity_get", {"name": "S. Tonegawa"},
    )
    payload = json.loads(blocks[0])
    assert payload["entity"]["id"] == eid


@pytest.mark.asyncio
async def test_hippo_entity_get_not_found(
    fake_agent_with_entity_kg,
) -> None:
    """RED: entity sconosciuta → entity=None, facts=[]."""
    blocks = await _invoke_tool(
        "hippo_entity_get", {"name": "Marie Curie"},
    )
    payload = json.loads(blocks[0])
    assert payload["entity"] is None
    assert payload["facts"] == []


# ---------- Round 2 RED test (critic counterexample fixes) -------------
# Critic round 1 (job 19f8c075d80732fa) ha trovato 3 bug reali:
# 1) Race condition: store() check-then-insert non atomico → duplicates
#    sotto concorrenza.
# 2) Cross-alias contract violation: store(canonical == alias_di_altra)
#    ritorna l'altra entity (perché store usa get_by_name che matcha
#    anche alias) — viola docstring "dedupe canonical-only".
# 3) Empty canonical_name bypass: store(Entity("")) crea N entities
#    vuote perché get_by_name("") early-returns None.


def test_store_rejects_empty_canonical_name(tmp_path: Path) -> None:
    """RED bug #3: canonical_name vuoto/whitespace deve sollevare
    ValueError, NON creare entity fantasma."""
    from verimem.entity_kg import Entity, EntityStore

    store = EntityStore(db_path=tmp_path / "entity_kg.db")

    with pytest.raises(ValueError):
        store.store(Entity(canonical_name=""))
    with pytest.raises(ValueError):
        store.store(Entity(canonical_name="   "))
    with pytest.raises(ValueError):
        store.store(Entity(canonical_name="\t\n"))

    assert store.count() == 0, (
        "nessuna entity deve essere creata da canonical_name vuoto"
    )


def test_store_canonical_matching_existing_alias_creates_new(
    tmp_path: Path,
) -> None:
    """RED bug #2: store(canonical_name X) DOPO add_alias(other_eid, X)
    deve creare una NUOVA entity, NON ritornare other_eid.

    Contract: dedupe è canonical→canonical, mai canonical→alias.
    Altrimenti è impossibile promuovere un alias a canonical di una
    nuova entity distinta.
    """
    from verimem.entity_kg import Entity, EntityStore

    store = EntityStore(db_path=tmp_path / "entity_kg.db")
    eid_tonegawa = store.store(
        Entity(canonical_name="Tonegawa", type="person"),
    )
    store.add_alias(eid_tonegawa, "Susumu Tonegawa")
    # Sanity: get_by_name su alias risolve a Tonegawa
    assert store.get_by_name("Susumu Tonegawa").id == eid_tonegawa

    # Adesso store con canonical_name == alias esistente di altra entity:
    # contract → NUOVA entity (eid diverso, count=2)
    eid_new = store.store(
        Entity(canonical_name="Susumu Tonegawa", type="person"),
    )
    assert eid_new != eid_tonegawa, (
        "store(canonical) deve creare nuova entity, non riusare via alias"
    )
    assert store.count() == 2


def test_store_dedupes_unicode_case_insensitive(tmp_path: Path) -> None:
    """RED round 3 — counterexample 0.95: SQLite LOWER() è ASCII-only,
    Python str.lower() è full-Unicode. Senza name_norm Python-computed,
    'MÜLLER' e 'Müller' creano 2 entity distinte (LOWER('MÜLLER')='mÜLLER'
    != LOWER('Müller')='mÜller' in SQLite ma == 'müller' in Python).

    Lo stesso si applica a Erdős/ERDŐS, Schrödinger/SCHRÖDINGER,
    İstanbul/ISTANBUL (Turkish), François/FRANÇOIS ecc.
    """
    from verimem.entity_kg import Entity, EntityStore

    store = EntityStore(db_path=tmp_path / "entity_kg.db")
    eid1 = store.store(Entity(canonical_name="MÜLLER", type="person"))
    eid2 = store.store(Entity(canonical_name="Müller", type="person"))
    eid3 = store.store(Entity(canonical_name="müller", type="person"))

    assert eid1 == eid2 == eid3, (
        f"Unicode case-insensitive dedup failed: "
        f"MÜLLER={eid1!r}, Müller={eid2!r}, müller={eid3!r}"
    )
    assert store.count() == 1

    # get_by_name deve trovare l'entity per qualsiasi casing Unicode
    for q in ("MÜLLER", "Müller", "müller", "MüLlEr"):
        e = store.get_by_name(q)
        assert e is not None, f"lookup '{q}' returned None"
        assert e.id == eid1

    # Cross-check con altri caratteri Unicode comuni in nomi europei
    eid_erdos = store.store(Entity(canonical_name="Erdős", type="person"))
    assert store.get_by_name("ERDŐS").id == eid_erdos
    assert store.get_by_name("erdős").id == eid_erdos


def test_migration_v4_handles_preexisting_nfc_nfd_duplicates(
    tmp_path: Path,
) -> None:
    """RED round 5 — counterexample 0.9: DB pre-esistente in schema v3
    può avere coppie NFC/NFD coesistenti (l'UNIQUE INDEX v3 le considera
    distinte byte-wise). Quando boot a v4 che ri-backfilla name_norm a
    NFC, le UPDATE violerebbero `idx_entities_name_norm_unique` →
    IntegrityError → rollback → DB stuck.

    Simuliamo lo scenario inserendo manualmente schema v3 + duplicate
    NFC/NFD, poi facciamo boot EntityStore (target_version=4): la
    migration v4 deve assorbire la riga NFD nel survivor NFC senza
    errore.
    """
    import sqlite3
    import unicodedata
    import uuid

    db_path = tmp_path / "entity_kg.db"

    # 1) Costruisco manualmente DB con schema v3
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE entities (
            id TEXT PRIMARY KEY,
            canonical_name TEXT NOT NULL,
            name_norm TEXT NOT NULL DEFAULT '',
            type TEXT NOT NULL DEFAULT '',
            created_at REAL NOT NULL
        );
        CREATE UNIQUE INDEX idx_entities_name_norm_unique
            ON entities(name_norm);
        CREATE TABLE entity_aliases (
            entity_id TEXT NOT NULL,
            alias TEXT NOT NULL,
            alias_norm TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (entity_id, alias)
        );
        CREATE INDEX idx_aliases_alias_norm
            ON entity_aliases(alias_norm);
        CREATE TABLE entity_facts (
            fact_id TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            PRIMARY KEY (fact_id, entity_id)
        );
        CREATE TABLE _schema_version (
            db_id TEXT PRIMARY KEY,
            version INTEGER NOT NULL,
            upgraded_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )
    # Stampa version=3 (DB già migrato fino a v3, prima dell'arrivo di
    # v4)
    conn.execute(
        "INSERT INTO _schema_version (db_id, version) VALUES "
        "('entity_kg', 3)"
    )

    # 2) Inserisco coppia NFC + NFD con name_norm byte-distinti
    # (.lower() senza NFC, simulando il bug round 3 → 4)
    nfc = unicodedata.normalize("NFC", "Müller")  # 6 cp
    nfd = unicodedata.normalize("NFD", "Müller")  # 7 cp
    eid_nfc = uuid.uuid4().hex[:12]
    eid_nfd = uuid.uuid4().hex[:12]
    conn.execute(
        "INSERT INTO entities "
        "(id, canonical_name, name_norm, type, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (eid_nfc, nfc, nfc.lower(), "person", 1000.0),
    )
    conn.execute(
        "INSERT INTO entities "
        "(id, canonical_name, name_norm, type, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (eid_nfd, nfd, nfd.lower(), "person", 1001.0),
    )
    # Linka un fatto e un alias a quella NFD per verificare che la
    # migration NON perda dati (devono finire sul survivor NFC).
    conn.execute(
        "INSERT INTO entity_aliases (entity_id, alias, alias_norm) "
        "VALUES (?, ?, ?)",
        (eid_nfd, "M. NFD", "m. nfd"),
    )
    conn.execute(
        "INSERT INTO entity_facts (fact_id, entity_id) "
        "VALUES (?, ?)",
        ("f_nfd_only", eid_nfd),
    )
    conn.commit()
    # Sanity: due righe coesistono (UNIQUE INDEX v3 non le vede uguali)
    n = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    assert n == 2, "test sanity: 2 duplicate NFC/NFD must coexist in v3"
    conn.close()

    # 3) Boot EntityStore con il modulo aggiornato (target_version=4) —
    # se la migration v4 è bacata, qui fallisce con IntegrityError o
    # propaga rollback.
    from verimem.entity_kg import EntityStore

    store = EntityStore(db_path=db_path)

    # 4) Dopo la migration: 1 sola entity, NFC survivor (min created_at),
    # alias + fact dell'NFD ri-linkati al survivor.
    assert store.count() == 1, (
        f"v4 must collapse NFC+NFD duplicates, got {store.count()}"
    )
    survivor = store.get_by_name("Müller")
    assert survivor is not None
    assert survivor.id == eid_nfc, (
        f"survivor must be min(created_at) = NFC eid; got {survivor.id}"
    )
    # Alias + fact dell'NFD assorbiti
    assert "M. NFD" in store.aliases_of(eid_nfc), (
        "alias di NFD perso durante migration"
    )
    assert "f_nfd_only" in store.facts_for_entity(eid_nfc), (
        "fact di NFD perso durante migration"
    )


def test_store_normalizes_unicode_nfc_nfd(tmp_path: Path) -> None:
    """RED round 4 — counterexample 0.92: NFC vs NFD bypass.

    `unicodedata.normalize('NFC', 'Müller')` (precomposed ü, 1 cp) ≠
    `unicodedata.normalize('NFD', 'Müller')` (u + combining diaeresis,
    2 cp) byte-wise. macOS APFS/HFS+ usa NFD per nomi file, clipboard
    cross-OS, OCR/scraping web mescolano forme. Senza `_norm()` che
    forza NFC, il dedupe Unicode-safe è incompleto.
    """
    import unicodedata

    from verimem.entity_kg import Entity, EntityStore

    store = EntityStore(db_path=tmp_path / "entity_kg.db")

    nfc = unicodedata.normalize("NFC", "Müller")
    nfd = unicodedata.normalize("NFD", "Müller")
    nfc_upper = unicodedata.normalize("NFC", "MÜLLER")
    nfd_upper = unicodedata.normalize("NFD", "MÜLLER")
    assert nfc != nfd, "test sanity: NFC/NFD must differ byte-wise"

    eid1 = store.store(Entity(canonical_name=nfc, type="person"))
    eid2 = store.store(Entity(canonical_name=nfd, type="person"))
    eid3 = store.store(Entity(canonical_name=nfc_upper, type="person"))
    eid4 = store.store(Entity(canonical_name=nfd_upper, type="person"))

    assert eid1 == eid2 == eid3 == eid4, (
        f"NFC/NFD dedupe failed: "
        f"nfc={eid1!r}, nfd={eid2!r}, "
        f"nfc_up={eid3!r}, nfd_up={eid4!r}"
    )
    assert store.count() == 1

    # Lookup cross-form deve risolvere alla stessa entity
    assert store.get_by_name(nfc).id == eid1
    assert store.get_by_name(nfd).id == eid1
    assert store.get_by_name(nfc_upper).id == eid1
    assert store.get_by_name(nfd_upper).id == eid1


def test_alias_lookup_unicode_case_insensitive(tmp_path: Path) -> None:
    """RED round 3: alias lookup Unicode case-insensitive.

    Caso critico: alias storato UPPERCASE 'ERWIN SCHRÖDINGER' (Ö
    uppercase) → lookup 'erwin schrödinger' (ö lowercase) deve matchare.
    Senza alias_norm Python-side, SQLite LOWER('ERWIN SCHRÖDINGER') =
    'erwin SCHRÖDINGER' (Ö preservato) ≠ Python 'erwin schrödinger'.
    """
    from verimem.entity_kg import Entity, EntityStore

    store = EntityStore(db_path=tmp_path / "entity_kg.db")
    eid = store.store(Entity(canonical_name="Schrödinger", type="person"))
    # Alias storato UPPERCASE Unicode — il caso che svela il bug
    store.add_alias(eid, "ERWIN SCHRÖDINGER")

    # Lookup con casing diverso DEVE risolvere alla stessa entity
    for q in ("ERWIN SCHRÖDINGER", "erwin schrödinger",
              "Erwin SCHRÖDINGER", "Erwin Schrödinger"):
        e = store.get_by_name(q)
        assert e is not None, f"alias lookup '{q}' returned None"
        assert e.id == eid

    # Anche Turkish dotless-i (caso noto di mismatch ASCII LOWER)
    eid_istanbul = store.store(Entity(canonical_name="İstanbul",
                                       type="place"))
    store.add_alias(eid_istanbul, "İSTANBUL")
    # NOTA: 'İ' (U+0130) lowercased in Python = 'i̇' (i + combining dot
    # above U+0307). Ci basta che il lookup sia consistente con se
    # stesso (storato lowercase 'i̇stanbul' → lookup 'İSTANBUL' lowercased
    # in Python diventa 'i̇stanbul' → match). Lo skip-test puro è che
    # entity con canonical 'İstanbul' sia recuperabile.
    e = store.get_by_name("İstanbul")
    assert e is not None and e.id == eid_istanbul


def test_store_concurrent_dedupe_no_duplicates(tmp_path: Path) -> None:
    """RED bug #1: 8 thread paralleli che fanno store(Entity("Tonegawa"))
    devono produrre UNA SOLA entity, non N duplicate.

    Counterexample critic 0.92: check-then-insert non atomico + schema
    senza UNIQUE su canonical_name → race window aperta.

    Test usa threading.Barrier per massimizzare la finestra di race.
    """
    import threading

    from verimem.entity_kg import Entity, EntityStore

    store = EntityStore(db_path=tmp_path / "entity_kg.db")

    n_workers = 8
    barrier = threading.Barrier(n_workers)
    results: list[str] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def worker() -> None:
        try:
            barrier.wait(timeout=10)
            eid = store.store(Entity(canonical_name="Tonegawa"))
            with lock:
                results.append(eid)
        except BaseException as e:  # noqa: BLE001
            with lock:
                errors.append(e)

    threads = [
        threading.Thread(target=worker) for _ in range(n_workers)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    assert not errors, f"workers errored: {errors}"
    assert store.count() == 1, (
        f"expected exactly 1 entity, got {store.count()} "
        f"(race condition in store dedupe)"
    )
    assert len(set(results)) == 1, (
        f"expected single eid for all workers, got {set(results)}"
    )
