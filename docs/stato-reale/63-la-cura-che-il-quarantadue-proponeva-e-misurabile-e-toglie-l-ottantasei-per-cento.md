# 63 — La cura che il 42 proponeva è misurabile, e toglierebbe l'86% dei conflitti

*ws6/Aldo — 31 agosto 2026, alba. Chiude il limite finale del [42](42-il-presidio-consiglia-una-cura-che-ritirerebbe-mille-fatti.md), e valida la cura che lì avevo solo proposto.*

Il `42` finiva con due cose non fatte:

> **La cura sensata è a monte**: portare nel rilevatore di contraddizioni il
> criterio di `L4.2`. **Non l'ho fatto** — è codice del gate, e il gate non si
> tocca senza mandato.
> **Quello che non ho misurato**: quante delle coppie `numeric_clash` con
> jaccard ≥ 0,50 siano contraddizioni **vere**. Sono ~137 nel campione.

**Il criterio esiste già come funzione pubblica**, e non serve toccare il gate
per usarlo: `numeric_conflict(a, b)` in `quantity_match.py` ritorna
`(unità, valore_a, valore_b)` **solo se** i due testi danno un valore diverso
per la **stessa unità** sullo **stesso soggetto** — con le guardie che il suo
docstring elenca (parola distintiva condivisa, nessun qualificatore contrastante,
nessun identificatore diverso). **L'ho chiamata in lettura.**

## ① Il criterio discrimina di trenta volte

Coppie `numeric_*` **irrisolte** lette dallo store: **19.981** (di 93.851 righe
totali in `contradictions`). Divise per somiglianza lessicale, 400 per gruppo:

| popolazione | n | il criterio conferma | quota |
|---|---|---|---|
| coppie ad **ALTO** jaccard (≥ 0,50) | 400 | **336** | **84,0%** |
| coppie a **BASSO** jaccard (< 0,50) | 400 | **11** | **2,8%** |

**Trenta volte di differenza.** ⇒ **il righello che lega numero e grandezza
separa le due popolazioni**, ed è la prova che mancava al `42`: là avevo mostrato
che il rilevatore dichiara in conflitto quasi tutto, **senza poter dire quali
avesse ragione**.

## ② Il limite è chiuso: le coppie ad alto jaccard sono vere nell'84%

**La domanda del `42` era «quante delle ~137 sono vere»**, e la risposta è
**l'84%** — misurata su 400 invece che 137. ⇒ **il rilevatore NON sbaglia
dappertutto: ha ragione proprio dove i due testi si somigliano**, e sbaglia dove
non si somigliano (97,2% di falsi).

## ③ Che cosa costerebbe la cura

Sulle 19.981 coppie irrisolte lette, la composizione è:

```
con jaccard >= 0.50 :  2.660   (13,3%)
con jaccard <  0.50 : 17.321   (86,7%)
```

Applicando le due quote misurate:

| | conflitti oggi | resterebbero col criterio |
|---|---|---|
| alto jaccard | 2.660 | ~2.234 (84,0%) |
| basso jaccard | 17.321 | ~485 (2,8%) |
| **totale** | **19.981** | **~2.719** |

⇒ **il rilevatore passerebbe da ~20.000 conflitti a ~2.700: meno 86%** — e
quelli che restano sono, per l'84%, coppie che il criterio conferma.

📌 **E questo è il numero che il `42` cercava per decidere**: là il problema era
che «normalizzare gli status renderebbe ritirabili fino a 998 fatti» sulla base
di scontri quasi tutti falsi. **Con il criterio a monte, la base di quei ritiri
si riduce di sei settimi.**

## ④ Che cosa NON dico

- ⛔ **«Confermata dal criterio» non vuol dire «vera».** `numeric_conflict` è il
  righello del prodotto, non la verità: dice che due testi danno valori diversi
  per la stessa unità sullo stesso soggetto. **Per sapere quante siano davvero
  contraddizioni bisogna leggerle**, e non l'ho fatto.
- ⛔ **Due campioni da 400**, non le popolazioni intere: le quote hanno un
  intervallo che non ho calcolato. Il divario 84 ↔ 2,8 lo regge; **la stima
  «~2.719» no** — è un'estrapolazione da due proporzioni campionarie, e va letta
  come ordine di grandezza.
- ⛔ **Non ho toccato il gate**, e la cura resta **proposta**: chiamare una
  funzione in lettura per misurare non è portarla nel rilevatore. Quello è
  codice del prodotto e richiede mandato, RED→GREEN e critic.
- ⛔ **`jaccard ≥ 0,50` è la soglia del `42`**, ereditata: non l'ho ritarata, e
  non so se sia il taglio migliore.

---
*Banco: `banchi/ws6-quante-sono-contraddizioni-vere.py` — misura entrambe le
popolazioni e stampa la composizione della tabella prima di contare. Store di
Aurelio in sola lettura.*
