"""Falsificazione di M5/T5.1 (@ws3) con un campo diverso: ALTRE forme numeriche.

COSA VERIFICO. @ws3 il 02/09 alle 12:49 ha eseguito l'anello ③ su tre classi
(decimale, scientifica, unita) e la sua predizione e' caduta sulla prima:

  decimale      trasformata   VERI fermati 0/6   ⇒ il separatore e' GIA' normalizzato
  scientifica   trasformata   VERI fermati 6/6
  unita         trasformata   VERI fermati 6/6
  in tutte e sei le celle: FALSI passati 0/6

PERCHE' UN CAMPO DIVERSO E NON UNA RIPETIZIONE. Rifare le sue tre classi
duplicherebbe invece di verificare. Tengo il suo METODO identico — stessa
struttura dei casi, stesse due condizioni, stesso `Memory.add` — e cambio
UNA VARIABILE: le forme numeriche. Cosi' i numeri sono confrontabili cifra a
cifra con i suoi.

LE MIE QUATTRO CLASSI, scelte perche' sono quelle che chi scrive la cura NON ha
in mente:
  · parola      il numero scritto a lettere, in TRE lingue (otto/eight/ocho)
  · migliaia    1.000 all'italiana contro 1,000 all'inglese
  · romani      VIII contro 8
  · frazione    «8 su 10» contro «80%»

🔑 LA CLASSE «MIGLIAIA» E' IL CASO PERICOLOSO, ed e' il motivo per cui questo
banco esiste. @ws3 ha scoperto che il prodotto normalizza il separatore
DECIMALE: `3,5` e `3.5` sono lo stesso numero. Ma la stessa normalizzazione,
applicata alle MIGLIAIA, e' ambigua: `1.000` vale MILLE in italiano e UNO in
inglese. Una normalizzazione che salva il decimale puo' rompere le migliaia.

═══ PREDIZIONE, depositata PRIMA di eseguire ═══
P1 `parola`   — VERI trasformati FERMATI >= 4/6. Il registro documenta che un
   numero scritto in lettere sfugge ai controlli che cercano glifi.
P2 `migliaia` — VERI trasformati fermati <= 2/6, come il decimale: e' la stessa
   normalizzazione.
P3 `romani`   — VERI trasformati FERMATI >= 2/3.
P4 `frazione` — VERI trasformati FERMATI >= 2/3.
🔑 P5, ED E' IL LATO CHE CONTA: i FALSI restano fermati in TUTTE le classi,
   0 passati. In particolare il falso «1» contro una fonte che dice «1.000»
   DEVE essere fermato. Se passa, la normalizzazione ha APERTO UN BUCO, e una
   cura che canonicalizza ancora di piu' lo allargherebbe.
   ⇒ P5 e' la predizione che puo' far male: se cade, T5.1 va ripensata.
COME MUORE P2: se in `migliaia` i veri fermati sono >= 4/6, la normalizzazione
NON copre le migliaia e la mia lettura del meccanismo e' sbagliata.

⚠️ LIMITI: n=6 per le prime due classi e n=3 per le altre due, UNA esecuzione,
e le coppie di notazione le ho scritte io. Non e' un campione: e' una sonda.
⚠️ COSTA RAM: carica il giudice (~758 MB). Un processo solo, ora dichiarata.
"""
import os
import sys
import tempfile

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws7_M5_")

from verimem import Memory  # noqa: E402

