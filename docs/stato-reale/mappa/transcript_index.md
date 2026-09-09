# mappa — `verimem/transcript_index.py`

**owner ws6 Aldo** · base `20257636` · 2026-09-09 12:26

**340 righe · 13 funzioni · 2 classi.** Contate con `ast`
(`scratchpad/inventario.py`), non con grep. **8 pubbliche, 4 private.**

Metodo e limiti: quelli dichiarati in `semantic.md`. Le quattro trappole già
pagate valgono anche qui — il nome con la parentesi non vede i **callback**;
escludere il file stesso fa sembrare morti gli helper; cercare solo in
`verimem/` e `tests/` dimentica `benchmark/`; il nome nudo dei metodi generici
pesca ogni dizionario.

## Le righe

| gruppo | test | verdetto | prova |
|---|---|---|---|
| `default_db_path` · `recall_report` e le altre 6 pubbliche | `tests/test_transcript_index_isolation.py` · `tests/test_il_tier_vuoto_non_e_nessun_risultato.py` | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_transcript_index_isolation.py` → `7 passed in 7.25s` EXIT=0 · `test_il_tier_vuoto_non_e_nessun_risultato.py` → `5 passed in 6.93s` EXIT=0 |
| le 4 `_private` | via i chiamanti | **NON MISURATE** direttamente | — |

## ⚠️ Qui il righello è inutilizzabile, e va detto

Le pubbliche di questo file si chiamano `count`, `get`, `recall`, `store`,
`prune`. Cercarle col nome nudo in `tests/` dà:

```
get     635 file        store   665 file        recall  398 file
count   204 file        prune    12 file
default_db_path  2      recall_report  1
```

⇒ Il conteggio automatico diceva «0 pubbliche senza test» ed era **vero per
caso**: `get` e `store` pescano ogni dizionario e ogni store del repo. Sono i
**nomi specifici** (`default_db_path`, `recall_report`) ad aver portato al test
vero, `test_transcript_index_isolation.py`, che il conteggio non aveva
nominato.

📌 È la quarta forma della trappola del righello, e questo file è il caso più
estremo che ho incontrato: **il 100% delle pubbliche “coperte” con un metodo che
su cinque nomi su otto non misura niente.**

## Inventario completo — ogni funzione per nome

**12 funzioni**, dall'albero sintattico. La colonna «test» dice
quanti file di `tests/` **nominano** quel nome e il primo di essi: è
rintracciabilità, **non** un verdetto — i verdetti con la prova eseguita
stanno nei blocchi qui sopra. I nomi generici sono marcati come tali,
perché il nome nudo di `get` o `store` pesca ogni dizionario del repo.

| riga | funzione | vis | cosa promette | test che la nominano |
|---|---|---|---|---|
| 66 | `default_db_path` | **pub** | Path di default del Tier C — DB dedicato, separato da ``CO | 2 — `test_documents_tier.py` |
| 109 | `_connect` | priv |  | 47 — `test_bridge.py` |
| 114 | `_init_db` | priv |  | 🔴 **nessuno** |
| 123 | `store` | **pub** | Persisti un turno. Stampa SEMPRE embedding_model + confide | _generico — cercato qualificato nei blocchi sopra_ |
| 141 | `store_batch` | **pub** | Persisti molti turni in un colpo (encode batch per velocit | 6 — `test_episode_batch_screen.py` |
| 172 | `_load_rows` | priv |  | 🔴 **nessuno** |
| 196 | `recall` | **pub** | Recall semantico SUL SOLO Tier C (pull-only). Ritorna ``[( | _generico — cercato qualificato nei blocchi sopra_ |
| 221 | `recall_report` | **pub** | Come :meth:`recall`, ma dice ANCHE se c'era qualcosa da ce | 1 — `test_il_tier_vuoto_non_e_nessun_risultato.py` |
| 261 | `get` | **pub** | Recupera un turno per id (usato da promozione / ispezione) | _generico — cercato qualificato nei blocchi sopra_ |
| 274 | `count` | **pub** |  | _generico — cercato qualificato nei blocchi sopra_ |
| 285 | `prune` | **pub** | Retention: cancella turni per cap (``max_turns``, tiene i  | _generico — cercato qualificato nei blocchi sopra_ |
| 324 | `_row_to_turn` | priv |  | 🔴 **nessuno** |

## Le classi di questo file — 2 sulla superficie

Il righello del lead conta le **classi** nel denominatore (480 sui miei 21 file
contro i 449 di sole funzioni): una classe e' superficie, e finche' non e'
nominata qui non e' mappata. Stesso patto dell'inventario sopra: la colonna
«test» dice quanti file di `tests/` **nominano** quel nome — rintracciabilita',
non un verdetto.

| riga | classe | metodi | cosa promette | test che la nominano |
|---|---|---|---|---|
| 52 | `Turn` | 0 | Un turno di conversazione grezzo (verbatim). | _generico — cercato qualificato nei blocchi sopra_ |
| 101 | `TranscriptIndex` | 12 | Indice isolato e low-trust del transcript grezzo. Pull-only. | 10 — `test_conversational_not_laundered.py` |

## I metodi speciali di questo file — 1

In tabella come tutto il resto: il righello legge la seconda colonna, e in prosa
questi undici (su tutti i file) restavano fuori dal conto. Sono costruttori e
accessori di protocollo: non hanno un claim del README ne' un test proprio, e
sono esercitati da **ogni** uso della loro classe — il verdetto e' quello dei
blocchi sopra, non una riga a se'.

| riga | metodo | classe | cosa fa | verdetto |
|---|---|---|---|---|
| 104 | `__init__` | `TranscriptIndex` | costruisce l'oggetto (apre la connessione, fissa i path) | esercitato da ogni uso di `TranscriptIndex` nei blocchi sopra |
