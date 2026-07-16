# AUDIT-LEDGER — registro dell'audit riga-per-riga (Fase C)

Mandato (Aurelio, 2026-07-16): «una cosa alla volta dovrà essere controllato,
riga per riga, funzione, logiche, metriche, numeri, dovrà essere provato».

**Metodo per ogni file**: (1) lettura INTEGRALE; (2) contratto dichiarato vs
comportamento PROVATO (probe eseguiti, non ragionamenti); (3) numeri dichiarati
ri-misurati dove possibile; (4) ogni finding con severità, evidenza riproducibile
ed esito (fixato con SHA / no-fix motivato / aperto). Un finding senza probe non
entra. «Verificato» = probe/test citato, mai un'opinione.

Severità: **ALTA** = comportamento sbagliato osservabile dall'utente o perdita
dati; **MEDIA** = comportamento scorretto in casi realistici, impatto limitato;
**BASSA** = imprecisione/edge teorico/documentazione fuorviante.

---

## Modulo 1 — write-gate

### engram/admission_gate.py (188 righe) — 2026-07-16, base `e3865d4`

Letto integralmente. Probe eseguiti: 3 (sotto). Contratto: route/flag mai
delete; ordine pollution→injection→telemetry→duplicate→provenance→accept.

| # | Finding | Sev. | Evidenza (probe) | Esito |
|---|---------|------|------------------|-------|
| 1 | Prefisso telemetria `"dialog/voice"` (senza `/` finale) cattura qualunque topic che inizi così: `classify_admission(topic="dialog/voicemail-from-mom")` → `route_telemetry` — un fatto personale legittimo esce dal corpus curato. | BASSA | Probe live 2026-07-16; il reason stampa inoltre `telemetry topic 'dialog/'` (namespace troncato a `split('/',1)[0]`, fuorviante: `dialog/` NON è in denylist). | **NO-FIX (design pinnato)**: `test_property_invariants_g5.py:45` asserisce `classify_tier("dialog/voice"+suffix)==TIER_TELEMETRY` per QUALSIASI suffisso — contratto deliberato. Osservazione registrata; l'unico topic reale osservato è `dialog/voice/turn`. |
| 2 | Reason `"grounded or verified"` è FALSO per ogni status ≠ `model_claim`: `status="user_belief"` → ACCEPT «grounded or verified» (un'asserzione utente NON verificata); idem `status="quarantined"`. `admit_to_curated=True` è corretto (il trust viaggia nello status), il REASON mente. | BASSA | Probe live 2026-07-16: `classify_admission(..., status="user_belief")` → `accept / "grounded or verified"`. Reason non pinnato da alcun test (grep 2026-07-16). | **FIXATO** in questo pacchetto: reason onesto per status non-model_claim + test contratto. |
| 3 | `gate_enabled()` default OFF con `except Exception: pass` sul ramo file-flag (fail-toward-OFF per un gate di sicurezza). | BASSA | Lettura righe 72-79; già censito in FLAGS-AUDIT §3 (claim-vs-default). | NO-FIX qui: decisione di default già trattata in FLAGS-AUDIT (Giro 1b: no flip senza misura); il silent-except resta accettabile perché il fallback è il comportamento documentato. |

Non-findings verificati (per completezza): `LIMIT {int(limit)}` cast-protetto
(no SQL injection); `audit_corpus` apre `mode=ro` (mai scrive); dedup key
whitespace+case-folded coerente tra `classify_admission` e `audit_corpus`;
`_MARKUP_LEAK` ridondanza innocua (`<parameter name=` già coperto da
`</?parameter\b`); alternativa CSV di `source_episodes` gestisce stringhe di
soli spazi.

Numeri dichiarati nel docstring (59.6% flagged sul corpus live 2026-06-04):
storici, non ri-misurabili al medesimo snapshot — marcati come storici, non
come claim correnti.

**Verdetto file**: SOLIDO. 1 fix cosmetico-semantico applicato, 1 osservazione
di design, nessun difetto funzionale.

### engram/_telemetry_prefixes.py (98 righe) — 2026-07-16, base `e3865d4`

Letto integralmente (è la single-source-of-truth write+read della denylist).
Struttura corretta: modulo LEAF senza import engram (niente cicli);
`classify_tier` ordina telemetry>test>dialog>knowledge coerente col commento.
Unico rilievo: il finding #1 sopra (`"dialog/voice"` senza slash). Nessun
altro prefisso è slash-mancante (verificato a occhio su tutte le 20 voci, ogni
altra termina con `/`).

**Verdetto file**: SOLIDO.
