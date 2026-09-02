"""Costruire una popolazione DAL CORPUS senza rompere il righello.

Scritto da ws2 il 2026-08-24 dopo aver rotto lo stesso banco **quattro volte in
un'ora**. Non è una libreria di comodo: ognuna delle cinque funzioni qui dentro
è un errore che ho commesso, misurato, e che mi è costato un numero pubblicato e
poi ritirato.

⚠️ NASCE DA UNA REGOLA DI @ws1 (24/08 20:13) più una correzione mia (20:18):
un presidio verifica una proprietà più debole di quella che promette **quando
non interroga la porta** (ws1) **oppure quando non gira sulla popolazione del
prodotto** (ws2). Le due condizioni sono indipendenti: si può misurare alla
porta giusta e ottenere lo stesso un numero falso, perché le frasi le ha scritte
chi voleva vedere il difetto.

I CINQUE ERRORI, ognuno con il numero che ha prodotto
-----------------------------------------------------
1. TRONCARE DOPO AVER SOSTITUITO
   Costruivo la domanda «scambiata» con ``p.replace(vecchio, nuovo)[:150]``.
   Sul corpus la posizione mediana del primo identificatore è il carattere
   **262** su proposizioni lunghe in mediana **585**: in **11 casi su 20** il
   token cadeva fuori dalla finestra e la domanda «scambiata» era BYTE-IDENTICA
   a quella giusta. Facevo la stessa domanda due volte e chiamavo «0 astensioni»
   il risultato.  →  :func:`finestra_attorno` + :func:`assert_diverse`

2. IDENTIFICATORI DEGENERI
   ``sorted(tutti)[0]`` restituisce ``'000000'``: gli zeri vengono per primi.
   Venti celle usavano lo stesso id degenere.  →  :func:`identificatore_utile`

3. CONTROLLI SCELTI DALLA PROPRIA TESTA
   Il mio negativo era ``176,6`` — UNA cifra dopo la virgola. Non ho mai provato
   un decimale a TRE cifre, che è la forma vera del corpus, e la regex contava
   ``0.624`` (un coseno) come «numero con separatore delle migliaia»: **741
   falsi**, con i controlli 5 su 5 passati.  →  :func:`controlli_dal_corpus`

4. IL RIGHELLO TAUTOLOGICO
   In una tabella 2×2 definivo «servibile» come «non quarantinato E non
   ritirato», ma il perdente è ritirato **per definizione**: una riga era zero
   per costruzione (0/0/751/1198) e il controllo «le celle sommano al totale»
   PASSAVA lo stesso.  🔑 Una somma non smaschera una tautologia.
   →  :func:`assert_tutte_le_celle_possibili`

5. CONSEGNARE IL CONTEGGIO SENZA GLI ESEMPI
   Ogni volta che il numero era falso, a smascherarlo NON è stato un controllo:
   sono stati gli esempi stampati accanto.  →  :func:`stampa_con_esempi`

📌 REGIME, sempre: fuori da pytest (``tests/conftest.py`` sostituisce
l'embedder con uno stub SHA-256 su ogni test) e su una COPIA del corpus, perché
una misura non deve poter scrivere sulla memoria di produzione.

⚖️ COSA SI TRASFERISCE E COSA NO — misurato, non supposto (@ws1, 24/08 20:42)
   L'ha eseguita per prima e ha riportato **quale parte** ha usato:

   · :func:`assert_diverse` e :func:`identificatore_utile` — usate, sul suo
     campione «scartate 0 su 15». Sono due funzioni di quattro righe.
   · :func:`coppie_scambiate` — **NON usata**: è tarata sul fronte di chi l'ha
     scritta (identificatori scambiati) e il suo era «coppie same-topic».
   · e il pezzo che le mancava non era il codice ma **una riga di docstring**:
     «un banco che dice "scartate 0" ha detto qualcosa; uno che non le conta
     no». Il suo banco non contava le scartate — *non perché credesse fossero
     zero, ma perché non si era posta la domanda*.

   🔑 **Il valore trasferibile erano le due funzioni piccole e una frase, non
   l'impianto grosso.** Chi arriva qui prenda i presidi e lasci
   :func:`coppie_scambiate` se il suo fenomeno non è «stessa frase, token
   diverso»: riscriverla per il proprio caso costa meno che piegarla.
"""
from __future__ import annotations

import random
import re
import sqlite3
from typing import Callable, Iterable, Sequence


def copia_consistente(sorgente: str, destinazione: str) -> str:
    """Copia il db con l'API di backup di sqlite: gestisce il WAL da sé.

    Copiare il file a mano lascia fuori il ``-wal`` e si ottiene uno stato
    vecchio senza nessun errore — un'altra misura che sembra buona.
    """
    a = sqlite3.connect(f"file:{sorgente}?mode=ro", uri=True)
    b = sqlite3.connect(destinazione)
    try:
        a.backup(b)
    finally:
        b.close()
        a.close()
    return destinazione


def identificatore_utile(x: str, *, minimo_distinti: int = 3) -> bool:
    """Scarta ``000000``, ``11111`` e simili: non sono casi, sono artefatti.

    Un identificatore con meno di tre caratteri distinti quasi sempre viene
    dall'ordinamento, non dal corpus.
    """
    return len(set(x)) >= minimo_distinti


