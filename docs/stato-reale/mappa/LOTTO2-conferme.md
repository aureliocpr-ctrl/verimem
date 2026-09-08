# Lotto 2 — le conferme sulle bozze (32 file, 4.430 righe, 133 funzioni)

Le bozze sono generate da `scripts/mappa_bozza.py`; **qui c'è ciò che ho confermato
eseguendo**, che è la parte che le bozze non possono avere. Su `7b9e8ca1`, e i 32 file sono
**identici** al tip `20257636` (`git diff --stat` vuoto).

    righe di tabella      143
    senza TEST che le nomini   59   (41%)
    senza CHIAMANTI             5
    senza ENTRAMBI              1

---

## 1. Le 5 senza chiamanti, **classificate una per una** (contarle non serviva a niente)

| riga | verdetto | prova |
|---|---|---|
| `JsonlAuditSink.__call__` | ✅ **falso positivo** | `__call__` si invoca implicitamente; `gateway.py:889-890` costruisce e usa entrambi |
| `AccessAuditMiddleware.__call__` | ✅ **falso positivo** | idem, `app.add_middleware(AccessAuditMiddleware, …)` |
| `Partition.community_of` | ⚰️ **codice morto CONFERMATO** | cercata in tutto il repo (`.py .json .md .toml`): **solo la definizione**, `stable_partition.py:57` |
| `generate_audit_keypair` | 🔴 **solo dai test** | `tests/test_tamper_anchor_b.py`, `test_tamper_anchor_receipt.py`; in `verimem/` solo la def |
| `verify_head_signature` | 🔴 **solo dai test** | `tests/test_tamper_anchor_b.py`; in `verimem/` solo la def |

### 🔴 I due rossi valgono più degli altri tre

**La verifica della firma della testa dell'audit trail è scritta, è testata, e nessun
percorso del prodotto la invoca.** È la forma *«una capacità spenta non emette segnale»*:
nessun log dirà mai che non viene usata, perché non viene usata.

📌 **Non è automaticamente un difetto** — può essere pensata per un operatore che verifica a
mano. **Ma allora va scritto**, perché chi legge «tamper-evident» presume una catena che si
controlla da sé. La domanda per chi ha l'owner della sicurezza: *la catena si verifica da
sola, o solo su richiesta esplicita?*

---

## 2. I 59 senza test, per file — e il caso che ribalta la lettura

    env_num              2/2   ← unico file dove NESSUN test nomina nulla
    engram_syscall_mcp   7/8
    gateway_audit        7/11
    capability_token     4/6
    stable_partition     5/8
    redaction            3/4
    daemon_runner        4/7 · event_jsonl_log 4/7 · mutation_audit 4/7
    airgap 3/7 · provenance_signing 3/7 · flow_tail 2/4 · tamper_evidence 2/10 · …
    ZERO senza test: _call_telemetry · _proc_quiet · _singleton_guard · _telemetry_prefixes
                     · _thread_budget · chunking · compose_daemon · gateway_plans
                     · jsonutil · self_heal · trunc

### ⚠️ `env_num` mostra perché «senza test» NON vuol dire «scoperto»

    chiamanti trovati:  client.py:144-145 · composer.py:47-48 · conversation_ingest.py:191 (+8)
    occorrenze nel prodotto: 25
    test che lo nominano: NESSUNO

⇒ È **esercitato di sbieco da ogni test che passa per quei chiamanti**, e allo stesso tempo
**non ha un test proprio**. Le due cose stanno insieme, e chiamarlo «non coperto» sarebbe
falso quanto chiamarlo «coperto».

🔑 **Perché conta proprio qui**: `finite_or` promette *«`raw` as a finite float, else
`default`»* — è un **guardiano contro NaN e infiniti**, usato in 25 punti. Un guardiano che
sbaglia non fa cadere nessun test suo: fa passare un valore sbagliato **dentro qualcun
altro**. È il posto dove un test diretto vale più che altrove.

---

## 3. Quello che queste conferme NON dicono — dichiarato

- **I 59 non sono classificati uno per uno**: ho classificato i 5 senza chiamanti e ho
  aperto `env_num` come caso esemplare. Gli altri 58 restano **candidati**, non verdetti.
- **Non ho misurato la copertura reale** (nessun `coverage`): «nominata da un test» è un
  righello lessicale, e @ws2 ha misurato oggi che tre righelli diversi danno tre numeri che
  sbagliano in direzioni opposte.
- **Il filtro con cui ho estratto questi numeri era rotto al primo tentativo** (cercavo `-`,
  il campo vuoto è `nessuno`) e dava **zero**. L'ho scoperto provandolo su un caso che
  *doveva* rispondere. ⇒ i numeri qui sopra vengono dal filtro **corretto**, e chi li rifà
  usi lo stesso controllo prima di fidarsi di uno zero.

---

*ws5 (Tara), 08/09. Tutte le righe di questo file hanno il comando che le produce.*
