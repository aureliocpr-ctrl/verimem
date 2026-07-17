"""Tier Documents/Sources — snapshot versionati-per-hash delle fonti.

Quarto store ISOLATO (come Tier C transcript_index): tiene gli snapshot grezzi
delle fonti/documenti (MD, articoli, pagine) FUORI dal corpus di recall accettato
(``semantic.db``). Serve a (a) continuità-MD versionata e (b) base d'ingest per
la distillazione gated -> facts con provenienza (fase successiva, NON qui).

Invarianti che questi test bloccano (TDD):
  1. ingest di un nuovo (source_id, content) -> version 1, is_new=True.
  2. ingest IDEMPOTENTE: stesso (source_id, content) -> NESSUNA nuova versione
     (is_new=False, stesso id, stessa version). content_hash = chiave di versione.
  3. ingest di content CAMBIATO sullo stesso source_id -> version incrementata, is_new=True.
  4. get_latest restituisce la versione piu' alta; list_versions e' ordinata.
  5. source_id diversi hanno versioning INDIPENDENTE.
  6. ISOLAMENTO: lo store di default e' un DB SEPARATO da CONFIG.semantic_db.

Hermetic: DB temporaneo, zero scrittura su ~/.verimem.
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem.documents import Document, DocumentStore, default_db_path


def test_ingest_new_returns_version_1(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "d.db")
    r = ds.ingest("notes/handoff.md", "contenuto iniziale del documento", uri="file://handoff.md")
    assert r["version"] == 1
    assert r["is_new"] is True
    assert r["id"]


def test_reingest_same_content_is_idempotent(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "d.db")
    r1 = ds.ingest("notes/handoff.md", "stesso identico contenuto")
    r2 = ds.ingest("notes/handoff.md", "stesso identico contenuto")
    assert r2["is_new"] is False, "stesso content -> niente nuova versione"
    assert r2["version"] == r1["version"] == 1
    assert r2["id"] == r1["id"], "deve ritornare la riga esistente"
    # nessun duplicato fisico
    with sqlite3.connect(tmp_path / "d.db") as c:
        n = c.execute("SELECT COUNT(*) FROM documents WHERE source_id='notes/handoff.md'").fetchone()[0]
    assert n == 1


def test_reingest_changed_content_bumps_version(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "d.db")
    ds.ingest("notes/handoff.md", "versione uno")
    r2 = ds.ingest("notes/handoff.md", "versione due, contenuto cambiato")
    assert r2["version"] == 2
    assert r2["is_new"] is True


def test_get_latest_returns_highest_version(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "d.db")
    ds.ingest("src", "v1")
    ds.ingest("src", "v2")
    ds.ingest("src", "v3 finale")
    latest = ds.get_latest("src")
    assert latest is not None
    assert latest.version == 3
    assert latest.content == "v3 finale"


def test_list_versions_ordered(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "d.db")
    ds.ingest("src", "a")
    ds.ingest("src", "b")
    versions = ds.list_versions("src")
    assert [d.version for d in versions] == [1, 2]
    assert versions[0].content == "a" and versions[1].content == "b"


def test_get_by_id_roundtrip(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "d.db")
    r = ds.ingest("src", "contenuto", uri="http://x", meta={"outlet": "TestPress"})
    doc = ds.get(r["id"])
    assert doc is not None
    assert doc.content == "contenuto"
    assert doc.uri == "http://x"
    assert doc.meta.get("outlet") == "TestPress"
    assert doc.content_hash, "il content_hash deve essere stampato"


def test_distinct_sources_independent_versioning(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "d.db")
    ds.ingest("a", "x")
    ds.ingest("b", "y")
    ds.ingest("a", "x2")
    assert ds.get_latest("a").version == 2
    assert ds.get_latest("b").version == 1


def test_get_latest_missing_source_returns_none(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "d.db")
    assert ds.get_latest("inesistente") is None
    assert ds.list_versions("inesistente") == []


def test_default_db_is_separate_from_semantic():
    from verimem.config import CONFIG
    p = default_db_path()
    assert p != CONFIG.semantic_db, "il tier documents NON deve coincidere col corpus accettato"
    assert "documents" in str(p).lower()


def test_same_content_different_sources_are_separate(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "d.db")
    r1 = ds.ingest("src1", "contenuto condiviso")
    r2 = ds.ingest("src2", "contenuto condiviso")
    assert r1["id"] != r2["id"], "stesso content ma source diverso = righe separate"
    assert r1["is_new"] and r2["is_new"]


# --- ingest_file: caso d'uso "linka un MD -> Engram ne fa una copia" ---

def test_ingest_file_snapshots_content(tmp_path):
    md = tmp_path / "handoff.md"
    md.write_text("# Handoff\nstato del progetto v1", encoding="utf-8")
    ds = DocumentStore(db_path=tmp_path / "d.db")
    r = ds.ingest_file(md)
    assert r["version"] == 1 and r["is_new"] is True
    latest = ds.get_latest(str(md))
    assert latest is not None and "stato del progetto v1" in latest.content
    assert latest.meta.get("filename") == "handoff.md"


def test_ingest_file_idempotent_then_versions_on_change(tmp_path):
    md = tmp_path / "doc.md"
    md.write_text("contenuto originale", encoding="utf-8")
    ds = DocumentStore(db_path=tmp_path / "d.db")
    r1 = ds.ingest_file(md)
    r2 = ds.ingest_file(md)  # file invariato -> idempotente
    assert r2["is_new"] is False and r2["version"] == 1
    md.write_text("contenuto modificato", encoding="utf-8")
    r3 = ds.ingest_file(md)  # file cambiato -> nuova versione
    assert r3["is_new"] is True and r3["version"] == 2
    assert len(ds.list_versions(str(md))) == 2


def test_ingest_file_default_source_id_is_path(tmp_path):
    md = tmp_path / "x.md"
    md.write_text("y", encoding="utf-8")
    ds = DocumentStore(db_path=tmp_path / "d.db")
    r = ds.ingest_file(md)
    assert ds.get(r["id"]).source_id == str(md)


def test_ingest_file_explicit_source_id(tmp_path):
    md = tmp_path / "x.md"
    md.write_text("y", encoding="utf-8")
    ds = DocumentStore(db_path=tmp_path / "d.db")
    r = ds.ingest_file(md, source_id="canonical/handoff")
    assert ds.get(r["id"]).source_id == "canonical/handoff"


# --- list_sources + search: rendono il tier ISPEZIONABILE/USABILE (MCP/agent) ---

def test_list_sources_returns_latest_version_only(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "d.db")
    ds.ingest("a/x.md", "v1")
    ds.ingest("a/x.md", "v2 piu' lungo")
    ds.ingest("b/y.md", "altro")
    srcs = ds.list_sources()
    by_id = {s["source_id"]: s for s in srcs}
    assert set(by_id) == {"a/x.md", "b/y.md"}
    assert by_id["a/x.md"]["version"] == 2, "solo l'ultima versione per source_id"
    assert len(srcs) == 2, "una riga per source, non per versione"


def test_list_sources_exposes_filename_and_size(tmp_path):
    md = tmp_path / "handoff.md"
    md.write_text("# Titolo\ncorpo del documento", encoding="utf-8")
    ds = DocumentStore(db_path=tmp_path / "d.db")
    ds.ingest_file(md)
    s = ds.list_sources()[0]
    assert s["filename"] == "handoff.md"
    assert s["chars"] == len("# Titolo\ncorpo del documento")


def test_search_substring_case_insensitive(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "d.db")
    ds.ingest("notes/verimem.md", "Il flip embedding e5 ha portato il recall a 0.71")
    ds.ingest("notes/altro.md", "contenuto senza alcun riscontro")
    hits = ds.search("FLIP Embedding")
    assert len(hits) == 1
    assert hits[0]["source_id"] == "notes/verimem.md"
    assert "flip embedding" in hits[0]["snippet"].lower(), "lo snippet contiene il match"


def test_search_matches_only_latest_version(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "d.db")
    ds.ingest("doc", "qui c'e' parolavecchia da trovare")
    ds.ingest("doc", "ora contiene solo parolanuova")
    assert ds.search("parolavecchia") == [], "la v1 non e' piu' la latest"
    assert len(ds.search("parolanuova")) == 1


def test_search_respects_limit(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "d.db")
    for i in range(5):
        ds.ingest(f"src{i}", "match comune in tutti")
    assert len(ds.search("match comune", limit=3)) == 3


def test_search_empty_query_returns_empty(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "d.db")
    ds.ingest("s", "qualcosa")
    assert ds.search("") == []
    assert ds.search("   ") == []


def test_search_no_match_returns_empty(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "d.db")
    ds.ingest("s", "contenuto presente")
    assert ds.search("stringa-assolutamente-assente") == []


def test_search_multi_term_any_order_non_contiguous(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "d.db")
    ds.ingest("notes/e.md", "il flip dell'embedding e5 ha alzato il recall")
    # termini NON contigui + ordine invertito -> deve matchare (AND di termini),
    # non solo la frase esatta contigua.
    hits = ds.search("embedding flip")
    assert len(hits) == 1 and hits[0]["source_id"] == "notes/e.md"


def test_search_requires_all_terms(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "d.db")
    ds.ingest("a", "contiene alfa e beta insieme")
    ds.ingest("b", "contiene solo alfa qui")
    hits = ds.search("alfa beta")
    assert {h["source_id"] for h in hits} == {"a"}, "tutti i termini devono esserci (AND)"


def test_search_phrase_still_matches(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "d.db")
    ds.ingest("p", "la frase esatta flip embedding e5 qui")
    assert len(ds.search("flip embedding")) == 1
