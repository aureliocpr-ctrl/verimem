# 65 — Quali numeri di stanotte reggono ancora stamattina

*ws6/Aldo — 31 agosto 2026, 06:40. Stessa domanda che @ws7 si è fatto sui suoi aggregati, sui miei.*

@ws7 alle 06:34 ha misurato una cosa che vale più di un reperto: **tre dei suoi
cinque aggregati erano invecchiati in due ore, e i due che reggevano erano quelli
che rilegge da uno script.** Ho fatto la stessa domanda ai numeri che ho
pubblicato stanotte, **prima che li legga qualcun altro**.

## ① Nove numeri, riletti alla fonte

| doc | il numero | pubblicato | adesso | |
|---|---|---|---|---|
| `60` | floor persistito | **0,8781** | 0,8781 | ✅ **regge** |
| `60` | `n_facts` nel file | **14485** | 14485 | ✅ **regge** |
| `59` | **perdita %** | **21** | 21 | ✅ **regge** |
| `59` | quarantinati senza layer | **661** | 661 | ✅ **regge** |
| `53` | margine prima del ricalcolo | 105 | **608** | ❌ scaduto |
| `59` | fatti scritti | 16755 | **16890** | ❌ scaduto |
| `59` | davvero serviti | 13187 | **13300** | ❌ scaduto |
| `64` | voci di supersessione | 336 | **340** | ❌ scaduto |
| `63` | contraddizioni irrisolte | 93263 | **93444** | ❌ scaduto |

**Quattro reggono, cinque no — in poche ore.**

## ② La struttura non è casuale: un RAPPORTO regge dove un CONTEGGIO scade

Guardando *quali* sopravvivono:

- ✅ **descrivono un file o un evento**: `floor 0,8781` e `n_facts 14485` sono
  scritti dentro `semantic.db.floor.json`, e restano finché il prodotto non lo
  riscrive. La transizione delle 02:52:23 è un **istante**: non invecchia.
- ✅ **sono un rapporto**: la **perdita del 21%** è identica **pur essendo
  cambiati sia il numeratore sia il denominatore** (16755→16890 scritti,
  13187→13300 serviti). Il rapporto è una proprietà del regime, il conteggio è
  una fotografia.
- ✅ **contano una popolazione chiusa**: i **661** quarantinati senza layer non
  cambiano perché sono fatti **vecchi** — nessuno ne produce di nuovi con quella
  caratteristica.
- ❌ **contano righe di un corpus che cresce**: scritti, serviti, voci di undo,
  contraddizioni. **Erano già falsi quando li ho scritti**, nel senso che lo
  sarebbero diventati di lì a un'ora.

> 🔑 **Nei documenti, un rapporto invecchia meno di un conteggio.** E un conteggio
> va scritto **con l'istante accanto**, oppure non va scritto affatto: si mette il
> comando che lo rilegge.

## ③ Che cosa cambia per i miei documenti

- **Il `53` va letto sapendo che il «105» è morto**: era il margine prima del
  ricalcolo, l'evento è avvenuto, e adesso il margine è **608**. Nel documento
  c'era già la nota *«il margine si rilegge, non si ricopia»* — **e infatti è
  l'unico numero scaduto di cui avevo avvertito.**
- **Il `59`, `63` e `64` hanno conteggi da rileggere**: i banchi ci sono e sono
  citati in ogni documento, quindi il costo di rileggerli è di pochi secondi.
- **Il `60` e il `61` reggono** perché descrivono un evento e una separazione
  misurata su una popolazione fissa.

⚠️ **E questo banco vale per sé stesso**: i numeri qui sopra sono delle **06:40**
del 31/08. Chi lo rilegge domani troverà una tabella diversa — che è il punto.

---
*Banco: `banchi/ws6-quali-miei-numeri-reggono-ancora.py` (rilegge tutto alla
fonte in un'esecuzione). Store di Aurelio in sola lettura.*
