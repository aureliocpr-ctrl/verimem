# 28 — Cercare nel topic costa MENO, non di più

**ws6 · 30/08 ore 19:10** · corpus servibile **12.445**, `mode=ro`, sole SELECT.

Il [documento 27](27-la-porta-ignora-il-campo-che-dice-di-cosa-parla-un-fatto.md) si chiude
dichiarando **due misure mancanti** — il costo e il rumore — e dicendo: *«non propongo la cura
finché non è cronometrata»*. **Ora lo è.**

---

## La predizione, scritta prima di eseguire

> `LIKE` su due colonne raddoppia i parametri, **ma fa riuscire il ramo AND** ed evita il ripiego OR
> che oggi aggancia migliaia di righe e le ordina tutte. ⇒ **P+T sarà più veloce sui recenti e sui
> medi, e comparabile sui vecchi.**

## Il cronometro

```
   fascia   |  P mediana   P max   ramo  |  P+T mediana   P+T max   ramo
   recenti  |    283,0 ms  340,7    OR   |     127,1 ms    138,7    AND
   medi     |    324,3 ms  406,7    OR   |     144,0 ms    172,2    AND
   vecchi   |     99,3 ms  323,3    AND  |     126,7 ms    171,9    AND
```

· **recenti −55% · medi −56% · vecchi +28%.**
· 🔑 **La colonna che spiega tutto è il RAMO**: dove oggi si ripiega sull'OR, cercare anche nel topic
  **fa riuscire l'AND**; dove l'AND già riesce, si paga solo il raddoppio dei parametri.

⚖️ **La predizione regge su due fasce su tre. Sulla terza era ottimista**: avevo scritto
«comparabile», ed è **+28%** (99 → 127 ms). Lo scrivo perché una predizione confermata a metà va
dichiarata così, non arrotondata.

## Il rumore — la seconda misura mancante

I candidati mediani passano da **1.259 / 2.411 / 5** a **1 / 1 / 20**.

⇒ **Il rumore non aumenta: crolla.** L'unico aumento è sui vecchi (5 → 20), e non è rumore nuovo —
è il contrario: **i 5 candidati di oggi non contengono il fatto cercato** (18 su 20 «mai
candidati»), quindi sono **pochi e sbagliati**. Con il topic diventano venti **e lo contengono**.

🔑 **Il meccanismo, detto bene: `P+T` non filtra meglio — fa riuscire l'AND.** Ed è per questo che
riduce insieme il tempo *e* il numero di candidati, che di solito vanno in direzioni opposte.

---

## Che cosa si può proporre adesso, e cosa ancora no

**Misurato:** l'aggancio (candidati da 2.411 a 1, «mai candidati» a zero) · il costo (−55% dove la
porta oggi ripiega, +28% dove già funziona) · il rumore (non aumenta).

**Ancora NON misurato, e quindi non promesso:**
· **la pertinenza dei candidati in più** sui vecchi: sono venti invece di cinque, e non li ho letti;
· **il comportamento su query che NON vengono dal topic** — tutto questo lavoro usa le parole del
  topic come domanda, e **quella circolarità resta** (dichiarata nel doc 27). Il costo e il numero di
  candidati non ne dipendono; **il tasso di ritrovamento sì**;
· **l'effetto su `hippo_facts_search` reale**: questo è SQL che replica la porta, **non la porta**.
  Prima di toccarla servirebbe un RED→GREEN come quello dell'avviso (`5219443a`).

## Limiti

· **n=20 per fascia**, 60 query in tutto, una sola esecuzione per variante: **le mediane sono
  robuste, i massimi no**.
· I tempi includono l'ordinamento e la materializzazione di tutti gli id — che è ciò che fa anche
  la porta, ma **su una macchina che nel frattempo faceva altro**.
· **L'istante è parte del dato**: 30/08 ore 19:10, corpus servibile 12.445.
