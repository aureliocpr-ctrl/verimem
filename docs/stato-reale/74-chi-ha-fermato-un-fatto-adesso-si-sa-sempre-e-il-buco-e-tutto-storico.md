# 74 — Chi ha fermato un fatto adesso si sa sempre, e il 71% di buco è tutto storico

*ws6/Aldo — 2 settembre 2026, 01:24 (letta). Chiude in positivo un aperto che il
registro portava con un numero superato.*

## ① L'aperto, com'era

In memoria l'aperto diceva **`quarantined_by` 3,8%** — cioè: per quasi tutti i
fatti trattenuti non si sapeva **quale strato** li avesse fermati, e chi si
chiedeva perché un fatto non tornasse non aveva risposta.

Oggi, sui **2688** quarantinati del corpus, il campo è vuoto su **1909 = 71%**.
Sembra lo stesso difetto, più grande. **Non lo è.**

## ② La domanda che separa il debito dal difetto

Un campo vuoto sul 71% ha due letture opposte: **nessuno lo popola** (difetto
vivo) oppure **è stato aggiunto dopo** (debito storico). Si separano guardando
**quando** sono stati scritti i fatti:

```
2026-05   1579 quarantinati   senza responsabile 1579 = 100.0%
2026-06     47                                     47 = 100.0%
2026-07     77                                     77 = 100.0%
2026-08    964                                    206 =  21.4%   ← entra in funzione
2026-09     21                                      0 =   0.0%

ULTIME 24H: 21 quarantinati, 0 senza responsabile
```

> ✅ **Il campo è vivo e completo.** Zero vuoti nelle ultime 24 ore e su tutto
> settembre; ad agosto la transizione. **Il 71% è interamente debito storico** —
> 1703 fatti di maggio-luglio più i 206 di agosto scritti prima che il campo
> entrasse in funzione.

## ③ E il contenuto è informativo, non un'etichetta vuota

Dei 779 che ce l'hanno:

```
moat 512 · L4.1 150 · gate 55 · L4-review 43 · L3-coexistence 15 · L1 2 · store-screen 1
```

⇒ Nomina lo **strato** che ha deciso, non un generico «bloccato». È
l'informazione che serve a chi chiede *perché questo fatto non torna*.

## ④ Perché lo pubblico con la stessa prontezza di un allarme

Il numero in memoria — **3,8%** — è **superato**, e finché resta scritto un
lettore lo cita come stato attuale. **Un dato favorevole al prodotto invecchia
esattamente come uno sfavorevole**, e correggerlo costa quanto correggere un
allarme.

📌 **La forma è quella già in registro**: *«un referto su una grandezza che si
muove va datato»*. Questo lo è: **02/09 01:24**.

## ④-bis Il limite che avevo dichiarato, chiuso due minuti dopo: **il campo discrimina**

Avevo scritto «ho misurato che il campo è popolato, non che l'attribuzione sia
corretta». Verificato su uno store **temporaneo** (`HIPPO_DATA_DIR` prima degli
import, mai lo store di Aurelio), quattro scritture con esiti attesi diversi:

| caso | status | `quarantined_by` |
|---|---|---|
| numero che la fonte non contiene | `quarantined` | **`moat`** (grounding 0,77) |
| claim non sostenuto dalla fonte | `quarantined` | **`moat`** (grounding 0,56) |
| auto-claim **senza fonte** | `quarantined` | **`L1`** ← strato diverso |
| vero **e** sostenuto *(controllo positivo)* | `model_claim` | **`None`** |

⇒ ✅ **Tre esiti, tre etichette diverse, e il controllo positivo resta vuoto.**
Il campo non è un'etichetta uniforme appiccicata a ogni quarantena: **nomina
strati diversi per cause diverse**, e tace dove non c'è quarantena.

🔎 **Un dato inatteso che NON dichiaro come correzione**: il decimale italiano
(`176,6`) **non** è stato quarantinato, mentre il registro porta *«decimali con
la virgola → quarantina»*. ⚠️ Ma la mia fonte conteneva `176.6` **col punto**,
quindi non è il caso puro — il moat può aver trovato la corrispondenza
semantica. **Serve un test mirato prima di toccare quella riga.**

## ⑤ Cosa NON prova
⚠️ **I 1909 storici restano ciechi** e non sono ricostruibili: chi analizza il
corpus di maggio-luglio non saprà mai chi ha fermato quei fatti.
✅ **Quello che regge**: le cinque righe per mese e il conteggio sulle 24 ore.
Sono `SELECT` su `mode=ro`, non inferenze.

---
*Nessun banco: due query in sola lettura sullo store di Aurelio.*
