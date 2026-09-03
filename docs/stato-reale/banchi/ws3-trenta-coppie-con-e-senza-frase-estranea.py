"""LIVELLO: porta del prodotto (`Memory.add`, `validate="full"`) — non lo strato.

Trenta contraddizioni, con e senza una frase estranea in coda alla fonte.

    python docs/stato-reale/banchi/ws3-trenta-coppie-con-e-senza-frase-estranea.py

⚠️ Carica il giudice. Serve uno slot di inferenza. ~30 s di freddo + ~0,45 s a
scrittura: 120 scritture ≈ 90 s (costo misurato il 03/09 in
`ws3-R1-quanto-costa-una-cella-di-porta-col-giudice.py`).

━━ PERCHE' ESISTE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
L'A/B appaiato del 03/09 ha mostrato che UNA frase estranea in coda alla fonte
porta il grounding di una falsita' da 1,84 a 99,94 e ne ribalta il verdetto. Ma
erano DUE claim, e due claim non sono un tasso. Il banco del 26/08 dava 4/12,
con un limite che dichiarava da solo: «le riformulazioni le ha scritte chi
conosceva il difetto».

Qui si misura QUANTO SPESSO, e si tolgono i due difetti del disegno precedente.

━━ IL DISEGNO, e le due obiezioni che deve reggere ━━━━━━━━━━━━━━━━━━━━━━━━━━
① **Le frasi non sono scelte a mano caso per caso.** Sono generate da una
   TABELLA DI OPPOSIZIONE fissa (dieci verbi con il loro contrario) applicata a
   tre soggetti e tre date, sempre con la stessa regola. Resta un disegno mio —
   la tabella l'ho scritta io — ma nessuna frase e' stata scelta DOPO aver
   visto come rispondeva il gate, che era il difetto vero del banco del 26/08.
② **Si misurano DUE popolazioni, non solo i falsi.** Trenta falsita' (la fonte
   le smentisce) e trenta VERITA' (la fonte le sostiene alla lettera). Se la
   zavorra alzasse anche i veri, non sarebbe un attacco alla contraddizione:
   sarebbe un'inflazione generale del punteggio, e la cura sarebbe un'altra.
   Sui soli falsi ogni criterio sembra ottimo: e' la lezione del banco dei
   caratteri difficili.

⚠️ UNA SOLA VARIABILE: la zavorra e' SEMPRE la stessa frase, sempre in coda,
sempre dopo la fonte intera. Non varia la lunghezza, non varia la posizione.
Quello che questo banco NON misura, e non riempio: se una zavorra diversa, o
in mezzo, faccia di piu' o di meno.

🔮 PREDIZIONE, depositata prima di eseguire:
  ① sui FALSI la zavorra fa entrare **fra il 25% e il 60%** (il 26/08 dava
     4/12 = 33% su un disegno diverso);
  ② sui VERI il cambio di verdetto e' **≤ 2 su 30** in ciascun verso;
  ③ il salto mediano di grounding sui falsi che passano e' **> 50 punti**
     (l'A/B appaiato dava +98).
🔴 COME MUORE: se i veri cambiano quanto i falsi, la diagnosi «la frase estranea
attacca la contraddizione» e' sbagliata e si tratta di rumore o di inflazione.

━━ MISURATO IL 2026-09-03 alle 20:20 — DUE PREDIZIONI SU TRE FALSIFICATE ━━━━
    popolazione FALSO (30 casi)
      trattenuti con la fonte CORTA   24/30
      trattenuti CON la zavorra       24/30
      LIBERATI dalla zavorra           0/30   (0%)
      salto di grounding: mediana +0,7 · min +0,1 · max +31,4

    popolazione VERO (30 casi)
      trattenuti con la fonte CORTA    7/30
      trattenuti CON la zavorra        6/30
      liberati 2 · fermati solo con la zavorra 1  -> 3 cambi

    ① falsi liberati 25-60%   ->  0%   🔴 FALSIFICATA
    ② veri che cambiano ≤2    ->  3    🔴 FALSIFICATA
    ③ non calcolabile: nessun falso liberato

⇒ SU TRENTA CONTRADDIZIONI GENERATE MECCANICAMENTE LA ZAVORRA NON NE LIBERA
NESSUNA. L'effetto +98 misurato lo stesso giorno su due claim NON si
generalizza, e la mia formulazione «una frase estranea vale 98 punti» era
troppo larga: vale per QUEI claim, non per la classe.

━━ E DUE SONDE HANNO ESCLUSO IL MIO BANCO PRIMA DI PUBBLICARE LO 0/30 ━━━━━━━
① **Non e' lo store condiviso.** Stessa coppia in tre regimi — store fresco /
   store unico con due sole scritture / store unico dopo 20 scritture estranee —
   da' lo STESSO risultato (0,73 -> 32,11, nessun ribaltamento). Il sospetto era
   che 120 scritture in un solo store cambiassero il giudizio: falsificato.
② **E' il CLAIM, e la sua grafia conta.** Due fattori incrociati sullo stesso
   verbale, otto scritture:

       confermato, «e'» con apostrofo   1,84 -> 99,94   RIBALTA
       confermato, «e» nuda             3,92 -> 99,95   no (grounding altissimo,
                                                        ma un altro strato tiene)
       in carica,  «e'» con apostrofo   0,73 -> 32,11   no
       in carica,  «e» nuda             0,93 -> 99,90   RIBALTA

   Sullo STESSO claim, scrivere «e» invece di «e'» porta l'effetto della zavorra
   da +31 a +99. Le mie trenta frasi usano tutte «e'», che e' la forma corretta:
   il banco non poteva vedere il fenomeno che voleva contare.
   ⚠️ E il gonfiare il giudice NON basta a far entrare il fatto: la seconda riga
   ha grounding 99,95 e resta trattenuta.

⇒ COSA RESTA VERO, e cosa no:
   VERO   la zavorra puo' portare il giudice da «contraddetto» a «sostenuto»,
          misurato tre volte su claim specifici;
   NON DIMOSTRATO  che sia una proprieta' della classe «contraddizione»: su
          trenta casi generati con una regola fissa, zero.
   APERTO quale caratteristica del claim renda la zavorra efficace. La grafia
          di «e'» e' UN fattore, non e' detto sia il solo, e non lo riempio.
"""
from __future__ import annotations

