"""Il giudice della fascia non eredita il profilo di chi scrive.

Quando il punteggio del giudice locale cade nella fascia d'incertezza, la porta
di scrittura chiede un secondo giudizio al CLI ``claude`` trovato sulla macchina
(``band_escalation._score_via_claude``). Lanciato senza isolamento, quel CLI
carica il profilo di chi scrive: i suoi server MCP, i suoi hook e il suo
CLAUDE.md, che entra nel prompt del giudice. Allora il verdetto dipende da chi
scrive, e ogni coppia nella fascia accende un server in piu'.

``--safe-mode`` spegne queste personalizzazioni e lascia l'autenticazione
dell'abbonamento. ``--bare`` no: accetta solo una chiave API.

La cella non lancia nessun CLI: cattura la riga di comando che verrebbe eseguita.
Sta all'ingresso dell'escalation, non alla porta di scrittura: per arrivare alla
fascia dalla porta serve un punteggio vero del giudice fra 40 e 80, che una cella
senza modello non puo' produrre.

T209, 23-24/09. Si esegue cosi', dalla radice del checkout:

    python -m pytest tests/test_il_giudice_della_fascia_non_eredita_il_profilo.py -q -p no:randomly
"""
from __future__ import annotations

from types import SimpleNamespace

from verimem import band_escalation as be


def test_il_cli_della_fascia_parte_senza_il_profilo_di_chi_scrive(monkeypatch):
    monkeypatch.delenv("ENGRAM_BAND_LLM", raising=False)
    monkeypatch.setattr(be.shutil, "which", lambda _: r"C:\bin\claude.EXE")
    be._resolve_cli.cache_clear()
    # la cascata prova prima ollama: spento, cosi' la fascia arriva a claude
    monkeypatch.setattr(be, "_local_ollama_available", lambda: False)
    catturate = []

    def _finto_run(argomenti, *a, **k):
        catturate.append(list(argomenti))
        return SimpleNamespace(returncode=0, stdout="Score: 87\n", stderr="")

    monkeypatch.setattr(be.subprocess, "run", _finto_run)

    # il giudizio e' passato davvero di qui: senza questo, una riga vuota
    # darebbe la cella per buona
    assert be.escalate_band_score("la fonte dice X", "X") == 87.0
    assert len(catturate) == 1
    riga = catturate[0]
    assert "--safe-mode" in riga, riga
    assert "--bare" not in riga, riga
