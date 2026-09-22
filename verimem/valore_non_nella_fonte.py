"""Il controllo DETERMINISTICO claim↔fonte che al gate mancava.

IL DIFETTO CHE LO MOTIVA, misurato e riprodotto due volte: stessa fonte, stesso
giudice, due popolazioni di claim falsi::

    A  inventa un'ENTITÀ (fornitore Verdi, ordine 91)   ammessi 0/4   il moat li ferma
    B  DETTAGLIO non detto su un'entità VERA            ammessi 5/5   con g 97,1–99,5

        «L'ordine 77 conteneva 40 pezzi.»                   g=97.1
        «Il fornitore Bianchi ha partecipato per 45 minuti» g=98.7
        «L'ordine 77 vale 1200 euro.»                       g=98.0

🔑 (B) è la forma in cui un LLM allucina davvero: non inventa un fornitore che
non esiste, inventa la durata, l'importo, il numero di pezzi. Ed entra col
punteggio più alto del sistema.

LA DIAGNOSI HA UN INDIRIZZO PRECISO::

    «Nessun rilevatore L1 riceve la fonte. Il confronto claim↔fonte esiste in
     UN SOLO posto: dentro il cross-encoder, che è esattamente quello che
     sbaglia su questa classe.
        L1  vede il claim, NON la fonte
        L4  vede claim + fonte, ma confonde PLAUSIBILE con IMPLICATO
     ⇒ manca un controllo DETERMINISTICO claim↔fonte»

e il numero che la rende strutturale: il 91,8% dei verdetti del moat sta
agli estremi (1324 su 1673 sopra 99) — **nessuna soglia può separare**, perché
il difetto non è dove si taglia: è che il giudice dà lo stesso punteggio a un
fatto vero e a un dettaglio inventato.

QUESTO MODULO NON USA MODELLI. Confronta i valori numerici del claim con quelli
della fonte, e non decide se il claim sia vero: dice che **un numero che la
fonte non contiene non è un numero verificato**.

⚠️ LIMITI DICHIARATI, entrambi misurati e non aggirati:
  * copre i valori in CIFRE. «durata due ore» e «alle nove» sono numeri in
    LETTERE e restano scoperti. Coprirli vuol dire una lista di parole per
    lingua — la classe che in questa casa è caduta sei volte in una notte.
    Prima il pezzo deterministico; la lista solo se il numero la giustifica.
  * un ANNO nudo non è una quantità (lo esclude già `extract_quantities`): «il
    contratto scade nel 2027» non è un dettaglio inventato dello stesso genere,
    e il percorso delle date è un altro.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from .quantity_match import (
    _QUANT_RE,
    claim_span,
    extract_quantities,
    valori_scritti_a_parole,
)

__all__ = ["ValoreAssente", "valori_non_nella_fonte"]


def _numeri_come_scritti(testo: str) -> dict[float, str]:
    """``{valore: il numero COM'E' SCRITTO}`` per i numeri del claim.

    Legge ``_QUANT_RE`` sullo stesso ``claim_span`` che usa
    ``extract_quantities``: il legame valore→testo e' esatto PER COSTRUZIONE,
    non ritrovato a posteriori. E' la differenza fra conservare e indovinare,
    ed e' il motivo per cui questa strada e' stata scelta contro l'alternativa
    di ricercare il token al punto di stampa.

    ⚠️ LIMITE DICHIARATO: se due scritture DIVERSE danno lo stesso ``float``
    («2607.2676» e «2607.26760» nello stesso claim) qui ne resta una — la
    prima. Non e' l'ambiguita' che affossa la ricerca a posteriori: la' i
    candidati sono tutti i numeri del testo, qui solo quelli che collassano
    sullo stesso valore, e fra quelli il gate non ha comunque nulla da
    distinguere: sono lo stesso numero.
    """
    fuori: dict[float, str] = {}
    for m in _QUANT_RE.finditer(claim_span(testo)):
        try:
            v = float(m.group(1))
        except ValueError:      # pragma: no cover — la regex cattura cifre
            continue
        fuori.setdefault(v, m.group(1))
    return fuori


@dataclass(frozen=True)
class ValoreAssente:
    """Un valore che il claim afferma e la fonte non contiene.

    ``testo`` E' IL NUMERO COM'E' SCRITTO NEL CLAIM, e non e' un lusso: senza,
    il gate stampava una cifra che l'utente non aveva mai scritto. Il caso, reale
    e incontrato usando il prodotto (id=21b5710c46f5)::

        claim  «Il paper Metis arXiv 2607.26760 elenca fra le affiliazioni ...»
        gate   «il claim afferma un valore che la fonte non contiene: 2607.27»

    Il ``2607.27`` non era nel claim ne' nella fonte: nasceva da ``f"{v:g}"``,
    che tiene SEI cifre significative e arrotonda. Corrompe ogni identificatore:
    ``1706.03762`` (Attention is all you need) diventa ``1706.04``.

    🔑 E NON BASTAVA STAMPARE PIU' CIFRE: lo zero finale muore prima, nella
    ``float()`` — ``2607.26760 -> 2607.2676`` — quindi ``:.15g`` darebbe ancora
    la cifra sbagliata. Questa strada e' stata scelta contro l'alternativa di
    ricostruire il token a valle: «(B) non e' rischiosa, e' IMPOSSIBILE: chiede
    una funzione inversa che non esiste; non puo' RITROVARE il token, puo' solo
    INDOVINARE quale pezzo di testo lo abbia generato» — e il suo referto di
    quella sera cita CINQUE id arXiv nello stesso claim, tutti della stessa
    forma. Qui invece il testo non si indovina: si conserva quando lo si legge.
    """
    valore: float
    unita: str
    #: vuoto solo per i costruttori che non lo passano: nessuno, oggi, fuori da
    #: questo modulo (verificato: `grep ValoreAssente(` non da' altri esiti).
    testo: str = ""

    def come_scritto(self) -> str:
        """Il numero da mostrare a chi legge: il suo, se ce l'abbiamo.

        Il ripiego su ``:g`` resta per i (nessuni) costruttori che non passano
        ``testo``, ed e' deliberatamente identico al comportamento vecchio: un
        ripiego che cambia anche il resto nasconderebbe quando viene usato.
        """
        return self.testo or f"{self.valore:g}"


_DECIMALI_RE = re.compile(r"(?<![\w.])\d+[.,](\d+)")


def _tolleranza_dichiarata(testo: str, valore: float) -> float:
    """±mezza unità dell'ultima cifra che il claim SCRIVE.

    IL FALSO POSITIVO CHE LA MOTIVA, incontrato usando il prodotto e non
    cercandolo — al primo fatto vero salvato dopo la cura::

        fonte «durata 443.0485324859619»  ·  claim «443 secondi»
        -> QUARANTINATO, con grounding 100.0

    Troncare un decimale è la forma più comune in cui un umano riporta una
    durata: il falso positivo è ad alta frequenza.

    🔑 IL CRITERIO, e le due alternative cadute prima di arrivarci:
      * **prefisso letterale** («443» sta dentro «443.048…»): ammette anche
        «44», che è un altro numero. veri 6/10, falsi fermati 8/9.
      * **tolleranza relativa ≤1%**: 19/19 sugli arrotondamenti, poi cade 4
        volte su 4 dove l'1% è una differenza VERA — «505» da «500 mg» è
        un'altra dose, «4.03» da «4 per cento» un altro tasso. *L'1% di una
        durata è rumore, l'1% di una dose è un errore clinico.*

    Un numero riportato con k decimali **dichiara la propria precisione**:
    ``0.5 * 10^-k``. Non è una costante che abbiamo scelto noi — la sceglie chi
    scrive il numero, ed è il modo standard in cui scienza e ingegneria
    trattano un valore riportato. Per questo regge su domini che nessuno di noi
    ha previsto: non c'è niente da ri-calibrare.

    Si contano i decimali SCRITTI e non quelli del float: ``443`` e ``443.00``
    sono lo stesso valore e due precisioni diverse, e il float non lo ricorda.
    Fallback prudente a ``0.5`` (intero) quando la cifra non si ritrova nel
    testo — la stessa tolleranza che il claim si attribuirebbe scrivendola
    senza decimali.
    """
    intero = int(valore) if float(valore).is_integer() else valore
    for m in _DECIMALI_RE.finditer(testo):
        try:
            if abs(float(m.group(0).replace(",", ".")) - valore) < 1e-12:
                return 0.5 * (10.0 ** -len(m.group(1)))
        except ValueError:  # pragma: no cover - gruppo non numerico
            continue
    del intero
    return 0.5


#: I quantificatori di assenza. ⚠️ È UNA LISTA, e le liste in questa casa sono
#: la classe di errore più ricorrente — quindi va detto perché qui è accettabile
#: e dove smette di esserlo.
#:
#: · L'assenza è **lessicale per natura**: a differenza delle date (`8月10日`) o
#:   della coda verbale giapponese, non esiste un criterio posizionale che dica
#:   «qui il testo nega una quantità». Se qualcuno ne trova uno, batte questa riga.
#: · Il costo di una voce mancante è **zero comportamento nuovo**: la lingua non
#:   coperta si comporta come oggi, cioè il claim viene fermato. Non si rompe
#:   niente, semplicemente non si guadagna.
#: · Il valore aggiunto è **uno solo, lo zero**: una voce di troppo non può
#:   inventare quantità arbitrarie, al massimo fa passare un claim che dice `0`.
#:
#: ⚠️ LIMITE DICHIARATO: copre italiano e inglese. Le altre lingue del perimetro
#: — francese «aucun», spagnolo «ninguno», tedesco «kein», russo «нет» — NON
#: sono qui, e il loro claim resta fermato come oggi. Aggiungerle è una riga a
#: testa; non l'ho fatto perché non ho un banco per misurarne i falsi.
_ASSENZA_RE = re.compile(
    r"(?<![\w-])(?:nessun[oa]?|neanche\s+un[oa]?|zero|none|no)(?![\w-])",
    re.IGNORECASE)


def _dichiara_un_assenza(testo: str) -> bool:
    """La fonte nega esplicitamente una quantità?

    Serve a rispondere a una domanda sola — «il valore 0 compare in questa
    fonte?» — e non a estrarre una misura: per questo non restituisce un numero
    ma un sì/no, e chi la chiama aggiunge lo zero all'insieme dei valori
    presenti invece di fabbricare una quantità.
    """
    return bool(_ASSENZA_RE.search(testo or ""))


# ── LO STESSO TESTO, LETTO SUI DUE LATI, DEVE DARE LO STESSO NUMERO ──────────
#
# I due lati si leggono con due modalità: il claim con `extract_quantities(p)`,
# la fonte con `extract_quantities(s, come_fonte=True)`. Sulle versioni attaccate
# a un nome le due letture divergono, e la divergenza va nel verso peggiore —
# il lato CLAIM fabbrica un valore che il lato FONTE non produce mai::
#
#     "… click-8.4.2."    claim ('', 4.2)     fonte —            inventato
#     "… pytest-8.4.1."   claim ('', 4.1)     fonte —            inventato
#     "… python-3.12."    claim ('', 12.0)    fonte ('', 3.12)   due numeri diversi
#     "cli.py-354-"       claim —             fonte ('', 354.0)  verso innocuo
#
# ⇒ Con `click-8.4.2` su ENTRAMBI i lati il veto scattava su un valore che nella
# fonte c'è ALLA LETTERA, e il fatto usciva quarantinato col giudice a 99,98.
# È la forma di ogni riga `Successfully installed`, cioè di ogni misura di
# dipendenza che scriviamo.
#
# ⚖️ IL CRITERIO È TESTUALE, NON NUMERICO, ed è per questo che non spegne il
# veto: si perdona un valore solo se il TOKEN che l'ha prodotto compare
# verbatim nella fonte. Una versione INVENTATA non è nella fonte, quindi non
# viene perdonata e resta fermata — c'è un controllo positivo che lo pin-a.
#
# 📌 E sta QUI e non in `extract_quantities`: è la stessa scelta già dichiarata
# sopra per «nessun X vale 0». Toccare l'estrattore alimenterebbe i sei moduli
# del gate che lo leggono; qui l'equivalenza vive solo nel confronto.
_TOKEN_CON_VERSIONE = re.compile(
    r"(?<![\w.-])[A-Za-z][\w.]*-\d+(?:\.\d+)+(?![\w-])")


def _valori_da_token_che_la_fonte_contiene(proposition: str, source: str) -> set[float]:
    """I valori che il lato claim estrae da token presenti verbatim nella fonte."""
    perdonati: set[float] = set()
    for m in _TOKEN_CON_VERSIONE.finditer(proposition or ""):
        token = m.group(0)
        if token and token in (source or ""):
            for _u, v in extract_quantities(token):
                perdonati.add(v)
    return perdonati


#: `1,5 x 10^3` · `4 x 10^-4` · `2,5 × 10^5` · `6 * 10^4`. Il segno di
#: moltiplicazione ha tre forme in giro per i testi veri (`x` ascii, `×`
#: unicode, `*`) e l'esponente puo' essere negativo. La mantissa ammette la
#: virgola perche' e' come l'italiano la scrive.
#:
#: ⚠️ I QUANTIFICATORI SONO LIMITATI, e non e' cosmesi: con `\d+` su un testo
#: che arriva dall'esterno questa e' una `py/polynomial-redos` — un claim con
#: migliaia di zeri consecutivi fa lavorare il motore in tempo polinomiale, e il
#: gate legge testo di cui non controlla la forma. I limiti coprono ogni numero
#: reale (una mantissa di 15 cifre, un esponente di 4) e rendono il
#: costo lineare. Misurato: l'avviso CodeQL alto sparisce e le celle del banco
#: non cambiano di una cifra.
_SCIENTIFICA_RE = re.compile(
#: ⚠️ I QUANTIFICATORI SONO SALITI DA 15 A 40, e la ragione e' che il tetto
#: vero ora sta ALTROVE. Il 15 era stato scelto per chiudere una `polynomial
#: ReDoS` («coprono ogni numero reale»), ma tagliava mantisse legittime: una
#: misura con 18 cifre decimali non veniva nemmeno riconosciuta. Il costo resta
#: lineare perche' il quantificatore resta LIMITATO, e cio' che protegge il
#: confronto e' `_CIFRE_MASSIME` sul RISULTATO, dove il numero entra davvero.
    r"(?<![\w.])(\d{1,40}(?:[.,]\d{1,40})?)[ 	]{0,4}[x×*][ 	]{0,4}10\^(-?\d{1,4})")


#: Quante cifre puo' avere il numero ESPANSO. Non e' una stima: e' il numero che
#: entra nel confronto claim-fonte, e oltre questa lunghezza non e' piu' una
#: misura che qualcuno ha scritto in una perizia — `10^9999` darebbe diecimila
#: cifre. Il valore piu' lungo osservato nei nostri banchi ha 18 cifre.
_CIFRE_MASSIME = 40


def _espandi_notazione_scientifica(testo: str) -> str:
    """Riscrive `1,5 x 10^3` come `1500`, lasciando intatto tutto il resto.

    Serve al solo confronto claim-fonte: il testo espanso non viene mai
    memorizzato ne' mostrato al posto dell'originale, tranne che nel nome del
    valore accusato — dove `2500` e' comunque piu' chiaro di `2.5` per chi
    legge l'avviso.

    ⚠️ NON tocca la notazione con esponente in apice (`10³`) ne' `1.5e3`:
    nessuna delle due compare nei casi misurati, e una regex che le prendesse
    tutte rischierebbe di catturare codici prodotto. Quando qualcuno le
    misurera', si aggiungono qui con la loro cella di banco.
    """
    if not testo or "10^" not in testo:
        return testo

    def _sost(m: re.Match) -> str:
        # ⚠️ ARITMETICA ESATTA, E IL PERCHE' NON E' L'ELEGANZA. Con `float` il
        # prodotto INVENTAVA un valore sopra le 15 cifre significative:
        # `123456789012345 x 10^3` usciva `123456789012344992`. Un valore
        # mancante si nota — il layer accusa e chi legge va a guardare — un
        # valore inventato no: il confronto claim-fonte avviene contro un numero
        # che non sta in nessuno dei due testi. `Decimal.scaleb` sposta la
        # virgola senza toccare le cifre.
        try:
            valore = Decimal(m.group(1).replace(",", ".")).scaleb(int(m.group(2)))
        except (ValueError, ArithmeticError):  # pragma: no cover — regex ristretta
            return m.group(0)
        # ⚠️ IL TETTO STA SUL RISULTATO, non sul tipo. Con l'aritmetica esatta
        # `10^9999` si espanderebbe DAVVERO, in diecimila cifre che finirebbero
        # nel testo dato al confronto. Prima non succedeva per un motivo
        # accidentale (il float andava in overflow) e il commento di questo
        # modulo lo raccontava al contrario — «un esponente di 4: 10^9999» —
        # mentre `1,5 x 10^9999` non e' mai stato espanso. Ora il limite e'
        # esplicito, e oltre il limite il ripiego resta il testo INTATTO.
        scritto = format(valore, "f")
        if len(scritto.lstrip("-").replace(".", "")) > _CIFRE_MASSIME:
            return m.group(0)
        # `%g` scriverebbe 1500 come `1500` ma 1e+20 come `1e+20`,
        # reintroducendo la notazione che stiamo togliendo; `format(…, "f")` no.
        if "." in scritto:
            scritto = scritto.rstrip("0").rstrip(".")
        return scritto or "0"

    return _SCIENTIFICA_RE.sub(_sost, testo)


#: Le estensioni che fanno di un token un NOME DI FILE. Sta qui e in nessun
#: altro posto: una lista scritta due volte diverge, e su questo prodotto e' gia'
#: successo tre volte in due giorni con una soglia. Il banco la LEGGE da qui
#: invece di ricopiarla, e prova ogni voce.
ESTENSIONI_DI_FILE = frozenset({
    "md", "py", "txt", "json", "yml", "yaml", "toml", "db", "log", "csv",
    "jsonl",
})

#: `00-ESAME.md` · `08-i-656-mb-le-quattro-strade.md` · `docs/stato-reale/77-x.md`.
#: Il token INTERO, non la sua testa: in «08-i-656-mb» il `656` sta nel titolo
#: quanto lo `08`, e con l'unita' attaccata verrebbe letto come una grandezza.
#: ⚠️ NIENTE REGEX COSTRUITA, e la ragione e' un carattere INVISIBILE: la prima
#: versione chiudeva il pattern con un `\b` dentro una stringa non raw, e quel
#: `\b` e' diventato un BACKSPACE (`\x08`) — la regex cercava un carattere di
#: controllo e non matchava mai. `print` del pattern non lo mostrava, `repr` si'.
#: Il riconoscimento e' per TOKEN: nessun backtracking e nessun ReDoS (questo
#: modulo ne ha gia' pagato uno il 20/09), e la lista resta in un posto solo.
def _e_un_nome_di_file(token: str) -> bool:
    """`00-ESAME.md` si', `README.md` no (niente da escludere), `22` no."""
    if "." not in token or not any(c.isdigit() for c in token):
        return False
    coda = token.rsplit(".", 1)[-1].strip(".,;:!?)\"'").lower()
    return coda in ESTENSIONI_DI_FILE


