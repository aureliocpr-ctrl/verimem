"""Il voto di salute epistemica non include una componente che nessuno ha misurato.

IL DIFETTO, in tre righe di codice::

    audit_one:      contested = bool(contested_fn(fact)) if contested_fn else False
    health_report:  uncontested_fraction = sum(1 for a in audits if not a.contested) / n
    health_report:  components.append(uncontested_fraction)      # SENZA `if`

`contested_fn` non era passato da NESSUN chiamante del pacchetto (misurato: 0
occorrenze fuori dal modulo; controllo positivo, `grounder=` 1) ⇒ `contested` era
`False` per ogni fatto ⇒ `uncontested_fraction` valeva `n/n = 1.0` **sempre** ⇒ ed era
l'unico componente che entrava nella media **senza condizione**.

MISURATO SUL CORPUS VERO prima della cura (`health_report` del prodotto, audit
costruiti da SQL in sola lettura)::

    limit=2000       composite **0.919**    grounded x coverage 0.839
    corpus intero    composite **0.79**     grounded x coverage **0.58**
    verifica della formula: (0.922 x 0.629 + 1) / 2 = 0.79   <- esatto

cioe' **meta' del voto era un 1.0 che nessuno aveva misurato**, e su un corpus senza
grounding ne' freschezza il composito usciva `mean([1.0]) = 1.0`.

⚠️ IL VOTO E' PUBBLICO: sta nella DESCRIZIONE dello strumento `hippo_epistemic_health`
(documentato in `docs/stato-reale/00-ESAME.md`, W2-141), quindi lo legge ogni client.

⚖️ E `False` per `contested` significa «NON contestato», cioe' un giudizio POSITIVO che
nessuno ha dato: e' esattamente cio' che il prodotto difende in `document_index`
(«absence stays absence, never a default that could read as a vouch nobody made»). La
dataclass gia' dichiarava la regola per `grounded`/`fresh` — «None when not checkable,
distinct from False» — e `contested` non era nell'elenco.
"""
from __future__ import annotations

from verimem.epistemic_health import FactAudit, audit_one, health_report


def _audit(**kw):
    base = dict(fact_id="f", has_source=True, grounded=True, fresh=None, contested=None)
    base.update(kw)
    return FactAudit(**base)


# ---- il voto non inventa il componente che manca -----------------------------

def test_senza_il_controllo_sulle_contestazioni_la_frazione_e_ignota():
    """Se nessuno ha controllato le contraddizioni, la frazione non e' 1.0: e' `None`.
    1.0 vorrebbe dire «li ho guardati tutti e nessuno era contestato»."""
    out = health_report([_audit(grounded=None, has_source=False)])
    assert out["uncontested_fraction"] is None, (
        f"non misurata ⇒ None, non 1.0: {out}")


def test_su_un_corpus_senza_niente_di_misurato_il_voto_e_ignoto():
    """🔑 LA CELLA CHE CONTA: nessun grounding, nessuna freschezza, nessun controllo
    sulle contestazioni ⇒ il composito e' `None`, non 1.0. Prima usciva un DIECI su
    un corpus di cui non si sapeva niente, accanto a `provenance_coverage 0.0`."""
    out = health_report([_audit(has_source=False, grounded=None)])
    assert out["composite"] is None, (
        f"su un corpus non misurato il voto non esiste: {out}")
    assert out["provenance_coverage"] == 0.0


def test_il_voto_non_e_gonfiato_dal_componente_non_misurato():
    """Con il solo grounding disponibile, il voto E' il grounding pesato — non la sua
    media con un 1.0 finto. Prima: (0.8*1.0 + 1)/2 = 0.9; adesso: 0.8."""
    out = health_report([_audit(grounded=True), _audit(grounded=True),
                         _audit(grounded=True), _audit(grounded=True),
                         _audit(grounded=False)])
    assert out["grounded_fraction"] == 0.8
    assert out["provenance_coverage"] == 1.0
    assert out["composite"] == 0.8, (
        f"il voto e' il grounding pesato, non la media con un 1.0 mai misurato: {out}")


def test_senza_contested_fn_il_verdetto_e_ignoto_non_falso():
    """La radice: nessun controllo iniettato ⇒ `contested` e' `None` («non l'ho
    guardato»), non `False` («l'ho guardato ed era pulito»).

    🪞 Avevo messo questa cella fra i CONTROLLI, e la falsificazione l'ha smentito:
    senza la cura cadono QUATTRO celle, non tre, e la quarta e' questa — perche'
    misura la cura, non cio' che la cura non deve rompere. Corretta l'etichetta, non
    il test: una sezione sbagliata avrebbe fatto leggere «la cura ha rotto un
    controllo» a chi guardava solo il conteggio.
    """
    a = audit_one({"id": "1", "proposition": "p", "source": "s"},
                  grounder=lambda s, p: 100.0)
    assert a.contested is None, (
        "senza contested_fn il verdetto non e' un giudizio positivo, e' un'assenza")


# ---- 🔑 COSA LA CURA NON DEVE ROMPERE ----------------------------------------

def test_quando_le_contestazioni_SONO_misurate_il_componente_entra():
    """CONTROLLO: chi passa `contested_fn` ha esattamente il comportamento di prima —
    la componente si calcola e pesa nella media."""
    a = audit_one({"id": "1", "proposition": "p", "source": "s"},
                  grounder=lambda s, p: 100.0, contested_fn=lambda f: False)
    b = audit_one({"id": "2", "proposition": "p", "source": "s"},
                  grounder=lambda s, p: 100.0, contested_fn=lambda f: True)
    assert a.contested is False and b.contested is True
    out = health_report([a, b])
    assert out["uncontested_fraction"] == 0.5, f"1 su 2 incontestato: {out}"
    assert out["composite"] == 0.75, f"media di 1.0 e 0.5: {out}"
