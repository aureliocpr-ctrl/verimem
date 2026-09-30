"""Lo schema del nucleo: le sei tabelle, e in che stato sta uno store.

⚠️ NON ANCORA CABLATO. Questo modulo esiste, è provato da un banco suo e non è
chiamato da nessuno, e il pacchetto lo sa: il criterio dei moduli senza porta
l'ha contato (C2 31, D 45) e i suoi tetti sono saliti di uno per lasciarlo
passare. **Quella salita è un debito con un nome — T125 — e scade quando il
cablaggio arriva**: il cambio si ferma in `migrations.ensure_schema_version`,
l'apertura si dichiara in `SemanticMemory.__init__` (D-0009). Se i tetti sono
ancora 31 e 45 dopo quel cablaggio, non è più un cricchetto a scendere.

Le sei tabelle del nucleo (D-0003): ``facts``, ``facts_undo_log``,
``audit_mutations``, ``trust_ledger``, ``trust_ledger_totals``,
``_schema_version``.

📌 PERCHÉ QUI NON C'È IL `CREATE TABLE` DI `facts`, ed è una scelta, non una
dimenticanza. Quella definizione oggi vive in ``semantic.py`` ed è cresciuta per
`ALTER TABLE` lungo diciassette versioni: ventiquattro colonne, ognuna con il
commento di quando e perché è nata. Ricopiarla qui creerebbe **due** definizioni
della stessa tabella, che divergerebbero alla prima colonna aggiunta — cioè
esattamente il difetto che uno schema unico deve togliere — la classe «copia
invece di superficie unica» del registro degli errori. Quando la fetta 3 parte, quelle definizioni
si **spostano** qui e da `semantic.py` spariscono. Stasera questo modulo porta
ciò che si può avere senza spostarle: i nomi del nucleo e lo STATO di uno store.

Lo stato è la parte che conta, e sono TRE, non due:

    non marcato   `PRAGMA user_version` = 0. Non vuol dire «versione zero»:
                  vuol dire che nessuno l'ha mai marcato. Al 18/09 sono tutti
                  e 41 gli store sotto ``~/.engram``.
    versione n    marcato, e n è un numero che il codice può confrontare.
    ignoto        il file c'è ma non si lascia leggere (non è un database, è
                  cifrato, è troncato). Distinto dagli altri due: «non lo so»
                  non è «non marcato» e non è una versione.

Confondere i primi due è il difetto che questo modulo esiste per evitare: un
confronto numerico che tratti 0 come una versione dichiarerebbe «più vecchio del
codice» uno store che non ha mai detto niente, e lo migrerebbe.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

#: Le sei tabelle del nucleo (D-0003). I nomi, non le definizioni: vedi il
#: docstring del modulo per il perché.
TABELLE_DEL_NUCLEO: tuple[str, ...] = (
    "facts",
    "facts_undo_log",
    "audit_mutations",
    "trust_ledger",
    "trust_ledger_totals",
    "_schema_version",
)

#: La versione che questo codice sa gestire. Sale con ogni migrazione numerata.
#:
#: ⚠️ VALE 17, NON 1, ed è una decisione: il sottosistema `semantic` è già alla
#: 17 dentro `_schema_version`, e far ripartire il nucleo da 1 creerebbe DUE
#: numerazioni per la stessa cosa — uno store direbbe «17» a una tabella e «1» a
#: un pragma, e nessuno dei due saprebbe che parlano dello stesso schema. È il
#: difetto che questo modulo cura, alla sua stessa radice. Il nucleo CONTINUA la
#: numerazione esistente: 17 è lo stato di oggi, la prima migrazione sarà la 18.
VERSIONE_DEL_NUCLEO = 17

#: Il valore che SQLite dà a un file mai marcato. Non è una versione.
NON_MARCATO = 0


class Marcatura(Enum):
    """I tre stati. Nominati, perché un'assenza non è una dichiarazione."""

    NON_MARCATO = "non marcato"
    VERSIONE = "versione"
    IGNOTO = "ignoto"


