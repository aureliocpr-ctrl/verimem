"""La varianza sugli scambi si spiega con QUANTI numeri porta ogni soggetto?

Ieri notte ho chiuso lasciando **una** osservazione esplicitamente NON misurata
(`1647cf98`). Su un dominio lo scambio di soggetto **passava** (fino a 73,0), su
un altro veniva **preso** (0,6-2,4), e avevo dichiarato la varianza
**inspiegata** invece di inventarle una storia. Ma le due fonti differivano per
piu' di una cosa, e la piu' vistosa era questa:

    dominio dove lo scambio PASSA   «Il workflow X ha avuto 50 run, di cui 0
                                     cancellati»      -> DUE numeri per soggetto
    dominio dove viene PRESO        «La citta' di X conta 390 mila abitanti»
                                                      -> UN numero per soggetto

L'IPOTESI: **non e' il dominio, e' quanti numeri ogni soggetto porta con se'.**
Con due numeri per soggetto la fonte contiene piu' coppie (soggetto, valore) fra
cui il giudice deve scegliere, e uno scambio ha piu' modi di sembrare vero.

IL DISEGNO, a variabile singola: **stesso dominio, stesso scambio, stessa
struttura di claim** — cambia SOLO se ogni soggetto porta **UN** numero o **DUE**.
Il secondo numero e' **irrilevante al claim**: non e' quello che lo scambio
sposta.

⚠️ **QUATTRO DOMINI, non uno.** Ieri ho ritirato cinque verdetti, tutti
costruiti su una fonte sola, tutti con i controlli in piedi. **La prima domanda
su un numero e' «su quante fonti DIVERSE?»** — qui la risposta deve essere
quattro prima che io dica qualunque cosa.

LA PREDIZIONE, scritta prima di eseguire:
    in **almeno 3 domini su 4**, lo scambio prende **piu' punti** nella
    variante a DUE numeri che in quella a UNO.

CONDIZIONE DI FALSIFICAZIONE: se lo scarto compare in **≤2 domini su 4**, o se
la direzione e' **incoerente** (in qualche dominio va al contrario),
**l'ipotesi cade** e la varianza torna a essere **INSPIEGATA** — e la dichiaro
tale, di nuovo, invece di cercarle una terza storia.

CONTROLLO CHE DEVE POTER FALLIRE, in **ogni** cella: il claim **vero** deve
stare alto e il valore **assente** basso. Una cella che non lo rispetta non
misura la cecita': misura una fonte scritta male, e viene **ESCLUSA e
dichiarata**, non contata di nascosto.

🔴 **ESITO: IPOTESI FALSIFICATA, e sotto c'e' una notizia BUONA per il prodotto.**

    dominio                numeri     vero  SCAMBIO  assente
    citta/abitanti         UNO        99.9      0.3      0.6
    citta/abitanti         DUE        99.9      0.4      0.7
    corsi/durate           UNO        99.9      1.1      0.7
    corsi/durate           DUE       100.0      0.9      0.8
    fornitori/denaro       UNO        99.9      1.8      0.5
    fornitori/denaro       DUE        99.9      1.7      0.6
    server/disponibilita   UNO       100.0      0.9      0.7
    server/disponibilita   DUE       100.0      0.8      0.6

**Controlli retti 4 domini su 4.** I delta fra UNO e DUE sono **±0,2** — cioe'
**rumore**, e in tre domini su quattro vanno pure nella direzione **contraria**.
⇒ **L'ipotesi dei due numeri e' morta**, e la varianza sugli scambi resta
**INSPIEGATA**. La dichiaro tale per la **seconda** volta invece di cercarle una
terza storia: ieri ne ho gia' ritirate quattro.

🟢 **MA GUARDANDO LA COLONNA CHE NON CERCAVO — e questa e' A FAVORE del
prodotto**: **tutti e otto gli scambi sono PRESI, sotto 2,0**, con `vero` a
99,9-100,0 e `assente` a 0,5-0,8. Su **quattro domini nuovi** il giudice
**distingue benissimo** un valore vero da uno predicato del soggetto sbagliato.

⇒ **Il conto complessivo si ribalta.** Sommando a ieri: su **cinque** domini
misurati, il giudice prende lo scambio **ovunque tranne che su UNA fonte** —
quella dei workflow, dove arrivava a **73,0**. Ieri quel caso sembrava la regola
e l'avevo gia' ristretto una volta (`1647cf98`); **oggi e' un outlier isolato in
mezzo a quattro domini che vanno bene.**

🔑 **E lo dico con la stessa prontezza con cui ieri ho detto il contrario.** Il
mio reperto di ieri sera suonava allarmante; quattro domini dopo, il quadro
onesto e' che **il giudice sugli scambi di soggetto funziona**, e che esiste
**una** fonte su cui non funziona e **non so perche'**. Un risultato che va a
favore del prodotto vale quanto uno che gli va contro, e va pubblicato con la
stessa velocita'.

⛔ **CHE COSA NON DICO**: non ho spiegato quella fonte. Le ipotesi provate e
cadute sono ormai **quattro** (forma, lingua, soggetto-clitico, due-numeri).
**Non ne propongo una quinta senza un disegno che la separi dalle altre.**

REGIME: store TEMPORANEO, giudice = cross-encoder locale su disco (nessuna API
esterna). Lo store di Aurelio NON e' toccato.

    python docs/stato-reale/banchi/ws3-due-numeri-per-soggetto-contro-uno.py
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

SOGLIA = 50.0

#: Per ogni dominio: (fonte a UN numero, fonte a DUE numeri, vero, scambio,
#: assente). Il claim NON cambia fra le due varianti: cambia solo la fonte.
DOMINI: list[tuple[str, str, str, str, str, str]] = [
    (
        "citta/abitanti",
        "La citta' di Bologna conta 390 mila abitanti. "
        "La citta' di Genova conta 560 mila abitanti.",
        "La citta' di Bologna conta 390 mila abitanti su 140 chilometri "
        "quadrati. La citta' di Genova conta 560 mila abitanti su 240 "
        "chilometri quadrati.",
        "La citta' di Genova conta 560 mila abitanti.",
        "La citta' di Bologna conta 560 mila abitanti.",
        "La citta' di Bologna conta 902 mila abitanti.",
    ),
    (
        "corsi/durate",
        "Il corso di base dura 12 ore. Il corso avanzato dura 30 ore.",
        "Il corso di base dura 12 ore e costa 400 euro. Il corso avanzato "
        "dura 30 ore e costa 950 euro.",
        "Il corso avanzato dura 30 ore.",
        "Il corso di base dura 30 ore.",
        "Il corso di base dura 88 ore.",
    ),
    (
        "fornitori/denaro",
        "Il fornitore Rossi ha fatturato 12500 euro. Il fornitore Bianchi ha "
        "fatturato 8400 euro.",
        "Il fornitore Rossi ha fatturato 12500 euro in 7 consegne. Il "
        "fornitore Bianchi ha fatturato 8400 euro in 4 consegne.",
        "Il fornitore Bianchi ha fatturato 8400 euro.",
        "Il fornitore Rossi ha fatturato 8400 euro.",
        "Il fornitore Rossi ha fatturato 6700 euro.",
    ),
    (
        "server/disponibilita",
        "Il server alfa ha una disponibilita' del 99 per cento. Il server beta "
        "ha una disponibilita' del 97 per cento.",
        "Il server alfa ha una disponibilita' del 99 per cento su 30 giorni. "
        "Il server beta ha una disponibilita' del 97 per cento su 30 giorni.",
        "Il server beta ha una disponibilita' del 97 per cento.",
        "Il server alfa ha una disponibilita' del 97 per cento.",
        "Il server alfa ha una disponibilita' del 41 per cento.",
    ),
]


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    os.environ["HIPPO_DATA_DIR"] = str(tmp)
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  REGIME: HIPPO_DATA_DIR={tmp}  (store di Aurelio NON toccato)")
    print("  giudice: cross-encoder locale su disco (nessuna API esterna)")
    print("  variabile singola: cambia SOLO quanti numeri porta ogni soggetto")
    mem = Memory(str(tmp / "duenum.db"))
    n = 0

    def s(claim: str, fonte: str) -> float:
        nonlocal n
        n += 1
        v = mem.add(claim, topic=f"dn/{n}", source=fonte,
                    validate="full").get("grounding_score")
        return -1.0 if v is None else float(v)

    print(f"\n  {'dominio':<22} {'numeri':<7} {'vero':>7} {'SCAMBIO':>8} "
          f"{'assente':>8}  controllo")
    print("  " + "-" * 70)
    scarti = 0
    validi = 0
    esclusi: list[str] = []
    contrari: list[str] = []
    for nome, f_uno, f_due, vero, scambio, assente in DOMINI:
        riga: dict[str, tuple[float, float, float]] = {}
        for et, fonte in (("UNO", f_uno), ("DUE", f_due)):
            v, sc, a = s(vero, fonte), s(scambio, fonte), s(assente, fonte)
            riga[et] = (v, sc, a)
            ok = v > SOGLIA and a < SOGLIA
            print(f"  {nome:<22} {et:<7} {v:>7.1f} {sc:>8.1f} {a:>8.1f}"
                  f"  {'ok' if ok else 'ESCLUSA'}")
        ok_uno = riga["UNO"][0] > SOGLIA and riga["UNO"][2] < SOGLIA
        ok_due = riga["DUE"][0] > SOGLIA and riga["DUE"][2] < SOGLIA
        if not (ok_uno and ok_due):
            esclusi.append(nome)
            continue
        validi += 1
        delta = riga["DUE"][1] - riga["UNO"][1]
        if delta > 0:
            scarti += 1
        else:
            contrari.append(f"{nome}({delta:+.1f})")

    print(f"\n  [1] CONTROLLI: domini validi {validi}/{len(DOMINI)}"
          + (f"  ESCLUSI: {', '.join(esclusi)}" if esclusi else ""))
    if validi < 3:
        print("      CONTROLLO CADUTO: meno di 3 domini superano vero-alto e")
        print("      assente-basso ⇒ misuro fonti scritte male, non l'ipotesi.")
        print("      NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    print(f"     domini in cui DUE numeri danno piu' punti allo scambio: "
          f"{scarti}/{validi}")
    if contrari:
        print(f"     direzione CONTRARIA in: {', '.join(contrari)}")
    if scarti >= 3 and not contrari:
        print("     PREDIZIONE RETTA: non e' il dominio, e' QUANTI NUMERI ogni")
        print("     soggetto porta con se'. La varianza dichiarata inspiegata")
        print("     ieri (1647cf98) ha una spiegazione misurata.")
    elif scarti <= 2 or contrari:
        print("     PREDIZIONE FALSIFICATA: l'ipotesi dei due numeri CADE.")
        print("     La varianza sugli scambi resta INSPIEGATA — e la dichiaro")
        print("     tale per la seconda volta, invece di cercarle una terza")
        print("     storia. Ieri ne ho gia' ritirate quattro.")

    print(f"\n  ⚠️ LIMITI: {n} celle, 4 domini, italiano, un solo giudice")
    print("     (cross-encoder locale). Il secondo numero cambia anche la")
    print("     LUNGHEZZA della fonte: e' un confondente che NON ho separato.")
    print("     NON e' un numero sul prodotto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
