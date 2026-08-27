# ⑫ Il rimedio del caso difficile parte, costa, e non arriva

**Misurato il 27/08/2026 fra le 20:37 e le 21:12** · codice `Code/HippoAgent`
`6cbeb283` (= il `build=` stampato nei log), `client.py` e `anti_confab_gate.py`
puliti nella stessa esecuzione · tutte le misure **fuori da pytest**, dove
l'embedder è uno stub su SHA-256 (`tests/conftest.py:121`).

---

## In una riga

Il gate **isola bene** il proprio caso difficile e **ha un rimedio dichiarato**
per quel caso; il rimedio **parte a ogni scrittura incerta, invoca davvero il
giudice, costa 20–52 secondi, e il verdetto si perde prima di tornare** — e
nessun campo della ricevuta dice che ci ha provato.

> ⚠️ **Il titolo di questo documento dice «non arriva» ed è impreciso**: misurato
> alle 21:17, la CLI c'è (`shutil.which('claude')` la trova), ollama no, e il
> percorso `_score_via_claude` **viene preso**. Il nome del file resta perché è
> già citato altrove; la formulazione giusta è nella §5-bis.

---

## 1. Come ci sono arrivata, compresi i tre errori

Il percorso conta perché tre delle mie letture intermedie erano sbagliate, e
ognuna sembrava conclusiva.

| ora | quello che ho scritto | come è caduta |
|---|---|---|
| 20:43 | «il giudice è più debole sulla fonte **corta**» | falso: a 1000 caratteri dà 0.3, cioè è perfetto |
| 20:47 | «a 4000–10000 il giudice **non vede** la smentita» | falso: togliendola il punteggio va da 99.3 a 1.1 ⇒ la vede |
| 21:02 | «i venti secondi **non** sono la band escalation» | falso: l'A/B con l'interruttore la conferma |

📌 La terza è la più istruttiva: avevo **dedotto** l'escalation dal sorgente,
poi l'ho **ritirata** perché la ricevuta diceva `judge: local_gate_ce_v2` e il
punteggio era identico al bit. Quei due fatti non la smentivano: **la
completavano**. `escalate_band` è *fail-soft* — torna `None` quando nessun
giudice risponde, e allora «*the write lands exactly as before*».
⇒ **Una deduzione dal codice e una misura che sembrano contraddirsi possono
descrivere due metà dello stesso meccanismo.**

---

## 2. Il fatto centrale: è la banda, non la lunghezza

Le due variabili erano confuse perché tutte le celle lente erano **anche**
corte. Il 2×2 le separa — **stessa fonte, 2000 caratteri**:

| fonte | claim | esito | ground | ms |
|---|---|---|---|---|
| 2000 | FALSO | quarantined | 55.2 | **43630** |
| 2000 | VERO | model_claim | 100.0 | **208** |
| 6000 | FALSO | quarantined | 99.3 | 79 |
| 6000 | VERO | model_claim | 100.0 | 119 |

⇒ **210 volte più lento a parità di lunghezza.** Il punteggio centrale costa,
quello estremo no. La lunghezza spiega solo **quando** il punteggio finisce al
centro — il «confine fra 2700 e 2800 caratteri» misurato per bisezione resta
una descrizione giusta e **non è una causa**.

## 3. La prova: l'interruttore che il modulo documenta

`band_escalation.py:16` dichiara «`ENGRAM_BAND_LLM=0` opts out». A/B **nella
stessa esecuzione**, immune alla copia di lavoro che si muove:

```
  A escalation ACCESA      55.2    52030 ms   judge=local_gate_ce_v2
  B escalation SPENTA      55.2      235 ms   judge=local_gate_ce_v2
  C riaccesa, controllo    55.2    22270 ms   judge=local_gate_ce_v2
```

Il giro **C** esclude che B sia veloce per essere il secondo. **E il punteggio è
55.2 in tutti e tre**: il rimedio che `band_escalation.py:1` promette — «*the
moat's uncertain middle gets a real verdict*» — **non arriva**.

---

## 4. ✅ Quello che il prodotto FA, e che va detto con la stessa forza

Soglie **lette a runtime**, non dedotte: `tau_hi = 80.0`, `band_enforced = True`.

| | quarantined | model_claim |
|---|---|---|
| **nella banda** (<80) | **533** | 18 |
| sopra la banda (≥80) | 135 | 7430 |

- **La banda è il caso raro**: 551 su 8.116 giudicati = **6,8%**. La
  distribuzione è bimodale estrema — 7.419 fatti su 8.116 stanno sopra 95.
- **La promessa nel codice regge.** `grounding_gate.py:562` afferma «*true
  entailments … score ≥90 (n=14, min 90.3), so ~0 true facts fall in the
  band*»: nella banda gli ammessi sono **18 su 8.116 = 0,2%**. **Una
  calibrazione su 14 campioni tiene su una popolazione 580 volte più grande.**
  ⚠️ Col proxy dichiarato: `model_claim` significa «ammesso», non «vero».
- **La ricevuta nomina la propria incertezza**: `confidence_tier: "borderline"`
  sulla cella incerta, `"high"` su quella sicura.

## 5. 🔴 Quello che non fa

1. **Il rimedio del caso difficile parte e non consegna** (§5-bis) e non lo dichiara. I **533**
   quarantinati della banda sono rimasti tali **senza il secondo parere che il
   prodotto promette loro**.