def _senza_i_nomi_di_file(testo: str) -> str:
    """Il testo con i nomi di file sostituiti da un segnaposto.

    ⚠️ IL PERIMETRO, e la ragione per cui la cura sta QUI e non in
    `extract_quantities`: quel parser lo usano sei moduli del gate, e insegnargli
    i nomi di file propagherebbe la conversione a tutti in silenzio — la stessa
    ragione gia' scritta sopra per la notazione scientifica. Qui si toglie una
    LETTURA al confronto claim-fonte, non una capacita' al parser, e il banco ha
    una cella che diventa rossa il giorno in cui questa cura si sposta di modulo.

    IL DIFETTO, misurato sullo store il 21/09: quattro fatti VERI col giudice fra
    99,69 e 99,98 trattenuti perche' il numero del nome di un DOCUMENTO non sta
    nella fonte — `03-cose-spente.md` accusava `03`, `00-ESAME.md` accusava `00`.
    La provenienza e' provata togliendo il nome dal claim: l'accusa sparisce.
    Raggio sul corpus (18 285 fatti): 134 letture cambiano, 0,73%, di cui 10 su
    fatti trattenuti. Una versione piu' larga — «un token con una barra e una
    cifra» — ne cambiava 4845 perche' prendeva `4/5` e `F#8/F#9`: percio'
    l'esclusione e' legata alla SOLA estensione nota.
    """
    if not testo or "." not in testo:
        return testo
    return " ".join("<FILE>" if _e_un_nome_di_file(t) else t
                    for t in testo.split())


