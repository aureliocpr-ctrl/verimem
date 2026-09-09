# Mappa — `verimem/gateway.py`

*ws3 Galileo. 1.798 righe, **87 fra funzioni, classi e metodi** (il conteggio è
quello del righello del lead, `scripts/mappa_completa.py`, che include i metodi
qualificati e le dunder). Il gateway è la **porta HTTP**: quello che promette
sta scritto per esteso nell'intestazione del modulo, ed è la parte del prodotto
dove una promessa sbagliata non è un difetto di comodità ma di sicurezza.*

**Metodo.** I claim dell'intestazione si provano **attaccandoli**, non
rileggendoli: il tenant sbagliato viene dichiarato nel corpo della richiesta, la
chiave viene cercata **in chiaro dentro i byte del database**, i nomi di tenant
pericolosi vengono creati davvero. Ogni controllo negativo ha accanto il suo
**controllo positivo**: un rifiuto che rifiuta tutto non prova niente.
Banco: `ws3-mappa-prova-gateway-auth-e-tenant.py` (09/09 12:15), avviato con
`fastapi.testclient.TestClient` — nessuna porta aperta sulla macchina.

## Autenticazione, tenant, chiavi (gateway.py 62-360, 792-960)

| # | funzione (file:riga) | cosa promette | verdetto | prova (comando e esito) |
|---|---|---|---|---|
| 1 | `verimem/gateway.py:792` `create_app` | «costruisce l'app FastAPI del gateway; `keys` iniettabile (test)… `admin_key` (None = default): SENZA, gli endpoint `/admin/*` **non esistono** — un gateway senza control plane è byte-identico a prima» | **FUNZIONA COME PROMESSO** | `create_app(data_dir=tmp, keys=keys)` costruisce l'app e serve; con `TestClient` tutti gli endpoint `/v1/*` rispondono. Il ramo `admin_key` è **NON MISURATO** (prossimo blocco) |
| 2 | `verimem/gateway.py:925` `create_app._tenant` | il cuore del claim: «il tenant deriva **SOLO** dalla chiave presentata, mai da un campo della richiesta — niente path traversal, niente confused deputy» | **FUNZIONA COME PROMESSO — attaccato, regge** | `POST /v1/memories` con la chiave di **acme** e `"tenant_id": "globex"` **nel corpo** → 200, `stored: True`. Poi: `GET /v1/search` con la chiave di acme → **1 risultato**; con la chiave di globex → **0**. E su disco nascono due DB distinti (`tenants/acme/memory.db`, `tenants/globex/memory.db`, cartelle `['acme','globex']`). Il campo del corpo **non ha spostato niente** |
| 3 | `verimem/gateway.py:956` `create_app.health` | liveness, e «`/v1/health` non è mai limitato» | **FUNZIONA COME PROMESSO** | `GET /v1/health` **senza chiave** → `200 {'ok': True, 'version': '0.7.7'}`; ed è l'unico: `GET /v1/search` senza chiave → **401** `{'detail': 'invalid or missing API key'}` |
| 4 | `verimem/gateway.py:251` `GatewayKeys` · `verimem/gateway.py:254` `GatewayKeys.__init__` · `verimem/gateway.py:266` `GatewayKeys._connect` | il registro delle chiavi su `gateway_keys.db` | **FUNZIONA COME PROMESSO** | il file nasce al primo `create`; tabelle `['gateway_keys','gateway_usage']`, colonne `['key_id','key_hash','tenant_id','name','plan','created_at','revoked_at']` |
| 5 | `verimem/gateway.py:275` `GatewayKeys.create` | «crea una chiave e la ritorna **IN CHIARO** — l'unica volta che esiste fuori dallo sha256»; `tenant_id` è «uno slug validato (finisce in un path di filesystem)» | **FUNZIONA COME PROMESSO**, e la validazione è provata **su sette nomi** | chiave `vm_` + 40 esadecimali (lunghezza **43**, prefisso `vm_` → `True`). Respinti con `ValueError` parlante: `'../evil'` e `'acme/../x'` (slug) · `'acme.'` («Windows strips trailing dots, collapsing it onto another tenant's directory») · `'con'` («reserved device name on Windows») · `'ACME'` (maiuscole) · 65 caratteri · stringa vuota. **Controllo positivo**: `'acme-2'` → creato. Un rifiuto che rifiuta tutto non proverebbe niente |
| 6 | `verimem/gateway.py:272` `GatewayKeys._hash` | «a riposo solo lo sha256 (`gateway_keys.db`)» | **FUNZIONA COME PROMESSO — misurato sui BYTE, non sulla struttura** | ho cercato la chiave in chiaro **dentro i byte del file**: `k_acme.encode() in gateway_keys.db (bytes)` → **False**. Nella riga c'è `key_hash` (`43cf7e9947011b6a0601449a03d5b66e95…`), non la chiave |
| 7 | `verimem/gateway.py:320` `GatewayKeys.resolve` | risolve la chiave presentata nel suo tenant, «confronto sull'hash via `secrets.compare_digest`» | **FUNZIONA COME PROMESSO** | chiave vera in `X-API-Key` → **200**; la stessa in `Authorization: Bearer` → **200**; una chiave inventata della forma giusta (`vm_` + 40 zeri) → **401** |
| 8 | `verimem/gateway.py:340` `GatewayKeys.revoke` | «revoca senza cancellare (audit)» | **FUNZIONA COME PROMESSO, ed è chirurgica** | `revoke('62fde42659db…')` → `True`; **quella** chiave → **401**, l'altra chiave (altro tenant) → **200**. La riga resta nel DB con `revoked_at` valorizzato |
| 9 | `verimem/gateway.py:350` `GatewayKeys.list` | elenca le chiavi con i loro metadati | **FUNZIONA COME PROMESSO** | usata per prendere il `key_id` da revocare: la riga porta `key_id`, `tenant_id`, `plan`, `created_at` |
| 10 | `verimem/gateway.py:310` `GatewayKeys.plan_for_tenant` | il piano commerciale del tenant, che decide il tetto di richieste | **NON MISURATO** | il piano è `free` di default e il tetto (`rate_limit_per_minute`) è 0 in questa app: il ramo che conta — il 429 con `Retry-After` — si misura con un'app costruita apposta, prossimo blocco |

