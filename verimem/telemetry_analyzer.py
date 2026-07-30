"""Cycle #115.A — Analyze the MCP audit log into a per-tool ROI report.

The MCP server (cycle #115.A onwards) emits one JSONL record per call,
including `latency_ms`. This module aggregates the log into a tabular
report used by:

* the CLI `scripts/analyze_telemetry.py` (human + JSON output),
* Aurelio's ROI assessment of HippoAgent: which of the 209 MCP tools
  are actually called, how often, how slow.

The function is pure (no side effects) and tolerant of malformed lines
(skipped, not raised) so it can run safely on a partially-corrupted log.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _percentile(values: list[float], pct: float) -> float:
    """Linear-interpolation percentile (matches numpy.percentile default).
    `pct` in [0, 100]. Returns 0.0 on empty input."""
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * (pct / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    frac = k - lo
    return s[lo] + (s[hi] - s[lo]) * frac


#: Il tool-sonda che una suite chiama per verificare la risposta a un nome
#: inesistente. Un processo che lo invoca sta ESPLORANDO il server, non
#: usandolo: e' la firma piu' netta che si trovi nell'audit log per separare le
#: chiamate di test da quelle vere.
_SONDA_DI_SUITE = "does_not_exist"


def _pid_di_suite(records: list[dict[str, Any]]) -> set[Any]:
    """I processi che hanno chiamato la sonda: sono suite, non utenti."""
    return {r.get("caller_pid") for r in records
            if r.get("tool") == _SONDA_DI_SUITE}


#: I caratteri che cambiano cio' che si LEGGE senza cambiare cio' che c'e'
#: scritto. Trovato nell'audit log dell'8 giugno un `hippo_‮status`: il
#: server si e' difeso (`unknown_tool`, niente eseguito), ma a schermo quel nome
#: si legge al contrario. E' «Trojan Source» applicato a un registro.
#:
#: Allowlist, non blocklist: si tiene cio' che e' stampabile invece di elencare
#: cio' che qualcuno ha immaginato — la classe di difetto dominante trovata dal
#: critic-orchestrator, dove la cura e' sempre invertire il criterio.
#:
#: `str.isprintable()` non basta da solo: considera stampabili lo zero-width
#: space e i marcatori di direzione, che sono invisibili. Si scrivono ESCAPED
#: apposta — la prima stesura li aveva messi letterali dentro la stringa, e nel
#: sorgente quella riga appariva vuota. Curare l'invisibile scrivendolo
#: invisibile e' esattamente il difetto in questione.
_INVISIBILI = (
    "​"   # ZERO WIDTH SPACE
    "‎"   # LEFT-TO-RIGHT MARK
    "‏"   # RIGHT-TO-LEFT MARK
    "­"   # SOFT HYPHEN
)
def nome_leggibile(valore: Any) -> str:
    """Il nome come si vede in un rapporto: nessun carattere che sposti il
    cursore, inverta la direzione o fabbrichi una riga.

    Il DATO nel log resta grezzo — un audit e' evidenza, e riscriverlo
    perderebbe proprio cio' che uno vorrebbe poter dimostrare. Qui si sanifica
    la VISUALIZZAZIONE, e il carattere tolto si vede come escape invece di
    sparire: cancellarlo in silenzio nasconderebbe il tentativo.
    """
    if valore is None:
        return ""
    fuori = []
    for c in str(valore):
        if c.isprintable() and c not in _INVISIBILI:
            fuori.append(c)
        else:
            fuori.append(f"\\u{ord(c):04x}")
    return "".join(fuori)


def analyze_audit_log(path: Path | str, *,
                      include_suite: bool = True) -> dict[str, Any]:
    """Parse the JSONL audit log and return a per-tool aggregate.

    Returns::

        {
            "total_calls": int,
            "per_tool": {
                "<tool_name>": {
                    "count": int,
                    "latency_p50_ms": float,
                    "latency_p99_ms": float,
                    "latency_max_ms": float,
                    "n_unique_pids": int,
                    "outcomes": { "<outcome>": int, ... },
                },
                ...
            },
        }
    """
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return {"total_calls": 0, "per_tool": {}}

    per_tool_latencies: dict[str, list[float]] = defaultdict(list)
    # Le latenze di ogni tool RAGGRUPPATE per processo, nell'ordine in cui il
    # log le ha viste (append-only, quindi cronologico). Serve per il confronto
    # appaiato: vedi il commento sui campi first/later piu' sotto.
    per_tool_pid_seq: dict[str, dict[Any, list[float]]] = defaultdict(
        lambda: defaultdict(list),
    )
    per_tool_count: dict[str, int] = defaultdict(int)
    per_tool_pids: dict[str, set[int]] = defaultdict(set)
    per_tool_outcomes: dict[str, dict[str, int]] = defaultdict(
        lambda: defaultdict(int),
    )

    # QUANTO DI QUESTO LOG E' SUITE. Misurato il 2026-07-30 sull'audit log di
    # produzione: 10652 chiamate su 14560 (73.2%) venivano da 276 processi di
    # test. Contarle insieme alle altre non e' un dettaglio — fa dire cose
    # false: `hippo_skill_retire` risultava con il 50% di `not_found`, e i
    # not_found VERI erano UNO (la suite prova apposta anche il caso negativo).
    # Chi legge questo rapporto per decidere cosa ottimizzare deve poter
    # separare i due mondi.
    tutti = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                tutti.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    pid_suite = _pid_di_suite(tutti)
    saltate_perche_suite = 0

    total = 0
    for rec in tutti:
        if not include_suite and rec.get("caller_pid") in pid_suite:
            saltate_perche_suite += 1
            continue
        tool = rec.get("tool")
        if not tool:
            continue
        total += 1
        per_tool_count[tool] += 1
        outcome = rec.get("outcome", "unknown")
        per_tool_outcomes[tool][outcome] += 1
        pid = rec.get("caller_pid")
        if pid is not None:
            per_tool_pids[tool].add(int(pid))
        lat = rec.get("latency_ms")
        if isinstance(lat, (int, float)):
            per_tool_latencies[tool].append(float(lat))
            per_tool_pid_seq[tool][pid].append(float(lat))

    per_tool: dict[str, Any] = {}
    for tool, count in per_tool_count.items():
        lats = per_tool_latencies[tool]
        # PRIMA CHIAMATA CONTRO SUCCESSIVE, dentro lo stesso processo.
        #
        # Il p50 sopra NON descrive «quanto costa una chiamata», e il modo in
        # cui inganna e' subdolo: misurato il 2026-07-30, dal 18 luglio quasi
        # ogni processo fa UNA chiamata e muore (settimana W29: 101 usa-e-getta
        # su 106) perche' il client va in timeout e respawna, e il server
        # orfano finisce il lavoro e scrive comunque la sua riga.
        #
        # Quei processi non sono un campione casuale: SOPRAVVIVE CHI HA
        # RISPOSTO IN FRETTA. Chi era lento viene ucciso e resta con una riga
        # sola. Quindi ogni aggregato per-processo e' selezionato dalla
        # velocita' che pretende di misurare — guardare tutto insieme gonfia
        # (mediana 122699 ms sui troncati), guardare i soli longevi sgonfia.
        #
        # Il confronto appaiato regge perche' non passa fra processi diversi.
        # Cio' che questo codice stampa sul corpus vero, per hippo_facts_recall
        # (386 chiamate): p50 1a 75239 ms, p50 dopo 106 ms, 293 processi di cui
        # 256 con una chiamata sola. «Prima» qui vuol dire prima di QUESTO tool
        # nel processo, non prima in assoluto — con l'altra definizione lo
        # stesso corpus da' 88939 ms, ed e' un'altra domanda, non un altro
        # risultato.
        prime: list[float] = []
        dopo: list[float] = []
        soli = 0
        for _pid, seq in per_tool_pid_seq[tool].items():
            if not seq:
                continue
            if len(seq) == 1:
                soli += 1
            prime.append(seq[0])
            dopo.extend(seq[1:])
        per_tool[tool] = {
            "count": count,
            "latency_p50_ms": _percentile(lats, 50.0) if lats else 0.0,
            "latency_p99_ms": _percentile(lats, 99.0) if lats else 0.0,
            "latency_max_ms": max(lats) if lats else 0.0,
            # None, non 0.0: «nessun processo e' arrivato a una seconda
            # chiamata» e «le successive sono istantanee» sono due cose
            # diverse, e uno zero si legge come la seconda.
            "latency_p50_first_call_ms": (
                _percentile(prime, 50.0) if prime else None),
            "latency_p50_later_calls_ms": (
                _percentile(dopo, 50.0) if dopo else None),
            "n_single_call_pids": soli,
            "n_unique_pids": len(per_tool_pids[tool]),
            "outcomes": dict(per_tool_outcomes[tool]),
        }

    return {
        "total_calls": total,
        "per_tool": per_tool,
        # Sempre presenti, anche quando la suite e' inclusa: chi legge deve
        # sapere QUANTO di questo rapporto e' traffico di test, non doverlo
        # dedurre. Su un log dove i tre quarti delle chiamate vengono dai test,
        # un numero senza questo contesto manda a ottimizzare la cosa sbagliata.
        "suite_calls_excluded": saltate_perche_suite,
        "suite_pids_seen": len(pid_suite),
    }
