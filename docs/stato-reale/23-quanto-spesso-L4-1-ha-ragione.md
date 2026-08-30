# 23 — Quanto spesso `L4.1` ha ragione

**ws6 · 30/08 ore 16:20** · store in `mode=ro`, sole SELECT.

Il [documento 22](22-un-quarto-dei-trattenuti-recenti-e-approvato-dal-giudice.md) si chiude con un
limite dichiarato: *«non ho letto i 70»* — i fatti che **`L4.1` trattiene mentre il giudice li
approva a ≥ 90**. Quel numero misurava **un disaccordo**, non una perdita. Qui lo chiudo.

---

## Il criterio, e perché non è un giudizio mio

`L4.1` ferma **«i valori del claim assenti dalla fonte»**. La verifica quindi non richiede di
decidere se un fatto «è vero»: basta estrarre i numeri dalla `proposition` e cercarli nel
`grounding_span`. **Se ci sono tutti, `L4.1` ha fermato qualcosa che la fonte sostiene.**

✅ Il troncamento della fonte pesa poco: solo **7 span su 70** sono al limite dei 400 caratteri,
**63 sono interi**.

## Il quadro

```
   L4.1 ha RAGIONE — almeno un numero del claim è assente dalla fonte     42
   falso allarme più probabile                                            14
   la fonte contiene un VERDETTO DEL GATE (eco)                            5
   il claim ha numeri scritti in LETTERE — il mio criterio non li vede     2
   fonte al limite dei 400 caratteri, non decidibile                       7
                                                                        ----
                                                                          70
```

⇒ **`L4.1` ha ragione in circa due casi su tre.** Non è un layer che sbaglia: è un layer che
**decide spesso contro il giudice, e per lo più con ragione**.

---

## 🔑 Il numero è sceso da 21 a 14 perché ho letto tre casi

Il conteggio automatico diceva **21** «tutti i numeri sono nella fonte». Leggendone tre, il criterio
si è rivelato più grossolano del fenomeno:

**① `db75b5bf67e8` — falso allarme confermato.**
Claim: *«Il commit del tag v0.7.0 è del 2026-07-22 13:13:18 mentre PyPI riporta upload alle 11:46»*.
Fonte: *«commit del tag v0.7.0: 2026-07-22 13:13:18 +0200»* e *«PyPI dice upload 2026-07-22T11:46»*.
**Tutti i valori ci sono, e il claim li usa nel modo giusto.**

**② `cf0517c6ef72` — il mio criterio è cieco.**
Claim: *«…contiene 0.971 **sei** volte»*. Fonte: *«veribench-preprint-DRAFT.md 0.971**x6**»*.
Il numero è scritto **in lettere** nel claim e in cifre nella fonte: **il mio estrattore non lo
vede**, e quel fatto non avrebbe dovuto entrare nel conto.

**③ `f72209bc802c` — un'eco, nel corpus reale.**
La fonte **contiene un verdetto del gate stesso**:
`{"layer": "L4.1", "reason": "il claim afferma un valore che la fonte non contiene: 999 passed"}`.
⇒ **La fonte non è un documento: è l'output di una misura che a sua volta cita il gate.**

Riclassificando i 21 con questi tre criteri: **5 eco · 2 ciechi · 14 falsi allarmi più probabili.**

📌 **Per @lead-audit e @ws4**: quei **5 sono esemplari di eco trovati nel corpus reale**, non in un
banco costruito. Se servono come popolazione di prova per il DoD della guardia ratificata alle
14:00, ci sono.

---

## Limiti

· **Il criterio è la presenza della STRINGA numerica**, non il legame soggetto-valore. Il reperto
  `752d625fac03` mostra che il gate distingue *il valore presente attribuito a un altro soggetto*:
  se `L4.1` fa altrettanto, **anche alcuni dei 14 sono suoi successi** e il numero scende ancora.
  **La direzione dell'errore è nota: 14 è un tetto, non un pavimento.**
· **7 casi restano non decidibili** per il troncamento a 400 caratteri.
· **Non ho eseguito `requalify`**, nemmeno in dry-run: riammettere è una decisione sullo store di
  Aurelio, e questo documento serve a chi la prende — non la prende.
· **L'istante è parte del dato**: 30/08 ore 16:20.

🪞 **E la lezione del pezzo**: il conteggio automatico dava 21, la lettura di **tre** casi l'ha
portato a 14 e ha trovato un fenomeno che non stavo cercando. **Tre letture valgono più di un
filtro**, e il filtro l'avevo scritto io.
