# -*- coding: utf-8 -*-
r"""ROTTO lo 0/18 di @ws3 — ma la sua PREDIZIONE regge: cadono cose diverse.

    cifra senza    ammessi 0/4   L4.1 su 4/4      <- controllo: riproduce il suo 0/18
    cifra TRAINO   ammessi 0/4   L4.1 su 4/4      <- la SUA predizione REGGE
    PAROLE senza   ammessi 3/4   L4.1 su 0/4
    PAROLE TRAINO  ammessi 4/4   L4.1 su 0/4      <- rotto

    EN colli    senza=bloc  TRAINO=bloc  |  senza=AMM   TRAINO=AMM
    EN voti     senza=bloc  TRAINO=bloc  |  senza=AMM   TRAINO=AMM
    IT colli    senza=bloc  TRAINO=bloc  |  senza=AMM   TRAINO=AMM
    IT assunti  senza=bloc  TRAINO=bloc  |  senza=bloc  TRAINO=AMM   <- il traino decide

CHIESTO DA @ws3, che ha proposto lui stesso il proprio risultato all'attacco:
«il dettaglio con una cifra e' fermato 0 su 18 in sei scritture, sempre da `L4.1`;
`_assenti = valori_non_nella_fonte(proposition, source)` prende i valori del CLAIM
e li cerca nella fonte — criterio lessicale, nessun giudizio semantico. ⇒ La
zavorra NON deve scalfire il numerico».

⇒ ① LA SUA PREDIZIONE E' VERA, ALLA LETTERA. Sulle cifre il traino non sposta
niente: 0/4 senza e 0/4 con, `L4.1` parla 4 volte su 4 in entrambe le colonne. La
sua difesa era giusta: `L4.1` non giudica, cerca una stringa, e una frase in piu'
non ha niente da spostare.
⇒ ② MA IL SUO 0/18 COME GARANZIA CADE, perche' la premessa «il caso e' numerico»
la decide `L4.1`, non noi. Misurato oggi: **vede il numero se e solo se compare un
glifo 0-9** («340 mila» bloccato, «trecentoquarantamila» no). Scritto a parole, per
lui quel caso NON E' PIU' NUMERICO: 3/4 ammessi, `L4.1` muto su 4 casi su 4.
⇒ ③ E IL TRAINO SCALFISCE DAVVERO — non le cifre, il resto: da 3/4 a 4/4. La riga
`IT assunti` e' la prova per contrasto: bloccato senza traino, ammesso con. ⇒ Le due
leve **si compongono**, come traino+implicita (IT 3/10 -> 6/10).

🔑 LA DISTINZIONE CHE NE ESCE, ed e' quella che serve alla vetrina: «il numerico e'
protetto» e' vero SE «numerico» significa *scritto in cifra*. Chi legge la riga
capisce *un claim che contiene un numero* — e quella lettura e' falsa. **Non e' una
correzione al numero di @ws3: e' una qualificazione della POPOLAZIONE su cui vale.**
⚖️ E si salda col regalo che lui stesso mi ha girato: `L4.1` protegge dal numero
INVENTATO, non da quello OMESSO — @ws4 ha misurato «pochi pazienti» contro «30 su
40» → **98.1, zero layer**. Vaghezza e numerali sono **la stessa classe**: in
nessuno dei due il claim porta un glifo 0-9.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-rompo-lo-zero-su-diciotto-di-ws3.py <dir-temp>
⚠️ Vuole una dir TEMPORANEA: scrive in HIPPO_DATA_DIR, mai lo store principale.
⚠️ REGIME: nessuna delle 10 variabili d'ambiente di questa macchina e' letta da
`anti_confab_gate.py`, e `cli.py:1867` / `client.py:529` / `mcp_server.py` chiamano
questa stessa porta. Dettaglio in `ws5-il-traino-contro-la-cifra.py`.
"""
import os, sys
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]
from verimem.anti_confab_gate import run_validation_gate

#: (etichetta, fonte, claim con la CIFRA inventata, claim con lo stesso numero A PAROLE)
CASI = [
 ("EN colli",  "Logistics note: the shipment was delivered to the Bari depot.",
   "340 parcels were delivered to the Bari depot.",
   "Three hundred and forty parcels were delivered to the Bari depot."),
 ("EN voti",   "Minutes: the board approved the budget.",
   "The board approved the budget with 12 votes in favour.",
   "The board approved the budget with twelve votes in favour."),
 ("IT colli",  "Nota logistica: la merce e' stata consegnata al deposito di Bari.",
   "340 colli sono stati consegnati al deposito di Bari.",
   "Trecentoquaranta colli sono stati consegnati al deposito di Bari."),
 ("IT assunti","Report: la filiale di Verona ha assunto nuovo personale.",
   "La filiale di Verona ha assunto 27 persone.",
   "La filiale di Verona ha assunto ventisette persone."),
]

def prova(claim, src):
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=src, grounding_llm=None, ground_write=True)
    ws = [w.get("layer", "?") if isinstance(w, dict) else str(w)
          for w in (getattr(r, "warnings", None) or [])]
    return (getattr(r, "action", "?") == "persist",
            any(str(w).startswith("L4.1") for w in ws))

tot = {k: [0, 0] for k in ("cifra senza", "cifra TRAINO", "PAROLE senza", "PAROLE TRAINO")}
print("")
for eti, src, c_cifra, c_parole in CASI:
    out = []
    for k, claim in (("cifra senza", c_cifra), ("cifra TRAINO", src + " " + c_cifra),
                     ("PAROLE senza", c_parole), ("PAROLE TRAINO", src + " " + c_parole)):
        ok, ha41 = prova(claim, src)
        tot[k][0] += int(ok); tot[k][1] += int(ha41)
        out.append("%s=%s" % (k.split()[-1][:6], "AMM" if ok else "bloc"))
    print("   %-11s %s" % (eti, "  ".join(out)))
print("")
for k in ("cifra senza", "cifra TRAINO", "PAROLE senza", "PAROLE TRAINO"):
    print("   %-14s ammessi %d/%d   L4.1 su %d/%d" % (k, tot[k][0], len(CASI), tot[k][1], len(CASI)))
