r"""Il pavimento del coseno vale anche per EPISODI e SKILL, o e' solo dei fatti?

Chiude l'ultima parte del censimento aperto con la riga 51 del registro. La' avevo
misurato che `contradiction.py` filtra a 0.75 mentre il pavimento fra fatti scorrelati
e' 0.767 (30 coppie su 30 sopra soglia) - una guardia che non ha mai occasione di dire
di no. Ma avevo DICHIARATO di non poter estendere il risultato: le altre soglie del
prodotto operano su popolazioni diverse, e popolazioni diverse hanno pavimenti diversi.

  sleep_nrem_cluster_threshold  0.40   (config.py:204, «cosine threshold»)
  trace_alignment_obs_threshold 0.55   (config.py:440)
  schema_cluster_threshold      0.62   (config.py:459, «cosine on trigger embeddings»)
  counterfactual_dedup_threshold 0.90  (config.py:452, «cosine over name+trigger»)

Le prime due vivono sul mondo degli EPISODI, le altre due sui TRIGGER DI SKILL.

RISULTATO (28/08 19:37) — TRE SOGLIE SU QUATTRO SONO SPENTE, E LA QUARTA E' L'UNICA
SOPRA 0.90:

  EPISODI (task_text, 435 episodi)   min **0.744** · p25 0.804 · mediana 0.898 · max 0.985
      sleep_nrem_cluster    0.40  ->  30/30 sopra  ->  SPENTA
      trace_alignment_obs   0.55  ->  30/30 sopra  ->  SPENTA
      controlli: quasi identici 1.000 · due diversi 0.764
  SKILL (trigger, 324 skill)         min **0.797** · p25 0.852 · mediana 0.874 · max 0.964
      schema_cluster        0.62  ->  30/30 sopra  ->  SPENTA
      counterfactual_dedup  0.90  ->   9/30 sopra  ->  **VIVA**, scarta 21 coppie su 30
      controlli: quasi identici 0.994 · due diversi 0.839

=> IL QUADRO COMPLETO delle sei soglie di coseno del prodotto, ognuna contro il pavimento
   della PROPRIA popolazione (le prime due dalla riga 51 del registro):

      soglia                  popolazione   pavimento   verdetto
      contradiction    0.75   fatti           0.767     SPENTA  (e RITIRA: danno)
      coherence_check  0.75   fatti           0.767     SPENTA  (avvisa: rumore)
      sleep_nrem       0.40   episodi         0.744     SPENTA
      trace_alignment  0.55   episodi         0.744     SPENTA
      schema_cluster   0.62   skill           0.797     SPENTA
      counterfactual   0.90   skill           0.797     VIVA

   **Cinque su sei sotto il pavimento. L'unica viva e' l'unica a 0.90.**

🔑 LA REGOLARITA' CHE SERVE A CHI PROGETTA: su tutte e tre le popolazioni il pavimento
   sta fra **0.744 e 0.797**. ⇒ **Su questo embedder, una soglia di coseno sotto ~0.80 e'
   spenta per costruzione**, qualunque cosa separi in teoria. Chi ne sceglie una nuova
   parta da li' e misuri il pavimento della sua popolazione PRIMA di fissare il valore.

⚠️ LIMITE CHE PUO' FAR CADERE UN «SPENTA», e lo dichiaro: le coppie sono prese da entita'
   diverse (`task_id`/`name` diversi), il che NON garantisce che siano semanticamente
   lontane — due episodi distinti possono parlare della stessa cosa. Questo **alza** il
   pavimento misurato, quindi il rischio e' di dire «spenta» a torto. Mitigazione: la
   statistica riportata e' il **MINIMO**, che basta una sola coppia davvero lontana per
   abbassare; su 30 coppie nessuna scende sotto 0.744. Con piu' coppie il numero si
   stringe, e chi lo rifa' con 300 e' benvenuto.
⚠️ E i controlli separano ma con margine STRETTO su episodi (quasi identici 1.000 contro
   due diversi 0.764): la distanza fra «uguale» e «diverso» su questa popolazione e' di
   circa due decimi, non di uno zero e un uno.

METODO, identico a quello della riga 51 perche' i numeri siano confrontabili: si prendono
coppie da entita' DIVERSE (episodi con `task_id` diverso, skill con `name` diverso), si
calcola il coseno con `embedding.encode` - la stessa funzione che il prodotto usa - e si
guarda il MINIMO. Se il minimo sta sopra una soglia, quella soglia non scarta nulla.

CONTROLLO POSITIVO obbligatorio: due testi quasi identici devono dare coseno alto, due
palesemente scorrelati basso. Sulla riga 51 questo controllo e' FALLITO ed era il
risultato; qui va rifatto perche' la popolazione e' un'altra e non si eredita niente.

REGIME: store di Aurelio in sola lettura (`mode=ro`), percorsi chiesti alla cartella dati
e non indovinati (⚠️ il percorso ovvio e' vuoto su TUTTI E TRE gli store: `episodes.db`
0,0 MB contro `episodes/episodes.db` 17,6 MB), FUORI da pytest dove l'embedder e' uno
stub su SHA-256 dei token.

RIPRODUCI:  python docs/stato-reale/banchi/ws6-il-pavimento-su-episodi-e-skill.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np

from verimem import embedding

D = Path.home() / ".engram"
POPOLAZIONI = [
    ("EPISODI · task_text", D / "episodes/episodes.db",
     "SELECT task_id, task_text FROM episodes WHERE task_text IS NOT NULL "
     "AND length(task_text) BETWEEN 30 AND 300 GROUP BY task_id LIMIT 60",
     [("sleep_nrem_cluster", 0.40), ("trace_alignment_obs", 0.55)]),
    ("SKILL · trigger", D / "skills/skills_index.db",
     "SELECT name, trigger FROM skills WHERE trigger IS NOT NULL "
     "AND length(trigger) BETWEEN 20 AND 300 GROUP BY name LIMIT 60",
     [("schema_cluster", 0.62), ("counterfactual_dedup", 0.90)]),
]


def cos(x: str, y: str) -> float:
    a, b = embedding.encode(x), embedding.encode(y)
    d = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / d) if d > 0 else 0.0


def main() -> None:
    for etichetta, db, query, soglie in POPOLAZIONI:
        print(f"\n{'='*70}\n=== {etichetta}   ({db.name}, {db.stat().st_size/1e6:.1f} MB)")
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        righe = con.execute(query).fetchall()
        con.close()
        if len(righe) < 4:
            print(f"   solo {len(righe)} righe utilizzabili: NON MISURABILE, e lo dichiaro")
            continue

        # controllo positivo, con materiale DI QUESTA popolazione
        base = righe[0][1]
        quasi = base[:-1] + ("." if not base.endswith(".") else "!")
        lontano = righe[len(righe) // 2][1]
        print(f"   controllo  quasi identici .. {cos(base, quasi):.3f}")
        print(f"   controllo  due diversi ..... {cos(base, lontano):.3f}")

        vals = []
        for i in range(0, len(righe) - 1, 2):
            (ka, ta), (kb, tb) = righe[i], righe[i + 1]
            if ka != kb:
                vals.append(cos(ta, tb))
        vals.sort()
        n = len(vals)
        print(f"   coppie fra entita' diverse: {n}")
        print(f"   min {vals[0]:.3f} · p25 {vals[n//4]:.3f} · mediana {vals[n//2]:.3f} "
              f"· p75 {vals[3*n//4]:.3f} · max {vals[-1]:.3f}")
        for nome, s in soglie:
            sopra = sum(1 for v in vals if v >= s)
            verdetto = ("SPENTA: il minimo e' sopra la soglia" if vals[0] >= s
                        else f"viva: scarta {n-sopra} coppie su {n}")
            print(f"   soglia {nome:<22} {s:.2f} -> {sopra}/{n} sopra   {verdetto}")


if __name__ == "__main__":
    main()
