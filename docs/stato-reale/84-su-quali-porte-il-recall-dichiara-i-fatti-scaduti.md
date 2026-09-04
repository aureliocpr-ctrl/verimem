# Su quali porte il recall dichiara i fatti scaduti — e su quali no

**04/09/2026 · banchi `ws6-quante-porte-dicono-cosa-hanno-tolto.py` e
`ws6-la-porta-mcp-dice-cosa-ha-tolto.py`**

Un fatto con `valid_until` nel passato spariva già dai risultati — lo toglie la
maschera vettoriale — ma **nessuna porta lo diceva**, e una risposta più corta
si legge come «non c'era altro». Questa pagina dice esattamente dove la
situazione è cambiata e dove no, perché una riga che promettesse la capacità
senza nominare le porte sarebbe falsa su metà di esse.

## Il quadro, misurato eseguendo

```
porta                    toglie   dichiara
SDK  Memory.recall         SI        SI
CLI  recall                SI        SI
CLI  ask (FIND)            SI        no     <- criterio non affidabile
MCP  hippo_facts_recall    SI        no     <- non espone il campo
MCP  hippo_facts_search    NO        —      <- serve gli scaduti: nulla da dire
```

⇒ **Due porte su quattro fra quelle che tolgono.** Nessuna porta MCP dichiara.

E `verimem remember --valid-until` permette ora di **scrivere** una scadenza
dalla riga di comando: prima si poteva solo dall'SDK, ed è il motivo per cui il
campo era popolato su **0 fatti su 17098** nel corpus di casa. Una capacità
cablata a cui nessuno può dare materiale non emette segnale e si legge come
assente.

## Le due ragioni del «no» sono diverse, e non vanno confuse

**`hippo_facts_recall` non espone il campo.** Toglie il fatto scaduto e non lo
dichiara. È la stessa forma curata su `recall` e su `ask`, una porta più in là.

**`ask` espone il campo ma il criterio tace.** Il criterio decide se uno scaduto
«sarebbe stato servito» confrontando la sua somiglianza col peggiore dei
risultati serviti, ed è **anticorrelato**: misurato su tre domande allo stesso
store,

```
in tema (deve avvisare)   servito 0,8969   scaduto 0,8159   -> tace
fuori tema (non deve)     servito 0,7552   scaduto 0,7600   -> parlerebbe
```

La ragione è scritta in `semantic.py` da prima di questo lavoro: gli embedding
sono anisotropi, *«every fact sits ~0.80 cos from any query»*, quindi a quei
valori un confronto fra punteggi vicini è rumore. Tre criteri sono caduti —
«quanti scaduti ci sono» (parlava a ogni lettura), «quanti entrerebbero nei
primi k» (cieco sugli store piccoli), e questo. La grandezza vera è «il fatto
sarebbe comparso se non fosse scaduto» e si ottiene solo rifacendo il ranking
senza la maschera: è una decisione sul comportamento del prodotto, non una
scelta da prendere di straforo.

**In tutti i casi l'errore è per DIFETTO**: la porta tace quando dovrebbe
parlare, non parla a sproposito. E il caso peggiore — la scadenza che porta via
**tutti** i risultati — resta coperto su SDK e CLI `recall`, dove l'avviso esce
anche quando la risposta è vuota.

## 🪞 Una riga di questa tabella era falsa fino a un'ora fa

Avevo scritto, e mandato come testo da incollare nel CHANGELOG, che **MCP
`hippo_facts_search` dichiara i fatti scaduti**. Non è vero. Quel payload
contiene il campo di ogni fatto:

```json
"valid_until": 1788458907.2275467
```

e il banco aveva `valid_until` nella lista delle parole con cui una porta
«dichiara»: **contava un dato come se fosse un avviso**. Il banco esisteva
proprio per non contare identificatori — nel suo docstring c'è scritto che
un'assenza si prova eseguendo — ed è caduto nella versione peggiore, contarne
uno *dentro i dati*.

Il dato per non sbagliare stava nella colonna accanto dello stesso banco:
quella porta **serve** il fatto scaduto. Se non toglie, non ha nulla da
dichiarare, e metterla nella stessa colonna dell'altra confondeva due
comportamenti opposti. Ora `dichiara` si calcola solo per le porte che tolgono.

## Cosa resta non verificato

⚠️ **Il thin client.** Con `VERIMEM_SERVER_URL` configurato, `Memory` parla con
un server remoto. Non ho misurato se l'avviso sopravviva a quel percorso, e non
scrivo che sopravvive. (Nel server MCP esiste una strada che ritorna prima dei
blocchi locali; non tocca questo lavoro, perché `mcp_server.py` non è stato
modificato — zero occorrenze del campo — ma la domanda sul thin client resta.)
⚠️ **Il criterio**, come sopra: non è tarato, è dichiarato.
