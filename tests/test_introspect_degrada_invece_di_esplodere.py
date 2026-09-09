"""T55 — `verimem introspect` deve degradare, non stampare un traceback.

`embedding.encode` solleva `EncodeDelegateUnavailable` quando il daemon di
encoding non c'e' e il caricamento in processo e' disabilitato
(`HIPPO_ENCODE_DELEGATE_ONLY=1`, che e' il modo in cui gira il server MCP —
`docs/LAUNCH_READINESS_AUDIT.md:33`). Il messaggio dell'eccezione lo dice
testualmente: **«caller must degrade»**.

`introspect` (`cli.py:2956`, `:2974`) non degrada: l'eccezione risale fino a
Typer e l'utente riceve ~40 righe di traceback con i locals dentro.

E la rete di sicurezza esiste **dodici righe piu' su nello stesso file**, sullo
stesso `encode`, con tanto di commento:

    cli.py:533   vec = embedding.encode("warmup probe")
    cli.py:534   except Exception as exc:  # noqa: BLE001 — report cleanly, no traceback

Come e' stato trovato: eseguendo alla porta i comandi che nessun test invoca
(`scripts/porte_provate.py` → `introspect` era «③ NOMINATO»), 2026-09-09.

⚠️ `xfail(strict=True)` E NON UN TEST ROSSO COMMITTATO: finche' il difetto c'e'
la CI resta verde e il debito resta visibile nel rapporto di pytest; il giorno
che la cura entra questo test **passa**, `strict` lo trasforma in un FAILED e
chi cura e' costretto a togliere il marcatore. Un `xfail` non strict, invece,
avrebbe nascosto entrambe le cose.
"""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from verimem import embedding
from verimem.cli import app


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.mark.xfail(strict=True, reason="T55: introspect non gestisce "
                                       "EncodeDelegateUnavailable — cura non ancora entrata")
def test_introspect_dice_una_riga_invece_di_un_traceback(runner: CliRunner, monkeypatch) -> None:
    """Alla porta: `verimem introspect <topic>` senza daemon di encoding."""
    def _esplode(*_a, **_k):
        raise embedding.EncodeDelegateUnavailable(
            "encode daemon unavailable and in-process cold-load is disabled "
            "(HIPPO_ENCODE_DELEGATE_ONLY=1) — caller must degrade")

    monkeypatch.setattr(embedding, "encode", _esplode)

    result = runner.invoke(app, ["introspect", "memoria"])

    # ⚠️ QUI C'ERANO DUE ASSERT CHE NON POTEVANO FALLIRE, e li lascio scritti
    #    perche' la lezione vale piu' del test:
    #        assert "Traceback" not in result.output
    #        assert "locals" not in result.output
    #    Con `CliRunner` l'eccezione NON finisce nell'output: finisce in
    #    `result.exception`, e il traceback di rich si vede solo quando il
    #    comando gira davvero in un terminale. I due assert passavano sempre —
    #    non perche' il prodotto degradasse, ma perche' il banco non poteva
    #    vederlo. Guardiani che mentono. Il criterio giusto alla porta e' che
    #    **l'eccezione non sfugga dal comando**.
    assert not isinstance(result.exception, embedding.EncodeDelegateUnavailable), (
        "l'eccezione risale fino a Typer invece di essere gestita: "
        f"{result.exception!r}")
    # e l'utente deve leggere UNA riga che dice che cosa manca
    assert "encode" in result.output.lower() or "daemon" in result.output.lower(), (
        "l'utente non capisce che manca il daemon di encoding:\n" + result.output[:400])
    # e il comando deve uscire con un codice di errore, non fingere successo
    # (la lezione di `facts restore`: un'operazione non avvenuta che esce 0)
    assert result.exit_code != 0


def test_CONTROLLO_il_banco_riproduce_davvero_il_guasto(runner: CliRunner, monkeypatch) -> None:
    """Il controllo positivo del test qui sopra: senza di questo, un `xfail`
    che fallisce per QUALUNQUE altro motivo sembrerebbe la stessa cosa.

    Qui verifico solo che la mia sostituzione morda: `embedding.encode`
    sostituito solleva davvero, e l'eccezione e' quella che dico io.
    """
    def _esplode(*_a, **_k):
        raise embedding.EncodeDelegateUnavailable("caller must degrade")

    monkeypatch.setattr(embedding, "encode", _esplode)
    with pytest.raises(embedding.EncodeDelegateUnavailable) as e:
        embedding.encode("qualunque cosa")
    assert "degrade" in str(e.value)
