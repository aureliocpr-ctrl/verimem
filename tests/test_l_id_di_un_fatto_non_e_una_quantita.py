"""L'id di un fatto non è un valore da cercare nella fonte.

IL DIFETTO, con l'output che l'ha mostrato
-------------------------------------------
Una caduta vera di CI, il 2026-09-12, gamba `ubuntu py3.12`, sul banco delle
due guardie — un banco che quel giorno era caduto **tre volte su PR che non lo
toccavano**::

    layer dei warning         = ['L4.1']
    quarantined_by (ricevuta) = 'L4.1'
    grounding_score           = 99.94818878173828
    withheld_despite_judge    = True

Il claim era «Nel verbale la coda aveva 500 elementi, come nel fatto
78222643329e.» e la fonte quel codice non lo nomina. L'estrattore spezzava il
codice alla lettera finale, leggeva **`78222643329`** come una quantità, non la
trovava nella fonte, e `L4.1` fermava un fatto **che il giudice aveva approvato
a 99,9**.

⇒ Non è il giudice e non è la soglia: è che **un identificatore veniva contato
fra le grandezze misurate.**

PERCHÉ ERA INTERMITTENTE, e il numero
--------------------------------------
L'id nasce casuale a ogni scrittura, quindi il difetto si presenta **solo
quando la forma dell'id lo permette**. Misurato su una popolazione casuale — non
sugli esempi scelti da chi scrive::

    2000 id casuali a 12 hex, stessa fonte, stesso claim
      prima della cura   22 su 2000 fermati   = 1,10 %
      dopo               9  su 2000           = 0,45 %

E l'ordine di grandezza torna con i fatti: **tre cadute in un giorno** su
qualche decina di run a sei gambe.

⚠️ IL RESIDUO È UN LIMITE DICHIARATO, NON UNA SVISTA
-----------------------------------------------------
Quei 9 su 2000 sono gli id di **sole cifre**: `000123456789` non si distingue da
un numero, e questa cura **non prova a indovinare**. Il criterio è «togli solo
ciò che NON PUÒ essere un decimale», cioè cifra **e** lettera insieme.
L'aritmetica lo conferma: un id di 12 hex senza nessuna lettera ha probabilità
``(10/16)**12 ≈ 0,35 %``, lo stesso ordine dello 0,45 % misurato.

🔑 Chi volesse chiudere anche quel residuo non lo faccia allargando il pattern:
dovrebbe far sapere all'estrattore **che quella stringa è un id**, e
l'estrattore non ha modo di saperlo. La strada è passargli l'informazione, non
indovinarla.
"""
from __future__ import annotations

from verimem.valore_non_nella_fonte import valori_non_nella_fonte

#: La fonte del caso vero: nomina 500 e 540, nessun codice.
FONTE = ("verbale: la coda aveva 500 elementi\n"
         "rettifica: la coda aveva 540 elementi\n")

#: L'id della caduta di CI del 2026-09-12, verbatim. Undici cifre e una
#: lettera: è la forma che veniva spezzata.
_ID_DELLA_CADUTA = "78222643329e"


def _assenti(claim: str) -> list[str]:
    return [v.come_scritto() for v in valori_non_nella_fonte(claim, FONTE)]


def test_l_id_citato_non_e_un_valore_assente_dalla_fonte() -> None:
    """Il caso vero, verbatim dalla caduta di CI.

    Prima della cura questa chiamata rendeva ``['78222643329']`` — il prefisso
    di cifre dell'id — e su quel valore `L4.1` fermava la scrittura.
    """
    assert _assenti(
        f"Nel verbale la coda aveva 500 elementi, come nel fatto "
        f"{_ID_DELLA_CADUTA}.") == [], (
        "l'id citato torna a essere letto come una quantita' assente dalla "
        "fonte: e' il difetto che ha fermato un fatto approvato a 99,9 e che "
        "ha fatto cadere tre PR estranee in un giorno")


def test_anche_gli_id_di_altra_lunghezza_e_forma() -> None:
    """La stessa forma, altre taglie: 8 e 12 hex, cifre e lettere mescolate."""
    for ident in ("b1e233fa3331", "7c1a9e02", "1234abcd", "a1b2c3d4"):
        assert _assenti(f"La coda ha 540 elementi (rettifica del fatto "
                        f"{ident}).") == [], f"l'id {ident} e' letto come valore"


def test_CONTROLLO_un_numero_VERO_assente_resta_visto() -> None:
    """Il controllo positivo, e senza di lui la cura non vale niente.

    Una potatura che tolga troppo rende `L4.1` cieco: il layer esiste per
    prendere **un numero che la fonte non dice**, e quel caso deve continuare a
    mordere. Se questa cella cade, la cura ha comprato la stabilita' al prezzo
    del presidio — cioe' ha spento cio' che proteggeva.
    """
    assert _assenti("La coda ha 540 elementi e occupa 176 MB.") == ["176"], (
        "un valore con unita' che la fonte NON contiene non viene piu' visto: "
        "la potatura degli id ha spento il layer invece di ripulirlo")


def test_CONTROLLO_un_numero_che_la_fonte_CONTIENE_non_e_assente() -> None:
    """L'altra faccia del controllo: ciò che la fonte dice non è mai assente."""
    assert _assenti("La coda ha 540 elementi.") == []


def test_il_residuo_dichiarato_e_solo_di_CIFRE() -> None:
    """Il limite scritto nel docstring, inchiodato.

    Un id di sole cifre **resta** letto come quantita', ed è la scelta: non si
    indovina. Questa cella esiste perché il limite non diventi una sorpresa —
    se un giorno qualcuno lo chiude, qui diventa rosso e trova scritto il
    perché era aperto.
    """
    assert _assenti("La coda ha 540 elementi (rettifica del fatto "
                    "000123456789).") == ["000123456789"], (
        "un id di SOLE CIFRE non viene piu' letto come quantita': se e' una "
        "cura voluta, il limite dichiarato in questo file va riscritto — e va "
        "misurato che `L4.1` non sia diventato cieco sui numeri veri lunghi")
