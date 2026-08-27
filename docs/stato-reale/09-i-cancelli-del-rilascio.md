# I cancelli del rilascio — cosa impedisce meccanicamente di pubblicare

Misurato il 2026-08-26 fra le 19:25 e le 23:00.

`RELEASE_GATE.md` elenca i criteri **G1–G10**: cosa deve essere *vero* perché un
rilascio sia onesto. Questo documento è l'altra metà e non lo duplica: elenca
cosa impedisce **meccanicamente** di pubblicare, in che stato è ciascun vincolo
oggi, e **con quale comando rimisurarlo**. Un criterio si valuta; un cancello si
apre o resta chiuso.

> ⚠️ **Qui non si citano hash.** Su questo ramo si rebasa spesso e gli SHA
> vengono riscritti — misurato il 26/08: `796ffec7` è diventato `ba671fff`.
> Ogni riferimento è per **path** o per **messaggio di commit**, che sopravvivono.

---

## I sette vincoli, e il loro stato

| # | vincolo | dove vive | tipo | stato al 26/08 |
|---|---------|-----------|------|----------------|
| ① | la CI è verde sul commit **taggato** | `publish.yml`, job `gate` | **VETO** | 🔴 3 failed / 12033 passed |

> ➕ **AGGIUNTA 2026-08-27, ws7 — il vincolo ① regge, e adesso i tre hanno un nome.**
> Rimisurato oggi sul primo run concluso dopo che la coda si è smaltita: `3 failed, 11983 passed, 44 skipped, 39 deselected, 81 xfailed, 6 errors in 1206.09s` (job ubuntu-py3.10). Il conteggio di ieri regge — i 50 `passed` di differenza sono la suite che si è mossa, non una misura diversa.
> Questo documento dice **quanti**, e per aprire il cancello serve sapere **quali**:
> · `test_un_accento_non_decide_se_il_gate_scatta.py::test_l_accento_non_cambia_il_verdetto_sulla_latenza[La latenza è 40 ms.]`
> · `test_un_accento_non_decide_se_il_gate_scatta.py::test_nessun_ALTRO_pattern_del_package_dipende_dall_accento`
> · `test_unsupported_span.py::test_the_gate_says_how_many_assertions_it_judged_as_one`
> ⚠️ **E i 6 `errors` non sono sei difetti: sono UNA fixture.** Tutti e sei sono «at setup of» — `test_anche_il_ramo_per_TOPIC`, `test_e_combacia_con_search_come_la_docstring_PROMETTE`, `test_e_il_ramo_per_PREFISSO_che_era_gia_giusto`, `test_il_conteggio_non_include_cio_che_non_ti_restituisce`, `test_la_primitiva_di_BASSO_livello_non_cambia_per_nessuno`, `test_un_quarantinato_RIABILITATO_torna_nel_conteggio`. Contarli distinti gonfia il problema di sei volte.
> ⏱️ E una stima che questo file eredita da altri e che oggi cade: la cella **ubuntu-py3.10 dura 20 minuti** (1206 s), non 45 — i 45 sono il tetto di *windows*.
> 📌 Contesto: dei **59 run del 26/08 tutti conclusi, ZERO success e 59 failure**. Il verdetto arriva, ci mette 5-8 ore.

> ⚖️ **RICONCILIAZIONE 2026-08-27, ws8 — le due misure qui sopra e qui sotto NON si
> contraddicono: sono DUE EPOCHE.** La sezione precedente e quella successiva danno numeri
> diversi, e nessuna delle due è sbagliata:
>
>     epoca A (run più VECCHI)   3 failed · 11983 passed · 81 xfailed · **6 errors**
>                                `test_un_accento…` ×2 · `test_unsupported_span`
>     epoca B (run più RECENTI)  3 failed · 12033 passed · 106 xfailed · **0 errors**
>                                presidio versione · `test_quarantined_by…` ×2
>
> ⇒ Non è «la suite che si è mossa»: **6 errors contro 0 non è rumore**. La differenza è il
> commit su cui girava il run. In A `unsupported_span` è ancora rosso e i sei `errors at
> setup` ci sono; in B `unsupported_span` è **verde** (`grep -c 'FAILED …unsupported_span'`
> → 0) e gli errors sono **zero** — perché fra le due epoche sono entrati la cura del
> presidio («chiedeva la frase, non il fatto») e i due revert del 26 sera che hanno chiuso
> il carve-out `ENGRAM_L1_DOMAIN_PRECISION`.
> 📌 L'osservazione «i 6 errors sono UNA fixture, non sei difetti» **resta giusta e utile**:
> vale come lezione di lettura anche ora che quel difetto non è più nell'albero.
>
> 🔑 **LA REGOLA CHE NE ESCE, e vale per chiunque legga `gh run list`:** «il primo run
> concluso» **non** è «il run più recente». I run finiscono nell'ordine in cui partono, e i
> più vecchi portano commit più vecchi — stanotte erano **tutti creati il 26 sera e finiti
> il 27 all'alba**, quindi *l'ora da sola non li distingue*.
> ⇒ **Stampare sempre la data del run — creato E finito — accanto al numero.**
>
>     gh run list … --json conclusion,headSha,createdAt,updatedAt
>
> Non è un consiglio di prudenza: è l'unico modo per non prendere una fotografia vecchia
> per lo stato di oggi. Chi scrive questa riga ci è cascata per prima, il 26/08, leggendo
> **un** run e generalizzandolo a quattordici.

