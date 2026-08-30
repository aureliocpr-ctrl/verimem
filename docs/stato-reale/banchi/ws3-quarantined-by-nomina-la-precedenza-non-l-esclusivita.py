"""`quarantined_by` nomina CHI HA LA PRECEDENZA, non chi da solo avrebbe fermato.

PERCHE' ESISTE QUESTO BANCO. Alle 18:51 @ws7 «Lanterna» ha consegnato
`LANT-71`: sui 29 claim VERI persi di `truthfulqa_pairs_heldout`, **25 hanno
`quarantined_by == 'moat'`** ⇒ *«a buttare i veri e' il moat, non i layer
lessicali; chi cura i layer lessicali cura il 14% del problema»*.
Il reperto e' nel mio perimetro (**il gate e cosa DICE**) e la domanda che gli
manca e' una sola: **quel campo dice «ha deciso lui» o «ha deciso lui SOLO»?**

LA RISPOSTA E' NEL SORGENTE, ed e' una precedenza a cinque rami
(`client.py:291`, `chi_ha_quarantinato`)::

    store-screen  ->  MOAT  ->  L1  ->  _BLOCK_LAYER_PRIORITY  ->  agito  ->  'gate'

⇒ **`moat` viene PRIMA di ogni layer lessicale** (tranne `store-screen`). Quando
il moat fallisce, qualunque cosa abbia fatto `L1`/`L3`/`L4` **non compare nel
campo**. ⚠️ E la precedenza e' **deliberata**, scritta al call site: *«L1 esiste
per intercettare le auto-affermazioni … ribaltare la precedenza aprirebbe
esattamente quella porta»*. **Non e' un difetto: e' un criterio di attribuzione,
e chi conta il campo deve sapere quale.**

MA IL SORGENTE E' IL LIVELLO SBAGLIATO PER CHIUDERE — «il livello a cui misuri
decide il verdetto». Quindi la stessa cosa **alla porta del prodotto**, due
celle appaiate, stessa fonte che NEGA, un solo fattore che cambia:

    cella                            status        quarantined_by   moat     strati
    A  solo numerico                 quarantined   moat             failed   L4.1,L4-grounding
    B  numerico + auto-affermazione  quarantined   moat             failed   L1.10,L1.15,L4.1,L4-grounding

    strati in piu' in B: ['L1.10', 'L1.15']       <- IL CONTROLLO, e regge

🔴 **In B hanno agito ANCHE `L1.10` e `L1.15`, e il campo dice ancora `moat`.**

⇒ **COSA SIGNIFICA PER `LANT-71`, e non e' una smentita.** Il 25/29 e' un
**tetto superiore** alla responsabilita' ESCLUSIVA del moat, non la misura.
La direzione del reperto puo' benissimo reggere — **ma il numero che la
sostiene non e' quello che si crede**, e il controllo che separa le due letture
si fa **sui dati che @ws7 ha gia'**:

    dei 25 con quarantined_by == 'moat', quanti hanno ANCHE un layer
    lessicale nei `warnings` della stessa ricevuta?
        0   -> la lettura di LANT-71 vale ESATTAMENTE come scritta
        k>0 -> solo 25-k sarebbero passati con un moat perfetto, e la
               conseguenza operativa («curare i lessicali cura il 14%»)
               si sposta di k

⚠️ E UNA SECONDA OSSERVAZIONE SULLO STRUMENTO, sulla seconda tabella di
`LANT-71` (*falsi fermati / veri persi* per layer): contiene la riga
`L1-domain-precision-observe  2 / 0`. Un layer `*-observe` **non puo' essere il
decisore**: `_is_advisory_layer` (`client.py:3586`) lo definisce come *«an
OBSERVE-mode advisory: it surfaces a would-be block for MEASUREMENT but does
not»* bloccare, e il commento di `chi_ha_quarantinato` dichiara che `agito` sono
i blocking layer, *«avvisi `*-observe` esclusi»*. ⇒ **Quella tabella conta la
CO-OCCORRENZA degli avvisi, la prima conta le DECISIONI: due strumenti
diversi.** Nessuno dei due e' sbagliato; leggerli come uno solo si'.

⚠️ LIMITI, dichiarati. Due celle, un claim, italiano, porta SDK, store
temporaneo, `ENGRAM_L1_DOMAIN_PRECISION=0`. **Non ho eseguito la popolazione di
@ws7**: qui si misura il COMPORTAMENTO DEL CAMPO, non il suo reperto. E non
dico che la precedenza vada cambiata — e' dichiarata e motivata al call site.

    python docs/stato-reale/banchi/ws3-quarantined-by-nomina-la-precedenza-non-l-esclusivita.py
"""

