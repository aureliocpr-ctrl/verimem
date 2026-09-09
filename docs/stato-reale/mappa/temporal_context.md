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
