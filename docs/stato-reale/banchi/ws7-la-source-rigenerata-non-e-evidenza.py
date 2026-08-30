# -*- coding: utf-8 -*-
"""LA SOURCE RIGENERATA NON E' EVIDENZA: e' una NUOVA misura.

PERCHE' ESISTE. Il 30/08 alle 12:41 ho salvato tre fatti veri con `verimem save
--source "$(python banco.py)"`. **Tre su tre quarantinati**, e la ricevuta diceva
`grounding_score=99.9 · layers=['L4.1'] · withheld_despite_judge=True`.

Ho creduto per due minuti di avere un reperto sul PRODOTTO — «il giudice
semantico dice 99,9 e i layer lessicali lo scavalcano». **Era un mio errore, e
il gate aveva ragione tre volte su tre.**

    quando ho MISURATO:              Wn-n = 160 · totale 258
    quando ho passato la source:     Wn-n = 162 · totale 261

Il registro cresce di circa una cella al minuto con otto istanze che scrivono.
`$(comando)` dentro la riga di `save` **riesegue il comando**: il gate ha
confrontato il mio numero di due minuti prima con un output di adesso.

⇒ 🔑 **Le forme di source sbagliata sono TRE, non due.** CLAUDE.md ne nomina
una — la parafrasi. Questa e' la terza, e su un bersaglio mobile e' peggio:

    (a) PARAFRASATA  -> il gate misura la mia coerenza interna, non i fatti
    (b) GREZZA       -> il gate misura i fatti                    <- l'unica giusta
    (c) RIGENERATA   -> il gate misura la DERIVA DEL BERSAGLIO, e quarantina
                        un fatto che era VERO nell'istante in cui l'hai misurato

⇒ E la cura e' una riga: **cattura l'output in un file, poi leggi il numero DA
QUEL FILE.** Il fatto e la sua prova devono venire dalla stessa esecuzione.

E IL PEZZO CHE VALE PER IL GRUPPO. Qui `withheld_despite_judge=True` e' il gate
che funziona **BENE**: il giudice semantico dava 99,9 perche' il testo e' quasi
identico alla source, e **solo il layer lessicale poteva vedere che la cifra era
160 contro 162.** ⇒ **Contro-esempio alla sintesi LANT-55** («il gate e' severo
sulla dimensione sbagliata»): non la falsifica, ma le mette un limite —
**`withheld_despite_judge` da solo non basta a dire «difetto»**, e chi conta quei
casi come «fatti veri persi» ci conta dentro anche errori come il mio.

    python docs/stato-reale/banchi/ws7-la-source-rigenerata-non-e-evidenza.py

Store TEMPORANEO (`HIPPO_DATA_DIR`), fuori da pytest. Non tocca lo store di
Aurelio. Il banco NON riesegue il righello: usa due source scritte a mano che
differiscono per una cifra, cosi' l'esito non dipende da quanto e' cresciuto il
registro mentre gira.
"""
from __future__ import annotations

import os
import tempfile

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws7_src_")

from verimem.valore_non_nella_fonte import valori_non_nella_fonte  # noqa: E402

#: la source come sarebbe stata CATTURATA all'istante della misura
CONGELATA = """  A  righe che cominciano con '|'  (grep grezzo)   =  849
  B  ID in prima colonna, tabella grande           =  258
  C1       forma Wn-n  (W7-1, W2-57)               =  160
"""
#: la stessa, RIGENERATA due minuti dopo: tre celle in piu'
RIGENERATA = CONGELATA.replace("849", "857").replace("258", "261").replace("160", "162")

#: ⚠️ NIENTE `00-ESAME.md` nel claim: `L4.1` ne estrarrebbe il numero `00` e lo
#: dichiarerebbe assente in ENTRAMBI i rami, sporcando l'A/B con un valore che
#: non c'entra. E' `LANT-42`: la prima volta erano le date, qui e' un nome di
#: file. ⇒ Il difetto NON e' di L4.1 — e' che un claim con un numero decorativo
#: rende illeggibile il confronto. Misurato: col nome del file, la CONGELATA
#: fermava `['00']` e la RIGENERATA `['00','160']`, e la riga di sintesi che
#: avevo scritto («il verdetto si ribalta») era piu' larga della misura.
CLAIM = "Nel registro degli esami gli id di forma Wn-n sono 160."

print(f"  claim: «{CLAIM}»\n")
for nome, src in (("CONGELATA  (l'output catturato all'istante della misura)", CONGELATA),
                  ("RIGENERATA (lo stesso comando, due minuti dopo)", RIGENERATA)):
    assenti = valori_non_nella_fonte(CLAIM, src)
    esito = "AMMESSO da L4.1" if not assenti else f"FERMATO da L4.1 -> {[a.testo for a in assenti]}"
    print(f"  {nome}\n     {esito}")

print("\n  ⇒ una sola cosa cambia — se la source e' stata rigenerata — e il verdetto si ribalta.")
print("     Il claim e' lo STESSO, ed era VERO nell'istante in cui l'ho misurato.")
print("\n  E il rovescio, per non misurare una popolazione sola: un claim FALSO")
print("     viene fermato anche con la source congelata?")
FALSO = "Nel registro degli esami gli id di forma Wn-n sono 900."
a = valori_non_nella_fonte(FALSO, CONGELATA)
print(f"     «...sono 900» con la CONGELATA: "
      f"{'FERMATO -> ' + str([x.testo for x in a]) if a else 'AMMESSO (L4.1 non lo vede)'}")
print(f"  ⇒ il layer non e' rotto: separa il vero dal falso quando la source e' quella giusta.")
