"""Il prodotto è completo per gli agenti e incompleto per gli umani.

Il file gemello `test_lo_stesso_verbo_su_ogni_superficie` guarda i NOMI fra CLI
e SDK («la CLI dice `correct`, l'SDK diceva `update`»). Questo guarda un'altra
cosa: se la CAPACITÀ è raggiungibile, e da quale superficie.

Misurato il 2026-08-04 con `scripts/matrice_delle_superfici.py`:

    CLI   100 comandi      HTTP  13 rotte /v1      MCP  243 tool
    7 verbi centrali su 14 non sono su tutte e tre le superfici
    mancanze: HTTP 6, CLI 3, MCP 0

    verbo          CLI  HTTP   MCP
    explain         --    si    si
    count           --    --    si
    history         --    --    si
    ignorance       si    --    si
    documents       si    --    si
    episodes        si    --    si
    lineage         si    --    si

Due letture, e la seconda pesa di più:

  * **HTTP è la superficie povera** — il gateway, cioè il modo in cui un
    cliente ESTERNO usa il prodotto, non espone il tier documenti, il tier
    episodi, il lineage né la mappa dell'ignoranza. Tutte cose che esistono e
    funzionano, e da lì non si raggiungono. Combacia con l'aperto già in
    memoria: «l'SDK non ha metodi documenti, il tier vive solo su CLI+MCP».
  * **`count`, `history` ed `explain` vivono solo su MCP**: raggiungibili da un
    agente e da nessun umano alla riga di comando.

DA DOVE VIENE, e il metodo conta quanto il risultato. L'altra istanza aveva
riportato «/v1/ask 404 — la cura ha aperto la porta su CLI e non su API».
Interrogando le rotte invece del nome — che è la loro stessa lezione —
`/v1/ask` non esiste e `/v1/answer` sì: il nome era sbagliato. Ma misurare
l'intera superficie invece di quei quattro nomi ha mostrato qualcosa di più
grande di quello che il finding diceva.

NON È UN INVARIANTE, È UN NUMERO. Pretendere che ogni verbo stia ovunque
sarebbe sbagliato: `doctor`, `backup-all`, `swarm` sono manutenzione della
macchina e non hanno niente da fare in un'API multi-tenant. Per questo il test
non chiede la parità: fissa lo stato misurato e si accende in ENTRAMBE le
direzioni — se peggiora, e anche se migliora senza che il numero venga
aggiornato, così il presidio non resta indietro rispetto al prodotto.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

RADICE = pathlib.Path(__file__).resolve().parent.parent
if str(RADICE / "scripts") not in sys.path:
    sys.path.insert(0, str(RADICE / "scripts"))

#: Lo stato misurato il 2026-08-04. Cambiarlo richiede di aver RIMISURATO con
#: `python scripts/matrice_delle_superfici.py`.
MANCANZE_ATTESE: dict[str, list[str]] = {
    "explain":   ["CLI"],
    "count":     ["CLI", "HTTP"],
    "history":   ["CLI", "HTTP"],
    "ignorance": ["HTTP"],
    "documents": ["HTTP"],
    "episodes":  ["HTTP"],
    "lineage":   ["HTTP"],
}


@pytest.fixture(scope="module")
def buchi() -> dict[str, list[str]]:
    from matrice_delle_superfici import misura
    return misura()


def test_nessuna_capacita_e_sparita_da_una_superficie(buchi):
    """Il verso che conta di più: qualcosa che si raggiungeva e non più."""
    nuovi = {v: m for v, m in buchi.items()
             if set(m) - set(MANCANZE_ATTESE.get(v, []))}
    assert not nuovi, (
        f"queste capacità non sono più raggiungibili da una superficie che le "
        f"serviva: {nuovi}\nse è voluto, rimisura con "
        f"`python scripts/matrice_delle_superfici.py` e aggiorna "
        f"MANCANZE_ATTESE qui, dicendo nel commit perché")


def test_e_se_una_mancanza_e_stata_COLMATA_va_aggiornato_il_numero(buchi):
    """L'altro verso. Un presidio che resta indietro rispetto al prodotto
    smette di misurarlo: se qualcuno porta `ignorance` sull'API e questo file
    continua a dichiararla mancante, la prossima regressione passa liscia."""
    colmate = {v: sorted(set(MANCANZE_ATTESE[v]) - set(buchi.get(v, [])))
               for v in MANCANZE_ATTESE
               if set(MANCANZE_ATTESE[v]) - set(buchi.get(v, []))}
    assert not colmate, (
        f"queste mancanze sono state colmate — buona notizia, ma il numero qui "
        f"va aggiornato perché il presidio continui a misurare: {colmate}")


def test_l_API_HTTP_resta_la_superficie_piu_povera(buchi):
    """Il dato che riassume tutto, fissato perché non passi inosservato: sei
    mancanze su HTTP, tre su CLI, zero su MCP."""
    per_superficie = {s: sum(1 for m in buchi.values() if s in m)
                      for s in ("CLI", "HTTP", "MCP")}
    assert per_superficie == {"HTTP": 6, "CLI": 3, "MCP": 0}, (
        f"la distribuzione delle mancanze è cambiata: {per_superficie} invece "
        f"di HTTP 6, CLI 3, MCP 0. Rimisura e aggiorna, dicendo nel commit "
        f"quale superficie si è mossa e perché")
