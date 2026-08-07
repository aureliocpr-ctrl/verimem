"""«cli:local» non e' un attore: e' una costante nel sorgente.

Seguito diretto del referto di ws4 delle 17:02 sul canale — *«il ramo che
ritira poggia su un'assunzione che il nostro uso viola: single-agent-per-tenant.
Noi siamo sette sullo stesso tenant e il prodotto ci vede come UNO»* — portato
sulla superficie che dovrebbe dirlo, che e' mia.

=== MISURATO PRIMA DI TOCCARE ===
    ritiri nello store            : 1814
      con una riga di audit       :  137   (7,6%)
      senza                       : 1677   (92,4%)
    e i 137 attribuiti si dividono in `cli:local` 111 e `system:heal` 26

Due difetti di natura diversa, e il secondo e' il peggiore:
  1. **copertura** — `by_principal` attribuisce il 7,6% dei ritiri, e il
     rapporto non e' dichiarato da nessuna parte: chi legge «cli:local 111»
     accanto a «(not recorded) 1677» puo' leggere 111 su 137 (81%) invece che
     111 su 1814 (6%);
  2. **risoluzione** — `verimem/cli.py` scrive ``principal="cli:local"``
     **inchiodato nel sorgente, in 11 punti**. Non e' un'identita': e' il nome
     della PORTA. Sette istanze che ritirano scrivono tutte la stessa stringa,
     e nessuna superficie potrebbe distinguerle.

=== 🔗 LA CURA ESISTE GIA' E NON ERA COLLEGATA ===
``VERIMEM_ACTOR`` e' documentato in `flow_events.py:19` come *«the agent's
label ... every one of its events arrives labeled — the single multi-agent
panel»*, ed e' letto da `flow_events`, `flow_tail` e `mcp_server`. **Il
percorso dei ritiri non lo consultava.** Prima domanda del filone: *«esiste
gia' e non e' collegato?»* — qui la risposta era si'.

⚠️ **E VA DETTO SUBITO**: l'attore arriva da una variabile d'ambiente, quindi
e' un'**ETICHETTA, non un'identita' autenticata** — chiunque puo' scriverci
quello che vuole. Serve a separare sette strumenti che collaborano, non a
rispondere a «chi e' stato» quando qualcuno mente. La stessa distinzione che
vale per il tag `actor` degli eventi.
"""
from __future__ import annotations

import sqlite3

import pytest


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    d = tmp_path / "dati"
    for k in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(d))
    monkeypatch.setenv("HIPPO_OFFLINE", "1")
    monkeypatch.delenv("VERIMEM_ACTOR", raising=False)
    monkeypatch.delenv("ENGRAM_ACTOR", raising=False)
    return monkeypatch


