# 33 — Il presidio anti-injection nasconde PHASE 0 della roadmap

**ws6 · 30/08 ore 21:50** · misure sul rilevatore vero, non sul codice letto.

Ogni risposta di `hippo_document_semantic_search` porta la riga:

> `"hidden_chunks": 1 — injection signals detected at index time. These results are PARTIAL.`

**Nessuno aveva guardato quale chunk.**

---

## Qual è

**`docs/ROADMAP-v0.7.md`, chunk 17: la sezione `PHASE 0 — days ("nothing silent, nothing
mislabeled"). START HERE.`** — cioè **il punto di partenza della roadmap**, con i tre punti 0.1
(ricevuta di aggiudicazione), 0.2 (judge-of-record) e 0.3 (i nomi onesti dei tier e la banda a due
soglie).

⇒ È l'**unico documento di prodotto** nell'indice — gli altri **40 su 42 sono nostri scratchpad**
([doc 30](30-la-porta-dei-documenti-e-costruita-meglio-e-l-indice-e-fatto-di-scratchpad.md)) — e la
parte nascosta è **quella che dice da dove cominciare**.

📌 E il testo silenziato contiene il motto della release: **«nothing silent, nothing mislabeled»**.

## Perché scatta — dopo DUE mie ipotesi sbagliate

**Ipotesi ①: «START HERE»**, un imperativo rivolto al lettore. **Falsificata**: togliendola,
`is_injection` resta `True`.

**Ipotesi ②: il tau greco** (`τ`), usato per le soglie. **Falsificata**: «la soglia τ vale 80» è
**pulita**, come σ, μ, α, β, π, Δ, gli accenti, l'euro e le emoji — **nessun carattere non-ASCII, da
solo, fa scattare niente**.

**La causa vera, isolata a variabile singola:**

```
   τ_hi   τhi   τ_x   σ_hi     ->  is_injection=True   severity=high   signals=['obfuscation']
   τ      τ_    t_hi (ascii)   ->  pulite
```

⇒ **Un carattere greco ATTACCATO a lettere latine dentro la stessa parola.** È la difesa classica
contro gli **homograph attack** — `pаypal` con la «а» cirillica — ed è **un criterio sensato**,
non un errore di progetto.

🔑 **Il falso positivo nasce dove la notazione tecnica assomiglia a un attacco**: `τ_hi` («tau high»)
è il nome standard di una soglia in statistica, ed è **greco+latino attaccati**, esattamente come un
homograph.

## Cosa costa

· **Severità `high`**, non un avviso minore.
· Nasconde **la sezione d'ingresso** dell'unico documento di prodotto indicizzato.
· Chi cerca *«da dove comincio?»* nella roadmap **non riceve la sezione che risponde**.
· ⚠️ **La porta lo dichiara** (`hidden_chunks: 1`, «These results are PARTIAL») — **il prodotto è
  onesto sul fatto di nascondere**; quello che non dice è **che cosa** e **perché**, e senza SQL
  diretto non è recuperabile.

## Cosa NON dico

· **Non dico che il criterio vada cambiato.** Contro gli homograph è la difesa giusta, e non ho
  misurato quanti attacchi veri prende: **rilassarlo per far passare `τ_hi` è una decisione di
  prodotto**, non una correzione ovvia. Un'alternativa possibile — non misurata — è **non applicare
  il mixed-script ai documenti di cui si conosce la provenienza**.
· **Non ho misurato quanti altri chunk sarebbero colpiti** in un corpus tecnico vero: qui è **1 su
  683**, ma il nostro corpus è fatto di prosa italiana, non di formule.
· **L'istante è parte del dato**: 30/08 ore 21:50.

## 🪞 La lezione del pezzo

**Due ipotesi mie, tutte e due sbagliate, e a smentirle è stato il prodotto — non io.** Ho chiesto
al rilevatore (`detect_injection` sul testo vero, poi riga per riga, poi carattere per carattere)
invece di dedurre dal codice. **Se avessi scritto «scatta su START HERE» dopo la prima lettura, era
plausibile, elegante e falso.**
