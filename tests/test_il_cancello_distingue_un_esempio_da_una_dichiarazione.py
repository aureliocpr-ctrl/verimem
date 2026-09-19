"""Il cancello leggeva un ESEMPIO come una dichiarazione.

🔴 MISURATO IL 19/09/2026, e il modo in cui è successo è la parte che conta.

Ieri alle 20:25 @ws8 ha scritto sul canale che NON avrebbe riempito lui le due
righe della Definition of Done su sette richieste altrui, perché «riempirle
vorrebbe dire far passare sette richieste senza che nessuno abbia dichiarato
niente». Poi, **nello stesso commento**, ha incollato il MODELLO da copiare —
dentro un blocco recintato, per aiutare chi doveva scriverlo.

Il cancello ha letto il modello come una dichiarazione. Sette richieste
(#26 #27 #34 #35 #36 #45 #59) sono diventate VERDI con «commenti dopo il mio: 0»
su tutte e sette: nessuno dei loro autori aveva scritto una riga.

    [17:41:06]  DoD:False Registro:False Decisione:False   <- il commento vero
    [18:21:32]  DoD:True  Registro:True  Decisione:True    <- l'ESEMPIO
    verdetto del cancello: VERDE

⇒ Il cancello cercava una STRINGA, non una DICHIARAZIONE, e la trovava anche
dentro ``` ```. È la classe del marcatore preso alla rovescia: non «un marcatore
non marca chi non lo conosce», ma **marca chi non voleva marcare**.

⚠️⚠️ E IL DIFETTO SI PROPAGA ATTRAVERSO L'AIUTO: chiunque incolli il modello per
spiegarlo — in una guida, in una risposta, in questo stesso file — rende verde
la richiesta dove lo incolla. Più uno cerca di essere utile, più lo allarga.

Il presidio ha DUE gambe, e la seconda è il controllo positivo: una cura che
bocciasse anche la dichiarazione vera costerebbe più del difetto.
"""
from __future__ import annotations

import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RADICE / "scripts"))

import messaggio_pulito as mp  # noqa: E402

CORPO = "Una riga sola di prosa.\n"

#: ⚠️ COSTRUITO DAI PEZZI, non scritto a mano: se lo scrivessi come stringa
#: letterale, questo file diventerebbe esso stesso un esempio che il cancello
#: legge — ed è esattamente il difetto in prova. Vedi `DOD_IN_COMMENTO` nello
#: script: la dichiarazione vera si prende da lì, non si ricopia.
DICHIARAZIONE_VERA = mp.DOD_IN_COMMENTO[0]


def _dentro_un_recinto(testo: str, marcatore: str = "```", lingua: str = "") -> str:
    """Lo stesso testo, ma incollato dentro un blocco recintato."""
    return (f"Ciao, ti mancano due righe. Il modello e' questo:\n\n"
            f"{marcatore}{lingua}\n{testo}\n{marcatore}\n\nSpero sia chiaro.\n")


def test_un_esempio_dentro_un_recinto_NON_vale_come_dichiarazione():
    """La gamba che era rossa: il modello incollato non deve far passare nulla."""
    problemi = mp.controlla_corpo(CORPO, commenti=[_dentro_un_recinto(DICHIARAZIONE_VERA)])
    assert problemi, (
        "il cancello ha accettato un ESEMPIO dentro ``` ``` come se fosse una "
        "dichiarazione: è così che sette richieste sono diventate verdi il 19/09 "
        "senza che nessun autore avesse scritto una riga"
    )


def test_anche_col_marcatore_a_tilde_e_con_un_linguaggio():
    """Le due forme che un recinto può avere, perché la cura non copra una sola."""
    for marcatore, lingua in (("```", "markdown"), ("~~~", ""), ("````", "")):
        problemi = mp.controlla_corpo(
            CORPO, commenti=[_dentro_un_recinto(DICHIARAZIONE_VERA, marcatore, lingua)])
        assert problemi, (
            f"recinto {marcatore!r} con linguaggio {lingua!r}: l'esempio è passato. "
            "Una cura che copre solo ``` senza linguaggio lascia aperta la porta "
            "accanto, e chi incolla non sa quale delle due sta usando"
        )


def test_LA_DICHIARAZIONE_VERA_PASSA_ANCORA():
    """⚠️ IL CONTROLLO POSITIVO, e qui vale doppio.

    Una cura che togliesse i recinti con troppa larghezza boccerebbe anche chi
    dichiara sul serio — e quel rosso sarebbe peggio del difetto, perché
    colpisce chi ha fatto la cosa giusta. Questa gamba deve restare verde sia
    prima sia dopo la cura: se diventa rossa, la cura è da rifare.
    """
    problemi = mp.controlla_corpo(CORPO, commenti=[DICHIARAZIONE_VERA])
    assert not problemi, (
        "la cura ha bocciato una dichiarazione VERA, fuori da qualunque recinto: "
        f"{problemi}"
    )


def test_la_dichiarazione_vera_vale_anche_se_NEL_COMMENTO_c_e_pure_un_esempio():
    """Il caso misto, che è quello di chi dichiara E spiega nello stesso commento.

    Chi scrive la sua DoD e poi incolla il modello per il prossimo non deve
    essere bocciato: fuori dal recinto la dichiarazione c'è davvero.
    """
    misto = DICHIARAZIONE_VERA + "\n\n" + _dentro_un_recinto("### Definition of Done\n- [ ] …")
    problemi = mp.controlla_corpo(CORPO, commenti=[misto])
    assert not problemi, (
        "bocciato chi ha dichiarato sul serio e in più ha incollato il modello "
        f"per aiutare il prossimo: {problemi}"
    )
