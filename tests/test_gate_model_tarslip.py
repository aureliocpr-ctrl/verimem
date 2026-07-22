"""tar-slip guard on the gate-model download (CodeQL py/tarslip, local_grounding).

Python 3.12+ extracts with tarfile's built-in ``filter="data"``; the pre-fix
py<3.12 fallback did a bare ``extractall()``, so a malicious model tarball with
a ``../`` member could write OUTSIDE the destination dir. ``_safe_tar_extract``
now validates every member on the fallback path too. These tests FORCE the
fallback (the local interpreter is 3.12+) by making ``extractall(..., filter=)``
raise ``TypeError``, exactly as an older Python would.
"""
from __future__ import annotations

import io
import tarfile

import pytest

from verimem import local_grounding as lg


def _make_tar(path, member_name: str, data: bytes = b"pwned") -> None:
    with tarfile.open(path, "w:gz") as t:
        info = tarfile.TarInfo(name=member_name)
        info.size = len(data)
        t.addfile(info, io.BytesIO(data))


def _force_pre312_fallback(monkeypatch) -> None:
    real = tarfile.TarFile.extractall

    def _no_filter(self, *args, **kwargs):
        if kwargs.get("filter") is not None:
            raise TypeError("simulating py<3.12: extractall has no filter kwarg")
        kwargs.pop("filter", None)
        return real(self, *args, **kwargs)

    monkeypatch.setattr(tarfile.TarFile, "extractall", _no_filter)


def test_fallback_refuses_parent_traversal(tmp_path, monkeypatch):
    _force_pre312_fallback(monkeypatch)
    evil = tmp_path / "evil.tar.gz"
    _make_tar(evil, "../escaped.txt")
    dest = tmp_path / "model"
    dest.mkdir()
    with tarfile.open(evil, "r:gz") as tar:
        with pytest.raises(Exception):
            lg._safe_tar_extract(tar, dest)
    assert not (tmp_path / "escaped.txt").exists(), "tar-slip escaped the dest dir"


def test_fallback_refuses_absolute_member(tmp_path, monkeypatch):
    _force_pre312_fallback(monkeypatch)
    evil = tmp_path / "abs.tar.gz"
    # an absolute-looking member; tarfile stores it stripped, but the resolved
    # target must still land inside dest — the guard rejects anything that won't
    _make_tar(evil, "sub/../../../etc/pwned.txt")
    dest = tmp_path / "model"
    dest.mkdir()
    with tarfile.open(evil, "r:gz") as tar:
        with pytest.raises(Exception):
            lg._safe_tar_extract(tar, dest)


def test_fallback_extracts_benign_members(tmp_path, monkeypatch):
    _force_pre312_fallback(monkeypatch)
    good = tmp_path / "good.tar.gz"
    _make_tar(good, "config.json", data=b"{}")
    dest = tmp_path / "model"
    dest.mkdir()
    with tarfile.open(good, "r:gz") as tar:
        lg._safe_tar_extract(tar, dest)
    assert (dest / "config.json").read_bytes() == b"{}"
