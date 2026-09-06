"""Il consolidamento notturno non ritira fra due fonti dichiarate e diverse.

LA TERZA PORTA. Il 2026-09-06 la cura sui 155/292 ritiri e' entrata nel GATE
(`_route_evolutions` e il ramo semantico), e misurando l'archivio e' venuto fuori
che **il 44% di quei ritiri non passa dal gate**::

    chi ha ritirato i 292          su tutti i 777 supersede in audit_mutations
    cli:local        154                      507
    system:heal      130                      209     <-- il consolidamento
    sdk:local         10                       63

`system:heal` e' `heal_contradictions`, chiamato da `auto_dream_worker`. E quella
strada **non guarda la fonte per niente**: prende le coppie dalla tabella
`contradictions` — non dal gate — e decide con `_rango_di_fiducia`. Curare il solo
gate lascia in piedi una porta su tre, e la riparazione dell'archivio si
disferebbe da sola.

⚠️ IL PERIMETRO E' LO STESSO DEL GATE, e deve restarlo: coesistenza SOLO quando
nessuno dei due lati dichiara un `verified_by` e le due `source_signature` sono
diverse. Un criterio diverso nelle due porte e' la classe di difetto numero uno
che abbiamo — «una copia invece della superficie unica» — quindi qui si CHIAMA
`due_fonti_dichiarate_e_diverse`, non si riscrive.

🔑 E LA COESISTENZA QUI NON RISOLVE LA CONTRADDIZIONE: la coppia resta
`unresolved`, come gia' accade per `skipped_equal_trust`. Marcarla risolta
direbbe «gestita», e nessuno l'ha gestita — e' il principio che il file
`contradiction.py` gia' applica al rango ignoto: «va nel SUO secchio e non fra
gli equal trust: contarlo li' sarebbe un'etichetta che porta una conclusione non
verificata».
"""
from __future__ import annotations

from verimem.contradiction import (
    Contradiction,
    ContradictionStore,
    heal_contradictions,
)
from verimem.semantic import Fact, SemanticMemory

FIRMA_A = "sha256:banco30ago-acceso"
FIRMA_B = "sha256:banco30ago-spento"


def _setup(tmp_path):
    db = tmp_path / "sm.db"
    return SemanticMemory(db_path=db), ContradictionStore(db)


def _coppia(mem, store, *, firma_debole, firma_forte):
    """I due bracci di un A/B, con trust DIVERSO perche' e' la condizione che
    fa scattare il ritiro: senza, la coppia uscirebbe da `skipped_equal_trust`
    e il banco non misurerebbe la fonte."""
    mem.store(Fact(id="braccioA", topic="ab/graded",
                   proposition="col graded acceso il gate ammette 296 falsi su 300",
                   status="legacy_unverified", source_signature=firma_debole))
    mem.store(Fact(id="braccioB", topic="ab/graded",
                   proposition="col graded spento il gate ammette 40 falsi su 300",
                   status="model_claim", source_signature=firma_forte))
    store.add(Contradiction(fact_a_id="braccioA", fact_b_id="braccioB",
                            kind="numeric_clash", similarity=0.95))


def test_heal_non_ritira_quando_le_due_fonti_sono_diverse(tmp_path):
    """I due bracci di un A/B non si archiviano a vicenda nel sonno."""
    mem, store = _setup(tmp_path)
    _coppia(mem, store, firma_debole=FIRMA_A, firma_forte=FIRMA_B)

    out = heal_contradictions(mem, store, principal="system:heal")

    assert out["healed_superseded"] == [], (
        "il consolidamento ha ritirato una misura vera: e' il difetto dei 292, "
        "e nel 44% dei casi passa proprio da qui")
    assert mem.get("braccioA").superseded_by is None
    # ⚠️ L'id della CONTRADDIZIONE, come negli altri secchi di questa funzione —
    # non quello del fatto. Asserito per valore, non con un `in str(...)`: un
    # controllo che puo' passare per la ragione sbagliata e' peggio di nessun
    # controllo, ed e' la forma che ci ha gia' fatto consegnare numeri falsi.
    assert out.get("skipped_fonti_distinte") == [
        Contradiction(fact_a_id="braccioA", fact_b_id="braccioB",
                      kind="numeric_clash", similarity=0.95).id], (
        f"tenuto vivo ma in silenzio, o nel secchio sbagliato: {out}")
    assert store.count_unresolved() == 1, (
        "la contraddizione NON e' stata gestita: marcarla risolta direbbe il "
        "contrario, ed e' il difetto che questo file esiste per non ripetere")