class TestIlPrincipaleDellaCLI:
    """`cli._principale()` — l'unico posto in cui la CLI decide chi dice di
    essere. Prima era la stessa costante ripetuta in undici punti."""

    def test_senza_attore_resta_il_nome_della_porta(self, ambiente):
        """PRESIDIO: chi non dichiara un attore non cambia comportamento, e i
        1814 ritiri gia' scritti restano leggibili come prima."""
        from verimem.cli import _principale
        assert _principale() == "cli:local"

    def test_con_l_attore_la_porta_RESTA_e_l_attore_si_aggiunge(self,
                                                               ambiente):
        """La porta non si perde: ws4 ha misurato la copertura del moat PER
        PORTA (CLI 99,2% contro MCP 69,5%), quindi sostituirla con l'attore
        spegnerebbe una misura che serve. Si aggiunge."""
        ambiente.setenv("VERIMEM_ACTOR", "ws7")
        from verimem.cli import _principale
        assert _principale() == "cli:local/ws7"

    def test_legge_anche_il_nome_storico(self, ambiente):
        """`ENGRAM_ACTOR` e' il nome legacy, e `flow_events` lo accetta gia':
        due porte che leggono la stessa cosa in modi diversi sono la classe (1)."""
        ambiente.setenv("ENGRAM_ACTOR", "ws3")
        from verimem.cli import _principale
        assert _principale() == "cli:local/ws3"

    def test_un_attore_smisurato_non_entra_nella_catena(self, ambiente):
        """`require_principal` rifiuta oltre 256 caratteri — e RIFIUTA, non
        tronca, «perche' un'identita' troncata e' un'identita' ambigua». Se il
        troncamento lo facessi qui, riporterei dentro proprio l'ambiguita' che
        quella guardia esiste per tenere fuori: quindi l'attore fuori misura si
        SCARTA, e resta la porta."""
        ambiente.setenv("VERIMEM_ACTOR", "x" * 400)
        from verimem.cli import _principale
        assert _principale() == "cli:local"

    def test_uno_spazio_o_una_barra_non_spezzano_il_campo(self, ambiente):
        """Il formato e' `porta/attore`: una barra dentro l'attore
        renderebbe la lettura ambigua. Stessa forma della virgola che oggi mi
        ha gia' spezzato una riga di diagnosi."""
        ambiente.setenv("VERIMEM_ACTOR", " ws7/ombra ")
        from verimem.cli import _principale
        principale = _principale()
        assert principale.count("/") == 1, principale
        assert principale == "cli:local/ws7-ombra"


class TestLaSuperficieDichiaraQuantoAttribuisce:

    def _breakdown(self, ambiente):
        from verimem.retirement_log import retirement_breakdown
        from verimem.semantic import Fact, SemanticMemory
        sm = SemanticMemory()
        a = Fact(proposition="il deposito ha 12 corsie", topic="t/x")
        b = Fact(proposition="il deposito ha 15 corsie", topic="t/x")
        sm.store(a, purpose="banco")
        sm.store(b, purpose="banco")
        sm.supersede(a.id, b.id, principal="cli:local/ws7", reason="banco")
        # un secondo ritiro scritto a mano: NESSUNA riga di audit, come i 1677
        c = Fact(proposition="il piazzale ha 9 posti", topic="t/y")
        d = Fact(proposition="il piazzale ha 11 posti", topic="t/y")
        sm.store(c, purpose="banco")
        sm.store(d, purpose="banco")
        con = sqlite3.connect(str(sm.db_path))
        con.execute("UPDATE facts SET superseded_by=?, superseded_at=9.0,"
                    " superseded_reason='scritto a mano' WHERE id=?",
                    (d.id, c.id))
        con.commit()
        con.close()
        return retirement_breakdown(sm)

    def test_dichiara_il_RAPPORTO_e_non_solo_i_conteggi(self, ambiente):
        """Sullo store vero l'attribuzione copre il 7,6%: chi legge
        «cli:local 111» accanto a «(not recorded) 1677» puo' calcolare 81%
        invece di 6%. Il rapporto va detto, non lasciato calcolare."""
        out = self._breakdown(ambiente)
        assert "attribution" in out, sorted(out)
        att = out["attribution"]
        assert att["attributed"] == 1, att
        assert att["unattributed"] == 1, att
        assert att["share"] == 0.5, att

    def test_dichiara_che_il_principale_e_una_PORTA(self, ambiente):
        """Senza questa frase «cli:local 111» si legge come un attore solo."""
        nota = self._breakdown(ambiente)["attribution"]["note"].lower()
        assert "port" in nota or "porta" in nota, nota
        assert "verimem_actor" in nota, nota

    def test_su_zero_ritiri_la_quota_non_e_una_percentuale(self, ambiente):
        """FALSIFICAZIONE: zero su zero non e' 0% ne' 100%. Stessa regola di
        `concentration`, che su un corpus senza ritiri vale None."""
        from verimem.retirement_log import retirement_breakdown
        from verimem.semantic import SemanticMemory
        out = retirement_breakdown(SemanticMemory())
        assert out["attribution"]["share"] is None, out["attribution"]
