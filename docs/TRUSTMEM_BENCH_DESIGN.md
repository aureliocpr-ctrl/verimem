# TrustMem-Bench — il benchmark che imponiamo noi (design v0, 2026-07-06)

**Perché.** Oggi corriamo sulle piste altrui (HaluMem è del gruppo MemOS; LoCoMo/
LongMemEval misurano accuratezza grezza). Nessun benchmark pubblico misura ciò
che rende una memoria *affidabile*. Chi definisce il metro vince la categoria:
i competitor dovranno o ignorarlo (e la domanda "perché non lo passate?" resta)
o correrci — in casa nostra.

**Il problema di credibilità (dichiarato).** Un benchmark scritto dal venditore
è giudice-e-giuria. Mitigazioni non negoziabili:
1. **Riproducibile al 100%**: harness open, task generati da script con seed
   pubblicati, prompt del giudice pubblicati, un comando per rifare tutto.
2. **Anche i NOSTRI fallimenti nel report** (un autore che si dà 100/100 non è
   credibile — pubblichiamo il nostro punteggio VERO, buchi inclusi).
3. **Giudice duale**: check deterministici locali dove possibile (astensione,
   resurrezione post-delete, supersede sbagliati = misurabili senza LLM);
   giudice LLM solo dove serve semantica, con prompt versionati.
4. Inviti espliciti a terzi + PR di risultati accettate.

## I 6 assi (ognuno già prototipato dal nostro lavoro interno)

| Asse | Domanda | Metrica | Nostro precedente |
|---|---|---|---|
| 1. Fabrication under absence | la risposta NON è in memoria: inventa? | abstention-rate | Boundary 1.000/0.976 |
| 2. Sycophancy resistance | l'utente contraddice con insistenza un fatto evidenziato: cede? | cave-rate sotto pressione crescente | 1.0→0.0 col gate |
| 3. Destructive-update resistance | update con trappole cross-attributo: cancella fatti innocenti? | wrongful-supersede rate | dial 99→7, 0 cross-attr |
| 4. Temporal integrity | "quanto era X a marzo?" / "da quando è Y?" | as-of accuracy + transition accuracy | as_of + storia (+16pp) |
| 5. Forget integrity (GDPR) | dopo il delete, il dato risorge da QUALSIASI via? | resurrection-rate su deep/as-of/history/search | purge-chain (fix d0a8863) |
| 6. Provenance honesty | sa dire COME lo sa? | dossier presente + campi verificabili | TrustReport |

## Dataset
Generatore sintetico multi-sessione (personas con timeline, update, trappole)
— stile HaluMem ma NOSTRO: script + seed fissi, umanamente auditabile, EN + **IT**
(nessun benchmark memoria esiste in italiano: prima mossa anche lì). Taglie:
smoke (5 personas) / full (50). Zero dati reali = zero privacy.

## Esecuzione competitor (onestà operativa)
- **Verimem**: harness nativo.
- **mem0 OSS**: adapter locale; config LLM dichiarata (non la loro default
  OpenAI — caveat esplicito nel report; invito a submitarci il run ufficiale).
- **Zep/servizi**: se non eseguibili localmente, riga "not run — invited" (non
  numeri inventati). Il vuoto parla da solo.

## Roadmap
v0 design (questo doc) → **✅ generatore+smoke-set+run Verimem (2026-07-06,
`benchmark/trustmem_bench.py`)** → adapter mem0 + invito pubblico → i 2 assi
LLM-judged (answer quality, sycophancy sotto pressione) → leaderboard nel repo.

## Stato v0.1 (2026-07-06) — SHIPPED
- **Generatore** `generate_dataset(n_personas, seed)`: puro, seeded, EN+IT,
  timeline datate + trappole cross-attributo + attributo assente + fatto GDPR.
  Stesso seed = byte identici (auditabile). Smoke-set committato
  (`benchmark/results/trustmem_smoke_dataset.json`, n=10 seed=42).
- **5 assi deterministici** (verdetto senza LLM, senza rete): abstention-under-
  absence, destructive-update, temporal-integrity, forget-integrity,
  provenance-honesty. `run_verimem` → scorecard
  (`benchmark/results/trustmem_verimem_scorecard.json`).
- **Verimem: 50/50** sugli assi deterministici. **Onestà (§2)**: 100% su assi
  che *costruiamo* è atteso e prova solo la non-regressione (vale da integration
  guard); il valore competitivo è (a) eseguire i competitor sugli stessi assi,
  (b) i 2 assi LLM-judged dove nessuno fa 100%.
- **Il bench ha già ripagato**: l'asse absence usciva 0/6 perché `explain()` non
  aveva un floor di rilevanza (bi-encoder anisotropo matcha ~0.8 qualsiasi
  query). Misurata la separazione (rilevante ≥0.842 vs assente ≤0.828) →
  aggiunto `min_relevance` opt-in a `build_trust_report`/`Memory.explain`
  (default 0.0 invariato). Un benchmark che possiedi trova i tuoi buchi.

## Prossimo
Adapter mem0 (config LLM dichiarata) + i 2 assi LLM-judged + invito pubblico.
Gate competitor-run: quando lo slot claude-p è libero.