def _radici_dei_nomi_di_file(testo: str) -> frozenset[str]:
    """Le radici dei nomi di file del testo: da `00-ESAME.md` esce `00-esame`.

    Serve per la NORMALIZZAZIONE fra i due testi: chi cita un documento non
    scrive sempre l'estensione, e `00-ESAME` e `00-ESAME.md` sono lo stesso
    nome. Confrontate a minuscole perche' la differenza di maiuscole in un
    titolo non e' un'affermazione su un numero.
    """
    fuori = set()
    for tok in (testo or "").split():
        pulito = tok.strip(".,;:!?)(\"'")
        if not _e_un_nome_di_file(pulito):
            continue
        radice = pulito.rsplit(".", 1)[0]
        if not radice:
            continue
        fuori.add(radice.lower())
        # ⚠️ ANCHE IL SOLO NOME, senza la cartella: la fonte scrive
        # `docs/stato-reale/00-ESAME.md` e il claim scrive `00-ESAME`. Senza
        # questa riga la normalizzazione riconosceva solo i nomi citati senza
        # percorso, ed erano DUE CELLE su cinque del banco di questa richiesta —
        # la mia prima versione era piu' STRETTA del difetto, per una volta, e
        # se ne e' accorto il presidio scritto da chi ha trovato il rovescio.
        base = radice.replace("\\", "/").rsplit("/", 1)[-1]
        if base:
            fuori.add(base.lower())
    return frozenset(fuori)


