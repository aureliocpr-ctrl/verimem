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
· ~~**Non ho provato la porta MCP.**~~ **Verificato — vedi l'aggiunta in fondo: confermato.**
· **Non ho letto il codice della document policy**: vedi sopra, le due cause non sono separate.
· **L'istante è parte del dato**: 30/08 ore 22:45.


---

## Aggiunta delle 23:05 — sulla porta MCP il rimedio non è nemmeno esprimibile

La memoria riportava un fatto di @ws5: *«su MCP `external_content` è rifiutato dallo schema»*.
**Confermato, con il riferimento**: `verimem/mcp_server.py:2527-2533`.

```json
"writer_role": {
    "type": "string",
    "enum": ["agent_inference", "user", "system_hook", "trusted_hook"],
    "default": "agent_inference"
}
```

**`external_content` non è fra i quattro valori ammessi.**

⇒ **Il quadro del rimedio è ora completo, e su entrambe le porte non porta a nulla:**

| porta | il valore suggerito dalla ricevuta | esito |
|---|---|---|
| **SDK** (`Memory.add`) | **accettato e registrato** nel database | **l'esito non cambia**: `quarantined` da `store-screen` |
| **MCP** (`hippo_remember`) | **non è nell'`enum`** | **non è nemmeno esprimibile** |

🔑 **La ricevuta consiglia un'azione che dalla porta dell'agente non si può compiere, e dalla porta
del programmatore non serve.** Ed è la porta MCP quella che legge quella ricevuta: **è l'agente a
riceverla**, ed è proprio lui a non poterla applicare.

📌 Questo **rafforza la correzione** fatta sopra al doc 34: la porta di scrittura resta la più
esplicita del prodotto, **ma la sua unica informazione rivolta al futuro — il rimedio — non regge su
nessuna delle due superfici.** Le altre quattro, che raccontano il passato, sono esatte su entrambe.

⚠️ **Resta non separato** (vedi sopra) se sull'SDK il valore instradi davvero alla document policy
con esito identico, oppure non instradi affatto: **non ho letto quel codice**, e la differenza
cambia la cura, non il fatto che il consiglio non sia azionabile.


---

## Aggiunta delle 23:50 — le due cause sono separate: il rimedio non viene MAI letto

Sopra restava aperto se `external_content` **instradasse davvero** alla document policy (con esito
identico) oppure **non instradasse affatto**. Letto il codice: **`verimem/admission_gate.py`,
righe 253-260**.

```python
_inj = detect_injection(prop)
_inj_topic = detect_injection(topic)
if _inj.is_injection or _inj_topic.is_injection:
    return AdmissionVerdict(FLAG_INJECTION, "prompt-injection signals: …", False)
```

**Il controllo sull'injection è il PRIMO del gate e ritorna immediatamente.** `writer_role` compare
una sola volta, alla **riga 276** — cioè **sedici righe dopo**, in un punto che **non viene mai
raggiunto** quando l'injection scatta:

```python
ungrounded = (status == "model_claim") and (not se) and (writer_role in (None, "agent_inference"))
```

⇒ **Non è «instrada e la document policy fa lo stesso»: è che il valore non viene mai letto su quel
ramo.** Il rimedio **non può funzionare, per costruzione.**

## 🟢 E il posizionamento è GIUSTO — il che sposta la cura

Il commento sopra quelle righe spiega perché il controllo sta lì, e la ragione è solida:

> *«is screened here, not only in `SemanticMemory.store` (red-team 2026-07-21: every OTHER caller of
> this function — `requalify_quarantined`, `cleanup_telemetry`, `audit_corpus` — was blind to a
> poisoned topic). The scan runs BEFORE the telemetry-prefix branch on purpose: **a declared prefix
> must never out-rank an injection payload sitting in the topic**.»*

**Uscire per primi è una scelta deliberata e difendibile**: nessun campo dichiarato dal chiamante —
né un prefisso, né `writer_role` — deve poter scavalcare un sospetto di injection. **Questa parte
del prodotto è progettata bene.**

⇒ 🔑 **Quindi la cura NON è spostare il controllo né far leggere `writer_role` prima: sarebbe
indebolire un presidio per accontentare un messaggio.** La cura è **il messaggio**: la ricevuta
consiglia un'azione che, su questo ramo, il codice non guarda. **È una riga di testo, non una riga
di logica** — e finché resta com'è, chi la segue perde tempo su un'istruzione che non può avere
effetto.

📌 **Questo chiude anche la formulazione**: non «la ricevuta mente», ma **«la ricevuta dà un
consiglio giusto per un altro ramo del gate, stampato su un ramo che non lo usa»**.