def test_heal_ritira_ancora_quando_la_fonte_e_LA_STESSA(tmp_path):
    """⚠️ IL GEMELLO OBBLIGATORIO. Senza, la cura sopra passerebbe smettendo di
    ritirare QUALUNQUE cosa — e una memoria che non ritira piu' nulla e' rotta
    quanto una che ritira tutto (misurato il 2026-08-03 su
    `ENGRAM_SUPERSEDE_SAME_SOURCE=0`)."""
    mem, store = _setup(tmp_path)
    _coppia(mem, store, firma_debole=FIRMA_A, firma_forte=FIRMA_A)

    out = heal_contradictions(mem, store, principal="system:heal")

    assert "braccioA" in out["healed_superseded"]
    assert mem.get("braccioA").superseded_by == "braccioB"
    assert store.count_unresolved() == 0


def test_heal_ritira_ancora_quando_una_penna_e_dichiarata(tmp_path):
    """Il perimetro e' lo stesso del gate: basta un `verified_by` su un lato per
    uscirne. Qui la penna c'e' su entrambi ed e' la stessa: aggiornamento."""
    mem, store = _setup(tmp_path)
    mem.store(Fact(id="vecchio", topic="listino",
                   proposition="l'abbonamento costa 100 euro al mese",
                   status="legacy_unverified", source_signature=FIRMA_A,
                   verified_by=["source-doc:billing:1"]))
    mem.store(Fact(id="nuovo", topic="listino",
                   proposition="l'abbonamento costa 150 euro al mese",
                   status="model_claim", source_signature=FIRMA_B,
                   verified_by=["source-doc:billing:1"]))
    store.add(Contradiction(fact_a_id="vecchio", fact_b_id="nuovo",
                            kind="numeric_clash", similarity=0.95))

    out = heal_contradictions(mem, store, principal="system:heal")

    assert "vecchio" in out["healed_superseded"], (
        "la stessa penna che aggiorna il proprio listino DEVE ancora ritirare")


def test_auto_supersede_ha_la_stessa_guardia(tmp_path):
    """`auto_supersede_on_contradiction` e' PUBBLICA e la chiama anche il gate
    MCP: la guardia va anche li', o la porta resta aperta da un'altra parte."""
    mem, _ = _setup(tmp_path)
    mem.store(Fact(id="braccioA", topic="ab/graded",
                   proposition="col graded acceso il gate ammette 296 falsi su 300",
                   status="legacy_unverified", source_signature=FIRMA_A))
    mem.store(Fact(id="braccioB", topic="ab/graded",
                   proposition="col graded spento il gate ammette 40 falsi su 300",
                   status="model_claim", source_signature=FIRMA_B))

    res = mem.auto_supersede_on_contradiction(
        "braccioB", ["braccioA"], principal="test:suite")

    assert res["superseded"] == [], f"ritirato dalla porta pubblica: {res}"
    assert mem.get("braccioA").superseded_by is None
    assert "braccioA" in res.get("fonti_distinte", []), (
        f"non ritirato, ma senza dire perche': {res}")


def test_auto_supersede_ritira_ancora_a_parita_di_fonte(tmp_path):
    """Il gemello della porta pubblica."""
    mem, _ = _setup(tmp_path)
    mem.store(Fact(id="braccioA", topic="ab/graded", proposition="296 falsi su 300",
                   status="legacy_unverified", source_signature=FIRMA_A))
    mem.store(Fact(id="braccioB", topic="ab/graded", proposition="40 falsi su 300",
                   status="model_claim", source_signature=FIRMA_A))

    res = mem.auto_supersede_on_contradiction(
        "braccioB", ["braccioA"], principal="test:suite")

    assert res["superseded"] == ["braccioA"]
    assert mem.get("braccioA").superseded_by == "braccioB"
