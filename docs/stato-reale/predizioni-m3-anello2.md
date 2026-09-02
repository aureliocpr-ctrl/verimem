# M3 anello ② — PREDIZIONI SCRITTE PRIMA DELL'ESPERIMENTO

**ws2 «Varco», 02/09 ore 12:52.** Scritte e salvate *prima* di eseguire qualunque
misura sui criteri. Chi le legge dopo può falsificarmi con il comando in fondo.

---

## Premessa: il banco «213 casi già classificati» non esiste

Il mandato dice *«sui 213 casi già classificati (143 ordinari + 70 sospetti)»*.
Ho controllato i due numeri prima di partire, e vengono da **due misure diverse**:

- **143** — da `49e67921d177`: *«Dei 1758 ritiri nel corpus 1463 sono master
  pre-compact che ne sostituiscono un altro e 143 sono fatti ordinari che ne
  ritirano un altro.»* È un censimento **per tipo di scrittura**, non una
  classificazione giusto/sbagliato.
- **70** — da `29b35cf2386b`: *«fra quelli ritirati da `numeric_clash` è 34.3 per
  cento **su 70**»*. È la popolazione di **un altro motivo di ritiro**.

⇒ **Sommarli dà 213 ma non dà un insieme classificato**: nessuno dei due porta
un'etichetta «questa supersessione era sbagliata». **E i `numeric_clash` oggi
sono 147, non 70** (baseline anello ①).

**Quindi la popolazione dell'esperimento la dichiaro io**: le coppie
`(ritirato → sostituto)` con `superseded_reason LIKE 'same-source%'`, che alla
baseline delle 12:35 sono **466**. Il verdetto «sbagliata» resta il criterio
dell'anello ①: il ritirato aveva `grounding_score >= 90`, cioè il giudice lo
sosteneva — **463 su 466, il 99,4%**.

---

## Le predizioni

Numeriche, falsificabili, e dove divergo da quella di `lead-audit` lo dico.

### T3.3 — i tre criteri, una variabile per volta

| # | criterio | la mia predizione | perché |
|---|---|---|---|
| **(a)** | **coseno alto** | **precision < 60%** — non separa | i fatti superseduti si somigliano *per costruzione*: è la ragione per cui il jaccard non li vede (memoria: *«si somigliano, quindi li scarta»*), e otto criteri su otto sono già caduti su questa strada |
| **(b)** | **entità+attributo uguali** | **recall > 80% ma precision < 40%** | `62c2a8610c99` misura che *«il veto sulle entità estratte blocca 56 delle 65 coppie con reason same-source evolution»* = **86%**. Un criterio che blocca l'86% delle supersessioni blocca anche quelle **giuste** |
| **(c)** | **NLI contradiction** | **precision > 80%, recall < 40%** | qui **concordo** con la letteratura e con `lead-audit` |

**DOVE DIVERGO DA `lead-audit`, e lo scrivo prima**: la sua predizione è
*«(b) da solo porta le supersessioni sbagliate sotto il 15%»*. **Io predico che
(b) le porti sotto il 15% E che allo stesso tempo blocchi la maggioranza delle
supersessioni legittime** — perché il numero che abbiamo già dice 86% di blocco.
⇒ **«sbagliate sotto il 15%» e «criterio utilizzabile» non sono la stessa cosa**,
e senza misurare i legittimi bloccati il primo numero non decide niente.
**Il banco deve misurare ENTRAMBE le popolazioni**, o ripete l'errore che ho già
pagato tre volte stanotte.

**PREDIZIONE AGGIUNTIVA, che nasce da una misura mia di stanotte e che la
letteratura non copre**: su una fonte **tabellare di più di ~13 righe** il
giudice smette di distinguere un valore falso da uno vero (`W2-405`: il falso
passa da `0,34` a `86,42` aggiungendo poche righe). ⇒ **predico che il recall di
(c) sia ANCORA PIÙ BASSO sulle coppie la cui source è tabellare**, e che la
differenza fra i due sottoinsiemi sia **almeno 15 punti di recall**.

### T3.1 — bi-temporale

- **≥ 80% dei fatti oggi muti per supersessione torna servibile.** *(la
  predizione di `lead-audit` dice ≥34%: io predico molto più alto, perché la
  baseline dice che il **99,4%** dei ritirati aveva grounding ≥90 — erano quasi
  tutti buoni)*
- **contraddizioni servite > 5%.** *(qui divergo nell'altro verso: `lead-audit`
  predice ≤5%. Servire due versioni di una misura A/B è precisamente ciò che la
  memoria registra come dannoso — «un A/B sta in UN fatto solo» — e il
  bi-temporale le rimette entrambe in circolo)*

### `supersede()` come append di una riga-versione

- **crescita DB < 2%** — concordo. Su 17186 fatti i superseduti sono 2300: una
  riga-versione per ognuno è metadato, non testo.
- **zero fatti persi** — concordo, ma **è una tautologia se non si misura il
  recall**: un fatto che c'è e non torna è perso per chi lo cerca. **Predico che
  il numero che conta non sia «fatti persi» ma «fatti serviti», e che vada
  misurato con una query, non con un `COUNT(*)`.**

---

## Come falsificarmi

Baseline riproducibile dell'anello ①:

```
python scripts/baseline_supersessioni_sbagliate.py
```

L'esperimento dell'anello ③ userà la stessa popolazione e lo stesso criterio, e
stamperà **entrambe le popolazioni** per ogni criterio: le sbagliate fermate e
le legittime bloccate.

---

## Cosa NON prometto

- Non ho ancora eseguito nulla dei tre criteri: **queste sono predizioni, non
  misure**.
- Il criterio «sbagliata = il ritirato aveva grounding ≥90» **è una proxy**: dice
  che il giudice sosteneva il fatto, non che il fatto fosse vero nel mondo. Se il
  giudice sbaglia, sbagliano tutte e tre le colonne insieme.
- `ChronoMem` non lo tocco: è fuori mandato e `lead-audit` lo ha già escluso.
