# `README.md` riga per riga — claim → codice → presidio → verdetto

> **@ws7 Iris**, mandato di Aurelio dell'08/09 20:33 («tutta la superficie
> mappata»). Base: `origin/main` **`20257636`**, `README.md` = **811 righe**.
> **Il README è la pagina di PyPI** (`pyproject.toml`: `readme = "README.md"`),
> quindi ogni riga qui è una promessa che un utente riceve.

## Come si legge una riga di questa tabella

| colonna | cosa contiene |
|---|---|
| **riga** | il numero di riga in `README.md` su `20257636` |
| **claim** | cosa promette a un utente — *prosa compresa*, non solo i comandi |
| **dove sta** | `file:riga` del codice che lo fa, o `—` se non c'è codice |
| **presidio** | il test che lo tiene fermo, o `—` |
| **verdetto** | **✅ FUNZIONA COME PROMESSO** · **❌ NON COME PROMESSO** · **⬜ NON MISURATO** |

⚠️ **`NON MISURATO` non è un'accusa e non è un'assoluzione**: dice che *da questa
mappa* non risulta né una prova né una smentita. È il verdetto più frequente e il
più utile: è la lista di cosa il prodotto promette **sulla fiducia**.

⚠️ **Cosa NON fa questa mappa**: non esegue il prodotto. Verifica che **il codice
esista** e che **un presidio lo nomini**. Un `✅` qui vuol dire *«la promessa ha
un'implementazione e qualcuno la guarda»*, non *«l'ho vista funzionare»* — quando
l'ho eseguita, la riga lo dice.

---

## Righe 1-30 — il banner e la frase di apertura

| riga | claim | dove sta | presidio | verdetto |
|---|---|---|---|---|
| 1 | il prodotto si chiama **Verimem** | `pyproject.toml:name` | `test_il_readme_insegna_il_nome_del_prodotto.py` | ✅ |
| 3 | `mcp-name: io.github.aureliocpr-ctrl/verimem` — l'identità sul registro MCP | `server.json` | `test_il_pacchetto_ha_cio_che_promettiamo.py` | ⬜ *(la coerenza col registro pubblico non è verificata da qui)* |
| 5 | «**la prima scrittura giudicata è lenta — e puoi spostare il costo**» | — *(è la tesi del blocco)* | `test_il_banner_in_cima_al_readme_non_puo_dire_che_il_moat_e_spento.py` | ✅ **il presidio esiste ed è acceso**: vieta la frase contraria in **tutto** il README (esteso da me l'08/09, RED→GREEN falsificato) |
| 7 | esiste il comando `verimem warmup` | `cli.py` | `test_i_comandi_che_il_readme_insegna_esistono.py` | ✅ **eseguito**: `python -m verimem.cli warmup --help` → `EXIT=0` |
| 9-10 | «**non sei obbligato a eseguirlo**: la prima `remember --source` si procura il giudice da sé» | `anti_confab_gate.py:2538` — `ensure_gate_model()` chiamata **fuori** da `warmup` | `test_ws5_giudice_si_procura_da_solo.py` | ✅ **il codice c'è e il commento accanto racconta il difetto curato** (`:2508`: *«era chiamata SOLO da `verimem warmup` (`cli.py:594`)»*) |
| 11-13 | la misura del **2026-09-06** sulla 0.7.6 pubblicata: **85,7 s**, `grounding_score 99.97`, `moat: judged 100.0` | — *(è una misura, non codice)* | `test_ws5_giudice_si_procura_da_solo.py` (registra la misura) | ⬜ **il numero non è ri-misurato da questa mappa**: la riga dichiara data, versione e condizioni, che è la forma giusta — ma nessun presidio lo rifà |
| 14-16 | il modello pesa **711 MB / 746 MB decimali**, **13-27 s** su una connessione normale, **nessun account** | — | `test_il_readme_e_la_cli_dicono_lo_stesso_peso.py` · `test_la_vetrina_nomina_i_modelli_che_scarica.py` | ✅ **sul peso** (il presidio confronta README e CLI) · ⬜ **sui 13-27 s** e sul «no account»: nessun presidio li tocca |
| 16-17 | dopo, «ogni scrittura è giudicata in **~0,2 s**, offline» | — | **nessuno** (`grep "0.2 s" tests/` → vuoto) | ⬜ **NON MISURATO** — e la mia misura del 07/09 sulla **prima** scrittura (22 s CLI) *non* riguarda questa riga, che parla delle **successive** |
| 19-22 | la nota storica: «questo riquadro diceva che il moat era OFF; era vero della **0.7.1**; la cura è entrata e il testo non l'ha seguita» | `anti_confab_gate.py:2508` (il commento) | `test_ws5_giudice_si_procura_da_solo.py` | ✅ **verificabile e verificata**: il file citato esiste, il codice citato esiste |
| 24-26 | 🔑 **la frase centrale**: «ogni scrittura passa un cancello di ammissione, ogni lettura porta la provenienza, e un claim che la fonte **apertamente contraddice** non torna come verità» | `anti_confab_gate.py` (gate) · `client.py:735` (la chiamata dalla porta) | `test_all_write_channels_judge_a_source.py` | ❌ **NON COME PROMESSO, e questo è il numero più duro che abbiamo**: dalla porta `Memory.add`, **6 self-claim su 7** preceduta da un fatto vero entrano `judged=True` con `grounding` 99,9x (banco `ws7-d1-dalla-porta-sdk.py`, 07/09). Chiamando il gate a mano sono **7/7 fermate**. ⚠️ E il presidio della parità **non poteva vederlo**: usa un giudice **finto** e verifica `judge.calls >= 1`, cioè che il canale *consulti*, non che l'esito sia giusto |
| 28-30 | «ogni cifra qui sotto viene da un banco in `docs/stato-reale/banchi/`, su fonti corte, dalla porta pubblica `remember --source`» | `docs/stato-reale/banchi/` (esiste, ~120 file) | **nessuno** | ⬜ **NON MISURATO come promessa universale**: nessun presidio verifica che *ogni* cifra del README abbia un banco. *È esattamente la classe che il 07/09 ho misurato a mano: su 52 identificatori della vetrina, uno non aveva codice sotto* |

---

## 📊 Contatore

```
righe lavorate:  30 / 811   (3,7%)
verdetti:  ✅ 5   ❌ 1   ⬜ 6   (una riga può portare due verdetti su due claim)
```

**Il primo ❌ è alla riga 24**, ed è la frase con cui il prodotto si presenta.
