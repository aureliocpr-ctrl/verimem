# `ci / windows` rossa su main: il gate del breaker non riarma dopo il cooldown

**Data** 2026-09-10 20:29 (letta con `date`) · **owner** ws1 Marie (QA) · **ticket** T38

1. **COSA** — sul tip `32273665` il job `test (windows-latest / py3.12)` di `ci`
   (run `34472648985`) va rosso. Gli altri **sette job su otto** sono verdi, e
   `security` (`34472649016`) è `success`.
   ```
   FAILED tests/test_rerank_breaker.py::test_observing_the_breaker_does_not_rearm_it
     AssertionError: the gate, and only the gate, re-arms after the cooldown
     E   assert True is False
     1 failed, 12848 passed, 44 skipped, 131 xfailed in 2737.13s (0:45:37)
   ```
   Cade la terza asserzione (riga 461): `_rerank_breaker_tripped()` — **il gate** —
   deve tornare `False` dopo il cooldown e torna `True`. Le due precedenti
   passano: il breaker **è** scattato e l'osservazione non lo riarma. **Solo il
   riarmo non avviene.**

2. **CLASSE** — **② TRAPPOLA ARMATA**, e non è una scelta mia: è scritta nel
   file dal **24/08** (`tests/test_rerank_breaker.py:390-404`), *«è una GARA,
   non una regressione — 2 celle `windows-latest / py3.12` su 6 (33%), col
   codice del breaker **byte-identico** fra i run che passano e quelli che
   cadono»*. Il diff che l'ha fatta scattare oggi non tocca `semantic.py`.

3. **CAUSA** — **NON TROVATA.** Quattro ipotesi escluse, ognuna con la misura:
   - ❌ **la grana dell'orologio** (la mia diagnosi dell'08/09, **ritirata**):
     `time.monotonic` = `QueryPerformanceCounter`, risoluzione `0.0001 ms`;
     `sleep(0.06)` misura 60,17–61,34 ms su 12 giri, **0 sotto i 50 ms** del
     cooldown;
   - ❌ **un thread orfano** del test precedente
     (`test_no_overrun_is_lost_when_a_rearm_is_in_flight` avvia un thread daemon
     dentro il gate): **ha `t.join(10)`**, letto alla riga;
   - ❌ **una cache del cooldown**: `_rerank_breaker_cooldown_s()` legge
     `os.environ` a ogni chiamata (`semantic.py:2140-2144`);
   - ❌ **riproduzione locale**: il test da solo `1 passed`, il file `17 passed`,
     e **8 giri consecutivi del file → 136 test, zero cadute**.
   📊 Se il tasso su questa macchina fosse quello della CI (33%), la probabilità
   di otto verdi di fila sarebbe **4,1 %** (`0,67^8`): indizio, non prova, che
   **le due popolazioni sono diverse** — la gara ha bisogno di qualcosa che il
   runner ha e questa macchina no.

4. **CURA** — **NON ENTRATA, e non ne esiste una giusta finché la causa manca.**
   ⚠️ Una cura c'era, ed era **sbagliata**: una cella con l'orologio finto scritta
   l'08/09 su `HA-ws1-asof` (untracked), figlia della diagnosi ritirata al punto
   3. **Non è stata portata**: avrebbe curato un difetto che non esiste, e il
   rosso sarebbe tornato al 33%.

5. **CONTROLLO AGGIUNTO** — **NESSUNO**, ed è un debito con un nome sopra (mio).
   La cosa da fare per prima **non è una cura**: è far parlare il rosso. L'assert
   del test *vicino* stampa già `cd`, `tripped_at` e `monotonic()` — chi ha
   scritto il commento del 24/08 li ha messi perché *«la prossima caduta dica la
   causa invece di ridarci solo un tasso»*. **L'assert che cade non li stampa**,
   e per questo la caduta di oggi ci ha ridato solo il tasso. Una riga.

6. **QUANTO È RIMASTO ROSSO** — la famiglia è nota dal **24/08** (17 giorni).
   Questa caduta: dal run del **10/09** che ha chiuso la finestra, e alle 20:29
   è **ancora aperta**. Se n'è accorto il lead leggendo i job; **nessun allarme
   suo**: un rosso al 33% in un job su otto non emette segnale, e due rerun su
   tre lo fanno sparire.

---

## Le tre cose che questo rosso insegna, e che non erano nel rosso

🔑 **La diagnosi vera era nel file da due settimane, e nessuno l'ha letta** — io
compresa, mentre diagnosticavo l'orologio *sullo stesso file*. La mia regola «la
lezione era nel commento del file» esisteva già; non l'ho applicata proprio dove
contava.

🔑 **Un numero citato a memoria è un'ipotesi travestita da misura.** «La grana su
Windows è 15,6 ms» era vera per un *altro* orologio. Bastava un
`time.get_clock_info("monotonic")`, ed è costato due giorni e una finestra.

🔑 **Un rosso che cade una volta su tre non si cura con un rerun**: il rerun lo
nasconde due volte su tre e lo riporta alla quarta. E un rosso guarito da un
rerun **sparisce da `gh run list`** (misurato da @Corrado il 09/09), quindi il
tasso vero è più alto di quello che la lista mostra.
