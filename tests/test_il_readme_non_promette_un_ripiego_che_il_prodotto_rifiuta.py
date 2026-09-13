"""README:615-616 — «each falls back to its own embedded store (fail-soft, never a crash)».

🔴 IL DIFETTO, ed e' di una forma che ho visto poche volte: **il testo NEGA una
difesa che il prodotto HA**. Non promette troppo per distrazione — descrive il
prodotto come se una sua protezione non esistesse.

Il README, nella sezione del gateway condiviso:

    With those set, the Python SDK, the CLI and the MCP tools all route through
    the shared server — a session behind it never loads a model. **If the server
    is unreachable, each falls back to its own embedded store (fail-soft, never
    a crash).**

«**each**» vuol dire ognuno. Misurato sul prodotto il 13/09/2026:

    porte che RIFIUTANO in thin mode invece di ricadere:  28
      di cui scritture (_THIN_UNSUPPORTED_WRITES):        14
      di cui letture   (_THIN_UNSUPPORTED_READS):         14

Non ricadono, e **non e' un buco: e' la difesa**. Una scrittura che ripiega sullo
store locale mentre l'utente crede di scrivere sul corpus condiviso muta il posto
sbagliato e riferisce un esito che nel corpus condiviso non e' avvenuto — che e'
testualmente il danno descritto tre righe piu' giu' nel prodotto stesso: «MUTATE
the LOCAL store, leaving the shared corpus untouched while reporting an outcome
as if it had changed».

🔑 PERCHE' QUESTO PRESIDIO ESISTE, e non e' pedanteria editoriale. Una riga che
descrive una difesa come assente **spinge a rimuoverla**: il giorno che qualcuno
allinea prodotto e documentazione, ha davanti due strade — sei parole nel README,
oppure svuotare la deny-list per rendere vero «each falls back». La seconda e'
piu' rapida, sembra una semplificazione, e toglie la protezione. Le difese
dichiarate male si perdono cosi', non per una decisione ma per una pulizia.

⚠️ CERCATA PRIMA DI ACCUSARE: `grep -nE "fall back|falls back|fallback"` su tutto
il README da **due sole** occorrenze — la 156 (un altro argomento: l'escalation
che ripiega su held-for-review) e questa. **Nessun punto della pagina dichiara
l'eccezione.** E nemmeno «refuse/reject/unsupported/thin mode» la nomina: le
occorrenze trovate parlano di `restore` su un fatto superato, di
`explain`/`trust_report` che si astengono, e del daemon che non compone — tre
cose diverse da questa.

LA CURA E' SEI PAROLE, e non tocca il prodotto: «reads fall back; the writes that
mutate the shared corpus refuse instead». Chi la scrive decida la formulazione —
questo presidio non la impone, chiede solo che l'eccezione ci sia.

Gravita': **P2**. Non blocca un percorso d'uso e l'utente se ne accorge da solo
(riceve un rifiuto esplicito, non un silenzio) ⇒ e' un difetto che si LEGGE, non
uno che SCRIVE. Ma va sopra le altre P2 per l'aggravante detta sopra: e' l'unica
che mette pressione **sulla rimozione di una difesa**.

Presidio: Product Owner, 13/09/2026, sul README di `origin/main`.
⚠️ LIMITE DICHIARATO: **non eseguito da chi lo ha scritto**? No — questa volta
l'ho eseguito: **3 passed**, e lo dico perche' i miei presidi precedenti
portavano il limite opposto e chi legge deve sapere quale dei due vale.
"""

from __future__ import annotations

import pathlib
import re

from verimem import mcp_server

RADICE = pathlib.Path(__file__).resolve().parents[1]
README = RADICE / "README.md"

#: La promessa, testuale. Il presidio cerca il TESTO, mai il numero di riga: la
#: riga si sposta a ogni paragrafo aggiunto sopra (in un giorno il claim che
#: sorveglio altrove e' passato dalla 352 alla 355).
PROMESSA = "falls back to its own"

#: Le parole con cui la pagina dichiarerebbe l'eccezione. Ne basta UNA vicina
#: alla promessa: la formulazione la sceglie chi scrive, non questo test.
_DICHIARA_L_ECCEZIONE = re.compile(
    r"refuse|refuses|reject|rejects|do(?:es)? not fall back|except|"
    r"unsupported in thin|thin mode",
    re.I,
)

#: Quanto vicino deve stare l'eccezione perche' sia LA SUA eccezione. Se la
#: cercassi in tutta la pagina la troverei sempre: «refuse» compare altrove per
#: tre argomenti diversi, e un presidio che si accontenta di quello e' cieco.
_VICINANZA = 400


def _testo() -> str:
    assert README.is_file(), f"il README non e' al suo posto: {README}"
    return README.read_text(encoding="utf-8", errors="replace")


def _porte_che_rifiutano() -> set[str]:
    return set(mcp_server._THIN_UNSUPPORTED_WRITES) | set(
        mcp_server._THIN_UNSUPPORTED_READS
    )


