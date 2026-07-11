# Security audit — Verimem/engram (2026-07-11)

Prima passata del mandato *hardcore security audit* (Aurelio, esecuzione formale
lunedì 2026-07-13). Questa sessione **inizia** l'integrazione/correzione — non è
l'audit completo.

## Verdetto complessivo (aggiornato dopo il deep-dive)

**La sicurezza del prodotto-memoria è solida.** La suite offensiva esistente
`tests/security/` passa **188 test** (SSRF incl. DNS-rebind TOCTOU, path-traversal,
prompt-injection, secrets-redaction, executor-isolation, editfmt) — il codebase era
già passato per uno sprint di security (CVE-001…011). Questo audit ha aggiunto i gap
**genuinamente nuovi** (E3 indirect injection nel tier documenti, G1/E1/E2 DoS) e ha
**verificato** il resto (write-gate, XXE, SQLi, homoglyph, RCE-sink, ledger,
asserted_at, AutoMemory), bloccando l'invariante "zero sink RCE" con un guard AST in CI.

**Rischio "figuraccia" pubblica: basso.** I claim (README, sito, BENCHMARKS.md) sono
onesti e caveati ("parity, not a win", "none is third-party audited", giudice e n
dichiarati) — un tecnico ci trova credibili, non ridicoli.

**Gap reali ma DICHIARATI** (ammissioni, non bugie): VeriBench non esiste ancora,
nessun audit di terze parti, scala live non testata oltre ~100k sintetici,
`mcp_server.py` non letto riga-per-riga (ma: stdio locale, no rete, no sink RCE, API
gated → superficie intrinsecamente limitata).

## Regole d'ingaggio

- **Default = NON-è-vuln.** Va provato il contrario con un **PoC concreto**.
- Pattern ≠ vulnerabilità. **Mai una severity senza un artefatto** (PoC isolato,
  numeri, riproduzione).
- Lavoro **manuale** (nessun workflow/swarm), PoC su tmpdir isolato.
- TDD: RED→GREEN, verde prima del commit, un fix per commit, push a ogni commit.

## Metodo

Scanner riprodotti in locale (non fidarsi di numeri a memoria): `bandit -r engram`
(severity HIGH), lettura sorgente manuale delle superfici del mandato, PoC Python
isolati per ogni claim.

---

## Findings FIXATI (con PoC + fix + commit)

| id | superficie | severity | PoC (artefatto) | fix | commit |
|----|-----------|----------|-----------------|-----|--------|
| **G1** | gateway `_body_limit` | MEDIA (DoS) | body 5KB su cap 1KB **CON** Content-Length → 413; **SENZA** (chunked) → 200 + `stored=True` (cap aggirato) | middleware ASGI buffer-and-replay che conta i **byte reali**; oltre cap = 413 senza far girare l'app | `5e474d0` |
| **E1** | Document RAG `_extract_epub` | MEDIA (DoS/OOM) | EPUB 38KB → **40MB** estratti in RAM (ratio **1025x**, peak heap 129MB) | `z.open().read(cap+1)` bound sui byte decompressi (per-member 25MB + budget 200MB) su **contenuto e metadati** | `aebbe7a` |
| **E2** | Document RAG `_extract_docx` | MEDIA (DoS/OOM) | DOCX 74KB → **40MB** estratti (ratio **529x**, peak 88MB) via python-docx non stream-cappabile | `_assert_zip_within_limits()` pre-screen delle dimensioni dichiarate nella central directory prima di python-docx | `380d4a9` |
| **E3** | Document RAG `DocumentIndex` | MEDIA-ALTA (indirect prompt injection) | doc con "Ignore all previous instructions…" → restituito **verbatim** da `search()` nel contesto agente; gli stessi byte come fatto erano quarantenati | sanitize-then-scan a index time, `flagged` + hide-by-default (invariante di citazione preservata), audit via `include_flagged` | `8755d04` |
| **H1** | igiene scanner | — (non-vuln) | bandit B324: 4 SHA1 flaggati HIGH | `usedforsecurity=False` su hash non-crittografici (id/cache/dedup); digest identici; bandit HIGH **7→3** | `324cb59` |

Tutti verificati con suite verdi: gateway 50/50, extract/document 22/22.

## Superfici VERIFICATE SOLIDE (nessuna azione, claim di sicurezza retto)

