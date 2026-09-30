"""La ricevuta: una sola, uguale da qualunque porta entri la scrittura.

PERCHE' ESISTE — misurato il 16/09 sulle tre porte con lo stesso ingresso:

    porta   chiavi rese   nome della lista degli avvisi
    SDK         14        `warnings`
    MCP         24        `anti_confab_warnings`   (e ANCHE `warning`, singolare)
    CLI         11        `warnings`, ma su un'uscita che una macchina non legge

⚠️ LA RIGA DELLA CLI DICEVA «0» ED ERA FALSA: il banco del 16/09 leggeva
   l'uscita per l'umano. Misurato il 18/09 eseguendo `save --json`: undici
   chiavi, UNA sola in comune con quelle qui sotto (`id`), e su uno stdout che
   una macchina non legge — due righe di giornale cadono prima del JSON e
   `json.load` muore con «Extra data: line 1 column 5». I DUE NUMERI SOPRA
   vengono dallo stesso banco che ha sbagliato il terzo: ipotesi, finche'
   qualcuno non li riesegue.

Non sono tre formati di comodo: sono tre contratti per la stessa operazione, e
chi legge non sa quale ha in mano senza sapere da dove e' entrato. Il 13/09 un
banco mio ha letto `nuovo["warnings"]` da una porta che rende
`anti_confab_warnings`: lista VUOTA, letta come «nessuno schermo ha parlato»
mentre ne avevano parlato due, e la diagnosi sbagliata e' finita sul canale.
Classe: copia invece di superficie unica.

PROMETTE che una ricevuta INCOERENTE non possa esistere: gli invarianti stanno
nel costruttore e sollevano `ValueError`, non nei commenti. NON promette che le
tre porte la usino — quella e' la 1b, una porta per volta, e finche' non e'
finita questo e' un TERZO schema, non l'unico.

⚠️ UN BUCO PORTA LA PROPRIA RAGIONE: `store=None` direbbe «non lo so» e «non
   c'e'» con lo stesso silenzio. Dove non si e' misurato si scrive il PERCHE'.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: L'esito della SCRITTURA. Quattro valori, chiusi. ⚠️ Non e' `Livello.stato`:
#: fino al 17/09 i due campi si chiamavano entrambi `esito` in due documenti,
#: ed e' l'errore che qui costa di piu' — una parola per due oggetti.
ESITI = ("ammesso", "degradato", "fermato", "rifiutato")

#: Lo stato di UN LIVELLO del cancello: ha girato e deciso · non ha girato · ha
#: girato senza decidere · una guardia ne ha ritirato l'avviso (T93).
STATI_LIVELLO = ("eseguito", "saltato", "osservato", "ritirato")

#: Corsia remota: codice mai misurato da qui (limite dichiarato). Un `None`
#: direbbe «l'ha deciso il disco», che sarebbe falso: si scrive la ragione.
NON_MISURATO_REMOTA = "non misurato: corsia remota"

#: `store_decided_by` quando l'alias risulta posto ma NON si puo' attribuire a
#: chi ha chiamato. ⚠️ RIPRODOTTO il 17/09: `VERIMEM_DATA_DIR` era vuota prima
#: di `import verimem` e l'import l'ha POSTA. Quindi «l'alias e' posto» non
#: prova che l'abbia posto un umano. Chi riempie il campo prende l'istantanea
#: PRIMA di importare; se non l'ha fatto scrive questo, non un nome.
ALIAS_NON_ATTRIBUIBILE = "non attribuibile: alias riempiti dall'import"

#: `store_decided_by` quando NESSUN alias era posto: lo store e' quello di
#: casa. Prima era `None`, cioe' un significato affidato al silenzio: la cosa
#: che questo modulo esiste per togliere. Una parola non si confonde con «non
#: lo so».
DECISO_DAL_DEFAULT = "default: nessun alias d'ambiente"


def _il_punteggio_porta_la_sua_scala(dove: str, punteggio, scala, modello) -> None:
    """Un numero di cui non si sa la scala non e' una misura.

    ⚠️ ERA SCRITTA DUE VOLTE, in `Livello` e in `Ricevuta`, con due messaggi
    diversi. Due copie divergono: basta che una si allenti e la ricevuta
    ammette dal livello cio' che vieta in cima. Classe ①, dentro il modulo
    che esiste per toglierla.
    """
    if punteggio is not None and (scala is None or modello is None):
        raise ValueError(
            f"{dove}: punteggio senza scala o senza modello — due livelli "
            "punteggiano su scale diverse, e un numero senza la sua scala "
            "non e' una misura")


@dataclass(frozen=True)
class Livello:
    """Che cosa ha fatto UN livello del cancello, e perche'."""

    nome: str
    stato: str
    ragione: str | None = None
    #: ⚠️ LA SCALA STA ANCHE QUI. La prima stesura la teneva solo sulla
    #: RICEVUTA: il moat 99.5 su 0-100 e il giudice delle relazioni 0.87 su 0-1
    #: finivano sotto un'etichetta sola, e chi legge 0.87 su «0-100» vede un
    #: numero bassissimo dov'e' alto. Il difetto che il campo esiste per
    #: impedire, riprodotto dentro la cura. Trovato dal pari, non da me.
    punteggio: float | None = None
    scala: str | None = None
    soglia: float | None = None
    modello: str | None = None

    def __post_init__(self) -> None:
        if not self.nome:
            raise ValueError("Livello senza nome: un livello anonimo non e' leggibile")
        if self.stato not in STATI_LIVELLO:
            raise ValueError(
                f"stato {self.stato!r} non ammesso: uno di {STATI_LIVELLO}")
        #: Un livello che NON ha deciso deve dire perche': e' la meta' della
        #: ricevuta che oggi non esiste da nessuna porta.
        if self.stato != "eseguito" and not self.ragione:
            raise ValueError(
                f"il livello {self.nome!r} e' {self.stato!r} senza ragione: "
                "uno stato diverso da 'eseguito' senza ragione dice meno di un "
                "campo assente, perche' sembra una risposta")
        _il_punteggio_porta_la_sua_scala(
            f"il livello {self.nome!r}", self.punteggio, self.scala, self.modello)

    def come_dizionario(self) -> dict[str, Any]:
        return {"nome": self.nome, "stato": self.stato, "ragione": self.ragione,
                "punteggio": self.punteggio, "scala": self.scala,
                "soglia": self.soglia, "modello": self.modello}


