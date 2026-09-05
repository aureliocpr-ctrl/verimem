# TICKET — la suite muore di SIGSEGV sempre nello stesso punto

> **Aperto da**: ws8 (Corrado, release manager). **Non è mio da curare**: tocca
> `verimem/_hang_watchdog.py` e il suo test. Qui ci sono i fatti misurati, una
> diagnosi dichiarata come ipotesi, e **l'esperimento che la falsifica** — che
> non posso eseguire io, e dico perché.

## 1 · I fatti, misurati su tre run

Finestra `2026-09-03 17:39 → 2026-09-04 19:54`, ultimi 60 run di `ci.yml`:

    run falliti esaminati:      10
    di cui morti di SIGSEGV:     3
    falliti per altro:           7

I tre, aperti uno per uno:

| run | commit | job | test iniziato e mai finito | PASSED prima |
|---|---|---|---|---|
| `#3102` | `75a768c6` | `test (ubuntu-latest / py3.12)` | `test_hang_watchdog.py::test_slow_body_leaves_a_stack_dump` | **3939** |
| `#3100` | `249a47ba` | `test (ubuntu-latest / py3.11)` | idem | **3939** |
| `#3089` | `fade02f0` | `test (ubuntu-latest / py3.12)` | idem | **3939** |

    Segmentation fault (core dumped) pytest -rsfE --cov=verimem ...
    ##[error]Process completed with exit code 139.

🔑 **`3939` in tutti e tre.** Tre commit diversi, due versioni di Python: il punto
non è casuale, è **deterministico**. Quello che varia è *se* capita, non *dove*.

Altri due fatti che restringono il campo:
- **solo `ubuntu`**. Nel `#3102` gli altri cinque job (windows, macos, le altre
  versioni) sono falliti **per altro**, non di segfault.
- **il file da solo passa**: nello stesso job la fase BIS rilancia
  `test_hang_watchdog.py` isolato e dà `9 passed in 64.25s`.

## 2 · Perché nessuno se n'era accorto

**`exit 139` non compare da nessuna parte nell'API**: né in `conclusion`, né
nei passi del job. Si legge **solo** scaricando il log del job
(`gh api repos/<R>/actions/jobs/<id>/logs`) e cercando `##[error]`. Nel `#3100`
stava alla riga **5131 di 5231**, e `gh run view --log-failed` restituiva righe
di setup.
⇒ Un rosso su tre veniva letto come «un test è fallito» quando il processo era
morto. **E un processo morto si porta via anche i 3939 verdi che aveva già
fatto**: del restante 70% della suite, in quei run, non sappiamo nulla.

## 3 · La diagnosi — è un'IPOTESI, e va falsificata

Il test fa questo (`tests/test_hang_watchdog.py:20`):

    with hw.hang_trace("slow_tool", budget_s=0.3):
        time.sleep(1.2)   # sfora il budget → il watchdog deve scattare

e il watchdog arma (`verimem/_hang_watchdog.py:97`):

    faulthandler.dump_traceback_later(budget_s, repeat=True, file=f)

`dump_traceback_later` cammina gli stack di **TUTTI i thread**, a livello C — e
il commento nel modulo lo dice già: *«il dump lo scrive faulthandler a livello C
e non si può interrompere da dentro»*.

Al punto in cui scatta, nel log dello stesso job, torch è già in gioco:

    Loading weights: 100%|██████████| 199/199 [00:00<00:00, 3561.14it/s]
    /opt/hostedtoolcache/Python/3.11.16/x64/lib/python3.11/site-packages/torch/jit/_script.py

e i test immediatamente precedenti sono `test_halumem_selector_v3` e
`test_halumem_updating_*` — cioè roba che carica modelli e apre thread pool.

**Ipotesi**: quando il timer scatta, faulthandler percorre anche i thread nativi
di torch/OpenMP; se uno di quelli è in uno stato che non può essere camminato, il
processo muore. Questo spiegherebbe tutte e quattro le osservazioni: il punto
sempre uguale (posizione deterministica nella suite), solo Linux (i thread pool
differiscono), il file da solo verde (nessun modello caricato), e il fatto che
non capiti sempre (una corsa fra il timer e ciò che i thread stanno facendo in
quel millisecondo).

⚠️ **È un'ipotesi.** Non ho eseguito nulla che la provi: quello che ho è la
coincidenza fra il punto del crash e la presenza di torch nello stesso processo.

## 4 · L'esperimento che la decide, e perché non lo eseguo io

**Su Linux**, nello stesso processo:

    python -c "import torch, sentence_transformers" && pytest tests/test_hang_watchdog.py -q

- se **crasha** → l'ipotesi regge, e la cura sta nel far girare quel test in un
  processo suo (`pytest-forked`, un marcatore, o l'isolamento che chi cura
  preferisce);
- se **passa** → l'ipotesi cade, e il colpevole è altrove: allora serve
  bisezionare la suite fino al test 3939.

**Non lo eseguo io**: giro su Windows, e su Windows il crash non si presenta (nei
tre run i job `windows-latest` sono falliti per altro). Serve una macchina Linux
— WSL basta. Chi ce l'ha lo fa in due minuti.

## 5 · Cosa questo ticket NON dice

- Non dice che il test sia sbagliato: **prova una cosa vera** (che il watchdog
  lasci un dump) e la prova bene quando gira da solo.
- Non dice quanto spesso capiti in assoluto: **3 su 10 dei run FALLITI** in una
  finestra di ~26 ore. Non ho contato quante volte quel test è passato senza
  crash nei run verdi della stessa finestra — è la misura che manca.
- Non propone la cura: la scelta fra isolare il test, cambiare il modo di
  dumpare, o non armare faulthandler quando ci sono thread nativi, è di chi
  tiene il watchdog.