@dataclass(frozen=True)
class StatoDelloStore:
    """Che cosa dice di sé un file, e perché lo diciamo così."""

    marcatura: Marcatura
    versione: int | None
    percorso: Path
    perche: str = ""
    #: Quel che dice la tabella applicativa `_schema_version` per `semantic`.
    #: Distinta da `versione`, che viene dal pragma: oggi TUTTI gli store hanno
    #: il pragma a 0 e questa a 17, quindi un file «non marcato» può essere
    #: perfettamente allineato al codice. Confonderle chiuderebbe fuori tutti.
    versione_applicativa: int | None = None

    def __str__(self) -> str:
        if self.marcatura is Marcatura.VERSIONE:
            return f"versione {self.versione}"
        if self.marcatura is Marcatura.NON_MARCATO:
            return "non marcato (nessuno l'ha mai marcato: non è la versione 0)"
        return f"ignoto ({self.perche})"


def leggi_stato(percorso: str | Path) -> StatoDelloStore:
    """Lo stato di uno store, SENZA aprirlo con il prodotto.

    ⚠️ Questa funzione apre in sola lettura e non tocca lo schema. Misurato il
    18/09 su copie: aprire uno store con ``SemanticMemory`` lo MIGRA sul posto,
    in silenzio e senza backup (v1, v13 e v14 diventano v17 alla prima
    apertura). Una funzione che serve a decidere *se* migrare non può essere
    quella che migra: elencare i candidati non deve essere l'atto che li
    consuma.
    """
    p = Path(percorso)
    if not p.is_file():
        return StatoDelloStore(Marcatura.IGNOTO, None, p, "il file non esiste")
    try:
        con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        return StatoDelloStore(Marcatura.IGNOTO, None, p, f"non si apre: {exc}")
    try:
        numero = int(con.execute("PRAGMA user_version").fetchone()[0])
        applicativa = _versione_applicativa(con)
    except (sqlite3.DatabaseError, TypeError, ValueError) as exc:
        return StatoDelloStore(Marcatura.IGNOTO, None, p, f"non si legge: {exc}")
    finally:
        con.close()
    if numero == NON_MARCATO:
        return StatoDelloStore(Marcatura.NON_MARCATO, None, p,
                               versione_applicativa=applicativa)
    return StatoDelloStore(Marcatura.VERSIONE, numero, p,
                           versione_applicativa=applicativa)


def _versione_applicativa(con: sqlite3.Connection, db_id: str = "semantic") -> int | None:
    """Quel che dice `_schema_version`, o None se la tabella non c'e'.

    E' la versione che il prodotto usa OGGI per decidere le migrazioni. Il
    pragma e' la marcatura nuova; questa e' quella storica, e finche' gli store
    hanno il pragma a 0 e' l'unica che sa qualcosa.
    """
    try:
        riga = con.execute(
            "SELECT version FROM _schema_version WHERE db_id = ?", (db_id,)).fetchone()
    except sqlite3.DatabaseError:
        return None
    return int(riga[0]) if riga else None


def riguarda_il_nucleo(percorso: str | Path) -> bool:
    """Se questo file contiene le tabelle del nucleo, e quindi se ci riguarda.

    ⚠️ Serve a non confondere «l'ho guardato e va bene» con «non l'ho guardato».
    Misurato il 18/09 sui file veri: su 76 `.db` sotto la data dir, 45 non hanno
    una versione per `semantic` — sono store di altri sottosistemi (episodi,
    competenze, grafo) o file vuoti. Contarli come «si apre» sarebbe vero e
    ingannevole insieme: non sono stati esaminati, e un giorno qualcuno leggerà
    quel numero come una promessa.
    """
    p = Path(percorso)
    if not p.is_file():
        return False
    try:
        con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    except sqlite3.Error:
        return False
    try:
        presenti = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
    except sqlite3.DatabaseError:
        return False
    finally:
        con.close()
    #: `facts` è la tabella che rende uno store «del nucleo»: le altre cinque
    #: possono mancare (un file appena creato) o esserci per altre ragioni.
    return "facts" in presenti


