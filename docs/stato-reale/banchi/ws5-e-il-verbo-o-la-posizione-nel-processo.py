r"""Il mio reperto sui verbi regge, o era la POSIZIONE nel processo?

⚠️ **Banco che prova a distruggere una misura mia**, non del prodotto.

@ws8 alle 20:39-20:43 ha isolato un confondente che tocca **tutti** i banchi che
fanno piu' scritture in un processo: «*la differenza vera e' la POSIZIONE DELLA
SCRITTURA NEL PROCESSO*» - e la causa: «*`ENGRAM_ENCODE_SERVICE=0` NON disarma
`L1.20` se `is_loaded()=True`, e il modello si carica alla PRIMA scrittura*».

⇒ **Il mio reperto delle 20:55 e' esposto in pieno.** Nel banco dei dieci verbi
`concluso` e' la **prima** chiamata e **passa**; `completato` e' la **seconda** e
**cade**. Se a decidere fosse l'ordine e non la parola, il reperto («*4 verbali
veri su 10 cadono per il verbo*») sarebbe un **artefatto della sequenza**.

IL TEST, e non ha vie di mezzo: **gli stessi dieci verbi in tre ordini diversi**.
    ordine 1  originale
    ordine 2  INVERTITO
    ordine 3  originale, ma preceduto da una scrittura di riscaldamento
              (cosi' il modello e' gia' carico anche per il primo verbo)

    se cadono SEMPRE gli stessi quattro   → e' il VERBO, il reperto regge
    se cambiano con l'ordine              → era la POSIZIONE, e ritiro tutto

⚠️ **Un banco che puo' solo confermarmi non serve a niente**: questo puo'
demolire un reperto che ho gia' consegnato sul canale un'ora fa, ed e' il motivo
per cui lo scrivo prima di difenderlo.

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) da `trap` ·
`ground_write=True` · porta `run_validation_gate` · **un processo solo**, che e'
esattamente la condizione in cui il confondente vive.

ESITO - **il reperto REGGE: e' il verbo, non la posizione**::

    ordine di esecuzione               verbi caduti                                 verdetto
    1. originale                       approvato, completato, validato, verificato  ✔ identico
    2. INVERTITO                       approvato, completato, validato, verificato  ✔ identico
    3. originale dopo riscaldamento    approvato, completato, validato, verificato  ✔ identico

✅ **Tre ordini, lo stesso identico insieme di quattro.** Il confondente che
@ws8 ha isolato **esiste** - la sua misura lo dimostra sul suo caso - **ma non
tocca questa**: l'insieme dei caduti **non dipende dall'ordine di esecuzione**,
e nemmeno dall'avere il modello gia' carico alla prima chiamata.
⇒ Il reperto delle 20:55 («*4 verbali veri su 10 cadono per il verbo*») **non e'
un artefatto della sequenza**.

🔑 **E IL METODO COSTA TRENTA SECONDI, VALE PER OGNI BANCO DI STASERA.** Il
confondente di @ws8 minaccia **qualunque** misura che faccia piu' scritture in
un processo - cioe' quasi tutti i nostri banchi. **Rieseguire in ordine
INVERTITO lo falsifica o lo conferma senza cambiare nient'altro**: se l'insieme
degli esiti e' lo stesso, l'ordine non decide; se cambia, il banco misurava la
posizione. Non serve un processo per cella (che @ws8 ha dovuto costruire): serve
**un giro in piu' sullo stesso banco**.
⇒ E' un caso della regola che @ws6 ha nominato alle 20:34 - «*il progresso viene
da UNA COLONNA IN PIU' sullo stesso banco*»: qui la colonna in piu' e' **lo
stesso banco letto al contrario**.

⚖️ **CIO' CHE QUESTO BANCO NON DICE**: non falsifica il reperto di @ws8. Lei
misura un **claim diverso** con `L1.20` e il servizio di encoding; io misuro
**quali verbi cadono** su una fonte fissa. **Due misure possono essere
entrambe vere**: il confondente c'e' dove lei l'ha trovato, e non c'e' dove ho
guardato io. Chi le mettesse in contraddizione leggerebbe male tutte e due.

REGIME: build corrente · store TEMPORANEO da `trap` · `ground_write=True` ·
porta `run_validation_gate` · **un processo solo**, che e' la condizione in cui
il confondente vive.
⚖️ PUNTI DEBOLI: tre ordini su 3.628.800 possibili - un ordine avverso potrebbe
esistere; guardo **l'insieme dei caduti**, non i punteggi (che possono muoversi
senza cambiare l'esito); una fonte sola.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-e-il-verbo-o-la-posizione-nel-processo.py <dir-temp>
"""
import os
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

FONTE = ("Il collaudo della linea 3 si e' concluso il 12 marzo con esito positivo "
         "e la linea e' stata approvata dalla commissione.")
CLAIM = "Il collaudo della linea 3 e' stato %s il 12 marzo."
VERBI = ["concluso", "completato", "ultimato", "effettuato", "eseguito",
         "svolto", "superato", "approvato", "validato", "verificato"]

#: quelli caduti nel banco originale: l'ipotesi da falsificare
ATTESI = {"completato", "approvato", "validato", "verificato"}


def _cade(verbo):
    r = run_validation_gate(proposition=CLAIM % verbo, verified_by=None, topic=None,
                            agent=None, source=FONTE, grounding_llm=None,
                            ground_write=True)
    az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
    return az != "persist"


def giro(nome, ordine):
    caduti = {v for v in ordine if _cade(v)}
    uguale = caduti == ATTESI
    print("  %-34s %-44s %s"
          % (nome, ", ".join(sorted(caduti)) or "(nessuno)",
             "✔ identico all'originale" if uguale else "🔴 DIVERSO"))
    return caduti


def main():
    print("  %-34s %-44s %s" % ("ordine di esecuzione", "verbi caduti", "verdetto"))
    print("  " + "-" * 100)
    a = giro("1. originale", VERBI)
    b = giro("2. INVERTITO", list(reversed(VERBI)))
    _cade("registrato")   # riscaldamento: il modello e' gia' carico
    c = giro("3. originale dopo riscaldamento", VERBI)

    print("\n=== SINTESI ===")
    tutti_uguali = (a == b == c == ATTESI)
    print("  attesi dal banco originale    %s" % ", ".join(sorted(ATTESI)))
    print("  i tre ordini coincidono?      %s" % ("SI" if a == b == c else "NO"))
    print("  coincidono con l'originale?   %s" % ("SI" if tutti_uguali else "NO"))
    if tutti_uguali:
        print("\n  ✅ E' IL VERBO. Il confondente di @ws8 esiste ma NON tocca questa")
        print("     misura: l'insieme dei caduti non dipende dall'ordine.")
    else:
        print("\n  🔴 ERA LA POSIZIONE. Il reperto delle 20:55 va RITIRATO:")
        print("     l'insieme dei caduti cambia con l'ordine di esecuzione.")
        for nome, s in (("originale", a), ("invertito", b), ("riscaldato", c)):
            print("      %-12s in piu': %-28s in meno: %s"
                  % (nome, ", ".join(sorted(s - ATTESI)) or "-",
                     ", ".join(sorted(ATTESI - s)) or "-"))


main()
