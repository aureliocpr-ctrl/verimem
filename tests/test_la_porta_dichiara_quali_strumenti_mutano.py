"""T71b-1 — la porta dice al client quali strumenti mutano, e continua a dirlo.

Fino al 2026-09-12 tutte e 249 le dichiarazioni `Tool(...)` portavano `name`,
`description` e `inputSchema` e NESSUNA `annotations`: un client non poteva
distinguere una lettura da una cancellazione se non leggendo la prosa di una
descrizione. Il protocollo MCP prevede quei campi, e il prodotto non li usava.

⚠️ SI MISURA ALLA PORTA, non su `_list_tools_unfiltered`. Il client non chiama
quella: chiama `list_tools()`, che filtra e puo' RINOMINARE. Un presidio
scritto sulla funzione interna direbbe verde mentre la superficie servita non
porta niente — «il livello a cui misuri decide il verdetto», e qui i due
livelli si comportano davvero in modo diverso.

COSA E' PRESIDIATO, e la asimmetria e' il punto:

  · `destructiveHint=True` esce SOLO dai due insiemi che il prodotto dichiara
    (`_THIN_UNSUPPORTED_WRITES`, `_EPISODE_MUTATING`) — e questo test
    verifica che l'annotazione ARRIVI alla porta, non che l'insieme sia
    giusto: di quello risponde il presidio dell'uguaglianza di T71a;
  · `readOnlyHint=True` non deve uscire su NESSUNO strumento. Sola lettura e'
    stata definita («non cambia il contenuto della memoria; il giornale non
    conta») e misurata NON derivabile: un criterio col ricevitore fissato
    riporta 9 dei 20 mutatori dichiarati come se non scrivessero, perche'
    mutano attraverso un aiutante di modulo o un secondo store. Concedere
    `readOnlyHint` per derivazione direbbe a un client che `smart_prune` e
    `forget_with_report` si possono chiamare senza pensarci.

L'ultima cella e' quella che protegge la configurazione consigliata: con il
namespace attivo i nomi diventano `verimem_*`, e le annotazioni si timbrano
PRIMA del rinominamento. Timbrare dopo lascerebbe senza annotazione, in
silenzio, proprio la configurazione che il README consiglia.
"""
from __future__ import annotations

import pytest

from verimem.mcp_server import _EPISODE_MUTATING, _THIN_UNSUPPORTED_WRITES, list_tools


def _annotazione(tool):
    return getattr(tool, "annotations", None)


async def _serviti() -> dict:
    return {s.name: s for s in await list_tools()}


async def test_ogni_mutatore_dichiarato_esce_dalla_porta_come_DISTRUTTIVO():
    """Il client deve poterlo sapere senza leggere la descrizione."""
    serviti = await _serviti()
    attesi = _THIN_UNSUPPORTED_WRITES | _EPISODE_MUTATING
    assert attesi, "i due insiemi dichiarati sono vuoti: non c'e' niente da provare"

    muti = []
    for nome in sorted(attesi):
        tool = serviti.get(nome)
        if tool is None:
            continue          # non servito in questa configurazione: non e' qui
        ann = _annotazione(tool)
        if ann is None or getattr(ann, "destructiveHint", None) is not True:
            muti.append(nome)
    assert not muti, (
        f"strumenti che il prodotto DICHIARA mutanti ed escono dalla porta "
        f"senza `destructiveHint`: {muti}. Il client non ha modo di saperlo se "
        f"non leggendo la prosa della descrizione. Non aggiungere i nomi a "
        f"mano qui: l'annotazione si ricava dai due insiemi, e se uno di "
        f"questi non arriva alla porta e' il timbro a non essere stato "
        f"applicato — o a essere stato applicato dopo il rinominamento.")


async def test_nessuno_strumento_esce_dichiarato_DI_SOLA_LETTURA():
    """La meta' pericolosa dell'annotazione, e per ora resta chiusa.

    Non e' una svista da colmare quando qualcuno avra' tempo: e' la posizione
    misurata. Finche' «sola lettura» non e' provata strumento per strumento —
    chiamandolo e guardando lo store, non leggendo il codice — dirla e'
    peggio che tacerla, perche' un tool non annotato il protocollo lo tratta
    gia' come possibilmente distruttivo.
    """
    serviti = await _serviti()
    dichiarati = sorted(
        n for n, s in serviti.items()
        if getattr(_annotazione(s), "readOnlyHint", None) is True)
    assert not dichiarati, (
        f"{dichiarati} escono dalla porta come `readOnlyHint=True`. Se e' "
        f"stato misurato CHIAMANDOLI e confrontando lo store prima e dopo, "
        f"togli questo test e scrivi qui il numero. Se e' stato DERIVATO "
        f"leggendo il codice, rimettilo: la derivazione e' stata provata e "
        f"riporta 9 dei 20 mutatori dichiarati come se non scrivessero.")


@pytest.mark.parametrize("variabile", ["VERIMEM_TOOL_NAMESPACE",
                                       "ENGRAM_TOOL_NAMESPACE"])
async def test_l_annotazione_sopravvive_AL_RINOMINAMENTO(monkeypatch, variabile):
    """La configurazione consigliata non deve perdere l'annotazione.

    `_apply_tool_namespace` espone i tool come `verimem_*`. Le annotazioni si
    timbrano PRIMA, e questa cella e' cio' che tiene fermo quell'ordine: se
    qualcuno sposta il timbro dopo il rinominamento, il prodotto smette di
    dichiarare le mutazioni esattamente nella configurazione che consiglia, e
    nessun altro test se ne accorge.
    """
    monkeypatch.setenv(variabile, "verimem")
    serviti = await _serviti()
    rinominati = [n for n in serviti if n.startswith("verimem_")]
    assert rinominati, (
        f"{variabile}=verimem non ha rinominato niente: questa cella non sta "
        f"misurando il caso che crede di misurare.")

    atteso = {"verimem_" + n[len("hippo_"):]
              for n in (_THIN_UNSUPPORTED_WRITES | _EPISODE_MUTATING)
              if n.startswith("hippo_")}
    muti = sorted(
        n for n in atteso
        if n in serviti
        and getattr(_annotazione(serviti[n]), "destructiveHint", None) is not True)
    assert not muti, (
        f"con {variabile}=verimem questi escono senza `destructiveHint`: "
        f"{muti}. Il timbro e' stato applicato DOPO il rinominamento, quando i "
        f"nomi non combaciano piu' con i due insiemi dichiarati.")