#: Che cosa deve esistere DAVVERO perché una versione sia quella che dice.
#:
#: ⚠️ Serve perché il numero, da solo, non garantisce niente. Misurato il 18/09:
#: `ensure_schema_version(target_version=17, migrations=[])` su una copia a 16
#: porta la versione a 17 senza applicare nulla — `colonne: 28 -> 28, aggiunte:
#: NESSUNA`. Lo store dichiara la 17 con lo schema della 16, e chiunque si fidi
#: del numero legge una garanzia che nessuno ha dato.
#:
#: Le colonne qui sotto sono quelle che la migrazione 16→17 aggiunge davvero,
#: lette da un salto eseguito su copia — non da una lista scritta a memoria.
ATTESE_PER_VERSIONE: dict[int, frozenset[str]] = {
    17: frozenset({"quarantined_by", "grounding_span"}),
}


class SchemaNonCorrisponde(RuntimeError):
    """Il numero dice una versione, le colonne ne dicono un'altra."""


def schema_corrisponde(percorso: str | Path, versione: int) -> bool:
    """Se lo schema sul disco è davvero quello della versione dichiarata.

    Torna False anche quando NON SI SA: una versione che non è in
    `ATTESE_PER_VERSIONE` non è «va bene», è «non ho un criterio» — e marcare
    senza criterio è esattamente il buco di T121.
    """
    p = Path(percorso)
    if not p.is_file():
        return False
    try:
        con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    except sqlite3.Error:
        return False
    try:
        return schema_corrisponde_su(con, versione)
    finally:
        con.close()


def colonne_del_nucleo(con: sqlite3.Connection) -> set[str]:
    """Le colonne di `facts` su una connessione già aperta; vuoto se non c'è.

    Vuoto vuol dire «questo file non ha ancora un nucleo», che è lo stato di
    uno store appena creato — non «un nucleo con zero colonne».
    """
    try:
        return {r[1] for r in con.execute('PRAGMA table_info("facts")')}
    except sqlite3.DatabaseError:
        return set()


def schema_corrisponde_su(con: sqlite3.Connection, versione: int) -> bool:
    """`schema_corrisponde` per chi ha già la connessione in mano.

    Serve a chi deve decidere DENTRO una transazione, dove riaprire il file in
    sola lettura darebbe una risposta su uno stato diverso da quello che sta
    per scrivere.
    """
    attese = ATTESE_PER_VERSIONE.get(versione)
    if attese is None:
        return False
    return attese <= colonne_del_nucleo(con)


class StoreTroppoNuovo(RuntimeError):
    """Lo store è di una versione che questo codice non sa gestire."""


class StoreDaMigrare(RuntimeError):
    """Lo store è più vecchio del codice: va migrato, non aperto di nascosto."""


#: Il comando che scioglie il rifiuto. Sta in una costante perché un messaggio
#: che dice «non lo apro» senza dire come uscirne costringe chi lo legge a
#: cercare, e chi cerca nel momento sbagliato apre il file a mano — cioè fa
#: proprio la cosa che il rifiuto voleva impedire.
COMANDO_DI_MIGRAZIONE = "verimem store migrate {percorso}"


