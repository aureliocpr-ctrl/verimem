"""Un tool che non puo' riuscire deve dirlo, invece di rispondere «found».

Reperto dell'altra istanza (in sola lettura) il 2026-07-31: `hippo_find_analogues`
risponde `found: true` con `analogues: []` su 325 candidati. Guardando il codice,
`"found": True` e' letterale nel ramo di successo e il `False` esiste solo per il
target mancante — quindi il campo significa «il target esiste», non «ho trovato
analogie».

Ma il segnale che mente e' il sintomo. Misurando il corpus vero (325 skill,
20.000 coppie campionate) viene fuori che il tool **non puo' restituire nulla**,
per nessun target, con i suoi default::

    SEMANTIC su 20000 coppie di skill, indipendentemente dalla struttura:
      min=0.7425  p01=0.7816  p50=0.8561  max=1.0000
      coppie con semantic <= 0.5 (il vincolo del tool): 0
      coppie con semantic <= 0.7                      : 0

Il default `max_semantic=0.5` sta **sotto il minimo osservabile**. Non e' una
soglia severa: e' una soglia che nessuna coppia puo' soddisfare. E la ragione e'
strutturale, non un numero sfortunato — le due dimensioni sono misurate sullo
stesso testo (`name` + `trigger`), quindi si muovono insieme::

    correlazione structural~semantic su 20000 coppie: r = 0.7503
      structural in [0.0,0.1): n= 10595  semantic mediano=0.8365
      structural in [0.3,0.4): n=   475  semantic mediano=0.9221
      structural in [0.4,1.01): n=   326  semantic mediano=0.9610

    coppie con structural >= 0.4 (soglia di default): 326
      il loro SEMANTIC: min=0.8743  p50=0.9610  max=1.0000
      quante hanno semantic <= 0.5 (cioe' sono ANALOGIE): 0

Il regime che il tool cerca — «stessa forma procedurale, dominio diverso» —
richiede alto overlap lessicale E basso coseno; ma piu' l'overlap sale, piu' il
coseno sale. La congiunzione e' quasi vuota per costruzione del metodo di misura.

E' la TERZA volta in una settimana che una soglia assoluta su un coseno si
rivela irraggiungibile o inutile: il `noise_floor` 0.8706 dei documenti
(ritirato lo stesso giorno) e il `max(floor, noise_floor)` della mappa
dell'ignoranza. La cura che ha retto le altre due volte non e' un numero
migliore, e' **esporre il dato invece di giudicarlo**.

Quindi qui non si cambia una soglia — cambiarla a occhio ripeterebbe l'errore in
un'altra direzione — e non si cambia il significato di `found`, che ha 155
chiamate `ok` gia' registrate. Si aggiunge cio' che manca per capire::

    n_analogues            quante ne ha trovate (0 non e' piu' indistinguibile)
    limiti_osservati       il massimo structural e il minimo semantic VISTI sul
                           pool per questo target, che sono gia' calcolati e
                           venivano buttati

Con quei due numeri accanto ai vincoli richiesti, un chiamante vede da se' che
`max_semantic=0.5` contro un minimo osservato di 0.87 e' una domanda senza
risposta possibile — e puo' alzare la soglia con cognizione invece che a caso.
"""
from __future__ import annotations

from verimem.analogy import find_structural_analogues
from verimem.skill import Skill


def _skill(sid: str, nome: str, trigger: str) -> Skill:
    return Skill(id=sid, name=nome, trigger=trigger)


def test_la_scansione_riporta_gli_estremi_che_ha_visto():
    """Il dato che dice se il vincolo era raggiungibile e' gia' calcolato dentro
    il ciclo: veniva solo scartato."""
    target = _skill("t", "ruota le stringhe di tre posizioni",
                    "quando serve trasformare un testo")
    pool = [
        _skill("a", "ruota le stringhe di cinque posizioni",
               "quando serve trasformare un testo"),
        _skill("b", "prenota un tavolo al ristorante",
               "quando l'utente ha fame"),
    ]
    report: dict = {}
    out = find_structural_analogues(
        target, pool, semantic_cosine_fn=lambda a, b: 0.9,
        min_structural=0.4, max_semantic=0.5, report=report)
    assert out == [], "con semantic 0.9 e tetto 0.5 non puo' passare nessuno"
    assert report["n_candidates"] == 2
    assert report["max_structural"] > 0.4, (
        f"il candidato 'a' condivide quasi tutti i token col target, quindi un "
        f"massimo strutturale sopra la soglia c'era: {report}")
    assert report["min_semantic"] == 0.9, (
        f"il minimo semantico osservato e' il dato che spiega la lista vuota: "
        f"{report}")