def _senza_i_nomi_normalizzati(testo: str, radici_dell_altro: frozenset[str]) -> str:
    """Il testo con i nomi di file tolti, CONTANDO come nome anche un token che
    coincide con la radice di un nome di file dell'ALTRO testo.

    ⚖️ PERCHE' NORMALIZZARE E NON CANCELLARE DALLA FONTE. La prima versione di
    questa cura toglieva i nomi di file da entrambi i testi, e quella simmetria
    ha aperto un difetto uguale e contrario: `00-ESAME` nel claim contro
    `00-ESAME.md` nella fonte accusava `00`, perche' dalla fonte il nome era
    stato cancellato e non poteva piu' assolvere nessuno. Misurato sulle coppie
    vere dello store: questa normalizzazione cambia 3 letture su 8876, tutte e
    tre accuse in meno, zero accuse nuove.

    ⚠️ E IL COSTO, misurato e non teorico: la strada scartata (smettere di
    pulire la fonte) cambiava QUATTRO letture, non tre. La quarta e' il fatto
    `2bf35b09d120`, dove il claim dice «estrae i numeri 07 e 13» e la fonte
    porta quei numeri solo dentro `..._2026-07-13.json`: li' l'assoluzione era
    giusta e questa cura non la da'. Il caso gemello — claim «il capannone
    misura 400 metri», fonte «vedi 400-piani.md» — ha la STESSA forma e il
    giudizio opposto, e nessuna regola sui token puo' distinguerli: per farlo
    servirebbe sapere se il claim parla del NOME o del MONDO. Si tiene l'accusa
    perche' un'accusa sbagliata si legge nella ricevuta, un perdono sbagliato
    no.
    La strada scartata era togliere la pulizia dalla FONTE. Lo avrebbe curato,
    e avrebbe aperto il suo rovescio: un valore che la fonte porta SOLO dentro
    un nome di file (claim «il capannone misura 400 metri», fonte «vedi
    400-piani.md») sarebbe stato perdonato. Oggi quel caso ha raggio zero sul
    corpus, e un raggio zero non e' una ragione: e' un debito che paga chi
    arriva dopo.
    Quindi non si cancella niente in piu' e non si smette di cancellare: si
    RICONOSCE che le due grafie dello stesso nome sono lo stesso nome. La fonte
    continua a non assolvere un numero che sta solo in un titolo, e il claim che
    nomina un documento senza estensione non viene piu' accusato del numero di
    quel documento.
    """
    if not testo:
        return testo
    if "." not in testo and not radici_dell_altro:
        return testo
    fuori = []
    for tok in testo.split():
        pulito = tok.strip(".,;:!?)(\"'")
        if _e_un_nome_di_file(pulito) or pulito.lower() in radici_dell_altro:
            fuori.append("<FILE>")
        else:
            fuori.append(tok)
    return " ".join(fuori)