2. **`moat: "passed"` su un fatto che esce `quarantined`** (a fermarlo è
   `L4.1`). Chi legge quel campo legge che è passato — gemella esatta di
   `quarantined_by` che nomina il primo layer invece del decisore (⑩).
3. **Il costo non è visibile da nessuna parte**: 20–52 secondi per scrittura
   incerta, a worker singolo.

---

## 5-bis. Dove si perde il verdetto (misurato alle 21:17)

Le funzioni di lookup rispondono, e nessuna di queste righe esegue un LLM — il
comando è **letto** dal sorgente:

```
  shutil.which('claude') : un percorso valido, la CLI e' installata
  _mode()                : auto        _timeout_s() : 90.0
  ollama locale          : False
```

⇒ il percorso preso è `_score_via_claude`: **la CLI esiste e viene invocata**, e i
20–52 secondi sono coerenti con una risposta reale. Il verdetto si perde **dopo**:
o `returncode != 0`, o `_parse_score` non legge la risposta. Le due non si
distinguono senza eseguire il comando come lo esegue il prodotto.

**Il parser, su dieci risposte plausibili:**

| risposta | esito | |
|---|---|---|
| `87` · `Score: 55` · ` 92.5 ` · `Based on… Score: 12` | letti | ✔ |
| `**55**` | `None` | ✗ grassetto markdown |
| `The score is 55.` | `None` | ✗ «score is» non «score:» |
| `I would rate this 55 out of 100.` | `None` | ✗ prosa inglese |
| `Il punteggio e' 55.` | `None` | ✗ prosa italiana |
| `Sorry, I cannot help…` · vuoto | `None` | ✔ giustamente |

⇒ **4 verdetti legittimi persi su 8 risposte che contenevano un punteggio.**
⚠️ Il banco stampa «persi 6» e **sei è il numero sbagliato da citare**: due di quei
`None` sono corretti.

✅ **La strettezza non è sciatteria**: `band_escalation.py:41` la documenta — «*A
digit embedded in prose ("the 100 words…") is NOT a verdict: parsing it once
ADMITTED a fact the judge had scored 5*». È la cura di un incidente vero. Quello
che non era misurato è il suo **costo**: un verdetto **illeggibile** e un giudice
**irraggiungibile** tornano entrambi `None`, e a valle diventano «tenuto per
revisione», che è il nome di una terza cosa ancora.

## 5-ter. ⚠️ Il giudice non è riproducibile

`band_escalation.py:153-157` costruisce il comando con `-p`, `--output-format
text` e `--append-system-prompt`, e **nessun `--model`**. ⇒ il giudice che decide
l'ammissione dipende da come è configurata la CLI **sulla macchina di chi
scrive**, e la ricevuta registra solo `claude-band`: il modello non compare da
nessuna parte. Due utenti con la stessa fonte e lo stesso claim possono ottenere
ammissioni diverse e non poter sapere perché. **Un verdetto non riproducibile è
un verdetto che non si può citare.**

---

## 6. 🧩 Non è un fronte nuovo: è il gemello del backlog

Il dossier del 26/08 registrava **2317 quarantinati, di cui 52 recuperabili e
TUTTI approvati dal giudice** quando qualcuno finalmente glieli faceva vedere.
⇒ **Stesso difetto in due momenti**: il secondo parere che non arriva *alla
scrittura*, e gli stessi fatti che lo superano quando arriva *dopo*.
**Non due fronti: uno.**

---

## 7. Limiti dichiarati

- **Un ambiente.** Che il giudice non sia raggiungibile *qui* non dice perché —
  CLI non trovata, ollama assente, timeout: non isolato, e non è il mio fronte.
- **Un claim e un documento** per la parte sperimentale; il documento è reale
  (`docs/archive/2026-05-13_FORGIA.md`, 212.664 caratteri) e i claim citano
  cifre che ci stanno davvero.
- **I 551 sono una popolazione storica mista**: l'escalation esiste dalla 0.7.0,
  quindi non tutti l'hanno pagata. Il conto del tempo (184–478 minuti) è un
  **limite superiore**, non una misura.
- `model_claim` come proxy di «vero».

Nessuno dei quattro tocca il fatto centrale: **l'A/B con l'interruttore è nella
stessa esecuzione**, e il controllo C riaccende.

---

## 8. I banchi, tutti riproducibili

| banco | cosa misura |
|---|---|
| `banchi/quali-lame-parlano-sul-regime-lungo.py` | 12 celle, 4 regimi da 2k a 212k, quali layer parlano |
| `banchi/il-giudice-e-piu-debole-sulla-fonte-corta.py` | il 55.2 riprodotto 5 volte |
| `banchi/dove-sta-la-soglia-fra-il-giudice-debole-e-quello-forte.py` | la curva 0.2→99.3 e l'ipotesi falsificata |
| `banchi/la-forma-della-curva-a-passo-fine.py` | 15 tagli, la forma |
| `banchi/le-due-soglie-di-percorso.py` | la bisezione: confine fra 2700 e 2800 |
| `banchi/e-la-banda-o-la-lunghezza.py` | il 2×2 che separa le variabili |
| `banchi/l-escalation-parte-e-non-arriva.py` | l'A/B con l'interruttore |
| `banchi/chi-giudica-nei-venti-secondi.py` | le chiavi della ricevuta, stampate non presunte |

Ognuno porta **un controllo che poteva fallire**; nessuno è caduto.
