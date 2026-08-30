# C3 — parità fra le porte: la scacchiera

*ws5, 30/08. Claim `f7eca18c246f`. Chiude il pezzo ② assegnato da `lead-audit`.*

C3 del contratto di uscita chiede se **le porte del prodotto si comportano allo
stesso modo**. Un utente ne incontra una sola, e non sa che ce ne sono altre: se
divergono, la sua esperienza dipende da quale ha in mano.

**Le quattro porte, in ordine di distanza dall'utente:**

| porta | chi la usa | come si chiama |
|---|---|---|
| `run_validation_gate` | nessuno direttamente — è la funzione interna | `anti_confab_gate.py` |
| CLI | chi usa `verimem save` | `cli.py:1867` |
| SDK | chi importa la libreria | `Client.add` / `Memory.add` |
| MCP | **un agente — è la porta headline** | `verimem mcp`, in-process o stdio |

> `pyproject.toml` chiama MCP «*the HEADLINE use (`verimem mcp` for Claude Code /
> Cursor)*». È la porta da cui passa il caso d'uso principale del prodotto.

---

## La scacchiera

Ogni cella è misurata, e sotto c'è il banco che la produce. **Vuoto = mai
misurato**, e resta dichiarato tale.

| operazione | gate | SDK | MCP in-proc | MCP stdio |
|---|---|---|---|---|
| claim VERO con source | ✅ persist | ✅ | ✅ | 🔴 **nessuna risposta entro 190s** |
| claim FALSO con source | ✅ quarantine | ✅ | ✅ | 🔴 idem |
| scrittura **senza** source | ✅ | ✅ | ✅ 3.7s | ✅ 3.8s, **esito identico** |
| `writer_role='user'` | ✅ | ✅ | ✅ | ✅ **identico** |
| `writer_role='external_content'` | ✅ accettato | ✅ accettato | 🔴 **RIFIUTATO** | 🔴 **RIFIUTATO** |
| solo l'advice della ricevuta | 0/4 salvi | **4/4 salvi** | 🔴 rifiutato | 🔴 rifiutato |
| supersessione (2ª scrittura) | — | ✅ `sup=True` | 🔴 `sup=False` | 🔴 `sup=False` |
| lettura `search` / `recall` | — | ✅ trova | 🔴 `[]` **in silenzio** | 🔴 `[]`, identico |
| lettura `facts_search` | — | — | ✅ trova | ✅ **identico** |

**Banchi**: `ws5-C3-le-stesse-operazioni-sulle-due-porte.py` (`37bc7a9a`) ·
`ws5-C3-la-lettura-quattro-vie-una-domanda.py` (`c90143cb`) ·
`ws5-la-cura-e-raggiungibile-dalle-porte-vere.py` (`2ed804bd`) ·
`ws5-mcp-su-stdio-batte-l-in-process.py` (`95772fc3`) ·
`ws5-C3-la-colonna-stdio-della-scacchiera.py` (`1c836a1c`).

---

## Le quattro divergenze reali, e cosa costano a chi usa il prodotto

**① Lo stesso consiglio dà tre esiti su tre porte.** La ricevuta suggerisce
`writer_role='external_content'`. Chi lo segue **alla lettera** ottiene:

```
  sull'SDK          i suoi quattro claim veri SALVI   (4/4)
  sulla porta gate  esattamente niente                (0/4)
  su MCP            un errore                         (rifiutato)
```

La differenza **non è nel suo comportamento: è nella porta**. Sull'SDK funziona
perché il `Client` aggiunge `provenance_trusted` per conto suo (`client.py:539`)
— la metà che l'advice non nomina. Le altre due porte non la mettono.

**② `recall` ha due significati opposti.** Sull'SDK `recall` **è** `search`
(`client.py:3125`, lo stesso oggetto); su MCP cerca gli **episodi** e risponde
`[]` **senza dire niente**. ⇒ Un agente che chiama `hippo_recall` per cercare un
fatto riceve una lista vuota e conclude «*la memoria non lo sa*», mentre il fatto
c'è ed è raggiungibile con un altro tool.

**③ MCP non supersede.** La seconda scrittura sullo stesso topic aggiorna
sull'SDK e non su MCP — riproduzione indipendente di `W2-2`, e confermata da una
terza direzione sulla colonna stdio.

**④ Su stdio, una scrittura *con* source non risponde entro 190 secondi**
mentre la stessa in-process costa 28,9s. ⚠️ **Confondente non tolto**: le prove
girano su store temporaneo, dove il daemon di encoding non esiste. Non è
verificato sullo store principale — sarebbe una scrittura lì dentro.

---

## 🔑 Ciò che la scacchiera dice, e che nessun banco singolo diceva

**Le due porte MCP sono identiche su 8 operazioni su 8** — protocollo,
validazione dello schema, supersessione, tre vie di lettura. ⇒ **La disparità
non è nel trasporto né nella validazione: è interamente nel percorso del
grounding.**

⇒ Due conseguenze:
1. **Il limite «in-process non è un client vero», che avevo dichiarato in tre
   banchi, è chiuso**: su tutto ciò che non passa dal giudice, in-process *è* la
   porta vera, e quei referti reggono.
2. **`external_content` rifiutato non era un artefatto**: lo rifiuta anche un
   client con processo separato e framing JSON-RPC.

---

## Regime, popolazione e limiti

**Regime**: build corrente · store **temporaneo** (`HIPPO_DATA_DIR`), mai quello
di Aurelio · server stdio come processo figlio, chiuso dal context manager.

**Popolazione, dichiarata riga per riga**: **un caso per operazione**. Non è un
corpus: è una scacchiera di comportamenti, e serve a dire *se* due porte
divergono, non *quanto spesso*.

**Limiti, in ordine di quanto possono ribaltare il quadro:**
1. Il client stdio è quello **ufficiale del pacchetto `mcp`**, non Claude Code o
   Cursor: un client con validazione propria potrebbe comportarsi altrimenti.
2. Le letture girano su uno store con **zero episodi**, quindi un `[]` va letto
   come «cerca altro» — il confronto è **fra le porte**, non contro un atteso.
3. La riga «con source» su stdio ha il **confondente del daemon** (sopra).
4. Confronto sullo **stato finale**, non su tutti i campi — e i campi **hanno
   nomi diversi fra le porte** (`warnings` su SDK, `anti_confab_warnings` su
   MCP): senza normalizzarli si conterebbero differenze che non ci sono.

## Cosa servirebbe per chiudere C3 come verde

| divergenza | cosa manca |
|---|---|
| l'advice dà tre esiti | che la ricevuta nomini **entrambi** i campi, o che le porte aggiungano la metà mancante come fa il `Client` |
| `recall` con due significati | che la porta MCP **dica** che sta cercando episodi, invece di rispondere `[]` in silenzio |
| MCP non supersede | è `validate='full'` che non arriva — cura nota, non mia |
| stdio non risponde con source | **causa ignota**: due ipotesi falsificate a variabile singola, e il confondente del daemon ancora da togliere |
