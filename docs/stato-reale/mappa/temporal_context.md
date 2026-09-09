# mappa — `verimem/temporal_context.py`

**owner ws6 Aldo** · base `20257636` · 2026-09-09 12:26

**597 righe · 14 funzioni · 0 classi.** Contate con `ast`
(`scratchpad/inventario.py`), non con grep. **9 pubbliche, 5 private.**

Metodo e limiti: quelli dichiarati in `semantic.md`. Le quattro trappole già
pagate valgono anche qui — il nome con la parentesi non vede i **callback**;
escludere il file stesso fa sembrare morti gli helper; cercare solo in
`verimem/` e `tests/` dimentica `benchmark/`; il nome nudo dei metodi generici
pesca ogni dizionario.

## Le righe

| gruppo | test | verdetto | prova |
|---|---|---|---|
| le **9 pubbliche** — `recall_as_of` e la famiglia del viaggio nel tempo | `tests/test_temporal_context.py` · `tests/test_il_routing_temporale_era_spento_di_default.py` | **FUNZIONA COME PROMESSO**, limitato a ciò che i test asseriscono | `pytest -q tests/test_temporal_context.py` → `6 passed, 1 warning in 8.x` EXIT=0 |
| le 5 `_private` | via i chiamanti | **NON MISURATE** direttamente | — |

**Zero pubbliche senza test.**

📌 È il file dietro `--as-of` e `recall_as_of`, cioè dietro il ticket che ho
curato il 07-08/09 (`ca5b7aa8`, la CLI che rispondeva col presente). La cura
stava in `cli.py`, non qui: questo file funzionava già, e la mappa lo conferma.

## Inventario completo — ogni funzione per nome

**14 funzioni**, dall'albero sintattico. La colonna «test» dice
quanti file di `tests/` **nominano** quel nome e il primo di essi: è
rintracciabilità, **non** un verdetto — i verdetti con la prova eseguita
stanno nei blocchi qui sopra. I nomi generici sono marcati come tali,
perché il nome nudo di `get` o `store` pesca ogni dizionario del repo.

| riga | funzione | vis | cosa promette | test che la nominano |
|---|---|---|---|---|
| 45 | `wants_history` | **pub** | Route a query to history-enriched recall iff its wording i | 2 — `test_il_routing_temporale_era_spento_di_default.py` |
| 53 | `_iso` | priv | Epoch → ISO date (UTC); empty string on anything unparseab | 3 — `test_cli_docs.py` |
| 99 | `_senza_accenti` | priv | `März` → `marz`, `août` → `aout`, `décembre` → `decembre`. | 🔴 **nessuno** |
| 132 | `extract_as_of` | **pub** | Data esplicitamente ancorata da una domanda retrospettiva  | 6 — `test_il_routing_temporale_era_spento_di_default.py` |
| 160 | `_event_ts` | priv | The fact's EVENT time (v13 ``asserted_at``, when it was sa | 🔴 **nessuno** |
| 168 | `fact_history` | **pub** | Predecessors of a live fact, most recent first — the main  | 2 — `test_la_storia_si_troncava_in_silenzio.py` |
| 188 | `history_line` | **pub** | Render one recall-context line: current value (+since date | 2 — `test_la_riga_di_recall_dice_se_e_verificato.py` |
| 218 | `stato_a` | **pub** | Che cos'era questo fatto all'istante ``when``: la SUPERFIC | 1 — `test_uno_stato_ignoto_non_e_uno_stato_debole.py` |
| 254 | `recall_as_of` | **pub** | Time-travel recall over the bi-temporal store: the facts t | 15 — `test_client_sdk.py` |
| 352 | `_died_event_ts` | priv | EVENT time a fact stopped being current: its successor's a | 🔴 **nessuno** |
| 375 | `recall_with_history` | **pub** | Live top-k recall, each hit enriched with its transition s | 5 — `test_due_tool_stessa_domanda_due_garanzie.py` |
| 508 | `date_menzionate` | **pub** | Le date di cui il testo PARLA, come ``{(anno, mese, giorno | 3 — `test_una_data_che_si_sposta_non_e_un_registro.py` |
| 575 | `_forma_programmata` | priv | True solo con una prova POSITIVA che la data è un appuntam | 🔴 **nessuno** |
| 585 | `stessa_frase_altra_data` | **pub** | Due frasi identiche tranne le date, ed entrambe un appunta | 1 — `test_una_data_che_si_sposta_non_e_un_registro.py` |
