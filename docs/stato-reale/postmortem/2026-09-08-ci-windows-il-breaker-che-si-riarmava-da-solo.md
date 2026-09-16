# 2026-09-08 — la ci windows rossa sul candidato al tag, con zero file di prodotto cambiati

* **Cosa** — il candidato al tag `5ac8d9f1` (README e presidi, nessun file sotto
  `verimem/`) ha reso rossa la gamba `test (windows-latest / py3.12)` con
  `1 failed, 12821 passed, 44 skipped, 40 deselected, 128 xfailed in 3053.25s`.
  Il test: `tests/test_rerank_breaker.py::test_observing_the_breaker_does_not_rearm_it`,
  `AssertionError: the gate, and only the gate, re-arms after the cooldown` ·
  `assert True is False`. Run `34221255060` tentativo 1
  (`2026-09-08T11:32:45Z` → `12:31:10Z`), job `102044644257`; il tentativo 2 è
  verde (`updated_at 2026-09-08T18:09:13Z`).
* **Classe** — **trappola armata**. Nessun file di prodotto era cambiato e le
  altre otto gambe erano verdi: il prodotto non poteva essersi rotto in quella
  finestra. Il test dipende da un tempo di raffreddamento che non ha dichiarato,
  e sulla macchina Windows quel tempo è passato mentre il test guardava.
* **Causa** — **NON PROVATA fino in fondo**, e va detto invece di completarla con
  l'ipotesi comoda: la lettura di `_rerank_breaker_tripped()` è tornata `True`
  dove il test ne pretendeva `False` dopo il raffreddamento. La causa radice sta
  in come il test misura il tempo, non in `semantic.py`, ma nessuno l'ha ancora
  riprodotta a comando. È il ticket **T38**, owner **ws5 Piattaforma**.
* **Cura** — **nessuna, e questo è il punto**: il rosso è stato tolto da un
  *rerun*, non da un cambiamento. Il codice del test è oggi quello di allora.
  Finché T38 non chiude, la stessa gamba può ridiventare rossa su un commit che
  non c'entra niente — e la prossima volta bloccherà di nuovo un tag.

  > **↑ QUESTA PREVISIONE SI È AVVERATA IN TRENTA ORE.** Il 10/09 alle 13:26 la
  > stessa gamba, lo stesso test, lo stesso identico messaggio hanno reso rossa
  > **main** su `32273665` (`1 failed, 12848 passed`) — dopo il merge di una PR
  > che non tocca né `semantic.py` né il breaker (`git diff | grep -c
  > rerank_breaker` → **0**). Ha bloccato la finestra invece di un tag. La stessa
  > sera è caduto anche su un altro ramo (`0784915a`).
  >
  > **Il 10/09 alle 21:00 il controllore ha deciso la QUARANTENA su windows**
  > (`xfail(sys.platform == "win32", strict=False)`) per riaprire la finestra. La
  > quarantena **non è una cura**: T38 resta aperto, la causa resta ignota, e il
  > marker si toglie con la cura, non con il tempo.
* **Controllo** — oggi **NESSUNO**, ed è un debito dichiarato. Il controllo che
  serve è di T38: rendere il tempo del breaker esplicito nel test (un orologio
  iniettato) così che il rosso si riproduca a comando o non capiti mai.
  Il controllo che questo postmortem aggiunge *subito* è diverso e sta un passo
  più indietro — **rendere i rossi contabili**: `gh run list` mostrava
  `success`, perché legge l'ultimo tentativo, e questo rosso era già sparito da
  ogni conteggio 24 ore dopo. Da qui in poi si contano i **tentativi**, e questa
  cartella è il registro che sopravvive al rerun.
  **E dal 10/09 c'è un secondo debito, creato dalla quarantena stessa.**
  `strict=False` rende verde sia il fallimento (`xfailed`) sia il successo
  (`xpassed`): **il segnale sparisce in tutt'e due le direzioni**, ed è la forma
  già misurata in casa — *una capacità spenta non emette segnale*. Il conteggio
  non è perduto, ma va CERCATO, e questo è il comando:

  ```
  gh api repos/<owner>/<repo>/actions/jobs/<job>/logs \
    | grep -E "XFAIL|XPASS" | grep test_observing_the_breaker
  ```

  `xfailed` = la gara ha morso · `xpassed` = quel giro è passato. Finché il
  marker è lì, **il tasso si legge solo così**, e chi apre la finestra dovrebbe
  guardarlo: un test in quarantena che smette di cadere è una notizia quanto uno
  che ricomincia.

* **Owner** — T38 e la causa radice: **ws5 Piattaforma**. Il conteggio dei rossi, la
  quarantena e questa cartella: **ws8 Release**.

---

## Le cinque ipotesi ESCLUSE il 10/09 (perché nessuno le rifaccia)

Tutte e cinque erano di ws8, tutte cadute nella stessa serata, con la prova:

| # | ipotesi | come è caduta |
|---|---|---|
| 1 | i rerank CE sono lenti su Windows e il breaker scatta davvero | i tre sforamenti li registra **il test stesso** |
| 2 | il margine di 10 ms è sotto la granularità dell'orologio | ⚠️ **NON ERA ESCLUSA: ERA LA CAUSA.** Vedi sotto |
| 3 | `_rerank_breaker_cooldown_s()` memoizza il valore | legge `os.environ` a ogni chiamata (`semantic.py:2140-2144`) |
| 4 | un thread orfano del test precedente | **c'è `t.join(10)`** (riga 429) — smentita da ws1 leggendo la riga |
| 5 | un worker di rerank in volo ri-scatta il breaker | lo sforamento lo registra **il caller** al timeout, non il worker: banco dedicato, **0 rossi su 8** |

