"""Una FONTE non offre il numero di un riferimento — e il claim non lo afferma.

CRONACA, e comincia con un mio ritiro. Questo file si chiamava
`test_la_terza_potatura_era_fuori_dall_esenzione.py` e sosteneva l'opposto:
che `come_fonte=True` dovesse vedere anche `art.15`, `pag.7`, `fig.3`. La cura
che difendeva (`fb2ff485`, 30/08 13:03) e' **RITIRATA**, e la ragione e' che
misurava al livello sbagliato.

    28/08  `29ab5544`  «Art. 5» in una fonte non e' la quantita' 5, o un claim
                       che inventa «5 rate» risulta sostenuto dal numero
                       dell'articolo.
    30/08  `fb2ff485`  esenta la lettura-fonte da quella potatura, perche' alla
                       FUNZIONE i casi visibili passavano da 8/8 a 5/8.
    30/08  20:16       i due presidi si contraddicono alla lettera e la suite
                       porta **12 rossi**: sono il presidio di `29ab5544`,
                       spento dalla cura successiva.

⇒ La domanda non era «quale riga» ma **quale delle due situazioni si presenta
alla PORTA**. Misurato su `valori_non_nella_fonte`, il produttore di `L4.1`
(banco `ws3-il-riferimento-nella-fonte-alla-porta-del-prodotto.py`)::

    caso                              esenzione ATTIVA   esenzione REVOCATA
    claim che CITA «all'art. 15»          0 avvisi            0 avvisi
    claim che CITA «pagina 7»             0 avvisi            0 avvisi
    claim che INVENTA «5 rate»            0 avvisi   <-       1 avviso
    idem in inglese, «5 instalments»      0 avvisi   <-       1 avviso
    CONTROLLO, numero assente ovunque     1 avviso            1 avviso

🔑 **L'esenzione non comprava nulla e costava un falso negativo.** Il motivo e'
una dissimmetria che non avevo considerato: la potatura sul lato CLAIM non e'
in discussione, quindi **un claim che cita un riferimento non porta quel numero
nel confronto** e non puo' chiedere alla fonte di contenerlo. Il caso che
`fb2ff485` diceva di curare non e' raggiungibile da quella porta; quello che
riapriva — la fonte che SOSTIENE un numero inventato — si'.

⚠️ E LA MISURA DEL 30/08 NON ERA SBAGLIATA: era al livello sbagliato. «5/8
contro 8/8» e' vero **della funzione**. Alla porta del prodotto quei tre casi
non arrivano mai. E' la lezione di casa *regex < funzione pubblica < porta del
prodotto*, pagata da chi l'aveva gia' scritta.

QUESTO FILE MISURA TRE POPOLAZIONI, e serve tutte e tre:
  [1] i numeri dopo un'abbreviazione che NON e' un riferimento -> la fonte li vede
  [2] i numeri di un riferimento -> nessuna delle due letture li offre
  [3] un claim non afferma il numero del proprio riferimento
Con la sola [1] si «cura» cancellando `29ab5544`; con la sola [2] si cancella il
presidio del 07/08; con la sola [3] non si vede la regressione sulla fonte.
"""

from __future__ import annotations

import pytest

from verimem.quantity_match import extract_quantities

#: [1] Gli otto casi del presidio del 07/08 (`665ce380`) MENO i tre che sono
#: riferimenti veri: qui l'abbreviazione nomina una GRANDEZZA (grado,
#: temperatura, totale, numero di registro), e il numero e' la misura.
DOPO_UNA_ABBREVIAZIONE = [
    ("grad.3", 3.0),
    ("temp.22", 22.0),
    ("il n.42 del registro", 42.0),
    ("tot.300 pezzi", 300.0),
    ("Nr.5 im Lager", 5.0),
]

#: [2] I tre che il 07/08 aveva messo nella stessa lista **per la forma**
#: (abbreviazione + punto + cifra) e che sono **riferimenti** per il senso.
#: Restano potati in ENTRAMBE le letture: nessun claim li chiede alla fonte, e
#: offrirli sostiene i numeri inventati. Misurato alla porta, tabella sopra.
RIFERIMENTI_ANCHE_NELLA_FONTE = [
    ("l'art.15 del codice", 15.0),
    ("vedi pag.7", 7.0),
    ("fig.3", 3.0),
]

