# ⑭ La **forma** della fonte decide quale layer sbaglia — e su un output di strumento uno dei due è rumore puro

**Misurato il 28/08/2026 fra le 22:35 e le 23:18** · codice `Code/HippoAgent`
(stampato da ogni banco) · tutte le misure **fuori da pytest** · SHA dichiarato
per cella nel registro (`ff4dfdbe` / `15a6ce4a`).

Il dossier ⑬ ha un asse solo: **quanto** testo circonda la prova. Questo ne
apre un secondo, indipendente: **com'è fatto** quel testo.

---

## In una riga

Su una **tabella allineata** — cioè su ogni output di strumento, cioè sulla
source che `O3` impone — **`L4.1` è perfetto e `L4.2` è rumore puro**: zero
falsi allarmi su otto contro **otto su otto**, e i falsi che `L4.2` prende li
prende già `L4.1`.

---

## 1. Il numero, e l'errore di lettura che lo nascondeva

8 coppie su source **reali** (gli output dei banchi di quella sera, non testi
costruiti). Ogni coppia: un claim **vero** e lo stesso con **un numero
inventato**.

```
  LETTURA AGGREGATA («almeno un layer L4 parla»)
     VERI  segnalati : 8 su 8
     FALSI segnalati : 8 su 8          →  «il gate non separa»

  SEPARATI PER LAYER
     L4.1   sui VERI 0 su 8      sui FALSI 8 su 8      separazione PERFETTA
     L4.2   sui VERI 8 su 8      sui FALSI 2 su 8      anti-separa
```

🔑 **L'aggregato è falso e nasconde proprio l'informazione che serve.** È
l'errore che chiunque farebbe leggendo la ricevuta — `layers=['L4.1','L4.2']`
si legge come un blocco solo.

## 2. ✅ Ciò che il gate fa, e va detto per primo

**`L4.1` non produce un solo falso allarme su otto**, e ferma **8 su 8** dei
numeri inventati.

⇒ E questo **corregge l'impressione lasciata dalla cella W7-25**: lì `L4.1`
perde il valore adiacente a una parola di `_RIFERIMENTO_RE` — misurato, vero —
**ma su questa popolazione quel difetto non gli è mai costato un fatto vero**.
Un difetto reale può avere costo zero sulla popolazione che conta, e dirlo è
parte del referto.

## 3. 🔴 `L4.2` su un output di strumento

**8 falsi allarmi su 8**, e i **2** falsi che prende **li prende già `L4.1`**.
⇒ **Valore aggiunto zero, costo otto fatti veri su otto.**

La causa è isolata a variabile singola (cella W7-30): **legge la grandezza a
DESTRA del numero**.

```
  A  tabella allineata (etichetta a SINISTRA)   SEGNALA   → «nella fonte «in»»
  B  la stessa, etichetta a DESTRA del numero   tace
  C  prosa                                      tace
  D  tabella SENZA la parola «in»               SEGNALA   → «nella fonte «file»»
```

Il caso **D** è la prova: tolta `in`, prende `file`. **Prende sempre la parola
successiva, qualunque sia.** In una tabella allineata a destra non c'è mai
l'etichetta.

## 4. Il gemello su `L4.1`, per completezza

Cella W7-25. Non è la parola «nota» come sembrava: è **la classe
`_RIFERIMENTO_RE`** (`quantity_match.py:1071`).

```
  dentro la lista  →  8 su 8 accecano   (nota note pagina art comma tabella riga figura)
  fuori dalla lista →  0 su 5           (alfa beta soglia misura gamma)
```

⇒ Riguarda **ogni documento a sezioni numerate**, contratti e leggi compresi.
Ma **perde solo il valore adiacente** (uno su quattro nella misura), e nel
verso opposto a «cieca»: alla porta **il layer PARLA dove dovrebbe tacere**.
⚖️ **Il varco non si apre**: col claim falso continua a fermarlo ⇒ **danno
unilaterale, non buco di sicurezza**.

---

## 5. ⚠️ Due controlli hanno cambiato il referto, e sono la parte riusabile

**①** Il **controllo positivo** ha scoperto che la prima versione del banco
chiamava `run_validation_gate` **senza `ground_write=True`**: il gate taceva su
**tutte e sedici** le coppie, veri e falsi. `_grounding_write_on()` legge
`ENGRAM_GROUNDING_WRITE`, e senza quella variabile **il blocco L4
(`anti_confab_gate.py:2337`) non gira affatto**.
⇒ **Senza quel controllo il referto sarebbe stato «zero falsi allarmi, il gate
regge»** — un verde che era un'assenza di misura.

**②** Il **conteggio per layer** ha ribaltato l'aggregato.

📌 **Per chi scrive banchi sul gate**: chiamando `run_validation_gate` a basso
livello, **passate `ground_write=True`** o state misurando un layer spento.

## 6. Come è arrivato il caso: usando il prodotto

Non l'ho costruito. Alle **23:03** un `verimem save` di un fatto **vero** con la
sua source ha prodotto:

```
  flow.write  grounding_score=99.98  judged=True  layers=['L4.1','L4.2']
              status=quarantined  withheld_despite_judge=True
```

⚖️ E su `L4.1` **il gate aveva ragione, l'errore era mio**: avevo scritto «Alle
23 del 28 agosto» e la source — l'output dello strumento — l'ora non ce l'ha.
**La cura è mettere l'istante NELLA SOURCE, non toglierlo dal claim**: rifatti
così, i due fatti sono passati (7 su 7 ammessi).

## 7. Limiti, dichiarati

- **8 coppie, tutte mie, tutte tabelle.** È **una forma di source**, non il
  corpus. Chi vuole il numero sul corpus deve prendere una popolazione che non
  sia la mia.
- Il campione di W7-25 usa **il claim di @ws6**, preso dal suo esempio: se nei
  casi discorsivi ne ha usato un altro, quei due punti vanno rifatti sul suo.
- **Non ho misurato** cosa succede con `L4.2` disattivato: che il costo sia
  «otto veri» lo dice questa popolazione, non un A/B sul prodotto.

## 8. I banchi

`chi-acceca-L4-1-la-parola-o-la-forma-della-frase.py` ·
`non-e-la-parola-nota-e-la-classe-dei-riferimenti.py` ·
`L4-1-e-troppo-zelante-non-cieca-i-due-livelli.py` ·
`L4-2-su-una-tabella-legge-la-grandezza-sbagliata.py` ·
`quanto-sbaglia-il-gate-su-una-tabella-vera.py`

Celle nel registro: **W7-25 · W7-30 · W7-31**.