**31 esecuzioni su Windows di casa, mai un rosso.** Con una gara al 13-33% questo
non prova l'assenza: prova che la finestra non si apre in quell'ambiente.

## 🔴 L'IPOTESI ② NON ERA ESCLUSA: ERA LA CAUSA (corretto il 10/09 alle 22:45)

**La causa l'ha trovata ws3 Ricerca, ws1 QA l'aveva vista per prima l'08/09 e
l'ha ritirata a torto, e io ho pubblicato la falsificazione sbagliata.** Il
motivo per cui tutt'e due abbiamo sbagliato è lo stesso, ed è misurabile in
dieci secondi:

```
py -3.11  ->  monotonic = GetTickCount64()            0.015625 s  = 15,625 ms
py -3.13  ->  monotonic = QueryPerformanceCounter()   1e-07 s
```

**Il job che cade è `test (windows-latest / py3.12)`.** L'implementazione di
`time.monotonic()` su Windows è cambiata **fra 3.12 e 3.13**: i miei 400 giri
«0 falsi» giravano su **3.13**, cioè sull'orologio sbagliato. Sull'orologio del
job, il margine del test — `sleep(0.06)` contro un cooldown di `0.05`, cioè
**10 ms** — sta **sotto il quanto di 15,625 ms**: la gara è esattamente quella.
ws3 Ricerca l'ha misurata: **5 fallimenti su 40** con l'orologio giusto.

### Il margine contato in TICK, e le celle a rischio sono CINQUE (ws5, 11/09)

ws5 Piattaforma ha rifatto il conto **in tick dell'orologio** invece che in millisecondi, ed
è la forma che rende la cosa evidente:

```
cella                                         cooldown  attesa  margine  tick
a_tripped_breaker_rearms_after_the_cooldown      0,3     0,35    50 ms    3,2
cold_trip_rearms_and_forgets_the_cold_count      0,3     0,35    50 ms    3,2
fusion_breaker_rearms_after_the_cooldown         0,3     0,35    50 ms    3,2
the_recall_gate_sees_the_rearm                   2,0     2,1    100 ms    6,4
no_overrun_is_lost_when_a_rearm_is_in_flight    0,05     0,06    10 ms   0,64   <- la nostra
cooldown_zero_keeps_the_trip_standing            0       0,05     --      --
```

🔑 **La cella più esposta non era «stretta»: era SOTTO UN TICK.** 10 ms contro una
grana di 15,625 fa **0,64 tick** — non un margine piccolo, ma **un margine che
quell'orologio non sa rappresentare**. In millisecondi sembra una soglia da
allargare; in tick si vede che è una quantità che non esiste.

E le celle a rischio erano **cinque, non una**: il commento del 24/08 ne
descriveva un'altra, e infatti la gara è più larga del singolo test — ora sappiamo
di quanto.

⇒ **La cura è la #30 di ws5 Piattaforma** (`6bc2f0e5`): le cinque celle **spostano** il
tempo (`tripped_at -= 10.0`) invece di aspettarlo, passando da 3-6 tick a dieci
secondi. Toglie la dipendenza dall'orologio invece di allargare il margine.

⇒ **E la quarantena NON entra in main.** Il controllore l'ha deciso l'11/09 alle
19:38: la cura è pronta, quindi il lasciapassare non serve. La PR #31 resta aperta
finché #30 non è dentro, poi si chiude. Questo documento — e la correzione qui
sopra — arrivano su main con la **#14**, non con la #31.

### La lezione, e mi appartiene per intero

**Un banco dichiara quale albero misura — e anche quale INTERPRETE.** Fra due
versioni dello stesso Python la stessa riga dà due risposte a 156.000× di
distanza, e il numero che avevo pubblicato come prova era vero e inutile
insieme, perché misurato altrove.

È la **terza forma** della stessa famiglia in ventiquattr'ore, tutte mie:
il banco con lo schema di database inventato da me; il `grep` con `join\(\)` che
non poteva matchare `join(10)`; e adesso l'interprete. Ogni volta **lo strumento
non poteva vedere il caso**, e ogni volta ho letto quel «non vedo» come «non
c'è». 🔑 *Un'assenza prodotta da uno strumento non è un'assenza: è la forma
dello strumento.*

E la parte che pesa di più: **la mia falsificazione ha contribuito a far
ritirare a ws1 QA una diagnosi giusta.** Un «escluso» pubblicato con dei numeri
accanto è molto più difficile da riaprire di un dubbio — per questo la riga
sopra dice «NON ERA ESCLUSA» invece di essere cancellata: chi ha letto la
versione sbagliata deve incontrare la correzione nello stesso posto.

---

Il fatto più solido dell'indagine resta il commento del **24/08** dentro
`test_rerank_breaker.py` (trovato da ws1): *«è una GARA, non una regressione»*,
breaker **byte-identico** fra i run che passano e quelli che cadono — e descrive
l'assert di un test **diverso** da quello caduto il 10/09, quindi **la gara è
più larga del singolo test**. È la ragione per cui la quarantena copre un test
solo: marcarne di più spegnerebbe più segnale di quello che serve.

---

## Perché questo è il primo file della cartella

Non è il rosso più grave che abbiamo avuto: è quello che mostra meglio a cosa
serve il registro. Ha tre proprietà insieme:

1. **ha fermato un rilascio** — il candidato al tag è rimasto in freeze;
2. **non ha lasciato traccia** — un rerun l'ha guarito e `gh run list` oggi dice
   `success`: senza questo file, fra un mese la giornata dell'08/09 risulterebbe
   senza rossi;
3. **la sua cura non è stata scritta** — e un limite non curato che nessuno
   registra torna, con la faccia di un problema nuovo.

Le tre misure del venerdì (R8) leggeranno **questa cartella**, non la pagina
Actions.
