# `verimem/skill_semantic_dedup.py`

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 QA (QA) · **08/09**.

## La catena: modulo → tool MCP → test

Misurata per tutti e 47 i moduli `skill*` in un colpo solo
(`catena_skill.py`): il nome del tool si legge dal ramo del
dispatcher (`if name == "hippo_…":` in `mcp_server.py`), **non**
da una funzione `tool_*` — quelle non esistono, e cercarle dava
**0 tool su 47** mentre 43 moduli erano importati.

⛔ **NESSUN CHIAMANTE NEL PRODOTTO.** Il righello non trova né un
tool MCP né un'altra porta; l'unica occorrenza del nome in
`verimem/` è un **commento** (`skill_name_dedup.py:19`).

Ha però un file di test dedicato (`tests/test_skill_semantic_dedup.py`): ⇒ **testato e non usato**, e la
suite verde fa credere che il prodotto lo esegua.

📎 Non è nuovo: `docs/MCP_DEAD_SURFACE_AUDIT_2026-05-17.md` — un
audit di quattro mesi fa — misurava «207 tool dichiarati, 83
usati almeno una volta (40%)» e già lo elencava.

**Verdetto: MAI CHIAMATA** per le sue funzioni pubbliche.
Propongo la rimozione **oppure** il cablaggio a un tool; non
decido io e non lo tocco (regola 2 del mandato).

## La tabella

⚠️ Bozza da `scripts/mappa_bozza.py`: la colonna «chiamata da» viene
da `git grep` **per nome**, e nel progetto **589 funzioni su 2.973
(19,8%) condividono il nome** con un'altra. Le righe con un omonimo
plausibile vanno lette prima di essere usate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/skill_semantic_dedup.py:64` `load_skills_with_embeddings` | funzione: Join ``SkillLibrary.all()`` with the persisted ``trigger_embedding``. | `verimem/skill_semantic_dedup.py:39`; `verimem/skill_semantic_dedup.py:152`; `verimem/skill_semantic_dedup.py:268` | `tests/test_skill_semantic_dedup.py` | - | NON MISURATO | - |
| 2 | `verimem/skill_semantic_dedup.py:96` `load_episode_reference_counts` | funzione: Count how many episodes reference each skill_id via skills_used JSON. | `verimem/skill_semantic_dedup.py:43`; `verimem/skill_semantic_dedup.py:154`; `verimem/skill_semantic_dedup.py:269` | nessuno | - | NON MISURATO | - |
| 3 | `verimem/skill_semantic_dedup.py:123` `_classify_pair` | funzione: Tag a duplicate pair by reference imbalance. | `verimem/skill_semantic_dedup.py:226` | nessuno | - | NON MISURATO | - |
| 4 | `verimem/skill_semantic_dedup.py:140` `find_semantic_duplicate_skills` | funzione: Find pairs of skills whose trigger embeddings are nearly identical. | `verimem/skill_semantic_dedup.py:47`; `verimem/skill_semantic_dedup.py:267` | `tests/test_skill_semantic_dedup.py` | - | NON MISURATO | - |
| 5 | `verimem/skill_semantic_dedup.py:260` `_fitness` | funzione: (nessun docstring) | `verimem/skill_semantic_dedup.py:211`; `verimem/skill_semantic_dedup.py:216`; `verimem/skill_semantic_dedup.py:217` (+1) | nessuno | - | NON MISURATO | - |

⚠️ **I verdetti di questa tabella NON sono ancora dati**: la catena
sopra dice che il modulo è raggiungibile e presidiato, **non** che
ogni sua funzione faccia ciò che promette. Per quello serve il banco
nel merito, che per questa famiglia **non ho ancora scritto** — e lo
dichiaro invece di lasciar credere che «catena completa» significhi
«funziona come promesso».

---

## Il banco nel merito: 11 promesse su 11 — **il modulo funziona, e nessuno lo chiama**

Il modulo è il reperto della famiglia (nessun chiamante nel prodotto), quindi la
domanda non è «funziona?» ma **«che cosa otterrebbe chi lo cablasse?»**. Prende
gli embedding già calcolati: banco puro, nessun modello, nessuno store.

```
── il sensore ──
OK  trova UNA coppia (a,b) e non tocca la ortogonale c        pairs=1
OK  e la coppia è proprio {a, b}                              estremi=['a','b']

── il classificatore, i tre casi dello «Honest scope» ──
OK  degenerate  (entrambe 0 riferimenti)         classification='degenerate'
OK  noise_clone (una sola a 0)                   classification='noise_clone'
OK    safe_to_retire nomina il perdente a 0      safe_to_retire='b'
OK  hot_clone   (entrambe usate)                 classification='hot_clone'
OK    safe_to_retire è None per un hot_clone     safe_to_retire=None

── i controlli che rendono leggibile il resto ──
OK  due skill ORTOGONALI non sono una coppia
OK  alzando la soglia a 0.999999 la coppia SPARISCE      ← la soglia MORDE
OK  una skill RITIRATA non forma coppie                  ← exclude_retired

11 casi · tutte le promesse reggono                                     EXIT=0
```

I due controlli in fondo sono quelli che rendono leggibile il resto: senza «la
soglia morde», un rilevatore che accoppia tutto avrebbe passato le prime prove a
pieni voti.

📌 E `safe_to_retire is None` per gli `hot_clone` è la promessa più delicata: il
docstring dichiara che quelle coppie «**cannot be deduped here**» e servono un
merge manuale. Il modulo **non propone di ritirare una skill viva**, ed è
esattamente ciò che deve fare un sensore read-only.

## Il paradosso, che vale più dei singoli verdetti

```
  skill_signature       cablato e usato   ·  ma la sua normalizzazione NON toglie
                                             la punteggiatura (T45), quindi manca
                                             i duplicati che differiscono per un punto
  skill_semantic_dedup  NON cablato       ·  ma fa tutto ciò che promette, 11 su 11 —
                                             ed è proprio quello che prenderebbe
                                             quei casi
```

🔑 **La rete contro i duplicati ha la maglia larga sul letterale e la maglia fine
non attaccata.** Nessuno dei due reperti, da solo, lo dice.

⇒ **verdetto: FUNZIONA COME PROMESSO** su tutte le funzioni provate; **MAI
CHIAMATA** resta il verdetto sulla sua raggiungibilità dal prodotto. Le due cose
convivono e vanno lette insieme. Nessuna cura (regola 2).

Banco: `<scratchpad>/banco_semantic_dedup.py`, 11 asserzioni, gira in un secondo.

🪞 **Un mio controllo era sbagliato** e lo tengo scritto: verificavo che la coppia
fosse `(a,b)` con `"c" not in str(coppia)` — una **sottostringa** cercata in una
`repr` che contiene la parola `classification`. La «c» c'era sempre. È la classe
degli id cercati come sottostringa: **si confrontano i campi, non il testo di un
dizionario**. Terza volta stasera che una scorciatoia sulla struttura dati
produce un rosso che non esiste.
