#!/usr/bin/env python3
r"""Il messaggio di un commit parla del prodotto, non della stanza in cui lavoriamo.

    python scripts/messaggio_pulito.py --file <path>   # un messaggio (hook commit-msg)
    python scripts/messaggio_pulito.py --range A..B    # i commit di una PR (CI)
    python scripts/messaggio_pulito.py --autotest      # prova che il controllo morde

QUATTRO REGOLE, e ognuna nasce da una cosa che il repository pubblico mostrava:

  1. AL MASSIMO 10 RIGHE non vuote. Un messaggio lungo racconta un'indagine; il
     posto dell'indagine sono i documenti sotto `docs/`, che restano leggibili
     anche quando il commit e' stato squashato via.
  2. NIENTE PERCORSI LOCALI (`C:\Users\...`, `/c/Users/...`, `D:\a\...`): dicono
     com'e' fatta la macchina di chi ha scritto, e a chi legge non servono.
  3. NIENTE NOMI UTENTE.
  4. NIENTE NOMI DI SESSIONE ne' ruoli interni: chi legge da fuori non sa chi
     siano, e il lavoro e' del progetto, non di una sigla.

MISURATO PRIMA DI SCRIVERLO, con QUESTO script, sugli ultimi 40 commit del ramo
principale (`--range d60cc326~40..d60cc326`, il 12/09/2026):

    oltre 10 righe    : 39
    nome di sessione  : 24
    nome utente       :  5
    percorso locale   :  2
    PULITI            :  0     <- zero su quaranta

I 24 sono nomi nel CORPO, non nel trailer di attribuzione, che e' escluso: 37
dei 40 portano un `Agent: <Nome>`, e restano leggibili da fuori come sigle senza
significato. Se la convenzione va cambiata e' una decisione del progetto, non di
questo script; qui la dichiaro perche' un controllo che non copre una cosa deve
dire QUALE.

=> Il controllo vale sui commit NUOVI. La storia resta com'e': riscriverla
costerebbe piu' di quanto valga, e un `git log` vecchio non e' una promessa
all'utente. L'hook ferma il prossimo; la CI ferma quelli di una PR.

COME SI CORREGGE un messaggio bocciato: il contenuto non si butta, si sposta.
Le righe in piu' vanno in `docs/stato-reale/` o nel corpo della PR; il commit
tiene la riga che dice *cosa cambia* e, se serve, due righe di come e' provato.

----------------------------------------------------------------------------
I TRAILER NON CONTANO, E IL PERCHE' E' LA PARTE CHE SI SBAGLIA.

Un trailer (`Agent:`, `Co-Authored-By:`, `Signed-off-by:`) e' un campo del
registro, non racconto: `Agent: <Nome>` e' la cura di un incidente vero, i
dieci commit non attribuibili del 13/08, ed e' scritto in `.githooks/prepare-commit-msg`.
Toglierlo riaprirebbe quell'incidente, quindi il conteggio delle righe e le tre
regole sul testo lo saltano.

⚠️ LA PRIMA VERSIONE DI QUESTO SCRIPT SALTAVA **OGNI** RIGA CHE SOMIGLIASSE A
UN TRAILER, in qualunque punto del messaggio. Il risultato, provato il
12/09/2026 prima di spedirlo:

    "Fix the parser\n\nNota: trovato da <sessione> in C:\Users\<utente>\x"
      -> PULITO

Un percorso locale e un nome di sessione, **tutt'e due invisibili**, e la via
d'uscita era scrivere una parola e due punti. Il mio autotest era 12 su 12
verde e non lo vedeva: dodici casi scelti da me, tutti diretti al bersaglio che
avevo in mente.

🔑 Ora si toglie **solo il blocco finale**, e solo se ogni sua riga e' un
trailer — che e' come lo intende git. Una riga in mezzo al corpo viene letta,
qualunque forma abbia.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

RIGHE_MASSIME = 10

#: L'etichetta che distingue il problema di LUNGHEZZA dagli altri. Sta qui e
#: non e' ricopiata in due posti perche' chi compone il messaggio e chi lo
#: filtra devono usare LA STESSA stringa: due copie divergono, e la seconda
#: smetterebbe di riconoscere la prima senza che niente diventi rosso.
ETICHETTA_LUNGHEZZA = "righe di prosa"

PERCORSO = re.compile(r"([A-Za-z]:[\\/]Users[\\/]|/c/Users/|[A-Za-z]:[\\/]a[\\/]|/home/[a-z]+/)")
UTENTE = re.compile(r"\baurel(io)?(cpr)?(-ctrl)?\b", re.IGNORECASE)
# ⚠️ L'ELENCO DEI NOMI NON STA PIU' QUI, e il perche' e' la storia del 12/09:
# lo stesso elenco viveva in QUATTRO posti con TRE contenuti diversi, e ognuno
# sbagliava in modo suo — qui mancava `Curie`, altrove mancavano `Varco`,
# `Paragone`, `Lanterna`, e una pulizia arrivata a «zero nomi» ne lasciava 495.
# ⇒ L'elenco E' il criterio: due elenchi sono due criteri. Ora sta in
# `scripts/nomi_delle_sessioni.py`, che porta anche la regola delle maiuscole
# per i nomi che sono ANCHE parole italiane comuni.
# ⚠️ La cartella di QUESTO file, non `sys.path[0]`: in un worktree la seconda
# punta all'albero da cui si e' lanciato il comando, e si finirebbe per
# misurare con l'elenco di un altro albero (gia' pagato in casa due volte).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from nomi_delle_sessioni import trova as _nomi_di_sessione  # noqa: E402, I001
# ⚠️ UNA LISTA CHIUSA, non una forma. Vedi il docstring del modulo: con la
# regola sintattica (`^Parola:\s`) bastava scrivere `Nota:` per far sparire una
# riga dal controllo. Un'esenzione aperta a qualunque parola non e' un'esenzione,
# e' una via d'uscita. Qui ogni nome ammesso ha una ragione:
#   Agent           - l'attribuzione, cura dei 10 commit non attribuibili del 13/08
#   Co-Authored-By  - la riga che il progetto chiede in coda
#   gli altri       - trailer standard di git, che le piattaforme leggono
TRAILER_AMMESSI = ("Agent", "Co-Authored-By", "Signed-off-by", "Reviewed-by",
                   "Acked-by", "Tested-by", "Cc", "Fixes", "Closes", "Refs")
TRAILER = re.compile(r"^(?:" + "|".join(TRAILER_AMMESSI) + r"):\s", re.IGNORECASE)

# `git commit --verbose` incolla il diff in coda al messaggio, dopo questa riga.
# git lo taglia da se'; l'hook riceve il file PRIMA che lo faccia.
FORBICI = re.compile(r"^[#;!$%^&|:]?\s*-+\s*>8\s*-+\s*$", re.MULTILINE)


CANDIDATO_PERCORSO = re.compile(r"[A-Za-z0-9_.\-/]*/[A-Za-z0-9_.\-]*")

#: L'apertura di un blocco recintato: tre o piu' backtick, oppure tre o piu'
#: tilde, con o senza il nome del linguaggio. Si chiude col MEDESIMO marcatore,
#: lungo almeno quanto quello che ha aperto — cosi' come lo intende Markdown, e
#: come serve qui: un recinto di quattro backtick puo' contenerne tre.
_RECINTO = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})[^\n`]*$", re.MULTILINE)


#: Una riga CITATA: il `>` di Markdown, cioe' quello che il pulsante «Quote
#: reply» di GitHub mette davanti a ogni riga del commento citato.
_CITAZIONE = re.compile(r"^[ \t]{0,3}>", re.MULTILINE)

#: Un commento HTML, anche su piu' righe: chi legge la pagina non lo vede, e un
#: controllo che lo legge giudica su un testo che nessun umano ha davanti.
_COMMENTO_HTML = re.compile(r"<!--.*?-->", re.DOTALL)


def _senza_righe_citate(testo: str) -> str:
    """Il testo senza le righe che iniziano con `>`.

    ⚠️ IL PULSANTE «QUOTE REPLY» E' UNA PORTA. Chi risponde citando un commento
    che porta la Definition of Done se la ritrova nel proprio, riga per riga,
    con un `>` davanti — e senza questo taglio avrebbe **ri-dichiarato** al posto
    dell'autore, senza volerlo e senza accorgersene. E' lo stesso incidente del
    modello incollato, da un'altra porta: rilievo di un pari, non mio.
    """
    return "\n".join(r for r in testo.splitlines() if not _CITAZIONE.match(r))


def _senza_blocchi_rientrati(testo: str) -> str:
    """Il testo senza i blocchi di codice RIENTRATI di quattro spazi.

    ⚠️ IL CRITERIO E' QUELLO DI MARKDOWN, NON «quattro spazi». Un blocco
    indentato comincia dopo una riga VUOTA: le righe rientrate che continuano un
    elenco non lo sono, e toglierle boccerebbe chi scrive una checklist annidata
    — cioe' proprio chi dichiara sul serio. Una cura piu' larga del difetto
    colpisce chi ha fatto la cosa giusta, e costa piu' del difetto.
    """
    fuori: list[str] = []
    dentro = False
    vuota_prima = True
    for riga in testo.splitlines():
        rientrata = riga.startswith("    ") or riga.startswith("\t")
        if not riga.strip():
            fuori.append(riga)
            vuota_prima = True
            continue
        if rientrata and (dentro or vuota_prima):
            dentro = True
        else:
            dentro = False
            fuori.append(riga)
        vuota_prima = False
    return "\n".join(fuori)


def _solo_il_testo_dichiarato(testo: str) -> str:
    """Il testo senza cio' che e' MOSTRATO invece che dichiarato.

    ⚠️ IL NOME DICE IL CRITERIO, non la tecnica: si chiamava
    `_senza_blocchi_recintati` finche' toglieva i soli recinti, e quando @Marie
    ha misurato che ne restavano fuori tre forme il nome sarebbe diventato
    falso. Un nome che descrive meno di quel che fa e' la prima cosa che inganna
    chi lo legge dopo.

    Le QUATTRO forme, e ognuna e' una porta vera:
      ``` ``` / ~~~     un modello incollato per spiegare        (19/09, sette richieste verdi)
      rientro di 4      la stessa cosa nell'altra sintassi       (rilievo di Marie)
      `>` in testa      il pulsante «Quote reply» di GitHub      (rilievo di Marie)
      <!-- -->          invisibile a chi legge la pagina         (rilievo di Marie)

    🔑 L'ultima e' la peggiore delle quattro: un commento HTML **nessun umano lo
    vede**, quindi un controllo che lo leggesse giudicherebbe su un testo che
    l'autore non ha davanti — e chi guarda la pagina non capirebbe perche'.

    ⚠️ T201 (23/09): I FINE RIGA SI NORMALIZZANO PER PRIMI. Un commento caricato
    da un file scritto su Windows arriva con `\\r\\n`, e la chiusura di un
    recinto si riconosce con `[ \\t]*$`: una riga `` ```\\r `` non chiude, il
    recinto resta aperto fino in fondo e tutto cio' che segue sparisce. Misurato
    su #126: 5306 caratteri, 154 dopo il filtro, e le due righe `Registro:` e
    `Decisione:` fra quelle sparite — il cancello diceva «non porta Registro»
    quando il Registro c'era. Lo script normalizzava gia' `\\r\\n` piu' sotto,
    ma nella funzione che prepara il CORPO della richiesta, da cui i commenti
    della Definition of Done non passano: qui mancava, e questa e' l'unica
    funzione da cui passano tutti e quattro i filtri.
    """
    testo = testo.replace("\r\n", "\n").replace("\r", "\n")
    testo = _COMMENTO_HTML.sub("\n", testo)
    testo = _senza_recinti(testo)
    testo = _senza_righe_citate(testo)
    return _senza_blocchi_rientrati(testo)


def _senza_recinti(testo: str) -> str:
    """Il testo senza cio' che sta dentro ``` ``` o ~~~ ~~~.

    ⚠️ IL CRITERIO E' «DICHIARATO», NON «PRESENTE». Un modello incollato dentro
    un recinto e' una CITAZIONE: serve a mostrare a qualcuno che cosa scrivere,
    e leggerlo come una dichiarazione fa passare esattamente le richieste in cui
    nessuno ha dichiarato niente (misurato il 19/09 su sette).

    ⚠️ E il difetto si propaga ATTRAVERSO L'AIUTO: piu' uno e' utile — una
    guida, una risposta, un esempio in un commento — piu' richieste rende verdi.
    Per questo il taglio si fa qui, in una funzione sola, e non in ognuno dei
    punti che cercano qualcosa dentro un commento.

    🔑 Un recinto APERTO e mai chiuso mangia tutto fino alla fine: e' come lo
    rende Markdown, ed e' anche il verso giusto dell'errore — chi lascia un
    recinto aperto ottiene un rosso, non un verde.
    """
    pezzi: list[str] = []
    resto = testo
    while True:
        apre = _RECINTO.search(resto)
        if not apre:
            pezzi.append(resto)
            break
        pezzi.append(resto[:apre.start()])
        marcatore = apre.group(1)[0] * len(apre.group(1))
        dopo = resto[apre.end():]
        chiude = re.search(rf"^[ \t]{{0,3}}{re.escape(marcatore[0])}{{{len(marcatore)},}}[ \t]*$",
                           dopo, re.MULTILINE)
        if not chiude:
            break          # recinto aperto: il resto e' tutto dentro
        resto = dopo[chiude.end():]
    return "\n".join(p.strip("\n") for p in pezzi if p.strip())


def _percorsi_del_repo(radice: str | None = None) -> frozenset[str]:
    """Ogni percorso tracciato, nell'indice E in HEAD.

    Serve anche HEAD perche' una RINOMINA si descrive citando il nome VECCHIO,
    che nell'indice non c'e' piu' ma in HEAD si'.

    Se git non risponde (non e' un repository, non e' installato) torna un
    insieme vuoto: il controllo diventa piu' SEVERO, non muto. Un misuratore
    che cade deve sbagliare contro chi lo usa, non a suo favore.
    """
    percorsi: set[str] = set()
    for comando in (["git", "ls-files"], ["git", "ls-tree", "-r", "--name-only", "HEAD"]):
        try:
            fatto = subprocess.run(comando, cwd=radice, capture_output=True,
                                   text=True, encoding="utf-8", errors="replace")
        except OSError:
            continue
        if fatto.returncode == 0:
            percorsi.update(r.strip() for r in fatto.stdout.splitlines() if r.strip())
    return frozenset(percorsi)


def _senza_percorsi_veri(testo: str, percorsi: frozenset[str]) -> str:
    """Il testo senza i percorsi CHE ESISTONO nel repository.

    ⚠️ 12/09, il difetto che questa funzione cura: 95 file su 775 in
    `docs/stato-reale/` portano un nome di sessione SOLO nel nome del file, e la
    squadra li sta rinominando. Un `git mv` si descrive citando i due percorsi,
    e i due percorsi contengono il nome —

        "docs/stato-reale/banchi/<nome>-porte-e-etichetta.py becomes ..."
          -> BOCCIATO: nome di sessione

    cioe' il cancello bocciava esattamente il lavoro che cura il difetto. Un
    nome dentro il nome di un file non e' un nome nel discorso: e' una
    citazione, e toglierla renderebbe il messaggio falso.

    🔑 IL CRITERIO E' L'ESISTENZA, non la forma. `<nome>/appunti` ha la forma di
    un percorso e non e' tracciato da nessuna parte: resta prosa, e resta
    bocciato. Cosi' l'esenzione non si ottiene scrivendo una barra.
    """
    if not percorsi:
        return testo

    def togli(trovato: re.Match[str]) -> str:
        pezzo = trovato.group(0).strip(".,;:()[]`\"'<>")
        if not pezzo or "/" not in pezzo:
            return trovato.group(0)
        if pezzo in percorsi:
            return " "
        # Una CARTELLA: non e' tracciata di per se', ma lo e' cio' che contiene.
        prefisso = pezzo.rstrip("/") + "/"
        if any(p.startswith(prefisso) for p in percorsi):
            return " "
        return trovato.group(0)

    return CANDIDATO_PERCORSO.sub(togli, testo)


