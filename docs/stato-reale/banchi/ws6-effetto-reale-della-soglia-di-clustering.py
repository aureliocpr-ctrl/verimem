r"""Cosa PRODUCE una soglia di clustering tarata sotto il pavimento?

La riga 54 del registro dice che cinque soglie di coseno su sei stanno sotto il pavimento
della loro popolazione. Ma «non scarta» non e' ancora «rompe qualcosa»: l'avevo dichiarato
come limite e questo banco chiude quel limite per la soglia del sonno NREM.

DUE VERIFICHE PRIMA DI MISURARE, e la prima mi ha quasi fatto attribuire l'effetto al
posto sbagliato:
  - i 98 cluster `*/auto-MASTER` del corpus **non misurano questa soglia**:
    `auto_consolidate` (consolidation.py) raggruppa per **topic-prefix depth 2**, non per
    coseno. `sleep_nrem_cluster_threshold` e' usata **solo** in `sleep.py:418`.
  - `eps_threshold` **si chiama come una distanza e si comporta come una similarita'**:
    `memory.py:2075` fa `mask = unvisited & (row >= eps_threshold)` e il docstring dice
    «episodes with cos-sim >= threshold». ⇒ il confronto col pavimento nella riga 54 aveva
    il **segno giusto**, ma andava verificato perche' il nome diceva il contrario.

RISULTATO (28/08 22:27) — 435 episodi veri, su una COPIA del db:

    soglia   cluster   il piu' grande   singoletti
      0.40       1          431              0     <- SOGLIA DI PRODUZIONE (sleep NREM)
      0.55       1          431              0     <- default della funzione
      0.62       1          431              0     <- schema_cluster
      0.75       1          431              0
      0.85      50           56             14     <- qui comincia a separare
      0.90     235           32            158     <- counterfactual_dedup (l'unica viva)
      0.95     385           18            364

=> ALLA SOGLIA DI PRODUZIONE **tutti i 431 episodi finiscono in UN SOLO CLUSTER**, e resta
   cosi' fino a 0.75 compreso. Non e' «non scarta»: **non separa niente**. Il consolidamento
   NREM tratta l'intero corpus di episodi come un unico gruppo.
=> CONTROLLO SUPERATO: a 0.85/0.90/0.95 i cluster si moltiplicano (50 -> 235 -> 385) ⇒ il
   banco misura **la soglia**, non il metodo. Se fosse uscito «1 cluster» anche a 0.95, il
   difetto sarebbe stato nel clustering e non nella taratura, e il banco lo direbbe.
=> CONFERMA INDIPENDENTE DEL PAVIMENTO: la separazione comincia a **0.85**, e per questa
   stessa popolazione avevo misurato pavimento **min 0.744 / mediana 0.898** (riga 54, banco
   `5ec3aecf`). I due numeri si sostengono: sotto il pavimento nessuna separazione, attorno
   alla mediana la separazione parte.
=> E `counterfactual_dedup` **0.90** — l'unica soglia che la riga 54 trovava VIVA — e' anche
   l'unica che cade in una zona dove il clustering separa davvero (**235 cluster**). Doppia
   conferma, da due strade diverse.

REGIME: **copia** del db degli episodi in tempdir (`shutil.copy2`), cosi' l'originale non
viene mai aperto in scrittura nemmeno per costruire l'indice di recall. FUORI da pytest.
⚠️ `EpisodicMemory` vuole un **`Path`**, non una `str`.
⚠️ LIMITE: misura la soglia del sonno NREM sulla popolazione EPISODI. Non dice cosa
produca `schema_cluster` sui trigger di skill, che e' un'altra popolazione e un altro
percorso.

RIPRODUCI:  python docs/stato-reale/banchi/ws6-effetto-reale-della-soglia-di-clustering.py
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path


def main() -> None:
    src = Path.home() / ".engram/episodes/episodes.db"
    tmp = Path(tempfile.mkdtemp()) / "episodes.db"
    shutil.copy2(src, tmp)
    print(f"copia di lavoro: {tmp.name} ({tmp.stat().st_size/1e6:.1f} MB) — "
          "l'originale non viene mai aperto in scrittura")

    from verimem.memory import EpisodicMemory
    em = EpisodicMemory(tmp)
    print(f"episodi: {len(em.all())}")
    print(f"\n{'soglia':>8} {'cluster':>9} {'piu grande':>11} {'singoletti':>11}   nota")
    note = {0.40: "<- SOGLIA DI PRODUZIONE (sleep NREM)", 0.55: "<- default della funzione",
            0.62: "<- schema_cluster", 0.90: "<- counterfactual_dedup"}
    for s in (0.40, 0.55, 0.62, 0.75, 0.85, 0.90, 0.95):
        cl = em.cluster_similar(eps_threshold=s)
        dim = sorted((len(c) for c in cl), reverse=True)
        soli = sum(1 for d in dim if d == 1)
        print(f"{s:>8.2f} {len(cl):>9} {dim[0] if dim else 0:>11} {soli:>11}   {note.get(s,'')}")


if __name__ == "__main__":
    main()
