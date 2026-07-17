"""audit#3-r3 R17: PUT /api/ide/file accepted an UNBOUNDED write body while the
read path (GET /api/ide/file) already refuses files >4MB. The asymmetry let an
(authenticated) client fill memory/disk with one request. Cap the written
content to the same 4MB ceiling and return 413.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from verimem.ide import FileWriteBody, ide_file_write


def test_ide_file_write_rejects_oversized_content(tmp_path, monkeypatch):
    monkeypatch.setenv("HIPPO_IDE_WORKSPACE", str(tmp_path))
    big = "x" * (4 * 1024 * 1024 + 1)
    with pytest.raises(HTTPException) as ei:
        ide_file_write(FileWriteBody(path="big.txt", content=big))
    assert ei.value.status_code == 413
    assert not (tmp_path / "big.txt").exists(), (
        "oversized write must be refused BEFORE touching disk"
    )


def test_ide_file_write_allows_small_content(tmp_path, monkeypatch):
    monkeypatch.setenv("HIPPO_IDE_WORKSPACE", str(tmp_path))
    res = ide_file_write(FileWriteBody(path="ok.txt", content="hello world"))
    assert res.status_code == 200
    assert (tmp_path / "ok.txt").read_text(encoding="utf-8") == "hello world"
