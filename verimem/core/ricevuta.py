"""La ricevuta: una sola, uguale da qualunque porta entri la scrittura.

PERCHE' ESISTE — misurato il 16/09 sulle tre porte con lo stesso ingresso:

    porta   chiavi rese   nome della lista degli avvisi
    SDK         14        `warnings`
    MCP         24        `anti_confab_warnings`   (e ANCHE `warning`, singolare)
    CLI         11        `warnings`, ma su un'uscita che una macchina non legge

⚠️ LA RIGA DELLA CLI DICEVA «0 — nessuna ricevuta: stampa e basta», ED ERA
   FALSA. Misurato il 18/09 eseguendo `save --json` su uno store isolato: rende
   undici chiavi, e in comune con quelle qui sotto ne ha UNA SOLA, `id`. Il
   banco del 16/09 aveva letto l'uscita per l'umano e ne aveva concluso che una
   ricevuta non ci fosse: lo zero misurava il banco, non il prodotto.
   E l'uscita macchina che c'è non è leggibile da una macchina — due righe di
   log strutturato escono su stdout PRIMA del JSON, e `json.load` muore con
   «Extra data: line 1 column 5». Uno script che oggi legge quell'uscita è già
   rotto, senza aspettare noi.
   ⚠️ I DUE NUMERI SOPRA VENGONO DALLO STESSO BANCO che ha sbagliato il terzo:
   finché non sono rimisurati eseguendo, vanno letti come ipotesi, non come
   misure. Un banco che sbaglia una porta su tre non ha sbagliato una riga: ha
   un difetto, e le altre due righe le ha scritte lo stesso difetto.

Non sono tre formati di comodo: sono tre contratti diversi per la stessa
operazione, e chi legge non puo' sapere quale ha in mano senza sapere da dove e'
entrato. Il 13/09 un banco mio ha letto `nuovo["warnings"]` da una ricevuta che
rende `anti_confab_warnings`: la lista tornava VUOTA e l'ho letta come «nessuno
schermo ha parlato», mentre ne avevano parlato due. La diagnosi sbagliata e'
finita sul canale. Classe: copia invece di superficie unica.

CHE COSA PROMETTE QUESTO MODULO, e cosa NON promette:
  · promette che una ricevuta INCOERENTE non possa esistere — gli invarianti
    stanno nel costruttore e sollevano `ValueError`, non nei commenti;
  · NON promette che le tre porte la usino: quella e' la fetta 1b, una porta
    per volta, e finche' non e' finita questo e' un TERZO schema, non l'unico.

⚠️ UN BUCO PORTA LA PROPRIA RAGIONE. `store=None` da solo direbbe «non lo so»
   e «non c'e'» con lo stesso silenzio. Dove il dato non e' stato misurato si
   scrive il PERCHE' (`NON_MISURATO_REMOTA`): un generico e' peggio di un buco,
   perche' dal buco nessuno deduce.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: L'esito della SCRITTURA. Quattro valori, chiusi.
#: ⚠️ Non confonderlo con `Livello.stato`: fino al 17/09 i due campi portavano
#: lo stesso nome `esito` in due documenti diversi, ed e' la classe di errore
#: che in questo progetto costa di piu' — una parola per due oggetti.
ESITI = ("ammesso", "degradato", "fermato", "rifiutato")

#: Lo stato di UN LIVELLO del cancello, quattro valori chiusi: ha girato e
#: deciso · non ha girato · ha girato senza decidere · ha girato, ha trovato,
#: e una guardia ha ritirato l'avviso (specifica del cancello, 17/09).
STATI_LIVELLO = ("eseguito", "saltato", "osservato", "ritirato")

#: Il valore di `store_decided_by` quando la scrittura e' passata dalla corsia
#: remota, il cui codice non e' stato misurato da qui (limite dichiarato). Un
#: `None` direbbe «l'ha deciso il disco», che qui sarebbe falso: si scrive la
#: ragione, non il silenzio.
NON_MISURATO_REMOTA = "non misurato: corsia remota"

#: Il valore di `store_decided_by` quando l'alias risulta posto ma NON si puo'
#: attribuire a chi ha chiamato.
#: ⚠️ RIPRODOTTO IL 17/09 SU QUESTA MACCHINA: `VERIMEM_DATA_DIR` era vuota
#: prima di `import verimem` e l'import l'ha POSTA (il mirror di compatibilita'
#: riempie gli alias). Quindi «l'alias e' posto» non prova che l'abbia posto un
#: umano, e un processo figlio lanciato dopo l'import li eredita gia' puntati
#: alla cartella di casa. Chi riempie questo campo DEVE prendere l'istantanea
#: degli alias PRIMA di importare `verimem`; se non l'ha fatto, scrive questo
#: valore invece di un nome, perche' un nome qui sarebbe una risposta falsa.
ALIAS_NON_ATTRIBUIBILE = "non attribuibile: alias riempiti dall'import"

#: Il valore di `store_decided_by` quando NESSUN alias era posto: lo store e'
#: quello di casa. Prima qui c'era `None`, e il docstring spiegava che quel
#: `None` «dice che l'ha deciso il disco» — un significato affidato al
#: silenzio, che e' la cosa che questo modulo esiste per togliere. Una parola
#: costa una parola e non si confonde con «non lo so».
DECISO_DAL_DEFAULT = "default: nessun alias d'ambiente"


@dataclass(frozen=True)
class Livello:
    """Che cosa ha fatto UN livello del cancello, e perche'."""

    nome: str
    stato: str
    ragione: str | None = None
    #: ⚠️ IL NUMERO VIAGGIA CON LA SUA SCALA, ANCHE QUI. La prima stesura
    #: teneva `scala` e `modello` solo sulla RICEVUTA: due livelli che
    #: punteggiano su scale diverse — il moat 99.5 su 0-100 e il giudice delle
    #: relazioni 0.87 su 0-1 — finivano sotto un'etichetta sola, e chi legge
    #: 0.87 su «0-100» vede un punteggio bassissimo dove invece e' alto. E'
    #: esattamente il difetto che questo campo esiste per impedire, riprodotto
    #: dentro la cura: il 13/09 un margine di 0,31 l'avevo letto ~60 confrontando
    #: due scale. Trovato dal pari, non da me.
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
        if self.punteggio is not None and (self.scala is None or self.modello is None):
            raise ValueError(
                f"il livello {self.nome!r} porta un punteggio senza scala o senza "
                "modello: due livelli punteggiano su scale diverse, e un numero "
                "senza la sua scala non e' una misura")

    def come_dizionario(self) -> dict[str, Any]:
        return {"nome": self.nome, "stato": self.stato, "ragione": self.ragione,
                "punteggio": self.punteggio, "scala": self.scala,
                "soglia": self.soglia, "modello": self.modello}


