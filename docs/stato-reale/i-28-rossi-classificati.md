# I 28 rossi della suite, letti uno per uno

*ws3 «Galileo», 30/08. Risposta a una domanda di Aurelio rimasta aperta quindici
ore: «**sei sicuro che la versione funziona, o è l'ennesima cazzata rotta?**»*

## Il verdetto, con ciò che lo rende un verdetto

`python scripts/suite_a_fette.py --fette 3`, avviata 12:19, letta dai file:

```
fetta 0  EXIT=1  = 16 failed, 3803 passed, 11 skipped, 24 xfailed in 1279.81s =
fetta 1  EXIT=1  =  4 failed, 4670 passed,  6 skipped, 62 xfailed in 1558.04s =
fetta 2  EXIT=1  =  8 failed, 3769 passed,  6 skipped, 40 xfailed in 1162.99s =
EXIT=1        →   28 failed · 12242 passed · 23 skipped · 126 xfailed
```

`EXIT=` **accompagnato dai tre riepiloghi**: è la REGOLA-VERDE v3, e senza i
riepiloghi quel numero sarebbe stato la firma di come è morto il processo, non
un verdetto ([l'EXIT che non è un verdetto](l-exit-che-non-e-un-verdetto.md)).

🔑 **La risposta onesta è in due tempi**: **non è verde** — e **28 rossi non sono
28 difetti**. Contarli avrebbe mentito in entrambe le direzioni.

## Le sei classi

| | classe | n |
|---|---|---|
| ① | **regressione mia** (`29ab5544`, 28/08) | **4** |
| ② | **ambiente — questa macchina** | 10 |
| ③ | **servizio esterno** | 1 |
| ④ | **`XPASS(strict)`: presidi guariti col marcatore addosso** | 3 |
| ⑤ | **debito di presidio: un numero da aggiornare** | 4 |
| ⑥ | **da capire — né mio né d'ambiente** | 6 |

### ② Ambiente (10) — dipendono da ciò che questa macchina ha

- **4 ricevuta** — `L4-skipped — source provided but the grounding judge was
  still loading`. Cold start: tre fette in parallelo, il giudice non è caldo.
  🔑 **Il prodotto lo DICE nella ricevuta**, e la ricevuta è leggibile. Ma il
  comportamento quando il giudice non è pronto è **ammettere**.
- **3 daemon** — `ensure_running_spawns_when_unreachable`,
  `ensure_running_cooldown_blocks_double_spawn`,
  `l120_parla_quando_l_encoding_non_costa_un_cold_load`. I test vogliono il
  daemon **morto**; qui è **vivo**.
- **2 dimensioni** — `768d` trovati dove il test attende `384`, e viceversa.
- **1** `offline_embedding_makes_no_external_connection` — encoder `Unavailable`.

⚠️ *Un rosso che non si riproduce non è «instabile»: dipende da ciò che la tua
macchina ha e la loro no.* Per ognuno serve il regime, non l'etichetta.

### ④ I tre `XPASS(strict)` non sono difetti: sono guarigioni non registrate

`every_claim_backed_by_artifact_and_regenerable` porta nel proprio stdout
**`8/8 claims backed by artifacts` · `8/8 regenerable` · `8/8 whose value is
actually compared`**. Il marcatore `xfail` dice che dovrebbe fallire. **La cura
è togliere una riga.** Stesso caso per `ogni_ricetta_del_registro_e_un_modulo` e
`il_package_non_porta_identificativi_di_sessione`.

### ⑤ Debito (4) — presidi che chiedono un numero aggiornato

codice scollegato **39 contro 38** · divergenze **scese a 0** (nota 159) ·
**versione ferma da 1073 commit** (è il bump congelato in attesa di Aurelio) ·
un banco che non dichiara come guarda l'esito del subprocess.

### ⑥ Da capire (6) — per chi mantiene `L1`

Tutti i `test_quarantine_restore_public.py` e `test_quarantine_log_*`. Il
fixture disattiva la precisione di dominio — `ENGRAM_L1_DOMAIN_PRECISION=0` —
per ottenere la quarantena legacy da cui partire, **e non la ottiene più**:

```
setup: expected FP, got {'moat': 'passed', 'stored': True,
                         'status': 'model_claim', 'grounding_score': 99.53…}
```

⚠️ **La fonte È il claim** (`source=LEGAL_FP` su un claim `LEGAL_FP`) e passa a
**99,53**. Va letto accanto al banco `ef234ae0` di lead-audit, dove il
fail-closed anti-auto-sorgente si aggira per riformulazione 3/3. **Non è il mio
perimetro e non lo decido io.**

---

## ① I quattro rossi miei — e la diagnosi che ho dovuto ritirare

Il 28/08 ho introdotto `_spans_dei_riferimenti` (`29ab5544`): «*art. 3*» in un
claim è un puntatore a una norma, non la quantità 3. Il commit diceva «RED→GREEN
alla porta» — **TDD su un test mio**. La suite non girava, la CI non gira.

Ieri ho detto al gruppo: *conflitto fra due intenzioni legittime, non lo curo*.
**Falso per tre casi su quattro**, e l'ho scoperto leggendo invece di dedurre.

### Il difetto è la giuntura, e il commento diceva già il numero

`extract_quantities(text, *, come_fonte=False)` ha **un bivio solo**, e la sua
docstring lo dichiarava: «*`come_fonte=True` legge il testo INTERO, saltando le
**due** potature*».

```python
claim = text if come_fonte else _senza_identificatori(claim_span(text))  # il bivio
_date = _spans_delle_date(claim)
_riferimenti = _spans_dei_riferimenti(claim)      # ← la TERZA, due righe SOTTO
```

Misura sugli otto casi del presidio del 07/08, **entrambe le modalità**:

```
frase                     come CLAIM    come FONTE
grad.3                         {3.0}         {3.0}
temp.22                       {22.0}        {22.0}
l'art.15 del codice            set()         set()   ← invisibile anche alla fonte
vedi pag.7                     set()         set()   ←
il n.42 del registro          {42.0}        {42.0}
tot.300 pezzi                {300.0}       {300.0}
fig.3                          set()         set()   ←
Nr.5 im Lager                  {5.0}         {5.0}
                        CLAIM 5/8     FONTE 5/8
```

⇒ **Non era un presidio rimasto indietro: avevo accecato anche il lato fonte**,
dove quel numero è contenuto e non citazione. Il claim che lo cita sembra
inventarselo, e `L4.1` quarantina un fatto vero — **esattamente il difetto che
la modalità `come_fonte` era nata per chiudere il 16/08**.

**Cura, una riga, sul bivio** (`fb2ff485`):

```python
_riferimenti = [] if come_fonte else _spans_dei_riferimenti(claim)
```

RED→GREEN **falsificato e non sul test introdotto con la cura**: riga vecchia
`EXIT=1` (4 failed, 8 passed), riga nuova `EXIT=0` (12 passed). Sweep sui due
riceventi di `come_fonte=True` — `soggetto_valore`, `valore_non_nella_fonte` —
**36 passed, 1 xfailed**.

Il presidio nuovo misura **entrambe le popolazioni**: la fonte torna a vedere
8/8 **e** il claim continua a non affermare il numero del proprio riferimento
3/3. Con una metà sola si sarebbe potuto «curare» cancellando `29ab5544`.

### Il quarto resta rosso, e non lo curo io

`test_un_numero_che_la_fonte_NON_contiene_resta_assente` — il claim «*Il
riepilogo viene stampato alla **riga 999***» contro una fonte priva di 999.
`riga` è una delle parole della potatura, il claim non afferma più nulla, e
**l'assenza non viene più segnalata**. Il docstring di quel test lo aveva
previsto: «*leggere la fonte per intero non deve diventare un lasciapassare*».

Sul lato claim la potatura **è voluta**. Ma un riferimento **inventato** è
comunque una confabulazione: «alla riga 999» quando la riga 999 non esiste è
falso. ⇒ **Questo sì è design** — trattare i riferimenti come una classe a sé,
non ignorarli — e va deciso da chi mantiene il layer, non da me di corsa per far
tornare verde un numero.

---

## Cosa NON dice questo documento

- **Non dice che il prodotto sia rotto.** 12242 test passano. Dei 28 rossi, 18
  sono ambiente, debito o marcatori da togliere; 6 vanno capiti; **4 li ho messi
  io e 3 sono curati qui**.
- **Non dice che sia verde.** Non lo è, e il rosso più fresco è mio.
- **Non classifica per me i 6 di ⑥**: li ho letti abbastanza per dire che non
  sono d'ambiente, non abbastanza per dire cosa siano.

## Le due lezioni, che valgono oltre questo caso

1. **Un RED→GREEN sul proprio test non è una verifica: è una conferma.** Dice
   che la cura fa ciò che volevo, non che non rompa ciò che altri volevano.
   Senza CI verde il TDD locale non è una rete, è uno specchio.
2. **La lezione era nel commento, e nominava il numero.** «Le due potature»:
   chi aggiunge la terza deve dirlo al bivio, o l'esenzione smette di essere
   completa **senza che nessuna riga diventi rossa**. Contare le porte veniva
   prima di aprirne una nuova — sei moduli leggono quella funzione. *Il
   docstring ora dice TRE, le elenca tutte, e chiede alla quarta di registrarsi.*

**Agent: Galileo**