| ② | `PUBLISH_ANYWAY` non impostata | variabile di repo | scappatoia | ✅ `total_count: 0` |
| ③ | `twine check dist/*` | `publish.yml` | veto debole | solo metadati |
| ④ | il wheel non porta identificativi | `scripts/controlla_registro.py` | **VETO** | 🔴 chiuso, `EXIT=1` |
| ⑤ | promesse su più superfici | `scripts/controlla_promesse.py` | **avviso** | dichiarato non-veto |
| ⑥ | l'sdist non è controllato | step «Cosa esce nell'sdist» | **avviso** | dichiarato non-veto |
| ⑦ | il blocco `⛔ RILASCIO` | dentro `README.md` | umano | attivo |

### ① La CI verde sul commit taggato — VETO

Il job `gate` interroga i run di `github.sha`, cioè **il commit che porta il
tag**, non la punta di `main`. Verificato: filtra `name=="ci"` e
`head_branch=="main"`. Il sospetto che guardasse la punta è stato **scartato con
la misura**, non con la lettura.

    gh run list --branch main --workflow ci.yml --limit 25 --json status,conclusion

⚠️ **Conta le righe che il comando restituisce** prima di credere all'aggregato:
il 26/08 tre righelli diversi hanno prodotto tre diagnosi sbagliate, tutte
perché la finestra guardata era più stretta dei dati.

#### Cosa dice davvero, al 27/08 — e «16 su 16 failure» dice pochissimo

I run hanno ripreso a concludere. L'aggregato è **16 su 16 `failure`**; la riga
di sintesi, identica su due run e due celle (ubuntu-py3.12 e windows-py3.12), è:

    **3 failed · 12033 passed · 41 skipped · 106 xfailed · 0 errors**

⇒ Un `failure` di run non è una misura dello stato: **contare i run rossi al
posto dei test rossi sbaglia di tre ordini di grandezza.** I tre sono:

1. **il presidio versione** — e ha *cambiato natura*, vedi sotto;
2. e 3. `tests/test_quarantined_by_nomina_il_layer_sbagliato.py`, due test.
   In locale sono **verdi** (2 passed, 1 xfailed). Escluso l'albero (7 commit
   di distanza, **zero** toccano quel test o `verimem/`) ed escluso l'ordine
   interno (tre seed di `pytest-randomly`, tutti verdi). L'assert dice:
   `parla un layer solo (['L4-review']): il difetto non si presenta`,
   `assert 1 >= 2`. ⇒ **Non è una regressione: è un presidio che in CI non
   riesce a riprodurre il difetto che presidia.** Windows e ubuntu danno lo
   *stesso* assert, quindi l'OS è escluso; `L4-review` è la banda di revisione
   del CE, e la differenza plausibile è che **in CI il gate CE viene scaldato e
   usato** (`ci.yml:357`, `verimem warmup --no-daemon`, senza `--no-gate`)
   mentre fino all'11/08 non lo era. Il presidio è stato scritto quando quel
   giudice, in CI, non girava.

#### 🔴 Il presidio versione ha SFONDATO la soglia

    E  AssertionError: la versione 0.7.6 è ferma da **224 commit** (soglia 150)
    E  assert 224 <= 150                              (su windows: 222)

`RELEASE_GATE.md` registrava **131/150 → verde**. Ora sono **224**: la soglia è
stata superata mentre si lavorava. ⇒ Il rosso «atteso» del presidio versione
**non è più lo stesso rosso**: non è il debito noto, è il debito che ha
oltrepassato il limite che si era dato. Si chiude in due modi soli — si
pubblica, oppure si dichiara la distanza — e nessuno dei due è una decisione
tecnica.

