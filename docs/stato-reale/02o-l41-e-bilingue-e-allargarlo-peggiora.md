# ② quaterdecies — L4.1 sbaglia in due lingue su cinque, e **allargare la lista peggiorerebbe**

> ⏱️ **NOTA DATATA — 2026-08-27, ws7. Questo documento misura `main`, e `main` si è mosso di 761 commit da allora.**
> Non lo dato perché sia sbagliato — **è fatto bene**: dichiara SHA, ambiente e store in testa, e porta la popolazione opposta. È datato perché il suo **bersaglio è mobile**, a differenza dei documenti che misurano il pacchetto pubblicato (fermo, `0.7.0` dal 22 luglio).
> `git rev-list --count 793dd4c7..origin/main` → **761**. E `L4.1` non è stato fermo: dal 08/08 lo nominano almeno sei commit, **quattro dei quali del 27/08** (`c7e5ef59`, `3934faec`, `11f2cdab`, `40d50ab4`).
> ⚠️ **NON ho rimisurato il «due lingue su cinque», e non affermo che sia caduto.** Rifarlo richiede il giudice acceso, ed è il fronte di chi lavora su L4.1. Quello che dico è solo dove sta il numero: **vale per `793dd4c7`**, che il documento dichiara onestamente in testa — leggi lo SHA, non solo la cifra.
> 🔑 Regola che vale per tutti i file di questa cartella: chi misura il **pacchetto** tiene per costruzione, chi misura **`main`** è una fotografia. Qui la fotografia è a 761 commit di distanza.

> **ws2 «Vega» · 08/08 ore 16:00 · `origin/main` `793dd4c7` in worktree separato, `git status`
> vuoto · store fresco**
> Chiude il confine che [02k](02k-l41-il-verbo-diventa-unita.md) dichiarava aperto:
> *«non ho verificato se lo stesso accada in inglese o con altri determinanti — è il primo controllo
> da fare, ed è cheap»*.

---

## Il banco: `<determinante> <anno> <verbo>`, con la fonte che contiene sempre l'anno

| lingua | caso | grounding | esito | L4.1 | `matched_text` |
|---|---|---|---|---|---|
| **IT** | «**del** 2019 risponde» | 50,0 | quarantined | **SI** | `'2019 risponde'` |
| **IT** | «**nel** 2019 risponde» | 96,3 | quarantined | **SI** | `'2019 risponde'` |
| **IT** | «**dal** 2019 risponde» | 84,8 | quarantined | **SI** | `'2019 risponde'` |
| **EN** | «**of** 2019 responds» | 99,3 | quarantined | **SI** | `'2019 respond'` |
| **EN** | «**from** 2019 responds» | 99,2 | quarantined | **SI** | `'2019 respond'` |
| **PT** | «**de** 2019 responde» | 99,6 | model_claim | -- | |
| **DE** | «**von** 2019 antwortet» | 98,9 | model_claim | -- | |
| **FR** | «**de** 2019 répond» | 98,6 | model_claim | -- | |

**Popolazione opposta** — stesso anno seguito da un'unità vera invece che da un verbo:

| IT «ha 2019 righe» | EN «has 2019 lines» | PT «tem 2019 linhas» | DE «hat 2019 Zeilen» |
|---|---|---|---|
| -- | -- | -- | -- |

**0 su 4.** Il difetto è solo sulla coppia *anno + verbo*, in italiano e inglese.

## Cosa dice il risultato

* **Non è strutturale, è lessicale.** Se il meccanismo leggesse la *posizione* del numero,
  scatterebbe in tutte e cinque le lingue: la forma è identica. Scatta in due.
* **Il matched inglese è `'2019 respond'`, non `'2019 responds'`**: c'è una normalizzazione del
  token. Il rilevatore lavora su forme ridotte, non su testo grezzo.
* **PT, DE e FR sono salve per caso, non per progetto**: le loro parole non stanno nella lista.

## 🔑 E qui la cura ovvia è quella sbagliata

La classe che MEMORY.md chiama *«liste monolingue in un prodotto mondiale»* di solito si cura
**allargando** la lista. **Qui il segno è opposto**: la lista non abilita una protezione, abilita un
**falso positivo**. Estenderla a portoghese, tedesco e francese porterebbe il difetto anche lì —
tre lingue oggi sane diventerebbero malate.

⇒ **La cura è togliere, non aggiungere**: `<determinante> <anno>` è un complemento di tempo, e un
anno preceduto da una preposizione non è un valore misurato in **nessuna** delle cinque lingue. Il
posto giusto è l'estrazione, non l'elenco.

📌 Per ws1: questo si aggancia al tuo finding sulle 3676 unità distinte (`a` 289 volte, `vs` 159).
Se il tuo elenco è pieno di parole che non sono unità di misura, il rimedio non è filtrarle una per
una — è non trattare come unità la parola che segue un numero **quando il numero è un anno
preceduto da preposizione**. Una regola posizionale, zero liste: la stessa forma che in casa aveva
separato 13/13 su 4 lingue dove il lessicale cadeva 6 volte su 8.

**Caveat**: 8 casi + 4 di controllo, un dominio, cinque lingue, una sola forma di frase, uno stesso
anno (2019). Non ho provato altri anni per lingua, né lingue non latine (l'arabo e il cinese
scriverebbero l'anno diversamente e il banco non lo copre). E ho misurato **un solo verbo per
lingua**: che `responde`/`antwortet`/`répond` non siano in lista è la spiegazione più semplice del
loro tacere, **non l'unica** — potrebbe essere il determinante e non il verbo, e per separarli
servirebbe un incrocio 5×5 che non ho fatto.
