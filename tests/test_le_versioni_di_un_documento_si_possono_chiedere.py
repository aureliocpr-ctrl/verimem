"""Il tier versiona i documenti apposta, e la storia non si poteva chiedere.

`DocumentStore.ingest` e' idempotente sul contenuto e incrementa la versione
quando il contenuto cambia — «contenuto nuovo -> versione = max(version)+1».
Versionare e' una scelta esplicita del tier, non un effetto collaterale.

`DocumentStore.list_versions(source_id)` esiste dal principio e restituisce
ogni versione in ordine. Ma la stringa `list_versions` non compariva in
NESSUNA delle tre superfici:

    mcp_server.py  0
    cli.py         0
    client.py      0

Sei tool `hippo_document_*` — get, list, search, index_file, promote_chunk,
semantic_search — e nessuno che dica come un documento e' cambiato.
`document_get` da' UNA versione, `document_list` da' le fonti alla loro
versione piu' alta: chi indicizza lo stesso file due volte con contenuto
diverso ha due snapshot nel database e nessun modo di vederli.

E' la quinta della classe che `test_le_capacita_senza_porta_non_aumentano`
sorveglia — una capacita' matura raggiungibile solo da chi importa il modulo
Python — con l'aggravante che qui non e' un dettaglio di configurazione: e' la
ragione per cui il tier si chiama «versionato-per-hash».
"""
from __future__ import annotations

import asyncio
import json

import pytest

from verimem.documents import DocumentStore


@pytest.fixture()
def store_con_due_versioni(tmp_path, monkeypatch):
    """Lo stesso source_id ingerito due volte con contenuto diverso."""
    db = tmp_path / "documents.db"
    ds = DocumentStore(db)
    ds.ingest("roadmap.md", "# Roadmap\nPrima stesura.")
    ds.ingest("roadmap.md", "# Roadmap\nSeconda stesura, piu' lunga.")
    ds.ingest("altro.md", "Un documento senza storia.")

    import verimem.documents as mod
    reale = mod.DocumentStore
    monkeypatch.setattr(
        mod, "DocumentStore",
        lambda *a, **k: reale(db) if not a and not k else reale(*a, **k))
    return ds


def _mcp(nome: str, args: dict):
    from verimem import mcp_server as srv
    res = asyncio.run(srv.call_tool(nome, args))
    return json.loads(res[0].text)


def test_il_negozio_le_ha_sempre_avute(store_con_due_versioni):
    """Presupposto: la capacita' esiste, e' la porta che mancava."""
    v = store_con_due_versioni.list_versions("roadmap.md")
    assert [d.version for d in v] == [1, 2], v


def test_le_versioni_si_chiedono_dal_canale_MCP(store_con_due_versioni):
    out = _mcp("hippo_document_versions", {"source_id": "roadmap.md"})
    versioni = out if isinstance(out, list) else out.get("versions", out)
    assert len(versioni) == 2, out
    assert [r["version"] for r in versioni] == [1, 2], versioni


def test_ogni_versione_dice_QUANDO_e_quanto_e_grande(store_con_due_versioni):
    """Una storia senza date non e' una storia: `fetched_at` e la dimensione
    sono il minimo per capire quale versione si sta guardando. Il contenuto
    pieno NO — `document_get` esiste per quello, e una lista che porta ogni
    revisione intera diventa impraticabile su un file grosso."""
    out = _mcp("hippo_document_versions", {"source_id": "roadmap.md"})
    versioni = out if isinstance(out, list) else out.get("versions", out)
    prima = versioni[0]
    for campo in ("version", "content_hash", "fetched_at", "chars"):
        assert campo in prima, f"manca {campo}: {sorted(prima)}"
    assert "content" not in prima, "la lista non deve portare il contenuto pieno"


def test_un_documento_senza_storia_ne_ha_una_sola(store_con_due_versioni):
    out = _mcp("hippo_document_versions", {"source_id": "altro.md"})
    versioni = out if isinstance(out, list) else out.get("versions", out)
    assert len(versioni) == 1, out


def test_un_source_id_che_non_esiste_da_una_lista_vuota(store_con_due_versioni):
    """Non un errore: chiedere la storia di un documento mai ingerito e' una
    domanda legittima, e la risposta e' «nessuna versione»."""
    out = _mcp("hippo_document_versions", {"source_id": "mai-visto.md"})
    versioni = out if isinstance(out, list) else out.get("versions", out)
    assert versioni == [], out
