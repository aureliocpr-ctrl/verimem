"""Il pavimento si deve trovare da OGNI forma di oggetto che la casa passa.

L'avviso `trattenuti` aveva gia' il suo ripiego («l'agente MCP espone sempre
lo store come `a.semantic`») e usciva da tutte le forme. L'avviso gemello
`sotto_il_pavimento` non ce l'aveva, e cercava `_auto_relevance_floor` su
`agent` e `agent.memory` soltanto — cioe' su nessuna delle due forme che il
prodotto passa davvero, visto che `Memory` non ha `.memory` e che nell'agente
MCP `a.memory` e' la memoria EPISODICA.

Misurato alla porta il 2026-08-31, con un corpus abbastanza grande da
calibrare (12 fatti, pavimento 0.9009)::

    forma                   trattenuti   sotto_il_pavimento
    il client stesso            SI              SI
    oggetto con .memory         SI              SI
    oggetto con .semantic       SI              no        <- la forma del prodotto

Il taglio di questi test e' percio' che le tre forme diano lo STESSO
pavimento: non il valore, che dipende dal corpus, ma il fatto che nessuna
forma resti a mani vuote mentre le altre no.

⚠️ Il corpus del banco NON puo' essere minuscolo: la stima vale 0.0 su uno
store troppo piccolo per calibrare (misurato: 1 fatto -> 0.0, 6 -> 0.9166), e
uno zero mascherebbe il difetto facendo passare il test per la ragione
sbagliata. Il test di controllo qui sotto lo pretende esplicitamente.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from verimem.client import Memory
from verimem.mcp_server import _avvisi_di_lettura, _pavimento_di


@pytest.fixture()
def memoria(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Memory:
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    m = Memory(path=tmp_path / "s.db")
    m.add("Ho implementato l'export del magazzino e funziona perfettamente.",
          topic="mag")
    for i in range(11):
        m.add(f"Nel registro la voce {i} del magazzino vale {i * 4}.",
              topic=f"mag/voce-{i}",
              source=f"Il registro riporta la voce {i} del magazzino "
                     f"pari a {i * 4}.")
    return m


def _forme(m: Memory) -> dict[str, object]:
    """Le tre forme che questa casa passa a `_avvisi_di_lettura`."""
    return {
        "il client stesso": m,
        "oggetto con .memory": type("_A", (), {"memory": m})(),
        "oggetto con .semantic": type("_A", (), {"semantic": m.semantic})(),
    }


def test_CONTROLLO_il_corpus_del_banco_calibra_davvero(memoria: Memory) -> None:
    """Senza questo, un pavimento a 0.0 farebbe passare tutto il resto per la
    ragione sbagliata: lo zero non e' un valore, e' l'assenza di taratura."""
    assert _pavimento_di(memoria) > 0.0, (
        "il corpus del banco e' troppo piccolo per calibrare: il resto dei "
        "test misurerebbe uno zero, non una risoluzione")


def test_le_tre_forme_danno_LO_STESSO_pavimento(memoria: Memory) -> None:
    """IL CUORE. Non il valore — che dipende dal corpus — ma il fatto che
    nessuna forma resti a mani vuote mentre le altre trovano il numero."""
    valori = {nome: _pavimento_di(ogg) for nome, ogg in _forme(memoria).items()}
    assert len(set(valori.values())) == 1, (
        f"le forme divergono, e chi passa quella sbagliata riceve silenzio: "
        f"{valori}")


def test_la_forma_che_il_prodotto_passa_non_resta_a_zero(memoria: Memory) -> None:
    """La regressione precisa: `.semantic` e' la forma dell'agente MCP, ed era
    l'unica delle tre a non trovare il pavimento."""
    solo_semantic = type("_A", (), {"semantic": memoria.semantic})()
    assert _pavimento_di(solo_semantic) > 0.0


def test_un_oggetto_senza_niente_vale_zero_e_non_esplode() -> None:
    """Fail-open: questo e' un percorso di lettura, e un pavimento che non si
    sa calcolare non puo' costare un'eccezione al chiamante."""
    assert _pavimento_di(object()) == 0.0
    assert _pavimento_di(None) == 0.0


def test_l_avviso_gemello_esce_da_tutte_le_forme(memoria: Memory) -> None:
    """Il controllo che dice che il banco non e' rotto: `trattenuti` il suo
    ripiego ce l'ha da prima, e deve continuare a uscire da tutte e tre."""
    for nome, ogg in _forme(memoria).items():
        avvisi = _avvisi_di_lettura(ogg, "export del magazzino")
        assert avvisi.get("trattenuti"), f"silenzio con «{nome}»"
