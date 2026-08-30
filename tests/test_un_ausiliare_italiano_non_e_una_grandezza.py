"""Un ausiliare italiano non e' una grandezza — e la lista lo sapeva solo in inglese.

⚠️ **QUESTO TEST NASCE DA UN DIFETTO DELLA CURA DI STAMANE**, non da un difetto
altrui. `_GRAMMATICA` (introdotta oggi in `af0422d7`) filtrava dalla ricevuta le
parole che non nominano una grandezza, e conteneva **sei ausiliari inglesi**
(`is are was were be been`) e **zero ausiliari italiani** — in un prodotto usato
in italiano. E' la classe ③ registrata in casa, *liste monolingue*, commessa
poche ore dopo averla citata.

Il caso che l'ha fatta vedere e' una ricevuta vera del prodotto, 19:02:36,
salvando un fatto::

    146 qui e' «hanno», nella fonte «prima del numero: quarantined»

Il lato `nella_fonte` e' curato — mostra il lato precedente. Il lato `nel_claim`
mostra **«hanno»**: ⇒ **la cura ha mancato esattamente il caso che l'aveva
motivata.**

MISURATO PRIMA DI CURARE (banco `quali-parole-la-ricevuta-mostra-come-
grandezza.py`, popolazione **INTERA** — 6261 fatti vivi con fonte, 5222 riusi,
funzione pura)::

    lato «nel_claim»  : 221 occorrenze su 3323  (6.7%)
    lato «nella_fonte»:  14 occorrenze su 6004  (0.2%)

⇒ 🔑 **L'asimmetria e' il reperto**: il claim e' prosa italiana, la fonte e'
quasi sempre output di macchina. Una lista tarata sull'inglese sbaglia **35
volte piu' spesso** sul lato che l'utente scrive. Nella classifica del lato
claim, «sono» e' il 3° token piu' frequente (92) e «hanno» il 12° (61).

⚖️ **COSA NON CAMBIA**: il **criterio** con cui `L4.2` decide non legge questa
lista — `valori_riusati_da_altro_contesto` confronta i token GREZZI. Cambia solo
il **testo della ricevuta**. Se cambiasse il criterio, questo test non
basterebbe e servirebbe una misura sui verdetti.

📌 **AMBIGUI ESCLUSI DI PROPOSITO**: «danno», «conta», «stato», «era» in
italiano sono **anche sostantivi**, quindi possono legittimamente essere una
grandezza. Non entrano in una lista di non-grandezze, per quanto frequenti.
"""

from __future__ import annotations

import pytest

from verimem.vicinato_del_valore import _GRAMMATICA, _da_mostrare

# ── IL CUORE: il caso vero, preso dalla ricevuta del prodotto

def test_il_caso_della_ricevuta_delle_19_02() -> None:
    """«146 hanno status quarantined» contro «status quarantined 146»."""
    reso = _da_mostrare({"hanno"}, {"quarantined"})
    assert "hanno" not in reso.split(), reso
    assert reso == "prima del numero: quarantined"


@pytest.mark.parametrize("ausiliare", [
    "ha", "hanno", "sono", "sia", "siano", "sta", "stanno", "viene",
    "vengono", "risulta", "resta", "restano", "diventano",
])
def test_gli_ausiliari_italiani_sono_filtrati(ausiliare: str) -> None:
    """I dodici candidati escono dal corpus, non dalla mia intuizione: sono i
    token che il banco ha trovato adiacenti a un numero."""
    assert ausiliare in _GRAMMATICA, (
        f"«{ausiliare}» non e' filtrata: la ricevuta lo mostrerebbe come"
        " grandezza")


@pytest.mark.parametrize("ausiliare", ["has", "have", "had"])
def test_anche_l_inglese_era_incompleto(ausiliare: str) -> None:
    """La lista aveva `is/are/was/were/be/been` ma non le forme di `have`:
    monolingue **e** parziale nella lingua che copriva."""
    assert ausiliare in _GRAMMATICA


def test_un_ausiliare_non_nasconde_una_grandezza_vera() -> None:
    """Se accanto al numero c'e' SIA un ausiliare SIA una grandezza, resta la
    grandezza — la cura toglie rumore, non informazione."""
    assert _da_mostrare({"hanno", "fatti"}, set()) == "fatti"


# ── GLI AMBIGUI: la cura NON deve prenderli

@pytest.mark.parametrize("ambigua", ["danno", "conta", "stato", "era"])
def test_le_parole_ambigue_restano_mostrate(ambigua: str) -> None:
    """In italiano sono anche sostantivi: «il danno», «la conta», «lo stato»,
    «l'era». Filtrarle nasconderebbe una grandezza vera."""
    assert ambigua not in _GRAMMATICA, (
        f"«{ambigua}» e' anche un sostantivo: filtrarla toglie una grandezza"
        " possibile")
    assert _da_mostrare({ambigua}, set()) == ambigua


# ── I PRESIDI ESISTENTI, che la cura non deve rompere

def test_presidio_il_precedente_INTEGRA_e_non_sostituisce() -> None:
    assert _da_mostrare({"pallet"}, {"riga"}) == "pallet"


def test_presidio_quando_e_tutta_grammatica_lo_DICE() -> None:
    reso = _da_mostrare({"hanno"}, {"di", "il"})
    assert "hanno" not in reso.split(), reso
    assert "grammatical" in reso or "nessuna" in reso, reso


def test_presidio_senza_parole_accanto_lo_dice() -> None:
    assert "nessuna parola" in _da_mostrare(set(), set())