def verifica_apribile(stato: StatoDelloStore,
                      versione_del_codice: int = VERSIONE_DEL_NUCLEO) -> None:
    """Solleva se lo store non è alla pari del codice. In lettura E in scrittura.

    Due rifiuti, non uno, e per ragioni opposte:

    * **più nuovo** — questo codice non sa che cosa c'è dentro. Scriverci
      mescolerebbe i dati invece di fallire.
    * **più vecchio** — aprirlo lo MIGRA sul posto, in silenzio e senza ritorno:
      misurato il 18/09 su copie, un v1 diventa v17 con 23 colonne, 2 tabelle e
      7 indici nuovi alla prima apertura. Il rifiuto vale anche in LETTURA
      proprio per questo: è la lettura che fa il danno.

    Entrambi i messaggi portano le due versioni, il file e il comando: chi legge
    non deve andare a cercare niente di ciò che il programma aveva già in mano.
    """
    if stato.marcatura is Marcatura.IGNOTO:
        return
    #: Un file non marcato non è «vecchio»: è un file che nessuno ha marcato.
    #: Se la sua versione applicativa è quella del codice, è allineato e si apre
    #: come oggi — sono i 41 store di Aurelio, e chiuderli fuori sarebbe la cura
    #: peggiore del male.
    effettiva = stato.versione if stato.marcatura is Marcatura.VERSIONE else stato.versione_applicativa
    if effettiva is None or effettiva == versione_del_codice:
        return
    comando = COMANDO_DI_MIGRAZIONE.format(percorso=stato.percorso)
    if effettiva > versione_del_codice:
        raise StoreTroppoNuovo(
            f"lo store dice di essere alla versione {effettiva}, questo codice "
            f"ne gestisce fino alla {versione_del_codice}: {stato.percorso}. "
            f"Non lo apro — un codice più vecchio che scrive su uno schema più "
            f"nuovo mescola i dati invece di fallire. Aggiorna verimem, oppure "
            f"apri una copia."
        )
    raise StoreDaMigrare(
        f"lo store è alla versione {effettiva}, questo codice è alla "
        f"{versione_del_codice}: {stato.percorso}. Non lo apro nemmeno in "
        f"lettura — aprirlo lo migrerebbe sul posto, senza ritorno e senza "
        f"che nessuno te l'abbia chiesto. Per migrarlo davvero, dopo un "
        f"backup verificato:\n    {comando}"
    )


def marca(percorso: str | Path,
          backup_verificato,
          versione: int = VERSIONE_DEL_NUCLEO) -> StatoDelloStore:
    """Porta uno store da «non marcato» a «versione n». Solo dopo un backup.

    `backup_verificato` è una funzione che riceve il percorso, esegue il backup
    e CONTA le righe per verificarlo, e torna True solo se il conteggio torna.
    Sta fuori di qui apposta: questo modulo decide QUANDO marcare, non come si
    fa un backup — e il chiamante non può saltare il passo, perché senza un
    ritorno vero non si marca.

    ⚠️ Verificare un ripristino sull'impronta del FILE è un falso allarme:
    misurato il 15/09, il backup passa da `VACUUM INTO` e compatta, quindi lo
    sha256 cambia mentre il contenuto è identico. Si contano le righe.
    """
    stato = leggi_stato(percorso)
    if stato.marcatura is Marcatura.IGNOTO:
        raise StoreTroppoNuovo(f"non marco uno store che non so leggere: {stato}")
    if stato.marcatura is Marcatura.VERSIONE:
        return stato
    if not schema_corrisponde(percorso, versione):
        attese = ATTESE_PER_VERSIONE.get(versione)
        raise SchemaNonCorrisponde(
            f"non marco {percorso} come versione {versione}: lo schema sul "
            f"disco non è quello di quella versione"
            + (f" (mancano {sorted(attese)} in `facts`)" if attese else
               f" — e non ho nemmeno un criterio per la {versione}")
            + ". Un numero scritto senza lo schema che lo sostiene è una "
              "garanzia che nessuno ha dato: chi la legge poi si fida."
        )
    if not backup_verificato(Path(percorso)):
        raise RuntimeError(
            f"backup non riuscito o non verificato: {percorso} resta non "
            f"marcato. La marcatura è una scrittura, e una scrittura senza "
            f"ritorno non si fa."
        )
    con = sqlite3.connect(str(percorso))
    try:
        con.execute(f"PRAGMA user_version = {int(versione)}")
        con.commit()
    finally:
        con.close()
    return leggi_stato(percorso)