@dataclass(frozen=True)
class Ritiro:
    """Un fatto che QUESTA scrittura ha ritirato, con la sua ragione.

    ⚠️ NON e' un `Livello`, e per un giro lo e' stato: «ritirato» resta uno
    STATO di `Livello` perche' un avviso ritirato da una guardia E' un livello,
    un fatto ritirato dalla supersessione no. Una classe per due oggetti e' la
    forma che qui costa di piu', e stava entrando nel modulo che la combatte.
    """

    id: str
    ragione: str

    def __post_init__(self) -> None:
        if not self.id or not self.ragione:
            raise ValueError(
                "un ritiro porta l'identificatore E la ragione: senza ragione "
                "e' un fatto sparito, non un fatto ritirato")

    def come_dizionario(self) -> dict[str, Any]:
        return {"id": self.id, "ragione": self.ragione}


@dataclass(frozen=True)
class Ricevuta:
    """Quello che il nucleo rende a OGNI porta, senza aggiunte ne' tagli."""

    esito: str
    #: ⚠️ OBBLIGATORI, SENZA DEFAULT. Stavano come `str | None = None` mentre
    #: il docstring vietava quel None: la regola viveva nel commento e non nel
    #: costruttore. Visto in lettura, non da me. `store` e' un percorso oppure
    #: NON_MISURATO_REMOTA; `store_decided_by` e' l'alias, DECISO_DAL_DEFAULT o
    #: la ragione. Mai vuoto, mai None.
    store: str
    store_decided_by: str
    id: str | None = None
    punteggio: float | None = None
    soglia: float | None = None
    scala: str | None = None
    modello: str | None = None
    giudice: str | None = None
    livelli: tuple[Livello, ...] = ()
    fermato_da: str | None = None
    #: ⚠️ OGGETTI, NON NOMI: un identificatore da solo non dice PERCHE'.
    ritirati: tuple[Ritiro, ...] = ()
    store_env_ignored: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.esito not in ESITI:
            raise ValueError(f"esito {self.esito!r} non ammesso: uno di {ESITI}")

        #: IL CONTROLLO NEGATIVO, PER COSTRUZIONE. Una ricevuta «ammessa» con
        #: un `fermato_da` pieno e' una contraddizione: qui non si corregge, si
        #: RIFIUTA. Chi la costruisse cosi' ha un difetto a monte, e deve
        #: vederlo alla costruzione e non tre porte piu' in la'.
        if self.esito == "ammesso" and self.fermato_da:
            raise ValueError(
                "ricevuta incoerente: esito 'ammesso' con "
                f"fermato_da={self.fermato_da!r}")
        if self.esito in ("fermato", "rifiutato") and not self.fermato_da:
            raise ValueError(
                f"ricevuta incoerente: esito {self.esito!r} senza fermato_da. "
                "Chi ferma ha un nome: un generico qui e' peggio di un buco")

        #: UN PUNTEGGIO SENZA LA SUA SCALA INGANNA, e questo progetto l'ha
        #: pagato: il 13/09 ho calcolato un margine di ~60 confrontando un
        #: punteggio su scala 0-100 con un taglio di un'altra scala. Il margine
        #: vero era 0,31. Da qui in poi i tre numeri viaggiano insieme.
        _il_punteggio_porta_la_sua_scala(
            "la ricevuta", self.punteggio, self.scala, self.modello)
        if self.punteggio is not None and self.soglia is None:
            raise ValueError("punteggio senza soglia: il margine non e' calcolabile")

        #: DOVE SI SCRIVE, SI SCRIVE SEMPRE. Una stringa vuota qui sarebbe il
        #: buco muto che NON_MISURATO_REMOTA esiste per impedire: chi legge non
        #: saprebbe se il dato manca o se nessuno l'ha guardato.
        if not self.store:
            raise ValueError(
                "store vuoto: una scrittura ha sempre un posto dove va, o dove "
                "non e' andata. Se non lo sai, scrivi il perche' "
                "(NON_MISURATO_REMOTA), non il silenzio")
        if not self.store_decided_by:
            raise ValueError(
                "store_decided_by vuoto: chi ha scelto lo store ha un nome — "
                "un alias, DECISO_DAL_DEFAULT, oppure la ragione per cui non "
                "e' attribuibile")

        #: GLI ELEMENTI, non solo le tuple: uno scambio non dava errore alla
        #: costruzione e spaccava dopo — un nome dentro `livelli` moriva in
        #: lettura, e prima che `ritirati` portasse oggetti json.dumps moriva
        #: con «Object of type Livello is not JSON serializable». Una ricevuta
        #: che non si serializza non e' una ricevuta. `ritirati` era l'unico
        #: campo che nessun banco riempiva: il pari ha predetto il difetto
        #: PRIMA di guardare. Dove non si e' mai guardato, il difetto sta li'.
        for _liv in self.livelli:
            if not isinstance(_liv, Livello):
                raise ValueError(
                    f"livelli porta {type(_liv).__name__}: qui vanno oggetti "
                    "Livello, non i loro nomi")
        for _rid in self.ritirati:
            if not isinstance(_rid, Ritiro):
                raise ValueError(
                    f"ritirati porta {type(_rid).__name__}: qui vanno oggetti "
                    "Ritiro, che portano l'identificatore E la ragione")

    @property
    def margine(self) -> float | None:
        """`punteggio - soglia`, calcolato QUI e mai dal chiamante."""
        if self.punteggio is None or self.soglia is None:
            return None
        return float(self.punteggio) - float(self.soglia)

    def come_dizionario(self) -> dict[str, Any]:
        """L'unica serializzazione. Le porte rendono QUESTO, senza ritocchi."""
        return {
            "esito": self.esito,
            "id": self.id,
            "punteggio": self.punteggio,
            "soglia": self.soglia,
            "margine": self.margine,
            "scala": self.scala,
            "modello": self.modello,
            "giudice": self.giudice,
            "livelli": [liv.come_dizionario() for liv in self.livelli],
            "fermato_da": self.fermato_da,
            "ritirati": [_r.come_dizionario() for _r in self.ritirati],
            #: ⚠️ SEMPRE PRESENTI, ANCHE VUOTI. Il percorso SDK di #63 li
            #: OMETTE quando non c'e' un alias, e finche' si guarda una porta
            #: sola funziona. Ma alla porta degli strumenti risultano assenti
            #: SEMPRE (misurato: quella porta ricostruisce il dizionario e li
            #: perde), quindi «assente» vuol dire due cose opposte: «l'ha
            #: deciso il disco» e «questa porta lo
            #: butta». Presenti sempre e con un VALORE sempre: «l'ha deciso il
            #: disco» si scrive DECISO_DAL_DEFAULT, perche' un significato
            #: affidato al None lo legge come «non lo so» il primo che passa.
            "store": self.store,
            "store_decided_by": self.store_decided_by,
            "store_env_ignored": list(self.store_env_ignored),
        }


#: Le chiavi che ogni porta DEVE rendere: ne' una di piu', ne' una di meno, in
#: un elenco che non viva dentro il test che le confronta.
#: ⚠️ ESPLICITE, NON DA UN ESEMPLARE: la prima stesura le prendeva da
#: `Ricevuta(esito="ammesso")` costruita ALL'IMPORT. La profezia si e' avverata
#: lo STESSO GIORNO — `store` e `store_decided_by` sono diventati obbligatori, e
#: quella riga avrebbe fatto esplodere l'import del nucleo e di ogni porta.
#: Che elenco e `come_dizionario()` non divergano lo prova un test, non questo.
CHIAVI = (
    "esito", "id", "punteggio", "soglia", "margine", "scala", "modello",
    "giudice", "livelli", "fermato_da", "ritirati",
    "store", "store_decided_by", "store_env_ignored",
)
