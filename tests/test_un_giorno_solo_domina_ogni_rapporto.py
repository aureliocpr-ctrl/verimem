"""Un rapporto su TUTTA la storia di un corpus non misura lo stato attuale.

Misurato sullo store vero il 2026-08-07, copertura dell'audit per giorno::

    2026-08-07    12 ritiri    12 con audit   100%
    2026-08-05    36           36             100%
    2026-08-04    22           22             100%
    2026-08-01    41           41             100%
    2026-07-31     5            5             100%
    2026-07-28    11           11             100%
    2026-07-25     5            5             100%
    2026-07-24     5            5             100%
    ------------------------------------------------
    **2026-07-02  1665            0             0%**
    2026-06-20     5            0               0%

**Dal 24/07 la copertura e' 100% su ogni singolo giorno. Un evento di massa in
UN giorno porta praticamente tutto il deficit** — ed e' quello che produce il
`7,6%` complessivo che avevo consegnato sul canale come se descrivesse lo stato
dell'audit. Il numero era giusto; la lettura che invita, no.

=== IL DIFETTO DELLA SUPERFICIE ===
`retirement_breakdown` **non accetta una finestra**. Prende `topic` e `limit`,
non `since` — mentre `retirement_log`, nello stesso modulo, ce l'ha. Quindi
ogni rapporto che quella superficie riporta (`attribution`, `by_reason`,
`by_scope`, `concentration`) e' calcolato su tutta la storia, e **un solo
giorno del passato lo domina per sempre**. Chi la interroga non ha modo di
chiedere «e di recente?».

🔑 E' la stessa forma del `measured_at` di stamattina: li' mancava **quando**
la misura e' stata presa, qui manca **su quale finestra** — e senza finestra un
rapporto non e' confrontabile con nessun altro.
"""
from __future__ import annotations

import sqlite3
import time

import pytest


@pytest.fixture
def sm(tmp_path, monkeypatch):
    """Uno store con UN evento di massa vecchio e pochi ritiri recenti —
    la forma dello store vero, in piccolo."""
    d = tmp_path / "dati"
    for k in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(d))
    monkeypatch.setenv("HIPPO_OFFLINE", "1")
    from verimem.semantic import Fact, SemanticMemory
    memoria = SemanticMemory()
    ora = time.time()
    vecchio = ora - 30 * 86400          # il giorno dell'evento di massa
    # ⚠️ PRIMA tutte le scritture del prodotto, POI le mie in SQL. Tenendo
    # aperta una seconda connessione DURANTE gli `store()` — con una UPDATE
    # non ancora committata, quindi una transazione di scrittura in corso —
    # il `conn.execute` di `semantic.py:3075` si blocca sul lock e il banco
    # resta appeso a tempo indefinito. Non e' lentezza: e' un deadlock, e da
    # fuori si vede identico a un test lento.
    coppie = []
    for n in range(12):
        a = Fact(proposition=f"il lotto {n} ha 12 pezzi", topic=f"m/{n}")
        b = Fact(proposition=f"il lotto {n} ha 15 pezzi", topic=f"m/{n}")
        memoria.store(a, purpose="banco")
        memoria.store(b, purpose="banco")
        coppie.append((n, a.id, b.id))
    con = sqlite3.connect(str(memoria.db_path))
    for n, a_id, b_id in coppie:
        # i primi 10 sono l'evento di massa, gli ultimi 2 sono di oggi
        quando = vecchio if n < 10 else ora - 3600
        motivo = "evento di massa" if n < 10 else "same-source evolution"
        con.execute("UPDATE facts SET superseded_by=?, superseded_at=?,"
                    " superseded_reason=? WHERE id=?",
                    (b_id, quando, motivo, a_id))
    con.commit()
    con.close()
    return memoria


def _breakdown(sm, **kw):
    from verimem.retirement_log import retirement_breakdown
    return retirement_breakdown(sm, **kw)


class TestLaFinestra:

    def test_la_superficie_accetta_una_finestra(self, sm):
        """IL ROSSO: `retirement_log` ha `since` dal primo giorno, questa no —
        due funzioni nello stesso modulo sulla stessa tabella, una sa fare una
        cosa che l'altra non sa."""
        out = _breakdown(sm, since=time.time() - 7 * 86400)
        assert out["by_reason"], out

    def test_dentro_la_finestra_l_evento_di_massa_sparisce(self, sm):
        """La prova che serviva: senza finestra il motivo dominante e'
        l'evento di massa; con la finestra, quello ordinario."""
        senza = _breakdown(sm)["by_reason"][0]["reason"]
        dentro = _breakdown(sm, since=time.time() - 7 * 86400)[
            "by_reason"][0]["reason"]
        assert senza == "evento di massa", senza
        assert dentro == "same-source evolution", dentro

    def test_la_finestra_vale_per_TUTTI_i_rapporti_non_solo_uno(self, sm):
        """Una finestra applicata a meta' dei campi sarebbe peggio di nessuna:
        chi legge la stessa risposta troverebbe due popolazioni diverse in due
        campi vicini, senza che niente lo dica."""
        out = _breakdown(sm, since=time.time() - 7 * 86400)
        assert sum(v["n"] for v in out["by_reason"]) == 2, out["by_reason"]
        assert sum(v["n"] for v in out["by_day"]) == 2, out["by_day"]
        assert out["attribution"]["attributed"] + \
            out["attribution"]["unattributed"] == 2, out["attribution"]

    def test_la_risposta_DICHIARA_la_finestra_che_ha_usato(self, sm):
        """Senza, due risposte identiche nella forma descrivono popolazioni
        diverse e nessuno se ne accorge — la stessa ragione per cui stamattina
        e' arrivato `measured_at`."""
        da = time.time() - 7 * 86400
        out = _breakdown(sm, since=da)
        assert out["since"] == da, out.get("since")
        assert _breakdown(sm)["since"] is None


class TestPresidio:

    def test_senza_finestra_il_comportamento_non_cambia(self, sm):
        """PRESIDIO: la chiamata di prima deve rendere esattamente quello di
        prima — 12 ritiri, evento di massa in testa."""
        out = _breakdown(sm)
        assert sum(v["n"] for v in out["by_reason"]) == 12
        assert out["attribution"]["attributed"] + \
            out["attribution"]["unattributed"] == 12

    def test_una_finestra_che_non_prende_niente_non_inventa_rapporti(self, sm):
        """FALSIFICAZIONE: zero ritiri nella finestra ⇒ nessuna quota, non 0%.
        Stessa regola di `concentration` e di `attribution.share`."""
        out = _breakdown(sm, since=time.time() + 3600)
        assert out["by_reason"] == []
        assert out["attribution"]["share"] is None, out["attribution"]
        assert out["concentration"]["share"] is None, out["concentration"]