### ② `PUBLISH_ANYWAY` — la scappatoia dichiarata

`build-and-publish` parte anche con la CI rossa se la variabile vale `1`. Non è
un difetto nascosto: il workflow lo annuncia e stampa un `::warning` quando il
cancello viene scavalcato. Misurato: `actions/variables` → `total_count: 0`.

    gh api repos/<owner>/<repo>/actions/variables

### ④ Il registro degli identificativi — VETO, e si richiude da solo

È il cancello che nessuno guarda, perché **non compare in nessun run di `ci`**:
vive dentro `publish.yml`, che parte al tag. Impedisce che gli identificativi
delle sessioni escano col pacchetto — finirebbero su PyPI e, nelle
`description` dei tool MCP, verrebbero letti a runtime dall'agente dell'utente.

**È stato riaperto almeno sei volte** (`git log`, per messaggio):

    registro: un mio commento di ieri fermava il veto del publish
    registro: l'ultima riga che il veto del publish trattiene
    registro: il docstring di _proposizione_di portava identificativi di sessione
    pkg: il wheel 0.7.6 portava fuori sette identificativi interni, adesso zero
    compat: un identificativo interno era finito nel pacchetto e bloccava il rilascio
    scripts: il controllo del registro non boccia più il collaudo che lo verifica

Il 26/08 si è richiuso **due volte in tre ore**. Non è disattenzione: è
strutturale. Scriviamo commenti densi mentre lavoriamo — lo prevede il commento
di `publish.yml` («il debito cresce perché scriviamo referti e commenti») — e i
banchi si chiamano `wsN-…` per costruzione (**29 file** in
`docs/stato-reale/banchi/`). Ogni citazione di un banco dentro `verimem/` chiude
il cancello.

Le due forme si curano in modo diverso:

