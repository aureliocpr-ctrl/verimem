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
  riprodotta a comando. È il ticket **T38**, owner **ws5 Tara**.
* **Cura** — **nessuna, e questo è il punto**: il rosso è stato tolto da un
  *rerun*, non da un cambiamento. Il codice del test è oggi quello di allora.
  Finché T38 non chiude, la stessa gamba può ridiventare rossa su un commit che
  non c'entra niente — e la prossima volta bloccherà di nuovo un tag.
* **Controllo** — oggi **NESSUNO**, ed è un debito dichiarato. Il controllo che
  serve è di T38: rendere il tempo del breaker esplicito nel test (un orologio
  iniettato) così che il rosso si riproduca a comando o non capiti mai.
  Il controllo che questo postmortem aggiunge *subito* è diverso e sta un passo
  più indietro — **rendere i rossi contabili**: `gh run list` mostrava
  `success`, perché legge l'ultimo tentativo, e questo rosso era già sparito da
  ogni conteggio 24 ore dopo. Da qui in poi si contano i **tentativi**, e questa
  cartella è il registro che sopravvive al rerun.
* **Owner** — T38 e la causa radice: **ws5 Tara**. Il conteggio dei rossi e
  questa cartella: **ws8 Corrado**.

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