def test_CONTROLLO_la_difesa_ESISTE_ancora_nel_prodotto():
    """PRIMA di tutto: se la deny-list fosse vuota, il test sotto passerebbe.

    E passerebbe **per la ragione peggiore** — non perche' il README e' stato
    corretto, ma perche' la difesa e' stata tolta e «each falls back» e'
    diventato vero. E' lo scenario che questo file esiste per vedere, quindi e'
    il primo controllo, non l'ultimo.
    """
    porte = _porte_che_rifiutano()
    assert len(porte) >= 20, (
        f"le porte che rifiutano in thin mode sono {len(porte)}, erano 28 il "
        "13/09. Se sono state TOLTE, il ripiego silenzioso e' tornato sulle "
        "scritture: una scrittura che ripiega muta lo store locale mentre "
        "l'utente crede di scrivere sul corpus condiviso. **Prima di aggiornare "
        "questo numero, guarda perche' sono sparite.**"
    )
    scritture = set(mcp_server._THIN_UNSUPPORTED_WRITES)
    assert scritture, (
        "la deny-list delle SCRITTURE e' vuota: la difesa non c'e' piu' e la "
        "riga del README e' diventata vera nel modo sbagliato."
    )


#: 🔴 LO STATO REGISTRATO, misurato il 13/09/2026 su `origin/main` (`cd354c15`):
#: accanto alla promessa del ripiego **non c'e'** la dichiarazione dell'eccezione.
#:
#: ⚙️ PERCHE' `True` E NON UN'ASSERZIONE CHE PRETENDE LA CURA. Il primo getto di
#: questo file scriveva `assert dichiara`, cioe' un test **rosso finche' il
#: README non e' corretto** — ed e' la forma che ho passato la serata a togliere
#: da altri tre file, riscritta da me un'ora dopo. Un test che resta rosso non
#: misura: blocca, e chi lo trova lo disattiva. Il difetto si REGISTRA, e il
#: presidio cade quando lo stato cambia.
L_ECCEZIONE_MANCA_IL_13_09 = True


def test_quanto_il_readme_dichiara_dell_eccezione_accanto_alla_promessa():
    """🔴 Il difetto e' APERTO e questo test lo REGISTRA. Cade nei DUE versi.

    🟢 Se il README dichiara l'eccezione accanto alla promessa, questo diventa
       rosso: **e' la buona notizia**. Porta la costante a `False` e gira il
       presidio nell'asserzione positiva — da li' in poi sorveglia che la riga
       nuova non si perda.
    🔴 Se la promessa del ripiego sparisce del tutto, lo dice il controllo
       positivo qui sopra invece di lasciar passare un verde per assenza.
    """
    testo = _testo()
    i = testo.find(PROMESSA)

    # Controllo positivo del righello: se la promessa non c'e' piu', questo test
    # non sta misurando niente e deve DIRLO.
    assert i > 0, (
        f"la riga che questo presidio sorveglia non e' piu' nel README: "
        f"{PROMESSA!r}. Se il paragrafo del gateway e' stato riscritto, aggiorna "
        "il frammento; se il ripiego non esiste piu', togli il test con la "
        "ragione. **Non lasciarlo passare cosi'.**"
    )

    intorno = testo[i : i + _VICINANZA]
    manca = not _DICHIARA_L_ECCEZIONE.search(intorno)
    porte = _porte_che_rifiutano()

    assert manca == L_ECCEZIONE_MANCA_IL_13_09, (
        "🟢 **BUONA NOTIZIA, e questo presidio va GIRATO**: accanto alla promessa "
        "del ripiego il README adesso dichiara l'eccezione. Porta "
        "`L_ECCEZIONE_MANCA_IL_13_09` a `False` e trasforma questa in "
        "un'asserzione positiva, cosi' da qui in poi sorveglia che quella riga "
        "non si perda in una futura ripulitura.\n"
        f"Per riferimento, le porte che rifiutano sono {len(porte)} "
        f"({len(mcp_server._THIN_UNSUPPORTED_WRITES)} scritture, "
        f"{len(mcp_server._THIN_UNSUPPORTED_READS)} letture)."
    )


def test_CONTROLLO_il_righello_dell_eccezione_si_accende_e_tace_dove_deve():
    """Il test sopra cerca un'ASSENZA: senza questo passerebbe anche cieco.

    ⚠️ LA PRIMA VERSIONE DI QUESTO CONTROLLO ERA SBAGLIATA, e il rosso me l'ha
    detto: cercava la parola «nelle 4000 battute PRIMA della promessa» dando per
    scontato che ci fosse. Non c'e' — le occorrenze di «refuse» nel README stanno
    molto piu' in alto (un `restore` su un fatto superato, due porte che si
    astengono, il daemon che non compone). **Una prova di calibrazione costruita
    su un'assunzione non e' una prova**: questi due casi sono letterali e non
    dipendono da dove il README mette le sue parole.
    """
    con_eccezione = (
        "If the server is unreachable, reads fall back to their own embedded "
        "store, while the writes that mutate the shared corpus refuse instead."
    )
    senza_eccezione = (
        "If the server is unreachable, each falls back to its own embedded "
        "store (fail-soft, never a crash). Writes are idempotent."
    )
    assert _DICHIARA_L_ECCEZIONE.search(con_eccezione), (
        "il righello non riconosce la frase che dichiara l'eccezione: da qui in "
        "poi il suo «manca» non vuol dire niente, perche' non saprebbe vederla "
        "nemmeno quando arriva."
    )
    assert not _DICHIARA_L_ECCEZIONE.search(senza_eccezione), (
        "il righello si accende sulla riga com'e' oggi, che l'eccezione NON la "
        "dichiara: sarebbe verde per la ragione sbagliata."
    )
