# ② bis — Il numero che l'utente vede, e chi decide davvero

> ⏱️ **NOTA DATATA — 2026-08-27, ws7. Questo documento misura `main`, e `main` si è mosso di 741 commit da allora.**
> Non è datato perché sbagli: è datato perché il suo **bersaglio è mobile**. Lo SHA che dichiara in testa è `31578d56`, e `git rev-list --count 31578d56..origin/main` dà **741**.
> ⚠️ **Non ho rimisurato il suo contenuto e non affermo che sia caduto.** Quello che dico è dove sta: leggi lo SHA accanto al numero, non il numero da solo.
> 🔑 Regola per questa cartella, dal 26/08 linkata dal README: chi misura il **pacchetto pubblicato** tiene per costruzione (`0.7.0` fermo dal 22 luglio), chi misura **`main`** è una fotografia.

> **ws2 «Vega» · 08/08 ore 14:00–14:11 · SHA `31578d56`**
> ⚠️ Il ramo condiviso aveva modifiche di ws3 non committate **sugli stessi file che misuro**
> (`anti_confab_gate.py`, `client.py`). Ho quindi rieseguito il caso decisivo su un **worktree
> pulito** allo SHA dichiarato, `git status` vuoto: i punteggi si riproducono **cifra per cifra**
> (96.81583404541016 · 93.60125732421875 · 1.0495223999023438). Il referto vale per lo SHA.

---

## Perché questo blocco esiste

Tre istanze diverse hanno incontrato oggi la stessa forma su tre porte diverse, senza sapersi:

| chi | dove | cosa ha visto |
|---|---|---|
| ws2 (ieri) | `trust_report` | `confidence` mostrato, il moat decide su `grounding_score` |
| ws4 (oggi) | corpus | 28 fatti a 99,98 **in quarantena**, 10 ammessi sotto 40 |
| ws5 (oggi) | `recall` | Trento **0.8495** sotto un pavimento **0.8617** — e risponde lo stesso |

Invece di trattarli come tre difetti, ho fatto il **censimento**, con un test che non richiede di
conoscere il criterio interno: l'**inversione**. Se esistono due casi con `numero_A > numero_B` ma
`esito_A` peggiore di `esito_B`, quel numero non è il criterio. È falsificabile dalla sola porta.

---

## 1. La mia ipotesi di partenza è CADUTA — e il perché vale più dell'ipotesi

**Predicevo inversioni ovunque. Sulla scrittura non ce n'è nessuna:**

```
12 fatti con fonte, store isolato
  ammessi      : grounding  95,7 – 99,6   (7 casi)
  quarantinati : grounding   0,6 –  1,2   (5 casi)
  INVERSIONI: 0/12 · casi senza numero: 0/12
```

Separazione netta, nessun caso ambiguo. **Su fatti neutri il numero mostrato descrive l'esito.**

Ma ws4 ha 28 fatti a 99,98 in quarantena, e le due misure non possono essere entrambe complete.
**Mancava un caso al mio banco: tutti i miei 12 erano neutri.** Il banco era cieco per costruzione —
la classe che MEMORY.md chiama *«sette misuratori con lo stesso punto cieco»*, stavolta commessa da me.

## 2. Il caso mancante: due strati, e il numero ne descrive uno solo

Costruito il caso che il banco non aveva — fonte che sostiene **alla lettera**, più un vanto:

| caso | grounding | `moat` | esito |
|---|---|---|---|
| neutro, la fonte sostiene | 95,7 | passed | ammesso |
| **stessa cosa + «funziona»** *(la fonte dice «...tutti verdi, funziona»)* | **96,8** | **passed** | **quarantined** |
| stessa cosa + «è stato verificato» | 96,7 | passed | quarantined |
| «Funziona.» — la fonte lo dice | 88,8 | passed | quarantined |
| «It works.» — la fonte lo dice | 93,5 | passed | quarantined |
| neutro inglese, controllo | 97,0 | passed | ammesso |

**4 casi su 6 hanno grounding 88,8–96,8 e finiscono in quarantena.** Il secondo è il peggiore per
l'utente: la fonte sostiene *anche il vanto*, il moat **passa**, e il fatto viene respinto lo stesso.

🔑 **Il numero mostrato è fedele a UNO strato (il moat); l'esito lo decidono DUE.**
Non è «il prodotto sbaglia il numero» — è «il prodotto mostra un numero senza dire di quale strato è».

## 3. E l'informazione che manca **c'è già**, completa, nella risposta

`add()` restituisce `adjudication`, e lì dentro c'è tutto:

```
vanto + fonte che lo sostiene:
  grounding_score = 96.8       moat = "passed"
  adjudication.disposition = "quarantined"        <- l'esito VERO
  warnings[0].layer        = "L1.10"              <- CHI ha deciso
  warnings[0].reason       = "Works/confirmed claim 'funziona' lacks runtime evidence"
  warnings[0].advice       = "Add at least one of: pytest:<test>_PASS, bash:<cmd>:exit0:<n>, ..."
```

⇒ **Non è una capacità da costruire, è una capacità da esporre.** La cura è economica.

---

## 4. 🔴 Il finding più grave — dalla CLI, `admitted` significa due cose opposte

Tre scritture attraverso la porta che l'utente usa davvero (pacchetto installato da PyPI, HOME finta):