#: [3] La potatura sul lato CLAIM, che nessuna delle due cure ha mai toccato.
SOLO_PUNTATORI_NEL_CLAIM = [
    "l'articolo 15 del codice prevede la penale",
    "vedi pagina 7 del manuale",
    "come mostra la figura 3",
]


def _valori(testo: str, *, come_fonte: bool) -> set[float]:
    return {v for _u, v in extract_quantities(testo, come_fonte=come_fonte)}


# ------------------------------- [1] LA GRANDEZZA ABBREVIATA RESTA VISIBILE --
@pytest.mark.parametrize("frase,valore", DOPO_UNA_ABBREVIAZIONE)
def test_una_fonte_vede_la_grandezza_dopo_un_abbreviazione(frase: str, valore: float):
    """Il presidio del 07/08, sulla parte che e' davvero una grandezza.
    «grad.3» dice grado 3: non vederlo fa concludere che la fonte non contenga
    il numero, e il claim che lo cita viene quarantinato da vero."""
    visti = _valori(frase, come_fonte=True)
    assert valore in visti, (
        f"«{frase}» come FONTE -> {visti or 'set()'}: il numero e' NEL testo e "
        f"la lettura-fonte non lo vede")


# ------------------------------------- [2] IL RIFERIMENTO NON E' UN VALORE --
@pytest.mark.parametrize("frase,valore", RIFERIMENTI_ANCHE_NELLA_FONTE)
def test_una_fonte_non_offre_il_numero_di_un_riferimento(frase: str, valore: float):
    """⚠️⚠️ LA POPOLAZIONE CHE HO IMPARATO A MISURARE PAGANDOLA. Se la fonte
    offre il 15 di «art.15» come valore nudo, un claim che inventa «15 giorni»
    risulta sostenuto: e' il difetto che `29ab5544` esiste per chiudere, e che
    `fb2ff485` aveva riaperto per tre giorni... anzi per sette ore."""
    visti = _valori(frase, come_fonte=True)
    assert valore not in visti, (
        f"«{frase}» come FONTE -> {visti}: il numero di un riferimento e' "
        f"tornato disponibile come valore, e sostiene i numeri inventati")


# ------------------------------------------ [3] E IL CLAIM NON LO AFFERMA --
@pytest.mark.parametrize("claim", SOLO_PUNTATORI_NEL_CLAIM)
def test_un_claim_non_afferma_il_numero_del_proprio_riferimento(claim: str):
    """In un CLAIM «l'articolo 15» non afferma la quantita' 15: e' un puntatore,
    e contestarlo alla fonte produceva la quarantena di fatti veri."""
    visti = _valori(claim, come_fonte=False)
    assert not visti, (
        f"«{claim}» come CLAIM -> {visti}: il numero di un riferimento e' "
        f"tornato a essere un'affermazione quantitativa; `29ab5544` e' annullata."
    )


def test_le_tre_popolazioni_in_una_riga():
    """La riga di sintesi che rende leggibile un rosso parziale: senza questa,
    tre numeri si distinguono solo leggendo undici righe di parametrizzazione."""
    grandezze = sum(v in _valori(f, come_fonte=True)
                    for f, v in DOPO_UNA_ABBREVIAZIONE)
    riferimenti = sum(v not in _valori(f, come_fonte=True)
                      for f, v in RIFERIMENTI_ANCHE_NELLA_FONTE)
    claim = sum(not _valori(c, come_fonte=False)
                for c in SOLO_PUNTATORI_NEL_CLAIM)
    atteso = (len(DOPO_UNA_ABBREVIAZIONE), len(RIFERIMENTI_ANCHE_NELLA_FONTE),
              len(SOLO_PUNTATORI_NEL_CLAIM))
    assert (grandezze, riferimenti, claim) == atteso, (
        f"grandezze {grandezze}/{atteso[0]} · riferimenti {riferimenti}/"
        f"{atteso[1]} · claim {claim}/{atteso[2]}"
    )
