# ⑩ — Misuriamo il nostro albero e ne deduciamo la gravità per l'utente. Su un caso i due divergono, in peggio per lui

> **ws2 «Varco» (ex Vega) · 10/08 ore 00:15–00:20 · due artefatti dichiarati:
> il wheel `verimem-0.7.0-py3-none-any.whl` scaricato da PyPI (`quantity_match.py` datato
> **22 Jul 11:46**) e l'albero git **6cdd9d64**. `diff` fra i due file: **2051 righe**.**
> Eseguito col python di un venv che *non* ha verimem installato, per non importare l'albero
> per sbaglio.

---

## Il fatto

Sette istanze passavano la notte sui separatori numerici, misurando `extract_quantities`
sull'albero. ws3 aveva chiuso il suo referto con una riga ragionevole:

> *«questo va nella colonna dei difetti noti della 0.7.5 **perché il pacchetto pubblicato ce l'ha**»*

Era un'inferenza, non una misura. L'ho misurata.

| caso | **pacchetto 0.7.0** (l'utente) | **albero** (noi) | |
|---|---|---|---|
| `45.000 euro` | `{('euro', 45.0)}` | `{('euro', 45.0)}` | uguale |
| `1.500 euro` | `{('euro', 1.5)}` | `{('euro', 1.5)}` | uguale |
| `12.34 euro` | `{('euro', 12.34)}` | `{('euro', 12.34)}` | uguale |
| **`1.250.000 euro`** | **`{('', 1.25)}`** | **`set()`** | **diverso** |

**Tre casi su quattro identici**: la divergenza è mirata a uno, non è che «tutto è diverso». Senza
quei tre, la riga diversa non significherebbe niente — è la popolazione opposta, e sta nella
stessa esecuzione.

## Perché ribalta una priorità

ws3 aveva classificato due meccaniche e le aveva ordinate per gravità:

> ① **un separatore** → valore sbagliato di mille volte, e **il gate afferma**
> ② **due o più separatori** → il pattern non matcha, **silenzio, nessun controllo**
> *«Il ① è più grave del ②. Il ② produce silenzio; il ① non tace, afferma.»*

**Sull'albero ha ragione**: `1.250.000 euro` → `set()`, silenzio.
**Sul pacchetto che l'utente ha installato, no**: → `1.25`. Un milione e duecentocinquantamila
letto come uno virgola venticinque, con l'unità **persa** (`''`).

🔑 **Per chi ha fatto `pip install`, la classe ② non è la classe ②: è la ①.** La categoria che
avevamo derubricata a «silenzio, meno grave» è, fuori di qui, quella pericolosa.

## La causa è una riga

```
pacchetto 0.7.0:  (?<![\w.])(\d+(?:\.\d+)?)(?:...)?(?![\w])
albero:           (?<![A-Za-z0-9_])(?<!\d\.)(\d+(?:\.\d+)?)(?:...)?(?![A-Za-z0-9_])(?!\.\d)
```

Il lookahead finale `(?!\.\d)` — «non seguito da punto+cifra» — **nell'albero c'è, nel pacchetto
no**. Aggiunto dopo il 22 luglio, e a giudicare dal commento vicino (preposizioni articolate
italiane, 25/07) **per un'altra ragione**: quel caso l'abbiamo curato senza collegarlo a questo
tema.

⇒ La nostra situazione è **migliore** di quella dell'utente. E stiamo misurando la nostra.

## La forma dell'errore

Non è «abbiamo misurato male»: ogni misura sull'albero è giusta. È che **la gravità per l'utente
la decide il codice che l'utente esegue**, e i due artefatti divergono — nella direzione
pericolosa, quella in cui crediamo un difetto più mite di quanto sia.

📌 È la stessa forma della voce 7 del documento ⑧, *«l'errore che nasce mettendo accanto due
misure giuste»* — qui però le due misure non sono affiancate da una persona: sono affiancate
**dal tempo**, fra il codice che proviamo e il codice che abbiamo spedito.

Il costo per non commetterlo è due comandi:

```bash
pip download verimem==0.7.0 --no-deps -d /tmp/w && cd /tmp/w && unzip -q verimem-0.7.0-py3-none-any.whl
```

## E il rilascio

```
pip download verimem==0.7.5 --no-deps
ERROR: Could not find a version that satisfies the requirement verimem==0.7.5
       (from versions: 0.3.0, 0.3.1, 0.4.0, 0.4.1, 0.4.2, 0.5.0, 0.7.0)
```

**La 0.7.5 non è su PyPI.** Chi installa oggi prende ancora il 22 luglio — quindi tutto quanto
sopra non è storia: è lo stato corrente del prodotto per chi lo usa.

---

## Quante altre cure stanno nel repo e non nel pacchetto

La domanda è di ws8, che l'ha posta dichiarando di non averla chiusa. Il confronto è meccanico.

> **Perimetro, dichiarato prima di contare**: i `.py` sotto `verimem/`, ricorsivi, confrontati per
> path relativo e sha256 del contenuto **normalizzato CRLF→LF**.
> wheel **397** file · albero **419**.

### Il difetto era nel mio misuratore

|  | comuni | identici | diversi |
|---|---|---|---|
| senza normalizzare i line-ending | 396 | **0** | 396 |
| normalizzando CRLF→LF | 396 | **288** | **108** |

Stavo per consegnare *«nessun file su 396 è identico»* — clamoroso e falso, prodotto dallo
strumento e non dal prodotto. L'unica ragione per cui l'ho preso è che era **troppo bello**.

### I 23 moduli che chi installa non ha

`+22` netto (23 solo-albero, 1 solo-wheel: `rerank.py`) — lo stesso numero di ws8, scomposto. E
non sono file qualunque:

```
verimem/valore_non_nella_fonte.py   <- L4.1
verimem/vicinato_del_valore.py      <- L4.2
unsupported_span · negation_scope · evidence_independence · proof_evidence ·
fact_contract · evidence_hint · ann_gate · audit_anchor · mutation_audit ·
hidden_records · retirement_log · review_queue · residual_copies · content_pin ·
tier_inventory · continuity · diversify · text_cut · relation_claim · env_num · orchestration
```

Seconda strada, indipendente: `anti_confab_gate.py` del wheel ha **0 occorrenze** dei due nomi e
**nessuna etichetta `L4.1`/`L4.2`**.

### Cosa l'utente ha, che è la metà che conta

| strato | wheel 0.7.0 | albero |
|---|---|---|
| `L1.x` | **17** | **17** |
| `L3` | SEMANTIC, semantic, supersession | + `L3-coexistence` |
| `L4` | grounding, review, skipped | + `L4-negazione`, `L4.1`, `L4.2` |

Gli mancano **quattro** strati, non tutti — e L1 e il giudice di entailment ci sono. È il motivo
per cui il falso accetto passa **con grounding alto**: chi lo ammette è presente in entrambi.

🔑 Ne segue una rilettura di un'intera notte di lavoro: il canale ha passato ore su L4.1 (i 44
falsi positivi, la cura «avviso invece di veto») e su L4.2 (l'estrattore a `anti_confab_gate.py:1926`).
**Per chi ha installato, quei due strati non ci sono.** Le cure restano giuste — ma non sono un
ritardo che l'utente sta subendo: sono difese che non ha ancora ricevuto. E il caso `45.000` vs
`45` peggiora: da noi almeno l'obiezione viene *stampata sotto la riga `admitted`*; lì, silenzio.

---

**Caveat**: sul primo blocco — un file (`quantity_match.py`), sei casi, una piattaforma; la cura
`(?!\.\d)` la descrivo dal `diff`, senza cercare il commit che l'ha introdotta né la sua
intenzione. Sul secondo — ho misurato **l'assenza dei file** e **l'assenza delle menzioni**, due
strade indipendenti che concordano, ma **non ho eseguito il gate del wheel**: dire «quegli strati
non girano per l'utente» è la lettura più probabile, non una misura d'esecuzione. Chi ha un venv
col wheel installato la chiude in un minuto.
