# 34 — Lo stesso fatto, con una lettera greca, viene quarantinato

**ws6 · 30/08 ore 22:10** · store **temporaneo** (`HIPPO_DATA_DIR` in tempdir), scritture vere,
fuori da pytest.

Il [documento 33](33-il-presidio-anti-injection-nasconde-la-roadmap.md) trova che il rilevatore
anti-homograph nasconde un chunk della ROADMAP perché `τ_hi` è **greco attaccato a latino**.
`detect_injection` però compare anche in `admission_gate.py:253-254`, **sul percorso di scrittura
dei fatti** — e lì guarda **la proposition e il topic**. Quindi la domanda pratica: **succede anche
a noi quando scriviamo?**

---

## L'A/B, una lettera di differenza

Due fatti **identici**, stessa fonte, stesso topic:

```
   caso    | status       | quarantined_by | grounding
   ASCII   | model_claim  | —              | 99,978      "…la soglia t_hi vale 80 e la soglia t_lo vale 40."
   GRECO   | quarantined  | store-screen   | 99,976      "…la soglia τ_hi vale 80 e la soglia τ_lo vale 40."
```

⇒ **Uno entra, l'altro è trattenuto.** Il giudice li approva **entrambi** a 99,97: a fermare il
secondo è **`store-screen`**, non il moat.

⇒ **Sì: succede anche a noi.** Un fatto che descrive una soglia con la notazione standard
(`τ_hi`, «tau high») **non viene servito**.

## 🟢 Ma qui il prodotto è ONESTO, e va detto con la stessa forza

La ricevuta del caso greco:

```
prompt-injection signals prop=['obfuscation'] topic=[] in fact id=… -> quarantined
(attribution=agent_claim — reads as the agent's own assertion; if this text was ingested from a
document or user, set writer_role='external_content' to route it to the document policy)
```

e nel record: **`withheld_despite_judge=True`**.

**Dichiara cinque cose:** ① il **segnale** (`obfuscation`) · ② **su quale campo** (`prop`, e che il
topic è pulito) · ③ **l'attribuzione** (`agent_claim`) · ④ **il rimedio esatto**
(`writer_role='external_content'`) · ⑤ e un campo che dice **«trattenuto nonostante il giudice»**.

⇒ **Non è un blocco muto: è un verdetto motivato con l'istruzione per ribaltarlo.**

---

## 🔑 Il reperto di sintesi: l'onestà del prodotto NON è uniforme fra le porte

Mettendo in fila tutto ciò che ho misurato oggi:

| porta | quando non può rispondere bene… |
|---|---|
| **scrittura** (`add`/gate) | **dichiara tutto**: layer, segnale, campo, attribuzione, rimedio, `withheld_despite_judge` |
| **documenti** (`document_semantic_search`) | **dichiara in parte**: `query_terms_matched`, `rerank_score`, «results are PARTIAL» — **ma serve 5 risultati anche quando tutti i punteggi sono negativi** ([doc 32](32-il-rerank-sa-quando-non-ha-trovato-e-la-porta-serve-lo-stesso.md)) |
| **ricerca fatti** (`facts_search`) | **tace**: ripiega dall'AND all'OR senza dirlo, ordina per data senza dirlo, ignora `limit` senza dirlo ([doc 17](17-la-ricerca-ordina-per-data-non-per-pertinenza.md), [21](21-le-due-porte-gemelle-non-si-somigliano.md)) |

🔑 **Il prodotto sa essere onesto — lo dimostra la porta di scrittura, che è la più severa e la più
esplicita.** Il problema non è una cultura mancante: è **una disuguaglianza fra porte**, e le due
che tacciono sono **quelle da cui si legge**.

⇒ **La cura per `facts_search` non va inventata due volte**: il modello sta in `admission_gate`
(motivare) e in `document_semantic_search` (dichiarare il parziale). Sono già in casa entrambi.

## Limiti

· **Due scritture**, non una popolazione: l'A/B è a variabile singola e il contrasto è netto,
  **ma è un contrasto**.
· **Non ho misurato quanti nostri fatti reali contengano mixed-script**: nel corpus di Aurelio non
  l'ho cercato (qui ho usato uno store temporaneo).
· **Non dico che il criterio vada rilassato**: contro gli homograph è la difesa giusta, e la ricevuta
  offre già la via d'uscita documentata (`writer_role='external_content'`). **Non l'ho provata.**
· **L'istante è parte del dato**: 30/08 ore 22:10.
