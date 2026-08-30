"""Col ranking degradato il dossier si asteneva — e lo DICHIARAVA.

Il QUINTO punto in cui un pavimento taglia senza guardare
`_recall_degraded_count`. Lo sweep, `git grep -n min_relevance -- verimem/`::

    client.py:1219               guardia   (`Memory.search`)
    mcp_server.py:13850          guardia   (`hippo_facts_recall`)
    proactive_step_injector:118  guardia
    temporal_context.py:332      guardia   (curata poco prima, `c97aa380`)
    cli.py:1349                  delega a `m.search` -> coperto
    trust_report.py:234          NESSUNA   <-- questo

MISURATO SULL'SDK il 2026-08-31 alle 00:40, cinque fatti, pavimento 0.5,
giudice locale assente per costruzione::

    regime      col pavimento 0.5        senza pavimento
    a caldo     n=5  abstained=False     n=5
    degradato   n=0  abstained=True      n=5

⇒ Le tre celle reggono: a caldo il dossier ha qualcosa (controllo), senza
pavimento il degrado non lo svuota (popolazione opposta), col pavimento si
svuota solo nel degrado.

🔑 L'AGGRAVANTE CHE LE ALTRE PORTE NON AVEVANO: `abstained: True`. **La porta
che esiste per sapere quando non sa diceva di non sapere per la ragione
sbagliata** — e la guida degli agenti la addita proprio per quello (*«To learn
WHETHER the store can answer at all, ask verimem_trust_report»*). Un'astensione
falsa che si giustifica da sola vale meno di zero: chi la riceve ha una ragione
per crederle.

📌 LA CLASSE ERA GIA' SCRITTA A DUE RIGHE DI DISTANZA. Il commento di
`client.py` accanto a `floor_applied_by` dice: *«E' la stessa classe dello `0.0`
del ranking degradato: un numero con la forma di una misura che significa
altro»*. Chi l'ha scritto conosceva la classe — e non ha visto che il filtro li'
accanto ne era l'istanza. 🪞 *Nominare una classe non chiude le sue istanze.*

⚖️ QUANDO IL CE GIRA il filtro grezzo non si applica gia' oggi (`not ce_ran`):
il caso riguarda chi non ha il reranker o chi passa un pavimento esplicito
dall'SDK, dove `ce_gate` si accende solo per `"auto"`.

📌 REPERTO MINORE, non curato: `floor_applied_by` vale `"cosine"` anche quando
nessun pavimento ha filtrato (pavimento 0.0). Quel campo dice QUALE pavimento
si userebbe, non che uno abbia filtrato — precede questa cura e non la riguarda.

Banco: ``docs/stato-reale/banchi/ws3-il-quinto-consumatore-e-il-dossier.py``
"""

from __future__ import annotations

import pytest

from verimem.trust_report import build_trust_report

PAVIMENTO = 0.5


class _Fatto:
    def __init__(self, i: int) -> None:
        self.id = f"f{i}"
        self.proposition = f"Il magazzino K-{70 + i} ha {4000 + i * 100} metri quadrati."
        self.topic = "deg5/mag"
        self.status = "model_claim"
        self.grounding_score = 99.0
        self.confidence = 0.9
        self.superseded_by = None
        self.verified_by = None
        self.created_at = 0.0


class _SM:
    """Il minimo che `build_trust_report` tocca.

    ⚠️ PERCHE' UN DOPPIO E NON LE PORTE: **sotto pytest l'embedder e' uno
    stub**, quindi a caldo il richiamo non restituisce nulla e una soglia
    assoluta non significa la stessa cosa dentro e fuori dalla suite. Il banco
    misura alle superfici vere; qui si tiene ferma la CLAUSOLA, con punteggi e
    contatore del degrado decisi dal test e nessun embedder di mezzo.
    """

    db_path = "/non/esiste/x.db"

    def __init__(self, punteggi: list[float], *, degrada: bool) -> None:
        self._punteggi = punteggi
        self._degrada = degrada
        self._recall_degraded_count = 0

    def recall(self, query: str, k: int = 5, deep: bool = False):
        if self._degrada:
            self._recall_degraded_count += 1
        return [(_Fatto(i), p) for i, p in enumerate(self._punteggi)]

    def get(self, fid):  # noqa: ANN001 — le dispute sono un arricchimento
        return None


def _n(rep: dict) -> int:
    assert "facts" in rep, sorted(rep)
    return len(rep.get("facts") or [])


def test_col_ranking_buono_il_pavimento_taglia_ancora():
    """IL PRESIDIO PIU' IMPORTANTE: la cura toglie il taglio SOLO nel degrado.
    Se avesse spento il pavimento in generale, avrei curato un'astensione falsa
    creando un'astensione MANCATA — cioe' il difetto che il prodotto esiste per
    non fare."""
    rep = build_trust_report(_SM([0.9, 0.8, 0.2, 0.1], degrada=False), "q",
                             min_relevance=PAVIMENTO, ce_gate=False)
    assert _n(rep) == 2, rep


def test_col_ranking_degradato_il_dossier_non_si_svuota():
    """IL CUORE: prima della cura, zero fatti e `abstained: True`."""
    rep = build_trust_report(_SM([0.0, 0.0, 0.0, 0.0], degrada=True), "q",
                             min_relevance=PAVIMENTO, ce_gate=False)
    assert _n(rep) == 4, rep


def test_e_non_dichiara_piu_un_astensione_che_non_ha_luogo():
    """⚠️ LA META' CHE RENDEVA GRAVE L'ALTRA: senza questa riga la cura
    riempirebbe il dossier lasciando scritto che si e' astenuto."""
    rep = build_trust_report(_SM([0.0, 0.0], degrada=True), "q",
                             min_relevance=PAVIMENTO, ce_gate=False)
    assert rep.get("abstained") is not True, rep


def test_il_dossier_dice_che_il_ranking_era_degradato():
    """Un dossier PIENO nonostante un pavimento alto e' inspiegabile da fuori.
    Stesso nome e stessa convenzione della porta della cronaca."""
    rep = build_trust_report(_SM([0.0, 0.0], degrada=True), "q",
                             min_relevance=PAVIMENTO, ce_gate=False)
    assert rep.get("ranking_degraded") is True, sorted(rep)


def test_col_ranking_buono_non_si_dichiara_un_degrado_che_non_c_e():
    """⚠️ L'ALTRA META' DEL PRESIDIO: un campo sempre vero passerebbe il test
    qui sopra senza dire niente."""
    rep = build_trust_report(_SM([0.9, 0.1], degrada=False), "q",
                             min_relevance=PAVIMENTO, ce_gate=False)
    assert rep.get("ranking_degraded") is None, sorted(rep)


@pytest.mark.parametrize("degrada", [False, True])
def test_senza_pavimento_nulla_cambia_in_nessuno_dei_due_regimi(degrada: bool):
    """⚠️ L'ULTIMA POPOLAZIONE: la guardia non deve fare NIENTE quando nessun
    pavimento e' stato chiesto."""
    rep = build_trust_report(_SM([0.9, 0.1], degrada=degrada), "q",
                             min_relevance=0.0, ce_gate=False)
    assert _n(rep) == 2, rep
