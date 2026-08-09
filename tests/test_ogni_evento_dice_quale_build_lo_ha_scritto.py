"""Tre indagini in un giorno, finite tutte sullo stesso confondente.

Oggi, 2026-08-07, TRE domande diverse hanno avuto la stessa risposta — e
nessuna delle tre poteva essere risolta dal dato:

  1. «`heal_contradictions` non registra l'undo» — 11 ritiri su 11 senza
     scatto. **Falso**: eseguito su store isolato, la via produce
     `undo_op_id`. Le righe le aveva scritte un altro build.
  2. «solo 3 ritiri su 114 hanno un appiglio» (`doctor`, check
     `undo-window`). Stessa causa.
  3. «la telemetria e' MUTA sul `grounding_score` per sdk e gateway» (ws4,
     `a905bb84`). **Falso per questo build**: eseguito, una scrittura SDK con
     una fonte emette `grounding_score=98.59` e `judged=True`. Le 1499 righe
     di oggi senza `judged` non hanno nemmeno il campo `store` — introdotto
     stamattina — quindi vengono da un build precedente.

🔑 **Il dato dice A QUALE MEMORIA appartiene un evento (l'impronta dello
store, aggiunta stamattina) ma non DA QUALE CODICE e' stato prodotto.** E
quando piu' build scrivono nello stesso journal — cioe' sempre, qui — un campo
mancante e un difetto sono indistinguibili. Tre volte in un giorno, tre
istanze, e ogni volta la strada per uscirne e' stata *rieseguire il codice su
uno store nuovo*: cara, e non sempre possibile.

⚠️ **La REVISIONE, non il percorso.** L'impronta dello store e' un hash e non
un percorso per una ragione scritta nel modulo: quel campo finisce in file che
ci scambiamo e su una pagina web. La revisione corta e' gia' un'impronta —
identifica il codice e non dice dove abita chi lo esegue.
"""
from __future__ import annotations

import json
import subprocess

import pytest

from verimem import flow_events


@pytest.fixture(autouse=True)
def _pulisci():
    """L'impronta e il build si calcolano una volta per processo: senza
    ripulire, il primo test fissa il valore per tutti gli altri."""
    flow_events.reset_store_fingerprint()
    yield
    flow_events.reset_store_fingerprint()


class TestIlCampoCE:

    def test_ogni_evento_di_flusso_porta_il_build(self):
        visti = []
        flow_events.BUS_TEST = None      # niente: solo per leggibilita'
        from verimem.observability import BUS

        def orecchio(evt):
            visti.append(evt)

        BUS.subscribe("*", orecchio)
        try:
            flow_events.emit_flow("flow.prova", cosa="x")
        finally:
            BUS.unsubscribe("*", orecchio)
        assert visti, "l'evento non e' arrivato"
        p = visti[-1].payload
        assert "build" in p, (
            "un evento non dice da quale codice viene: chiavi = "
            + str(sorted(p)))
        assert p["build"], p["build"]

    def test_il_build_e_la_REVISIONE_e_non_un_percorso(self):
        """Il campo viaggia in file che ci scambiamo e su una pagina web —
        stessa ragione per cui l'impronta dello store e' un hash."""
        b = flow_events._build()
        assert "\\" not in b and "/" not in b, b
        assert "Users" not in b and "home" not in b, b
        assert len(b) <= 32, b

    def test_in_un_albero_git_e_la_revisione_corrente(self):
        """Su QUESTO albero deve coincidere con `git rev-parse --short=8 HEAD`
        — se non coincide il campo non identifica il codice, che e' tutto il
        suo scopo."""
        atteso = subprocess.run(
            ["git", "rev-parse", "--short=8", "HEAD"],
            capture_output=True, text=True, check=True).stdout.strip()
        assert flow_events._build() == atteso, flow_events._build()


class TestFuoriDaUnAlberoGit:

    def test_un_pacchetto_installato_dice_la_VERSIONE(self, monkeypatch):
        """FALSIFICAZIONE: la maggior parte delle installazioni NON e' un
        albero git. Un campo che li' resta vuoto non risolve niente — e un
        campo che INVENTA una revisione e' peggio del vuoto."""
        monkeypatch.setattr(flow_events, "_revisione_git", lambda: None)
        flow_events.reset_store_fingerprint()
        b = flow_events._build()
        assert b, "fuori da git il campo resta vuoto"
        from verimem import __version__
        assert __version__ in b, b

    def test_si_distingue_una_revisione_da_una_versione(self, monkeypatch):
        """Le due cose rispondono a domande diverse — «quale commit» e «quale
        release» — e confonderle rimetterebbe dentro l'ambiguita' che il
        campo esiste per togliere: due checkout della stessa release hanno la
        stessa versione e revisioni diverse."""
        monkeypatch.setattr(flow_events, "_revisione_git", lambda: None)
        flow_events.reset_store_fingerprint()
        senza_git = flow_events._build()
        flow_events.reset_store_fingerprint()
        monkeypatch.setattr(flow_events, "_revisione_git", lambda: "abcd1234")
        flow_events.reset_store_fingerprint()
        con_git = flow_events._build()
        assert senza_git != con_git
        assert con_git == "abcd1234"


class TestCosto:

    def test_si_calcola_UNA_volta_per_processo(self, monkeypatch):
        """`_ambient()` gira su OGNI evento: leggere `.git/HEAD` a ogni
        emissione sarebbe I/O per evento. Stessa cura dell'impronta dello
        store, che e' memorizzata in una variabile di modulo."""
        conta = {"n": 0}

        def finto():
            conta["n"] += 1
            return "abcd1234"

        monkeypatch.setattr(flow_events, "_revisione_git", finto)
        flow_events.reset_store_fingerprint()
        for _ in range(50):
            flow_events._build()
        assert conta["n"] == 1, f"letto {conta['n']} volte invece di 1"

    def test_l_emissione_non_si_rompe_se_il_calcolo_fallisce(self,
                                                             monkeypatch):
        """`emit_flow` NON solleva mai nel percorso di scrittura: e' il
        contratto del modulo, e un campo nuovo non lo cambia."""
        def esplode():
            raise OSError("albero illeggibile")

        monkeypatch.setattr(flow_events, "_revisione_git", esplode)
        flow_events.reset_store_fingerprint()
        flow_events.emit_flow("flow.prova", cosa="x")   # non deve sollevare
        assert flow_events._build()


class TestFinoAlJournal:
    """Non basta il bus: il confondente si e' manifestato leggendo
    `events.jsonl`, quindi il campo deve arrivare FIN LA'."""

    def test_il_campo_arriva_nel_journal(self, tmp_path, monkeypatch):
        p = tmp_path / "events.jsonl"
        monkeypatch.setenv("ENGRAM_EVENT_LOG", str(p))
        from verimem import event_jsonl_log
        monkeypatch.setattr(event_jsonl_log, "EVENT_LOG_PATH", p)
        flow_events.emit_flow("flow.prova", cosa="x")
        righe = [json.loads(r) for r in
                 p.read_text(encoding="utf-8").splitlines() if r.strip()]
        assert righe, "niente nel journal"
        assert righe[-1]["payload"].get("build"), righe[-1]