def _senza_trailer(testo: str) -> str:
    """Il messaggio senza il blocco di trailer finale, come lo intende git.

    NON basta scartare ogni riga che somigli a un trailer: `Nota: ...` somiglia,
    sta nel corpo, e scartandola il controllo lo evade chiunque scriva una
    parola e due punti (provato, vedi il docstring del modulo).
    """
    blocchi = testo.replace("\r\n", "\n").rstrip().split("\n\n")
    if len(blocchi) < 2:
        return testo
    ultime = [r for r in blocchi[-1].splitlines() if r.strip()]
    if ultime and all(TRAILER.match(r) for r in ultime):
        return "\n\n".join(blocchi[:-1])
    return testo


def _come_lo_salva_git(testo: str) -> str:
    """Il messaggio come git lo scrivera' davvero: senza commenti ne' diff.

    L'hook `commit-msg` riceve `.git/COMMIT_EDITMSG` prima della pulizia, quindi
    con dentro le righe `# ...` che git mette e poi toglie. Contarle direbbe «22
    righe» a chi ne ha scritte due. La pulizia la fa `git stripspace`, che e'
    l'implementazione di git e non una mia imitazione: `core.commentChar` puo'
    non essere `#`, e indovinarlo sarebbe l'ennesimo righello che sbaglia.
    """
    testo = FORBICI.split(testo, maxsplit=1)[0]
    try:
        fatto = subprocess.run(
            ["git", "stripspace", "--strip-comments"],
            input=testo, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
    except OSError:
        return testo
    return fatto.stdout if fatto.returncode == 0 else testo


def controlla(testo: str, percorsi: frozenset[str] | None = None) -> list[str]:
    """Le violazioni di un messaggio, in chiaro. Lista vuota = pulito.

    `percorsi` sono i file tracciati, per riconoscere le CITAZIONI di percorso;
    se non lo si passa li chiede a git. L'autotest ne passa uno finto apposta:
    un banco che dipendesse dai file veri del repository misurerebbe la pulizia
    di oggi invece del criterio, e diventerebbe rosso al primo `git mv`.
    """
    if percorsi is None:
        percorsi = _percorsi_del_repo()
    corpo = _senza_trailer(testo.replace("\r\n", "\n"))
    # ⚠️ 13/09 — SI CONTA LA PROSA, NON LE RIGHE. Le caselle di una Definition
    # of Done non sono prosa, e da quando il repository fonde con
    # `squash_merge_commit_message: PR_BODY` il corpo di una richiesta DIVENTA
    # il messaggio su main: con le dieci caselle del modello, il verde di un
    # cancello garantiva il rosso dell'altro. Il rilievo e' di chi ha letto
    # questa cura, misurato su tre casi costruiti; una zona compatibile
    # esisteva (prosa corta + DoD corta), quindi era una collisione di
    # parametri e non una regola impossibile. Su un messaggio senza DoD il
    # taglio non toglie niente e il conteggio resta quello di prima.
    righe_intere = [r for r in _solo_prosa(corpo).splitlines() if r.strip()]
    corpo = _senza_percorsi_veri(corpo, percorsi)
    problemi = []
    # ⚠️ Le righe si contano PRIMA della mascheratura: una riga fatta di solo
    # percorso diventerebbe vuota, e un messaggio di dodici righe ne
    # dichiarerebbe dieci. La mascheratura serve ai NOMI, non alla lunghezza.
    if len(righe_intere) > RIGHE_MASSIME:
        problemi.append(f"{len(righe_intere)} {ETICHETTA_LUNGHEZZA} "
                        f"(il massimo e' {RIGHE_MASSIME})")
    for etichetta, regola in (("percorso locale", PERCORSO),
                              ("nome utente", UTENTE)):
        trovati = sorted({m.group(0) for m in regola.finditer(corpo)})
        if trovati:
            problemi.append(f"{etichetta}: {', '.join(trovati[:4])}")
    # ⚠️ `con_identificatori=True`, ed e' una scelta di DOMINIO. L'esenzione per
    # gli identificatori generati (`iris-ub-jivzor1t`) vale per i DOCUMENTI, che
    # contengono dati di misure registrate: cambiarli falsificherebbe un reperto.
    # Un messaggio di commit non contiene reperti, e li' un nome attaccato a un
    # trattino e' un nome — provato: senza questo, «vedi docs/…/ws5-ha-sbagliato.md»
    # passava pulito. I percorsi VERI del repository sono gia' stati tolti sopra.
    nomi = sorted({n for n, _ in _nomi_di_sessione(corpo, con_identificatori=True)})
    if nomi:
        problemi.append("nome di sessione o ruolo interno: " + ", ".join(nomi[:4]))
    return problemi


# ─────────────────────────────────────────────────────────────────────────────
# 🆕 13/09 — IL CORPO DELLA RICHIESTA, giudicato con le STESSE regole.
#
# Il messaggio di fusione si compone dal corpo della richiesta: e' scritto nel
# modello della richiesta e lo facciamo a mano da due giorni. Finche' la regola
# vive solo li', vale quanto la disciplina di chi apre la richiesta — e una
# regola che dipende dalla disciplina non e' un presidio.
#
# ⚠️ Le regole sui NOMI e sui PERCORSI sono le stesse del messaggio e stanno
# nella stessa funzione: due superfici divergono, e questo progetto l'ha gia'
# pagato con l'elenco dei nomi che viveva in quattro posti con tre contenuti.
# Cambia SOLO il conteggio: qui si contano le righe di PROSA prima della DoD,
# perche' le caselle non sono prosa e il materiale sotto la DoD sta in fondo
# apposta.
RIGHE_DI_PROSA_MASSIME = 3
INTESTAZIONE_DOD = "### Definition of Done"

#: Le righe che non sono prosa in nessuno dei due oggetti che misuriamo — un
#: corpo di richiesta e un messaggio di commit. Una casella di spunta non
#: racconta niente a chi legge il registro fra un anno: e' un adempimento, e
#: contarla come una riga di racconto ha prodotto la collisione del 13/09, in
#: cui il verde di un cancello garantiva il rosso dell'altro.
_NON_E_PROSA = re.compile(
    r"^\s*(?:"
    r"- \[[ xX]\]"                 # una casella della Definition of Done
    r"|#{1,6}\s"                   # un'intestazione markdown
    r"|-{3,}\s*$"                  # un separatore
    r"|🤖\s"                        # il trailer generato
    r"|\|.*\|\s*$"                 # una riga di tabella
    r")",
)


def _solo_prosa(testo: str) -> str:
    """Il testo senza le righe che non sono prosa.

    ⚠️ Si toglie la RIGA, non il carattere: mascherare lascerebbe una riga
    vuota, e le righe vuote non si contano comunque — ma un giorno qualcuno
    conterebbe i caratteri e troverebbe un testo che non ha mai scritto
    nessuno.
    """
    # ⚠️ I COMMENTI DEL MODELLO NON SONO PROSA, e vanno tolti PRIMA di contare
    # le righe: un blocco `<!-- … -->` sta su piu' righe, e un filtro riga per
    # riga non lo vedrebbe. Provato il 13/09: il modello della richiesta, com'era
    # scritto nel repository, produceva un corpo di 39 righe di prosa — cioe' il
    # modello stesso non passava il controllo che accompagna.
    # 📌 LIMITE DICHIARATO: non sappiamo se la piattaforma tolga questi commenti
    # dal messaggio di fusione, perche' nel tronco non c'e' NESSUN commit nato
    # dal corpo intero (`git log --grep '<!--'` -> 0, misurato). Se li porta,
    # restano rumore nel log: per questo il modello e' anche CORTO — due difese
    # invece di una scommessa.
    senza_commenti = re.sub(r"<!--.*?-->", "", testo.replace("\r\n", "\n"),
                            flags=re.DOTALL)
    return "\n".join(r for r in senza_commenti.splitlines()
                     if not _NON_E_PROSA.match(r))


def _prosa_del_corpo(testo: str) -> str:
    """Cio' che sta PRIMA della Definition of Done: quello e' il messaggio."""
    return testo.replace("\r\n", "\n").split(INTESTAZIONE_DOD, 1)[0]


def controlla_corpo(testo: str, percorsi: frozenset[str] | None = None,
                    commenti: list[str] | None = None) -> list[str]:
    """Le violazioni del corpo di una richiesta. Lista vuota = pulito.

    🔴 13/09 — LA DoD NON STA PIU' NEL CORPO, e il perche' e' una misura, non
    un gusto. Da quando il repository fonde con `squash_merge_commit_message:
    PR_BODY` il corpo DIVENTA il messaggio su main: con le dieci caselle del
    modello, il corpo che questo controllo pretendeva produceva un messaggio che
    l'altro cancello bocciava — il verde di un cancello garantiva il rosso
    dell'altro. La cura non e' spostare una soglia: e' tenere fuori dal corpo
    cio' che non deve arrivare su main.

    ⇒ Tre pretese, e la terza e' quella che impedisce di perdere la DoD per
    strada:
      · al massimo tre righe di PROSA (le caselle non sono prosa, ovunque
        stiano, e il trailer generato non conta);
      · zero nomi di sessione e zero percorsi locali, sul corpo INTERO;
      · la Definition of Done deve esistere in un COMMENTO della richiesta.
        Se `commenti` non viene passato, la terza pretesa non si misura e lo
        DICE: un controllo che non gira e tace si legge come un controllo
        verde.
    """
    if percorsi is None:
        percorsi = _percorsi_del_repo()
    testo = testo.replace("\r\n", "\n")
    problemi: list[str] = []

    prosa = [r for r in _solo_prosa(testo).splitlines() if r.strip()]
    if len(prosa) > RIGHE_DI_PROSA_MASSIME:
        problemi.append(f"{len(prosa)} {ETICHETTA_LUNGHEZZA} (il massimo e' "
                        f"{RIGHE_DI_PROSA_MASSIME}): il resto va in un commento "
                        f"della richiesta, non nel corpo che diventa il messaggio")

    # ⚠️⚠️ SI LEGGE CIO' CHE E' DICHIARATO, NON CIO' CHE E' MOSTRATO. Un modello
    # incollato dentro ``` ``` per aiutare qualcuno NON e' una dichiarazione, e
    # il 19/09 questo controllo lo leggeva come tale: sette richieste sono
    # diventate verdi con «commenti dopo il mio: 0» su tutte e sette, perche' un
    # pari aveva incollato il modello in un commento — nello stesso messaggio in
    # cui spiegava che NON voleva far passare richieste senza dichiarazioni.
    # ⇒ Cercavo una STRINGA, e una stringa la trova anche dentro un recinto.
    if commenti is not None:
        commenti = [_solo_il_testo_dichiarato(c) for c in commenti]

    if commenti is None:
        problemi.append("NON MISURATO: la Definition of Done in un commento "
                        "(nessun commento passato al controllo)")
    elif not any(INTESTAZIONE_DOD in c for c in commenti):
        # ⚠️⚠️ QUESTA DIAGNOSI HA MENTITO, e per venti minuti ha bocciato le
        # richieste che facevano la cosa giusta. Diceva «nessun commento porta
        # la DoD» mentre il commento c'era: il controllo leggeva i commenti
        # ~25 s dopo l'apertura, e il commento nasce dopo — nessuno puo' aprire
        # una richiesta e commentarla nello stesso istante. Misurato il 18/09
        # su cinque richieste: #68, #69, #71 rosse con la DoD presente; #65 e
        # #66 verdi solo perche' il loro run era di UN GIORNO dopo il commento.
        #
        # ⇒ La cura vera e' l'attesa, e sta nel workflow. Questa e' l'altra
        # meta': un'assenza si dichiara CON L'ISTANTE IN CUI SI E' GUARDATO,
        # altrimenti chi legge conclude di aver sbagliato e riscrive una cosa
        # giusta. Un messaggio che mente su cio' che vede costa piu' di un
        # rosso muto.
        problemi.append(f"al momento di questo controllo nessun commento "
                        f"portava «{INTESTAZIONE_DOD}»: la richiesta non "
                        f"dichiara cosa considera finito. ⚠️ Se l'hai aggiunto "
                        f"DOPO l'apertura, il contenuto e' gia' giusto e non va "
                        f"riscritto: rilancia il controllo "
                        f"(`gh run rerun <id> --failed`)")
    else:
        # Il commento che porta la DoD deve dire anche DA DOVE viene la
        # richiesta: quale riga del registro previene, e quale decisione segue.
        # Senza, fra un anno la casella spuntata resta e la ragione no.
        dod = next(c for c in commenti if INTESTAZIONE_DOD in c)
        mancanti = [e for e, r in CAMPI_DELLA_PROVENIENZA.items() if not r.search(dod)]
        if mancanti:
            problemi.append(
                "il commento della Definition of Done non porta "
                + ", ".join(f"«{m}»" for m in mancanti)
                + ": una casella spuntata dice CHE e' finito, non PERCHE' e'"
                  " stato fatto ne' quale difetto gia' visto impedisce")

    # ⚠️ I nomi e i percorsi si cercano su TUTTO il corpo, non sulla sola prosa:
    # una riga in fondo e' pubblica quanto la prima, e finisce su main con lei.
    mascherato = _senza_percorsi_veri(testo, percorsi)
    for etichetta, regola in (("percorso locale", PERCORSO), ("nome utente", UTENTE)):
        trovati = sorted({m.group(0) for m in regola.finditer(mascherato)})
        if trovati:
            problemi.append(f"{etichetta}: {', '.join(trovati[:4])}")
    nomi = sorted({n for n, _ in _nomi_di_sessione(mascherato, con_identificatori=True)})
    if nomi:
        problemi.append("nome di sessione o ruolo interno: " + ", ".join(nomi[:4]))
    return problemi


#: I due campi che il commento della Definition of Done deve portare, con la
#: forma minima che il controllo accetta. Il VALORE non si giudica qui — un
#: numero di riga o «nessuna, non tocca il nucleo» sono entrambi validi e chi
#: legge li verifica nelle due pagine: questo controllo pretende che ci SIANO.
#:
#: ⚠️ PERCHE' DUE E NON DIECI. Una Definition of Done di dieci caselle esiste
#: gia' (CONTRIBUTING.md) e il controllo la pretende gia' qui sopra. Aggiungerne
#: altre dieci ne farebbe venti, e una lista di venti caselle si spunta senza
#: leggerla: sarebbe un rito. Questi due campi non sono caselle — sono due
#: puntatori, e chiedono la cosa che nessuna delle dieci chiede: da dove viene
#: la richiesta e quale difetto gia' visto impedisce.
CAMPI_DELLA_PROVENIENZA = {
    "Registro: riga <n>": re.compile(r"^\s*Registro:\s*\S", re.I | re.M),
    "Decisione: <n>": re.compile(r"^\s*Decisione:\s*\S", re.I | re.M),
}

#: ⚠️ QUESTO FIXTURE E' CONDIVISO DA OTTO CASI, e cinque di essi si aspettano
#: «pulito». Aggiungendo la pretesa dei due campi senza aggiungerli QUI, quei
#: cinque cadono tutti insieme: e' il rosso 5-su-40 riportato dal pari il 16/09,
#: e non e' un difetto del controllo ma del fixture rimasto indietro. Un caso di
#: prova che rappresenta «la richiesta fatta bene» deve essere aggiornato nello
#: stesso commit in cui «fatta bene» cambia significato.
DOD_IN_COMMENTO = [
    INTESTAZIONE_DOD
    + "\n- [x] RED at the port\n- [ ] GREEN\n"
    + "\nRegistro: riga 4\nDecisione: nessuna, non tocca il nucleo\n"
]

#: Lo stesso commento SENZA i due campi: e' il caso che deve essere bocciato, ed
#: e' anche il controllo negativo del fixture qui sopra. Se un giorno questo
#: passasse, la pretesa non starebbe piu' mordendo.
DOD_SENZA_PROVENIENZA = [
    INTESTAZIONE_DOD + "\n- [x] RED at the port\n- [ ] GREEN\n"
]

# (nome, corpo, commenti, ci aspettiamo che sia pulito)
CASI_CORPO: list[tuple[str, str, list[str] | None, bool]] = [
    ("tre righe e la DoD in un commento",
     "Una.\n\nDue.\n\nTre.\n", DOD_IN_COMMENTO, True),
    ("una riga sola", "Una.\n", DOD_IN_COMMENTO, True),
    ("quattro righe di prosa",
     "Una.\n\nDue.\n\nTre.\n\nQuattro.\n", DOD_IN_COMMENTO, False),
    # La terza pretesa: la DoD non sparisce, si sposta.
    ("nessun commento porta la DoD", "Una.\n", ["un commento qualunque"], False),
    # 🔴 19/09: il MODELLO incollato per aiutare non e' una dichiarazione. Sette
    # richieste verdi con «commenti dopo il mio: 0» su tutte e sette.
    ("la DoD dentro un recinto e' un ESEMPIO, non una dichiarazione", "Una.\n",
     ["Ti mancano due righe:\n\n```\n" + DOD_IN_COMMENTO[0] + "\n```\n"], False),
    ("nessun commento affatto", "Una.\n", [], False),
    # ⚠️ Il controllo che NON GIRA lo dice: se `commenti` non arriva, il
    # verdetto non e' verde, e' «NON MISURATO».
    ("commenti non passati al controllo", "Una.\n", None, False),
    # I due campi della provenienza: la DoD c'e', ma non dice da dove viene.
    ("la DoD non porta i due campi", "Una.\n", DOD_SENZA_PROVENIENZA, False),
    ("la DoD porta solo il registro", "Una.\n",
     [INTESTAZIONE_DOD + "\n- [x] GREEN\n\nRegistro: riga 4\n"], False),
    ("la DoD porta solo la decisione", "Una.\n",
     [INTESTAZIONE_DOD + "\n- [x] GREEN\n\nDecisione: D-0003\n"], False),
    # «nessuna» e' un VALORE, non un'assenza: una richiesta che non tocca il
    # nucleo lo dichiara invece di lasciare il campo vuoto.
    ("«nessuna» e' una decisione dichiarata", "Una.\n",
     [INTESTAZIONE_DOD + "\n- [x] GREEN\n\nRegistro: riga 7\n"
      "Decisione: nessuna, non tocca il nucleo\n"], True),
    # Le caselle non sono prosa NEANCHE nel corpo: se qualcuno le lascia li',
    # non fanno scattare la lunghezza — ma la DoD deve stare comunque in un
    # commento, perche' il corpo diventa il messaggio su main.
    ("caselle lasciate nel corpo", "Una.\n" + INTESTAZIONE_DOD
     + "\n- [x] GREEN\n- [ ] altro\n", DOD_IN_COMMENTO, True),
    ("una tabella non e' prosa",
     "Una.\n\n| a | b |\n|---|---|\n| 1 | 2 |\n", DOD_IN_COMMENTO, True),
    ("il trailer generato non e' prosa",
     "Una.\n\nDue.\n\nTre.\n\n🤖 Generated with qualcosa\n", DOD_IN_COMMENTO, True),
    ("un nome di sessione nel corpo",
     "Rilievo di ws5 sul gate.\n", DOD_IN_COMMENTO, False),
    ("un nome umano in fondo al corpo",
     "Una.\n\nDue.\n\ntrovato da Marie\n", DOD_IN_COMMENTO, False),
]


def _messaggi_del_range(intervallo: str) -> list[tuple[str, str]]:
    out = subprocess.run(
        ["git", "log", "--format=%H%x00%B%x1e", intervallo],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if out.returncode != 0:
        raise SystemExit(f"git log {intervallo} non ha funzionato: {out.stderr.strip()[:120]}")
    coppie = []
    for blocco in out.stdout.split("\x1e"):
        if not blocco.strip():
            continue
        sha, _, corpo = blocco.strip().partition("\x00")
        coppie.append((sha[:8], corpo))
    if not coppie:
        # Un intervallo vuoto non e' una PR pulita: e' una misura che non c'e'.
        raise SystemExit(f"{intervallo} non contiene nessun commit: non ho misurato niente.")
    return coppie


def stampa(coppie: list[tuple[str, str]], righe_solo_rapporto: bool = False) -> int:
    """Stampa il verdetto e lo rende come codice di uscita.

    🆕 13/09 — `righe_solo_rapporto` separa due cose che hanno urgenze diverse,
    e serve sulle RICHIESTE:
      · i NOMI e i PERCORSI restano bloccanti anche li', perche' la pagina di
        una richiesta e' pubblica quanto il tronco: quel testo si legge oggi;
      · la LUNGHEZZA diventa un rapporto, perche' i commit di una richiesta
        sono quelli grezzi dell'autore e lo squash non li porta in main —
        chiedere di riscrivere una storia che nessuno leggera' e' attrito che
        non compra niente.
    Sul tronco e sui rami di integrazione NON si usa: li' quei messaggi sono
    esattamente quelli che restano.
    """
    sporchi = 0
    rapporti = 0
    for sha, testo in coppie:
        problemi = controlla(testo)
        avvisi: list[str] = []
        if righe_solo_rapporto:
            avvisi = [p for p in problemi if ETICHETTA_LUNGHEZZA in p]
            problemi = [p for p in problemi if ETICHETTA_LUNGHEZZA not in p]
        prima = testo.strip().splitlines()[0][:52] if testo.strip() else "(vuoto)"
        if problemi:
            sporchi += 1
            print(f"  BOCCIATO {sha}  {prima}")
            for p in problemi:
                print(f"           - {p}")
        else:
            print(f"  ok       {sha}  {prima}")
        for a in avvisi:
            rapporti += 1
            print(f"           · (rapporto, non blocca qui) {a}")
    print()
    if rapporti:
        print(f"  {rapporti} messaggi sono piu' lunghi del tetto. Qui e' un rapporto: "
              "quei commit non arrivano in main con lo squash.")
    if sporchi:
        print(f"VERDETTO: ROSSO - {sporchi} messaggi su {len(coppie)} parlano della "
              "nostra stanza invece che del prodotto.")
        print("  Il contenuto non si butta, si sposta: le righe in piu' vanno in "
              "docs/stato-reale/ o in un commento della richiesta.")
        return 1
    print(f"VERDETTO: VERDE - {len(coppie)} messaggi, nessuno da correggere.")
    return 0


# (nome, messaggio, ci aspettiamo che sia pulito)
CASI: list[tuple[str, str, bool]] = [
    ("una riga pulita", "Cap the scan at one place", True),
    ("dieci righe esatte", "Titolo\n" + "\n".join(f"riga {i}" for i in range(9)), True),
    ("undici righe", "Titolo\n" + "\n".join(f"riga {i}" for i in range(10)), False),
    ("percorso windows", "Fix\n\nvisto in C:\\Users\\tizio\\repo", False),
    ("percorso msys", "Fix\n\nvisto in /c/Users/tizio/repo", False),
    ("percorso del runner", "Fix\n\nD:\\a\\progetto\\progetto", False),
    ("nome utente", "Fix\n\nsegnalato da aureliocpr", False),
    ("sigla di sessione", "Fix\n\nrilievo di ws5", False),
    ("nome di sessione", "Fix\n\ntrovato da Marie", False),
    # Il nome che il mio elenco NON aveva, e che l'altro righello aveva.
    ("il nono nome, quello che mancava", "Fix\n\nrilievo di Curie", False),
    # I tre che NESSUNO dei due righelli aveva: nomi veri che sono anche
    # parole comuni. Le due righe qui sotto sono la coppia che rende il
    # criterio un criterio — se cadesse la seconda, sarebbe un cancello che
    # grida su «il varco fra i due».
    ("un nome che e' anche una parola, maiuscolo",
     "Fix the parser\n\nrilievo di Varco, controfirmato da Paragone", False),
    ("la stessa parola in minuscolo NON e' un nome",
     "Close the gap between the two ports\n\nil varco fra i due era largo, "
     "e per paragone la porta vecchia lo chiudeva", True),
    ("ruolo interno", "Fix\n\nchiesto da lead-audit", False),
    ("il trailer non conta", "Fix\n\nDue righe di spiegazione.\n"
                             "Co-Authored-By: Qualcuno <a@b.c>", True),
    ("il trailer di attribuzione non conta", "Fix the parser\n\nAgent: Corrado", True),
    ("parola che CONTIENE un nome", "Fix the marieterapia parser", True),
    # I quattro casi qui sotto NON li avevo previsti: li ha trovati la prova di
    # evasione del 12/09, contro la prima versione che era 12 su 12 verde.
    ("riga del corpo travestita da trailer",
     "Fix the parser\n\nNota: trovato da Marie in C:\\Users\\tizio\\x", False),
    ("due righe travestite da trailer",
     "Fix\n\nReported: ws5 says the port is wrong\nAltro: /c/Users/tizio/repo", False),
    ("trailer veri DOPO un corpo sporco",
     "Fix\n\nvisto da Tara\n\nAgent: Iris\nCo-Authored-By: Q <a@b.c>", False),
    ("un blocco finale misto NON e' un blocco di trailer",
     "Fix\n\nAgent: Iris\nma questa riga nomina ws5", False),
]

# Percorsi FINTI per i casi di citazione: se il banco leggesse i file veri
# misurerebbe la pulizia di oggi invece del criterio, e diventerebbe rosso al
# primo `git mv` — cioe' proprio quando la cura funziona.
PERCORSI_FINTI = frozenset({
    "docs/stato-reale/banchi/ws7-porte-e-etichetta.py",
    "docs/stato-reale/banchi-ws2/porte.py",
    "docs/stato-reale/ws8-corrado-notte-05-06-09.md",
})

CASI_CON_PERCORSI: list[tuple[str, str, bool]] = [
    ("una rinomina, citando il nome vecchio",
     "Rename the bench so its name carries a role\n\n"
     "docs/stato-reale/banchi/ws7-porte-e-etichetta.py becomes "
     "docs/stato-reale/banchi/porte-e-etichetta.py.", True),
    ("la citazione di un documento che esiste",
     "Link the postmortem from the README\n\n"
     "Adds a pointer to docs/stato-reale/ws8-corrado-notte-05-06-09.md.", True),
    ("una cartella tracciata",
     "Move the benches out of a per-session folder\n\n"
     "docs/stato-reale/banchi-ws2/ becomes docs/stato-reale/banchi/porte/.", True),
    # 🔑 I due che rendono l'esenzione un criterio e non una via d'uscita.
    ("una barra NON basta: il percorso non esiste",
     "Fix the parser\n\nvedi ws5/appunti per il dettaglio", False),
    ("un percorso inventato dentro una cartella vera",
     "Fix\n\nvedi docs/stato-reale/ws5-ha-sbagliato.md", False),
]

# ⚠️ I TRE CASI DELLA COLLISIONE, dal rilievo del 13/09. Il primo e' quello che
# la rompeva: da quando si fonde con `squash_merge_commit_message: PR_BODY` il
# corpo di una richiesta DIVENTA il messaggio su main, e con le dieci caselle
# del modello arrivava a quindici righe — il verde di un cancello garantiva il
# rosso dell'altro. Il terzo e' il CONTROLLO POSITIVO che il rilievo stesso
# chiede: la prosa lunga deve restare ROSSA, altrimenti abbiamo allargato la
# soglia invece di distinguere l'oggetto.
_CASELLE = "\n".join(f"- [ ] casella {i}" for i in range(10))
DOD_INTERA = INTESTAZIONE_DOD + "\n" + _CASELLE
CASI += [
    ("tre righe di prosa e la DoD intera",
     "Titolo\n\nUna.\n\nDue.\n\n" + DOD_INTERA, True),
    ("dieci caselle non fanno un papiro",
     "Titolo\n\n" + DOD_INTERA, True),
    ("undici righe di prosa restano rosse ANCHE con la DoD",
     "Titolo\n" + "\n".join(f"riga {i}" for i in range(10)) + "\n" + DOD_INTERA,
     False),
]


def autotest() -> int:
    """Il controllo positivo: deve bocciare cio' che deve e TACERE sul resto."""
    esiti = []
    coppie = ([(n, t, a, frozenset()) for n, t, a in CASI]
              + [(n, t, a, PERCORSI_FINTI) for n, t, a in CASI_CON_PERCORSI])
    for nome, testo, atteso_pulito, percorsi in coppie:
        problemi = controlla(testo, percorsi=percorsi)
        ok = (not problemi) == atteso_pulito
        esiti.append(ok)
        stato = "pulito" if not problemi else f"bocciato ({problemi[0][:44]})"
        print(f"  [{'OK ' if ok else 'ROSSO'}] {nome:38s} -> {stato}")

    # ⚠️ I casi del CORPO girano nello stesso autotest: un criterio nuovo che
    # avesse un autotest suo verrebbe lanciato da un posto in meno.
    for nome, corpo, commenti, atteso_pulito in CASI_CORPO:
        problemi = controlla_corpo(corpo, percorsi=PERCORSI_FINTI, commenti=commenti)
        ok = (not problemi) == atteso_pulito
        esiti.append(ok)
        stato = "pulito" if not problemi else f"bocciato ({problemi[0][:40]})"
        print(f"  [{'OK ' if ok else 'ROSSO'}] corpo: {nome:31s} -> {stato}")

    # Il commento di git non e' una riga del messaggio: contarlo bocerebbe un
    # commit di due righe scritto nell'editor.
    con_commenti = ("Titolo vero\n\nCorpo vero.\n"
                    + "# Please enter the commit message for your changes.\n"
                      "# On branch principale\n" * 9)
    pulito = _come_lo_salva_git(con_commenti)
    ok_commenti = not controlla(pulito) and "# On branch" not in pulito
    esiti.append(ok_commenti)
    print(f"  [{'OK ' if ok_commenti else 'ROSSO'}] {'i commenti di git non contano':38s} -> "
          f"{len([r for r in pulito.splitlines() if r.strip()])} righe dopo la pulizia")

    print()
    if all(esiti):
        print(f"AUTOTEST VERDE: {len(esiti)} casi su {len(esiti)} - il controllo boccia "
              "cio' che deve e tace sul resto.")
        return 0
    print(f"AUTOTEST ROSSO: {esiti.count(False)} casi sbagliati su {len(esiti)}.")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--file", help="un messaggio da file (hook commit-msg)")
    parser.add_argument("--range", dest="intervallo", help="i commit di un intervallo git")
    parser.add_argument("--corpo", help="il corpo di una richiesta, da file")
    parser.add_argument("--titolo", help="il titolo della richiesta, da file")
    parser.add_argument("--commenti", help="i commenti della richiesta, da file JSON")
    parser.add_argument(
        "--righe-solo-rapporto", action="store_true",
        help=("la lunghezza diventa un rapporto invece di un veto: sulle "
              "richieste i commit sono quelli grezzi dell'autore e lo squash "
              "non li porta in main. I nomi e i percorsi restano bloccanti."),
    )
    parser.add_argument("--autotest", action="store_true")
    a = parser.parse_args(argv)
    if a.autotest:
        return autotest()
    if a.corpo:
        testo = pathlib.Path(a.corpo).read_text(encoding="utf-8", errors="replace")
        titolo = ""
        if a.titolo:
            titolo = pathlib.Path(a.titolo).read_text(
                encoding="utf-8", errors="replace").strip()
        esito = 0
        commenti = None
        if a.commenti:
            import json
            commenti = json.loads(
                pathlib.Path(a.commenti).read_text(encoding="utf-8", errors="replace"))
        problemi = controlla_corpo(testo, commenti=commenti)
        if problemi:
            esito = 1
            print("  BOCCIATO  il corpo della richiesta")
            for p in problemi:
                print(f"            - {p}")
        else:
            print("  ok        il corpo della richiesta")
        # ⚠️ E POI L'OGGETTO CHE NASCE DOPO: con `squash_merge_commit_title:
        # PR_TITLE` e `_message: PR_BODY`, il messaggio su main E' titolo + corpo.
        # Giudicare il solo corpo lascia passare un nome di sessione scritto nel
        # TITOLO — rilievo del 13/09, ed e' la stessa classe che questo controllo
        # esiste per chiudere, un pezzo piu' in la'.
        if titolo:
            composto = titolo + "\n\n" + testo
            problemi = controlla(composto)
            if problemi:
                esito = 1
                print("  BOCCIATO  il messaggio che nascerebbe (titolo + corpo)")
                for p in problemi:
                    print(f"            - {p}")
            else:
                print("  ok        il messaggio che nascerebbe (titolo + corpo)")
        print()
        if esito:
            print("VERDETTO: ROSSO - il corpo della richiesta non compone un "
                  "messaggio di fusione.")
            print("  Il contenuto non si butta, si sposta: le righe in piu' vanno "
                  "in un commento della richiesta o in docs/stato-reale/.")
            return 1
        print("VERDETTO: VERDE - il corpo compone.")
        return 0
    if a.file:
        grezzo = pathlib.Path(a.file).read_text(encoding="utf-8", errors="replace")
        return stampa([("(in scrittura)", _come_lo_salva_git(grezzo))])
    if a.intervallo:
        return stampa(_messaggi_del_range(a.intervallo),
                      righe_solo_rapporto=a.righe_solo_rapporto)
    parser.error("serve --file, --range o --autotest")
    return 2


if __name__ == "__main__":
    sys.exit(main())