- **Gateway multi-tenant — isolamento & auth** (`engram/gateway.py`):
  - il `tenant_id` deriva **solo** dalla chiave risolta dal DB, mai da un campo
    della richiesta; slug validato `^[a-z0-9][a-z0-9._-]{0,63}$` (no `/`, no `..`
    iniziale) → **no path traversal**.
  - **IDOR**: `get(fact_id)` gira sul DB **per-tenant isolato** → un fact_id di un
    altro tenant = 404 (namespacing per store, non per campo).
  - **timing**: confronto `secrets.compare_digest` costante sull'sha256; una chiave
    non valida scorre comunque tutte le righe (lavoro costante) → **no oracle di
    enumerazione**.
- **XXE / billion-laughs nei parser documento**:
  - DOCX: `python-docx` usa `etree.XMLParser(resolve_entities=False)` → entità
    interne non espanse (billion-laughs neutro) + esterne non risolte (XXE neutro).
  - EPUB: `safe_xml` rifiuta ogni `<!DOCTYPE`/`<!ENTITY>` → guarda l'espansione di
    entità dello stdlib ElementTree; il fallback usa BeautifulSoup `html.parser`.
- **Write-gate — forgiatura di `verified_by`/status** (`semantic.py` store, mandato
  #2): difesa a strati — unicode-sanitize → **injection-screen ALWAYS-ON** su
  proposition E topic (→ quarantena, rank -1) → admission-gate → **hard-gate v2 con
  verifica I/O reale** (`file:path:line` deve esistere sul filesystem, `commit sha`
  via `git rev-parse`; se `repo_root=None` nessun ref verifica → demote a
  `model_claim`). Nel gateway multi-tenant `Memory()` è costruito **senza
  repo_root** → **forgiare `status='verified'` da remoto è impossibile** (tutto
  demota). Il bypass del hard-gate (trusted-hook) richiede il token server-side
  `ENGRAM_HOOK_TOKEN` (`writer_role` è client-spoofable → fail-closed). `status='provisional'`
  richiede solo un match URL/arxiv (format-only) = etichetta onesta di trust
  inferiore, non un bypass.
- **Ledger fail-open** (`trust_ledger.py`, mandato #3): il fail-open è *by design*
  (observability, non data-path) e ora **visibile** — le perdite incrementano
  `write_failures`, esposto da `trust_stats` (review 2026-07-09), non zeri
  silenziosi. Soprattutto **la difesa non dipende dal ledger**: il gate
  quarantena/rifiuta comunque. Rompere l'odometro non indebolisce il gate.
- **`asserted_at` temporale** (`truth_reconciliation.py` gate C6, mandato #6): un
  `asserted_at` nel futuro (oltre `_FUTURE_SKEW_S`=300s) → `classify_conflict`
  ritorna **`dispute`, non `update`** → non supersede il presente. Un tenant non
  può datare un fatto nel futuro per farlo "vincere" per sempre. In più il
  reconcile-on-write è opt-in e il default è fail-safe (contende, non supersede).
- **AutoMemory** (`auto_memory.py`, mandato #5): opt-in per costruzione; `_do_flush()`
  chiama `Memory.add(...)` = **stessa pipeline gated** dell'ingest esplicito (nessun
  canale privilegiato; un fatto auto-osservato nasce `model_claim`). Non bypassa il gate.
- **SQLi storage** (mandato #6): sweep sistematico sulle f-string SQL — interpolano
  solo stringhe di placeholder `?,?,?`, `LIMIT {int(...)}` coerced, o identificatori
  interni (schema/costanti). **Nessun valore untrusted in SQL**; i VALORI sono sempre
  parametrizzati.

---

## LEAD APERTI (per il deep-audit di lunedì — non ancora provati)

Elencati con onestà come **ipotesi da falsificare**, non come vulnerabilità.

1. **Write-gate L1-L4** (mandato #2): **ASSESSATO → solido da remoto** (vedi
   "verificate solide"). Residui reali, non ancora chiusi: (a) *ref-resolves ≠
   ref-supports* — la verifica I/O conferma che il ref **esiste**, non che
   **sostenga** il claim (un `commit sha` valido ma irrilevante "passa"),
   sfruttabile solo in **locale** con `repo_root` settato (auto-confabulazione
   dell'agente), non da remoto; (b) recall del detector di injection su
   offuscamenti oltre l'unicode (arms race: red-team catch 0.9677, residuo 38
   homoglyph + 1 role_hijack dichiarati).
2. **Recall del detector di injection** — arms race sui payload offuscati oltre
   l'unicode (homoglyph, base64, split-token): red-team catch 0.9677, residuo 38
   homoglyph + 1 role_hijack dichiarati. Vale per i fatti E per i documenti (E3
   usa lo stesso `detect_injection`).
4. **PDF bomb** via PyMuPDF (C lib, generalmente hardened) — da valutare con un
   PDF craftato; priorità bassa.
5. **3× `subprocess shell=True`** in `interactive_judge.py` (bandit B602 HIGH
   residui): tooling **interno** del giudice, args non attacker-controlled →
   convertire a `shell=False` o `# nosec` con giustificazione.
6. **~192 finding ruff-S** (report-only in CI `security.yml`): triage per separare
   il rumore dai reali; obiettivo = poter rendere bandit/ruff-S **bloccanti**.

## Deep-dive superfici esposte (mandato "anticipa lunedì")

Passata più a fondo, oltre i gate del write-path:

- **Homoglyph injection — VERIFICATO SOLIDO empiricamente.** Sonda su 8 attacchi
  (mixed-script Cirillico/Greco, mono-script lookalike, fullwidth, role-hijack,
  exfil) + 6 legittimi multilingua: **8/8 presi, 0 falsi positivi**.
  `_has_mixed_script_token` + fold confusables chiudono la classe. La stima "38
  residuo aperto" che avevo dato **era stale** — corretta con la sonda.
- **RCE / deserializzazione — pulito.** Nessun `pickle.load`/`marshal.load`/
  `yaml.load(`/`eval(`/`exec(`/`os.system`/`__import__` su input untrusted. Tutti i
  `subprocess` sono interni (spawn daemon, `git rev-parse` per la verifica dei ref,
  `clp ai-eye`) e non ricevono input attacker-controlled dal percorso memoria.
- **SQLi — pulito completo** (f-string + `.format` + `%` + concatenazione): i VALORI
  sono sempre parametrizzati; le f-string interpolano solo placeholder/`LIMIT int`/
  identificatori interni.
- **Dashboard routes** (`dashboard_routes/`): auth session-token (file 0600, CVE-009)
  sulle route state-changing (`/api/chat|plan|sleep|feedback`); read-route
  loopback-default.
- **Sandbox shell** (`sandbox.py`): superficie del CODING-AGENT (agentos), NON del
  prodotto memoria; già indurita in più round adversariali (deny-by-default, metachar
  denylist, strict-mode `shell=False` opt-in). Residuo dichiarato: legacy mode
  `shell=True` (default) = mitigazione parziale — fuori scope VeriMem-memoria.

**Conclusione onesta**: la superficie di sicurezza del *prodotto memoria* è in buono
stato — questo giro ha trovato 1 buco nuovo reale (E3, fixato) + DoS induriti; il
resto è solido o già-auditato in round precedenti (CVE-001 ide, CVE-009 dashboard,
i round sandbox). Il rischio "figuraccia" **non è un buco tecnico spalancato**: è (a)
overclaim nel posizionamento pubblico, (b) superfici non-prodotto (agentos), (c)
non-testato-a-scala. **Non** auditato line-by-line: `mcp_server.py` (~7000 righe, solo
grep-ato), concorrenza/race condition, la config di deploy reale.

## Concatenazione → Vivarium + VeriBench

Il gap *ref-resolves ≠ ref-supports* del write-gate è la **stessa legge** del lab
Vivarium (v4.1 derivazione-condivisa: la conoscenza derivata va ri-verificata
contro la base condivisa — non basta l'esistenza/reputazione della fonte; e v10.0:
il trust certifica "chi l'ha detto + corroborato", non la verità). Il security
audit **conferma dal vivo** ciò che il lab ha derivato in simulazione.

Diventa un **asse VeriBench inedito** (#11): *provenance verification DEPTH* — il
sistema verifica che la fonte citata **sostenga** il claim, o solo che
**risolva/esista**? Verimem ha già l'hard-gate v2 con verifica I/O; nessun
competitor ha né hard-gate né verifica dei ref (mem0/engram-memory accettano
qualsiasi `verified_by` come stringa) → misurare la *depth* è un asse su cui
partiamo avanti.

## Nota di scope (onestà)

Questa è la **prima passata**, non l'audit completo. Superfici del mandato non
ancora toccate: AutoMemory poisoning (#5), import conversazioni, storage SQLite
(SQLi/manipolazione supersession), gateway purge-GDPR/restore. La postura resta:
provare, non assumere.
