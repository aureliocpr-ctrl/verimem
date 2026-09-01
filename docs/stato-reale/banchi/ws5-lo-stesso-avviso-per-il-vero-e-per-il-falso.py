r"""Lo stesso avviso, parola per parola, per il claim VERO e per quello FALSO — e il
falso passa a 99.9.

Non l'ho cercato: e' emerso salvando i fatti di stasera. **Quattro salvataggi su
quattro** con source = output di banco hanno prodotto un `L4.2` la cui spiegazione cita
come «parola accanto» un frammento della colonna precedente o la lettera di riga::

    58   qui «(nessuna parola accanto)», nella fonte «(solo parole grammaticali accanto)»
    0.3  qui «prima del numero: ground», nella fonte «b»
    99.5 qui «(solo parole grammaticali accanto)», nella fonte «f»
    8.6  qui «delta», nella fonte «pt»

⚠️ Quattro aneddoti non sono una misura: manca una popolazione in **prosa** e manca un
caso in cui `L4.2` **deve** scattare — senza, «scatta troppo» non e' distinguibile da
«scatta».

L'INCROCIO 2x2, stessa informazione, stesso numero::

                        claim CORRETTO              claim SCAMBIATO
    fonte TABELLARE     A  L4.2 non dovrebbe        C  L4.2 DEVE scattare
    fonte PROSA         B  L4.2 non dovrebbe        D  L4.2 DEVE scattare

🔴🔴 ESITO — **tre reperti, e la mia ipotesi di partenza e' fra i falsificati**::

    caso                     esito    ground   layer
    A tabellare, VERO        passa      99.9   L4.2
    B prosa, VERO            passa     100.0   L4.2
    C tabellare, FALSO       passa      99.9   L4.2
    D prosa, FALSO           passa     100.0   L4.2

    A: «... 14304 qui e' «(nessuna parola accanto)», nella fonte «quarantinati»»
    C: «... 14304 qui e' «(nessuna parola accanto)», nella fonte «quarantinati»»   ← IDENTICA
    B: «... 14304 qui e' «(nessuna parola accanto)», nella fonte «(solo parole
        grammaticali accanto)»»
    D: identica a B

🔴 **① L'AVVISO NON DISTINGUE IL VERO DAL FALSO.** `A` dice il vero («gli ammessi sono
14304») e `C` dice il falso (i quarantinati sono **2679**, non 14304): **ricevono la
stessa identica stringa, parola per parola**. ⇒ Un avviso che dice la stessa cosa
quando hai ragione e quando hai torto **non porta informazione**: leggerlo non aiuta a
decidere, e chi lo legge sul caso vero impara a ignorarlo — proprio prima di incontrare
quello falso.

🔴🔴 **② E IL CLAIM FALSO PASSA**: `C` a **99.9** e `D` a **100.0**. E' lo scambio di
grandezza classico — prendere il numero giusto e attaccarlo all'oggetto sbagliato — e
**ne' il giudice ne' i layer lo fermano**, in nessuna delle due forme.

🪞 **③ LA MIA IPOTESI CADE: non e' la forma tabellare.** Ero partita da «*l'avviso legge
la colonna sbagliata*». `B` e `D` sono **in prosa** e si comportano uguale. ⇒ La causa
sta nel lato **claim**: «*14304 qui e' (nessuna parola accanto)*» in **tutti e quattro**
i casi. In «Gli ammessi sono 14304» il soggetto non e' adiacente al numero — c'e' il
verbo in mezzo — quindi il layer non trova mai il contesto che dovrebbe confrontare, e
**i due claim gli sembrano lo stesso claim**.

⚠️ **④ E sulla tabella il contesto estratto e' l'OPPOSTO del significato**: la riga e'
`ammessi (status != quarantined)  14304`, e il layer riporta «*nella fonte
«quarantinati»*» — ha preso la parola piu' vicina **dentro una parentesi di negazione**,
ignorando il `!=`. La forma tabellare non e' la causa, ma **aggiunge un errore**: da' un
contesto sbagliato invece di nessuno.

📌 **SI LEGA AL CONTROLLO POSITIVO DI @ws4** (canale, 20:00): «*il claim prende il numero
giusto e lo attacca alla grandezza sbagliata. E' esattamente W7-98, e qui il moat lo
ferma: g=2.12. E' IL CONTROLLO POSITIVO CHE MI MANCAVA: su questa popolazione il moat
NON e' cieco*». ⇒ **Qui c'e' il controesempio**: stesso tipo di scambio, `g=99.9` e
`g=100.0`, passa. **Il moat becca quello scambio su quella popolazione e non su questa**
— e chi decide sul cut deve avere tutti e due i casi, non uno solo.

⇒ **PER LA DECISIONE**: non e' una cura all'avviso. `L4.2` **non ha in mano
l'informazione** per distinguere `A` da `C`, perche' guarda l'adiacenza e in italiano il
soggetto non e' adiacente al numero. **La domanda vera e' se il gate debba dichiarare
questa classe come non coperta**, invece di emettere un avviso che suona come una
diagnosi.

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) · `ground_write=True` ·
porta `run_validation_gate` · daemon attivo, nessun `None` nel grounding.
⚖️ PUNTI DEBOLI: un claim per cella; la fonte tabellare e' **la mia** (l'output di un
banco), non una tabella qualunque; misuro la **stringa** dell'avviso, che puo' cambiare
senza che cambi il verdetto; e **non ho provato la forma in cui il soggetto E' adiacente
al numero** («*i quarantinati 14304*») — che direbbe se il layer si sveglia quando il
contesto c'e'.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-lo-stesso-avviso-per-il-vero-e-per-il-falso.py <dir-temp>
"""
import os
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

