# 2026-09-13 — main rosso su una gamba su sei, e la gamba non c'entrava

* **Cosa** — `gh run view 34722126612`: su `cba765c4`, `test (macos-latest /
  py3.12): failure`, le altre **cinque** gambe `success`.
  `tests/test_due_guardie_si_coprono_e_nessuno_lo_sa.py::test_un_fatto_che_cita_l_id_di_un_altro_SENZA_contraddirlo_non_lo_ritira`,
  riga 138: *«CONTROLLO POSITIVO SPENTO: il secondo fatto e' entrato come
  'quarantined'»*.
* **Classe** — **rosso vero**. Non «instabile», non «macos»: il banco ha detto
  esattamente la verita', e il difetto che ha toccato e' nel prodotto.
* **Causa** — il giudice ha ammesso e un layer deterministico ha trattenuto lo
  stesso; l'innesco e' l'**id citato**, che e' casuale. Sotto, misurato.
* **Cura** — nessuna qui. La cura in avanti e' la richiesta #40, che aveva la
  causa dalle 17:40 del 12/09 e tre cure gia' proposte e **ritirate** con le
  ragioni scritte. Questo file le porta il meccanismo e il tasso.
* **Controllo** — `tests/test_il_setup_del_banco_non_deve_dipendere_dal_caso.py`
  (in #40) tiene il BANCO. Per il PRODOTTO il controllo **manca**, ed e' quello
  che nomino qui: una cella che chiami `valori_non_nella_fonte()` con un id
  **costruito** (`3642665edbce`) e pretenda zero valori. Senza, la cura del
  banco nasconde il difetto invece di chiuderlo.
* **Owner** — il banco: il perimetro di #40. Il difetto di `L4.1` sugli
  identificatori: **da assegnare**.

---

## La causa, misurata

Il journal delle due scritture, dallo stesso run:

```
fact_id=3642665edbce  grounding_score=99.775  judged=True  layers=[]
                      status=model_claim   withheld_despite_judge=False
fact_id=10da3854295a  grounding_score=99.956  judged=True  layers=['L4.1']
                      status=quarantined   withheld_despite_judge=True
```

Il giudice **ha girato** e ha dato 99,96: per lui la fonte sostiene il fatto.
A trattenerlo e' stato `L4.1`, e il prodotto lo dichiara nel campo
`withheld_despite_judge`.

Il claim del secondo fatto e' *«Nel verbale la coda aveva 500 elementi, come nel
fatto 3642665edbce.»* — dove `3642665edbce` e' l'id del primo fatto, **generato
a caso** (`uuid.uuid4().hex[:12]`, `verimem/semantic.py:1605`).

Chiamando il prodotto al livello in cui decide:

```
valori_non_nella_fonte(claim, source) sugli id di quel run
  3642665edbce  ->  🔴 L4.1: ['3642665 edbce']
  10da3854295a  ->  passa
  abcdefabcdef  ->  passa
  a1b2c3d4e5f6  ->  passa
  9977eb8024f5  ->  passa
  364266512345  ->  🔴 L4.1: ['364266512345']
  ffffffffffff  ->  passa
  500abcdefabc  ->  passa
```

**L'id viene letto come un valore con la sua unita' di misura**: `3642665` e'
il numero, `edbce` e' l'unita'. Un identificatore esadecimale che comincia con
abbastanza cifre *entra* nell'estrattore delle quantita', e siccome quel numero
nella fonte non c'e', il fatto viene trattenuto.

## Il tasso: non e' la piattaforma, e' un dado

```
id generati come il prodotto (uuid4().hex[:12]): 2000
fanno scattare L4.1: 17  ->  0,8%
esempi: 7504855cbead · 6265039240fd · 6321056477ec · 57275604594c · 211457142efb
```

Lo 0,8% e' **per gamba**: con sei gambe per run, la probabilita' che almeno una
cada e' circa il 4,7%. Su macos e' uscito il dado, e sui due merge precedenti
(`a9c8b4f6`, `bc1c0366`) la stessa gamba era `success`. Il commit che ha
«rotto» main non tocca `verimem/`: la richiesta #14 porta cricchetti, documenti
e postmortem, zero righe di prodotto.

⇒ **Chiamarlo «il rosso di macos» manda chi legge nella direzione sbagliata** —
lo cercherebbe nella piattaforma, e non e' li'.

## Perche' conta oltre al banco

Il banco e' l'unica cosa che oggi lo espone, ma l'ingresso non e' un caso di
laboratorio: **citare l'id di un altro fatto e' il modo normale di rettificare**
— la porta del prodotto lo prevede, e
`supersession_policy.references_fact()` cerca proprio l'id dentro il testo
nuovo. Un utente che scrive «come nel fatto <id>» ha una probabilita' su
centoventicinque di vedersi quarantenare un fatto vero, **con il giudice
d'accordo**, e la ricevuta glielo dice solo se legge `withheld_despite_judge`.

E il prodotto sa gia' che un identificatore non e' un numero: `quantity_match`
ha `_senza_identificatori()` e `_spans_dei_riferimenti()`. Il difetto e' che
`valori_non_nella_fonte()` non passa di li'. La cura sta in quella giuntura, non
in una soglia.