def valori_non_nella_fonte(proposition: str, source: str) -> list[ValoreAssente]:
    """I valori numerici del claim che nella fonte non compaiono.

    Vuoto quando manca uno dei due testi: senza fonte non c'è nulla con cui
    confrontare, e inventarsi un verdetto è esattamente ciò che questo modulo
    esiste per impedire.

    Si confrontano i VALORI e non le coppie (unità, valore): «l'ordine 77» e
    «77 pezzi» portano lo stesso numero con unità diverse, e l'unità in un
    testo libero è la parola che segue — troppo fragile per farci poggiare un
    veto. Il valore no: o quel numero è nella fonte, o non c'è.
    """
    if not proposition or not source:
        return []
    # `00-ESAME.md` NON afferma che qualcosa vale zero: il numero e' nel TITOLO.
    # Si toglie da entrambi i testi, perche' un nome di file nella FONTE non
    # deve nemmeno perdonare un valore che il claim afferma davvero.
    _radici_claim = _radici_dei_nomi_di_file(proposition)
    _radici_fonte = _radici_dei_nomi_di_file(source)
    proposition = _senza_i_nomi_normalizzati(proposition, _radici_fonte)
    source = _senza_i_nomi_normalizzati(source, _radici_claim)
    # `1,5 x 10^3` E `1500` SONO LO STESSO NUMERO, e il layer non lo sapeva.
    # Misurato il 02/09 sul banco T5.1: sulla notazione scientifica il gate
    # fermava 6 VERI su 6, e in TRE casi a fermarli era questo layer DA SOLO
    # mentre il moat li approvava (`withheld_despite_judge`)::
    #
    #     caso 8   grounding 89,91   layers ['L4.1']
    #     caso 9   grounding 99,37   layers ['L4.1']
    #     caso 11  grounding 98,45   layers ['L4.1']
    #
    # perche' `_QUANT_RE` legge `1,5 x 10^3` come TRE numeri separati — 1.5, 10
    # e 3 — e nessuno dei tre sta nella fonte che dice `1500`.
    #
    # ⚠️ E IL DIFETTO NON ERA SOLO SUI VERI: prima di questa riga il claim FALSO
    # `2,5 x 10^3` produceva gli STESSI assenti del vero (`['2.5','3','10']`
    # contro `['1.5','3','10']`) ⇒ su questa classe il layer non distingueva
    # affatto le due popolazioni. Espandere la notazione non toglie un
    # controllo: gliene da' uno che non aveva.
    #
    # ⚖️ E STA QUI, NON IN `extract_quantities`, per la stessa ragione gia'
    # scritta piu' sotto per «nessun X vale 0»: insegnare la notazione al
    # parser propagherebbe la conversione ai sei moduli del gate che lo usano,
    # mentre qui l'equivalenza vive SOLO nel confronto claim-fonte e non entra
    # nel corpus.
    proposition = _espandi_notazione_scientifica(proposition)
    source = _espandi_notazione_scientifica(source)
    nel_claim = extract_quantities(proposition)
    if not nel_claim:
        return []
    # `come_fonte=True`: la fonte si legge INTERA. Le due potature di
    # `extract_quantities` sono giuste su un claim e sbagliate qui — misurato
    # il 16/08 su due casi con firme identiche e cause diverse:
    #
    #   la fonte finiva con «… Source: `veribench_…_2026-07-13.json`» e tutto
    #   cio' che seguiva il marcatore non veniva letto (righe 8+9 da sole
    #   davano [7.0, 13.0], le righe 7+8 davano [])
    #
    #   la fonte era un `git grep -C`: `cli.py:100:` dava 100, `cli.py-354-`
    #   dava nulla, perche' lettere-trattino-cifre e' la forma di un codice
    #   prodotto e veniva cancellata
    #
    # In entrambi il numero ERA nella fonte, il claim che lo citava sembrava
    # inventarselo, e L4.1 quarantinava un fatto vero contro un giudice a
    # 99,98. ⚖️ E il verso e' quello sicuro: leggere piu' fonte TOGLIE veti,
    # non ne mette — un errore qui costa un veto in meno, mai un falso ammesso.
    nella_fonte = {v for _u, v in extract_quantities(source, come_fonte=True)}
    # ⚠️ UNA FONTE CHE DICHIARA UN'ASSENZA CONTIENE LO ZERO, anche se non lo
    # scrive in cifre. Senza questa riga la stessa verità aveva due destini::
    #
    #     claim «il numero di success è 0»  ·  fonte «success: 0»      ammesso
    #     claim «il numero di success è 0»  ·  fonte «NESSUN SUCCESS»  fermato
    #
    # perché `extract_quantities("NESSUN SUCCESS")` restituisce l'insieme vuoto:
    # per il parser quella fonte non contiene alcun numero, quindi il claim
    # numerico risultava senza appiglio. Misurato su quattro forme (nessun /
    # nessuna / no+inglese), tutte e quattro fermate a torto.
    #
    # ⚖️ LA CURA STA QUI E NON IN `extract_quantities`, ed è una scelta
    # misurata. Insegnare al parser che «nessun X» vale 0 creerebbe quantità
    # dove il testo non ne misura nessuna — nel corpus reale «zero costo»,
    # «zero MCP», «Zero API» sono frequentissimi — e quelle quantità fantasma
    # finirebbero nei sei moduli del gate che leggono `extract_quantities`,
    # alimentando i rilevatori di conflitto. Qui invece l'equivalenza vive solo
    # nel confronto fra claim e fonte: non entra nel corpus e non crea nulla.
    #
    # 📌 E RESTA DENTRO IL CRITERIO CHE QUESTO MODULO DICHIARA DI SÉ — «o quel
    # numero è nella fonte, o non c'è». Una fonte che dice «zero costo» il
    # numero zero ce l'ha: se poi quello zero parli d'altro è la domanda di
    # L4.2, non di questo layer. I due ruoli restano separati.
    if _dichiara_un_assenza(source):
        nella_fonte.add(0.0)
    come_scritti = _numeri_come_scritti(proposition)
    # Vedi `_TOKEN_CON_VERSIONE` sopra: un valore estratto da un token che la
    # fonte contiene alla lettera non e' un valore che la fonte non contiene.
    perdonati = _valori_da_token_che_la_fonte_contiene(proposition, source)
    fuori: list[ValoreAssente] = []
    for u, v in sorted(nel_claim, key=lambda q: q[1]):
        if v in nella_fonte or v in perdonati:
            continue
        # UN ARROTONDAMENTO NON E' UN'INVENZIONE. Confronto STRETTO (`<` e non
        # `<=`): sulle 38 prove del banco l'inclusivo dava 37/38 e lo stretto
        # 38/38 — al bordo esatto due valori sono distinguibili, e ammetterli
        # sarebbe la stessa indulgenza che ha fatto cadere la tolleranza fissa.
        tol = _tolleranza_dichiarata(proposition, v)
        if any(abs(v - y) < tol for y in nella_fonte):
            continue
        fuori.append(ValoreAssente(valore=v, unita=u,
                                   testo=come_scritti.get(v, "")))
    return fuori


