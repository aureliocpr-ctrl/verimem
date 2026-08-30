"""«grad.3» non conteneva nessun 3, e il fatto che lo citava veniva quarantinato.

IL DIFETTO, isolato da ws1 con due prove, ed è **la classe di oggi vista
dall'altro lato**. Nel parser «attaccato» faceva catturare di troppo (il numero
dentro un identificatore); qui fa NON riconoscere, e il costo è opposto e
peggiore — un fatto VERO viene bocciato::

    fonte  «Rilevazione: grad.3 su scala 5, temp.22 gradi»  -> solo (5.0)
    claim  «La rilevazione riporta grado 3 … e temperatura 22 gradi»
    ⇒ valori dichiarati ASSENTI dalla fonte: [3.0, 22.0]   ⇒ L4.1 quarantina

I due numeri *sono* nella fonte. Non vengono estratti perché il lookbehind
``(?<![A-Za-z0-9._])`` rifiuta ogni numero preceduto da un punto, e in italiano
il punto di abbreviazione davanti a un numero è una forma corrente::

    grad.3 · temp.22 · art.15 · pag.7 · n.42 · fig.3 · tab.2 · cap.4 · tot.300

⚠️ IL PUNTO NEL LOOKBEHIND SERVE, e la cura non lo toglie: senza, «1.2» darebbe
la quantità 2 e ogni versione o indirizzo IP si spezzerebbe in tronconi.

LA DISTINZIONE È STRUTTURALE E NON HA BISOGNO DI UNA LISTA DI ABBREVIAZIONI::

    1.2      punto fra due CIFRE          -> decimale o versione: NON catturare
    grad.3   punto fra LETTERA e cifra    -> abbreviazione: catturare

Il lookbehind diventa «non preceduto da cifra-punto» invece di «non preceduto
da punto». Nessuna lista da mantenere, e vale per ``art.``, ``§``, ``Nr.`` e per
ogni abbreviazione che nessuno di noi ha in mente.

MISURATO PRIMA DI SCRIVERE, su entrambe le popolazioni e sul corpus vero:
    recuperati    7/7   grad.3 temp.22 art.15 pag.7 n.42 tot.300 fig.3
    protetti      7/7   v1.2 · release 3.4.0 · 2.1.3 · 65.61.137.117 ·
                        127.0.0.1 · SKU300 · abc300
    corpus        160 proposizioni su 8951 cambiano (1,79%)
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import extract_quantities
from verimem.valore_non_nella_fonte import valori_non_nella_fonte

#: Il punto di abbreviazione: il numero che segue è una quantità vera.
#: ⚠️ TRE CASI SONO USCITI DA QUI IL 30/08 SERA, e non per farli sparire:
#: `art.15`, `pag.7` e `fig.3` erano in lista per la FORMA (abbreviazione,
#: punto, cifra) e sono RIFERIMENTI per il senso. Vivono ora in
#: `test_una_fonte_non_offre_il_numero_di_un_riferimento.py`, dove sono
#: asseriti con il segno OPPOSTO: la fonte non deve offrirli, o un claim che
#: inventa «15 giorni» risulta sostenuto dal numero dell'articolo. La
#: popolazione non si e' ridotta — ha cambiato segno, e resta misurata.
#: La misura che l'ha deciso e' alla PORTA (`valori_non_nella_fonte`), non
#: alla funzione: banco
#: `docs/stato-reale/banchi/ws3-il-riferimento-nella-fonte-alla-porta-del-prodotto.py`.
ABBREVIAZIONI = [
    ("grad.3", 3.0),
    ("temp.22", 22.0),
    ("il n.42 del registro", 42.0),
    ("tot.300 pezzi", 300.0),
    ("Nr.5 im Lager", 5.0),
]

#: ⚠️ LA POPOLAZIONE OPPOSTA, ed è la ragione per cui il punto sta nel
#: lookbehind: un numero dentro una versione o un indirizzo IP non è una
#: quantità, e spezzarlo in tronconi riempie il confronto numerico di rumore.
NON_SONO_QUANTITA = [
    "la versione v1.2 e' uscita",
    "release 3.4.0",
    "il file 2.1.3 pesa poco",
    "l'host e' 65.61.137.117",
    "il codice SKU300",
    "abc300 xyz",
]


@pytest.mark.parametrize("frase,valore", ABBREVIAZIONI)
def test_un_numero_dopo_una_abbreviazione_e_una_quantita(frase, valore):
    """IL CUORE: «grad.3» dice grado 3. Non vederlo fa concludere che la fonte
    non contenga il numero, e il claim che lo cita viene quarantinato — cioè un
    fatto vero esce dal recall per un punto.

    ⚠️ `come_fonte=True` DAL 30/08, ed è una parola che allinea la chiamata a ciò
    che questo docstring già diceva: parla della **FONTE** («fa concludere che
    *la fonte* non contenga il numero»), e la modalità-fonte è nata il 16/08
    (`da6d083e`), **nove giorni dopo questo test** (07/08, `665ce380`) — quando
    non esisteva, la modalità-claim era l'unica e coincideva.

    Il 28/08 `29ab5544` ha aggiunto una terza potatura (i riferimenti: «art. 15»
    in un CLAIM è un puntatore, non la quantità 15) e le due modalità hanno
    smesso di coincidere su `art.`/`pag.`/`fig.`. Il 30/08 pomeriggio
    `fb2ff485` ha esentato la lettura-fonte da quella potatura per riportare
    la lista a 8 su 8; **la sera quella cura e' stata RITIRATA**, perche' alla
    porta del prodotto l'esenzione non comprava nulla e faceva sostenere i
    numeri inventati.

    🔑 I tre casi che erano riferimenti stanno ora in
    `test_una_fonte_non_offre_il_numero_di_un_riferimento.py`, che misura TRE
    popolazioni: la grandezza abbreviata che la fonte deve vedere, il
    riferimento che nessuna delle due letture offre, e il claim che non
    afferma il numero del proprio riferimento.
    """
    valori = {v for _u, v in extract_quantities(frase, come_fonte=True)}
    assert valore in valori, (
        f"«{frase}» come FONTE -> {extract_quantities(frase, come_fonte=True)}")


@pytest.mark.parametrize("frase", NON_SONO_QUANTITA)
def test_CONTROLLO_POSITIVO_versioni_e_indirizzi_restano_fuori(frase):
    """⚠️ IL PRESIDIO. Senza il punto nel lookbehind «1.2» darebbe la quantità 2
    e «65.61.137.117» si spezzerebbe in quattro numeri che non misurano niente:
    è il rumore che questa guardia esiste per tenere fuori."""
    assert not extract_quantities(frase), frase


def test_il_fatto_di_ws1_non_viene_piu_quarantinato():
    """🔑 IL CASO END-TO-END, dalla porta che decide: prima i due numeri erano
    dichiarati assenti dalla fonte che li contiene, e L4.1 quarantinava."""
    fonte = "Rilevazione: grad.3 su scala 5, temp.22 gradi, cap.40100 Firenze"
    claim = "La rilevazione riporta grado 3 su scala 5 e temperatura 22 gradi."
    assenti = [v.valore for v in valori_non_nella_fonte(claim, fonte)]
    assert not assenti, f"dichiarati assenti da una fonte che li contiene: {assenti}"


def test_di_un_indirizzo_con_porta_si_salva_la_PORTA_e_non_gli_ottetti():
    """⚠️ UN MIO ERRORE CORRETTO DAL BANCO, e la distinzione che ne esce è
    giusta: avevo messo «Uvicorn su 127.0.0.1:8080» fra le frasi che non devono
    produrre nessuna quantità, e il test pretendeva che la cura sbagliasse.

    Gli OTTETTI dell'indirizzo restano fuori — è ciò che il lookbehind protegge
    — ma «8080» è un numero di porta, separato dai due punti, e un fatto può
    legittimamente affermarlo («il server ascolta sulla 8080»). Tenerlo è
    corretto; era il mio caso a chiedere troppo.
    """
    assert extract_quantities("Uvicorn su 127.0.0.1:8080") == {("", 8080.0)}


def test_CONTROLLO_POSITIVO_un_numero_DAVVERO_assente_resta_fermato():
    """⚠️ L'altra metà, senza la quale la cura è soddisfatta anche da un gate
    che non ferma più niente: se il claim inventa un numero, deve cadere."""
    fonte = "Rilevazione: grad.3 su scala 5, temp.22 gradi"
    claim = "La rilevazione riporta grado 3 e temperatura 99 gradi."
    assert [v.valore for v in valori_non_nella_fonte(claim, fonte)] == [99.0]
