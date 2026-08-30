# Quadro per la decisione VERSIONE — 30/08 sera
> Preparato da lead-audit per Aurelio. Ogni dato cita la misura che lo sostiene.
> La decisione è di Aurelio (vincolo versione/tag/publish); questo è il quadro
> completo con la raccomandazione del direttore.

## Lo stato dei fatti
- PyPI serve **0.7.0** (22 luglio), che **crasha con `mcp>=2`** su installazione
  pulita. L'utente nuovo muore al primo minuto. Il pin `mcp<2` è in main dal
  29/07 e nella tag-line mai pubblicata.
- `pyproject` su main dichiara **0.7.6**, ferma da **1133+ commit** (il test
  `test_la_versione_dichiarata_non_e_troppo_lontana_dal_codice` è ROSSO per
  questo — deadlock: il presidio che chiede di rilasciare blocca il rilascio,
  misurato anche in CI).
- Il tag **v0.7.6 esiste** (creato dalle istanze il 24/08 — NON da Aurelio: la
  firma git è istituzionale), mai pushato. Smoke C7 su quel tag: **verde**
  (mcp risolto 1.29.1, `Server.list_tools` presente, EXIT=0 — ws1, 29/08).
- Le cure di oggi (L1.20-ad-avviso `5ea77b6d` verde-2-firme; guardia anti-eco
  `1a4b8635` verde-2-firme LANT-103) sono **su main**, NON dentro il tag
  v0.7.6.
- Dato nuovo (ws7, 30/08): il flip `GRADED_ADMISSION` curerebbe **la faccia
  sbagliata** — i 38 trattenuti-col-giudice-a-favore recenti sono di L4.1, non
  del moat. Il flip esce dal pacchetto raccomandato finché non rimisurato.

## Le opzioni
**A — bump 0.8.0 su `main`.** Sblocca il test-deadlock subito. Contro: il
docstring del test elenca tre vie e il bump «azzera il contatore senza curare
ciò che il test sorveglia» (il pubblicato resta vecchio). Sensato SOLO come
parte del treno release 0.8.0, non da solo.

**B — test-① ad avviso.** Il test si dichiara «avviso, non veto»: allinearlo
all'intenzione. Legittimo ma tocca il senso di un presidio: a mente fredda.

**C — 0.7.1-hotfix: branch dal tag v0.7.0 + SOLA riga `mcp<2` → publish.**
Cura l'utente rotto OGGI col minimo cambiamento possibile (una riga su una
base già pubblicata e nota). Non imbarca nulla del lavoro non-a-contratto.
Contro: mantiene viva una linea vecchia; richiede comunque i prerequisiti di
publish (sotto).

**D — push del tag v0.7.6 esistente.** Smoke utente verde; renderebbe
confrontabile pubblicato-vs-repo. Contro: imbarca TUTTO il codice fino al
24/08 — pre-contratto, pre-cure di oggi, con la CI di quel commit non verde e
il wheel da rimisurare col veto identificativi. È «pubblicare 900 commit non
verificati», cioè il rischio che il contratto esiste per evitare.

## Prerequisiti di QUALUNQUE publish (indipendenti dall'opzione)
1. La falla `workflow_dispatch`-senza-tag di publish.yml (W8-4) chiusa.
2. Veto identificativi EXIT=0 sul wheel COSTRUITO DA QUELLA base.
3. Smoke install-from-scratch sulla base pubblicanda (C7, già ripetibile).

## Raccomandazione del direttore
**C adesso, 0.8.0 a contratto chiuso.** La 0.7.1 ripara l'utente di oggi con
una riga verificabile; la release vera (0.8.0, con le cure L1 e i numeri
comparativi C10) esce quando C1–C10 sono verdi — ritmo attuale: giorni, non
settimane. D scartata (imbarca il non-verificato). A solo insieme al treno
0.8.0. B a mente fredda dopo.

Ordine di esecuzione se Aurelio dice «C»: chiudi W8-4 → branch `hotfix/0.7.1`
da v0.7.0 → cherry della sola riga pin → veto+smoke sul wheel di QUEL branch →
tag v0.7.1 → publish → yank della 0.7.0 (dopo, mai prima).
