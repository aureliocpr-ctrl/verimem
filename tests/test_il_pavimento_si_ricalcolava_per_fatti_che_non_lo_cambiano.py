"""Il pavimento si invalidava per la crescita di fatti che NON possono
cambiarne il valore — e ogni invalidazione costa un ricalcolo intero.

PEZZO (iv) del blocco CURA-PAVIMENTO. Il reperto e' del banco che ha misurato
il costo: **ogni ricalcolo costa 24169 ms**, e la deriva che lo innesca contava
una popolazione diversa da quella su cui il pavimento si stima.

LA GIUNTURA, in tre righe che stanno in due file:

    client.py    n = int(self.semantic.count())        <- la DERIVA conta tutto
    semantic.py  def count(..., include_quarantined: bool = True)
    relevance_floor.py   hits = sm.recall(p, k=k, ...)  <- la STIMA non li vede

⇒ Un fatto quarantinato **non puo' spostare il pavimento** (la stima non lo
incontra mai) **ma fa avanzare la deriva** verso il ricalcolo. Si paga un
ricalcolo intero per un fatto che non cambia il risultato.

🔑 IL LIMITE CHE QUESTO FILE CHIUDE, e non era mio: chi ha aperto il reperto ha
dichiarato *«che `sm.recall` escluda i quarantinati l'ho preso dal DOCSTRING,
non l'ho eseguito»*. **Eseguito il 2026-09-01 alle 19:33, store temporaneo::**

    count()                          = 2      <- include i quarantinati
    count(include_quarantined=False) = 1
    sm.recall(k=10) su 2 fatti       -> 1 riga, il quarantinato NON esce

⚠️ Con `k=10` su uno store da DUE fatti l'assenza non puo' essere un effetto di
ranking: e' esclusione. Il limite si chiude nel verso che CONFERMA la tesi.

⚖️ COSA CAMBIA E COSA NO: il pavimento resta invalidato dalla crescita del
corpus **servibile**, che e' quella che lo sposta davvero. Cambia solo QUALI
fatti fanno scattare l'orologio. Il valore stimato non cambia di una cifra.

⚠️ MIGRAZIONE, dichiarata: il file persistito porta ora `n_metric`. Un file
scritto prima della cura non ce l'ha, quindi non e' confrontabile con la nuova
metrica e si paga **un ricalcolo, una volta per store** — dopodiche' il file e'
coerente. Un ricalcolo dichiarato batte un confronto fra due popolazioni.
"""

from __future__ import annotations

import json

import pytest

from verimem import relevance_floor as _rf
from verimem.client import Memory


@pytest.fixture()
def memoria(tmp_path, monkeypatch):
    monkeypatch.delenv("ENGRAM_MIN_RELEVANCE", raising=False)
    return Memory(str(tmp_path / "s.db"))


def _conta_ricalcoli(monkeypatch) -> list[int]:
    """Spia sul ricalcolo vero, non su un proxy."""
    n = [0]
    vero = _rf.estimate_relevance_floor

    def _spia(sm, **kw):
        n[0] += 1
        return vero(sm, **kw)

    monkeypatch.setattr(_rf, "estimate_relevance_floor", _spia)
    return n


def _quarantina(m: Memory, testo: str) -> str:
    """Un'auto-affermazione senza fonte: la ferma il gate lessicale."""
    return str(m.add(testo, topic="iv/bad").get("status"))


def test_i_fatti_quarantinati_NON_innescano_il_ricalcolo(memoria, monkeypatch):
    """IL CUORE: prima, due fatti che la stima non puo' nemmeno incontrare
    facevano scattare la deriva e costavano un ricalcolo intero."""
    memoria.add("Il canone del contratto Rossi e' 900 euro al mese.",
                source="Contratto Rossi: canone 900 euro al mese.",
                topic="iv/ok")
    memoria._auto_relevance_floor()          # primo calcolo: scrive il file

    assert _quarantina(memoria, "Ho verificato di persona che tutto funziona "
                                "perfettamente.") == "quarantined"
    # ⚠️ La forma conta: «ho testato tutto e confermo che e' corretto» NON viene
    # quarantinata (misurato: torna `model_claim`), e l'assert qui sopra ha
    # fermato il banco invece di lasciarlo passare con due fatti servibili
    # travestiti da quarantinati — che avrebbe dato un verde falso.
    assert _quarantina(memoria, "Ho verificato personalmente che il sistema "
                                "funziona perfettamente.") == "quarantined"

    ricalcoli = _conta_ricalcoli(monkeypatch)
    memoria._floor_cache = None              # la cache per-istanza non deve mascherare
    memoria._auto_relevance_floor()

    assert ricalcoli[0] == 0, (
        "il pavimento si e' ricalcolato per due fatti QUARANTINATI, che la "
        "stima non incontra mai: e' il pezzo (iv), e ogni ricalcolo costa "
        "24169 ms misurati")