import statistics
import tempfile
from pathlib import Path

from verimem.client import Memory

ZAVORRA = "La mensa aziendale resta chiusa il primo maggio."

#: (cio' che la fonte afferma, la FALSITA', la VERITA' riformulata).
#:
#: ⚠️ La terza colonna NON e' la fonte ricopiata, ed e' una correzione al primo
#: disegno di questo banco: un claim vero identico alla fonte sta al SOFFITTO
#: del punteggio, quindi non puo' salire e la popolazione di controllo non
#: potrebbe rilevare un'inflazione — proverebbe solo che 99 resta 99. La
#: riformulazione lascia il margine che serve al controllo per falsificare.
OPPOSIZIONI = [
    ("ha rassegnato le dimissioni", "e' ancora in carica",
     "ha lasciato l'incarico"),
    ("e' deceduto in terapia intensiva", "e' stato dimesso in buone condizioni",
     "non e' sopravvissuto al ricovero"),
    ("ha respinto il ricorso", "ha accolto il ricorso",
     "ha dato torto a chi aveva fatto ricorso"),
    ("ha chiuso lo stabilimento", "ha tenuto aperto lo stabilimento",
     "ha cessato l'attivita' nello stabilimento"),
    ("ha venduto la partecipazione", "ha mantenuto la partecipazione",
     "non detiene piu' la partecipazione"),
    ("e' stato assolto", "e' stato condannato",
     "non e' stato ritenuto colpevole"),
    ("ha annullato la seduta", "ha tenuto la seduta regolarmente",
     "ha fatto saltare la seduta"),
    ("ha lasciato scadere il contratto", "ha rinnovato il contratto",
     "non ha rinnovato il contratto"),
    ("ha ritirato il prodotto dal mercato", "ha lasciato il prodotto in vendita",
     "ha tolto il prodotto dal commercio"),
    ("ha bocciato la proposta", "ha approvato la proposta",
     "non ha dato via libera alla proposta"),
]
SOGGETTI = ["Il direttore", "Il consiglio", "Il responsabile"]
DATE = ["il 4 maggio", "il 12 giugno", "il 30 luglio"]


