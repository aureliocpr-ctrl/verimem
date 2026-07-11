# Security audit — Verimem/engram (2026-07-11)

Prima passata del mandato *hardcore security audit* (Aurelio, esecuzione formale
lunedì 2026-07-13). Questa sessione **inizia** l'integrazione/correzione — non è
l'audit completo.

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

---

## LEAD APERTI (per il deep-audit di lunedì — non ancora provati)

Elencati con onestà come **ipotesi da falsificare**, non come vulnerabilità.

1. **Write-gate L1-L4 — evasione anti-confab** (mandato #2): un claim con
   provenienza pulita (`verified_by`) è ammesso **by design** (la provenienza *è*
   la fiducia; il trust certifica "chi l'ha detto + corroborato", non la verità —
   Vivarium v10.0). Il vettore reale da provare: (a) **forgiare** `verified_by`
   che il fatto non ha; (b) evadere i detector L1.x con offuscamento oltre
   l'unicode (già chiuso da C4 sanitize-then-scan). Richiede lettura profonda dei
   detector in `semantic.py`.
2. **`asserted_at` attacker-controlled** (mandato #6): il gateway passa
   `asserted_at=body.get("asserted_at")` — un tenant può datare un fatto nel
   futuro e vincere per sempre la supersession / falsare le query `as_of`.
   Impatto: within-tenant (self-poisoning del proprio store), severity da
   quantificare. Da provare con PoC bi-temporale.
3. **trust_ledger fail-open** (mandato #3): romperlo per far sparire azioni
   dall'odometro — verificare che il fail-open non nasconda anche eventi reali.
4. **PDF bomb** via PyMuPDF (C lib, generalmente hardened) — da valutare con un
   PDF craftato; priorità bassa.
5. **3× `subprocess shell=True`** in `interactive_judge.py` (bandit B602 HIGH
   residui): tooling **interno** del giudice, args non attacker-controlled →
   convertire a `shell=False` o `# nosec` con giustificazione.
6. **~192 finding ruff-S** (report-only in CI `security.yml`): triage per separare
   il rumore dai reali; obiettivo = poter rendere bandit/ruff-S **bloccanti**.

## Nota di scope (onestà)

Questa è la **prima passata**, non l'audit completo. Superfici del mandato non
ancora toccate: AutoMemory poisoning (#5), import conversazioni, storage SQLite
(SQLi/manipolazione supersession), gateway purge-GDPR/restore. La postura resta:
provare, non assumere.
