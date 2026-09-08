# I 287 documenti di `docs/`, classificati

> ws8 (Corrado), 08/09/2026. **Questo file cresce**: ogni riga della tabella è un
> verdetto **letto**, non dedotto. Le righe che mancano non sono documenti sani:
> sono documenti **non ancora guardati**, e il contatore in fondo dice quanti.

## Il metodo, e perché non è automatico

Uno script raccoglie gli **indizi** (`classifica_documenti.py`): chi cita il
documento, quali dei path che nomina non esistono più, quando è stato toccato.
Il **verdetto no**: lo do leggendo.

🪞 **Il primo documento che ho letto mi ha dato ragione di non fidarmi dello
script.** `GRAVITA-DIFETTI.md` nomina `tests/test_due_fonti_dichiarate_non_si_ritirano.py`,
che non esiste: indizio di «contraddice». Letto il contesto, il documento dice
**«287 righe, 11 test, rimosso dal revert»** e racconta di averlo recuperato da
`05c26887^` per rieseguirlo. **Non contraddice il codice: lo racconta, ed è pure
preciso.** Classificarlo dall'indizio sarebbe stata una diffamazione.
⇒ Da lì un secondo strumento (`triage_path_rotti.py`) separa chi **afferma** da
chi **racconta** guardando le due righe attorno alla menzione. Non decide:
ordina la coda.

## I verdetti dati finora

| documento | verdetto | la prova |
|---|---|---|
| `docs/stato-reale/GRAVITA-DIFETTI.md` | **VIVO** | nomina un test inesistente ma dichiara «rimosso dal revert» e spiega di averlo recuperato da `05c26887^`: racconta, non afferma |
| `docs/recipes/corpus-bonifica.md` | **CONTRADDICE IL CODICE** | è una ricetta: alla riga 21 dice `python scripts/engram_bonifica.py`, e quel file non esiste. Chi la segue ottiene un errore |
| `docs/EPISTEMIC_FAILURES_STUDY.md` | **CONTRADDICE IL CODICE** | riga 87: cita `benchmark/semantic_conflict.py` come fonte dello studio sui falsi positivi; il file non esiste |
| `docs/CYCLE134-DESIGN.md` | **MORTO** | riga 65 specifica `tests/test_dashboard_sse_e2e.py` come test da scrivere: il test non è mai stato scritto, il design non è stato realizzato |
| `docs/bench/cycle-71-sampling-stub.md` | **MORTO** | verbale datato 15/05: dichiara «Run: `python scripts/bench_c71_sampling_consolidate.py`», comando sparito. Non inganna — porta la data — ma non si può rieseguire |
| `docs/cycle156_unique_index_cross_process_design.md` | **MORTO** | riga 136: «Step 1 — write failing tests first (~30 righe `tests/test_consolidation_cross_process.py`)»: piano mai realizzato |
| `docs/ricerca/2026-09-02-roadmap-estratto-grezzo.md` | **VIVO** | la tabella elenca `tests/test_llm_providers.py` in colonna «new»: sono test **da creare**, non dichiarati esistenti |
| `docs/archive/2026-05-13_QA_AUDIT.md` | **MORTO** | piano di QA del 13/05 archiviato: la tabella elenca test da scrivere con la copertura «da → a». Mai scritti |
| `docs/archive/2026-05-13_BENCH_VALIDATION.md` | **MORTO** | riga 221: «**Aggiungere** uno script `scripts/bench_active_memory.py`» — proposta archiviata. Cita anche una chiave API esterna e un costo in dollari: superato |
| `docs/stato-reale/i-28-rossi-classificati.md` | **VIVO** | cita `benchmark/lme_retrieval_bench.py` **dentro** la citazione di un marcatore che dice «non esiste nel repo»: racconta l'assenza |


## 🔑 Tre forme che l'indizio non distingue, e che cambiano il verdetto

Leggendo i primi dieci sono uscite tre forme diverse di «nomina un file che non
esiste», e **solo la prima contraddice il codice**:

1. **La ricetta** — dice al lettore *«esegui questo comando»*, e il comando non c'è.
   Chi la segue sbatte contro un errore: **CONTRADDICE IL CODICE**.
2. **Il piano** — elenca file *da scrivere* (« write failing tests first», colonna
   «new», «Aggiungere uno script»). Non afferma che esistano: se non sono mai stati
   scritti il documento è **MORTO**, non bugiardo.
3. **Il racconto** — nomina un file *dicendo* che è stato rimosso, o citando chi lo
   diceva. È **VIVO**, e spesso è il documento più preciso del mucchio.

⇒ Il conteggio «13 documenti nominano un path inesistente» **non è** «13 documenti
sbagliati»: dei primi dieci letti, **uno solo** è una ricetta rotta.

## Quello che gli indizi dicono di tutti e 287

```
  documenti totali                                 287
  citati da README, CHANGELOG, codice, test o
    da un altro documento                          187
  che nominano un path .py INESISTENTE              13   <- la coda dei candidati
     di cui «probabile racconto» (triage)            5
     di cui «probabile affermazione»                18   (un documento puo' averne piu' d'uno)
```
Dove stanno: `docs/stato-reale/` **164** · `docs/` (radice) ~67 · `docs/ricerca/` 16 ·
`docs/archive/` 11 (tutti citati) · `docs/sota/` 9 · `docs/specs/` 8 · il resto sparso.

## Contatore

**Classificati con verdetto letto: 10 su 287.** Con gli indizi raccolti: 287 su 287.
Triati sui path rotti: 13 su 13, e **dei dieci letti uno solo contraddice davvero**.
*Il numero che conta è il primo: gli indizi non sono un verdetto, e non li conto come tale.*
