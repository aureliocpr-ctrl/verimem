"""Dal dizionario del cancello alla `Ricevuta` del nucleo.

⚠️ QUESTO MODULO E' UN PONTE, E I PONTI SI TOLGONO. Oggi il cancello
(`client.py`) costruisce un dizionario a mano e ogni porta lo ritocca a modo
suo; il nucleo ha una `Ricevuta` sola. Finche' le due cose convivono serve
qualcuno che traduca, e quel qualcuno deve stare in UN POSTO SOLO — altrimenti
la traduzione diventa la quarta copia dello stesso schema, che e' il difetto da
cui parte tutta la fetta.
Quando il motore costruira' la `Ricevuta` direttamente (1b.4), questo file
sparisce: se e' ancora qui dopo, vuol dire che il ponte e' diventato la strada.

CHE COSA SA, e cosa NON sa:
  · sa leggere le chiavi che `client.py` mette nel suo dizionario;
  · NON sa dove finira' il risultato — non stampa, non decide, non conosce
    nessuna porta. Una funzione sola, senza effetti.
"""
from __future__ import annotations

from typing import Any

from .core import (
    ALIAS_NON_ATTRIBUIBILE,
    DECISO_DAL_DEFAULT,
    STATI_LIVELLO,
    Livello,
    Ricevuta,
)

#: La scala del punteggio del moat: 0-100, e la soglia sta sulla stessa.
#: ⚠️ Scritta qui e non dedotta: il 13/09 un margine di 0,31 e' stato letto ~60
#: confrontando un punteggio 0-100 con un taglio di un'altra scala. Un numero
#: che viaggia senza la sua scala non e' una misura, e la scala non si indovina
#: dal valore.
SCALA_MOAT = "moat-0-100"

#: Quando il cancello non dice chi ha giudicato.
GIUDICE_NON_DICHIARATO = "non dichiarato dal cancello"

#: Quando il cancello ferma una scrittura e non dice QUALE schermo.
#: ⚠️ E' una COSTANTE e non una frase ripetuta nei banchi: la prima cella la
#: cercava come sottostringa («non dichiarato») e cadeva appena il testo
#: diventava «non ha dichiarato» — un banco che misura la FORMA delle parole
#: invece dell'oggetto, che e' la stessa classe di difetto che questa fetta
#: cura. Chi vuole verificarlo confronta con questo nome.
BLOCCANTE_NON_DICHIARATO = ("il cancello ha fermato la scrittura senza "
                            "dichiarare quale schermo")
RIFIUTO_NON_DICHIARATO = ("il cancello ha rifiutato la scrittura senza "
                          "dichiarare la ragione")


#: LA TABELLA, ESPLICITA. Ogni valore che il cancello emette ha una riga: chi
#: legge sa che cosa diventa, e un valore NUOVO non scivola dentro un esito per
#: esclusione.
#: ⚠️ LA PRIMA STESURA FACEVA `if not stored: rifiutato`, e una scrittura VUOTA
#: sarebbe diventata «rifiutata» — un esito FALSO, cioe' esattamente la
#: giuntura che la ricevuta esiste per togliere: il verdetto calcolato in un
#: posto e riscritto in un altro. Rilievo in lettura, 19/09.
#: I quattro valori sono quelli che `client.py` passa davvero (misurati:
#: `rejected`, `routed_telemetry`, `quarantined`, `admitted`), piu' lo stato
#: `empty` della scrittura senza contenuto.
DAL_CANCELLO_ALL_ESITO = {
    "admitted": ("ammesso", None),
    #: Il ripiego DICE che il nome manca, non ripete lo stato: «fermato da
    #: quarantined» non aggiunge niente a «fermato», e chi legge crederebbe
    #: che quello SIA il nome dello schermo.
    "quarantined": ("fermato", BLOCCANTE_NON_DICHIARATO),
    "rejected": ("rifiutato", RIFIUTO_NON_DICHIARATO),
    #: NON e' un rifiuto: la riga e' stata mandata alla telemetria invece che al
    #: corpus. Finche' `ESITI` non ha una parola per questo, si usa la piu'
    #: vicina e si DICE che cos'e' successo nel campo che porta il nome.
    "routed_telemetry": ("rifiutato", "routed_telemetry: instradata alla "
                                      "telemetria, non al corpus"),
    "empty": ("rifiutato", "empty: nessun contenuto da scrivere"),
}

#: Il marcatore dell'ammissione GRADUATA: ammessa, ma con una riserva scritta.
#: Non e' un'ammissione piena e non e' un blocco — e' il terzo valore per cui
#: `degradato` esiste.
SUFFISSO_GRADUATO = "-graded"


def _e_graduata(grezzo: dict[str, Any]) -> bool:
    for avviso in grezzo.get("warnings") or ():
        if isinstance(avviso, dict) and str(
                avviso.get("layer") or "").endswith(SUFFISSO_GRADUATO):
            return True
    return False