def test_senza_report_la_firma_resta_quella_di_prima():
    """`report` e' opzionale: i chiamanti esistenti non cambiano di una riga."""
    target = _skill("t", "ruota le stringhe", "trasformare un testo")
    pool = [_skill("a", "ruota le stringhe di cinque", "trasformare un testo")]
    out = find_structural_analogues(
        target, pool, semantic_cosine_fn=lambda a, b: 0.1,
        min_structural=0.0, max_semantic=1.0)
    assert [c.id for c, _ in out] == ["a"]


def test_il_minimo_semantico_e_quello_dei_candidati_STRUTTURALMENTE_ammessi():
    """Precisazione che vale il test: il coseno si calcola solo per chi supera
    il filtro strutturale — e' cosi' che la funzione risparmia encode, e il
    report deve dire la verita' su cio' che ha VISTO, non stimare il resto.

    Se riportasse un minimo su tutto il pool, il numero costerebbe un encode per
    ogni skill dello store: si pagherebbe una diagnostica quanto la ricerca."""
    target = _skill("t", "alfa beta gamma", "delta epsilon")
    vicino = _skill("v", "alfa beta gamma zeta", "delta epsilon")
    lontano = _skill("l", "niente in comune qui", "proprio niente")
    visti: list[str] = []

    def _cos(a, b):
        visti.append(b.id)
        return 0.95

    report: dict = {}
    find_structural_analogues(target, [vicino, lontano], semantic_cosine_fn=_cos,
                              min_structural=0.4, max_semantic=0.5,
                              report=report)
    assert visti == ["v"], (
        f"il coseno e' stato calcolato anche per chi non passava il filtro "
        f"strutturale: {visti}")
    assert report["min_semantic"] == 0.95
    assert report["n_scored"] == 1, (
        f"il report deve dire su QUANTI candidati il minimo e' stato "
        f"osservato, altrimenti «min 0.95» su uno solo si legge come una "
        f"proprieta' del corpus: {report}")


def test_la_superficie_MCP_dice_perche_la_lista_e_vuota(monkeypatch):
    """Il difetto e' nato qui: `found: true` con `analogues: []` su 325
    candidati. `found` resta com'e' — l'audit registra 155 chiamate `ok` e 51
    `unknown_target`, cioe' chiamanti veri — ma accanto ci sono ora i numeri
    che permettono di leggerlo."""
    import asyncio
    import json

    import numpy as np

    from verimem import embedding as _emb
    from verimem import mcp_server

    class _Store:
        def __init__(self, ss): self._by = {s.id: s for s in ss}
        def get(self, sid): return self._by.get(sid)
        def all(self, status=None): return list(self._by.values())

    class _Ag:
        def __init__(self, ss): self.skills = _Store(ss)

    ss = [_skill("t", "alfa beta gamma", "delta epsilon"),
          _skill("v", "alfa beta gamma zeta", "delta epsilon")]
    monkeypatch.setattr(mcp_server, "_ag", lambda: _Ag(ss))
    # Coseno alto per tutti: e' il regime REALE misurato sullo store (minimo
    # osservato 0.7425), non un caso costruito.
    monkeypatch.setattr(_emb, "encode",
                        lambda *_a, **_k: np.array([1.0, 0.0], dtype=np.float32))

    async def _chiama():
        from mcp.types import CallToolRequest, CallToolRequestParams
        h = mcp_server.server.request_handlers[CallToolRequest]
        r = await h(CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(name="hippo_find_analogues",
                                         arguments={"target_skill_id": "t"})))
        p = r.root if hasattr(r, "root") else r
        return json.loads([c.text for c in p.content if hasattr(c, "text")][0])

    out = asyncio.run(_chiama())
    assert out["analogues"] == [], "il caso da inchiodare e' la lista vuota"
    assert out["n_analogues"] == 0, (
        f"senza n_analogues, «zero» resta indistinguibile guardando `found`: {out}")
    lim = out["limiti_osservati"]
    assert lim["min_semantic"] is not None and lim["min_semantic"] > 0.5, (
        f"il minimo semantico osservato e' il dato che spiega la lista vuota "
        f"contro il vincolo max_semantic=0.5: {out}")
    assert out["vincoli_richiesti"]["max_semantic"] == 0.5, out


def test_un_pool_vuoto_non_inventa_estremi():
    """Nessun candidato = nessun estremo osservato. Un `min_semantic: 0.0` qui
    direbbe «ho visto una coppia lontanissima», che e' il contrario del vero."""
    target = _skill("t", "alfa", "beta")
    report: dict = {}
    out = find_structural_analogues(target, [], semantic_cosine_fn=lambda a, b: 0.0,
                                    report=report)
    assert out == []
    assert report["n_candidates"] == 0
    assert report["max_structural"] is None and report["min_semantic"] is None, (
        f"estremi inventati su un pool vuoto: {report}")