from __future__ import annotations

import json
import subprocess
import sys

FONTE = "Il contratto fissa la penale in 120 euro al giorno."
CELLE: list[tuple[str, str]] = [
    ("A  solo numerico", "La penale e' di 500 euro al giorno."),
    ("B  numerico + auto-affermazione",
     "Ho verificato che funziona: la penale e' di 500 euro al giorno."),
]

FIGLIO = r'''
import json, os, sys, tempfile
os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()
os.environ["ENGRAM_L1_DOMAIN_PRECISION"] = "0"
from verimem.client import Memory
r = Memory().add(sys.argv[1], topic="prec/x", validate="full", source=sys.argv[2])
lay = [str(w.get("layer")) for w in (r.get("warnings") or []) if isinstance(w, dict)]
print(json.dumps({"status": r.get("status"), "qb": r.get("quarantined_by"),
                  "moat": r.get("moat"), "lay": lay},
                 default=str, ensure_ascii=False))
'''


def main() -> int:
    print("  PRECEDENZA dichiarata in `chi_ha_quarantinato` (client.py:291):")
    print("    store-screen -> MOAT -> L1 -> _BLOCK_LAYER_PRIORITY -> agito -> 'gate'\n")
    print(f"  {'cella':<34} {'status':<12} {'quarantined_by':<16} "
          f"{'moat':<8} strati")
    print("  " + "-" * 96)

    letto: dict[str, dict] = {}
    for nome, claim in CELLE:
        p = subprocess.run([sys.executable, "-c", FIGLIO, claim, FONTE],
                           capture_output=True, text=True, timeout=1800)
        if p.returncode != 0:
            print(f"  {nome:<34} PROCESSO MORTO exit={p.returncode} "
                  f"{p.stderr.strip()[-100:]!r}")
            return 1
        d = json.loads(p.stdout.strip().splitlines()[-1])
        letto[nome[0]] = d
        print(f"  {nome:<34} {str(d['status']):<12} {str(d['qb']):<16} "
              f"{str(d['moat']):<8} {','.join(d['lay']) or '-'}")

    a, b = letto["A"], letto["B"]
    extra = [x for x in b["lay"] if x not in a["lay"]]
    print("\n  CONTROLLO — la cella B deve DAVVERO portare un layer in piu':")
    print(f"     strati in piu' in B: {extra or 'NESSUNO'}")
    if not extra:
        print("     CONTROLLO CADUTO: le due celle non differiscono ⇒ non misuro")
        print("     la precedenza, misuro due volte la stessa cosa.")
        print("     NESSUN VERDETTO.")
        return 1
    if b["moat"] != "failed":
        print("     CONTROLLO CADUTO: in B il moat non fallisce ⇒ il ramo che")
        print("     voglio osservare non viene nemmeno percorso. NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    if b["qb"] == "moat":
        print("     🔴 IL CAMPO NOMINA LA PRECEDENZA, NON L'ESCLUSIVITA':")
        print(f"     in B hanno agito ANCHE {extra}, e `quarantined_by` dice 'moat'.")
        print("     ⇒ contare 'moat' nel campo NON dice che i layer lessicali")
        print("     avrebbero lasciato passare quel fatto: e' un TETTO SUPERIORE")
        print("     alla responsabilita' esclusiva del moat.")
    else:
        print(f"     🟢 in B il campo dice {b['qb']!r}: la precedenza non schiaccia")
        print("     il layer lessicale ⇒ il conteggio per campo si legge come")
        print("     esclusivita'.")

    print("\n  ⚠️ LIMITI: due celle, un claim, italiano, porta SDK, store")
    print("     temporaneo. Si misura il COMPORTAMENTO DEL CAMPO, non il")
    print("     reperto di @ws7 sulla sua popolazione.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
