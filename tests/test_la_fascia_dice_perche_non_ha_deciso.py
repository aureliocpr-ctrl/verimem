"""La fascia dice perche' il secondo giudice non ha deciso (W7-52).

Quando il punteggio del giudice locale cade nella fascia d'incertezza, la porta
di scrittura chiede un secondo giudizio al CLI ``claude``. Il 29/08 quel CLI,
su una macchina con la sessione OAuth scaduta, usciva con codice 1 e il
messaggio sullo stdout, con lo stderr vuoto (``docs/stato-reale/00-ESAME.md``,
W7-52). Il prodotto buttava tutto (``if r.returncode != 0: return None``), e la
scrittura finiva «held for review» senza nominare nessuna causa.

Il motivo e' un'ETICHETTA da un elenco chiuso (auth, unknown-flag, timeout,
no-cli, off, exception:<tipo>, unreadable), mai una riga copiata: il codice guarda
stdout e stderr per scegliere l'etichetta, e nella ricevuta non entra nessun byte
dell'uscita. Lo stdout porta la risposta del giudice sul contenuto del fatto, e
nessun contenuto del fatto finisce in una ricevuta. Il caso misurato del 29/08
diventa «exit 1 (auth)».

Le celle non lanciano nessun CLI: il comando e' finto. Il punteggio nella fascia
(60) e' iniettato come nel test della fascia che gia' esiste.

W7-52, 24/09. Si esegue cosi', dalla radice del checkout:

    python -m pytest tests/test_la_fascia_dice_perche_non_ha_deciso.py -q -p no:randomly
"""
from __future__ import annotations

from types import SimpleNamespace

from verimem import anti_confab_gate as g
from verimem import band_escalation as be
from verimem import grounding_gate as gg


def _revisione(monkeypatch, stdout, stderr, returncode=1):
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE_THRESHOLD", raising=False)
    monkeypatch.delenv("ENGRAM_GROUNDING_THRESHOLD", raising=False)
    monkeypatch.setenv("VERIMEM_CE_BAND_ENFORCE", "1")
    monkeypatch.delenv("ENGRAM_BAND_LLM", raising=False)
    monkeypatch.setattr(gg, "fact_grounding_score_ex", lambda *a, **k: (60.0, "local"))
    monkeypatch.setattr(be.shutil, "which", lambda _: r"C:\bin\claude.EXE")
    be._resolve_cli.cache_clear()
    monkeypatch.setattr(be, "_local_ollama_available", lambda: False)
    monkeypatch.setattr(
        be.subprocess, "run",
        lambda *a, **k: SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr))
    gate = g.run_validation_gate(
        proposition="The cache TTL is 30 minutes.",
        verified_by=["source-doc:x:1"], topic="t", agent=None,
        validate="fast", source="the config sets the cache TTL to 30 minutes",
    )
    in_revisione = [w for w in gate.warnings if w.get("layer") == "L4-review"]
    # siamo nel ramo giusto: senza questo, un avviso assente passerebbe per muto
    assert in_revisione, [w.get("layer") for w in gate.warnings]
    return " ".join(str(v) for w in in_revisione for v in w.values())


def test_la_revisione_nomina_l_uscita_del_cli_e_non_copia_lo_stdout(monkeypatch):
    # il caso misurato il 29/08: il messaggio sullo stdout, lo stderr vuoto
    stdout = "Failed to authenticate: OAuth session expired and could not be refreshed\n"
    testo = _revisione(monkeypatch, stdout=stdout, stderr="")
    assert "exit 1" in testo, testo
    assert "(auth)" in testo, testo
    assert "OAuth" not in testo, testo            # l'etichetta, non la riga


def test_la_revisione_nomina_l_opzione_sconosciuta(monkeypatch):
    # un CLI che non conosce --safe-mode (il limite dichiarato di T209): l'etichetta
    # entra nella ricevuta, nessun byte dell'uscita
    testo = _revisione(monkeypatch, stdout="the cache TTL is 30 minutes: Score: 90\n",
                       stderr="error: unknown option '--safe-mode'\n")
    assert "unknown-flag" in testo, testo
    assert "Score: 90" not in testo, testo
    assert "--safe-mode'" not in testo, testo
