"""Il punteggio salta perche' il MODELLO decide, o perche' la SOGLIA e' tarata male?

Tre misure indipendenti di stasera dicono la stessa cosa: **il punteggio del
giudice e' bimodale**.

    corpus reale (`897d0048`)   91,73% sopra 95 · 5,46% sotto 40 · 1,08% in banda
    scala di distanza (`44dbf0a3`)  salti di 94,8 · 95,0 · 72,1 punti fra gradini
    dodici irrilevanti (`706de500`) punteggi 93,3 · 0,4 · 73,7 · 99,0 · 87,7 · 1,5…

E la conseguenza pesa: **se il punteggio non sta mai in mezzo, la banda 40-80 —
il ramo che "escalates or holds for review" — non puo' raccogliere quasi
niente**, e infatti raccoglie l'1,08%.

**MA LE DUE SPIEGAZIONI POSSIBILI PORTANO A DECISIONI OPPOSTE, e finora non le
ho separate:**

    (a) e' del **MODELLO** — un cross-encoder addestrato a **decidere** (sono
        due frasi che si implicano: si' / no) e non a **graduare**. Allora la
        banda 40-80 e' **strutturalmente inefficace**: nessuna taratura la
        riempie, e va detto come limite di architettura.
    (b) e' della **SOGLIA / calibrazione** — il modello gradua, ma la scala e'
        schiacciata agli estremi. Allora **si corregge**, e la banda ha senso.

⚠️ Finora ho misurato **casi discreti** (pertinente / irrilevante / negato): un
salto fra categorie **non distingue (a) da (b)**, perche' le mie categorie erano
gia' discrete. **Serve una serie a supporto CONTINUO**, dove ogni gradino toglie
**un pezzetto** di supporto — e guardare se il punteggio scende **liscio** o
**a scalino**.

LA SERIE, sei gradini che erodono il supporto **un po' alla volta**:

    G1 esatto        il claim ridice cio' che la fonte afferma
    G2 riformulato   stesse informazioni, parole diverse
    G3 parziale      solo META' di cio' che la fonte afferma
    G4 indebolito    lo stesso, ma con «di solito / in genere»
    G5 esteso        aggiunge una conseguenza plausibile ma NON detta
    G6 negato        contraddice la fonte

LA PREDIZIONE, scritta prima di eseguire: **il punteggio SALTA** — la
**zona grigia (20-80)** restera' quasi vuota anche su una serie continua,
⇒ la bimodalita' e' **del MODELLO**, ipotesi (a).

CONDIZIONE DI FALSIFICAZIONE: se **almeno un terzo** dei punteggi cade nella
zona grigia, la serie continua **produce** valori intermedi ⇒ la bimodalita' non
e' del modello ma di **come sono fatti i casi che gli diamo**, e la banda ha
senso: ipotesi (b), e la mia predizione cade.

CONTROLLO CHE DEVE POTER FALLIRE: **G1 alto e G6 basso in tutte le fonti**. Se
i due estremi non si separano, la serie non erode niente e i valori in mezzo non
significano nulla.

⚠️ CONFONDENTE DICHIARATO: «erodere un po' alla volta» e' **la mia idea** di
gradazione. Un altro avrebbe scritto altri sei gradini. Questo banco puo'
mostrare che **esistono** valori intermedi, non che **non esistano**.

🔴 **ESITO: PREDIZIONE RETTA, e la zona grigia e' VUOTA.**

    fonte        G1 esatto G2 riform G3 parzia G4 indebo G5 esteso G6 negato
    consegna         100.0      99.9      99.0      99.9      99.8       0.5
    biblioteca       100.0      99.6      98.3      97.0      98.7       1.9
    impianto         100.0       0.1      96.9      95.9      99.8       1.1

    alti (>=80): 14   ·   GRIGI (20-80): **0**   ·   bassi (<=20): 4

**Controllo retto: G1 alto e G6 basso in 3 serie su 3.**

⇒ **La bimodalita' e' del MODELLO, non della taratura.** Anche erodendo il
supporto **un pezzetto alla volta** — riformulazione, meta' del contenuto, un
«di solito», un'aggiunta non detta — il punteggio **non produce nemmeno un
valore intermedio**. Un cross-encoder addestrato a **decidere** non **gradua**.
🔑 **Conseguenza per l'architettura: la banda 40-80 non puo' riempirsi.** Non e'
un parametro mal tarato che qualcuno puo' correggere: e' una **rete tesa dove il
pesce non passa mai**, perche' il punteggio non transita da li'. L'1,08% del
corpus (`897d0048`) non era un caso: era la misura di questo.

🔴 **E UNA RIGA VA LETTA, NON CONTATA: `impianto G2 = 0,1`.**
G2 e' una **riformulazione fedele**: «*a parte la manutenzione semestrale,
l'impianto lavora senza interruzioni*» contro la fonte «*fermato ogni sei mesi
per la manutenzione e produce a ciclo continuo nel resto dell'anno*». **Dicono
la stessa cosa.** Il giudice le da' **0,1** — la tratta come una **contraddizione**
(G6, la negazione vera, prende 1,1: **G2 sta PEGGIO della negazione**).
⇒ **E' il ROVESCIO ESATTO del buco documentato in `706de500`**: il giudice non
solo lascia passare l'**irrilevante** a 87-99, ma **respinge una parafrasi
corretta** a 0,1. **Entrambi gli errori sono ESTREMI**, e li' sta la gravita':
un errore binario non lascia traccia di incertezza. Un falso a 45 chiama una
revisione; un falso a **0,1** dice «e' certamente falso» e chiude la questione.
⚠️ **1 caso su 3: non e' una legge, e' un'osservazione.** La riporto col suo
limite, non come tasso.

REGIME: store TEMPORANEO, cross-encoder locale (nessuna API esterna). Lo store
di Aurelio NON e' toccato.

    python docs/stato-reale/banchi/ws3-la-bimodalita-e-del-modello-o-della-soglia.py
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

GRIGIO = (20.0, 80.0)

#: (nome, fonte, [G1 esatto, G2 riformulato, G3 parziale, G4 indebolito,
#:  G5 esteso, G6 negato])
SERIE: list[tuple[str, str, list[str]]] = [
    (
        "consegna",
        "Il fornitore consegna la merce entro cinque giorni lavorativi e "
        "sostiene le spese di trasporto.",
        [
            "Il fornitore consegna entro cinque giorni lavorativi e sostiene "
            "le spese di trasporto.",
            "Le spese di trasporto sono a carico del fornitore, che consegna "
            "in cinque giorni lavorativi.",
            "Il fornitore sostiene le spese di trasporto.",
            "Di solito il fornitore sostiene le spese di trasporto.",
            "Il fornitore sostiene le spese di trasporto e quelle di "
            "assicurazione della merce.",
            "Le spese di trasporto sono a carico del cliente.",
        ],
    ),
    (
        "biblioteca",
        "La biblioteca apre dal martedi' al sabato e mette a disposizione una "
        "sala studio silenziosa.",
        [
            "La biblioteca apre dal martedi' al sabato e ha una sala studio "
            "silenziosa.",
            "Dal martedi' al sabato la biblioteca e' aperta, con una sala "
            "studio in cui si sta in silenzio.",
            "La biblioteca ha una sala studio silenziosa.",
            "In genere la biblioteca ha una sala studio silenziosa.",
            "La biblioteca ha una sala studio silenziosa e distribuisce "
            "tessere gratuite agli studenti.",
            "La biblioteca non dispone di una sala studio.",
        ],
    ),
    (
        "impianto",
        "L'impianto viene fermato ogni sei mesi per la manutenzione e produce "
        "a ciclo continuo nel resto dell'anno.",
        [
            "L'impianto e' fermato ogni sei mesi per manutenzione e produce a "
            "ciclo continuo nel resto dell'anno.",
            "A parte la manutenzione semestrale, l'impianto lavora senza "
            "interruzioni.",
            "L'impianto produce a ciclo continuo.",
            "L'impianto produce a ciclo continuo quasi sempre.",
            "L'impianto produce a ciclo continuo ed e' certificato per la "
            "sicurezza.",
            "L'impianto non viene mai fermato per manutenzione.",
        ],
    ),
]

GRADINI = ("G1 esatto", "G2 riform", "G3 parzia", "G4 indebo",
           "G5 esteso", "G6 negato")


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    os.environ["HIPPO_DATA_DIR"] = str(tmp)
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  REGIME: HIPPO_DATA_DIR={tmp}  (store di Aurelio NON toccato)")
    print(f"  zona grigia sotto esame: {GRIGIO[0]:.0f}-{GRIGIO[1]:.0f}")
    mem = Memory(str(tmp / "bimod.db"))
    n = 0

    def punteggio(claim: str, fonte: str) -> float:
        nonlocal n
        n += 1
        r = mem.add(claim, topic=f"bm/{n}", source=fonte, validate="full")
        gs = r.get("grounding_score")
        return -1.0 if gs is None else float(gs)

    print(f"\n  {'fonte':<12} " + " ".join(f"{g[:9]:>9}" for g in GRADINI))
    print("  " + "-" * 70)
    tutti: list[float] = []
    estremi_ok = 0
    for nome, fonte, claims in SERIE:
        v = [punteggio(c, fonte) for c in claims]
        tutti.extend(v)
        if v[0] >= 80.0 and v[-1] <= 20.0:
            estremi_ok += 1
        print(f"  {nome:<12} " + " ".join(f"{x:>9.1f}" for x in v))

    print(f"\n  [1] CONTROLLO — G1 alto E G6 basso: {estremi_ok}/{len(SERIE)}")
    if estremi_ok < len(SERIE):
        print("      CONTROLLO CADUTO: gli estremi non si separano in tutte le")
        print("      serie ⇒ la serie non erode niente e i valori intermedi non")
        print("      significano nulla. NESSUN VERDETTO.")
        return 1

    grigi = [x for x in tutti if GRIGIO[0] < x < GRIGIO[1]]
    alti = [x for x in tutti if x >= GRIGIO[1]]
    bassi = [x for x in tutti if x <= GRIGIO[0]]
    print(f"\n  [2] DOVE CADONO I {len(tutti)} PUNTEGGI")
    print(f"      alti  (>= {GRIGIO[1]:.0f}) .... {len(alti):>3}")
    print(f"      GRIGI ({GRIGIO[0]:.0f}-{GRIGIO[1]:.0f}) ...... {len(grigi):>3}"
          f"   <- la banda 40-80 vive QUI")
    print(f"      bassi (<= {GRIGIO[0]:.0f}) .... {len(bassi):>3}")
    if grigi:
        print("      valori grigi: "
              + " · ".join(f"{x:.1f}" for x in sorted(grigi)))

    quota = len(grigi) / len(tutti)
    print("\n  ══ VERDETTO ══")
    print(f"     quota in zona grigia: {quota:.0%}")
    if quota < 1 / 3:
        print("     PREDIZIONE RETTA: anche su una serie a supporto CONTINUO il")
        print("     punteggio salta ⇒ la bimodalita' e' del MODELLO, non della")
        print("     taratura. Un cross-encoder addestrato a DECIDERE non")
        print("     gradua, e la banda 40-80 non puo' riempirsi: e' un limite")
        print("     di ARCHITETTURA, non un parametro da correggere.")
    else:
        print("     PREDIZIONE FALSIFICATA: una serie continua PRODUCE valori")
        print("     intermedi ⇒ la bimodalita' vista finora veniva da come")
        print("     erano fatti i MIEI casi, non dal modello. La banda ha senso,")
        print("     e la mia lettura di `44dbf0a3` va ristretta.")

    print(f"\n  ⚠️ LIMITI: {n} celle, 3 serie, italiano, un giudice")
    print("     (cross-encoder locale). «Erodere un po' alla volta» e' la MIA")
    print("     idea di gradazione: questo banco puo' mostrare che i valori")
    print("     intermedi ESISTONO, non che non esistano.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
