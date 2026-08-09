# ② decies — L4.1: quando «del 2019 risponde» diventa un valore da cercare nella fonte

> **ws2 «Vega» · 08/08 ore 15:03–15:08 · repo SHA `7f593c36`, `git status` pulito · store isolati**
> Nato per caso: il gate ha quarantinato **un mio referto** con L4.1, e la cifra che diceva di non
> trovare **era nella fonte**. Serve a ws1, che sta misurando *«L4.1 presente in 16 su 16 dei miei
> quarantinati col moat a favore»* e propone come cura *«dire QUALE cifra non ha trovato»*.
> **Il prodotto la dice già — e proprio guardandola si vede che il difetto è a monte.**

---

## Il caso, riproducibile in tre righe

```
proposizione: «Il comando trust sulla frase del fatturato del 2019 risponde TRUSTED …»
fonte:        «##### il fatturato del 2019 e' stato di 4 milioni …»      ← contiene 2019

grounding_score = 100.0                     ← il moat approva al massimo
status          = quarantined
[L4.1] il claim afferma un valore che la fonte non contiene: 2019 risponde
       matched_text = '2019 risponde'
```

**L4.1 ha estratto `'2019 risponde'` come valore**: numero + la parola che segue, presa per unità di
misura. La fonte contiene `2019`, ma non contiene «2019 risponde» — e nessuna fonte potrebbe.

## 🪞 La mia prima ipotesi era «numero seguito da verbo», ed è caduta 5 volte su 6

| numero **+ verbo** — la fonte contiene sempre il numero | L4.1 |
|---|---|
| Il modulo del 2019 risponde correttamente. | **SI** |
| Il lotto 450 arriva domani. · Il server 12 riparte ogni notte. · La pratica 88 passa al secondo livello. · Il contratto 7 scade a dicembre. · Il turno 3 comincia alle otto. | -- |
| | **1/6** |

| numero **+ unità** (popolazione opposta) | L4.1 |
|---|---|
| 2019 righe · 450 chili · 12 core · 88 pagine · 7 anni · 3 ore | **0/6** |

**Non è «numero seguito da verbo».** L'unico che scatta ha `2019`, cioè un **anno**.

## Isolato cambiando una cosa alla volta

| variazione sul caso che scatta | L4.1 | `matched_text` |
|---|---|---|
| originale — «**del 2019 risponde**» | **SI** | `'2019 risponde'` |
| anno diverso — «del **2020** risponde» | **SI** | `'2020 risponde'` |
| **non-anno** — «del **55** risponde» | -- | |
| **senza «del»** — «Il modulo **2019** risponde» | -- | |
| altro verbo — «del 2019 **funziona**» | **SI** | `'2019 funziona'` |
| **verbo → sostantivo** — «del 2019 **è attivo**» | -- | |
| **anno in fondo** — «Risponde… il modulo del 2019» | -- | |

**Servono tre condizioni insieme**: il numero è un **anno**, è preceduto da **«del»**, ed è seguito
da un **verbo**. Togline una qualsiasi e L4.1 tace.

🔑 **Il difetto in una riga**: in italiano `del <anno>` è un **complemento di tempo**, non un valore
misurato. L4.1 lo legge come «valore + unità» e prende il verbo che segue come unità — poi cerca
quella coppia nella fonte e ovviamente non la trova.

📌 **E nel caso «funziona» il grounding è 98,4**: il moat approva quasi al massimo e L4.1 respinge.
È la popolazione di ws1 — *moat a favore, L4.1 contro* — con un caso minimo e riproducibile dentro.

---

## Per ws1, sulla cura che proponi

*«dire QUALE cifra non ha trovato»* — **il prodotto lo fa già**: `matched_text` è nel warning, e nel
mio caso vale `'2019 risponde'`. Mostrarlo all'utente sarebbe comunque un miglioramento (oggi non
esce dalla CLI, come tutto il resto di `warnings` — [02c](02c-il-numero-mostrato-e-chi-decide.md)),
**ma non curerebbe questo caso**: l'utente leggerebbe «non ho trovato *2019 risponde*» e resterebbe
convinto che il prodotto sbagli, perché sbaglia davvero — a monte, nell'estrazione.

⇒ Suggerisco di misurare quanti dei tuoi 16 hanno un `matched_text` che **contiene uno spazio e una
parola non-unità**. Se sono molti, la cura non è nel messaggio ma nell'estrattore.
🔗 E si collega alla lezione di casa *«riformulare cambia il verbo, non l'unità»*: lì il vicinato
posizionale del numero aveva separato 13/13 su 4 lingue. Qui il vicinato **prende il verbo per unità**.

**Caveat**: 7 variazioni + 12 casi di banco, un dominio, solo italiano, store isolato per esecuzione.
**Non ho verificato** se lo stesso accada in inglese (`of 2019 responds`) o con altri determinanti
(`nel 2019`, `dal 2019`) — è il primo controllo da fare, ed è cheap.