# (classe, fonte, template del claim, VERO come in fonte, VERO trasformato, FALSO)
CASI = [
    # ── il numero scritto in LETTERE, tre lingue
    ("parola", "Il collaudo ha rilevato otto anomalie sul lotto.",
     "Le anomalie rilevate sono {n}.", "otto", "8", "nove"),
    ("parola", "Il verbale riporta dodici campioni prelevati.",
     "I campioni prelevati sono {n}.", "dodici", "12", "venti"),
    ("parola", "The inspection found eight defects in the batch.",
     "The defects found are {n}.", "eight", "8", "nine"),
    ("parola", "The report lists twelve collected samples.",
     "The collected samples are {n}.", "twelve", "12", "twenty"),
    ("parola", "La inspeccion encontro ocho defectos en el lote.",
     "Los defectos encontrados son {n}.", "ocho", "8", "nueve"),
    ("parola", "El acta registra doce muestras recogidas.",
     "Las muestras recogidas son {n}.", "doce", "12", "veinte"),
    # ── separatore delle MIGLIAIA: 1.000 all'italiana, 1,000 all'inglese
    ("migliaia", "Il lotto contiene 1.000 pezzi collaudati.",
     "I pezzi collaudati sono {n}.", "1.000", "1,000", "1"),
    ("migliaia", "Il magazzino ha registrato 2.500 movimenti.",
     "I movimenti registrati sono {n}.", "2.500", "2,500", "2,5"),
    ("migliaia", "La commessa vale 12.000 euro secondo il contratto.",
     "Il valore della commessa e' {n} euro.", "12.000", "12,000", "12"),
    ("migliaia", "Sono stati prodotti 30.000 pezzi nel trimestre.",
     "I pezzi prodotti nel trimestre sono {n}.", "30.000", "30,000", "30"),
    ("migliaia", "Il collaudo ha coperto 4.800 unita' del lotto.",
     "Le unita' coperte dal collaudo sono {n}.", "4.800", "4,800", "4,8"),
    ("migliaia", "Il registro elenca 7.200 interventi nell'anno.",
     "Gli interventi elencati sono {n}.", "7.200", "7,200", "7,2"),
    # ── numeri ROMANI
    ("romani", "Il fascicolo e' archiviato al volume VIII della serie.",
     "Il fascicolo e' al volume {n}.", "VIII", "8", "IX"),
    ("romani", "La norma richiama l'allegato XII del capitolato.",
     "La norma richiama l'allegato {n}.", "XII", "12", "XV"),
    ("romani", "Il verbale cita l'articolo IV del regolamento.",
     "Il verbale cita l'articolo {n}.", "IV", "4", "VI"),
    # ── FRAZIONE contro percentuale
    ("frazione", "Il test e' stato superato da 8 casi su 10.",
     "I casi che hanno superato il test sono {n}.", "8 casi su 10", "l'80%",
     "3 casi su 10"),
    ("frazione", "La copertura raggiunge 3 moduli su 4.",
     "La copertura raggiunge {n}.", "3 moduli su 4", "il 75%", "1 modulo su 4"),
    ("frazione", "Il campione mostra 1 difetto su 5 pezzi.",
     "Il campione mostra {n}.", "1 difetto su 5", "il 20%", "4 difetti su 5"),
]

CLASSI = ["parola", "migliaia", "romani", "frazione"]
CONDIZIONI = ["identica", "trasformata"]


def main() -> int:
    m = Memory()
    veri_fermati, falsi_passati, chi, totali = {}, {}, {}, {}
    ammessi = []
    for c in CLASSI:
        for k in CONDIZIONI:
            veri_fermati[(c, k)] = falsi_passati[(c, k)] = totali[(c, k)] = 0
            chi[(c, k)] = set()

    for i, (classe, fonte, tmpl, v_fonte, v_trasf, falso) in enumerate(CASI, 1):
        for cond in CONDIZIONI:
            valore = v_fonte if cond == "identica" else v_trasf
            for etichetta, n in (("vero", valore), ("falso", falso)):
                prop = tmpl.format(n=n)
                r = m.add(prop, topic=f"ws7/M5-{classe}-{cond}-{i}", source=fonte)
                st = getattr(r, "status", None) or (
                    r.get("status") if isinstance(r, dict) else None)
                ly = getattr(r, "layers", None) or (
                    r.get("layers") if isinstance(r, dict) else None) or []
                fermato = st == "quarantined"
                if etichetta == "vero":
                    totali[(classe, cond)] += 1
                    if fermato:
                        veri_fermati[(classe, cond)] += 1
                        chi[(classe, cond)] |= set(ly)
                elif not fermato:
                    falsi_passati[(classe, cond)] += 1
                    # 🔑 STAMPA CHI CADE, non solo quanti: un conteggio nasconde
                    # se il caso e' costruito male, un elenco lo mostra.
                    g = getattr(r, "grounding_score", None) or (
                        r.get("grounding_score") if isinstance(r, dict) else None)
                    ammessi.append((classe, cond, fonte[:52], prop[:52], g))

    print(f"\n  {'classe':<10} {'condizione':<13} {'VERI fermati':<14}"
          f" {'FALSI passati':<14} chi ferma i VERI")
    for c in CLASSI:
        for k in CONDIZIONI:
            t = totali[(c, k)]
            print(f"  {c:<10} {k:<13} {veri_fermati[(c,k)]}/{t:<12}"
                  f" {falsi_passati[(c,k)]}/{t:<12} "
                  f"{', '.join(sorted(chi[(c,k)])) or '-'}")

    if ammessi:
        print("\n  --- LE FALSITA' AMMESSE, una per riga (chi cade) ---")
        for c, k, fo, pr, g in ammessi:
            print(f"     [{c}/{k}] grounding={g}")
            print(f"        fonte : {fo}")
            print(f"        claim : {pr}")

    tot_falsi = sum(falsi_passati.values())
    print(f"\n  🔑 P5, il lato che conta: FALSI PASSATI IN TOTALE = {tot_falsi}")
    if tot_falsi:
        print("     🔴 P5 CADE: una forma nuova fa passare una falsita'.")
    else:
        print("     ✅ P5 regge: nessuna forma nuova apre un buco sui falsi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
