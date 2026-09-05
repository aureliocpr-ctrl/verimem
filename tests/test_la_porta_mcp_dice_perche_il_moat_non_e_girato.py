"""Quando il moat NON gira, la porta MCP deve dire PERCHÉ — non solo l'etichetta.

Misurato il 04/09 su 0.7.6 da PyPI, stesso claim e stessa fonte, due porte:

  · da CLI, 1,2 s: il record dice `judged=False` **e** stampa la spiegazione —
    che il giudice sta scaldando su un thread di sfondo, che NON manca, che
    `warmup` non serve, che serve un daemon raggiungibile e che `verimem doctor`
    dice se c'è.
  · da MCP: lo stesso esito, ma di quel testo al client non arriva niente. Chi
    scrive attraverso un agente vede un fatto salvato e basta.

L'advisory esiste già ed è scritto bene (`anti_confab_gate._avviso_moat_saltato`,
i tre stati del giudice). Non c'è da inventarlo: c'è da farlo passare dalla porta.

È lo stesso presidio di `test_the_promise_holds_on_the_MCP_port_too`, che vigila
sulla ricevuta `adjudication`, e ne ripete la ragione: **una promessa presidiata
su una porta sola non è una promessa presidiata.** Qui la promessa è quella che
il README fa per primo — «mai spacciato per verificato, mai saltato in silenzio»:
la prima metà regge su MCP, la seconda no.
"""
import asyncio
import json
import os

# encoder in-process (nessun daemon condiviso), come nel presidio gemello
os.environ["ENGRAM_ENCODE_SERVICE"] = "0"
os.environ.setdefault("VERIMEM_HOSTED", "1")

from verimem.client import Memory  # noqa: E402


def _ricevuta_mcp(tmp_path, monkeypatch, stato_del_giudice: str) -> dict:
    """Una scrittura con fonte attraverso la porta MCP, col giudice in `stato`."""
    from verimem import grounding_gate as gg
    from verimem import local_grounding as lg
    from verimem import mcp_server as srv

    # Il giudice non gira, ed è la condizione VERA che si vede in campo: il
    # modello è sul disco (`_have_judge` resta True) ma il punteggio non arriva,
    # e il gate emette l'advisory. `fact_grounding_score_ex` è importata DENTRO
    # la funzione del gate, quindi si sostituisce sul suo modulo — non su
    # `anti_confab_gate`, dove non esiste come attributo.
    def _il_giudice_non_risponde(*_a, **_k):
        raise gg.NoGroundingJudge("il giudice sta ancora scaldando")

    monkeypatch.setattr(gg, "fact_grounding_score_ex", _il_giudice_non_risponde)
    monkeypatch.setattr(lg, "judge_state", lambda: stato_del_giudice)

    m = Memory(str(tmp_path / "porta.db"))

    class _Ag:
        def __init__(self):
            self.semantic = m.semantic

    monkeypatch.setattr(srv, "_ag", lambda: _Ag())

    fuori = asyncio.run(srv.call_tool("hippo_remember", {
        "proposition": "Il modulo di fatturazione ha 12 utenti attivi.",
        "topic": "porta/moat-saltato",
        "source": "Verbale del 3 marzo: il modulo ha 12 utenti attivi.",
    }))
    return json.loads(fuori[0].text)


def test_la_porta_mcp_spiega_perche_il_giudice_non_ha_giudicato(
        tmp_path, monkeypatch):
    """Col giudice che sta scaldando, la ricevuta MCP deve portare il PERCHÉ."""
    out = _ricevuta_mcp(tmp_path, monkeypatch, "warming")

    testo = json.dumps(out, ensure_ascii=False).lower()
    assert "warming" in testo or "warm" in testo, (
        "la ricevuta MCP non nomina lo stato del giudice: chi scrive da un "
        "agente non ha modo di sapere perché il moat non è girato. "
        f"Chiavi presenti: {sorted(out)}"
    )
    assert "daemon" in testo, (
        "la ricevuta MCP non dice COSA serve perché la prima scrittura venga "
        "giudicata (un daemon raggiungibile). Dalla CLI questa riga c'è; qui "
        f"no. Chiavi presenti: {sorted(out)}"
    )
