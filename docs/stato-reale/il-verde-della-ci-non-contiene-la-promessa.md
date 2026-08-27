# Il verde della CI non contiene la verifica della promessa centrale

> ## ⏱️ RIVERIFICATO IL 27/08, sedici giorni dopo — e il cuore è stato CURATO
>
> Questo documento è rimasto **fuori dal repo per sedici giorni**: file nuovo in `docs/`,
> mai `git add`-ato, e `git commit -F- -- <path>` su un file non tracciato **non lo
> include e non protesta**. Segnalato da un'altra sessione il 27/08. Prima di committarlo
> ho riverificato ogni fonte, perché un documento vecchio che entra nel repo senza data
> **autorizza** conclusioni scadute.
>
> **③ NON VALE PIÙ, ed è la tesi centrale.** Al 11/08 la CI warmava con `--no-gate` e i 24
> test del moat non venivano eseguiti mai. Oggi `.github/workflows/ci.yml:357` esegue
> **`verimem warmup --no-daemon`** — *senza* `--no-gate` — e il commento accanto dichiara
> l'intento: «Scaldare il gate PRIMA dei test rende il verdetto indipendente dall'ordine.»
> ⇒ **Il gate CE viene scaricato e quei test girano.** Il buco che questo documento
> misurava è stato chiuso da qualcun altro, e va detto prima di tutto il resto.
>
> **⚠️ MA IL RESIDUO NON È CHIUSO, ed è la forma peggiore.** Quello step porta
> `continue-on-error: true`, e il commento lo dichiara: «se il download cade, i test del
> moat tornano a saltare o a fallire». La condizione di skip
> (`tests/conftest.py:588-596`) dipende da `real_ce_cached()`. ⇒ **Il giorno in cui il
> download del gate fallisce, i 24 test tornano a non girare — e non compaiono come
> rossi, compaiono come niente.** Uno step non-fatale che fallisce lascia un verde che
> non contiene ciò che sembra contenere: è lo stesso difetto di prima, con un innesco
> diverso e più raro.
>
> **① ② ④ REGGONO** al 27/08: `_CE_MOAT_TESTS` è ancora in `tests/conftest.py:550`;
> `tests/test_le_promesse_valgono_appena_installato.py` esiste e ha ancora **8 test**;
> `build:` ha ancora `needs: test` (riga 955), quindi la catena seriale è intatta.
>
> Il testo sotto è quello dell'11/08, **non riscritto**: si legge con questa nota davanti.

**ws8 Vedetta — 11/08/2026, 19:26→20:00. Sola lettura su `origin/main` (`f728a5eb`).**
Metodo: statico — `git show` su ref, nessuna suite, nessun giudice, nessun embedder caricato,
nessun commit, nessun file del package modificato. Unica esecuzione: il predicato
`local_ce_available()`, che per proprio docstring **«never loads the model»**.
*(L'unica scrittura è questo documento: un file nuovo in `docs/`, non tracciato, che non entra in
nessuna build. Lo dichiaro perché la prima stesura di questa riga diceva «working tree mai toccato»
ed era falsa nel momento in cui la scrivevo.)*

---

## ⚠️ Prima di tutto: questo NON è un finding nuovo, ed è giusto dirlo per primo

Che la CI non eserciti il moat **è già scritto nel codice, in due punti indipendenti**:

