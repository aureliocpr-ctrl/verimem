"""Elenca le celle del registro che QUALCUN ALTRO puo' firmare in un minuto.

Nasce da un dato, non da un'idea: le celle che dichiarano `rifallo con:` sono
passate da 1 a 17 in una sera, ma le firme restano tutte di una sola istanza.
La cura era stata adottata e la firma no ⇒ l'attrito non era piu' «la cella non
dice come rifarla», era «non so QUALI celle posso firmare senza rileggerle
tutte». Questo script toglie quel passo: un comando, la lista, il comando da
incollare.

Uso:
    python scripts/celle_da_firmare.py --io <NomeAgente>     # es. --io Varco

Stampa solo le celle NON tue e NON gia' firmate da te, con la riga
`rifallo con` estratta. Esce 0 sempre: e' un elenco, non un cancello.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

REGISTRO = pathlib.Path("docs/stato-reale/00-ESAME.md")
#: una FIRMA vera e' preceduta da un marcatore di chiusura. Senza questo
#: vincolo il conteggio include le celle che PARLANO di firme e si conta da
#: sola (misurato due volte il 29/08: davi 2 celle «a due firme» che nessuno
#: aveva firmato).
#: fra il marcatore e la parola «firma» ci sta altro: chi firma DECORA, e
#: `✅⚠️ **firma @…` o `✅🪞 **firma @…` non matchano se qui si pretende
#: `\s*`. Misurato il 01/09: DUE firme vere (`W7-36`, `W7-51`) risultavano
#: inesistenti per questo, e la cella tornava nell'elenco delle firmabili
#: come se nessuno l'avesse verificata. Il difetto è ricorsivo — chi ha
#: scritto questo regex ha poi decorato le proprie firme rendendole
#: invisibili al proprio strumento. I sei caratteri non alfanumerici bastano
#: per una o due emoji e non arrivano a un'altra parola.
FIRMA = re.compile(r"(?:✅|✍️|_)[^A-Za-z0-9|]{0,6}(?:\*\*)?"
                   r"(?:2ª |seconda )?firma @([A-Za-z0-9_-]+)")
#: Chi firma ha DUE nomi — la sigla e il nome proprio — e il conteggio grezzo
#: li tratta come due persone: `W7-14` risulta «a due firme» con `['ws2',
#: 'Varco']`, che e' una sola. Misurato il 31/08 sul registro: delle 6 celle
#: che un conteggio ingenuo dava a due firme, ZERO era una doppia controfirma
#: vera. Le quattro coppie qui sotto sono quelle viste firmare; le altre
#: istanze non compaiono ancora con un nome proprio e non si indovinano.
ALIAS = {"varco": "ws2", "galileo": "ws3", "paragone": "ws4", "lanterna": "ws7"}
#: `@X` e `@Nome` NON sono firmatari: vengono dalle celle che SPIEGANO come si
#: firma, e il criterio matcha il segnaposto scritto per documentarlo. E' la
#: forma piu' insidiosa del difetto nel misuratore — il testo che descrive il
#: criterio soddisfa il criterio (@ws4, 31/08: 2 casi su 6, `W2-117` e
#: `W2-183`). Resta scoperto il caso in cui e' l'INTERA cella a documentare la
#: convenzione: li' il segnaposto e' un nome vero citato, e non si distingue
#: senza leggere.
SEGNAPOSTI = {"x", "nome", "tuonome", "agente"}


def firmatari(riga: str) -> set[str]:
    """I firmatari DISTINTI di una riga: alias normalizzati, segnaposti fuori.

    Senza normalizzare, `['Varco', 'Varco']` conta due e `['ws2', 'Varco']`
    pure — e una cella con una firma sola si legge come verde.
    """
    return {ALIAS.get(f.lower(), f.lower()) for f in FIRMA.findall(riga)
            } - SEGNAPOSTI


#: CONVENZIONE B, ratificata il 31/08 (FIRMA-AB). Una controfirma non vive
#: solo dentro la riga verificata (convenzione A): puo' essere una CELLA
#: PROPRIA il cui titolo e' «SECONDA FIRMA su <ID|SHA>», con la riesecuzione
#: dentro. Il contatore vedeva solo A, quindi dichiarava «NESSUNA firma» su
#: celle che erano state verificate davvero — e chi le aveva verificate in B
#: NON deve rifirmare in A: la firma vale, era il contatore a essere indietro.
FIRMA_B = re.compile(r"^\| ([A-Za-z0-9-]+) \| \*{0,2}[^|]{0,14}?SECONDA FIRMA\b"
                     r"([^|]{0,90})", re.I)
#: dentro il titolo di una cella B, CHI viene verificato: un ID di cella e'
#: attribuibile, uno SHA di commit no — la cella firmata non e' nominata.
BERSAGLIO = re.compile(r"\b(LANT-\d+|W\d-\d+)\b")
#: Uno SHA nel titolo e' un bersaglio LEGITTIMO — il contratto dice «SECONDA
#: FIRMA su <ID|SHA>» — ma NON identifica una cella: `5ea77b6d` e' nominato da
#: quattro celle diverse, e attribuire la controfirma a tutte e quattro
#: gonfierebbe il contratto. Quindi si riconosce (non e' un errore di chi l'ha
#: scritta) e si tiene da parte, invece di contarla o di tacerla.
SHA_BERSAGLIO = re.compile(r"\b([0-9a-f]{8})\b")


def autore_di(riga: str) -> str:
    """Chi ha SCRITTO la cella: l'ottava colonna, non un `| wsN |` cercato a caso.

    Il regex `\\| (ws\\d) \\|` perdeva ogni autore che non si chiami `wsN` —
    `lead-audit` fra questi — e con lui la controfirma che aveva dato
    (`LANT-145` su `LANT-122`, misurato 02/09 01:20). Misurate anche le
    conseguenze dell'altro verso: **34 celle hanno autore non-`wsN` e ZERO
    portano la firma del proprio autore**, quindi il difetto non stava
    producendo autofirme contate come controfirme. Restava latente.
    """
    campi = riga.split("|")
    if len(campi) < 9:
        return ""
    a = campi[7].strip().lower()
    return ALIAS.get(a, a)


def controfirme_b(righe: list[str], con_sha: bool = False):
    """Le controfirme in convenzione B, indicizzate per cella BERSAGLIO.

    Ritorna anche l'elenco delle celle B che NON si sono potute attribuire, e
    ritorna l'elenco e non un totale perche' un numero nudo non dice quali
    guardare. Sono controfirme REALI, e tacerle le farebbe sparire due volte:
    dal totale e dalla cella che verificano.

    Due modi di non essere attribuibile, misurati il 01/09 sul registro:
      · il titolo nomina uno SHA di commit invece di un ID di cella (`LANT-86`
        su `5ea77b6d`) — la riga verificata non e' nominata;
      · la riga non porta l'autore nella forma `| wsN |` che il registro usa
        (`LANT-105`, `LANT-108`) — e la prima versione di questa funzione le
        SCARTAVA IN SILENZIO con un `continue`, cioe' proprio il taglio muto
        contro cui il resto di questo script mette in guardia.
    L'autore NON si indovina dal prefisso dell'ID: `LANT-` suggerisce ws7 ma
    suggerire non e' misurare, e una controfirma attribuita a chi non l'ha
    data e' peggio di una non contata.
    """
    per_cella: dict[str, set[str]] = {}
    orfane: list[str] = []
    su_sha: list[tuple[str, str]] = []
    for riga in righe:
        m = FIRMA_B.match(riga)
        if not m:
            continue
        aut = autore_di(riga)
        bersagli = set(BERSAGLIO.findall(m.group(2)))
        if not bersagli:
            sha = SHA_BERSAGLIO.findall(m.group(2))
            (su_sha.append((m.group(1), sha[0])) if sha
             else orfane.append(m.group(1)))
            continue
        if not aut:
            orfane.append(m.group(1))
            continue
        for b in bersagli:
            per_cella.setdefault(b, set()).add(aut)
    return (per_cella, orfane, su_sha) if con_sha else (per_cella, orfane)


#: Comandi che la disciplina della copia CONDIVISA vieta: otto istanze e un
#: solo albero, dove uno `stash pop` tocca il lavoro non committato delle
#: altre sette. La ricetta di una cella e' testo scritto da un'ALTRA, e puo'
#: CITARE un comando invece di proporlo — `LANT-41` racconta uno stash pop
#: gia' avvenuto, non chiede di rifarlo. Misurato il 30/08: 1 ricetta su
#: 139. Questo resta un elenco e non un cancello (vedi il docstring): la
#: riga si stampa lo stesso, con l'avviso accanto.
VIETATO = re.compile(r"git\s+(stash|checkout\s+--|reset|clean|push)"
                     r"|--no-verify|rm\s+-rf|requalify\s+--apply", re.I)

RIFALLO = re.compile(r"🔎\s*\*{0,2}(?:rifallo con|Rifallo con)\*{0,2}[^`]*`([^`]+)`")
#: gli ID del registro NON sono di una forma sola: accanto a `W2-57` ci sono
#: `LANT-41` e le celle NUMERICHE (`| 12 |`). Misurato il 30/08: le numeriche
#: sono 86, e le scrivono soprattutto le istanze che ricevono MENO controfirme
#: (ws6 16, ws8 6, ws5 5). Riconoscendo un solo formato questo elenco le
#: teneva fuori TUTTE, cioe' nascondeva proprio il lavoro che aveva piu'
#: bisogno di essere offerto. Un marcatore non marca chi non lo conosce.
#: e c'e' una QUARTA forma, segnalata da @ws4 il 01/09: l'ID con SUFFISSO
#: letterale (`W7-20b`), che nasce quando una cella viene spezzata in due
#: dopo essere stata scritta. Sul registro ne esiste UNA sola, e il regex
#: senza suffisso la perdeva in silenzio — poco, ma e' esattamente il tipo di
#: cella che nessuno rivede, perche' non compare in nessun elenco. Il
#: suffisso e' di UNA lettera: allargarlo di piu' farebbe entrare righe che
#: celle non sono.
CELLA = re.compile(r"^\| ((?:[A-Z]+\d*-)?\d+[a-z]?) \| ([^|]*)\|")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--io", required=True,
                    help="il tuo nome agente (le tue celle e le tue firme sono escluse)")
    ap.add_argument("--tutte", action="store_true",
                    help="mostra anche le celle senza riga `rifallo con`")
    a = ap.parse_args()
    if not REGISTRO.exists():
        print(f"NON RIUSCITO: {REGISTRO} non c'e' — lancia dalla radice del repo")
        return 2
    io_l = a.io.lower()
    righe = REGISTRO.read_text(encoding="utf-8").split("\n")
    trovate = 0
    #: quante ne sto SCARTANDO perche' non dicono come rifarle. Senza
    #: questo numero l'elenco si legge come «ecco tutto il lavoro che
    #: puoi firmare», mentre e' «ecco la parte che qualcuno ha reso
    #: rifacibile»: un taglio silenzioso si legge come copertura piena.
    #: Misurato il 30/08 sulle celle W2: 47 scartate su 108 (43,5%), e
    #: chi chiedeva le firme — io — non lo sapeva.
    nascoste = 0
    b_per_cella, b_orfane, b_su_sha = controfirme_b(righe, con_sha=True)
    for riga in righe:
        m = CELLA.match(riga)
        if not m:
            continue
        cid, titolo = m.group(1), m.group(2).strip()
        #: A OPPURE B: una cella e' verificata se porta la firma nella propria
        #: riga o se qualcun altro le ha dedicato una cella «SECONDA FIRMA».
        firme = firmatari(riga) | b_per_cella.get(cid, set())
        io_n = ALIAS.get(io_l, io_l)
        if io_n in firme:            # gia' firmata da me, sotto uno dei due nomi
            continue
        autore = autore_di(riga)
        if autore and autore == io_n:
            continue
        #: la firma dell'AUTORE non e' una controfirma: la cella resta da
        #: verificare anche quando chi l'ha scritta si e' firmato in fondo.
        if autore:
            firme = firme - {autore}
        rif = RIFALLO.search(riga)
        if not rif and not a.tutte:
            nascoste += 1
            continue
        trovate += 1
        #: «controfirma» e non «firma»: quello che resta qui e' chi ha
        #: VERIFICATO, non chi ha scritto. Il nome vecchio faceva leggere come
        #: verde una cella firmata solo dalla propria autrice.
        stato = (f"{len(firme)} controfirma/e" if firme
                 else "NESSUNA controfirma")
        print(f"\n  {cid}  [{stato}]  {titolo[:74]}")
        if rif:
            _cmd = rif.group(1)
            # La ricetta e' il PRIMO backtick dopo «rifallo con», e quando
            # quel backtick e' lontano appartiene a un'altra frase: LANT-33
            # rimanda a un blocco in cima al file e il primo backtick che
            # segue e' una variabile citata 245 caratteri piu' in la',
            # stampata come se fosse il comando da eseguire. Misurato il
            # 30/08: 12 ricette su 148 (8%), e una a distanza NEGATIVA —
            # il backtick veniva da prima della riga stessa.
            _q = riga.lower().find("rifallo con")
            _d = riga.find("`" + _cmd + "`", _q) - _q if _q >= 0 else 999
            if 0 <= _d <= 70:
                print(f"      $ {_cmd[:110]}")
            else:
                # niente falso `$`: si stampa cio' che la cella DICE.
                _testo = riga[_q:_q + 150].split("`")[0] if _q >= 0 else ""
                print(f"      ↪ {_testo.strip()[:110]}")
                print("      ⚠️  non e' un comando: la cella rimanda "
                      "a un altro punto. Leggila prima di eseguire.")
            if VIETATO.search(_cmd):
                print("      ⛔ NON ESEGUIRLA COSI': contiene un comando "
                      "che la disciplina della copia condivisa vieta. "
                      "Probabile CITAZIONE nel racconto, non una ricetta.")
    coda = "." if a.tutte else " (con la ricetta gia' pronta)."
    print(f"\n  ⇒ {trovate} celle che puoi firmare{coda}")
    if b_per_cella or b_orfane:
        print(f"  📋 convenzione B: {len(b_per_cella)} celle risultano "
              f"verificate da una cella «SECONDA FIRMA» dedicata, e sono "
              f"gia' escluse da questo elenco.")
    if b_su_sha:
        #: NON e' un errore di chi le ha scritte: il contratto ammette lo SHA.
        #: Ma uno SHA non nomina UNA cella, e attribuirle a tutte quelle che lo
        #: citano gonfierebbe il contratto — cosa peggiore del non contarle.
        print(f"  ⚠️  {len(b_su_sha)} celle «SECONDA FIRMA» valide ma su SHA, "
              "non su un ID di cella — "
              + ", ".join(f"{c} su {s}" for c, s in b_su_sha)
              + ". Sono controfirme REALI e il contratto le ammette, ma non "
              "dicono QUALE riga verificano: chi le ha scritte aggiunga anche "
              "l'ID, e la cella passa a due firme.")
    if b_orfane:
        print(f"  ⚠️  {len(b_orfane)} celle «SECONDA FIRMA» NON attribuibili "
              f"— {', '.join(b_orfane)} — perche' non nominano ne' un ID ne' "
              "uno SHA, o non portano l'autore nell'ottava colonna. Sono "
              "controfirme REALI che non contano per nessuna cella.")
    if nascoste:
        _quota = 100 * nascoste / (trovate + nascoste)
        print(f"  ⚠️  {nascoste} celle NON mostrate: non dicono come "
              f"rifarle ({_quota:.0f}% del totale). Non sono firmabili da "
              "nessuno finche' non portano una riga `🔎 rifallo con`. "
              "Vedile con --tutte.")
    #: «in fondo alla cella» e' AMBIGUO e ha rotto undici celle il 01/09:
    #: chi lo legge appende dopo il `|` di chiusura, la riga smette di
    #: chiudere e l'ultima colonna — il REGIME — non si rende piu'. Il
    #: contenuto resta (le pipe restano 9, la mediana delle celle sane), ma
    #: `conta_celle_esame.py` la conta fra le TRONCATE, dove finisce insieme
    #: alle righe a cui il regime manca DAVVERO: stesso sintomo, due cause,
    #: due cure diverse. L'istruzione qui sotto dice il posto esatto.
    print("  Rifai il banco, poi aggiungi la firma DENTRO l'ultima colonna,")
    print("  cioe' PRIMA del `|` che chiude la riga (non dopo: la riga deve")
    print("  continuare a finire con `|`):")
    print(f"      ✅ **firma @{a.io} <ora>** — rifatta, <cosa hai ottenuto>.")
    print("  ⚠️ Se i numeri NON tornano scrivilo lo stesso: ritirare vale piu' che confermare.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