def _esito_e_bloccante(grezzo: dict[str, Any]) -> tuple[str, str | None]:
    """L'esito della scrittura e, se c'e', il NOME di chi l'ha fermata.

    ⚠️ IL CAMPO ESISTE MA E' CONDIZIONALE. `client.py` mette `quarantined_by`
    solo quando ha un valore, quindi la sua ASSENZA non distingue «nessuno ha
    fermato» da «questa porta non lo dichiara». Qui non si legge mai da sola.
    """
    giudizio = grezzo.get("adjudication") or {}
    chiave = giudizio.get("disposition") or grezzo.get("status")
    fermato_da = grezzo.get("quarantined_by") or None

    if chiave in DAL_CANCELLO_ALL_ESITO:
        esito, ragione = DAL_CANCELLO_ALL_ESITO[chiave]
        if esito == "ammesso" and _e_graduata(grezzo):
            return "degradato", None
        if esito == "ammesso":
            return "ammesso", None
        return esito, fermato_da or ragione

    #: UN VALORE CHE LA TABELLA NON PREVEDE NON DIVENTA MUTO. Lo stato di una
    #: scrittura ordinaria (`model_claim`, `promoted`, `candidate`...) non e'
    #: una disposizione: se e' entrata, e' ammessa.
    if grezzo.get("stored", False):
        return ("degradato", None) if _e_graduata(grezzo) else ("ammesso", None)
    #: Non entrata e non riconosciuta: si scrive IL VALORE VERO, perche' chi
    #: legge possa aggiungere la riga che manca invece di indovinare.
    return "rifiutato", fermato_da or f"esito non previsto dalla tabella: {chiave!r}"


def _livelli_dagli_avvisi(grezzo: dict[str, Any]) -> tuple[Livello, ...]:
    """Gli schermi che hanno parlato, quando l'avviso porta il suo livello.

    Un avviso senza `layer` non diventa un livello anonimo: verrebbe fuori un
    `Livello(nome="")`, che il nucleo rifiuta, e avrebbe ragione anche li'.
    """
    livelli = []
    for avviso in grezzo.get("warnings") or ():
        if not isinstance(avviso, dict):
            continue
        nome = str(avviso.get("layer") or "").strip()
        if not nome:
            continue
        stato = str(avviso.get("stato") or "eseguito")
        if stato not in STATI_LIVELLO:
            stato = "eseguito"
        ragione = avviso.get("reason") or avviso.get("message") or None
        livelli.append(Livello(
            nome=nome, stato=stato,
            ragione=str(ragione) if ragione else (
                None if stato == "eseguito" else "ragione non dichiarata"),
        ))
    return tuple(livelli)


def ricevuta_dal_cancello(grezzo: dict[str, Any]) -> Ricevuta:
    """Traduce il dizionario di `client.py` nella `Ricevuta` del nucleo.

    I campi che il cancello non porta restano VUOTI con la loro ragione, mai
    riempiti a indovinare: una ricevuta che inventa e' peggio di una che tace.
    """
    esito, fermato_da = _esito_e_bloccante(grezzo)
    giudizio = grezzo.get("adjudication") or {}
    giudice_grezzo = giudizio.get("judge") or {}

    punteggio = grezzo.get("grounding_score")
    if punteggio is None:
        punteggio = giudizio.get("score")
    soglia = giudizio.get("threshold")
    #: Un punteggio senza la sua soglia non ha un margine, e il nucleo lo
    #: rifiuta: meglio non portarlo che portarlo zoppo.
    if punteggio is not None and soglia is None:
        punteggio = None

    modello = giudice_grezzo.get("model") or grezzo.get("judged_by")
    giudice = (giudice_grezzo.get("backend") or grezzo.get("judged_by")
               or GIUDICE_NON_DICHIARATO)

    return Ricevuta(
        esito=esito,
        #: ⚠️ MAI VUOTI. `client.py` li mette sempre (la dichiarazione della
        #: provenienza dello store), ma qui non si dà per scontato quello che
        #: scrive un altro modulo: se un giorno uno dei due sparisse, chi legge
        #: deve trovare una ragione e non una stringa vuota.
        store=str(grezzo.get("store") or ALIAS_NON_ATTRIBUIBILE),
        store_decided_by=str(grezzo.get("store_decided_by")
                             or DECISO_DAL_DEFAULT),
        store_env_ignored=tuple(grezzo.get("store_env_ignored") or ()),
        id=grezzo.get("id"),
        punteggio=float(punteggio) if punteggio is not None else None,
        soglia=float(soglia) if punteggio is not None else None,
        scala=SCALA_MOAT if punteggio is not None else None,
        modello=str(modello) if punteggio is not None and modello else (
            GIUDICE_NON_DICHIARATO if punteggio is not None else None),
        giudice=str(giudice),
        livelli=_livelli_dagli_avvisi(grezzo),
        fermato_da=fermato_da,
        #: I fatti ritirati da questa scrittura il cancello non li porta ancora
        #: con la loro ragione: finche' non li porta, la lista resta vuota
        #: invece di contenere identificatori senza il perche'.
        ritirati=(),
    )