#: l'output di un banco, come lo passiamo tutti i giorni con --source
TABELLARE = (
    "  popolazione                          totale marca breve    quota\n"
    "  ---------------------------------------------------------------\n"
    "  ammessi (status != quarantined)       14304       2328    16.3%\n"
    "  quarantinati, qualunque causa          2679       1468    54.8%\n")

#: le stesse identiche informazioni, in prosa
PROSA = (
    "Gli ammessi, cioe' i fatti il cui status non e' quarantined, sono 14304 e di questi "
    "2328 portano la marca breve, pari al 16.3 per cento. I quarantinati di qualunque "
    "causa sono 2679 e di questi 1468 portano la marca breve, pari al 54.8 per cento.")

VERO = "Gli ammessi sono 14304."
#: 14304 e' il numero degli AMMESSI: attribuirlo ai quarantinati (che sono 2679) e' falso
FALSO = "I quarantinati sono 14304."

CASI = [
    ("A tabellare, VERO", VERO, TABELLARE, "non dovrebbe"),
    ("B prosa, VERO", VERO, PROSA, "non dovrebbe"),
    ("C tabellare, FALSO", FALSO, TABELLARE, "DEVE"),
    ("D prosa, FALSO", FALSO, PROSA, "DEVE"),
]


def main():
    print("  %-24s %-8s %8s  %-22s %s"
          % ("caso", "esito", "ground", "layer", "atteso su L4.2"))
    print("  " + "-" * 92)
    spieg = {}
    scatta = {}
    passa = {}
    for nome, claim, fonte, atteso in CASI:
        r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                                agent=None, source=fonte, grounding_llm=None,
                                ground_write=True)
        g = getattr(r, "grounding_score", None)
        warn = [w for w in (getattr(r, "warnings", None) or []) if isinstance(w, dict)]
        layers = [str(w.get("layer", "?")) for w in warn]
        l42 = [w for w in warn if str(w.get("layer", "")).startswith("L4.2")]
        k = nome[0]
        scatta[k] = bool(l42)
        if l42:
            spieg[k] = " ".join(str(l42[0].get("reason") or l42[0]).split())
        az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
        passa[k] = az == "persist"
        det = [x for x in layers if x not in {"L4-grounding", "L4-review", "moat", "gate"}]
        print("  %-24s %-8s %8s  %-22s %s"
              % (nome, "passa" if passa[k] else "CADE",
                 ("%.1f" % g) if g is not None else "None",
                 ", ".join(det) or "-", atteso))

    print("\n  --- IL TESTO DELL'AVVISO ---")
    for k in sorted(spieg):
        print("  %s: %s" % (k, spieg[k][:230]))

    print("\n=== SINTESI ===")
    if not (scatta.get("C") or scatta.get("D")):
        print("  ⚠️ L4.2 non scatta nemmeno sui claim SCAMBIATI: layer spento, nulla da dire.")
        return
    # ⚠️ Il confronto che conta non e' «scatta o no»: e' se il messaggio DIFFERISCE
    # fra il claim vero e quello falso. Se e' identico, l'avviso non porta informazione.
    for forma, vero, falso in (("tabellare", "A", "C"), ("prosa", "B", "D")):
        if vero in spieg and falso in spieg:
            uguale = spieg[vero] == spieg[falso]
            print("  %s %-10s: avviso sul VERO e sul FALSO %s"
                  % ("🔴" if uguale else "🟢", forma,
                     "IDENTICO parola per parola" if uguale else "DIVERSO"))
    if passa.get("C") or passa.get("D"):
        quali = [k for k in ("C", "D") if passa.get(k)]
        print("  🔴🔴 E IL CLAIM FALSO PASSA (%s): lo scambio di grandezza non e' fermato"
              % ", ".join(quali))
        print("       ne' dal giudice ne' dai layer.")
    if scatta.get("A") and scatta.get("B"):
        print("  🪞 La forma tabellare NON e' la causa: succede anche in prosa ⇒ il difetto")
        print("     e' sul lato CLAIM, dove il contesto del numero non viene mai trovato.")


main()
