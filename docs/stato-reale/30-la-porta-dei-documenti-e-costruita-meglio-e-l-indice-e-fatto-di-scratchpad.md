# 30 — La porta dei documenti è costruita meglio, e l'indice è fatto di scratchpad

**ws6 · 30/08 ore 20:15** · `~/.engram/documents/document_index.db`, `mode=ro`, sole SELECT.

Tutto il lavoro di oggi (documenti 17-29) misura **la ricerca dei FATTI**. La ricerca dei
**DOCUMENTI** è un'altra porta, con un altro store, e non l'aveva guardata nessuno. È nel mio
perimetro.

---

## 🟢 La buona notizia: qui il difetto principale NON c'è

```
                     ricerca FATTI                    ricerca DOCUMENTI
   criterio      LIKE + ORDER BY created_at DESC      coseno + rerank
   decide        la DATA                              il PUNTEGGIO
   vettore       —                                    683 chunk su 683
```

`document_index.py:470` calcola il coseno (`np.dot(qv, v) / (qn * vn)`); `_applica_rerank`
(riga 156) aggiunge un secondo passaggio e **tiene `score` e `rerank_score` separati**, con un
commento che spiega perché: *«sono due misure diverse»*.

⇒ **Il difetto che ho documentato tutto il giorno — l'ordinamento per data — sulla porta dei
documenti non esiste.** E ogni chunk ha il suo vettore: **683 su 683**, nessuna eccezione.

## 🔴 La cattiva: l'indice è fatto quasi solo di nostri scratchpad

```
   683 chunk · 42 documenti distinti · 30 source_id

   40 documenti su 42 vengono da scratchpad o da temp        (95%)
   il singolo HANDOFF-dogfooding-2026-08-01.md               334 chunk = 49% dell'indice
   l'unico documento "di prodotto":  docs/ROADMAP-v0.7.md     53 chunk
```

Gli altri sono messaggi di lavoro (`PER-WS3-il-percorso-utente-nuovo-e-rotto-due-volte.md`,
`PER-WS3-la-guardia-polarita-non-parla-italiano...`) e un `log-fissato.txt` in `AppData\Local\Temp`.

⇒ **Un utente che installa il prodotto e indicizza i suoi documenti userebbe una porta ben
costruita su un indice che, da noi, contiene i nostri appunti.** Le due cose non si contraddicono:
**la porta è buona, il corpus è nostro** — ed è lo stesso avvertimento che @ws3 ha dato sui fatti
(*«ogni tasso che misuriamo qui è sul nostro traffico»*), qui in forma più estrema: **95%**.

## 🪞 Due campi che esistono e non dicono niente

· **`indexed_by`: vuoto in 683 chunk su 683.** Il campo per sapere **chi** ha indicizzato un
  documento c'è, ed è **sempre nullo**.
· **Nessun campo data.** Non esiste `created_at` né equivalente: **non si può sapere quando un
  documento è stato indicizzato**, e quindi **non si può spezzare per era** — la regola che oggi ha
  salvato due miei allarmi falsi sui fatti **qui non è applicabile per mancanza del campo**.

⇒ È la stessa forma di `writer_principal` (generico nel 94% dei casi sui fatti) e di
`quarantined_by` prima del 7 agosto: **un campo presente e muto è peggio di un campo assente**,
perché chi lo legge crede di avere un'informazione.

## Cosa NON ho misurato

· **La qualità della ricerca sui documenti**: ho letto il criterio nel codice, **non l'ho provata**
  con una query nota. Dire «è costruita meglio» è un'affermazione **sul codice**, non sul
  comportamento — e oggi ho imparato tre volte che sono due cose diverse.
· **Se il rerank sui documenti gira o va in timeout** come quello dei fatti.
· **Perché l'indice contiene scratchpad**: se sia stato un test, un dogfooding o un incidente.
  **Non l'ho ricostruito, e senza il campo data non è ricostruibile da qui.**
· **L'istante è parte del dato**: 30/08 ore 20:15.
