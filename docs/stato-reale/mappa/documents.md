# mappa — `verimem/documents.py`

**owner ws6 Aldo** · base `20257636` · 2026-09-09 12:37

**332 righe · 13 funzioni · 2 classi** (`ast`). **8 pubbliche, 4 private.**
Metodo e limiti: quelli di `semantic.md`, con le quattro trappole del righello già pagate.

## Le righe

| gruppo | test | verdetto | prova |
|---|---|---|---|
| le **8 pubbliche** | `tests/test_documents_tier.py` | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_documents_tier.py` → `24 passed in 8.07s` EXIT=0 |
| le 4 `_private` | via i chiamanti | **NON MISURATE** direttamente | — |

**Zero pubbliche senza test.** `test_documents_tier.py` con 24 celle è il test
più denso incontrato su un file di questa dimensione.
