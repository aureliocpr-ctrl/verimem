"""Un piano che oscilla fra due passi non e' un piano, e va detto.

Reperto dell'altra istanza (in sola lettura), verificato e risultato PIU' GRANDE
di come l'aveva visto. Misurato il 2026-08-01 su `hippo_plan_forward` partendo
dalle sei skill piu' frequenti nelle sequenze reali::

    CICLO  prob=0.3068  ['bbc513ccf05f', '6e9dfdd5d5c7', 'bbc513ccf05f', '6e9dfdd5d5c7']
    CICLO  prob=0.2338  ['cbdbd385abef', '6e9dfdd5d5c7', 'bbc513ccf05f', '6e9dfdd5d5c7']
    CICLO  prob=0.2231  ['6e9dfdd5d5c7', 'bbc513ccf05f', '6e9dfdd5d5c7', 'bbc513ccf05f']
    ...
    piani totali: 16 · con almeno una skill RIPETUTA: 11

**Undici piani su sedici** ripetono almeno una skill, e il piano con la
probabilita' PIU' ALTA in assoluto e' un ping-pong puro fra due id. Ci sono
anche auto-anelli (`anthropic-skil -> anthropic-skil`).

La causa non e' un difetto di implementazione, e' cosa il beam search
massimizza: la probabilita' della sequenza sulla matrice di transizione. Se A->B
e B->A sono entrambe frequenti — cioe' se due skill si usano spesso insieme — il
percorso piu' probabile e' alternarle all'infinito. Il «piano» diventa la
descrizione della coppia piu' frequente, ripetuta fino alla profondita' chiesta.

PERCHE' NON SI VIETANO I CICLI. Un ciclo puo' essere legittimo: «scrivi il test
-> eseguilo -> scrivi il test -> eseguilo» e' il loop TDD, non un errore.
Filtrarli toglierebbe piani veri per curare una presentazione. E scegliere una
penalita' sarebbe un numero deciso a occhio — l'errore gia' pagato tre volte
questa settimana con le soglie sui coseni.

Si espone il dato, come per `limiti_osservati` delle analogie e
`query_terms_matched` dei documenti: ogni piano dichiara quanti passi DISTINTI
contiene. Chi legge distingue da se' un piano che avanza da uno che oscilla, e
puo' filtrare col criterio che gli serve.

SECONDO REPERTO, stesso tool: la matrice contiene 558 id di skill mentre lo
store ne ha 325, e **519 di quei 558 non esistono**::

    episodi con skills_used: 216  |  id nella matrice: 558
    skill NELLO STORE: 325
    id nella matrice che NON esistono nello store: 519
      esempi: ['A1_anti_confab', 'A2_anti_hallucination', ...]

Sono nomi di REGOLE, non id di skill: gli episodi storici registravano in
`skills_used` cose che skill non erano. Un piano puo' quindi nominare passi che
nessuno potra' mai eseguire, e il chiamante non ha modo di accorgersene.
Anche qui si conta invece di filtrare: il tool dichiara quanti passi del piano
corrispondono a skill vive.
"""
from __future__ import annotations

from verimem.successor_repr import build_transition_matrix, forward_plan


def test_un_piano_dichiara_quanti_passi_sono_distinti():
    """Il caso misurato, in piccolo: due skill che si alternano sempre."""
    seqs = [["A", "B", "A", "B", "A"], ["B", "A", "B", "A"], ["A", "B", "A"]]
    ids, P = build_transition_matrix(seqs)
    piani = forward_plan("A", ids, P, depth=3, beam_width=2)
    assert piani, "nessun piano prodotto: il test non esercita niente"
    for path, _lp in piani:
        assert len(set(path)) < len(path), (
            "questo corpus produce SOLO ping-pong: se un piano qui ha tutti "
            f"passi distinti, il test non sta misurando il caso reale: {path}")


