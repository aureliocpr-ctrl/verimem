"""TRE PORTE, UNA RISPOSTA — il presidio permanente sull'avviso degli SCADUTI.

Gemello dichiarato di `test_tre_porte_una_risposta_sul_pavimento.py`, e non per
somiglianza estetica: e' la STESSA forma di difetto, sullo stesso helper, un
avviso piu' in la'. Quel file esiste perche' una cura applicata a una superficie
sola era comparsa tre volte in un pomeriggio. Questo esiste perche' e' comparsa
una QUARTA — e il codice lo dice da solo, in `mcp_server.py`, nel ramo di
`hippo_facts_recall`::

    # ⚠️ QUARTA GENERAZIONE DELLA STESSA CURA. [...] due ore fa ho messo su
    # `Memory.search` la guardia sul RANKING DEGRADATO, e questo handler
    # chiama `a.semantic` direttamente.

LA CAUSA E' UNA SOLA, e non e' «una porta ha dimenticato un campo»:
`hippo_facts_recall` e `hippo_facts_search` parlano ad `a.semantic` e SALTANO
`Memory.search`, cioe' il punto dove il prodotto costruisce `Risultati`. Tutto
cio' che vive li' — il pavimento, il ranking degradato, `letto_al_passato`,
`esclusi_perche_scaduti` — non puo' raggiungerli per costruzione. Curare il
quinto campo a mano significa aspettare il sesto.

MISURATO IL 2026-09-05 su `build=5d7152d8`, dai due banchi end-to-end
(`docs/stato-reale/banchi/ws6-quante-porte-dicono-cosa-hanno-tolto.py` e
`...-la-porta-mcp-dice-cosa-ha-tolto.py`)::

    porta                      risponde  dichiara
    SDK  Memory.recall         si        SI
    CLI  recall                si        SI
    CLI  ask (FIND)            si        no     <- toglie e tace
    MCP  hippo_facts_recall    si        no     <- toglie e tace
    MCP  hippo_facts_search    si        no        (NON toglie: serve lo
                                                    scaduto, nulla da dichiarare)

⚠️ QUELLA QUINTA RIGA E' UNA TRAPPOLA GIA' SCATTATA. Il 04/09 avevo scritto che
`hippo_facts_search` «dichiara», perche' il suo payload contiene il CAMPO
`"valid_until": 1788458907.22` di ogni fatto e il mio banco cercava quel nome
fra le parole di un avviso: **contavo un dato come se fosse un avviso**. Una
porta che SERVE i fatti scaduti non toglie niente, quindi non ha niente da
dichiarare. Qui `dichiara` si chiede solo a chi TOGLIE.

PREDIZIONI DEPOSITATE PRIMA DI ESEGUIRE (2026-09-05):
  P1 — la porta MCP espone l'esclusione per scadenza quando lo store ne ha.
       ATTESA: **ROSSA** senza manomettere niente. `_avvisi_di_lettura` oggi
       conosce due avvisi (`trattenuti`, `sotto_il_pavimento`) e questo no.
  P2 — controllo positivo: senza fatti scaduti nessuna chiave compare.
       ATTESA: VERDE gia' oggi. Serve a provare che P1 non e' rossa perche' il
       test non sa leggere: se anche P2 fosse rossa, il difetto sarebbe mio.
  P3 — l'SDK, che la cura ce l'ha, dichiara. ATTESA: VERDE.
       E' il secondo controllo positivo: se P3 cadesse, il RED di P1 non
       direbbe «la porta MCP tace», direbbe «il banco non produce scaduti».

⚠️ LE PORTE NON SI UNIFORMANO QUI. Si legge da ognuna nella SUA forma (SDK
`Risultati.esclusi_perche_scaduti`, MCP il dict di `_avvisi_di_lettura`) e si
confronta solo il CONTRATTO: «l'esclusione per scadenza e' dichiarata, si'/no».
Un test che le uniformasse misurerebbe l'adattatore, non le porte.

⚠️ E NON SI CONFRONTA IL *CRITERIO*: sull'SDK il numero dichiarato nasce da un
confronto fra similarita' che ho gia' dichiarato ANTICORRELATO (0,8969/0,8159 in
tema tace; 0,7552/0,7600 fuori tema parlerebbe). Il contratto che questo file
difende e' «la porta lo dice», non «lo dice con quel criterio»: legare il
presidio a un criterio che so non tarato lo renderebbe rosso quando lo cureremo.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from verimem.client import Memory  # noqa: E402
from verimem.mcp_server import _avvisi_di_lettura  # noqa: E402

_DOMANDA = "quale fornitore di pagamenti usa il negozio online adesso"
_PASSATO = 1_600_000_000.0        # 2020, ampiamente scaduto
_FUTURO = 4_102_444_800.0         # 2100, ampiamente valido


class _SemConScaduti:
    """Lo store come lo vede la porta MCP DOPO una `recall`.

    `_recall_scaduti_sim` e' l'attributo che `SemanticMemory.recall` popola con
    le similarita' dei fatti che la maschera temporale ha tolto. Non e'
    ricostruibile a posteriori — a differenza di `trattenuti`, che si ricalcola
    con una seconda interrogazione — perche' e' un sottoprodotto della chiamata
    appena fatta. E' proprio per questo che l'avviso non e' mai arrivato qui.
    """

    db_path = None

    def __init__(self, scaduti: tuple[float, ...]):
        self._recall_scaduti_sim = scaduti

    def recall(self, query, k=3):          # noqa: ARG002 — firma della porta
        return [("il fornitore corrente e' Stripe", 0.89)]


class _AgenteMcp:
    def __init__(self, scaduti: tuple[float, ...] = ()):
        self.semantic = _SemConScaduti(scaduti)

    def _auto_relevance_floor(self):
        return 0.0                          # nessun avviso di pavimento qui


def _porta_mcp_dichiara(*, scaduti: tuple[float, ...]) -> bool:
    """Il CONTRATTO, non la forma: la porta dice che la scadenza ha tolto?"""
    out = _avvisi_di_lettura(_AgenteMcp(scaduti), _DOMANDA)
    return "esclusi_perche_scaduti" in out


def _porta_sdk_dichiara(tmp_path) -> bool:
    m = Memory(str(tmp_path / "sdk.db"))
    m.add("Il negozio online incassa con Stripe.",
          topic="pagamenti", valid_until=_PASSATO)
    m.add("Il negozio online incassa con Adyen.",
          topic="pagamenti", valid_until=_FUTURO)
    r = m.search(_DOMANDA, k=10)
    return bool(getattr(r, "esclusi_perche_scaduti", None))


def test_P2_controllo_positivo_senza_scaduti_nessuna_chiave():
    """Se non c'e' niente di scaduto, la porta non deve inventarsi un avviso.

    Va PRIMA di P1 di proposito: e' la prova che il lettore funziona. Un P1
    rosso accanto a un P2 rosso non accuserebbe il prodotto, accuserebbe me.
    """
    assert not _porta_mcp_dichiara(scaduti=())


def test_P3_controllo_positivo_l_sdk_dichiara(tmp_path):
    """La porta che la cura ce l'ha deve accendersi sullo stesso materiale.

    Senza questo, il rosso di P1 sarebbe ambiguo: «la porta MCP tace» e «il
    banco non produce nessuno scaduto» si leggono identici da fuori.
    """
    assert _porta_sdk_dichiara(tmp_path), (
        "l'SDK non dichiara: il materiale del banco non contiene scaduti, "
        "quindi il rosso di P1 non proverebbe niente sulla porta MCP")


def test_P1_la_porta_dell_agente_dichiara_gli_scaduti():
    """IL RED. Oggi la porta MCP toglie il fatto scaduto e non lo dice.

    Diventa verde quando `_avvisi_di_lettura` espone il terzo avviso, e da quel
    momento torna rossa da sola se qualcuno lo toglie o aggiunge un quarto campo
    all'SDK senza portarlo di qua.
    """
    assert _porta_mcp_dichiara(scaduti=(0.87, 0.81)), (
        "la porta MCP non espone `esclusi_perche_scaduti`: chi legge da li' "
        "riceve una risposta ridotta dalla scadenza senza alcun modo di "
        "accorgersene")
