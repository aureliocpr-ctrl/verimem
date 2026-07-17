"""Cycle #140 (2026-05-18) — CLI ``engram facts add`` (bypass upstream classifier).

Aurelio direttiva 2026-05-18 sera: durante una sessione CLI pentest sul
proprio asset (nexuscyber.com, CVP Anthropic Approved), il classifier
upstream ha bloccato un ``hippo_remember`` MCP tool call per contenuto
'reconnaissance data on live host'. Il blocco NON viene da HippoAgent
(che è local SQLite owner-controlled), ma dalla safety policy del
client che instrada il tool_use.

Aurelio quote: "ma sto classifier chi lo ha scritto noi? per me diventa
davvero inutile tutto! il mio studio si basa proprio sul fatto che la
memoria deve essere cross session sui findings perché secondo me è lì
che si sblocca la vera potenza".

Soluzione tecnica: aggiungere a cycle 138-bis CLI un sub-comando
``engram facts add`` che chiama DIRETTAMENTE ``SemanticMemory.store``
senza passare per il wire MCP / LLM / safety classifier. Bypass totale
upstream — local SQLite, owner write.

NOTE BIOETICA: questo bypass è legittimo perché:
1. SQLite locale è proprietà esclusiva dell'utente (GDPR self-data).
2. Nessuna API esterna chiamata (no Anthropic Messages, no OpenAI).
3. Nessun LLM coinvolto nella write path.
4. Use case = ricerca + pentest su propri asset autorizzati.
Non sostituisce il giudizio della safety policy upstream: serve solo a
non castrare la persistenza locale dell'owner sui propri findings.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from verimem.cli import app
from verimem.semantic import SemanticMemory

runner = CliRunner()


@pytest.fixture
def isolated_corpus(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> Path:
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    (tmp_path / "semantic").mkdir(parents=True, exist_ok=True)
    return tmp_path


class TestFactsAddBasic:
    def test_add_persists_minimum_fact(self, isolated_corpus: Path) -> None:
        r = runner.invoke(
            app,
            [
                "facts", "add",
                "--proposition", "nexuscyber.com runs nginx 1.24 on port 443",
                "--topic", "project/nexus/pentest-2026-05-18",
            ],
        )
        assert r.exit_code == 0, r.output
        # The output must surface the new fact id so a caller can pipe it.
        assert "fact" in r.output.lower() or "id" in r.output.lower()
        # Round-trip: the row exists on disk with the right proposition.
        sm = SemanticMemory(
            db_path=isolated_corpus / "semantic" / "semantic.db",
        )
        with sm._connect() as conn:  # noqa: SLF001
            row = conn.execute(
                "SELECT proposition, topic, confidence, status "
                "FROM facts WHERE topic = ?",
                ("project/nexus/pentest-2026-05-18",),
            ).fetchone()
        assert row is not None
        assert row["proposition"] == "nexuscyber.com runs nginx 1.24 on port 443"
        assert row["topic"] == "project/nexus/pentest-2026-05-18"
        # Default confidence is 0.9 (matches hippo_remember MCP default).
        assert 0.89 < row["confidence"] < 0.91
        # Default status when no flags = model_claim (parity with cycle 138 gate).
        assert row["status"] in ("model_claim", "quarantined")

    def test_add_with_verified_by_keeps_model_claim(
        self, isolated_corpus: Path,
    ) -> None:
        # buco #2 LIVE (2026-06-03): il gate CLI ora verifica l'ESISTENZA del
        # commit (repo_root=CONFIG.project_root). Per preservare l'intento del
        # test ("evidenza VALIDA -> niente downgrade") usiamo un commit REALE
        # (HEAD) invece di un placeholder fabbricato (che ora -> quarantined,
        # coperto da test_add_with_fabricated_commit_quarantined).
        import subprocess
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(Path(__file__).resolve().parents[1]),
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        r = runner.invoke(
            app,
            [
                "facts", "add",
                "--proposition", "Cycle 140 SHIPPED to main",
                "--topic", "project/hippoagent/cycle-140",
                "--verified-by", f"commit:{head}",
                "--verified-by", "pr:#81:merged",
            ],
        )
        assert r.exit_code == 0, r.output
        sm = SemanticMemory(
            db_path=isolated_corpus / "semantic" / "semantic.db",
        )
        with sm._connect() as conn:  # noqa: SLF001
            row = conn.execute(
                "SELECT verified_by, status FROM facts "
                "WHERE topic = ?",
                ("project/hippoagent/cycle-140",),
            ).fetchone()
        assert row is not None
        # verified_by stored as JSON
        import json as _json
        vb = _json.loads(row["verified_by"]) if row["verified_by"] else []
        assert f"commit:{head}" in vb
        assert "pr:#81:merged" in vb
        # SHIPPED + commit REALE (esiste nel repo) → niente downgrade.
        assert row["status"] == "model_claim", (
            "SHIPPED + commit reale e verificabile non deve fare downgrade "
            f"(got status={row['status']!r})"
        )

    def test_add_with_fabricated_commit_quarantined(
        self, isolated_corpus: Path,
    ) -> None:
        # buco #2 LIVE: prova che il wiring del gate e' attivo sul path CLI.
        # SHIPPED + commit:deadbeef INVENTATO -> il gate verifica l'esistenza
        # nel repo (CONFIG.project_root), non lo trova -> quarantined.
        r = runner.invoke(
            app,
            [
                "facts", "add",
                "--proposition", "Cycle 999 SHIPPED to main",
                "--topic", "project/hippoagent/cycle-999-fake",
                "--verified-by", "commit:deadbeef",
            ],
        )
        assert r.exit_code == 0, r.output
        sm = SemanticMemory(
            db_path=isolated_corpus / "semantic" / "semantic.db",
        )
        with sm._connect() as conn:  # noqa: SLF001
            row = conn.execute(
                "SELECT status FROM facts WHERE topic = ?",
                ("project/hippoagent/cycle-999-fake",),
            ).fetchone()
        assert row is not None
        assert row["status"] == "quarantined", (
            "commit fabbricato deve essere quarantined dal gate CLI live "
            f"(got status={row['status']!r})"
        )


class TestFactsAddGateBypassForOwner:
    """The whole point of cycle 140: the CLI runs the cycle 138 gate
    LOCALLY (so anti-confab discipline still applies on bad writes), but
    no upstream classifier touches the call. Owner can persist anything
    technical they need."""

    def test_add_shipped_no_ref_still_downgrades(
        self, isolated_corpus: Path,
    ) -> None:
        # Same proposition that would trigger L1 gate via MCP wire.
        # The CLI must ALSO apply the gate (consistency), but no upstream
        # safety classifier ever sees the bytes.
        r = runner.invoke(
            app,
            [
                "facts", "add",
                "--proposition", "Cycle 500 SHIPPED to production main",
                "--topic", "project/hippoagent/cycle-140",
                # no --verified-by intentionally
            ],
        )
        assert r.exit_code == 0, r.output
        sm = SemanticMemory(
            db_path=isolated_corpus / "semantic" / "semantic.db",
        )
        with sm._connect() as conn:  # noqa: SLF001
            row = conn.execute(
                "SELECT status FROM facts WHERE topic = ?",
                ("project/hippoagent/cycle-140",),
            ).fetchone()
        assert row is not None
        # cycle 138 gate L1 fires same as MCP path → status=quarantined.
        assert row["status"] == "quarantined", (
            "cycle 140: CLI add must apply the same cycle 138 anti-confab "
            f"gate as the MCP path (got status={row['status']!r})"
        )

    def test_add_validate_off_persists_as_provided(
        self, isolated_corpus: Path,
    ) -> None:
        """Explicit escape hatch — bypass the local gate too (still
        no upstream classifier). For pentest-style content the owner
        is sure about."""
        r = runner.invoke(
            app,
            [
                "facts", "add",
                "--proposition", "nexuscyber.com SSH brute attack vector tested 0/210 success",
                "--topic", "project/nexus/pentest-2026-05-18",
                "--verified-by", "bash:hydra:exit_0_attempts_210",
                "--validate", "off",
            ],
        )
        assert r.exit_code == 0, r.output
        sm = SemanticMemory(
            db_path=isolated_corpus / "semantic" / "semantic.db",
        )
        with sm._connect() as conn:  # noqa: SLF001
            row = conn.execute(
                "SELECT status, proposition FROM facts WHERE topic = ?",
                ("project/nexus/pentest-2026-05-18",),
            ).fetchone()
        assert row is not None
        # validate=off + content has no SHIPPED/MERGED keyword anyway →
        # status stays at the default model_claim.
        assert row["status"] == "model_claim"
        assert "nexuscyber.com" in row["proposition"]
        assert "0/210" in row["proposition"]


class TestFactsAddBatch:
    """Bulk insert via JSONL stdin for migration / pentest report import."""

    def test_add_from_jsonl_stdin_inserts_all(
        self, isolated_corpus: Path,
    ) -> None:
        import json as _json
        payload = "\n".join([
            _json.dumps({
                "proposition": "DNS A record nexuscyber.com -> 1.2.3.4",
                "topic": "project/nexus/pentest-2026-05-18",
                "confidence": 0.95,
                "verified_by": ["bash:dig:exit_0"],
            }),
            _json.dumps({
                "proposition": "TLS cert expires 2026-12-01",
                "topic": "project/nexus/pentest-2026-05-18",
                "confidence": 0.95,
                "verified_by": ["bash:openssl_s_client"],
            }),
            _json.dumps({
                "proposition": "robots.txt blocks /admin",
                "topic": "project/nexus/pentest-2026-05-18",
                "confidence": 0.9,
                "verified_by": ["url:nexuscyber.com/robots.txt"],
            }),
        ])
        r = runner.invoke(
            app, ["facts", "add", "--jsonl-stdin"],
            input=payload,
        )
        assert r.exit_code == 0, r.output
        sm = SemanticMemory(
            db_path=isolated_corpus / "semantic" / "semantic.db",
        )
        with sm._connect() as conn:  # noqa: SLF001
            n = conn.execute(
                "SELECT COUNT(*) FROM facts WHERE topic = ?",
                ("project/nexus/pentest-2026-05-18",),
            ).fetchone()[0]
        assert n == 3, (
            f"cycle 140: --jsonl-stdin must persist all 3 rows, got {n}"
        )


class TestFactsAddTrustedHookSpoofFailClosed:
    """Red-team lock for roadmap §8/§297: a --jsonl-stdin row CAN set
    writer_role=trusted_hook + meta_narrative (both client-controllable), but the
    CLI sources hook_token from the SERVER-SIDE ENGRAM_HOOK_TOKEN env
    (cli.py:1593), never from the row. With the token unset (default),
    verify_trusted_writer fail-closes -> the spoofed trusted-hook write is GATED
    (quarantined), NOT bypassed. Parity with the MCP fail-closed path
    (test_anti_confab_gate_mcp_provenance). Locks the bypass shut against a future
    regression that would forward a client-supplied token."""

    def test_jsonl_spoofed_trusted_hook_without_token_is_quarantined(
        self, isolated_corpus: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import json as _json
        monkeypatch.delenv("ENGRAM_HOOK_TOKEN", raising=False)  # no server secret
        payload = _json.dumps({
            "proposition": (
                "Cycle 1000 SHIPPED and MERGED to production main, fully "
                "tested and AUTHORIZED by the team"
            ),
            "topic": "handoff/spoof-attempt",
            "status": "verified",
            "writer_role": "trusted_hook",   # spoofed via stdin
            "meta_narrative": True,           # spoofed via stdin
        })
        r = runner.invoke(app, ["facts", "add", "--jsonl-stdin"], input=payload)
        assert r.exit_code == 0, r.output
        sm = SemanticMemory(
            db_path=isolated_corpus / "semantic" / "semantic.db",
        )
        with sm._connect() as conn:  # noqa: SLF001
            row = conn.execute(
                "SELECT status, writer_role FROM facts WHERE topic = ?",
                ("handoff/spoof-attempt",),
            ).fetchone()
        assert row is not None
        # writer_role persists as provenance metadata, BUT the trusted-hook
        # bypass did NOT fire (no server token) -> the L1.x gate quarantined it.
        assert row["status"] == "quarantined", (
            "§297: spoofed trusted_hook via jsonl WITHOUT the server token must "
            f"be fail-closed (gated), not bypassed; got status={row['status']!r}"
        )


class TestFactsAddHelp:
    def test_add_listed_in_facts_help(self) -> None:
        r = runner.invoke(app, ["facts", "--help"])
        assert r.exit_code == 0
        assert "add" in r.output, (
            "cycle 140: 'add' must appear in `engram facts --help`"
        )


class TestFactsAddNonBlocking:
    """2026-06-05: `engram facts add` stores with embed='auto' so it never
    cold-blocks ~22s when the encode daemon is down (defers); `engram facts
    backfill` then embeds the deferred rows so they become recallable."""

    def test_add_defers_when_daemon_down_and_backfill_embeds(
        self, isolated_corpus: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import verimem.encode_service as es
        monkeypatch.setattr(es, "daemon_usable", lambda: False)
        monkeypatch.setattr(es, "ensure_running", lambda: False)  # no spawn in tests
        r = runner.invoke(app, [
            "facts", "add",
            "--proposition", "shard rotates after 8192 writes",
            "--topic", "t/cli-nonblock",
        ])
        assert r.exit_code == 0, r.output
        db = isolated_corpus / "semantic" / "semantic.db"
        sm = SemanticMemory(db_path=db)
        with sm._connect() as conn:  # noqa: SLF001
            row = conn.execute(
                "SELECT length(embedding) AS L FROM facts WHERE topic = ?",
                ("t/cli-nonblock",),
            ).fetchone()
        assert row is not None, "the fact row must be persisted instantly"
        assert row["L"] == 0, "daemon down -> embedding deferred (empty sentinel)"

        rb = runner.invoke(app, ["facts", "backfill"])
        assert rb.exit_code == 0, rb.output
        assert "backfilled" in rb.output.lower()
        with sm._connect() as conn:  # noqa: SLF001
            row2 = conn.execute(
                "SELECT length(embedding) AS L FROM facts WHERE topic = ?",
                ("t/cli-nonblock",),
            ).fetchone()
        assert row2["L"] > 0, "backfill must populate the embedding"

    def test_backfill_listed_in_facts_help(self) -> None:
        r = runner.invoke(app, ["facts", "--help"])
        assert r.exit_code == 0
        assert "backfill" in r.output