def finestra_attorno(testo: str, posizione: int, largo: int = 150) -> tuple[int, int]:
    """Finestra CENTRATA sul token: garantisce che il token sia nella domanda.

    È la cura dell'errore n° 1. Troncare dall'inizio (``testo[:largo]``) butta
    fuori proprio ciò che si sta variando, e le due varianti diventano uguali.
    """
    inizio = max(0, posizione - largo // 2)
    return inizio, inizio + largo


def assert_diverse(a: str, b: str) -> bool:
    """True se le due varianti differiscono davvero. Chi la usa SCARTA e CONTA.

    ⚠️ Non sollevare: i casi degeneri vanno **contati e dichiarati**, non
    nascosti. Un banco che dice «scartate 0» ha detto qualcosa; uno che non le
    conta non sa cosa ha misurato.
    """
    return a != b


def controlli_dal_corpus(
    righe: Iterable[tuple[str, str]],
    predicato: Callable[[str], bool],
    *,
    quanti: int = 5,
) -> list[tuple[str, bool, str]]:
    """Estrae casi VERI dal corpus per farne controlli, invece di inventarli.

    Restituisce ``(testo, esito_del_predicato, id)`` per i primi ``quanti``
    positivi e altrettanti negativi. Chi chiama li LEGGE: è la lettura che
    smaschera, non il conteggio.

    È la cura dell'errore n° 3: i miei negativi inventati passavano tutti
    mentre il predicato sbagliava sul 90% della popolazione reale.
    """
    pos: list[tuple[str, bool, str]] = []
    neg: list[tuple[str, bool, str]] = []
    for fid, testo in righe:
        if not testo:
            continue
        esito = predicato(testo)
        bersaglio = pos if esito else neg
        if len(bersaglio) < quanti:
            bersaglio.append((testo[:110], esito, fid))
        if len(pos) >= quanti and len(neg) >= quanti:
            break
    return pos + neg


def assert_tutte_le_celle_possibili(
    celle: dict[tuple[str, ...], int],
    attese: Sequence[tuple[str, ...]],
) -> tuple[bool, list[tuple[str, ...]]]:
    """Il controllo che una SOMMA non fa: ogni cella dev'essere raggiungibile.

    Se una cella è vuota può essere un fatto del mondo — oppure il segno che il
    criterio la rende **impossibile per costruzione**. Chi chiama guarda le
    celle vuote e per ognuna si chiede: *«il mio predicato potrebbe mai
    metterci qualcosa?»*  Se la risposta è no, il referto misura la definizione
    e non il prodotto.

    È la cura dell'errore n° 4.
    """
    vuote = [c for c in attese if not celle.get(c)]
    return (not vuote), vuote


def stampa_con_esempi(
    etichetta: str,
    quanti: int,
    totale: int,
    esempi: Sequence[str],
    *,
    massimo: int = 5,
) -> None:
    """Un conteggio non si consegna da solo. È la cura dell'errore n° 5."""
    quota = f"  ({quanti / totale * 100:.2f}%)" if totale else ""
    print(f"  {etichetta:<48} {quanti:>6}/{totale}{quota}")
    for e in list(esempi)[:massimo]:
        print(f"      · {' '.join(str(e).split())[:104]}")
    if quanti and not esempi:
        print("      ⚠️ nessun esempio stampato: il numero non è verificabile")


def coppie_scambiate(
    righe: Iterable[tuple[str, str]],
    token: re.Pattern[str],
    *,
    quante: int = 20,
    seme: int = 20260824,
    largo: int = 150,
) -> tuple[list[tuple[str, str, str, str, str]], int]:
    """La popolazione «stessa frase, token diverso», costruita senza i 5 errori.

    Restituisce ``(coppie, scartate)`` dove ogni coppia è
    ``(fact_id, domanda_giusta, token_originale, domanda_scambiata, token_altro)``
    e ``scartate`` conta i casi degeneri — **da dichiarare nel referto**.

    Il token si sostituisce PRIMA e la finestra si centra DOPO, così il token
    scambiato è per costruzione dentro la domanda; poi si verifica lo stesso con
    :func:`assert_diverse`, perché una garanzia per costruzione che non viene
    controllata è un ricordo, non un presidio.
    """
    trovati: list[tuple[str, str, int, str]] = []
    for fid, testo in righe:
        if not testo:
            continue
        for m in token.finditer(testo):
            if identificatore_utile(m.group(0)):
                trovati.append((fid, testo, m.start(), m.group(0)))
                break
    vocabolario = sorted({t for *_, t in trovati})
    rnd = random.Random(seme)
    coppie: list[tuple[str, str, str, str, str]] = []
    scartate = 0
    for fid, testo, pos, mio in trovati:
        alternativi = [x for x in vocabolario if x != mio and len(x) == len(mio)]
        if not alternativi:
            continue
        altro = rnd.choice(alternativi)
        a, b = finestra_attorno(testo, pos, largo)
        giusta = testo[a:b]
        scambiata = testo.replace(mio, altro, 1)[a:b]
        if not assert_diverse(giusta, scambiata):
            scartate += 1
            continue
        coppie.append((fid, giusta, mio, scambiata, altro))
        if len(coppie) >= quante:
            break
    return coppie, scartate
