"""LA CURVA: quanti falsi allarmi di `L4.1` in funzione di QUANTE CIFRE ha il claim.

W7-44 ha misurato che i 53 fatti **approvati dal moat (≥80) e fermati da `L4.1`**
hanno **mediana 4 numeri** contro **1** dei quarantinati sotto il cut, e ne ha
tratto una spiegazione: *`L4.1` verifica OGNI numero, quindi un claim con cinque
numeri ha cinque occasioni di essere fermato per sbaglio.*

⚠️ **Quella e' una spiegazione, non una misura.** Qui la misuro: su **una fonte
fissata**, claim **tutti VERI** — ogni cifra compare nella fonte **alla lettera**
— con densita' crescente da 1 a 8 numeri. Se la spiegazione regge, **il tasso di
falso allarme cresce con la densita'**.

⚖️ E la **popolazione opposta**, senza la quale il numero non significa niente:
per ogni densita', lo stesso claim con **UNA cifra inventata**. Quelli devono
essere fermati **tutti**: se il layer smettesse di fermarli alle alte densita',
il problema non sarebbe il falso allarme ma un varco.

CONTROLLI CHE POSSONO FALLIRE:
 (1) a densita' 1 il claim vero deve PASSARE: se lo ferma gia' li', non sto
     misurando la densita', sto misurando altro.
 (2) i FALSI devono essere fermati a ogni densita': se cedono, e' un varco e va
     detto prima del resto.
 (3) ogni cifra dei claim VERI deve comparire nella fonte: lo verifico nel
     banco invece di fidarmi di come li ho scritti.

    python -u docs/stato-reale/banchi/la-curva-dei-falsi-allarmi-in-funzione-delle-cifre.py
"""

from __future__ import annotations

import re
import sys

FONTE = (
    "Referto della sessione del 12 marzo. Il job windows ha impiegato 45 minuti "
    "e ha prodotto 22 test passati, 8 saltati e 3 falliti su 7 file. "
    "La suite security ha registrato 19 esiti positivi con durata media 6 minuti. "
    "Il run 31409905021 e' terminato alle 14 e 30, con 91 richieste servite e "
    "una coda di 20 elementi. Il coefficiente di copertura risulta 84 per cento "
    "su 512 righe esaminate."
)

# claim VERI a densita' crescente: ogni cifra e' nella fonte alla lettera
VERI = [
    (1, "Il job windows ha impiegato 45 minuti."),
    (2, "Il job windows ha impiegato 45 minuti e ha prodotto 22 test passati."),
    (3, "Il job windows ha impiegato 45 minuti con 22 test passati e 8 saltati."),
    (4, "Il job windows ha impiegato 45 minuti con 22 passati, 8 saltati e 3 falliti."),
    (5, "Il job windows ha impiegato 45 minuti con 22 passati, 8 saltati e 3 falliti su 7 file."),
    (6, "Il job windows ha impiegato 45 minuti con 22 passati, 8 saltati e 3 falliti su 7 file, "
        "mentre security ha 19 esiti positivi."),
    (7, "Il job windows ha impiegato 45 minuti con 22 passati, 8 saltati e 3 falliti su 7 file, "
        "mentre security ha 19 esiti positivi in 6 minuti."),
    (8, "Il job windows ha impiegato 45 minuti con 22 passati, 8 saltati e 3 falliti su 7 file, "
        "mentre security ha 19 esiti positivi in 6 minuti e la coda era di 20 elementi."),
]
NUM = re.compile(r"\d+")


def falsifica(claim: str) -> str:
    """Sostituisce l'ULTIMA cifra con una che la fonte non contiene."""
    m = list(NUM.finditer(claim))
    if not m:
        return claim
    ultimo = m[-1]
    return claim[:ultimo.start()] + "777" + claim[ultimo.end():]


def main() -> int:
    try:
        from verimem.valore_non_nella_fonte import valori_non_nella_fonte
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    print("  -- CONTROLLO (3): ogni cifra dei claim VERI e' nella fonte?")
    fuori = []
    for k, c in VERI:
        for n in NUM.findall(c):
            if n not in FONTE:
                fuori.append((k, n))
    if fuori:
        print(f"     CADUTO - {len(fuori)} cifre non sono nella fonte: {fuori[:6]}")
        print("     I claim «veri» non lo sono: il banco misurerebbe i miei errori.")
        return 1
    print("     retto - tutte le cifre dei claim veri compaiono nella fonte")

    print(f"\n  == LA CURVA  (fonte fissata, {len(FONTE)} caratteri)")
    print(f"     {'cifre':>6} {'VERO':<26} {'FALSO (una inventata)'}")
    veri_fermati = falsi_fermati = 0
    primo_falso_allarme = None
    for k, c in VERI:
        a = valori_non_nella_fonte(c, FONTE)
        b = valori_non_nella_fonte(falsifica(c), FONTE)
        if a:
            veri_fermati += 1
            if primo_falso_allarme is None:
                primo_falso_allarme = k
        if b:
            falsi_fermati += 1
        va = ("FERMA " + ",".join(f"{float(getattr(x, 'valore', 0)):g}"
                                  for x in a[:3])) if a else "passa"
        vb = "ferma" if b else "PASSA (varco!)"
        print(f"     {k:>6} {va:<26} {vb}")

    n = len(VERI)
    print(f"\n  == I DUE NUMERI, su {n} densita'")
    print(f"     VERI fermati (falso allarme) : {veri_fermati} su {n}")
    print(f"     FALSI fermati (il suo lavoro): {falsi_fermati} su {n}")

    print("\n  -- CONTROLLO (1): a densita' 1 il vero passa?")
    primo = valori_non_nella_fonte(VERI[0][1], FONTE)
    if primo:
        print("     CADUTO - gia' con UNA cifra il claim vero e' fermato: non")
        print("     sto misurando la densita'.")
        return 1
    print("     retto - a densita' 1 il vero passa")

    print("\n  -- CONTROLLO (2): i falsi sono fermati a ogni densita'?")
    if falsi_fermati < n:
        print(f"     ATTENZIONE - solo {falsi_fermati} su {n}: alle densita' dove")
        print("     il falso passa c'e' un VARCO, e va detto prima del resto.")
    else:
        print(f"     retto - {falsi_fermati} su {n}, il layer non cede")

    print("\n  -- LA SPIEGAZIONE DI W7-44 REGGE?")
    if veri_fermati == 0:
        print("     NO - nessun falso allarme a nessuna densita'. La spiegazione")
        print("     «piu' numeri, piu' occasioni di sbagliare» NON si riproduce")
        print("     su una fonte fissata: il tratto misurato in W7-44 e' vero ma")
        print("     la causa e' un'altra, e non la so.")
    elif primo_falso_allarme:
        print(f"     il primo falso allarme compare a {primo_falso_allarme} cifre,")
        print(f"     e in totale sono {veri_fermati} su {n}. La direzione e'")
        print("     quella prevista; la forma esatta si legge nella tabella.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
