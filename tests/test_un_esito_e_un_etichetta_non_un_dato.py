"""`outcome` dice COM'E' ANDATA. I numeri stanno accanto, non dentro.

Misurato il 2026-07-31 sull'audit log di produzione (3909 chiamate vere):
**27 dei 52 valori distinti di `outcome` contengono cifre**::

    ok_n_live=0        ok_n_live=3       ok_n_live=34     ok_n_live=122
    ok_n_total=13      ok_n_total=161    backfilled=10
    ok_total=10149_chains=7             warm=True

La cardinalita' del campo cresce COI DATI, quindi nessuno puo' calcolare un
tasso di successo per tool: `hippo_summary_topic` risultava «100% di esiti non
ok» su quindici chiamate tutte riuscite, perche' ognuna aveva scritto il
proprio conteggio dentro il nome dell'esito. E' un aggregato che manda a
ottimizzare la cosa sbagliata — lo stesso genere di errore del «50% di
not_found» ritirato il giorno prima, che pero' li' era mio e qui e' del
formato.

Due meta', e servono entrambe:

* alla SORGENTE l'esito torna un'etichetta chiusa, e il numero viaggia in
  `detail`, dove si puo' leggere senza rompere l'aggregazione;
* in LETTURA i 78 giorni di log gia' scritti restano aggregabili — il campo
  storico si riduce alla sua famiglia. Curare solo la sorgente lascerebbe
  illeggibile tutto cio' che il prodotto ha registrato finora, che e' l'unica
  evidenza che abbiamo su come viene usato davvero.
"""
from __future__ import annotations

import json

from verimem.telemetry_analyzer import analyze_audit_log, famiglia_esito


def test_un_esito_senza_numeri_resta_se_stesso():
    """Le distinzioni VOLUTE non si perdono: `ok_new` e `ok_replaced` dicono
    due cose diverse e devono restare due etichette diverse."""
    for e in ("ok", "ok_new", "ok_replaced", "not_found", "rejected_empty",
              "cap_allow", "unknown_tool"):
        assert famiglia_esito(e) == e


def test_un_esito_col_dato_dentro_si_riduce_alla_famiglia():
    assert famiglia_esito("ok_n_total=161") == "ok"
    assert famiglia_esito("ok_n_live=0") == "ok"
    assert famiglia_esito("ok_total=10149_chains=7") == "ok"
    assert famiglia_esito("backfilled=10") == "backfilled"
    assert famiglia_esito("warm=True") == "warm"


def test_due_chiamate_riuscite_contano_come_UNA_famiglia(tmp_path):
    """Il difetto misurato: quindici chiamate riuscite di hippo_summary_topic
    producevano quindici esiti distinti, e nessun tasso calcolabile."""
    righe = [
        {"tool": "hippo_summary_topic", "caller_pid": 1, "ts": 1.0,
         "outcome": "ok_n_total=13", "latency_ms": 5.0},
        {"tool": "hippo_summary_topic", "caller_pid": 1, "ts": 2.0,
         "outcome": "ok_n_total=161", "latency_ms": 6.0},
        {"tool": "hippo_summary_topic", "caller_pid": 1, "ts": 3.0,
         "outcome": "rejected_empty", "latency_ms": 1.0},
    ]
    p = tmp_path / "mcp_audit.log"
    p.write_text("\n".join(json.dumps(r) for r in righe) + "\n",
                 encoding="utf-8")
    esiti = analyze_audit_log(p)["per_tool"]["hippo_summary_topic"]["outcomes"]
    assert esiti == {"ok": 2, "rejected_empty": 1}, esiti


def test_non_esplode_su_cio_che_non_e_una_stringa():
    assert famiglia_esito(None) == "unknown"
    assert famiglia_esito("") == "unknown"
    assert famiglia_esito(7) == "7"


def test_alla_sorgente_il_numero_finisce_in_detail(tmp_path, monkeypatch):
    """L'altra meta': il record NUOVO nasce gia' pulito, e il numero non si
    perde — si legge in `detail` invece che dentro il nome."""
    from verimem import mcp_server

    log = tmp_path / "audit.log"
    monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(log))
    mcp_server._audit("hippo_prova", {}, outcome="ok", detail={"n_total": 161})

    riga = json.loads(log.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert riga["outcome"] == "ok", riga
    assert riga["detail"] == {"n_total": 161}, riga


def test_senza_detail_il_record_non_porta_un_campo_vuoto(tmp_path, monkeypatch):
    """Un `detail: null` su ogni riga sarebbe peso e rumore su un file che
    cresce di 1.9 MB ogni due mesi."""
    from verimem import mcp_server

    log = tmp_path / "audit.log"
    monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(log))
    mcp_server._audit("hippo_prova", {}, outcome="ok")
    riga = json.loads(log.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert "detail" not in riga, riga