def test_CONTROLLO_i_fatti_SERVIBILI_lo_INVALIDANO_ancora(memoria, monkeypatch):
    """⚠️ LA POPOLAZIONE OPPOSTA, e senza di essa la cura sarebbe un disastro
    silenzioso: se smettesse di invalidare del tutto, il pavimento resterebbe
    fermo su un corpus che cambia — un valore vecchio servito come calibrato.

    🪞 AGGIORNATA il 2026-09-02 alle 00:26 (ora letta dal commit, non
    stimata), e va detto perche' modificare un proprio test per farlo passare
    e' la cosa piu' pericolosa che esista.
    **La garanzia non e' cambiata, e' cambiato DOVE si osserva.** Prima
    l'invalidazione si vedeva come un ricalcolo dentro la lettura; ma quel
    ricalcolo costa 24169 ms sul corpus vero e stava nel percorso di OGNI
    `search`, quindi lo pagava chi stava solo cercando. Ora la lettura serve il
    valore che ha e alza `_floor_stantio`: l'invalidazione c'e' ancora, e a
    ricalcolare e' chi ha il costo atteso (`verimem warmup`).

    ⚠️ LA CELLA PUO' ANCORA FALLIRE, ed e' l'unica cosa che la rende una
    verifica: se la cura avesse spento l'invalidazione — invece di spostarne
    l'effetto — `_floor_stantio` resterebbe False e questa cella diventerebbe
    rossa. Il contrasto col caso dei quarantinati (cella sopra) regge il
    reperto del pezzo (iv): li' NON deve alzarsi, qui si'.
    """
    memoria.add("Il canone del contratto Rossi e' 900 euro al mese.",
                source="Contratto Rossi: canone 900 euro al mese.",
                topic="iv/ok")
    memoria._auto_relevance_floor()
    assert getattr(memoria, "_floor_stantio", None) is False, (
        "appena calcolato non puo' essere stantio: la premessa non regge")

    memoria.add("La penale del contratto Bianchi e' 250 euro.",
                source="Contratto Bianchi: penale 250 euro.", topic="iv/ok")
    memoria.add("Il deposito del contratto Verdi e' 1800 euro.",
                source="Contratto Verdi: deposito 1800 euro.", topic="iv/ok")

    ricalcoli = _conta_ricalcoli(monkeypatch)
    memoria._floor_cache = None
    memoria._auto_relevance_floor()

    assert getattr(memoria, "_floor_stantio", None) is True, (
        "due fatti SERVIBILI non hanno invalidato il pavimento: la cura ha "
        "spento l'invalidazione invece di correggerne la popolazione")
    assert ricalcoli[0] == 0, (
        "la LETTURA ha ricalcolato: l'invalidazione deve marcare il valore "
        "come vecchio, non far pagare 24 secondi a chi sta cercando")


def test_il_file_persistito_dichiara_QUALE_popolazione_ha_contato(memoria):
    """⚠️ LA MIGRAZIONE SI VEDE: senza un marcatore, un file scritto con la
    vecchia metrica verrebbe confrontato con la nuova e i due lati direbbero
    cose diverse sullo stesso store. Un ricalcolo dichiarato batte un confronto
    fra due popolazioni."""
    memoria.add("Il canone del contratto Rossi e' 900 euro al mese.",
                source="Contratto Rossi: canone 900 euro al mese.",
                topic="iv/ok")
    memoria._auto_relevance_floor()
    d = json.loads(memoria._floor_file().read_text(encoding="utf-8"))
    assert d.get("n_metric") == "servibili", d


def test_un_file_della_vecchia_metrica_non_viene_creduto(memoria, monkeypatch):
    """⚠️ E il file vecchio non deve essere USATO come se fosse confrontabile:
    costa un ricalcolo, una volta, e questo e' il prezzo dichiarato."""
    memoria.add("Il canone del contratto Rossi e' 900 euro al mese.",
                source="Contratto Rossi: canone 900 euro al mese.",
                topic="iv/ok")
    memoria._auto_relevance_floor()
    f = memoria._floor_file()
    vecchio = json.loads(f.read_text(encoding="utf-8"))
    vecchio.pop("n_metric", None)                  # com'era prima della cura
    f.write_text(json.dumps(vecchio), encoding="utf-8")

    ricalcoli = _conta_ricalcoli(monkeypatch)
    memoria._floor_cache = None
    memoria._auto_relevance_floor()
    assert ricalcoli[0] == 1, (
        "un file senza `n_metric` e' stato creduto confrontabile con la nuova "
        "metrica: i due lati contano popolazioni diverse")