- **attribuzione** — «(misurati da @wsN)»: si riformula la frase, il fatto resta;
- **path** — «`docs/stato-reale/banchi/wsN-…`»: l'identificativo è nel *nome del
  file*, riformulare non basta. O si cita il banco senza il nome, o i banchi
  nuovi si chiamano per contenuto (l'autore è nel `git log`, che non va su PyPI),
  o si usa il meccanismo di esenzione che lo script già prevede
  («esentate, con la ragione dichiarata»).

Presidiato da `tests/test_il_package_non_porta_identificativi_ADESSO.py`, che
rende visibile al push un blocco che prima si scopriva solo al tag.

    python scripts/controlla_registro.py verimem/          # veloce, perimetro vicino
    python -m build --wheel && python scripts/controlla_registro.py dist/*.whl

⚠️ **Il perimetro decide il numero.** Sul *sorgente* (2299 file .py) si contano
418 identificativi; sull'*artefatto* (422 file .py) **uno**. `tests/` e
`benchmark/` non entrano nel pacchetto. Un numero senza il suo perimetro qui non
significa nulla — errore commesso e ritirato il 26/08.

### ⑤ e ⑥ — avvisi, non veti, e lo dicono

`controlla_promesse.py` dichiara nel proprio docstring «uscita 0 SEMPRE: questo
non è un veto», con una ragione argomentata («un controllo che blocca sempre
viene disattivato»). Lo step sull'sdist si chiama, testualmente, «Cosa esce
nell'sdist e non è controllato (avviso, non veto)».

⚠️ `controlla_promesse` raggruppa per **stringa**, non per promessa: segnalava
«never silently — 12 occorrenze in 8 file» come un debito, e aperte le occorrenze
sono promesse **diverse** che condividono una formula. Curato il messaggio (non
l'algoritmo: separare promesse da formule chiede semantica), presidiato da
`tests/test_una_formula_condivisa_non_e_una_promessa_sola.py`.

### ⑦ Il blocco dentro il README

`pyproject.toml` dichiara `readme = "README.md"`: **quel file è la pagina di
PyPI**. Il README porta un blocco `⛔ RILASCIO — LEGGERE PRIMA DI PUBBLICARE`
che avverte che la nota sulla versione pubblicata diventa *falsa* nell'istante in
cui si pubblica. È l'unico vincolo scritto dove chi rilascia non può non vederlo.

---

## Il buco nella giuntura

Nessuno dei due file è sbagliato da solo, e insieme aprono una porta:

- `ci.yml` — il job che costruisce e installa il pacchetto ha
  `if: … && (github.event_name == 'push' || github.event_name == 'pull_request')`
  ⇒ **su `workflow_dispatch` quei job non girano**, e sono il meccanismo
  dichiarato di **G8**;
- `publish.yml` — il cancello filtra per **nome** e **ramo**, non per evento.

⇒ Un run di `ci` lanciato **a mano** su `main` che passa i test risulta
`success` e **aprirebbe il cancello senza aver costruito né installato il
pacchetto**.

**Non è mai successo**: su 60 run l'evento è `push` 60 volte, `workflow_dispatch`
zero. Ma il commento in cima a `ci.yml` *raccomanda* `workflow_dispatch` («un
verdetto si deve poter chiedere, non solo provocare») proprio per il problema
della coda satura — cioè la prima persona che segue quel consiglio per sbloccarsi
produce un verdetto incompleto che il cancello accetta.

Due cure possibili, entrambe da decidere (il cancello non si tocca senza mandato):
aggiungere `and .event=="push"` al filtro del gate — chiude la porta e lascia
`workflow_dispatch` utile per iterare; oppure togliere la condizione dal job del
pacchetto — rende un dispatch un run completo, al prezzo dichiarato nel commento
stesso («tre job per run … va rimisurato se la coda peggiora», e la coda **è**
peggiorata).

---

## Cosa è dichiarabile, il giorno del rilascio

Misurato da un'altra sessione il 26/08 e riportato qui perché è la frase che
finirà sulla vetrina:

- ✅ **dichiarabile**: «un claim che la fonte *apertamente contraddice* non torna
  come verità» — 0/10, 1/10 e 2/10 su tre classi di falsità, IT e EN, con i veri
  ammessi 19–20 su 20;
- ❌ **non dichiarabile**: «un claim che la fonte non sostiene» — oggi è
  **ammesso** 8/10 in IT e 9/10 in EN;
- ⚠️ fuori da IT/EN **non si spegne a un confine, degrada per gradi**:
  EN 2 · ZH 2 · JA 1 · KO 3 · AR 5 · HI 7 · TH 10 (su 10, in scrittura).

La differenza fra le prime due non è sfumatura: è la differenza fra «la memoria
non ti restituisce una falsità come vera» e «la memoria verifica ciò che scrivi».
Solo la prima regge alla misura.

### ⚠️ Il punto che un analista ostile colpirebbe per primo

Aggiunto il 27/08 dopo la matrice del commit «banco: la seconda garanzia non
degrada con la scrittura, si spezza sulla CIFRA». **Quell'8/10 è una media su
due popolazioni opposte**, e finché resta un numero solo è criticabile — non
come promessa falsa, ma come *media su popolazioni disomogenee*:

    lingua   dettaglio NUMERICO   dettaglio non numerico   veri rifiutati
    EN            0/3                    3/3                    0/1
    ZH            0/3                    2/3                    0/1
    JA            0/3                    3/3                    0/1
    KO            0/3                    2/3                    0/1
    AR            0/3                    3/3                    0/1
    HI            0/3                    3/3                    0/1
    ───────────────────────────────────────────────────────────────────
    totale       **0/18**              **16/18**

⇒ Il non sostenuto **non passa un po' dappertutto**: passa **quasi sempre**
quando il dettaglio aggiunto non porta una cifra, e **non passa mai** quando la
porta. Chi legge «8/10» conclude «ne ferma due su dieci»; il vero è «tutti o
quasi nessuno, a seconda che ci sia un numero».

📌 La riga di vetrina **regge**: `README.md:707` dichiara già, per iscritto,
«unsupported ones are admitted: 8/10 IT, 9/10 EN» — nessuno può dire «afferma
cose che non fa» su questo punto, ed è una cosa buona che sia scritta. Il rischio
è di *lettura*, non di promessa, e si chiude con una riga sola: separare le due
popolazioni. Chi tiene la vetrina decide se metterla.

⚖️ E vale anche per questo documento: la riga qui sopra («ammesso 8/10 in IT e
9/10 in EN») l'avevo scritta io poche ore prima **senza la separazione**. Un
registro che riporta una media ingannevole è peggio di nessun registro.

---

## Il tag

`v0.7.6` esiste **solo in locale** (`git ls-remote --tags origin` → zero
occorrenze) e `push.followTags` non è impostata: serve un atto esplicito.

⚠️ Punta a un commit che **precede tutte le cure** di questi giorni — al 26/08
sera la distanza era di 52 commit — e quel commit è, ironicamente, *esso stesso*
una cura del cancello ④. ⇒ Quando arriverà il via, **il tag va rifatto sul commit
giusto, non pushato**: un numero di versione, una volta su PyPI, non si riusa.
