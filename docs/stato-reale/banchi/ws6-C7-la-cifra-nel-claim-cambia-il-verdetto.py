r"""La classe «claim-senza-cifra» spiega C7, o e' una tesi comoda?

@ws3 (riga 19 del registro) ha unificato omissione, vaghezza e numerali-a-parole in una
classe sola - «in nessuno il claim porta una cifra» - e @lead-audit l'ha ratificata.
La NEGAZIONE che ho misurato (46 su 108) sembra la quarta di quella classe: i miei claim
C7 non contengono cifre, quindi `L4.1` (che nei dati di @ws1 ferma 57 dei 121 fatti
documentati con grounding >=80) e' MUTO per costruzione, e resta solo il giudice
semantico.

La tesi e' comoda, quindi la tratto da sospetta. Tre celle a fonte fissa che NEGA il
claim; cambia SOLO la presenza della cifra e dove sta:

  (a) claim SENZA cifra                        atteso: ammesso (su SDK era 12/18)
  (b) claim CON cifra, presente anche nella fonte   L4.1 non ha nulla da ridire
  (c) claim CON cifra ASSENTE dalla fonte      atteso: bloccato  <- CONTROLLO POSITIVO

  Se (b) e' ammesso quanto (a), la cifra non c'entra e la tesi NON spiega C7.
  Se (c) non e' bloccato, il banco non discrimina e va buttato.

RISULTATO (27/08 21:52, sei soggetti, tre per lingua):

  (a) claim SENZA cifra ..................... ammesse per errore  **5 su 6**
  (b) claim con cifra PRESENTE nella fonte ... ammesse per errore  **6 su 6**  <- NON INTERPRETABILE
  (c) claim con cifra ASSENTE dalla fonte .... ammesse per errore  **0 su 6**  <- controllo positivo

⚠️ IL BRACCIO (b) NON RISPONDE, ED E' COLPA DEL BANCO: per dare a `L4.1` una cifra da
confermare ho dovuto AGGIUNGERE alla fonte la riga che la contiene («nel deposito DELTA
ci sono 34 forniture») - e quella riga SOSTIENE il claim. La fonte (b) quindi si
contraddice da sola («e' vuoto» + «ci sono 34»), e ammettere non e' chiaramente
sbagliato. Due variabili cambiate insieme: il claim E la fonte. Il confronto (a) vs (b)
NON e' a variabile singola e non lo uso.

✅ CIO' CHE IL BANCO DICE DAVVERO, ed e' (c): quando il claim porta una cifra che la
fonte non conferma, la negazione viene fermata **0 su 6** - e la ricevuta dice da CHI:
`['L4.1', 'L4-grounding']` in cinque celle su sei. ⇒ **A fermare la negazione non e' il
giudice semantico: e' il rilevatore lessicale dei numeri**, che interviene perche' la
cifra manca dalla fonte, non perche' capisca la negazione.

🔑 E QUI STA IL PUNTO, che RAFFORZA la classe «claim-senza-cifra» di @ws3 invece di
falsificarla: **una fonte che nega un claim numerico non ne contiene la cifra per
costruzione** - se la contenesse, non lo starebbe negando. ⇒ Le due classi non sono
separabili: **la negazione passa esattamente dove il claim non ha cifre**, perche' li'
`L4.1` non ha nulla su cui intervenire e resta solo il giudice, che su C7 non discrimina.
⇒ La protezione dei claim numerici contro la negazione e' un EFFETTO COLLATERALE del
controllo sui numeri, non una difesa progettata: nessuno dei due layer sa cosa sia una
negazione.

📌 CASO ISOLATO CHE VALE LA PENA GUARDARE - `OMEGA`, (a): **0.46 quarantined**, l'unico
dei sei giudicato correttamente senza bisogno della cifra. Stessa struttura di frase
degli altri cinque, stesso schema di negazione, esito opposto. E' la stessa bimodalita'
per-soggetto misurata alle 21:12 (`GAMMA` sbagliava 3 volte su 3, `SIGMA` e `OMEGA` mai)
e continua a non avere una causa attribuita.

CONTROLLI: A (la fonte SOSTIENE) 99.98-99.99 in tutte e sei - C (fonte NEUTRA) 0.06-0.07
in tutte e sei. Nessuna inflazione generale.

Piu' due controlli gia' usati in tutta la serie: A la fonte SOSTIENE (deve restare alta),
C la fonte e' NEUTRA (deve restare al pavimento).

REGIME: `Memory(path=...)` su store temporaneo - FUORI da pytest (dove l'embedder e' uno
stub SHA-256) - un solo processo - riempitivo `docs/BENCHMARKS.md`, 200 parole, il caso
piu' netto della serie - warm-up di due write buttati - sei soggetti, tre per lingua.

RIPRODUCI:  python docs/stato-reale/banchi/ws6-C7-la-cifra-nel-claim-cambia-il-verdetto.py
"""
from __future__ import annotations

