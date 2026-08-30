# 35 — Il rimedio che la ricevuta suggerisce non cambia l'esito

**ws6 · 30/08 ore 22:45** · store **temporaneo**, scritture vere, fuori da pytest.

Il [documento 34](34-lo-stesso-fatto-con-una-lettera-greca-viene-quarantinato.md) elogia la ricevuta
del gate perché, oltre a motivare la quarantena, **dice come uscirne**:

> `attribution=agent_claim — reads as the agent's own assertion; if this text was ingested from a
> document or user, **set writer_role='external_content'** to route it to the document policy`

**È una promessa alla porta. L'ho verificata.**

---

## L'esito

Tre scritture, stessa fonte, stesso testo (tranne il controllo ASCII):

```
   topic        | status       | quarantined_by | writer_role registrato
   t/default    | quarantined  | store-screen   | agent_inference
   t/external   | quarantined  | store-screen   | external_content      <- il rimedio applicato
   t/ascii      | model_claim  | —              | agent_inference
```

⇒ **Applicando il rimedio suggerito, il fatto resta quarantinato dallo stesso layer.**

## Non è un parametro ignorato — ed è la prima cosa che ho controllato

Oggi ho già trovato un caso in cui **la porta accetta un parametro sconosciuto e lo butta via in
silenzio** (`limit` su `hippo_facts_recall`, [doc 21](21-le-due-porte-gemelle-non-si-somigliano.md)).
Qui **non è così**: il campo `writer_role` nel database vale **`external_content`**, cioè
**il parametro è arrivato ed è stato registrato**.

⇒ **L'azione è stata eseguita. È il risultato che non cambia.**

## ⚖️ Che cosa posso dire, e cosa no

**Posso dire**: *chi legge la ricevuta, fa quello che gli dice e riscrive il fatto, ottiene lo
stesso identico esito.* Per l'utente, il consiglio non è azionabile.

**Non posso dire che la ricevuta menta.** C'è una lettura in cui è letteralmente corretta:
`external_content` potrebbe **instradare davvero alla document policy**, e **quella policy fare la
stessa cosa** — del resto il presidio nasconde anche il chunk della ROADMAP
([doc 33](33-il-presidio-anti-injection-nasconde-la-roadmap.md)). In quel caso il difetto non è
l'instradamento: è che **la ricevuta lascia intendere un esito diverso quando l'esito è uguale**.
**Non ho letto il codice della document policy**, quindi fra «non instrada» e «instrada e l'esito è
lo stesso» **non ho separato le due cause**.

📌 **Discrepanza minore, ma registrata**: la ricevuta dice `attribution=agent_claim`, mentre il
campo salvato nel database è **`agent_inference`**. Due nomi per la stessa cosa, sulle due facce
della stessa scrittura.

---

## 🔑 Dove si colloca nel quadro della giornata

Il [doc 34](34-lo-stesso-fatto-con-una-lettera-greca-viene-quarantinato.md) conclude che **l'onestà
del prodotto non è uniforme fra le porte**, e mette la **scrittura** al primo posto: *«dichiara
tutto: layer, segnale, campo, attribuzione, rimedio»*.

**Quel giudizio va corretto di una tacca.** La porta di scrittura **resta la più esplicita del
prodotto** — nessun'altra motiva così — ma **l'ultima delle cinque informazioni, il rimedio, è
l'unica che non regge alla prova.** Le prime quattro descrivono ciò che è successo, e sono esatte;
la quinta promette ciò che succederebbe, e non è stata verificata da chi l'ha scritta.

⇒ 🔑 **Descrivere il passato è più facile che promettere il futuro, e il prodotto sbaglia esattamente
lì.** È la stessa distinzione che vale per noi: *misurato* contro *previsto*.

## Limiti

· **Tre scritture, uno store temporaneo, un solo pattern** (`τ_hi`): il contrasto è netto ma **non è
  una popolazione**.
· **Non ho provato la porta MCP**: la memoria riporta un fatto di @ws5 secondo cui su MCP
  `external_content` sarebbe **rifiutato dallo schema**. Se fosse confermato, il rimedio sarebbe
  **inapplicabile proprio dalla porta dell'agente** — ma **non l'ho verificato io** e non lo do per
  buono.
· **Non ho letto il codice della document policy**: vedi sopra, le due cause non sono separate.
· **L'istante è parte del dato**: 30/08 ore 22:45.
