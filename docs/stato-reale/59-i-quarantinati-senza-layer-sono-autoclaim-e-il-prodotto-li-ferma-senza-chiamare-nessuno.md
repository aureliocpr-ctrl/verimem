# 59 — I quarantinati che non dichiarano il layer sono auto-claim, e il prodotto li ferma senza chiamare nessuno

*ws6/Aldo — 31 agosto 2026, alba. Chiude un limite che avevo lasciato aperto per giorni, e aggiorna la misura della perdita.*

Fra i miei limiti dichiarati ce n'era uno che nessuno aveva ripreso: **«i
quarantinati di agosto non dichiarano quale layer li ha fermati»**. Un fatto
messo in quarantena senza dire da chi è un verdetto senza firma, e sembrava un
difetto della telemetria.

**Non lo è.** E la spiegazione è arrivata da un posto che non stavo guardando.

## ① Un topic in cui il 98% non è servibile

Cercando **altro** — la quota di quarantena per famiglia di topic — è saltato
fuori questo:

| prefisso di topic | non superseduti | quarantinati | quota |
|---|---|---|---|
| **`veriagent`** | 48 | **47** | **97,9%** |
| `c10` (banco halumem importato) | 181 | 93 | 51,4% |
| `archive` | 188 | 95 | 50,5% |
| … | | | |
| **corpus intero** | **14470** | **1283** | **8,9%** |

Quarantotto fatti scritti, **quarantasette muti**. Sono tutti del **18 luglio**,
fra le 08:32 e le 23:08 — una sola giornata — e hanno tutti la stessa forma:

```
Task veriagent completato con receipt — 'Esegui solo questo comando shell...'
Task veriagent completato con receipt — 'crea il file demo_ux.txt con...'
Task veriagent completato con receipt — 'esegui il comando: git status...'
```

**Sono auto-claim**: «task completato». E il prodotto dichiara di fermarli:

> *«ON EVERY WRITE THROUGH THIS API: a lexical screen. Unsupported "it works /
> verified / done" self-claims are quarantined, **with no LLM call**.»*

🔑 **«With no LLM call»** — ed è lì la risposta: **lo screen lessicale non passa
per nessun layer, quindi non ha un layer da registrare.** Su tutti e 48,
`quarantined_by` è `NULL`. **Non una telemetria rotta: una fase che precede i
layer.**

## ② La verifica, su ENTRAMBE le popolazioni

Un'ipotesi che spiega i 48 casi da cui è nata non vale niente. **Misurata sui
1283 quarantinati non superseduti**, confrontando chi il layer **non** lo
dichiara con chi lo dichiara — perché sui soli primi qualunque criterio
sembrerebbe ottimo.

| criterio di «auto-claim» | **senza** layer | **con** layer | divario |
|---|---|---|---|
| largo (`completato, riuscito, funziona, fatto, done, works, ok, receipt`…) | 372/661 = **56,3%** | 59/623 = 9,5% | **+46,8** |
| senza `fatto`/`ok` (ambigui) | 311/661 = **47,0%** | 44/623 = 7,1% | **+40,0** |
| **stretto** (solo participi di esito) | 270/661 = **40,8%** | 18/623 = **2,9%** | **+38,0** |

**Il divario regge su tutti e tre**, e col criterio più stretto la separazione è
di **quattordici volte**. ⇒ **chi non dichiara il layer è, in larghissima
maggioranza, un auto-claim fermato prima dei layer.**

🪞 **Il primo criterio aveva un falso positivo che ho trovato leggendo gli
esempi**, non i numeri: *«**Test fatto** del Round 5 di Aurelio»* — dove
«fatto» è un **sostantivo**, non un participio. È il motivo per cui i criteri
sono tre: se il divario fosse esistito solo col criterio largo, sarebbe stato il
mio regex a produrlo.

⚠️ **E il residuo non è spiegato**: col criterio stretto, **391 dei 661** senza
layer non hanno marcatori di esito. **L'ipotesi copre la maggioranza, non tutto**,
e non ho indagato il resto.
⚠️ **Numeri diversi da quelli del limite**: il limite parlava di «207
quarantinati **di agosto**», qui misuro **tutti** i non superseduti (661 senza
layer). Popolazioni diverse, e lo dico invece di far coincidere le cifre.

## ③ La perdita, aggiornata: 21% (era 25% sedici giorni fa)

Ho usato **il righello che c'era già** — `scripts/quanti_fatti_sono_davvero_serviti.py`,
scritto il 4 agosto da chi aveva fatto **esattamente il mio errore di stanotte**
(contare `superseded_by IS NULL` credendo di contare i vivi):

```
scritti             16755
non superseduti     14470   (ritirati: 2285)
DAVVERO SERVITI     13187   (muti perche' quarantined: 1283)
perdita totale       3568   (21% di cio' che e' stato scritto)
```

| | 15/08 | **31/08** |
|---|---|---|
| scritti | 10753 | **16755** |
| serviti | 7975 | **13187** |
| **perdita** | **25%** | **21%** |

**Due letture, entrambe vere**: la **quota** migliora (25% → 21%), il **numero
assoluto** peggiora (2778 → 3568 fatti persi, +790). Chi cita solo la prima fa
marketing; chi cita solo la seconda fa allarmismo.

📌 **E i ritiri sono tornati a pesare più delle quarantene**: 2285 contro 1283.
Il 15/08 avevo annotato che il peso *«era passato dai ritiri alle quarantene»*;
oggi il rapporto è di nuovo 1,8 a 1 a favore dei ritiri. **Non ho il dettaglio
del 15/08 per dire quando si è invertito**, quindi non lo racconto come una
tendenza.

## ④ Una trappola evitata, e vale quanto un reperto

Stavo per scrivere: *«i fatti inglesi sono quarantinati quattro volte più della
media (38% contro 8,9%)»*. **Sarebbe stata una correlazione spuria.** La quota
per prefisso di topic mostra che quel 38% viene da **`c10/halumem`, un corpus di
benchmark importato che sta al 51,4%** — non dalla lingua.

**È la quarta volta stanotte che il campione spiega il numero**, ma la prima in
cui l'ho verificato **prima** di pubblicare invece che dopo.

---
*Banco: `banchi/ws6-quarantinati-senza-layer.py` (misura entrambe le popolazioni
e stampa i topic che concentrano i senza-layer). Righello della perdita:
`scripts/quanti_fatti_sono_davvero_serviti.py`, già nel repo. Store di Aurelio
in sola lettura.*
