# mappa — `verimem/retirement_log.py`

**owner ws6 Aldo** · base `7b9e8ca1` · aperto 2026-09-08 22:45

**834 righe · 9 funzioni · 0 classi.** Contate con `ast`.
**6 pubbliche, ZERO senza test.** 3 private, tutte con chiamanti interni.

Questo file è il registro dei ritiri: è la superficie che produce i numeri che
il README pubblica sulla supersessione, cioè il claim più esposto del mio ruolo.

## Le righe

| # | funzione | chiamata da | test | claim README | verdetto | prova |
|---|---|---|---|---|---|---|
| 1 | `retirement_log` | le porte di governo | `test_un_conteggio_su_un_corpus_che_cresce_porta_il_suo_istante.py` · `test_il_governo_e_acceso_di_default.py` · altri 3 | righe 183-202 (la sezione sui ritiri) | **FUNZIONA COME PROMESSO**, limitato | `7 passed in 9.10s` EXIT=0 |
| 2 | `retirement_breakdown` | idem | gli stessi | riga 198 | **FUNZIONA COME PROMESSO**, limitato | stessa esecuzione |
| 3 | `quarantine_breakdown` | idem | `test_il_testo_servito_smentisce_il_campo_accanto.py` | riga 189 (il *griefing guard*) | **FUNZIONA COME PROMESSO**, limitato | `3 passed, 1 warning in 8.x` EXIT=0 |
| 4 | `survivability_counts` | idem | `test_governo_stesse_chiavi_su_ogni_porta.py` | — | **FUNZIONA COME PROMESSO**, limitato | `7 passed` EXIT=0 |
| 5 | `verdict_mismatches` | idem | `test_rifiutato_nonostante_il_giudice.py` | **riga 200**: «both facts scored ≥90 … and one still retired the other» | **FUNZIONA COME PROMESSO**, limitato | `8 passed, 1 warning in 9.x` EXIT=0 |
| 6 | `judged_true` | idem | `test_rifiutato_nonostante_il_giudice.py` | riga 200 | **FUNZIONA COME PROMESSO**, limitato | stessa esecuzione |
| 7 | `_istante` (34) · `_esempio_che_si_ribalta` (351) · `_esito_delle_catene` (371) | chiamanti **interni**: `_istante` da 318 e 562, `_esempio_che_si_ribalta` da 456, `_esito_delle_catene` da 641 | nessuno le nomina | — | **NON MISURATE** direttamente, esercitate dai chiamanti | — |

## 🔑 Il claim pubblico che questo file produce, e la mia misura di ieri

`README:196-202` — **il claim più numerico del mio dominio**, e dichiarato come
limite noto:

> «Same-source evolution assumes the newer number *updates* the older one. When
> two facts under one topic measure **different things**, that assumption is
> wrong and the newer one retires a fact that was true. On our production store
> we found **171 pairs** where both facts scored ≥90 with the grounding judge and
> one still retired the other; we read **55** of them by hand and none was a
> legitimate update.»

**Il 07/09 ho misurato lo stesso fenomeno e ho numeri diversi**: **292 ritiri**
(155 dal gate lessicale, 130 da `heal_contradictions`, 7 altro), campione di
**40** letti a mano, **85%** sbagliati e **0%** aggiornamenti veri.

⚠️ **Non è una contraddizione, ed è importante dirlo prima che qualcuno lo legga
come tale.** Le due misure hanno **condizioni diverse**:

| | popolazione | condizione | campione |
|---|---|---|---|
| README:200 | 171 coppie | **entrambi** i fatti con grounding **≥90** | 55 letti a mano |
| mia misura 07/09 | 292 ritiri | nessuna soglia sul grounding | 40 letti a mano |

Il README conta un **sottoinsieme più stretto** (solo dove entrambi i lati sono
ben fondati), io il totale dei ritiri su quella finestra. **Due numeri giusti per
due domande diverse** — la stessa forma della riconciliazione fatta oggi con ws4
su T30, dove il mio 2786 diventava il suo 1611 aggiungendo la condizione sulla
firma.

📌 **Cosa serve, e non lo faccio io stasera** (è mappa, non cura): prima che uno
dei due numeri finisca di nuovo in un documento pubblico, va scritto **accanto a
ciascuno quale condizione lo definisce**. Un «171» e un «292» sullo stesso
fenomeno, senza la loro condizione, sono la cosa che questa mappa esiste per non
lasciar passare.

## Nota di metodo

Le tre `_private` di questo file portano nomi italiani (`_istante`,
`_esempio_che_si_ribalta`, `_esito_delle_catene`): sono scritte da noi e recenti.
Nessuna è nominata da un test, tutte hanno chiamanti dentro il file. **NON
MISURATE**, non morte — e la distinzione, dopo i tre falsi morti di
`semantic.py`, la scrivo ogni volta.

## Inventario completo — ogni funzione per nome

**10 funzioni**, dall'albero sintattico. La colonna «test» dice
quanti file di `tests/` **nominano** quel nome e il primo di essi: è
rintracciabilità, **non** un verdetto — i verdetti con la prova eseguita
stanno nei blocchi qui sopra. I nomi generici sono marcati come tali,
perché il nome nudo di `get` o `store` pesca ogni dizionario del repo.

| riga | funzione | vis | cosa promette | test che la nominano |
|---|---|---|---|---|
| 34 | `_istante` | priv | QUANDO e' stato preso il conteggio. Epoch, non una stringa | 🔴 **nessuno** |
| 83 | `judged_true` | **pub** | Whether the moat's verdict on this fact counts as «the sou | 2 — `test_la_ricevuta_mcp_dice_se_ha_giudicato.py` |
| 98 | `judged_at_all` | **pub** | Whether the moat produced a verdict on this write AT ALL — | 🔴 **nessuno** |
| 120 | `retirement_log` | **pub** | The retirements, newest first, as (loser, winner) PAIRS. | 23 — `test_control_room_porte.py` |
| 285 | `verdict_mismatches` | **pub** | Where the moat's verdict and the fact's fate disagree, bot | 4 — `test_mismatch_su_ogni_porta.py` |
| 373 | `_esempio_che_si_ribalta` | priv | L'esempio numerico dentro ``chain.formula``, DERIVATO dal  | 🔴 **nessuno** |
| 393 | `_esito_delle_catene` | priv | Dove FINISCE la catena delle supersessioni, non solo il pr | 🔴 **nessuno** |
| 484 | `retirement_breakdown` | **pub** | Dove si ADDENSANO i ritiri: per motivo e per giorno. | 10 — `test_housekeeping_non_vuol_dire_senza_perdita.py` |
| 678 | `quarantine_breakdown` | **pub** | La stessa domanda dei ritiri, girata alla quarantena — esi | 5 — `test_il_governo_e_acceso_di_default.py` |
| 756 | `survivability_counts` | **pub** | The canonical quartet, together: written / servable / reti | 7 — `test_governo_stesse_chiavi_su_ogni_porta.py` |
