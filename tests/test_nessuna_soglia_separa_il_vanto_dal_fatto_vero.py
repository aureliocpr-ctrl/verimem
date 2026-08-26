"""Non esiste una soglia di grounding che separi il vanto infondato dal fatto vero.

Chiude la domanda «il difetto si aggiusta alzando un parametro?»: no.

Misurato il 2026-08-26 alle 20:40, `15b7cd2e`, fuori da pytest, store
temporaneo, `validate="full"`. Otto fonti, ognuna enuncia un fatto E nomina un
difetto; VERO = cio' che la fonte dice, VANTO = la conformita' che la fonte non
dice (e a volte quasi nega):

    VERO   trattenuti 0/8   grounding  97 · 100 · 100 · 100 · 100 · 100 · 100 · 100
    VANTO  trattenuti 3/8   grounding   1 ·   1 ·   7 ·  89 ·  93 ·  95 ·  98 ·  99
    min(VERO) 97.5   max(VANTO) 99.3   ->  si sovrappongono
    vanti con grounding >= del VERO piu' basso: 2 su 8

Il caso peggiore: fonte «Il lotto B12 e' arrivato il 3 marzo con 40 pezzi. Due
pezzi risultano difformi.» — claim «Il lotto B12 e' conforme alle specifiche.»
-> **99.3, ammesso**. Non e' un silenzio: e' quasi il contrario.

E la cattura non e' consistente dentro la stessa classe. Tre casi hanno la
stessa struttura — la fonte nomina un difetto, il claim afferma la conformita':

    «lavora a pieno regime» / «la quarta e' ferma»          -> TRATT 0.8
    «arrived in good condition» / «One unit was damaged»    -> TRATT 1.1
    «e' conforme alle specifiche» / «due pezzi difformi»    -> 99.3, passa

Due catturati, uno no. Non ho la spiegazione e non la invento.

⚖️ Non e' un veto sul prodotto: sulla CONTRADDIZIONE esplicita il moat e' 4/4
con grounding 0.6-1.3, margine enorme (misura indipendente di ws3: 0/10
falsita' ammesse nei due versi). E `README:30-32` dichiara gia' la lacuna e
dice che si chiude «only with an llm judge» — su quel punto la vetrina e'
onesta. Cio' che questo banco aggiunge e' che **non si chiude con un
parametro**.

⚠️ Perche' 4 casi bastano qui e non bastavano prima. Lo stesso banco con 4
blocchi diversi concludeva «una soglia esiste» (min VERO 99.3 · max VANTO 96.8)
ed era falso. La differenza non e' il numero: e' il tipo logico. «Una soglia
esiste» e' universale e vuole una popolazione; «non esiste» e' esistenziale e
basta un controesempio. Questo banco ne tiene due.

⚠️ Dove non protegge: CE locale, nessun giudice llm iniettato
(`Memory(llm=...)`, `client.py:410`). Se un giorno gira con l'llm, il quadro
puo' cambiare e questi xfail vanno rimisurati, non cancellati.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from verimem.client import Memory

# fonte, fatto VERO, VANTO che la fonte non sostiene
CASI = [
    (
        "Il lotto B12 e arrivato il 3 marzo con 40 pezzi. Due pezzi risultano difformi.",
        "Il lotto B12 e arrivato il 3 marzo con 40 pezzi.",
        "Il lotto B12 e conforme alle specifiche.",
    ),
    (
        "The audit started on March 1 and covers three departments.",
        "The audit covers three departments.",
        "The audit found no irregularities.",
    ),
]


def _g(prop: str, fonte: str) -> tuple[str, float | None]:
    mem = Memory(str(Path(tempfile.mkdtemp()) / "s.db"))
    ric = mem.add(prop, topic="t/soglia", source=fonte, validate="full")
    return str(ric.get("status")), ric.get("grounding_score")


@pytest.mark.parametrize("fonte,vero,_vanto", CASI)
def test_CONTROLLO_il_fatto_che_la_fonte_dice_resta_ammesso(fonte, vero, _vanto):
    """Il righello. Se il VERO cade, il confronto sotto non significa nulla."""
    stato, punteggio = _g(vero, fonte)
    assert stato != "quarantined", (
        f"un fatto che la fonte enuncia viene rifiutato: {stato} g={punteggio}"
    )


@pytest.mark.xfail(
    strict=True,
    reason="il vanto che la fonte non sostiene entra con grounding alto: "
    "min(VERO) 97.5 contro max(VANTO) 99.3, nessuna soglia li separa (26/08)",
)
@pytest.mark.parametrize("fonte,_vero,vanto", CASI)
def test_il_vanto_che_la_fonte_non_sostiene_dovrebbe_cadere(fonte, _vero, vanto):
    stato, punteggio = _g(vanto, fonte)
    assert stato == "quarantined", f"ammesso con g={punteggio}"


def test_LA_SOVRAPPOSIZIONE_e_questo_e_il_cuore():
    """I due punteggi si scavalcano: il vanto prende piu' del fatto vero.

    Se un giorno questo test fallisce perche' il vanto e' sceso sotto il vero,
    la separazione e' comparsa: rimisurare tutto il banco, e' una buona notizia.
    """
    fonte, vero, vanto = CASI[0]
    _, g_vero = _g(vero, fonte)
    stato_v, g_vanto = _g(vanto, fonte)
    assert isinstance(g_vero, (int, float)) and isinstance(g_vanto, (int, float)), (
        f"un punteggio manca: vero={g_vero} vanto={g_vanto} — senza numeri il "
        "confronto non si puo' fare e questo banco va riscritto"
    )
    assert stato_v != "quarantined", (
        f"il vanto ora e' trattenuto (g={g_vanto}): buona notizia, aggiornare il banco"
    )
    assert g_vanto > 90, (
        f"il vanto prende {g_vanto}: se e' sceso molto sotto il vero ({g_vero}), "
        "la separazione sta comparendo e il banco va rimisurato"
    )
