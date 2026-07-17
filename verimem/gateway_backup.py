"""Backup/restore consistente della directory gateway (datacenter Fase 1).

Nessun deploy enterprise senza backup. Lo snapshot usa l'**online backup API**
di SQLite (``Connection.backup``): corretto anche con connessioni WAL aperte
e scritture concorrenti — una copia cieca dei file con un ``-wal`` separato
perderebbe le ultime transazioni. Ogni ``.db`` sotto la directory gateway
(keys + un file per tenant, la scommessa "un tenant = un file") viene
snapshottato singolarmente; un ``backup_manifest.json`` dichiara contenuto e
momento dello snapshot — verificabilità come per tutto il resto.

Restore = ricreare la struttura in una directory VUOTA (mai sovrascrivere
silenziosamente uno stato esistente) e ripartire: chiavi e store tornano
identici, il gateway riparte sugli stessi dati.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any

#: file di servizio SQLite da NON copiare mai (lo snapshot li rigenera)
_SQLITE_SIDECARS = (".db-wal", ".db-shm", ".db-journal")


def _snapshot_db(src: Path, dest: Path) -> None:
    """Snapshot consistente di un singolo SQLite via online backup API."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    src_conn = sqlite3.connect(f"file:{src}?mode=ro", uri=True, timeout=30.0)
    try:
        dst_conn = sqlite3.connect(dest)
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
    finally:
        src_conn.close()


def backup_gateway(data_dir: str | Path, dest: str | Path) -> dict[str, Any]:
    """Snapshot della directory gateway in ``dest``. Ritorna il manifest.

    Copre ``gateway_keys.db`` e ogni ``*.db`` sotto ``tenants/<id>/`` (inclusi
    eventuali entity-kg per-tenant). ``dest`` viene creata; se esiste già NON
    deve contenere un manifest precedente (uno snapshot non si sovrascrive:
    ogni backup ha la sua directory)."""
    data_dir = Path(data_dir)
    dest = Path(dest)
    if not data_dir.exists():
        raise FileNotFoundError(f"gateway data dir not found: {data_dir}")
    if (dest / "backup_manifest.json").exists():
        raise ValueError(
            f"destination already holds a snapshot: {dest} — "
            "one directory per backup, never overwrite")
    dest.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    for src in sorted(data_dir.rglob("*.db")):
        if src.name.endswith(_SQLITE_SIDECARS):
            continue
        rel = src.relative_to(data_dir)
        _snapshot_db(src, dest / rel)
        copied.append(str(rel).replace("\\", "/"))

    tenants = sorted({p.split("/")[1] for p in copied
                      if p.startswith("tenants/") and len(p.split("/")) > 2})
    manifest: dict[str, Any] = {
        "created_at": time.time(),
        "source": str(data_dir),
        "files": copied,
        "n_files": len(copied),
        "tenants": tenants,
        "n_tenants": len(tenants),
    }
    (dest / "backup_manifest.json").write_text(
        json.dumps(manifest, indent=1), encoding="utf-8")
    return manifest


def restore_gateway(snapshot: str | Path, target: str | Path) -> dict[str, Any]:
    """Ripristina uno snapshot in ``target`` (directory NUOVA o vuota — mai
    sovrascrivere silenziosamente uno stato gateway esistente). Ritorna il
    manifest dello snapshot ripristinato."""
    snapshot = Path(snapshot)
    target = Path(target)
    manifest_path = snapshot / "backup_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"not a gateway snapshot (no manifest): {snapshot}")
    if target.exists() and any(target.iterdir()):
        raise ValueError(f"restore target is not empty: {target}")
    target.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for rel in manifest.get("files", []):
        src = snapshot / rel
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return manifest


__all__ = ["backup_gateway", "restore_gateway"]