* `verimem/cli.py:334` — *«`--no-gate` skips it (e.g. **CI that doesn't exercise the moat**).»*
* `tests/_real_model.py:47` — *«**CI warms with `--no-gate`** (it historically "doesn't exercise
  the moat"), so CE-moat tests **must skip there**.»*

Il mio contributo non è la scoperta. È **il numero, la sua composizione, e il collegamento col
cancello del rilascio** — tre cose che non risultano scritte da nessuna parte.

---

## ① QUANTI SONO, e sono due gruppi disgiunti (non uno)

**Gruppo A — 16 test, skip esplicito da `tests/conftest.py:541-587`** (lista `_CE_MOAT_TESTS`):

| file | test |
|---|---|
| `test_abstention_hybrid.py` | 2 |
| `test_answer_judge_stage.py` | 6 |
| `test_band_escalation.py` | 3 |
| `test_graded_admission_supersession.py` | 5 |

Non è periferia: è **il cuore decisionale del moat** — astensione ibrida, answer-judge, escalation
di banda, ammissione graduata.

**Gruppo B — 8 test, `tests/test_le_promesse_valgono_appena_installato.py`**, che si spengono da
soli perché la fixture `appena_installato` fa `pytest.skip(...)` quando il CE non è in cache
(righe 54-58). **Questi 8 NON sono nella lista dei 16**: i quattro file del gruppo A sono altri.
⇒ **Chi legge `_CE_MOAT_TESTS` crede che i test spenti siano 16. Sono 24.**

## ② E il gruppo B è quello che pesa di più — lo dichiara il file stesso

Il primo test si chiama `test_una_scrittura_con_fonte_viene_GIUDICATA_senza_chiedere_nulla`, e il
suo docstring dice:

> *«Se questo diventa rosso, il moat è tornato a non girare di default — **ed è la promessa su cui
> poggia tutto il resto del prodotto**.»*

Il file nasce da una frase di Aurelio del 01/08 (*«il sistema deve essere fatto in modo da
funzionare dall'installazione, inutile altrimenti»*) e verifica le promesse del README a data dir
vergine, **zero flag, zero env**. Gli altri sette coprono ritiro del valore vecchio, astensione del
dossier, risposta con evidenza, esattezza della citazione documentale, interrogazione del passato.

🔑 **E la riga più dura è nel file, non nel mio referto** (riga 52):
> *«Scritto il limite e non applicato: **la stessa distanza fra promessa ed esecuzione che questo
> banco esiste per misurare**.»*
⇒ **Il banco aveva già misurato sé stesso. Il risultato non è stato letto da nessuno.**

## ③ ✅ CONTROLLO POSITIVO — l'asimmetria è reale, non ipotizzata

`local_ce_available()` sulla macchina di sviluppo → **`True`**.
⇒ **In locale questi 24 test GIRANO e si vedono verdi. In CI non vengono eseguiti mai.**
La condizione è certa e non stimata: `verimem warmup` scarica il gate CE **solo senza `--no-gate`**
(`_real_model.py:47`), e `.github/workflows/ci.yml` warma **con** `--no-gate`.
⇒ Chi sviluppa non vede la differenza; la vede solo chi guarda la CI, e lì i test **non compaiono
come rossi: compaiono come niente.**

## ④ 🎯 IL COLLEGAMENTO COL CANCELLO DEL RILASCIO — ed è il pezzo per cui l'ho misurato

Stamattina (referto `60c3ec0b2e125df9`, non ancora replicato da nessuna) ho misurato che il
rilascio è una **catena seriale**: `build: needs: test` (riga 132 di `ci.yml`) e
`wheel-install: needs: build` (riga 159) ⇒ `build` parte **solo** se `test` è interamente verde.

Mettendo insieme le due cose:

> **Il cancello del rilascio si apre su un `test` verde che — per costruzione, non per caso — non
> contiene la verifica che il moat giri di default.**

⇒ Non è «la CI è rossa quindi non pubblichiamo». È che **il giorno in cui diventerà verde, quel
verde non dirà ciò che sembra dire**: dirà che 10.000 test passano, e tacerà sui 24 che
verificano la promessa scritta in cima al README.

## ⑤ ⚠️ LIMITI, dichiarati

* **Non propongo di togliere `--no-gate` dalla CI.** Scaricare il gate CE su sei gambe di matrice
  ha un costo, e la gamba Windows è già a 39:41 dentro un cap di 45 (misura di ws7,
  `0cdabf1b6e03e7ae`). Chi decide è Aurelio: qui c'è il costo di **non** farlo, non la cura.
* **Non ho eseguito la suite** né i 24 test: leggo la condizione di skip e il predicato che la
  governa, non l'esito. Il livello della mia misura è **la configurazione**, non l'esecuzione — e
  lo dichiaro perché in casa il livello a cui si misura ha già ribaltato cinque verdetti.
* **Gli altri 5 file** che dipendono dal solo modello di embedding (22 test) **non li conto fra i
  24**: il warmup CI scarica l'embedder, quindi con ogni probabilità girano. Non l'ho verificato.
* **Non ho misurato** se qualche altro test eserciti il moat per vie diverse (stub, mock, fixture
  proprie). Il mio conteggio è dei test che dipendono **esplicitamente** dal gate CE reale. Se
  qualcuno lo esercita altrimenti, il mio 24 è un limite inferiore sul buco, non la sua misura.

---

**Fonti citate, tutte da `origin/main`:** `tests/conftest.py:531-587` · `tests/_real_model.py:42-70` ·
`tests/test_le_promesse_valgono_appena_installato.py:1-120` · `verimem/cli.py:332-334` ·
`verimem/llm.py:1629-1631` · `.github/workflows/ci.yml:129-159`.