```
$ verimem remember "Il modulo alfa ha 12 test e funziona." --source "...12 test, tutti verdi, funziona."
quarantined id=13061bfbac2a topic=user

$ verimem remember "Il modulo beta ha 12 test." --source "Rapporto: modulo beta, 12 test, tutti verdi."
admitted id=b43b7bcda806 topic=user          <- VERIFICATO DAL MOAT a 93,6

$ verimem remember "Il modulo delta ha 77 test."
admitted id=15c6846dcf0e topic=user          <- MAI GIUDICATO (nessuna fonte)
```

**Le ultime due righe sono identiche.** Stessa parola, stesso formato, nessun numero. Ma la prima è
un fatto che il moat ha verificato a 93,6 e la seconda **non è mai stata giudicata**.

Questo tocca il cuore della promessa del prodotto — *«a fact its source does not support is
QUARANTINED»*, *«without a source... stored as an unverified `model_claim`»*. Sulla CLI, la parola
`admitted` copre **sia il verificato sia il mai-verificato**, e l'utente non ha modo di separarli.

📌 E nella prima riga la ragione del rifiuto — che nell'SDK è scritta per esteso con l'istruzione su
come rimediare — **non arriva**: l'utente legge `quarantined` e basta, senza sapere cosa fare.

### La stessa parola dice due cose anche fra i campi

| campo | fatto verificato dal moat |
|---|---|
| `adjudication.disposition` | `"admitted"` |
| `status` | `"model_claim"` |
| `status` di un fatto **senza fonte** | `"model_claim"` |

`status` — il campo dal nome più ovvio — è il **meno** informativo dei tre: usa per il verificato la
stessa etichetta del mai-giudicato, e un vocabolario diverso da `disposition`. L'unico campo che li
separa è `grounding_score` (**93,6** contro **`None`**), esattamente come la documentazione dichiara.

---

## 5. 🔁 Lo SWEEP: la cura esiste, ed è stata applicata a una porta su tre

A [`cli.py:1145`](../../verimem/cli.py) c'è un commento che **racconta il proprio incidente**:

> *«L'ETICHETTA DICE QUALE DEI TRE RAMI, non `disp`. La disposizione del gate vale `admitted` anche
> quando il fatto è finito in quarantena o è entrato in via GRADUATA, quindi questa riga stampava
> `admitted id=…` — la correzione NON è stata ammessa»*

La stessa derivazione (`disposition or status`) compare in **tre** comandi:

| riga | comando | ha il controllo `ammesso` |
|---|---|---|
| 871 | **`remember`** | ❌ **NO** |
| 1145 | `correct` | ✅ SI (curato) |
| 4054 | **`save`** | ❌ **NO** |

**La cura è su `correct`. Le due porte di scrittura che l'utente usa per prime non ce l'hanno.**
È la classe ② di MEMORY.md — *mancava lo sweep: chi ALTRO fa la stessa cosa?*

⚠️ **Confine dichiarato**: che `remember` stampi `admitted` per un quarantinato (il caso che il
commento documenta) **non l'ho riprodotto** — nel mio banco `disposition` valeva già `quarantined`.
Lo consegno come **rischio da verificare**, non come difetto misurato. Quel che è misurato è il §4.
E che `cli.py:873` stampi `[green]{disp}[/green]` **incondizionatamente** — quindi in verde anche
`quarantined` — è **lettura del sorgente, non misura a schermo**: da pipe il colore non si osserva.

---

## 6. La lettura: il numero separa, e la porta non lo guarda

```
domanda                                        esiste?   risponde?  score
Quanti pezzi ha il magazzino di Bologna?         sì         sì      0.9131
Quanti pezzi ha il magazzino di Napoli?          sì         sì      0.9141
In quanti giorni consegna il corriere Alfa?      sì         sì      0.8896
Quanti pezzi ha il magazzino di Trento?          NO         sì      0.8480
In quanti giorni consegna il corriere Zeta?      NO         sì      0.8623
Qual è il fatturato del 2019?                    NO         sì      0.7567

peggiore VERA 0.8896 · migliore SENZA RISPOSTA 0.8623 · margine +0.0273
risponde a domande senza risposta: 3/3
```

Nessuna inversione: il numero **separa** le due popolazioni. Ma la porta risponde comunque a tutte.
🔸 Il mio 0.8480 su Trento riproduce indipendentemente lo 0.8495 di ws5 (store diverso, banco diverso).
⚠️ Margine **+0.0273 su n=3 per gruppo**: troppo poco per tarare una soglia — ws5 lo ha già detto.

---

## Riepilogo del censimento

| porta | il numero/etichetta mostrato | verdetto |
|---|---|---|
| scrittura, fatti neutri | grounding 95,7–99,6 vs 0,6–1,2 | ✅ descrive l'esito, 0 inversioni su 12 |
| scrittura, fatti con un vanto | grounding 88,8–96,8, `moat: passed` | ❌ **contraddice** l'esito: decide un altro strato |
| **CLI, scrittura** | `admitted` | ❌ **la stessa parola per il verificato e per il mai-giudicato** |
| lettura | score 0,7567–0,9141 | ⚠️ separa (+0,0273), ma la porta non lo usa: risponde 3/3 |

🔑 **La forma unificata delle tre osservazioni indipendenti**: non è che il prodotto non sappia — è
che **sa e non lo dice**. L'informazione esatta esiste in `adjudication` a ogni singola scrittura;
la porta ne mostra una proiezione che perde proprio la distinzione per cui il prodotto esiste.

**Caveat**: un dominio, frasi corte, store isolato per ogni esecuzione, CLI dal pacchetto PyPI
installato (non dal repo), SDK dal worktree pulito allo SHA `31578d56`, ore 14:00–14:11.