@dataclass(frozen=True)
class Ricevuta:
    """Quello che il nucleo rende a OGNI porta, senza aggiunte ne' tagli."""

    esito: str
    #: ⚠️ OBBLIGATORI, E SENZA DEFAULT. Stavano in fondo come `str | None =
    #: None` mentre il docstring di questo modulo vietava quel None: la regola
    #: viveva nel commento e non nel costruttore — che e' esattamente il difetto
    #: per cui gli invarianti stanno qui dentro. Visto in lettura, non da me.
    #: `store` e' un percorso, oppure NON_MISURATO_REMOTA.
    #: `store_decided_by` e' il nome dell'alias, oppure DECISO_DAL_DEFAULT,
    #: oppure ALIAS_NON_ATTRIBUIBILE / NON_MISURATO_REMOTA. Mai vuoto, mai None.
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
    ritirati: tuple[str, ...] = ()
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
        if self.punteggio is not None and (self.scala is None or self.modello is None):
            raise ValueError(
                "punteggio senza scala o senza modello: un numero di cui non si "
                "sa la scala non e' una misura")
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

        #: LE DUE TUPLE PORTANO OGGETTI DIVERSI e nessuno lo controllava:
        #: `livelli` contiene `Livello`, `ritirati` contiene IDENTIFICATORI.
        #: Uno scambio non dava errore alla costruzione e spaccava dopo — un
        #: Livello dentro `ritirati` usciva GREZZO da come_dizionario() e
        #: json.dumps moriva con «Object of type Livello is not JSON
        #: serializable»; una stringa dentro `livelli` moriva in lettura.
        #: Una ricevuta che non si serializza non e' una ricevuta. E
        #: `ritirati` era l'unico campo che nessun banco riempiva: il pari
        #: ha predetto il difetto PRIMA di guardare, cercando il campo non
        #: esercitato. Dove non si e' mai guardato, il difetto sta li'.
        for _liv in self.livelli:
            if not isinstance(_liv, Livello):
                raise ValueError(
                    f"livelli porta {type(_liv).__name__}: qui vanno oggetti "
                    "Livello, non i loro nomi")
        for _rid in self.ritirati:
            if not isinstance(_rid, str) or not _rid:
                raise ValueError(
                    f"ritirati porta {type(_rid).__name__}: qui vanno gli "
                    "identificatori ritirati, stringhe non vuote")

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
            "ritirati": list(self.ritirati),
            #: ⚠️ SEMPRE PRESENTI, ANCHE VUOTI. Il percorso SDK di #63 li
            #: OMETTE quando non c'e' un alias («un campo assente dice: l'ha
            #: deciso il disco»), e finche' si guarda una porta sola funziona.
            #: Ma alla porta degli strumenti quei campi risultano assenti
            #: SEMPRE — misurato: la porta ricostruisce il proprio dizionario e
            #: li perde — quindi sotto quella convenzione «assente» vuol dire
            #: due cose opposte: «l'ha deciso il disco» e «questa porta lo
            #: butta». Presenti sempre, e con un VALORE sempre: dal 18/09
            #: `store_decided_by` non puo' piu' essere None — «l'ha deciso il
            #: disco» si scrive DECISO_DAL_DEFAULT, perche' un significato
            #: affidato al None lo legge come «non lo so» il primo che passa.
            "store": self.store,
            "store_decided_by": self.store_decided_by,
            "store_env_ignored": list(self.store_env_ignored),
        }


#: Le chiavi che ogni porta DEVE rendere: ne' una di piu', ne' una di meno.
#: Serve alla proprieta' della fetta 1 («stessa ricevuta sulle tre porte») per
#: avere un elenco da confrontare che non sia scritto dentro il test.
#:
#: ⚠️ ESPLICITE, NON PRESE DA UN ESEMPLARE. La prima stesura faceva
#: `tuple(Ricevuta(esito="ammesso").come_dizionario().keys())`: costruiva
#: un'istanza AL MOMENTO DELL'IMPORT — un invariante futuro che rendesse
#: obbligatorio un campo avrebbe fatto esplodere l'import dell'intero nucleo, e
#: con esso ogni porta che lo importa. E un elenco preso da UN esemplare
#: descrive quell'esemplare, non il tipo.
#: Che questo elenco e `come_dizionario()` non divergano e' compito di un test,
#: non di un commento: la proprieta' della fetta 1 confronta le chiavi.
CHIAVI = (
    "esito", "id", "punteggio", "soglia", "margine", "scala", "modello",
    "giudice", "livelli", "fermato_da", "ritirati",
    "store", "store_decided_by", "store_env_ignored",
)
