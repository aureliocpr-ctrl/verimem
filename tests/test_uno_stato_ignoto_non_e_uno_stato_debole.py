"""Un rango che non si conosce non e' un rango BASSO.

Trovato misurando la copertura dell'annullamento e finito altrove. Sullo store
vero, `2026-08-07`::

    stati nella tabella `_STATUS_RANK` :  7
    stati presenti nello store         : 12
    fatti vivi con stato NOTO          : 4442
    fatti vivi con stato IGNOTO        : 2540   (36%)

`user_manual` da solo ne fa **2493**, la seconda popolazione dello store — e
`scripts/bench_recall_self.py:21` lo dichiara gia' fuori dall'enum. Nessun
modulo di `verimem/` lo assegna: arriva da fuori.

=== LA CONSEGUENZA, contata e non dedotta ===
`heal_contradictions` (`contradiction.py:546`) e
`auto_supersede_on_contradiction` (`semantic.py:5578`) leggono il rango con
``_STATUS_RANK.get(status, 0)``. Uno stato che la tabella non conosce vale
quindi **0** — cioe' **piu' debole di `model_claim`, che vale 2**. Non e' un
caso limite: sullo store, fra le coppie non risolte con entrambi i fatti vivi,

    rango PARI    -> lasciate al giudizio umano : 80194
    rango DIVERSO -> decide l'auto-heal         :  7256
      di cui il PERDENTE ha stato IGNOTO        :   257
        227  vince model_claim (2)  ritira user_manual (0 per difetto)
         30  vince provisional (1)  ritira user_manual (0 per difetto)

e l'auto-heal **gira da solo**, nel dream worker (`auto_dream_worker.py:392`,
`principal="system:heal"`).

=== 🪞 E IL PUNTO E' CHE LA REGOLA DICE L'OPPOSTO DI QUEL CHE FA ===
La docstring di `auto_supersede_on_contradiction` chiama la regola NON
NEGOZIABILE e la enuncia cosi': «*a weak/unverified claim can never invalidate
a stronger one*». Per i 2540 fatti a stato ignoto fa **esattamente il
contrario**, e non per un errore di logica: perche' `.get(..., 0)` **traduce
«non lo so» in «vale poco»**. Sono due cose diverse, e solo una delle due
autorizza un ritiro.

REGOLA: se non conosci il rango di uno dei due lati, **non decidere** — e' lo
stesso posto in cui la funzione gia' si ferma quando i ranghi sono PARI, per la
stessa ragione (non sappiamo chi ha ragione). L'ignoto non e' piu' informativo
della parita': e' meno.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest


@pytest.fixture
def memoria(monkeypatch):
    d = tempfile.mkdtemp(prefix="rango_")
    for k in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, d)
    monkeypatch.setenv("HIPPO_OFFLINE", "1")
    from verimem.semantic import SemanticMemory
    return SemanticMemory()


def _metti(sm, testo: str, topic: str, stato: str | None = None):
    """Scrive un fatto e, se serve, gli impone lo stato via SQL.

    Lo stato si forza nel DB e non alla scrittura perche' i gate di scrittura
    riportano `verified` e `provisional` a `model_claim` quando mancano i
    riferimenti — misurato mentre costruivo questo banco, e senza saperlo si
    misurerebbe il gate di scrittura al posto della regola di ritiro.
    """
    from verimem.semantic import Fact
    f = Fact(proposition=testo, topic=topic)
    sm.store(f, purpose="banco")
    if stato is not None:
        con = sqlite3.connect(str(sm.db_path))
        con.execute("UPDATE facts SET status=? WHERE id=?", (stato, f.id))
        con.commit()
        con.close()
    return f


class TestLaViaDIRETTA:
    """`auto_supersede_on_contradiction`: il chiamante passa i candidati."""

    def test_uno_stato_ignoto_non_viene_ritirato_da_un_model_claim(
            self, memoria):
        """IL ROSSO: `user_manual` non e' nella tabella, quindi vale 0, quindi
        un `model_claim` lo supera e lo ritira."""
        perdente = _metti(memoria, "Il deposito ha 12 corsie.", "t/a",
                          "user_manual")
        vincitore = _metti(memoria, "Il deposito ha 15 corsie.", "t/a",
                           "model_claim")
        esito = memoria.auto_supersede_on_contradiction(
            vincitore.id, [perdente.id], principal="system:heal",
            reason="banco")
        assert esito["superseded"] == [], (
            "ha ritirato un fatto il cui rango non e' noto: " + str(esito))
        assert perdente.id in esito["skipped"]
        assert memoria.get(perdente.id).superseded_by is None

    def test_presidio_uno_stato_NOTO_e_piu_debole_viene_ancora_ritirato(
            self, memoria):
        """PRESIDIO: la funzione deve continuare a fare il suo mestiere dove il
        rango si conosce davvero. `legacy_unverified` (0) contro `model_claim`
        (2): il ritiro resta."""
        perdente = _metti(memoria, "Il magazzino ha 12 corsie.", "t/b",
                          "legacy_unverified")
        vincitore = _metti(memoria, "Il magazzino ha 15 corsie.", "t/b",
                           "model_claim")
        esito = memoria.auto_supersede_on_contradiction(
            vincitore.id, [perdente.id], principal="system:heal",
            reason="banco")
        assert esito["superseded"] == [perdente.id], esito
        assert memoria.get(perdente.id).superseded_by == vincitore.id

    def test_anche_il_VINCITORE_a_stato_ignoto_non_puo_decidere(self, memoria):
        """La simmetria, che e' la meta' che si dimentica: se non conosco il
        rango di CHI VINCE, non so nemmeno che sia piu' forte. Un
        `bootstrap_rule` non deve poter ritirare un `quarantined` solo perche'
        `-1 < 0`."""
        perdente = _metti(memoria, "Il piazzale ha 12 posti.", "t/c",
                          "quarantined")
        vincitore = _metti(memoria, "Il piazzale ha 15 posti.", "t/c",
                           "bootstrap_rule")
        esito = memoria.auto_supersede_on_contradiction(
            vincitore.id, [perdente.id], principal="system:heal",
            reason="banco")
        assert esito["superseded"] == [], esito


class TestLaViaAUTOMATICA:
    """`heal_contradictions`: quella che gira DA SOLA nel dream worker. Il
    rango lo calcola per conto suo, quindi curare solo l'altra via non
    basterebbe — e' la classe «chi ALTRO fa la stessa cosa?»."""

    def _coppia(self, sm, stato_a: str, stato_b: str, topic: str):
        from verimem.contradiction import ContradictionStore
        a = _metti(sm, f"Il sito {topic} ha 12 unita.", topic, stato_a)
        b = _metti(sm, f"Il sito {topic} ha 15 unita.", topic, stato_b)
        store = ContradictionStore(sm.db_path)
        con = sqlite3.connect(str(sm.db_path))
        con.execute(
            "INSERT INTO contradictions (id, fact_a_id, fact_b_id, kind,"
            " similarity, detected_at) VALUES (?,?,?,?,?,?)",
            (f"c{topic}".replace("/", "")[:16], a.id, b.id, "numeric_clash",
             0.9, 1786000000.0))
        con.commit()
        con.close()
        return a, b, store

    def test_l_auto_heal_non_ritira_un_lato_a_rango_ignoto(self, memoria):
        from verimem.contradiction import heal_contradictions
        a, b, store = self._coppia(memoria, "user_manual", "model_claim", "t/d")
        esito = heal_contradictions(memoria, store, principal="system:heal")
        assert esito["healed_superseded"] == [], esito
        assert memoria.get(a.id).superseded_by is None

    def test_presidio_l_auto_heal_continua_a_curare_i_ranghi_noti(
            self, memoria):
        from verimem.contradiction import heal_contradictions
        a, b, store = self._coppia(memoria, "quarantined", "model_claim",
                                   "t/e")
        esito = heal_contradictions(memoria, store, principal="system:heal")
        assert esito["healed_superseded"] == [a.id], esito
