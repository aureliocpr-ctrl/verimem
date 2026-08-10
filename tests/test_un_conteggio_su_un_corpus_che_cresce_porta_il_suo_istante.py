"""Tre istanze, tre numeri, e nessuno dei tre era sbagliato.

Il 2026-08-07 tre istanze hanno misurato **la stessa** quantita' — i
quarantinati recuperabili da ``requalify_quarantined`` — e hanno ottenuto::

    ws4    155 su 172
    ws7    164 su 220   (io, qualche ora prima)
    ws1    171 su 235   (16:35)
    ws7    171 su 236   (16:41, sei minuti dopo ws1)

Ne sono seguiti messaggi per riconciliarli, e ws1 ha proposto due cause
(«il DB e' cambiato» / «query invece della funzione»), nessuna delle due
verificata.

=== LA CAUSA, misurata ===
La popolazione **cresce mentre la si misura**. Quarantinati vivi nuovi, per
ora, nelle ultime 12 ore sullo store di casa::

    ore 11: 8 · ore 12: 1 · ore 13: 12 · ore 14: 5 · ore 15: 13 · ore 16: 6
    totale 45 in sei ore  ⇒  ~7,5 all'ora

e infatti i quattro numeri sono **monotoni crescenti nell'ordine in cui sono
stati presi**. Non erano in disaccordo: erano **la stessa misura in quattro
istanti diversi**, e nessuno dei quattro portava con se' il proprio istante.

=== 🔑 LA REGOLA ===
**Un conteggio su un corpus che cambia non e' un numero: e' un numero PIU' un
istante.** Senza l'istante non e' confrontabile — nemmeno con se stesso, e
soprattutto non fra istanze che lavorano in parallelo sullo stesso store.

⚠️ E non basta curarne uno: cinque osservabili di governo restituiscono
conteggi sullo stesso corpus vivo, e la domanda della classe ② e' *«chi ALTRO
fa la stessa cosa?»*. Questo banco la pone a tutte e cinque insieme.
"""
from __future__ import annotations

import sqlite3
import time

import pytest

#: ⚠️ Niente schema scritto a mano in questo banco. La prima stesura ne
#: costruiva uno e cadeva su `no such column: writer_role`: uno schema di
#: fantasia misura la mia idea della tabella, non la tabella. Le righe si
#: scrivono nello store che crea il PRODOTTO.


@pytest.fixture
def sm(tmp_path, monkeypatch):
    """Uno store VERO con tre fatti: uno vivo, uno ritirato, uno quarantinato.

    Le tre righe si scrivono in SQL sullo store creato dal prodotto: cosi' il
    banco misura le funzioni di governo sullo schema vero (che e' il punto)
    senza passare dai gate di scrittura, che riportano gli stati a
    `model_claim` e renderebbero le tre popolazioni una sola.
    """
    d = tmp_path / "dati"
    for k in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(d))
    monkeypatch.setenv("HIPPO_OFFLINE", "1")
    from verimem.semantic import SemanticMemory
    # ⚠️ PERCORSO ESPLICITO: senza, dentro la suite intera si finisce nella
    # cartella condivisa del run e il banco conta i ritiri degli altri test.
    memoria = SemanticMemory(db_path=d / "semantic" / "semantic.db")
    from verimem.semantic import Fact
    ids = {}
    for chiave, testo, topic in (
            ("a", "il deposito ha 12 corsie", "t/x"),
            ("b", "il deposito ha 10 corsie", "t/x"),
            ("c", "il piazzale ha 9 posti", "t/y")):
        f = Fact(proposition=testo, topic=topic)
        memoria.store(f, purpose="banco")
        ids[chiave] = f.id
    # ⚠️ Le righe le crea il PRODOTTO e in SQL si toccano solo i due campi che
    # servono. La prima stesura le inseriva a mano e ha inseguito tre NOT NULL
    # (`confidence`, `writer_role`, `source_episodes`) uno alla volta: indovinare
    # lo schema colonna per colonna e' il metodo sbagliato, non un dettaglio.
    con = sqlite3.connect(str(memoria.db_path))
    con.execute("UPDATE facts SET superseded_by=?, superseded_at=2.0,"
                " superseded_reason='same-source evolution',"
                " grounding_score=80.0 WHERE id=?", (ids["a"], ids["b"]))
    con.execute("UPDATE facts SET status='quarantined', grounding_score=12.0"
                " WHERE id=?", (ids["c"],))
    con.execute("UPDATE facts SET grounding_score=99.0 WHERE id=?", (ids["a"],))
    con.commit()
    con.close()
    return memoria


#: Le cinque porte che rispondono con un conteggio sul corpus VIVO.
def _osservabili(sm):
    from verimem.retirement_log import (
        quarantine_breakdown,
        retirement_breakdown,
        survivability_counts,
        verdict_mismatches,
    )
    return {
        "survivability_counts": lambda: survivability_counts(sm),
        "retirement_breakdown": lambda: retirement_breakdown(sm),
        "quarantine_breakdown": lambda: quarantine_breakdown(sm),
        "verdict_mismatches": lambda: verdict_mismatches(sm),
    }


class TestOgnunaPortaIlSuoIstante:

    @pytest.mark.parametrize("nome", [
        "survivability_counts", "retirement_breakdown",
        "quarantine_breakdown", "verdict_mismatches",
    ])
    def test_l_osservabile_dichiara_quando_ha_misurato(self, sm, nome):
        prima = time.time()
        esito = _osservabili(sm)[nome]()
        dopo = time.time()
        assert "measured_at" in esito, (
            f"{nome} restituisce un conteggio senza dire QUANDO: "
            f"chiavi = {sorted(esito)}")
        assert prima <= float(esito["measured_at"]) <= dopo, esito["measured_at"]

    def test_anche_requalify_quarantined(self, sm):
        """La quinta porta sta in un altro modulo — ed e' proprio quella su cui
        le istanze hanno prodotto quattro numeri diversi."""
        from verimem.admission_cleanup import requalify_quarantined
        prima = time.time()
        esito = requalify_quarantined(str(sm.db_path), dry_run=True)
        dopo = time.time()
        assert "measured_at" in esito, sorted(esito)
        assert prima <= float(esito["measured_at"]) <= dopo


class TestPresidio:

    def test_i_conteggi_non_cambiano(self, sm):
        """PRESIDIO: aggiungere l'istante non deve toccare i numeri. Una cura
        che cambia anche cio' che non c'entra e' una cura che nessuno puo'
        verificare."""
        esito = _osservabili(sm)["survivability_counts"]()
        assert esito["written"] == 3
        assert esito["servable"] == 1        # 'a' (b superseduto, c quarantinato)
        assert esito["retired"] == 1
        assert esito["quarantined"] == 1

    def test_l_istante_non_e_una_stringa_da_leggere_a_occhio(self, sm):
        """FALSIFICAZIONE: un `measured_at` scritto come '07/08 16:41' sembra
        piu' leggibile e NON e' confrontabile fra fusi orari ne' sottraibile.
        Deve essere un epoch."""
        v = _osservabili(sm)["survivability_counts"]()["measured_at"]
        assert isinstance(v, (int, float)) and not isinstance(v, bool)
        assert v > 1_600_000_000        # un epoch in secondi, non in millisecondi
        assert v < 100_000_000_000
