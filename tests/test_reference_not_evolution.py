"""TDD — un fatto che CITA l'id di un altro non lo sta sostituendo.

Trovato addosso, oggi, facendo dogfooding. CLAUDE.md prescrive: "Fatti oltre
~2000 char eccedono la finestra dell'embedder -> accompagnali con un fatto
compatto che faccia da esca". Ho seguito il protocollo:

  2bd8341db295  "PERCHE' LA REGOLA claude -p NON HA MORSO..." (2993 char)
  80b1c4cb2fd3  "ESCA per il fatto 2bd8341db295: ... dettaglio nel fatto 2bd8341db295"

L'esca ha SUPERSEDUTO il fatto. Verificato: recall('perche la regola claude -p
non ha morso...') restituisce l'esca e NON il dettaglio. Cioe' il protocollo
raccomandato dal prodotto produce un puntatore a un fatto che il recall non
restituisce piu' — la stessa forma di fallimento che il prodotto esiste per
prevenire.

Il discriminante e' deterministico e non richiede semantica: il nuovo testo
CONTIENE l'id del vecchio. In quel caso il rilevatore lessicale/NLI non e' in
grado di distinguere "vedi X" da "X e' sbagliato", e allora non decide: ammette
il nuovo e NON ritira il vecchio. In caso di ambiguita' si CONSERVA, perche' la
perdita e' irreversibile e la ridondanza no — coerente col contratto che questo
codice si e' già dato ("a false conflict downgrades a true fact, the opposite of
the trust we sell").
"""
from __future__ import annotations

from verimem.supersession_policy import references_fact


def test_a_lure_that_names_the_fact_id_is_a_reference():
    assert references_fact(
        "ESCA per il fatto 2bd8341db295: le regole non venivano re-iniettate. "
        "Dettaglio completo nel fatto 2bd8341db295.", "2bd8341db295")


def test_a_correction_that_names_the_id_is_also_a_reference():
    """references_fact e' PURA: risponde solo "il testo cita questo id?", e una
    correzione cita. Cosa farne e' del chiamante, e la prima versione sbagliava:
    esentava anche le correzioni, quindi "CORREZIONE del fatto X: il valore e'
    200" lasciava vivo lo stored "100" accanto alla propria smentita. Due
    avversari indipendenti (glm-5.2, deepseek-v4-pro) hanno convergito su questo
    e avevano ragione: ora la guardia agisce SOLO sul verdetto NLI, mai su un
    conflitto deterministico. Vedi i test del router qui sotto."""
    assert references_fact(
        "CORREZIONE del fatto 39e4745d6ba8: la diagnosi era incompleta.",
        "39e4745d6ba8")


def test_no_mention_is_not_a_reference():
    assert not references_fact(
        "la full suite di verimem conta 8004 test passati", "2bd8341db295")
    assert not references_fact("", "2bd8341db295")


def test_partial_or_empty_ids_never_match():
    """Un id vuoto o troncato non deve trasformare ogni write in un riferimento
    (sarebbe la fine del supersede, non una guardia)."""
    assert not references_fact("parla di 2bd8341db295", "")
    assert not references_fact("parla di 2bd8341db295", "2bd")
    assert not references_fact("nessun id qui", None)


def test_case_insensitive_and_word_bounded():
    assert references_fact("vedi il fatto 2BD8341DB295 per il dettaglio",
                           "2bd8341db295")
    # un id che e' PREFISSO di un token piu' lungo non conta
    assert not references_fact("hash 2bd8341db295ffff non e' quel fatto",
                               "2bd8341db295")

# --- il call-site: DATO un conflitto, la guardia deve fermare il ritiro -----
#
# Il primo tentativo di test end-to-end era TEATRO, e la mutazione l'ha
# mostrato: neutralizzando references_fact il caso non cambiava, perche' su un
# DB con due fatti nessun giudice rileva un conflitto (il caso reale aveva 6291
# fatti e il giudice NLI col modello caricato). Riprodurre il GIUDIZIO non e' il
# punto: il punto e' che QUANDO il giudice segnala un conflitto, la guardia
# impedisca il ritiro di un fatto citato. Quindi il conflitto si inietta.


class _FakeFact:
    def __init__(self, fid, proposition, status="model_claim"):
        self.id = fid
        self.proposition = proposition
        self.status = status
        self.verified_by = ["qa:check_PASS"]
        self.created_at = 1000.0
        self.asserted_at = 1000.0


class _FakeStore:
    def __init__(self, facts):
        self._by_id = {f.id: f for f in facts}

    def get(self, fid):
        return self._by_id.get(fid)


class _FakeAgent:
    def __init__(self, facts):
        self.semantic = _FakeStore(facts)


def _route(new_text, old_facts, *, asserted_at=2000.0):  # noqa: ARG001
    """Chiama il router delle evoluzioni come lo chiama il gate, con i
    contradicting id già decisi dal giudice."""
    from verimem.anti_confab_gate import _route_evolutions

    supersede: list[str] = []
    conflicts = _route_evolutions(
        _FakeAgent(old_facts), ["qa:check_PASS"], asserted_at,
        [f.id for f in old_facts], supersede, "model_claim")
    return supersede, conflicts


def test_router_retires_a_true_same_source_evolution():
    """Controllo nullo del fix: senza citazione dell'id il supersede deve
    continuare a funzionare, altrimenti la guardia ha spento la feature."""
    old = _FakeFact("aaaaaaaaaaaa", "la full suite conta 7883 test passati")
    supersede, conflicts = _route("la full suite conta 8004 test passati", [old])
    assert supersede == ["aaaaaaaaaaaa"], (supersede, conflicts)


def test_router_still_retires_on_a_deterministic_clash_even_if_cited():
    """Il path lessicale NON ha la reference guard, per decisione presa dopo la
    review avversariale. Qui i conflitti li trovano i rilevatori DETERMINISTICI
    (anni, quantita', versioni, date, negazione): quando uno di quelli scatta
    c'e' un contrasto concreto, e nominare un id non lo cancella. Altrimenti
    "CORREZIONE del fatto X: il valore e' 200" lascerebbe vivo il vecchio 100 —
    esattamente il danno che glm-5.2 e deepseek-v4-pro hanno segnalato."""
    old = _FakeFact("2bd8341db295", "la full suite conta 7883 test passati")
    supersede, conflicts = _route(
        "CORREZIONE del fatto 2bd8341db295: la full suite conta 8004 test passati",
        [old])
    assert supersede == ["2bd8341db295"], (
        f"la citazione ha annullato un conflitto deterministico: "
        f"{supersede} / {conflicts}")


def test_reference_guard_is_scoped_to_the_nli_path_only():
    """Controllo di scopo: la reference guard vive SOLO nel path semantico, dove
    il verdetto e' l'opinione di un modello. Sul path lessicale la citazione non
    ha effetto, e questo test lo fissa: se qualcuno la ri-aggiunge qui, cade."""
    import inspect

    from verimem import anti_confab_gate as g

    src = inspect.getsource(g._route_evolutions)
    assert "references_fact(" not in src, (
        "la reference guard e' ricomparsa sul path deterministico: rompe la "
        "correzione legittima (review glm-5.2 + deepseek-v4-pro 2026-07-25)")
