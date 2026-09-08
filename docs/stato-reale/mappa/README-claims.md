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

## Righe 31-90 — i numeri di punta: le due garanzie e i due dataset pubblici

| riga | claim | dove sta | presidio | verdetto |
|---|---|---|---|---|
| 32-37 | la tabella delle **contraddizioni ammesse come vere**: negazione **0/10 IT, 0/10 EN** · entità scambiata **1/10 IT, 2/10 EN** · inferenza **0/10 EN, 3/10 IT** · claim non menzionato **8/10 IT, 9/10 EN** | — *(numeri di banco)* | **nessuno** | ⬜ **NON MISURATO**: nessun test lega questi numeri a un file di risultati. *Sono i numeri che descrivono la prima garanzia del prodotto.* |
| 39-46 | i **tre limiti** accanto a quei numeri: **lunghezza** (un caso 9,6 → 35,9 contro un taglio di 40) · **scrittura** (ZH/JA come EN, KO 3, AR 5, HI 7, **Thai 10/10**) · **cifre** (con un numero **0/18** passa, senza **16/18** passa) | `docs/stato-reale/banchi/ws3-la-seconda-garanzia-fuori-da-it-en.py` — **il file esiste** | **nessuno** | ✅ **sul fatto che il banco citato esista** · ⬜ **sui numeri**: nessun presidio li rilegge. 🔑 **Ma la riga 46 è scritta come va scritta**: dice *«leggi quella riga come "quasi sempre fermato se c'è un numero, quasi mai se non c'è", non come 2 su 10"»* — **una media che dichiara di essere una media su due metà opposte** |
| 48-51 | i quattro **badge**: PyPI, CI, licenza AGPL-3.0, sito | — | `test_i_collegamenti_della_vetrina_reggono_fuori_dal_repository.py` | ✅ **sui link** *(che il badge PyPI mostri la versione giusta dipende da PyPI, non da noi)* |
| 53-57 | «i fatti sono ammessi da un cancello anti-confabulazione, conservati con le fonti, rivisti per **supersessione esplicita (mai sovrascritture silenziose)**, e risposti **con le citazioni** — o con un onesto *"non lo so"*» | `anti_confab_gate.py` · `supersession_policy.py` · `client.py` | `test_la_promessa_della_citazione_vale_su_ogni_superficie.py` | ⚠️ **verdetto SPEZZATO, e va spezzato**: ✅ sulla citazione (presidiata su ogni superficie) · ✅ sulla supersessione (`superseded_by`, verificato da @ws2 il 06/09 su entrambe le porte) · ❌ **sul cancello**, per la riga 24: dalla porta le self-claim in coda entrano giudicate |
| 59-66 | «**sul recupero siamo competitivi**»: LongMemEval_s **recall@5 = 0.87** (500 domande, senza giudice) · LoCoMo **QA-accuracy = 0.81** (n=150, giudice Claude) — dichiarati *«nostre run interne, non riprodotti da terzi, non il giudice GPT-4 delle classifiche pubbliche»* | `docs/BENCHMARKS.md` — **il file esiste** | **nessuno** *(il `grep` di `0.87` trova due test che parlano d'altro: omonimia, non presidio)* | ⬜ **NON MISURATO** · ✅ **sulla forma**: la riga **dichiara da sé** che non è un confronto alla pari, ed è la cosa più difficile da scrivere quando un numero fa gola |
| 68-77 | la tabella dei **due dataset pubblici**: TruthfulQA **15,9%** (40/252) con baseline cieca **51,3** · HaluEval **35,7%** (90/252) con baseline **70,8** | — | **nessuno** | ⬜ **NON MISURATO** — 🔑 **e sono i numeri più citabili della pagina**: se qualcuno li riprende, non abbiamo un test che dica che il README riporta ciò che il banco ha misurato |
| 78-86 | «**leggi la seconda colonna o non leggere la prima**»: la baseline cieca dice quanta parte del punteggio è raggiungibile **dalla forma** del claim, e per questo 35,7 e 15,9 **non** vanno letti come «siamo il doppio peggio su HaluEval» | — | **nessuno** | ✅ **come metodo, ed è la riga migliore della pagina**: mette accanto al numero la cosa che lo rende leggibile, invece che in appendice. ⬜ **come misura**: la baseline non è ri-verificata da un presidio |
| 88-90 | «**i due denominatori sono uguali per coincidenza, non per costruzione**»: 162+90 = 252 su HaluEval, 212+40 = 252 su TruthfulQA, da popolazioni di 600 e 400 | — | **nessuno** | ✅ **come metodo**: dichiarare che due numeri identici *non* significano la stessa cosa è esattamente ciò che impedisce a un lettore di dedurre un rapporto che non c'è |

### 📌 Il reperto di questo blocco

**Nessuno dei numeri di punta del README ha un presidio che lo leghi al suo
banco.** Il solo presidio di quel tipo — `test_la_tabella_metric_regge_le_sue_fonti.py`
— copre la **tabella «Metric»**, che sta altrove. ⇒ Se un banco cambia esito, il
README **non lo scopre da solo**: la sua correttezza dipende da chi si ricorda di
aggiornarlo. *È la stessa forma della nota del 26/08 sui numeri della release:
**una nota non è un presidio**, e oggi quella lezione è costata un numero
sbagliato a un passo dal tag.*

---

## 📊 Contatore

```
righe lavorate:  90 / 811   (11,1%)
verdetti:  ✅ 10   ❌ 2   ⬜ 12   (una riga può portare due verdetti su due claim)
```

**I due ❌ sono la riga 24 e la 53-57**, e sono **lo stesso difetto**: la frase con
cui il prodotto si presenta, e la sua ripetizione dodici righe sotto.

**Il ⬜ dominante non è pigrizia mia**: è che **i numeri di punta della pagina non
hanno un presidio**. Hanno i banchi — dichiarati, con il nome del file — ma
nessun test rilegge il README contro di essi.
