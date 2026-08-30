"""La somiglianza non misura l'indipendenza — ma una soglia c'e', e il margine e' largo.

NASCE DA UN VOTO. Il 30/08 lead-audit ha aperto il voto su una **guardia
anti-eco** per `L1.13`, dopo che ho misurato che il perdono introdotto da
`e3ecd7f1` si ottiene **5 volte su 5** ripassando il claim come `source`.

Prima di votare mi sono cercato la controipotesi migliore, ed e' questa:

    ⚠️ la guardia anti-eco e la cura `e3ecd7f1` tirano in direzioni OPPOSTE
    sullo STESSO caso. La cura perdona *perche' la fonte ricalca il claim*; la
    guardia toglie il perdono *perche' la fonte ricalca il claim*.

🔑 Cio' che distingue i due casi **non e' la somiglianza: e' se la fonte sia
INDIPENDENTE**. E la somiglianza testuale non misura l'indipendenza. Se la
guardia si tara sulla somiglianza, rischia di colpire **proprio i verbali
d'ufficio che la cura esisteva per salvare** — cioe' di riaprire il falso
allarme che il dossier ⑲ di ws4 identifica come *il verso che arriva
all'utente*.

LA GRANDEZZA MISURATA — **copertura della fonte**: quanta parte della FONTE e'
gia' contenuta nel claim. `1.00` significa «la fonte non aggiunge nulla».
Non e' una distanza fra stringhe: e' **quanto la fonte porta di suo**, che e' il
candidato piu' vicino all'indipendenza fra le cose che si possono contare.

LA PREDIZIONE, scritta prima di eseguire: **le due popolazioni si separano**,
perche' un verbale vero porta sempre qualcosa in piu' — un numero di protocollo,
un'ora, una firma, un chi. E' quel *di piu'* il segnale, non la distanza.

CONDIZIONE DI FALSIFICAZIONE: se gli intervalli si **sovrappongono**, nessuna
soglia su questa grandezza separa l'eco dal verbale legittimo, la guardia
colpirebbe cio' che la cura proteggeva, e il voto andrebbe dato **con una
condizione molto piu' pesante** — o negato.

CONTROLLO CHE DEVE POTER FALLIRE: **oggi devono passare tutti e sei**. Gli ECO
perche' il perdono e' attivo (e' il difetto sotto esame); i VERBALI perche' sono
**fatti veri con una fonte che li sostiene** e devono passare in ogni caso. Se un
verbale fosse gia' fermato oggi, non misurerei la guardia: misurerei un gate che
sbaglia gia' da solo.

🟢 ESITO: **PREDIZIONE RETTA, e il margine e' largo.**

    popolazione   copertura      esito oggi
    ECO               1.00       passa    (×3, IT/EN)
    VERBALE           0.29       passa    «Verbale n.114: …chiusa il 3 marzo dal responsabile»
    VERBALE           0.31       passa    «Bolla 2231 — …alle 17:40, firmata dal magazziniere»
    VERBALE           0.33       passa    «Minutes: …on 14 March by the external firm»

    ECO 1.00-1.00   ·   VERBALE 0.29-0.33   ·   margine 0,33 → 1,00

⇒ **La guardia e' tarabile senza sacrificare il caso che la cura protegge**, e le
due condizioni operative escono dalla misura, non dal gusto:

    (a) tarare su «la fonte NON AGGIUNGE NULLA» (copertura ~1.00), non su
        «si somigliano»
    (b) la guardia NON deve quarantinare: deve NEGARE IL PERDONO, cioe'
        rimettere in gioco `L1.13` come se la fonte non ci fosse — il verso piu'
        conservativo dello stringere, che e' esattamente la riserva di ws4

⚠️ E IL LIMITE, dichiarato prima che qualcuno lo trovi: **3+3 casi scritti da
me**, e **un caso resta indistinguibile PER COSTRUZIONE** — una fonte legittima
*minimale*, identica al claim, perche' l'utente ha copiato una riga sola. Li' la
copertura e' `1.00` come l'eco e **nessuna taratura le separa**: il gate non puo'
sapere se quel testo sia un documento vero o l'eco dell'agente.
⇒ **La guardia deve SCEGLIERE un verso di errore su quel caso**, e (b) e' la
scelta: un falso allarme su una citazione minimale, in cambio della chiusura di
un perdono **totale**. **Costo accettato, da scrivere nel DoD — non da scoprire
dopo.**

REGIME: store TEMPORANEO per ogni scrittura; quello di Aurelio NON e' toccato.

    python docs/stato-reale/banchi/ws3-la-somiglianza-non-misura-l-indipendenza.py
"""

from __future__ import annotations

import json
import subprocess
import sys

