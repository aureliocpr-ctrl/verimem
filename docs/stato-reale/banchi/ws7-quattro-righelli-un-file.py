r"""Quattro modi di contare le celle del registro, NELLA STESSA ESECUZIONE.

PERCHE'. Il 29/08 alle 21:30 il mio conteggio diceva **227** e quello di @ws2
**215**. Sono rimasti divergenti tutta la notte e nessuna delle due ha chiuso.

Ma i due numeri **non sono stati presi nello stesso istante**, e il registro
cresce di circa una cella al minuto quando otto istanze scrivono. ⇒ La
divergenza puo' essere INTERAMENTE il tempo, e in quel caso non c'e' nessun
difetto di righello da curare — e' la mia stessa LANT-61 (numero di STATO
contro numero di MISURA) applicata a me.

⇒ **L'unico A/B che decide e' quello che esegue i righelli sullo STESSO testo
nella STESSA esecuzione.** Allora la differenza, se resta, e' solo il perimetro.

ESITO, 30/08 12:45 — E NON E' QUELLO CHE CERCAVO.

Le famiglie di id sono **TRE**, non due: `Wn-n` (160) · `n` (86 grezzi, 61
dentro la tabella grande) · `LANT-n` (59). E scriverle in un regex solo e'
piu' difficile di quanto sembri: **la prima versione di questo banco non
vedeva la famiglia piu' grande**, perche' `[A-Za-z]{1,6}-?\d+` consuma `W7`
e poi inciampa sul `-1`. Cadevano **159 celle su 258, il 62%**. Diceva 145
dove `scripts/conta_celle_esame.py` diceva 258.

⇒ 🔑 **Ho scritto un righello nuovo per arbitrare fra due righelli, e il
nuovo era il peggiore dei tre.** L'ho visto SOLO perche' ho eseguito il
vecchio a fianco, nella stessa esecuzione. ⇒ **Un righello scritto per
arbitrare non e' neutrale: e' un TERZO righello, con i suoi difetti, e va
validato contro quelli che deve giudicare — non il contrario.**

E il secondo scarto, dopo aver corretto il primo: **il filtro sulle pipe.**
La tabella grande del registro ha >=9 colonne; dentro le celle vivono
tabelle piccole (3-7 pipe) le cui righe cominciano anch'esse con un numero.
Il vecchio le escludeva, il nuovo no: altre **47** di differenza. ⇒ **Su un
file dove le celle CONTENGONO tabelle, «riga che comincia con un id» non
basta: serve anche «della tabella giusta».**

RIFALLO CON: python docs/stato-reale/banchi/ws7-quattro-righelli-un-file.py
"""
import re
import subprocess
from pathlib import Path

REG = Path(__file__).resolve().parents[1] / "00-ESAME.md"
RADICE = Path(__file__).resolve().parents[3]
testo = REG.read_text(encoding="utf-8")
righe = testo.splitlines()

#: la tabella grande del registro ha 9+ pipe; le tabelle DENTRO le celle no.
COLONNE_TABELLA_GRANDE = 9

# --- i righelli, tutti sullo stesso `righe` --------------------------------
#: A. qualunque riga che cominci con `|` (il grep grezzo: vede anche legenda,
#:    intestazioni, separatori |---| e le tabelle annidate)
A = [r for r in righe if r.lstrip().startswith("|")]

#: B. riga con un ID in prima colonna, QUALUNQUE forma, dentro la tabella grande.
#: ⚠️ `[A-Za-z]{1,6}\d*` con `\d*` DENTRO la sigla: senza di quello `W7-1` non
#: matcha — la sigla consuma `W`, `-?` non trova il trattino perche' c'e' il
#: `7`, e `\d+` mangia il `7` lasciando `-1` fuori. Era il difetto della prima
#: versione di questo banco, e nascondeva 159 celle su 258.
ID_QUALSIASI = re.compile(r"^\|\s*([A-Za-z]{1,6}\d*-\d+[a-z]?|\d+)\s*\|")
B = [m.group(1) for r in righe
     if (m := ID_QUALSIASI.match(r)) and r.count("|") >= COLONNE_TABELLA_GRANDE]

