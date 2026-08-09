"""Il contratto non spende contesto per dire cio' che e' gia' il default.

Misurato sul corpus vivo il 2026-07-30, 20 fatti veri: il payload e' passato da
6958 a 11273 byte (+62%, +215 per fatto) quando il contratto di uscita ha
iniziato a portare tutti i campi. Per un agente MCP quella crescita e' contesto
tolto al resto della conversazione, quindi va spesa dove informa.

Il verdetto, il tier del giudice e chi ha scritto il fatto la valgono. Due no:

    last_verified_at   valorizzato nel 96% delle righe, e il dataclass dichiara
                       che quando manca «freshness lo coalesce a created_at» —
                       quindi se coincide con created_at non dice niente
    writer_role        quasi sempre "agent_inference", che e' il default del
                       dataclass: ripeterlo e' rumore

Restano appena diversi dal default. Non e' un'ottimizzazione fine a se stessa:
e' lo stesso principio per cui i campi vuoti non escono — una chiave che non
cambia niente per chi legge e' peso senza informazione.
"""
from __future__ import annotations

from verimem.fact_contract import fact_payload
from verimem.semantic import Fact


def test_last_verified_at_uguale_a_created_at_non_esce():
    f = Fact(proposition="x", created_at=1000.0, last_verified_at=1000.0)
    assert "last_verified_at" not in fact_payload(f)


def test_last_verified_at_diverso_esce_SOLO_con_un_verdetto():
    """RISCRITTO il 2026-08-07, e la ragione conta piu' del test.

    Diceva: «una verifica successiva alla scrittura E' un'informazione»,
    e lo verificava su un fatto SENZA verdetto. Quella premessa e' stata
    misurata da ws5 sul corpus reale ed e' falsa: il campo avanza su 2762
    fatti e di quelli ZERO hanno un `grounding_score` — si muove solo dove
    un giudizio non c'e' mai stato (migrazione o re-embedding: un tocco).

    Combinato con la regola di emissione «esce se differisce da
    created_at», il contratto emetteva una chiave chiamata
    `last_verified_at` ESATTAMENTE sui fatti mai verificati. Questo test,
    verde, teneva in vita quel comportamento — che e' il modo in cui un
    banco protegge un difetto invece di un dato.

    Il caso che voleva difendere resta difeso: con un verdetto a
    sostenerlo, il campo esce."""
    senza = Fact(proposition="x", created_at=1000.0, last_verified_at=2000.0)
    assert "last_verified_at" not in fact_payload(senza)

    con = Fact(proposition="x", created_at=1000.0, last_verified_at=2000.0,
               grounding_score=98.0)
    assert fact_payload(con)["last_verified_at"] == 2000.0


def test_il_writer_role_di_default_non_esce():
    f = Fact(proposition="x")
    assert f.writer_role == "agent_inference"
    assert "writer_role" not in fact_payload(f)


def test_un_writer_role_dichiarato_esce():
    for ruolo in ("user", "system_hook", "trusted_hook"):
        f = Fact(proposition="x", writer_role=ruolo)
        assert fact_payload(f)["writer_role"] == ruolo


def test_il_verdetto_resta_sempre():
    """La sfoltitura non tocca cio' che il prodotto vende: il verdetto esce
    anche da vuoto, perche' «assente» e «mai giudicato» sono cose diverse."""
    p = fact_payload(Fact(proposition="x"))
    assert "grounding_score" in p and p["grounding_score"] is None
    assert "verified_by" in p


def test_il_payload_si_alleggerisce_su_un_fatto_ordinario():
    """Il caso comune: un fatto scritto e mai piu' toccato."""
    f = Fact(proposition="Il servizio ascolta sulla porta 8443.", topic="t",
             created_at=1000.0, last_verified_at=1000.0)
    p = fact_payload(f)
    assert "last_verified_at" not in p and "writer_role" not in p
    assert p["proposition"].endswith("8443.")
