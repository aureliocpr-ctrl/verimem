# DESIGN — pre-filtro a soggetto per il conflict-gate (ESC stage B, proposta)

**Stato: PROPOSTA misurata, NON cablata.** Decisione richiesta ad Aurelio.
Data 2026-07-21 · misure riproducibili (probe in sessione, numeri sotto) ·
contesto architetturale: review GLM-5.2 "Entity-Slot Consistency" (fact
`9068f627749b`), root-cause L3-semantic (fact `c5db422751d0`).

## Problema (misurato, non asserito)

Il conflict-gate L3-semantic confronta il fatto nuovo con i vicini di topic via
pre-filtro coseno (`min_cosine=0.7`) e giudice NLI locale (DeBERTa-MNLI).

* **Il pre-filtro è inerte**: su un corpus KB di 35 fatti, **595/595 coppie**
  superano 0.7 (minimo osservato 0.712, media 0.772). L'NLI riceve TUTTO.
* **Nessuna soglia separa**: i conflitti veri difficili stanno a coseno
  0.80–0.87 (caso A del banco); a 0.9 il recall di A crolla 1.00 → 0.00.
* **L'NLI sovra-predice** CONTRADICTION su coppie di soggetto diverso
  (out-of-distribution: MNLI ha l'ipotesi *about* la premessa).

## Proposta: chiave-soggetto per-fatto + policy di confronto

1. **A write-time, per-fatto (O(n), cacheabile)**: estrai il SOGGETTO della
   proposizione con estrattore two-tier offline:
   * tier 1 — euristica leading-NP (zero dipendenze, deterministica);
   * tier 2 — fallback Qwen2.5-1.5B-Instruct locale (già in cache HF) sui casi
     in cui il tier 1 non estrae.
2. **Policy di confronto (pre-filtro al posto del coseno)**: una coppia va al
   giudice NLI solo se i soggetti combaciano; soggetto vuoto o pronome =
   wildcard → **passa al giudice** (fail-open verso il giudizio, mai verso il
   blocco).

## Numeri (probe 2026-07-21, asset locali, zero download)

| misura | risultato |
|---|---|
| baseline `extract_entities_lite` (soggetti trovati) | **2/35** |
| euristica tier-1 su fatti KB | **35/35** corretti |
| euristica tier-1 su testo wild (squad/snli) | 42% / 34% → **wildcard = degrado sicuro** |
| fallback tier-2 Qwen sui NO-SUBJ squad | **19/20**, 1.1 s/frase CPU |
| banco pre-esistente: conflitti veri A/B/C/D che passano | **14/14** (wildcard salva i pronomi) |
| coppie F* (FP contestate) che arrivano all'NLI | **0/4** |
| caso E bloccato | 1/4 (gold non-conflitto → costo zero) |
| coppia Rossi (contraddizione vera del prodotto) | **passa** |
| coppie del corpus 35-fatti inviate al giudice | **7/595 (1%)** vs 100% oggi |
| alternativa reranker bge-v2-m3 | **falsificata**: A≈0.004 < F*≈0.016 |

## Limiti onesti (perché NON è cablata oggi)

* **Matcher lasco**: overlap di token fa combaciare "payments team" ↔ "design
  team" (testa comune). Serve head-noun matching, da tarare **con gold**.
* **Accuratezza tier-2 non certificata**: 19/20 è copertura, non correttezza
  (1 errore netto osservato). Il gold esterno è il treebank **UD English-EWT**
  (soggetti annotati, zero nostre etichette) — download da autorizzare.
* **Etichette F\***: contestate dai critic (F3 probabilmente conflitto vero).
  La policy però non decide il verdetto: **decide solo cosa vede il giudice**;
  un F3 bloccato dal pre-filtro è il rischio da quantificare con la eval
  Wikidata (triple reali, mutazione meccanica di uno slot).
* Il coseno resta per il recall semantico; qui si parla SOLO del conflict-gate.

## Percorso di ship (se approvato)

1. Gold UD → accuracy tier-1/tier-2 misurata, head-noun matcher tarato.
2. Eval Wikidata anti-circolarità (mutazioni = conflitti veri; coppie negative).
3. Wiring observe-first dietro env (`ENGRAM_SUBJECT_PREFILTER=observe`),
   ricevuta col layer `-observe` (convenzione già in uso).
4. Critic pre-commit + full suite + bench HaluMem prima/dopo.

---

## AGGIORNAMENTO 2026-07-21 notte — DECISIONE CONVERGENTE (mandato Aurelio: design delegato, "la cosa più completa e tecnicamente migliore")

Metodo: la mia posizione depositata PRIMA di leggere i critici
(`scratchpad/my_design_position.md`), poi diff col verdetto GLM-5.2
indipendente. Convergenza su tutti e 5 gli assi. Kimi-k3: 4 timeout su 4
(moonshot irraggiungibile stanotte) — consultato, non disponibile.

### Decisione (impegni, non opzioni)
1. **Target**: clean-admission ≥90% (floor; 95 aspirazionale) CON
   noise-rejection ≥95% su HaluMem A/B; verticale wrong-block ≤3%;
   non-regressione: banco caso-A 8/8, Rossi catturata, injection 0, confab 0.
2. **CE grounding → AMMISSIONE GRADUATA** (passo 1, massimo guadagno):
   sotto-soglia con source dichiarata → ammetti come `model_claim` con
   `grounding_confidence: low` sulla ricevuta; quarantena riservata a
   injection / contraddizione attiva / evidenza che CONTRADDICE.
   Falsificatore verificato: al cut shippato (40) clean-admission = 66.7%
   (40/60) con noise-rejection 100% → il sovra-rigetto è reale, non taratura.
   «La moat vive nello spazio di lettura, non di scrittura» (GLM).
3. **L3-semantic → subject pre-filter** con matcher **head-noun + modifier
   agreement** (head diverso → scarta; head uguale → i modifier devono
   concordare: "payments team" vs "design team" NON matcha). Observe-first.
   Gold UD scaricato e attivo: tier-1 iter-1 wrong 20.7% wild / 0% KB.
4. **L1 keywords → advisory-by-default CON marker** (il marker esiste,
   `bf35c9b`) + `ENGRAM_L1_STRICT` per deployment agentici. Differenza dal
   flip regredito d15e4ca: tracciabilità completa + suite riscritta
   deliberatamente + L3/L4/injection fail-closed intatti. `source_type`
   scartato (spoofabile a livello API — refutazione GLM della sua stessa
   proposta precedente).
5. **Ordine**: CE graded (1) → head-noun L3 (2) → L1 advisory default (3).
   Ogni passo: TDD + observe + bench prima/dopo + critic pre-commit + suite.

### Failure-mode PRE-REGISTRATO (GLM, punto 6)
Se il read-path non PESA i fatti `grounding_confidence: low`, l'ammissione
graduata sposta i FP dalla scrittura alla risposta. **Obbligatorio prima di
dichiarare vinto il passo 1**: A/B sul read-path con fatti low-conf iniettati
(confab-rate e astensione devono restare 0 / corrette).
