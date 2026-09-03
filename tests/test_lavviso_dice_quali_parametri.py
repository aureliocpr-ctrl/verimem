"""La modalita' AVVISO deve dire QUALI PARAMETRI aveva la chiamata, non solo che
c'e' stata — e oggi non lo dice.

IL CONTRATTO CHIESTO (@lead-audit, 03/09 18:58): «accensione in modalita' AVVISO
— fail-open, ogni tool sconosciuto scrive una riga di log CON NOME E ARGOMENTI,
nessun blocco». Serve a classificare i 230 tool non ancora nella matrice: senza
sapere *come* vengono chiamati, la classificazione si fa a indovinare.

COSA C'E' OGGI. `_audit()` scrive `{ts, tool, caller_pid, args_hash, outcome,
error}`: gli argomenti sono passati per SHA256 troncato a 16 caratteri («cheap
PII shield»). ⇒ il nome c'e', gli argomenti NO — c'e' un'impronta che non si
inverte.

E IL TEST CHE GIA' ESISTE NON LO VEDE: `test_warn_mode_allows_but_audits`
sostituisce `_audit_capability_call` con una funzione di cattura, quindi
verifica che la funzione VENGA CHIAMATA — non che il log contenga qualcosa. Il
file di audit non lo apre nessuno. E' verde e resterebbe verde anche se il
record fosse vuoto.

⚠️ PERCHE' NON TOLGO L'HASH. Lo scudo PII e' deliberato e i payload possono
contenere testo dell'utente. La via che tiene insieme le due cose: registrare le
CHIAVI degli argomenti, non i valori. «quale tool, con quali parametri» basta a
classificare; il contenuto non serve e non va scritto. I flag di controllo
(`_capability_override`, `_user_confirmed`) sono gia' esposti a parte e non sono
PII.

QUESTO TEST E' IL RED di quella cura.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from verimem import mcp_server


def _righe(p: Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


class TestAvvisoDiceIParametri:
    """Il log della modalita' avviso deve bastare a classificare un tool."""

    def test_la_riga_porta_il_nome_del_tool(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Controllo POSITIVO: se questo fallisce, il banco non misura nulla e
        il test sotto non va letto."""
        log = tmp_path / "audit.log"
        monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(log))
        monkeypatch.setenv("ENGRAM_CAPABILITY_GATE", "warn")
        ok, _ = mcp_server._capability_gate(
            "hippo_tool_mai_classificato_xyz", {"query": "x", "limit": 3})
        assert ok is True, "in modalita' avviso la chiamata NON si blocca"
        righe = _righe(log)
        assert righe, f"nessuna riga scritta in {log}"
        assert any(r.get("tool") == "hippo_tool_mai_classificato_xyz"
                   for r in righe), f"il nome del tool non e' nel log: {righe}"

    def test_la_riga_dice_QUALI_parametri_aveva_la_chiamata(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """IL RED. Oggi il log porta `args_hash`, un'impronta che non si
        inverte: da li' non si sa se il tool e' stato chiamato con `query` o con
        `fact_id`, e la classificazione resta a indovinare."""
        log = tmp_path / "audit.log"
        monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(log))
        monkeypatch.setenv("ENGRAM_CAPABILITY_GATE", "warn")
        mcp_server._capability_gate(
            "hippo_tool_mai_classificato_xyz",
            {"query": "x", "limit": 3, "topic": "y"})
        righe = [r for r in _righe(log)
                 if r.get("tool") == "hippo_tool_mai_classificato_xyz"]
        assert righe, "controllo positivo fallito: nessuna riga per quel tool"
        chiavi = set()
        for r in righe:
            det = r.get("detail") or {}
            for c in (det.get("arg_keys") or []):
                chiavi.add(c)
        assert {"query", "limit", "topic"} <= chiavi, (
            f"la riga di audit non dice QUALI parametri aveva la chiamata: "
            f"chiavi trovate {sorted(chiavi)}. Il record porta solo "
            f"`args_hash`, che non si inverte — con quello i 230 tool non "
            f"classificati non si possono classificare. Le CHIAVI bastano e "
            f"non sono PII: i valori restano fuori.")

    def test_i_valori_NON_finiscono_nel_log(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Il presidio dell'altra meta': la cura non deve diventare una fuga di
        dati. Le CHIAVI si', i VALORI mai."""
        log = tmp_path / "audit.log"
        monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(log))
        monkeypatch.setenv("ENGRAM_CAPABILITY_GATE", "warn")
        segreto = "SEGRETO-DA-NON-SCRIVERE-4f2a"
        mcp_server._capability_gate(
            "hippo_tool_mai_classificato_xyz", {"query": segreto})
        testo = log.read_text(encoding="utf-8") if log.exists() else ""
        assert segreto not in testo, (
            "il VALORE di un argomento e' finito nel log di audit: lo scudo "
            "PII e' deliberato e va tenuto")
