"""«Healthy» è la stessa parola su due scale diverse, e nessuna lo dice.

Misurato da ws4 il 2026-08-06 leggendo i due sorgenti, verificato qui:

    corpus_health_score.py:178   score   >= 75  -> "Healthy"   (50/30/…)
    memory_health_report.py:64   overall >= 80  -> "Healthy"   (60/40/…)

Stesse quattro etichette, due tagli. **Un corpus a 77 è «Healthy» per uno
strumento e «Acceptable» per l'altro.** E i due punteggi non sono nemmeno
confrontabili, perché sono somme pesate diverse:

    0.40·success + 0.30·promoted + 0.20·fitness + 0.10·connect
    0.40·episodi + 0.35·skill    + 0.25·fatti

⛔ **Non unifico i tagli**: sceglierne uno sarebbe una decisione travestita
da correzione, e quale dei due sia «giusto» non lo sa nessuno — i pesi
misurano cose diverse. Qui si dichiara: ogni verdetto esce con la scala
che lo ha prodotto e con la formula del punteggio, così chi legge due
referti può vedere che parlano due lingue invece di crederli d'accordo.

È la stessa forma della cura sulla banda contesa: una parola senza la sua
soglia si legge come un assoluto.
"""
from __future__ import annotations

from verimem.corpus_health_score import compute_health_score
from verimem.memory_health_report import generate_health_report


class _AgenteVuoto:
    """La firma vera è `compute_health_score(*, agent=...)`: legge
    `agent.skills` e `agent.memory`. Un agente senza nessuno dei due
    esercita il ramo che non dipende dai dati — qui interessa cosa il
    risultato DICHIARA, non quanto vale."""

    skills = None
    memory = None


def test_il_punteggio_del_corpus_dichiara_la_sua_soglia():
    out = compute_health_score(agent=_AgenteVuoto())
    assert "verdict" in out
    assert "75" in str(out.get("thresholds")), out
    assert "Healthy" in str(out.get("thresholds")), out


def test_il_referto_di_memoria_dichiara_LA_SUA_che_e_diversa():
    out = generate_health_report(episodes=[], skills=[], facts=[])
    assert "80" in str(out.get("thresholds")), out


def test_ognuno_dichiara_la_formula_perche_i_punteggi_NON_sono_confrontabili():
    """Due numeri sulla stessa scala 0-100 sembrano confrontabili e non lo
    sono: uno pesa success/promoted/fitness/connect, l'altro
    episodi/skill/fatti. Senza la formula accanto, «77 contro 82» si legge
    come un confronto."""
    a = compute_health_score(agent=_AgenteVuoto())
    b = generate_health_report(episodes=[], skills=[], facts=[])
    assert "0.40" in str(a.get("formula")) or "40" in str(a.get("formula")), a
    assert str(a.get("formula")) != str(b.get("formula")), (
        "due formule diverse devono LEGGERSI diverse")


def test_le_due_scale_restano_diverse_e_il_test_lo_pinna():
    """Guardia contro la correzione sbagliata: se un giorno qualcuno
    allinea i tagli, che sia una DECISIONE presa apposta e non un
    allineamento involontario — questo test cade e lo costringe a
    guardare."""
    a = compute_health_score(agent=_AgenteVuoto())
    b = generate_health_report(episodes=[], skills=[], facts=[])
    assert "75" in str(a["thresholds"]) and "80" in str(b["thresholds"]), (
        "i tagli sono cambiati: se e' voluto, aggiorna questo test e "
        "dichiara la scelta")


def test_la_scala_viaggia_col_verdetto_non_solo_nel_dizionario():
    """Chi stampa `verdict` da solo — ed è quello che fa una UI — deve
    poter dire da quale scala viene senza andare a cercarla."""
    out = compute_health_score(agent=_AgenteVuoto())
    assert out.get("verdict_scale"), out
    assert "corpus_health_score" in out["verdict_scale"], out
    altro = generate_health_report(episodes=[], skills=[], facts=[])
    assert altro["verdict_scale"] != out["verdict_scale"]
