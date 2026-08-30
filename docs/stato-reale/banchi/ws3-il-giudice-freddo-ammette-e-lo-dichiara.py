"""Il giudice freddo AMMETTE — e la promessa che lo circonda regge.

I quattro rossi «ricevuta» della suite del 30/08 portavano tutti la stessa riga::

    admitted id=… topic=t
      L4-skipped — source provided but the grounding judge was still loading
      - entailment NOT verified for THIS write

Un gate che **ammette quando il giudice non e' pronto** merita una misura, non
un'etichetta. Ma prima di misurare va cercato se e' PRESCRITTO — e lo e', in
quattro posti, con i numeri:

    anti_confab_gate.py  «Il write resta AMMESSO in ogni caso (regola della
                         provenance da fonte), etichettato onestamente
                         "entailment NOT verified": mai spacciato per
                         verificato, mai saltato in silenzio.»
    README.md:64         «…the gate fail-open (admit) … and says so on the write
                         with an `L4-skipped` advisory»
    README.md:367        «admitted WITH an explicit L4-skipped advisory (never
                         silently)»
    CHANGELOG.md:635     «SDK processes keep the synchronous one-time load.»
    CHANGELOG.md:716     «first write (~32 s -> 0.3 s, `7d64b91`)»

⇒ Il fail-open **non e' nascosto**. Restano DUE promesse verificabili, e un
limite dichiarato e' un debito finche' qualcuno non lo paga:

    ① «SDK processes keep the synchronous one-time load»
       ⇒ un processo SDK fresco non deve MAI ammettere per giudice freddo:
         la prima scrittura ASPETTA e riceve il verdetto del moat.
    ② «first write ~32 s -> 0.3 s»
       ⇒ l'ordine di grandezza del prezzo che l'utente paga per ①.

LA PREDIZIONE, scritta prima di eseguire: **entrambe reggono**. La macchina a
stati (`local_grounding.judge_state`) ha un posto solo che decide, e la riga che
conta e' esplicita::

    return "warming" if _delegate_only() else "ready"

CONDIZIONE DI FALSIFICAZIONE: se anche UNA scrittura di un processo SDK fresco
esce con `L4-skipped`, ① cade e il fail-open non e' confinato al server
delegate-only — sarebbe il reperto piu' grave, perche' la porta piu' usata
ammetterebbe senza che il chiamante abbia scelto quel regime.

CONTROLLO CHE DEVE POTER FALLIRE: la fonte **NEGA** il claim («500 euro» contro
«120 euro»), quindi a giudice pronto il moat DEVE quarantinare. Se non
quarantinasse nemmeno a caldo, non misurerei il freddo: misurerei un moat spento,
e ogni cella sarebbe illeggibile.

🟢 ESITO: **ENTRAMBE REGGONO**, e va detto con la stessa forza con cui direi il
contrario.

    proc   import   1a scrittura                 2a scrittura
    #0     0.51s    quarantined  36.24s          quarantined  0.31s
    #1     0.55s    quarantined  35.99s          quarantined  0.28s
    #2     0.52s    quarantined  35.69s          quarantined  0.28s

    ammesse per giudice freddo: 0 su 6

① **regge 6/6**: il carico e' sincrono, la prima scrittura aspetta e riceve il
verdetto. ② **regge**: dichiarato «~32 s -> 0.3 s», misurato **35,7-36,2 s ->
0,28-0,31 s** — stesso ordine, macchina diversa, 12% sopra il numero pubblicato.

🔑 ALLORA PERCHE' I QUATTRO ROSSI? **La catena, cinque anelli, tutti letti:**

    1. `HIPPO_ENCODE_DELEGATE_ONLY='1'` e' ATTIVA nell'ambiente di questa
       macchina (verificato: la suite la eredita)
    2. -> `_delegate_only()` True                     `local_grounding.py:590`
    3. -> `judge_state()` restituisce «warming»       `local_grounding.py:383`
       (lo scorer non e' caricato E il daemon non ha ancora giudicato per
        questo processo: `_GATE_DELEGATO["ok"]` False)
    4. -> `_advisory_l4_skipped()` -> `L4-skipped`    `anti_confab_gate.py:1797`
    5. -> il write e' AMMESSO con l'avviso, e i test che attendono
       `quarantined` cadono

⇒ **Rosso d'AMBIENTE, e l'ambiente e' una variabile**: non «la macchina e'
strana», ma *quella riga di env*. Su una macchina senza quella variabile il
caricamento e' sincrono e i quattro test passano.

⚠️ E DUE COSE CHE QUESTO LASCIA APERTE, per chi le possiede:
  · **La suite eredita quella variabile e la CI (probabilmente) no** ⇒ i due
    regimi non misurano la stessa cosa, e quattro rossi locali possono non
    esistere in CI (o il contrario). Materia di chi mantiene la CI.
  · **Il test non dichiara il regime che richiede.** La ricevuta dice
    benissimo cosa e' successo; l'assert che cade dice solo «'quarantined' not
    in "admitted…"», e chi legge risale da solo. Un test che presuppone il
    giudice pronto potrebbe interrogare `judge_state()` e saltare dicendolo.
    **Proposta, non cura: i test non sono miei.**

REGIME: store TEMPORANEO per ogni processo, `HIPPO_DATA_DIR` a una temp; lo
store di Aurelio NON e' toccato. ⚠️ Il banco costa ~2 minuti: tre processi che
caricano il cross-encoder da freddo, ed e' esattamente cio' che misura.
⛔ NON esegue `verimem warmup` (~2,3 GB): il modello e' gia' presente.

    python docs/stato-reale/banchi/ws3-il-giudice-freddo-ammette-e-lo-dichiara.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

PROCESSI = 3

#: la fonte NEGA il claim: a giudice pronto il moat deve quarantinare.
CLAIM = "La penale e' di 500 euro al giorno."
FONTE = "Il contratto fissa la penale in 120 euro al giorno."

FIGLIO = r'''
import json, os, sys, tempfile, time
os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()
t0 = time.perf_counter()
from verimem.client import Memory
mem = Memory(os.environ["HIPPO_DATA_DIR"] + "/cold.db")
t_imp = time.perf_counter() - t0
claim, fonte = sys.argv[1], sys.argv[2]
out = []
for i in range(2):
    a = time.perf_counter()
    r = mem.add(f"{claim} (n.{i})", topic=f"cold/{i}", source=fonte, validate="full")
    lay = [str(w.get("layer")) for w in (r.get("warnings") or []) if isinstance(w, dict)]
    out.append({"s": r.get("status"), "freddo": any("L4-skipped" in x for x in lay),
                "dt": round(time.perf_counter() - a, 2)})
print(json.dumps({"import_s": round(t_imp, 2), "w": out}, default=str))
'''


def main() -> int:
    print("  PROMESSE SOTTO ESAME")
    print("    ① CHANGELOG:635  «SDK processes keep the synchronous one-time load»")
    print("    ② CHANGELOG:716  «first write (~32 s -> 0.3 s)»")
    print(f"\n  claim: {CLAIM}")
    print(f"  fonte: {FONTE}   ⇒ NEGA: a giudice pronto il moat DEVE fermare")
    print("\n  ambiente rilevante di QUESTA macchina:")
    for k in ("HIPPO_ENCODE_DELEGATE_ONLY",):
        v = os.environ.get(k)
        print(f"    {k} = {'(non impostata)' if v is None else v!r}")

    print(f"\n  {'proc':<6} {'import':>7}  {'1a scrittura':<28} {'2a scrittura':<28}")
    print("  " + "-" * 74)
    freddi = 0
    fermati = 0
    celle = 0
    for k in range(PROCESSI):
        p = subprocess.run([sys.executable, "-c", FIGLIO, CLAIM, FONTE],
                           capture_output=True, text=True, timeout=1800)
        if p.returncode != 0:
            print(f"  #{k:<5} PROCESSO-MORTO exit={p.returncode} "
                  f"coda={p.stderr.strip()[-90:]!r}")
            continue
        d = json.loads(p.stdout.strip().splitlines()[-1])
        testo = []
        for w in d["w"]:
            celle += 1
            freddi += w["freddo"]
            fermati += w["s"] == "quarantined"
            marca = "L4-skipped(freddo)" if w["freddo"] else str(w["s"])
            testo.append(f"{marca:<20}{w['dt']:>6.2f}s")
        print(f"  #{k:<5} {d['import_s']:>6.2f}s  {testo[0]:<28} {testo[1]:<28}")

    if celle == 0:
        print("\n  NESSUNA CELLA: tutti i processi sono morti. NESSUN VERDETTO.")
        return 1

    print(f"\n  [1] CONTROLLO — scritture FERMATE dal moat: {fermati}/{celle}")
    if fermati < celle:
        print("      CONTROLLO CADUTO: una fonte che NEGA non quarantina ⇒ sto")
        print("      misurando un moat spento, non il giudice freddo.")
        print("      NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    print(f"     ammesse per GIUDICE FREDDO: {freddi}/{celle}")
    if freddi == 0:
        print("     🟢 ① REGGE: il carico SDK e' sincrono, la prima scrittura")
        print("     aspetta e riceve il verdetto. Il fail-open a giudice freddo")
        print("     esiste, e' DICHIARATO, ed e' confinato al regime delegate-only.")
        print("     ⇒ i rossi «ricevuta» della suite vengono da")
        print("       HIPPO_ENCODE_DELEGATE_ONLY nell'ambiente, non dall'SDK.")
    else:
        print("     🔴 ① CADE: un processo SDK fresco AMMETTE per giudice freddo,")
        print("     quindi il fail-open non e' confinato al delegate-only e la")
        print("     porta piu' usata ammette senza che il chiamante l'abbia scelto.")

    print(f"\n  ⚠️ LIMITI: {PROCESSI} processi, una macchina, un claim, italiano.")
    print("     Il numero di ② dipende dal disco e dalla cache del SO: dice")
    print("     l'ordine di grandezza, non un tempo da citare altrove.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