def assenti_che_la_fonte_scrive_a_parole(
        assenti: list[ValoreAssente], source: str) -> list[ValoreAssente]:
    """Quali fra i valori «assenti» la fonte porta scritti a PAROLE.

    Serve a DECLASSARE, mai ad ammettere: il chiamante sposta questi da veto ad
    avviso, e il fatto entra CON l'avviso. La differenza non e' formale — sta
    scritta a `anti_confab_gate.py:1897`, «un avviso non ha bisogno della
    popolazione opposta, un veto si'» — ed e' cio' che permette di tenere
    dentro `sei` e `venti` nonostante gli omonimi: un omonimo qui costa un
    avviso in piu' su un fatto che entra, non un numero inventato che passa.

    ⚠️ E NON si limita a toglierli dall'elenco. Lo stesso modulo ha gia' pagato
    questo errore altrove (riga 228 e commento a `L4.1-bis`): «i falsi negativi
    nascono convertendo i veri positivi in silenzio» — per chi legge il fatto,
    un valore ammesso da un confronto sbagliato e un valore ammesso da NESSUN
    confronto sono identici.
    """
    if not assenti or not source:
        return []
    a_parole = valori_scritti_a_parole(source)
    if not a_parole:
        return []
    return [a for a in assenti if a.valore in a_parole]