def test_il_tool_espone_i_passi_distinti_e_i_passi_vivi(monkeypatch):
    """La superficie MCP: `passi_distinti` e `passi_noti` accanto al piano.

    Senza, un ping-pong e un piano che avanza si leggono uguali — `path` e
    `prob` e basta."""
    import asyncio
    import json

    from verimem import mcp_server

    class _Ep:
        def __init__(self, s): self.skills_used = s

    class _Mem:
        def all(self, limit=None):
            return [_Ep(["A", "B", "A", "B"]), _Ep(["B", "A", "B"]),
                    _Ep(["A", "B", "A"])]

    class _Sk:
        # solo A esiste davvero: B e' un id storico, come i 519 misurati
        def all(self, status=None):
            class S:
                id, name, trigger, status = "A", "a", "t", "promoted"
            return [S()]

    class _Ag:
        memory, skills = _Mem(), _Sk()

    monkeypatch.setattr(mcp_server, "_ag", lambda: _Ag())

    async def _chiama():
        from mcp.types import CallToolRequest, CallToolRequestParams
        h = mcp_server.server.request_handlers[CallToolRequest]
        r = await h(CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(name="hippo_plan_forward",
                                         arguments={"start_skill": "A",
                                                    "depth": 3})))
        p = r.root if hasattr(r, "root") else r
        return json.loads([c.text for c in p.content if hasattr(c, "text")][0])

    out = asyncio.run(_chiama())
    assert out["plans"], out
    primo = out["plans"][0]
    assert primo["passi_distinti"] < len(primo["path"]), (
        f"il piano oscilla e non lo dichiara: {primo}")
    assert primo["passi_noti"] < len(primo["path"]), (
        f"il piano nomina passi che non sono skill vive e non lo dichiara: "
        f"{primo} — nello store c'e' solo A")


def test_un_conteggio_che_non_si_puo_fare_non_costa_il_piano(monkeypatch):
    """Trovato dalla suite intera, ed e' un difetto che avevo INTRODOTTO io.

    `passi_noti` e `n_skill_vive` hanno bisogno dello store delle skill, che
    questo ramo non aveva mai toccato: i sette test del tool montano un agente
    finto con la sola `memory`, e li ho fatti fallire tutti con
    `'_FakeAgent' object has no attribute 'skills'`.

    La cura non e' aggiustare i sette test — sarebbe curare il sintomo di un
    difetto mio. E' che un'informazione diagnostica non deve MAI costare la
    funzione: senza store i due numeri valgono None e il piano esce lo stesso.
    Stesso contratto del watchdog degli stalli, «observability ONLY, never
    raises». Un tool che muore perche' una diagnostica non trova il suo dato
    sarebbe peggio del difetto che quella diagnostica cura."""
    import asyncio
    import json

    from verimem import mcp_server

    class _Ep:
        def __init__(self, s): self.skills_used = s

    class _Mem:
        def all(self, limit=None):
            return [_Ep(["A", "B", "A"]), _Ep(["B", "A", "B"])]

    class _AgSenzaSkill:
        memory = _Mem()          # nessun attributo `skills`, come i test del tool

    monkeypatch.setattr(mcp_server, "_ag", lambda: _AgSenzaSkill())

    async def _chiama():
        from mcp.types import CallToolRequest, CallToolRequestParams
        h = mcp_server.server.request_handlers[CallToolRequest]
        r = await h(CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(name="hippo_plan_forward",
                                         arguments={"start_skill": "A"})))
        p = r.root if hasattr(r, "root") else r
        return json.loads([c.text for c in p.content if hasattr(c, "text")][0])

    out = asyncio.run(_chiama())
    assert "plans" in out, (
        f"senza lo store delle skill il tool non ha prodotto piani: la "
        f"diagnostica e' costata la funzione\n{out}")
    assert out["n_skill_vive"] is None, (
        f"un conteggio impossibile e' stato riportato come numero: {out}")
    assert out["plans"][0]["passi_noti"] is None, out["plans"][0]
    assert out["plans"][0]["passi_distinti"] >= 1, (
        "passi_distinti non dipende dallo store e deve esserci comunque")


def test_un_piano_che_avanza_non_viene_marcato_per_sbaglio():
    """Controprova: senza questa, «passi_distinti» potrebbe essere sempre
    minore della lunghezza per un errore di conteggio, e il campo direbbe
    «oscilla» su ogni piano."""
    seqs = [["A", "B", "C", "D"], ["A", "B", "C"], ["B", "C", "D"]]
    ids, P = build_transition_matrix(seqs)
    piani = forward_plan("A", ids, P, depth=3, beam_width=1)
    assert piani
    path = piani[0][0]
    assert len(set(path)) == len(path), (
        f"su un corpus senza cicli il piano ha una ripetizione: {path}")