## Il write path HTTP: gate, LLM, corpi malformati (gateway.py 1004-1180)

| # | funzione (file:riga) | cosa promette | verdetto | prova (comando e esito) |
|---|---|---|---|---|
| 11 | `verimem/gateway.py:1048` `create_app.add_memory` | «stessa semantica dell'SDK — **ogni write passa il gate anti-confab**» | **FUNZIONA COME PROMESSO** | `POST /v1/memories` con un claim che la fonte non sostiene → **200** con `{'moat': 'failed', 'quarantined_by': 'moat', 'stored': True, 'status': 'quarantined'}`. Il fatto entra ma **non è servito**: la porta HTTP dà la stessa risposta dell'SDK, compreso il campo che dice **chi** ha fermato |
| 12 | `verimem/gateway.py:1069` `create_app._add_memory_impl` | «validazione dell'input al bordo: un tipo malformato è un errore del client (400), **mai un 500** — un 500 non gestito su input costruito è un endpoint che si può far cadere = un DoS» | **FUNZIONA COME PROMESSO — quattro corpi, quattro 400** | corpo vuoto `{}` → **400** (la guardia contro lo scarto silenzioso) · `{'content': 123}` → **400** · `{'messages': 'non una lista'}` → **400** · `topic` come dizionario → **400**. Nessun 500 |
| 13 | `verimem/gateway.py:1048` `create_app.add_memory` (ramo `messages`) | «**niente LLM implicito** (O4): l'ingest conversazionale è disponibile solo se l'operatore costruisce l'app con un `llm`; senza, **400 onesto**» | **FUNZIONA COME PROMESSO, e l'errore insegna** | `POST /v1/memories` con `messages` su un'app senza `llm` → **400**: «conversation ingest needs a server-side extraction llm: start the gateway with one (`create_app(llm=...)`); single verified facts work witho…». Dice cosa manca, come rimediare, e **cosa funziona lo stesso** |
| 14 | `verimem/gateway.py:1178` `create_app.search` | la lettura per tenant | **FUNZIONA COME PROMESSO** (isolamento provato alla riga 2) | `GET /v1/search?q=canone capannone` → 200 con i risultati del **proprio** tenant; il `k` di default di questa porta è **4** (letto nel codice, riga 621 per la variante non-tenant) |
| 15 | `verimem/gateway.py:383` `_Metering` · `verimem/gateway.py:409` `_Metering.bump` | il contatore d'uso per tenant | **FUNZIONA COME PROMESSO** (misurato di riflesso) | dopo il giro di prove, `gateway_usage` porta `['acme', '2026-09-09', 4, 3, 1, 1, 0]`: **4 richieste, 3 letture, 1 scrittura, 1 memorizzata, 0 respinte** — i conti tornano con quello che ho fatto io in quella sessione |