def coppie() -> list[tuple[str, str, str]]:
    """(fonte, claim FALSO, claim VERO) — trenta, per costruzione."""
    fuori = []
    for i, (fatto, contrario, riformulato) in enumerate(OPPOSIZIONI):
        for k in range(3):
            sogg, data = SOGGETTI[(i + k) % 3], DATE[(i + k) % 3]
            fonte = f"Verbale: {sogg.lower()} {fatto} {data}."
            fuori.append((
                f"{fonte[0].upper()}{fonte[1:]}",
                f"{sogg} {contrario} {data}.",
                f"{sogg} {riformulato} {data}.",
            ))
    return fuori[:30]


def main() -> None:
    mem = Memory(str(Path(tempfile.mkdtemp()) / "trenta.db"))
    dati = coppie()
    print("TRENTA COPPIE, CON E SENZA FRASE ESTRANEA\n")
    print(f"casi: {len(dati)}  ·  zavorra unica: {ZAVORRA!r}\n")

    esiti: dict[str, list] = {"falso": [], "vero": []}
    for n, (fonte, falso, vero) in enumerate(dati, 1):
        for etichetta, claim in (("falso", falso), ("vero", vero)):
            r_corta = mem.add(claim, topic=f"t/30/{etichetta}/{n}/corta",
                              source=fonte, validate="full")
            r_zav = mem.add(claim, topic=f"t/30/{etichetta}/{n}/zavorra",
                            source=f"{fonte} {ZAVORRA}", validate="full")
            esiti[etichetta].append((
                claim,
                str(r_corta.get("status")), r_corta.get("grounding_score"),
                str(r_zav.get("status")), r_zav.get("grounding_score"),
            ))
        if n % 5 == 0:
            print(f"  ...{n}/{len(dati)}", flush=True)

    print()
    for etichetta in ("falso", "vero"):
        righe = esiti[etichetta]
        fermi_corta = sum(1 for r in righe if r[1] == "quarantined")
        fermi_zav = sum(1 for r in righe if r[3] == "quarantined")
        liberati = [r for r in righe if r[1] == "quarantined" and r[3] != "quarantined"]
        chiusi = [r for r in righe if r[1] != "quarantined" and r[3] == "quarantined"]
        salti = [r[4] - r[2] for r in righe
                 if isinstance(r[2], int | float) and isinstance(r[4], int | float)]
        print(f"── popolazione {etichetta.upper()} ({len(righe)} casi)")
        print(f"   trattenuti con la fonte CORTA   : {fermi_corta}/{len(righe)}")
        print(f"   trattenuti CON la zavorra       : {fermi_zav}/{len(righe)}")
        print(f"   🔴 LIBERATI dalla zavorra       : {len(liberati)}/{len(righe)}"
              f"  ({100.0 * len(liberati) / max(1, len(righe)):.0f}%)")
        print(f"   fermati SOLO con la zavorra     : {len(chiusi)}/{len(righe)}")
        if salti:
            print(f"   salto di grounding: mediana {statistics.median(salti):+.1f}"
                  f"  ·  min {min(salti):+.1f}  ·  max {max(salti):+.1f}")
        print()

    n_lib_falsi = sum(1 for r in esiti["falso"]
                      if r[1] == "quarantined" and r[3] != "quarantined")
    n_cambi_veri = sum(1 for r in esiti["vero"] if (r[1] == "quarantined") != (r[3] == "quarantined"))
    quota = 100.0 * n_lib_falsi / max(1, len(esiti["falso"]))
    print("── le tre predizioni")
    print(f"   ① falsi liberati 25-60%      : {quota:.0f}%   "
          f"{'✅' if 25 <= quota <= 60 else '🔴 FALSIFICATA'}")
    print(f"   ② veri che cambiano ≤2       : {n_cambi_veri}   "
          f"{'✅' if n_cambi_veri <= 2 else '🔴 FALSIFICATA'}")
    salti_lib = [r[4] - r[2] for r in esiti["falso"]
                 if r[1] == "quarantined" and r[3] != "quarantined"
                 and isinstance(r[2], int | float) and isinstance(r[4], int | float)]
    if salti_lib:
        med = statistics.median(salti_lib)
        print(f"   ③ salto mediano >50 punti    : {med:+.1f}   "
              f"{'✅' if med > 50 else '🔴 FALSIFICATA'}")
    else:
        print("   ③ nessun falso liberato: la predizione ① e' gia' morta")


if __name__ == "__main__":
    main()
