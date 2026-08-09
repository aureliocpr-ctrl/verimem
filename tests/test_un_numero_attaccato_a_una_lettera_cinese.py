"""«罗维戈仓库500个托盘» non conteneva nessun numero. E nemmeno «abc300 pallet».

IL DIFETTO, isolato da ws1 con l'osservazione che lo rende curabile: **non è un
difetto CJK**. Il lookbehind ``(?<![\\w.])`` di ``_QUANT_RE`` rifiuta il numero
ogni volta che è preceduto da un carattere di parola, e ``\\w`` in Python
comprende gli ideogrammi — ma anche le lettere latine::

    abc300 pallet      -> []       il magazzino ha 300 pallet -> ('pallet', 300.0)
    SKU300 pallet      -> []       peso 300kg                 -> ('kg', 300.0)
    ordine-A300 pezzi  -> []
    罗维戈仓库500个托盘  -> []

In cinese, giapponese e thai il lookbehind è **sempre acceso**, perché lo spazio
non esiste: ogni numero è preceduto da un ideogramma. Il difetto è lo stesso del
latino, ma lì colpisce il 100% delle frasi invece dei casi limite.

📌 È IL GRADINO 3 della mappa di ws4, e la sua diagnosi era «la regex non assume
una lingua, assume la SEGMENTAZIONE PER SPAZI». Corretta, e la cura che ne
sembrava discendere — «aggiungere il supporto CJK» — era la strada sbagliata:
non c'è niente di CJK da aggiungere, c'è una classe di caratteri da restringere.

⚠️ IL LOOKBEHIND ESISTE PER UNA RAGIONE, e la cura non lo toglie: serve a non
leggere come quantità un pezzo di identificatore o di versione. ``SKU300`` non
contiene 300 pallet, ``v1.2`` non è una quantità. La cura restringe la classe da
«qualunque carattere di parola» a «lettera LATINA, cifra, punto o underscore»:
gli identificatori restano protetti — sono scritti in ASCII per costruzione —
e gli ideogrammi smettono di bloccare.

🔑 E RIPARA UN DIFETTO CHE NESSUNO CERCAVA, misurato scrivendo questo test::

    release 3.4.0    prima -> quantità 3.4      dopo -> nessuna
    il file 2.1.3    prima -> quantità 2.1      dopo -> nessuna

Le versioni a tre componenti venivano lette anche come quantità decimali,
perché il lookahead ``(?![\\w])`` non vedeva il punto che seguiva. Erano numeri
che entravano nel confronto numerico senza essere quantità di niente.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import extract_quantities

#: Scritture senza spazi: il numero è una quantità vera e va visto.
SENZA_SPAZI = [
    ("ZH", "罗维戈仓库500个托盘", 500.0),
    ("JA", "500個パレット", 500.0),
    ("TH", "คลัง500พาเลท", 500.0),
    ("ZH", "仓库有40件", 40.0),
]

#: ⚠️ LA POPOLAZIONE OPPOSTA, ed è quella per cui il lookbehind esiste: un
#: numero incastonato in un identificatore o in una versione NON è una quantità.
#: Senza questa metà, la cura è soddisfatta da un regex che cattura tutto.
NON_SONO_QUANTITA = [
    "il codice SKU300 e' nuovo",
    "abc300 xyz",
    "l'ordine-A300 e' partito",
    "la versione v1.2 e' uscita",
    "release 3.4.0",
    "il file 2.1.3 pesa poco",
    "codice_300",
]

#: Ciò che già funzionava e non deve muoversi.
NON_DEVONO_MUOVERSI = [
    ("il magazzino ha 300 pallet", ("pallet", 300.0)),
    ("на складе 40 паллет", ("паллет", 40.0)),
    ("peso 300kg", ("kg", 300.0)),
    ("(300 pallet)", ("pallet", 300.0)),
    ("la riunione e' durata 45 minuti", ("minuto", 45.0)),
]


@pytest.mark.parametrize("lingua,frase,valore", SENZA_SPAZI)
def test_una_quantita_senza_spazi_viene_vista(lingua, frase, valore):
    """IL CUORE: in cinese «仓库有40件» dice che il magazzino ha 40 pezzi. Senza
    catturare il numero, il confronto numerico non ha valori da opporre e la
    memoria in quelle lingue non si aggiorna mai — misurato da ws1 end-to-end:
    ZH→ZH lascia 2 fatti vivi dove IT→IT ne ritira uno."""
    valori = {v for _u, v in extract_quantities(frase)}
    assert valore in valori, f"{lingua}: «{frase}» -> {extract_quantities(frase)}"


@pytest.mark.parametrize("frase", NON_SONO_QUANTITA)
def test_CONTROLLO_POSITIVO_un_identificatore_non_e_una_quantita(frase):
    """⚠️ IL PRESIDIO CHE RENDE CONSEGNABILE LA CURA, ed è la ragione per cui il
    lookbehind esiste: «SKU300» non contiene 300 di niente, «v1.2» è una
    versione. Se la cura li catturasse, ogni codice prodotto diventerebbe una
    misura e i conflitti numerici si riempirebbero di rumore."""
    assert not extract_quantities(frase), frase


@pytest.mark.parametrize("frase,attesa", NON_DEVONO_MUOVERSI)
def test_CONTROLLO_POSITIVO_cio_che_funzionava_resta(frase, attesa):
    """La popolazione già verde: restringere una classe di caratteri può
    togliere quello che prima passava, e qui si misura che non succeda."""
    assert attesa in extract_quantities(frase), frase


def test_una_VERSIONE_a_tre_componenti_non_e_piu_anche_una_quantita():
    """🔑 IL DIFETTO RIPARATO SENZA CERCARLO, misurato scrivendo questo test.

    «release 3.4.0» produceva la quantità 3.4 e «il file 2.1.3» produceva 2.1:
    il lookahead non vedeva il punto che seguiva, quindi il troncone entrava nel
    confronto numerico come se fosse una misura. Due fatti che parlano di due
    release diverse potevano risultare in conflitto NUMERICO — su numeri che non
    misurano niente.
    """
    assert not extract_quantities("release 3.4.0")
    assert not extract_quantities("il file 2.1.3 pesa poco")
    # e la versione resta leggibile dal percorso che la riguarda
    from verimem.quantity_match import extract_versions
    assert extract_versions("release 3.4.0") == {"3.4.0"}
