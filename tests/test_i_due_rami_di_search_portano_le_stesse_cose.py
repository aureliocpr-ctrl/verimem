"""I due rami di `Memory.search` devono portare le stesse cose.

`Memory.search` sceglie fra DUE percorsi che non sono lo stesso codice:

    if as_of is not None:  hits = recall_as_of(...)          # ramo A
    else:                  hits = self.semantic.recall(...)  # ramo B

Il ramo A **sostituisce** il percorso normale invece di comporlo: tutto cio' che
vive sul ramo B — le opzioni, gli avvisi, i contatori — non arriva al ramo A se
non lo si ri-aggiunge a mano. E chi aggiunge domani una capacita' al percorso
normale non ha modo di accorgersi che il ramo `as_of` e' rimasto indietro.

NELLA NOTTE DEL 05-06/09 QUESTA GIUNTURA HA PRODOTTO DUE SINTOMI, trovati da due
persone diverse che misuravano cose diverse:
  · l'avviso degli SCADUTI tace quando c'e' `as_of`      (trovato dai Dati)
  · `include_superseded` e' ignorato quando c'e' `as_of` (trovato dalle Porte)

⚠️ QUESTA CELLA NON CURA NIENTE: presidia la GIUNTURA, cioe' rende rosso il
terzo sintomo prima che qualcuno lo paghi. Due patch chiudono i due sintomi
noti e lasciano la strada aperta al prossimo; questo file la chiude.

⚠️ NASCE ROSSO, ED E' VOLUTO: `test_include_superseded_vale_anche_col_tempo`
fallisce sul codice attuale — e' il RED della cura, non un difetto del banco.
Diventa verde quando il ramo `as_of` inoltra l'opzione.

Niente giudice: le scritture passano da `sm.store()` diretto e le date stanno
su `asserted_at` con un epoch FISSO. Un test che legge l'orologio del muro e'
una prova che cambia da sola — misurato il 06/09: un fratello di questo file
e' caduto in CI solo perche' eseguito a cavallo della mezzanotte UTC.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory
from verimem.semantic import Fact

_BASE = 1_700_000_000.0
_DAY = 86400.0
#: l'istante che chiediamo: DOPO il ritiro, cosi' il ramo `as_of` e' esercitato
#: davvero e non si limita a restituire il presente.
_ISTANTE_T = _BASE + 300 * _DAY


@pytest.fixture()
def memoria(tmp_path) -> Memory:
    """TRE fatti in catena, non due — il caso e' della QA e distingue di piu'.

    ⚠️ CON DUE FATTI LA CELLA PROVA MENO. Se all'istante chiesto il ritirato
    e' l'unico «altro», `as_of` da solo e `as_of + include_superseded` possono
    rendere insiemi che non separano «i filtri COMPONGONO» da «uno dei due e'
    IGNORATO». Con tre:

        A (asserito _BASE)      --ritirato da-->  B  ... T ...  --> C

    all'istante T il corrente e' B, A e' GIA' ritirato, C non esiste ancora.
    Quindi `as_of=T` deve rendere SOLO B, e `as_of=T` + `include_superseded`
    deve rendere B **e** A: due richieste che chiedono cose DIVERSE, ed e'
    l'unico modo di vedere se il secondo filtro arriva.
    """
    m = Memory(str(tmp_path / "s.db"))
    m.semantic.store(Fact(id="A", proposition="Il canone e' 2400 euro.",
                          topic="t", asserted_at=_BASE), embed="sync")
    m.semantic.store(Fact(id="B", proposition="Il canone e' 2900 euro.",
                          topic="t", asserted_at=_BASE + 100 * _DAY), embed="sync")
    m.semantic.store(Fact(id="C", proposition="Il canone e' 3400 euro.",
                          topic="t", asserted_at=_BASE + 500 * _DAY), embed="sync")
    m.semantic.supersede("A", "B", principal="test:suite",
                         reason="same-source evolution")
    m.semantic.supersede("B", "C", principal="test:suite",
                         reason="same-source evolution")
    return m


def _ids(risultati) -> list[str]:
    return sorted(r.get("id") for r in risultati if isinstance(r, dict))


def test_controllo_positivo_i_due_rami_rispondono(memoria) -> None:
    """Se questo cade, tutto il resto del file non misura niente."""
    assert _ids(memoria.search("quanto e' il canone", k=5)) == ["C"]
    assert _ids(memoria.search("quanto e' il canone", k=5,
                               as_of=_ISTANTE_T)) == ["B"], (
        "il ramo `as_of` non risponde nemmeno il corrente: la cella e' cieca")


def test_include_superseded_vale_anche_col_tempo(memoria) -> None:
    """L'opzione deve valere su ENTRAMBI i rami, o essere rifiutata su uno.

    ⚠️ ROSSO SUL CODICE ATTUALE, ed e' il punto: `Memory.search` accetta
    `include_superseded` nella firma pubblica e il ramo `as_of` non lo
    inoltra a `recall_as_of` — che infatti non lo accetta nemmeno. Il
    chiamante chiede i ritirati, non li riceve, e NESSUNO glielo dice.
    E' la stessa forma curata sulle due porte MCP il 05/09 (un parametro
    accettato e ingoiato in silenzio): qui e' sulla TERZA porta.
    """
    q = "quanto e' il canone"
    senza_tempo = _ids(memoria.search(q, k=5, include_superseded=True))
    assert senza_tempo == ["A", "B", "C"], (
        "CONTROLLO: senza `as_of` l'opzione funziona — se cade qui, il "
        "difetto e' altrove e questa cella non c'entra")

    col_tempo = _ids(memoria.search(q, k=5, as_of=_ISTANTE_T,
                                    include_superseded=True))
    assert col_tempo == ["A", "B"], (
        "I DUE RAMI DIVERGONO: `include_superseded` vale senza `as_of` e "
        "viene IGNORATO con `as_of`. Un parametro pubblico accettato e "
        "ingoiato in silenzio e' il difetto che il pezzo 3 ha chiuso sulle "
        "porte MCP: questa e' la terza porta, e da qui passa anche la CLI")


def test_ogni_opzione_pubblica_o_vale_su_entrambi_i_rami_o_e_rifiutata(
        memoria) -> None:
    """La regola generale, cosi' il PROSSIMO parametro non ripete la storia.

    Non elenca i sintomi noti: prende le opzioni dalla FIRMA e chiede che
    ognuna non sparisca in silenzio quando si aggiunge `as_of`. Un parametro
    nuovo aggiunto domani finisce qui dentro senza che nessuno lo aggiunga.
    """
    import inspect

    q = "quanto e' il canone"
    firma = inspect.signature(Memory.search).parameters
    #: le opzioni booleane che cambiano CIO' CHE TORNA (non come e' ordinato)
    da_provare = [n for n in ("include_superseded", "include_beliefs", "deep")
                  if n in firma]
    assert da_provare, "la firma non espone piu' quelle opzioni: aggiorna la cella"

    divergenti = []
    for nome in da_provare:
        a = _ids(memoria.search(q, k=5, **{nome: True}))
        b = _ids(memoria.search(q, k=5, as_of=_ISTANTE_T, **{nome: True}))
        base_a = _ids(memoria.search(q, k=5))
        base_b = _ids(memoria.search(q, k=5, as_of=_ISTANTE_T))
        #: l'opzione "morde" sul ramo B se cambia il risultato; se morde di
        #: la' e non di qua, i due rami non portano la stessa cosa.
        if a != base_a and b == base_b:
            divergenti.append(nome)

    assert not divergenti, (
        f"opzioni che valgono SENZA `as_of` e spariscono CON `as_of`: "
        f"{divergenti}. O il ramo `as_of` le inoltra, o la firma le rifiuta "
        "quando c'e' `as_of` — quello che non va bene e' ingoiarle in silenzio")
