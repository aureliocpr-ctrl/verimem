"""TDD — fs_list_dir / fs_search_files devono applicare la deny-list _is_sensitive
(scan 68-Opus 2026-06-02). fs_read_file/fs_write_file gia la applicano; list/search NO
=> esponevano path (e fs_search anche il CONTENUTO via filtro `contains`) di file
sensibili (.pem/.key/ssh/aws/secrets) sotto la root.

HERMETIC: HIPPO_FS_ROOT puntato a tmp_path, nessun accesso al FS reale.
"""
from __future__ import annotations

from engram.tools_extra import fs_list_dir, fs_search_files


def test_fs_list_dir_hides_sensitive(tmp_path, monkeypatch):
    monkeypatch.setenv("HIPPO_FS_ROOT", str(tmp_path))
    (tmp_path / "notes.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "server.key").write_text("PRIVATE", encoding="utf-8")
    res = fs_list_dir("")
    names = [it["name"] for it in (res.extra or {}).get("items", [])]
    assert "notes.txt" in names, f"file normale assente: {names}"
    assert "server.key" not in names, f"file sensibile (.key) listato: {names}"


def test_fs_search_files_skips_sensitive(tmp_path, monkeypatch):
    monkeypatch.setenv("HIPPO_FS_ROOT", str(tmp_path))
    (tmp_path / "readme.md").write_text("token=public", encoding="utf-8")
    (tmp_path / "id_rsa.pem").write_text("token=SECRET", encoding="utf-8")
    res = fs_search_files("*", contains="token")
    matches = (res.extra or {}).get("matches", [])
    assert any("readme.md" in m for m in matches), f"file normale non trovato: {matches}"
    assert not any(m.endswith(".pem") or "id_rsa" in m for m in matches), \
        f"file sensibile (.pem) trovato/letto da fs_search: {matches}"
