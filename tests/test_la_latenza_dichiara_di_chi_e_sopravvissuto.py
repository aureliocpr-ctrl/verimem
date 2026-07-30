"""Il p50 delle latenze e' condizionato alla SOPRAVVIVENZA del processo.

Misurato il 2026-07-30 sull'audit log di produzione, per settimana::

    settimana     usa-e-getta  longevi  % getta  chiam/proc
      2026 W21              3       33       8%         8.5
      2026 W28             84       65      56%         1.6
      2026 W29            101        5      95%         1.2

Da fine luglio quasi ogni processo fa UNA chiamata e muore: il client va in
timeout e respawna il server (la race sulla prima ``tools/call`` diagnosticata
in parallelo), il server orfano finisce il lavoro e scrive la sua riga.

Il guaio non e' solo che i troncati sono tanti — e' che **non sono un campione
casuale**. Sopravvive chi ha risposto in fretta; chi era lento viene ucciso e
finisce fra gli usa-e-getta. Quindi:

* aggregare tutto insieme gonfia il p50 (mediana 122699 ms sui troncati),
* guardare solo i processi longevi lo sgonfia (14026 ms, e 192 ms in W29 su
  n=5), perche' quel campione E' definito dall'essere stato veloce.

Nessuna delle due mediane descrive «quanto costa una recall». Io stesso ho
riportato ad Aurelio «p50 41858 ms, quarantadue secondi mediani» prendendo il
primo numero per buono: e' la stessa classe di errore del «50% di not_found»
ritirato lo stesso giorno — un aggregato letto senza guardare da quali
processi venisse.

Un rapporto che stampa un p50 senza dire questo manda a ottimizzare la cosa
sbagliata. Il numero che REGGE e' appaiato — la prima chiamata contro le
successive DENTRO LO STESSO processo — perche' li' il confronto non passa fra
processi diversi selezionati dalla loro stessa velocita'.
"""
from __future__ import annotations

import json

from verimem.telemetry_analyzer import analyze_audit_log


def _log(tmp_path, righe):
    p = tmp_path / "mcp_audit.log"
    p.write_text("\n".join(json.dumps(r) for r in righe) + "\n",
                 encoding="utf-8")
    return p


def test_il_rapporto_dice_quanti_processi_hanno_UNA_SOLA_chiamata(tmp_path):
    """Il lettore deve poter vedere il regime, non dedurlo."""
    righe = [
        # tre processi usa-e-getta, lentissimi
        {"tool": "hippo_facts_recall", "caller_pid": 1, "ts": 1.0,
         "outcome": "ok", "latency_ms": 120000.0},
        {"tool": "hippo_facts_recall", "caller_pid": 2, "ts": 2.0,
         "outcome": "ok", "latency_ms": 90000.0},
        {"tool": "hippo_facts_recall", "caller_pid": 3, "ts": 3.0,
         "outcome": "ok", "latency_ms": 150000.0},
        # un processo longevo, veloce
        {"tool": "hippo_facts_recall", "caller_pid": 9, "ts": 4.0,
         "outcome": "ok", "latency_ms": 300.0},
        {"tool": "hippo_facts_recall", "caller_pid": 9, "ts": 5.0,
         "outcome": "ok", "latency_ms": 120.0},
    ]
    rep = analyze_audit_log(_log(tmp_path, righe))
    t = rep["per_tool"]["hippo_facts_recall"]
    assert t["n_single_call_pids"] == 3, t
    assert t["n_unique_pids"] == 4, t


def test_il_numero_APPAIATO_esce_accanto_al_p50(tmp_path):
    """Prima chiamata contro successive, dentro lo stesso processo: e' la sola
    misura che non passa fra processi selezionati dalla loro velocita'."""
    righe = [
        {"tool": "hippo_facts_recall", "caller_pid": 9, "ts": 1.0,
         "outcome": "ok", "latency_ms": 14000.0},   # 1a: cold
        {"tool": "hippo_facts_recall", "caller_pid": 9, "ts": 2.0,
         "outcome": "ok", "latency_ms": 200.0},
        {"tool": "hippo_facts_recall", "caller_pid": 9, "ts": 3.0,
         "outcome": "ok", "latency_ms": 100.0},
        {"tool": "hippo_facts_recall", "caller_pid": 7, "ts": 4.0,
         "outcome": "ok", "latency_ms": 12000.0},   # 1a: cold
        {"tool": "hippo_facts_recall", "caller_pid": 7, "ts": 5.0,
         "outcome": "ok", "latency_ms": 150.0},
    ]
    t = analyze_audit_log(_log(tmp_path, righe))["per_tool"]["hippo_facts_recall"]
    assert t["latency_p50_first_call_ms"] == 13000.0, t
    assert t["latency_p50_later_calls_ms"] == 150.0, t


def test_un_solo_processo_non_produce_un_confronto_finto(tmp_path):
    """Se nessun processo ha una seconda chiamata, il numero appaiato NON
    esiste e deve dirsi assente invece di uscire 0.0 — che si leggerebbe come
    «le successive sono istantanee»."""
    righe = [
        {"tool": "hippo_facts_recall", "caller_pid": i, "ts": float(i),
         "outcome": "ok", "latency_ms": 50000.0} for i in range(1, 4)
    ]
    t = analyze_audit_log(_log(tmp_path, righe))["per_tool"]["hippo_facts_recall"]
    assert t["latency_p50_later_calls_ms"] is None, t
    assert t["latency_p50_first_call_ms"] == 50000.0, t


def test_il_conto_dei_troncati_e_per_tool_non_globale(tmp_path):
    """Due tool sullo stesso processo non devono contarsi a vicenda i
    troncati: e' il tool a essere lento, non il pid."""
    righe = [
        {"tool": "hippo_facts_recall", "caller_pid": 1, "ts": 1.0,
         "outcome": "ok", "latency_ms": 9000.0},
        {"tool": "hippo_health", "caller_pid": 2, "ts": 2.0,
         "outcome": "ok", "latency_ms": 10.0},
        {"tool": "hippo_health", "caller_pid": 2, "ts": 3.0,
         "outcome": "ok", "latency_ms": 8.0},
    ]
    per = analyze_audit_log(_log(tmp_path, righe))["per_tool"]
    assert per["hippo_facts_recall"]["n_single_call_pids"] == 1
    assert per["hippo_health"]["n_single_call_pids"] == 0
