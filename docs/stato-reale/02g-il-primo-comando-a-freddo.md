# ② sexies — Il primo comando su un'installazione fredda: la cura è una riga

> **ws2 «Vega» · 08/08 ore 14:38–14:47 · repo SHA `6d1080cf`, `git status` pulito ·
> pacchetto `verimem 0.7.0` da PyPI · HOME nuova, cache modelli vuota, nessuno store**
> Punto (a) del ruolo assegnato: *«il prodotto deve DIRE all'utente che la verifica è spenta al
> primo comando che scrive, non solo nel doctor»*. **Il prodotto lo dice già. La CLI non lo stampa.**

---

## 1. Cosa succede davvero al primo comando

HOME appena creata, `HF_HOME` vuoto — l'utente che ha appena finito `pip install`:

```
$ verimem remember "Il modulo alfa ha 12 test." --source "Rapporto: modulo alfa, 12 test, tutti verdi."
[…warning su symlink Windows, HF token mancante, FutureWarning su get_sentence_embedding_dimension…]
admitted id=f0517209c950 topic=user
```

**156 secondi** (14:38:26 → 14:41:02), quasi tutti spesi a scaricare l'embedder
`intfloat/multilingual-e5-base`. E poi il DB dice:

```
proposition      = Il modulo alfa ha 12 test.
status           = model_claim
grounding_score  = None        ← MAI GIUDICATO
confidence       = 0.5
verified_by      = []
```

⇒ **L'utente ha passato una fonte, il prodotto ha risposto `admitted`, e l'entailment non è stato
verificato.** Il giudice del moat non è installato: è l'embedder a essere stato scaricato, non lui.

## 2. 🔑 Ma il prodotto lo sa, e lo dice in tre punti — nessuno arriva alla CLI

Stessa scrittura, guardando **tutti** i campi che l'SDK restituisce:

```json
"adjudication": {
    "disposition": "admitted",
    "evidence_class": "ungated",          ← non passato da nessun cancello
    "judge": null, "score": null, "threshold": null,
    "confidence_tier": "unverified"       ← lo dice in una parola
},
"warnings": [{
    "layer":  "L4-skipped",
    "reason": "source provided but no grounding judge is available - entailment NOT verified",
    "advice": "the local grounding model is not installed and no llm was passed.
               Run `verimem warmup` to fetch the free multilingual CE judge,
               or pass Memory(llm=...) — either turns the source into a verified fact"
}]
```

**L'avviso è già scritto, è esatto, e contiene il rimedio.** `evidence_class: "ungated"`,
`confidence_tier: "unverified"`, e un `warnings[0]` che spiega cosa manca e come rimediare.

**La CLI stampa `admitted id=… topic=user`.** Nient'altro. ([`cli.py:871-875`](../../verimem/cli.py))

## 3. La popolazione opposta: stampare i warnings costa rumore? **No, zero su 8**

Stessa domanda dal lato opposto — con il giudice installato e scritture sane, quanti warnings escono?

| fatto | grounding | tier | warnings |
|---|---|---|---|
| Il modulo alfa ha 12 test. | 95,7 | high | **0** |
| Il server gamma risponde in 45 ms. | 98,1 | high | **0** |
| La release 2.1 è del 3 marzo. | 99,1 | high | **0** |
| Il team conta 7 persone. | 96,5 | high | **0** |
| Il contratto scade nel 2027. | 97,1 | high | **0** |
| Module alpha has 12 tests. | 97,0 | high | **0** |
| O time tem 7 pessoas. | 82,1 | high | **0** |
| Der Vertrag läuft 2027 aus. | 93,6 | high | **0** |

**8 scritture sane su 4 lingue: 0 warnings, tier `high` in tutte.** Il campo è vuoto esattamente
quando non c'è niente da dire ⇒ **stamparlo non produce rumore sul caso normale.**

## 4. La cura, e cosa chiude

**Una riga in `remember_cmd`: stampare `warnings` e `adjudication.confidence_tier`.**
Non serve costruire niente — l'informazione è già nella risposta di `m.add()`.

Chiude **tre** cose che avevamo trattato come difetti separati:

| difetto | dove | come lo chiude |
|---|---|---|
| l'utente non sa che la verifica è spenta | punto (a) del ruolo | stampa `L4-skipped` con il rimedio |
| `admitted` copre il verificato e il mai-giudicato | [02c §4](02c-il-numero-mostrato-e-chi-decide.md) | `confidence_tier`: `high` contro `unverified` |
| la ragione del rifiuto non arriva | [02c §4](02c-il-numero-mostrato-e-chi-decide.md) | stampa `warnings[0].reason` e `.advice` |

📌 **ws3, è materia tua** (solo tu scrivi): io non tocco il codice. Il banco per la falsificazione
alla cieca è quello sopra — HOME nuova + `HF_HOME` vuoto per il caso freddo, store isolato con
giudice installato per la popolazione opposta.

⚠️ E **la cura da sola non basta per chi installa oggi**: `remember_cmd` è nel pacchetto del 22/07
([02e](02e-chi-installa-riceve-il-22-luglio.md)), quindi la riga andrà pubblicata per arrivare
all'utente.

---

**Caveat**: un'installazione, un OS, un fatto per condizione nel caso freddo (8 nella popolazione
opposta). I 156 s sono una misura sola e includono il download dell'embedder su questa rete. Non ho
verificato se `warmup` a freddo risolva davvero — è il passo successivo, dichiarato non fatto.
