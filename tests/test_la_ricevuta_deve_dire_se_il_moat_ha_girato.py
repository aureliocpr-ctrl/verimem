"""`grounding_score = None` significa DUE cose, e non si distinguono.

L'ANOMALIA, misurata da ws5 e dimensionata qui sul corpus vero::

    scritti oggi              250
    con grounding NULL          6
       di cui SENZA fonte       2   <- corretto: niente fonte, niente verdetto
       di cui CON una fonte     4   <- IL DIFETTO: fonte dichiarata, moat non girato

Tre istanze hanno bruciato CINQUE ipotesi su questo fenomeno (il gate sotto
carico, delegate-only, la raffica, il `verified_by` vuoto, la source
condivisa): tutte cadute. Il motivo per cui è costato tanto è che **il verdetto
esiste al momento della scrittura e non viene conservato**, e `NULL` a
posteriori non dice quale dei due casi sia.

⚠️ E LA REGOLA DI CASA PROMETTE UN CAMPO CHE NON C'ERA. O3, testuale::

    «se un giorno un fatto torna `not run`, leggi il campo `moat` della
     ricevuta, che ora dice quale dei quattro casi è»

Misurato: la ricevuta di `add` aveva
``['adjudication','advice','grounding_score','id','status','stored','warnings']``
e nessun `moat`. L'unico `out["moat"]` in `client.py` sta dentro le STATISTICHE.

🔑 E IL CASO CHE CONTA È IL SECONDO: quando il giudice non è raggiungibile, il
gate emette `L4-skipped` — «source provided but no grounding judge is available,
entailment NOT verified» — **e il fatto entra lo stesso come `model_claim`**,
cioè ammesso. È un fail-open corretto come scelta (non si blocca una scrittura
perché il modello non è su disco) ma muto nel risultato: chi scrive crede di
aver messo un fatto verificato, e ha messo un claim.

Il campo `moat` non cambia il comportamento del gate: dichiara quale dei quattro
casi è stato.
"""
from __future__ import annotations

import pytest

import verimem.grounding_gate as gg
from verimem.client import Memory
from verimem.grounding_gate import NoGroundingJudge

FONTE = "Planimetria 2026: magazzino K-77, superficie 4200 metri quadrati."


@pytest.fixture()
def mem(tmp_path):
    return Memory(str(tmp_path / "s.db"))


@pytest.fixture()
def senza_giudice(monkeypatch):
    """Il giudice non raggiungibile: modello non su disco, OSError, import
    fallito. È la condizione che il gate già tollera — qui si verifica che il
    RISULTATO la dichiari."""
    def _no(*a, **k):
        raise NoGroundingJudge("giudice non caricabile")
    monkeypatch.setattr(gg, "fact_grounding_score_ex", _no)


def test_senza_fonte_il_moat_dichiara_di_non_aver_girato(mem):
    """Caso 1 dei quattro: nessuna fonte, nessun verdetto. È corretto, e ora
    si distingue dal caso 2."""
    r = mem.add("Il magazzino di Trento sara ampliato.", topic="az/x")
    assert r.get("moat") == "not_run:no_source", r.get("moat")
    assert r.get("grounding_score") is None


def test_con_fonte_e_giudizio_positivo(mem):
    """Caso 3: il moat ha girato e la fonte sostiene."""
    r = mem.add("Il magazzino K-77 ha 4200 metri quadrati.", topic="az/x",
                source=FONTE)
    assert r.get("moat") == "passed", r.get("moat")
    assert isinstance(r.get("grounding_score"), float)


def test_con_fonte_e_giudizio_NEGATIVO(mem):
    """Caso 4: il moat ha girato e ha trattenuto. Il verdetto c'è, il fatto no."""
    r = mem.add("Il magazzino K-77 ha 9999 metri quadrati.", topic="az/y",
                source=FONTE)
    assert r.get("moat") == "failed", r.get("moat")
    assert r.get("status") == "quarantined"


def test_IL_CASO_CHE_CONTA_fonte_dichiarata_e_giudice_assente(mem, senza_giudice):
    """⚠️ CASO 2 — il difetto misurato: 4 fatti su 250 sul corpus vero.

    Chi scrive passa una fonte, crede di aver messo un fatto verificato, e ha
    messo un claim. Il fatto entra (fail-open corretto: non si blocca una
    scrittura perché il modello non è su disco) e ora IL RISULTATO LO DICE."""
    r = mem.add("Il magazzino K-77 ha 4200 metri quadrati.", topic="az/z",
                source=FONTE)
    assert r.get("moat") == "not_run:no_judge", r.get("moat")
    assert r.get("grounding_score") is None
    assert r.get("stored") is True, "il fail-open resta: la scrittura non si blocca"


def test_il_warning_L4_skipped_resta(mem, senza_giudice):
    """IL PRESIDIO: il campo si AGGIUNGE al warning che c'era già, non lo
    sostituisce. Chi leggeva `L4-skipped` continua a leggerlo."""
    r = mem.add("Il magazzino K-77 ha 4200 metri quadrati.", topic="az/z",
                source=FONTE)
    assert "L4-skipped" in [w.get("layer") for w in (r.get("warnings") or [])]


def test_i_quattro_casi_sono_DISTINTI(mem, monkeypatch):
    """CONTROLLO POSITIVO sul senso della cura: se due casi collassassero
    sullo stesso valore, il campo non servirebbe a niente — ed è esattamente
    il difetto che cura (due cose diverse sotto un solo `NULL`)."""
    visti = set()
    visti.add(mem.add("Il deposito sara ampliato.", topic="a").get("moat"))
    visti.add(mem.add("Il magazzino K-77 ha 4200 metri quadrati.",
                      topic="b", source=FONTE).get("moat"))
    visti.add(mem.add("Il magazzino K-77 ha 9999 metri quadrati.",
                      topic="c", source=FONTE).get("moat"))

    def _no(*a, **k):
        raise NoGroundingJudge("x")
    monkeypatch.setattr(gg, "fact_grounding_score_ex", _no)
    visti.add(mem.add("Il magazzino K-77 ha 4200 metri quadrati.",
                      topic="d", source=FONTE).get("moat"))
    assert len(visti) == 4, sorted(str(v) for v in visti)