FIGLIO = r'''
import json, os, sys, tempfile
os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()
from verimem.client import Memory
mem = Memory(os.environ["HIPPO_DATA_DIR"] + "/g.db")
claim, fonte = sys.argv[1], sys.argv[2]
r = mem.add(claim, topic="voto/eco", source=fonte, validate="full")
lay = [str(w.get("layer")) for w in (r.get("warnings") or []) if isinstance(w, dict)]
print(json.dumps({"status": r.get("status"), "layers": lay},
                 default=str, ensure_ascii=False))
'''

#: ECO — la fonte E' il claim: cio' che la guardia deve colpire.
ECO: list[str] = [
    "La pratica e' stata chiusa il 3 marzo.",
    "La consegna e' stata completata.",
    "The compliance audit was completed.",
]

#: VERBALE — fonte VERA e indipendente, e CORTA: dice poco piu' del claim.
#: E' il caso che `e3ecd7f1` esiste per proteggere, e che la guardia NON deve
#: colpire.
VERBALE: list[tuple[str, str]] = [
    ("La pratica e' stata chiusa.",
     "Verbale n.114: la pratica e' stata chiusa il 3 marzo dal responsabile "
     "di settore."),
    ("La consegna e' stata completata.",
     "Bolla 2231 - la consegna e' stata completata alle 17:40, firmata dal "
     "magazziniere."),
    ("The compliance audit was completed.",
     "Minutes: the compliance audit was completed on 14 March by the external "
     "firm."),
]


def copertura(claim: str, fonte: str) -> float:
    """Quanta parte della FONTE e' gia' nel claim. 1.0 = non aggiunge nulla."""
    a = set(claim.lower().split())
    b = set(fonte.lower().split())
    return len(a & b) / max(1, len(b))


def _esito(claim: str, fonte: str) -> str:
    p = subprocess.run([sys.executable, "-c", FIGLIO, claim, fonte],
                       capture_output=True, text=True, timeout=900)
    if p.returncode != 0:
        return f"MORTO exit={p.returncode}"
    d = json.loads(p.stdout.strip().splitlines()[-1])
    if d["status"] != "quarantined":
        return "passa"
    return f"FERMATO {','.join(d['layers']) or '?'}"


def main() -> int:
    print("  GRANDEZZA: «copertura della fonte» = quanta parte della FONTE e'")
    print("  gia' nel claim. 1.00 = la fonte non aggiunge nulla.\n")
    print(f"  {'popolazione':<12} {'copertura':>10}   {'esito oggi':<18} claim")
    print("  " + "-" * 74)

    cop_eco: list[float] = []
    cop_ver: list[float] = []
    passano = 0
    for claim in ECO:
        k = copertura(claim, claim)
        cop_eco.append(k)
        e = _esito(claim, claim)
        passano += e == "passa"
        print(f"  {'ECO':<12} {k:>10.2f}   {e:<18} {claim[:32]}")
    for claim, fonte in VERBALE:
        k = copertura(claim, fonte)
        cop_ver.append(k)
        e = _esito(claim, fonte)
        passano += e == "passa"
        print(f"  {'VERBALE':<12} {k:>10.2f}   {e:<18} {claim[:32]}")

    tot = len(ECO) + len(VERBALE)
    print(f"\n  [1] CONTROLLO — passano tutti oggi: {passano}/{tot}")
    if passano < tot:
        print("      CONTROLLO CADUTO: un caso e' gia' fermato oggi ⇒ non misuro")
        print("      la guardia, misuro un gate che sbaglia gia' da solo.")
        print("      NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    print(f"     ECO      copertura {min(cop_eco):.2f} - {max(cop_eco):.2f}")
    print(f"     VERBALE  copertura {min(cop_ver):.2f} - {max(cop_ver):.2f}")
    if min(cop_eco) > max(cop_ver):
        print(f"     🟢 SI SEPARANO — margine {max(cop_ver):.2f} → {min(cop_eco):.2f}.")
        print("     La guardia e' tarabile su questa grandezza senza sacrificare")
        print("     il verbale legittimo: tarare su «la fonte NON AGGIUNGE NULLA»,")
        print("     e NEGARE IL PERDONO invece di quarantinare.")
    else:
        print("     🔴 SI SOVRAPPONGONO: nessuna soglia su questa grandezza separa")
        print("     l'eco dal verbale legittimo corto ⇒ la guardia colpirebbe cio'")
        print("     che la cura proteggeva, e il voto va dato con una condizione")
        print("     molto piu' pesante, o negato.")

    print(f"\n  ⚠️ LIMITI: {len(ECO)}+{len(VERBALE)} casi scritti da me, IT/EN. E un caso")
    print("     resta indistinguibile PER COSTRUZIONE: una fonte legittima")
    print("     MINIMALE, identica al claim, ha copertura 1.00 come l'eco.")
    print("     Nessuna taratura le separa ⇒ la guardia deve SCEGLIERE un verso")
    print("     di errore, e va scritto nel DoD come costo accettato.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