#: B_senza_filtro: lo stesso, ma senza «della tabella giusta» — per misurare
#: quanto pesa quel solo criterio.
B_senza = [m.group(1) for r in righe if (m := ID_QUALSIASI.match(r))]

#: C/D. le famiglie di id, dentro B
SIGLATO = re.compile(r"^[A-Za-z]{1,6}\d*-\d+[a-z]?$")
C = [i for i in B if SIGLATO.match(i)]
D = [i for i in B if i.isdigit()]
#: e le siglate sono DUE famiglie che un regex tratta diversamente
C1 = [i for i in C if re.match(r"^[A-Za-z]+\d+-", i)]      # W7-1, W2-57
C2 = [i for i in C if not re.match(r"^[A-Za-z]+\d+-", i)]  # LANT-42

#: E. il righello VECCHIO, `scripts/conta_celle_esame.py`, verbatim
VECCHIO = re.compile(r"^\| [\w-]+ \|")
E = [VECCHIO.match(r).group(0).strip("| ") for r in righe
     if VECCHIO.match(r) and r.count("|") >= COLONNE_TABELLA_GRANDE]

print(f"  A  righe che cominciano con '|'  (grep grezzo)   = {len(A):4}")
print(f"  B  ID in prima colonna, tabella grande           = {len(B):4}   <- il mio righello, corretto")
print(f"  C     di cui SIGLATI                             = {len(C):4}")
print(f"  C1       forma Wn-n  (W7-1, W2-57)               = {len(C1):4}   <- la piu' grande, ed e' quella che cadeva")
print(f"  C2       forma SIGLA-n  (LANT-42)                = {len(C2):4}")
print(f"  D     di cui NUMERICI  (12, 45, ...)             = {len(D):4}")
print(f"     C + D = {len(C) + len(D)}   "
      f"{'== B, la scomposizione e completa' if len(C)+len(D)==len(B) else '!= B, MANCA UNA FORMA DI ID'}")
print(f"  E  `conta_celle_esame.py` verbatim               = {len(E):4}")

print(f"\n  ⇒ i due righelli concordano: "
      f"{'SI, ' + str(len(B)) + ' entrambi' if len(E) == len(B) else 'NO, ' + str(abs(len(E)-len(B))) + ' di scarto'}")

# --- quanto pesa CIASCUN criterio, tolto uno per volta ---------------------
#: la prova che un criterio serve e' che togliendolo il numero cambi.
print(f"\n  quanto pesa ogni criterio, TOLTO uno per volta:")
print(f"     senza «della tabella grande» (>= {COLONNE_TABELLA_GRANDE} pipe): "
      f"{len(B_senza):4}   (+{len(B_senza) - len(B)} tabelle annidate dentro le celle)")
vecchio_no_filtro = [r for r in righe if VECCHIO.match(r)]
print(f"     lo stesso sul vecchio:                          "
      f"{len(vecchio_no_filtro):4}   (+{len(vecchio_no_filtro) - len(E)})")

#: e il vecchio conta righe che NON hanno un id? (falsi positivi)
VERO_ID = re.compile(r"^([A-Za-z]{1,6}\d*-\d+[a-z]?|\d+)$")
non_id = [i for i in E if not VERO_ID.match(i)]
print(f"\n  falsi positivi del vecchio (prima colonna non e' un id): {len(non_id)}"
      + (f" -> {non_id}" if non_id else ""))

# --- il regime: lo stato ESATTO del file misurato -------------------------
sha = subprocess.run(["git", "log", "-1", "--format=%h %cd", "--date=format:%d/%m %H:%M"],
                     cwd=RADICE, capture_output=True, text=True).stdout.strip()
sporco = subprocess.run(["git", "status", "--porcelain", "--", "docs/stato-reale/00-ESAME.md"],
                        cwd=RADICE, capture_output=True, text=True).stdout.strip()
print(f"\n  REGIME  commit {sha} · registro {'MODIFICATO in locale' if sporco else 'pulito'} "
      f"· {len(righe)} righe · tutti i numeri da QUESTA esecuzione")
