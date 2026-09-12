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

*ws5 (Piattaforma), 08/09. Tutte le righe di questo file hanno il comando che le produce.*

---

# Aggiunta — il secondo giro, e una correzione al righello

## Il mio conteggio «senza chiamanti» era ROTTO: 20 falsi positivi su 21

Avevo contato i chiamanti **escludendo il file stesso**, e ottenuto 21 righe a «0
chiamanti». Col righello corretto (dentro **e** fuori il modulo):

    _compute_hmac   dentro:3 fuori:0     ·  _canonical_body  dentro:2 fuori:0
    _load_secret    dentro:2 fuori:0     ·  _mac             dentro:3 fuori:0
    … 19 righe cosi': PRIVATE USATE IN CASA …
    community_of    dentro:1 fuori:0     ← l'unica con la sola definizione

⇒ **Su 21 «candidati morti», uno solo regge** — ed è quello già confermato. Gli altri 20
erano miei falsi positivi. *Un righello che esclude il caso normale trova soprattutto sé
stesso.*

## `engram_syscall_mcp` — importato da ZERO posti, ma non è morto

    importato da: 0        (per confronto: mutation_audit 21 · redaction 15 ·
                            capability_token 10 · airgap 10 · stable_partition 9)
    ma:  :203 def main()   ·  :233 if __name__ == "__main__"
    documentato in: CONTRIBUTING.md · docs/F2_MODULE_INVENTORY.md · docs/stato-reale/85-…
    in pyproject.toml / setup.py: NO

⇒ **È una porta da riga di comando** (`python -m`), non un modulo morto. ⚠️ Ma **non è un
console-script**: chi installa il pacchetto non lo trova fra i comandi, e nessun test lo
esercita. Decisione di prodotto, non mia.

## T42 è puntato sui file sbagliati

    verimem/engram_syscall_mcp.py   0 occorrenze di 'clp'
    verimem/capability_token.py     5, tutte commenti o un PATH (~/.clp/a2a-secret.bin)
    verimem/mesh_memory.py:76       from clp.agentos import vec_bus as _vb   ← il vero import

📌 Su `capability_token` resta però una dipendenza **di dati**: legge
`~/.clp/a2a-secret.bin`, cioè **condivide il segreto col bus A2A sul filesystem**. Diversa
da un import, e per la sicurezza vale una riga sua.

---

# Chiusura del lotto 2 — il righello corretto passato su TUTTE le 59

    ⚰️ stable_partition.community_of   dentro:1  fuori:0   ← la sola definizione
    (nient'altro)

Tutte le altre 58 hanno `dentro:2-3` (private usate in casa) o chiamanti esterni.
⇒ **Il lotto 2 — 32 file, 4.430 righe — contiene UN codice morto**, confermato tre volte con
righelli diversi.

📌 Il numero da citare resta **«59 su 143 non sono NOMINATE da un test»**, non «59 scoperte».

## La classe che due istanze hanno trovato nello stesso quarto d'ora

@ws2, mappando un'altra superficie: *«"spenta" 3 volte su 5 voleva dire "non ci sono
arrivato io". Cinque funzioni VIVE le avevo viste tutte spente.»*
Io, dieci minuti prima: **21 candidati morti, 20 falsi**, perché il righello escludeva il
file stesso.

🔑 **Regola che ne esce, e vale per chiunque mappi**: *un verdetto «spenta / morta / mai
chiamata» va rifatto con un SECONDO righello prima di uscire dal proprio worktree.* Il primo
righello sbaglia quasi sempre nella stessa direzione — dice «assente» dove c'è «non l'ho
guardato».

E la rarità è essa stessa il dato: @ws6 ha trovato **un** codice morto vero (`by_task`,
`memory.py:1573`), io **uno** (`community_of`). Su due superfici grandi, uno a testa.

---

# Precisazione al reperto della tamper-evidence: **due firme, una sola verificata**

Il primo giro diceva *«`verify_head_signature` è chiamata solo dai test»*. Vero, ma
incompleto: il quadro esatto sono **quattro funzioni**, e l'asimmetria sta dentro lo stesso
file.

    funzione                    in tamper_evidence   altrove in verimem/   test
    sign_head                          1 (solo def)          4              1
    verify_head_signature              1 (solo def)          0   ⚠️         1
    sign_receipt                       2                     3              1
    verify_receipt_signature           2                     2   ✅         1

⇒ **Il prodotto FIRMA la testa in 4 punti e non verifica MAI quella firma.** Non è che «non
verifica niente»: `verify_receipt_signature` è chiamata da `client.audit_verify_anchor`, il
cui docstring lo conferma — *«Verify a signed anchor receipt …: signature valid, both chains
intact, row counts only grew»*.

## E sono DUE LIVELLI, non uno

    livello 1  catena di hash      client.audit_verify()      ✅ provata da @ws3 rompendo
                                                                 la catena: torna l'id
                                                                 della riga manomessa
    livello 2  firma della testa   sign_head → verify_head…   ⚠️ apposta, mai controllata

`mutation_audit` **non nomina mai** la firma: i due livelli non si toccano. **Nessuno dei
due reperti, da solo, lo diceva**: serviva la prova di @ws3 *e* questo conteggio.

📌 **La forma è la stessa che ho mappato nella ricevuta MCP**: @ws3 osserva che `None` di
`audit_verify` vale sia «catena intatta» sia «audit mai acceso» — due casi in un valore solo,
esattamente come `grounding_score: null` valeva «non giudicato» e «giudicato zero». Là la
cura è stata **un booleano in cima alla ricevuta**. Qui sarebbe la stessa.

⛔ **Quello che questa riga NON dice**: se sia sfruttabile. Non c'è un modello di minaccia
qui, e la firma della testa potrebbe servire a un verificatore **esterno**. Dice solo che
nessun percorso del prodotto la controlla.
