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


def _rientrato(testo: str) -> str:
    """Il modello come blocco di codice RIENTRATO di quattro spazi."""
    righe = "\n".join("    " + r for r in testo.splitlines())
    return f"Ecco il modello:\n\n{righe}\n\nCopialo pure.\n"


def _citato(testo: str) -> str:
    """Il modello come lo rende il pulsante «Quote reply» di GitHub."""
    righe = "\n".join("> " + r for r in testo.splitlines())
    return f"{righe}\n\nConcordo con quanto sopra.\n"


def _in_un_commento_html(testo: str) -> str:
    """Il modello dentro un commento HTML: invisibile a chi legge la pagina."""
    return f"Ci penso io.\n\n<!--\n{testo}\n-->\n"


#: ⚠️ LE SEI FORME, e NON le ho trovate io. Le ha misurate @Marie con la mia
#: stessa funzione dopo che l'avevo dichiarata curata, e TRE passavano ancora:
#: il blocco rientrato, la citazione con «>» e il commento HTML. Una cura
#: provata solo dai casi di chi l'ha scritta copre i casi che aveva in mente.
LE_SEI_FORME = [
    ("recinto con tre backtick", lambda t: _dentro_un_recinto(t)),
    ("recinto con un linguaggio", lambda t: _dentro_un_recinto(t, "```", "markdown")),
    ("recinto con le tilde", lambda t: _dentro_un_recinto(t, "~~~")),
    ("recinto con quattro backtick", lambda t: _dentro_un_recinto(t, "````")),
    ("blocco RIENTRATO di quattro spazi", _rientrato),
    ("citazione con «>» (Quote reply)", _citato),
    ("commento HTML (invisibile a chi legge)", _in_un_commento_html),
]


def test_LE_SEI_FORME_di_Marie_cadono_tutte():
    """Nessuna delle forme in cui un modello si MOSTRA vale come dichiarazione.

    ⚠️ La più insidiosa non è il recinto: è la **citazione**. Il pulsante «Quote
    reply» di GitHub mette un «>» davanti a ogni riga del commento citato, e chi
    risponde a un commento che porta la Definition of Done se la ritrova nel
    proprio — avrebbe dichiarato al posto dell'autore **senza volerlo e senza
    accorgersene**. Il difetto non ha bisogno di nessuno che incolli: basta il
    pulsante.

    ⚠️ La più grave è il commento HTML: nessun umano lo vede sulla pagina,
    quindi un controllo che lo legge giudica su un testo che l'autore non ha
    davanti, e chi guarda non capisce perché.
    """
    for nome, forma in LE_SEI_FORME:
        problemi = mp.controlla_corpo(CORPO, commenti=[forma(DICHIARAZIONE_VERA)])
        assert problemi, (
            f"{nome}: il modello è passato come se qualcuno avesse dichiarato. "
            "È la forma che questo presidio esiste per fermare"
        )


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


def test_il_nulla_cade_ANCORA():
    """⚠️ IL NEGATIVO, e sta qui perché me l'ha insegnato il presidio di un pari.

    Corrado aveva curato lo stesso difetto in parallelo, e il suo RED aveva tre
    gambe dove il mio ne aveva due: *un esempio recintato passa, una
    dichiarazione vera passa, **il nulla cade***. La terza nel mio file non
    c'era — il comportamento era giusto (lo copre l'autotest dello script) ma
    **il presidio esplicito no**, e un presidio che vive in un solo posto
    protegge solo quel posto.

    Senza questa gamba, una cura futura che togliesse i recinti con troppa
    larghezza — fino a svuotare il commento — passerebbe le prime due e
    resterebbe verde: nessun commento e un commento svuotato si somigliano.
    """
    for nome, commenti in (("nessun commento", []),
                           ("un commento che non dichiara niente", ["ciao, come va"])):
        problemi = mp.controlla_corpo(CORPO, commenti=commenti)
        assert problemi, (
            f"{nome}: il cancello ha lasciato passare una richiesta in cui "
            "NESSUNO ha dichiarato che cosa considera finito"
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