import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

# per ogni soggetto: (lingua, claim senza cifra, claim con cifra, negazione, riga di fonte
# che contiene la cifra vera). La cifra "assente" e' ottenuta cambiando il numero.
CASI = [
    ("IT", "Il registro ALFA elenca le misure del progetto.",
     "Il registro ALFA elenca 12 misure del progetto.",
     "Il registro ALFA e' vuoto.", "Nel registro ALFA sono elencate 12 misure."),
    ("IT", "Il deposito DELTA contiene le forniture invernali.",
     "Il deposito DELTA contiene 34 forniture invernali.",
     "Il deposito DELTA e' vuoto.", "Nel deposito DELTA ci sono 34 forniture."),
    ("IT", "Il collaudo EPSILON copre i moduli consegnati.",
     "Il collaudo EPSILON copre 7 moduli consegnati.",
     "Il collaudo EPSILON e' vuoto.", "Il collaudo EPSILON riguarda 7 moduli."),
    ("EN", "The GAMMA ledger lists the project measurements.",
     "The GAMMA ledger lists 12 project measurements.",
     "The GAMMA ledger is empty.", "The GAMMA ledger records 12 measurements."),
    ("EN", "The OMEGA warehouse holds the winter supplies.",
     "The OMEGA warehouse holds 34 winter supplies.",
     "The OMEGA warehouse is empty.", "The OMEGA warehouse stores 34 supplies."),
    ("EN", "The KAPPA review covers the delivered modules.",
     "The KAPPA review covers 7 delivered modules.",
     "The KAPPA review is empty.", "The KAPPA review spans 7 modules."),
]


def main() -> None:
    parole = (REPO / "docs" / "BENCHMARKS.md").read_text(encoding="utf-8").split()
    coda = " ".join(parole[:200])
    from verimem.client import Memory
    mem = Memory(str(Path(tempfile.mkdtemp()) / "cifra.db"))
    for i in range(2):
        mem.add(f"Il registro WARMUP{i} elenca le misure.", topic="cifra/warmup",
                source=f"Il registro WARMUP{i} elenca le misure.")

    def g(claim, src, topic):
        r = mem.add(claim, topic=topic, source=src) or {}
        lay = [w.get("layer") for w in (r.get("warnings") or []) if isinstance(w, dict)]
        return (r.get("grounding", r.get("grounding_score")), r.get("status", "?"), lay)

    conta = {"a": [0, 0], "b": [0, 0], "c": [0, 0]}
    for i, (ling, senza, con, nega, riga) in enumerate(CASI):
        print(f"\n--- {ling}  {senza}")
        # la fonte NEGA sempre; in (b) e (c) contiene anche la riga con la cifra vera
        f_a = f"{nega}\n\n{coda}"
        f_bc = f"{nega}\n{riga}\n\n{coda}"
        con_assente = con.replace(" 12 ", " 99 ").replace(" 34 ", " 88 ").replace(" 7 ", " 5 ")
        for tag, claim, fonte in (("a", senza, f_a), ("b", con, f_bc),
                                  ("c", con_assente, f_bc)):
            gs, st, lay = g(claim, fonte, f"cifra/{tag}{i}")
            bad = st != "quarantined"
            conta[tag][0] += 1
            conta[tag][1] += 1 if bad else 0
            print(f"   ({tag}) {claim[:52]:<52} {gs:7.2f} {str(st)[:12]:<12} "
                  f"{lay if lay else ''}{'   <== AMMESSA' if bad else ''}")
        # controlli
        ga, _, _ = g(senza, f"{senza}\n\n{coda}", f"cifra/A{i}")
        gc, _, _ = g(senza, coda, f"cifra/C{i}")
        print(f"   controlli: A(sostiene)={ga:7.2f}   C(neutra)={gc:6.2f}")

    print("\n=== AMMESSE PER ERRORE (la fonte nega sempre) ===")
    for k, et in (("a", "senza cifra"), ("b", "cifra PRESENTE nella fonte"),
                  ("c", "cifra ASSENTE dalla fonte")):
        n, bad = conta[k]
        print(f"   ({k}) {et:<30} {bad} su {n}")
    print("   (c) e' il CONTROLLO POSITIVO: se non e' 0 su 6, il banco non discrimina")


if __name__ == "__main__":
    main()
