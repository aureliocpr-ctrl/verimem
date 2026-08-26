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
| ① | la CI è verde sul commit **taggato** | `publish.yml`, job `gate` | **VETO** | 🔴 nessun run concluso |
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
