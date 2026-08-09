# ⑧ — Sette osservazioni sugli artefatti, raccolte durante un rilascio

> **Artefatto**: `origin/main` `34d4d272`, worktree separato, `git status` vuoto.
> Le misure dettagliate stanno nei referti; qui restano le sette osservazioni che si applicano al
> prossimo rilascio. Ognuna riporta il caso misurato che l'ha prodotta.

---

## 1. Lo `sha256` identifica il file, non il contenuto

In un'ora sono esistiti **cinque** wheel «0.7.5», e due erano già stati collaudati come se fossero
distinti. La regola «chi nomina un wheel dichiara sha256 e ora» è corretta e non sufficiente:

```
wheel A (da 84a4a706)   sha256 d7e81cdc…
wheel B (da ec411ac1)   sha256 8370de61…
contenuto: 458 file contro 458 · solo in A: 0 · solo in B: 0 · DIVERSI: 0
```

Contenuto identico, impronte diverse: lo zip incorpora i timestamp, quindi lo `sha256` cambia a
ogni build anche senza modifiche. Due collaudi su wheel con `sha256` diversi possono concordare
legittimamente.
Per affermare che due wheel sono lo stesso occorre confrontare i file contenuti — una quindicina
di righe.

## 2. Un verdetto di merge scade come un conteggio

Un ramo usato come controllo negativo dava 1 conflitto; venti minuti dopo:

```
<ramo>        x main         → 0 conflitti
<ramo>        x origin/main  → 0 conflitti
origin/<ramo> x main         → 0 conflitti
origin/<ramo> x origin/main  → 0 conflitti
```

Il ramo non era cambiato (stesso SHA, `ec75d0c6`): era cambiato **main**, tre volte in pochi
minuti (`ec411ac1` → `661b364a` → `34d4d272`).

`git merge-tree` misura due oggetti in movimento; non è una proprietà del ramo. Il verdetto sul
ramo esaminato restava valido, il controllo negativo no.

## 3. Il README è dentro il pacchetto ed è permanente quanto il numero di versione

`Description-Content-Type: text/markdown`, e il corpo del METADATA è il README: la pagina
pubblicata su pypi.org. Nel primo wheel 0.7.5 era presente questa riga:

```
- **the CLI cannot delete at all.** `verimem forget` is not a command — of the
```

già ritirata come falsa, su un tema GDPR. PyPI non riusa un filename nemmeno dopo la cancellazione
della release: un README sbagliato nella 0.7.5 non si corregge, si passa alla 0.7.6.

«Correggere dopo» non era un'opzione, perché una delle due strade non esisteva. Ogni riga di
README è una riga di prodotto. Il banco automatico controlla i *comandi* che il README insegna; le
*affermazioni* può verificarle solo chi misura la porta corrispondente.

## 4. Un numero in un documento immutabile va ancorato a due estremi fissi

Il CHANGELOG riportava «419 commits since 0.7.0»: esatto alle 21:30, falso un'ora dopo (430, poi
433), perché il secondo estremo era HEAD.

Il numero corretto era un terzo ancora, per un difetto del metodo di conteggio: cercare il bump
con `git log -1 -S 'version = "0.7.0"'` trova, dopo il bump, il commit che quella riga ha
**rimosso**, non quello che l'ha introdotta. Serve `--reverse`.

| | |
|---|---|
| 0.7.0 → HEAD alle 21:59 | 430 |
| 0.7.0 → HEAD alle 22:05 | 433 |
| **0.7.0 → il commit del bump** | **420** — stabile |

Su main la formulazione è diventata «Over 400 commits», che risolve per altra via. La differenza
resta utile: la forma vaga non scade mai ma dirà lo stesso anche per la 0.8; la forma ancorata
dice cosa contiene *questa* release e resta vera.

## 5. `twine check` verifica che il markup renda, non che renda bene

Il controllo che PyPI esegue prima di accettare è una riga, e mancava:

```bash
python -m twine check dist/*.whl
```

Ha un limite misurato: due wheel dello stesso giorno, uno con 7 righe di tabella indentate dentro
un bullet e uno con 0, passano entrambi. Una tabella indentata non è un errore di sintassi: PyPI
la accetta e la rende male.
Copre «l'upload viene rifiutato», non «la pagina viene bene». Il limite è scritto nel test, perché
senza quella nota la riga verrebbe letta come una garanzia che non offre.

## 6. Un ramo già assorbito non può fare da controllo negativo

Il caso della voce 2 ha una formulazione più precisa di «main si muove»:

> **Un ramo mergiato dà zero conflitti per costruzione.**

Il controllo negativo va scelto fra i rami non ancora assorbiti e va ri-scelto quando vengono
assorbiti. Chi usa un controllo negativo ne dichiari l'SHA, come per i wheel.

## 7. L'errore che nasce mettendo accanto due misure entrambe corrette

> L'errore non è «misurare male»: nasce dall'affiancare **due misure giuste ottenute con metodi
> diversi**. La conclusione sembra più solida, perché ha due misure vere dietro.

Caso misurato: `419` (moduli ricorsivi, da git) accanto a `384` (primo livello, dal wheel) →
«35 mancanti», di cui 4 sarebbero stati moduli di governo. Nessuno dei due numeri era sbagliato.
Misurati con lo stesso metodo: git 388/419, wheel 388/419, **zero mancanti**.

Lo stesso schema si è ripetuto sui comandi: **52** (parser del sorgente), **40** (`--help`), **37**
(un terzo conteggio) — tre insiemi diversi con lo stesso nome. Lì il confronto sbagliato non ha
prodotto un falso allarme ma **un test cieco**: verificava i comandi del README contro il sorgente,
e avrebbe approvato `verimem tui`, che è definito e invisibile in `--help`.

Un numero non è confrontabile con un altro finché non è confrontabile il metodo. È la forma più
insidiosa perché non ha l'aspetto di un errore: due fonti, due misure, e una conclusione falsa.

---

## La forma comune

Tre volte in una sera due misure contrapposte erano **entrambe corrette** — sui cinque wheel, sui
tre conteggi, sul controllo negativo. Mai per un errore di misura: sempre perché l'oggetto
misurato era diverso, o era lo stesso oggetto in un istante diverso.

> Un artefatto non coincide con il suo nome. `verimem 0.7.5` sono stati sei file diversi in
> un'ora; `main` è stato quattro SHA in venti minuti. Chi consegna un verdetto dichiari su cosa
> l'ha misurato, e chi lo verifica usi lo stesso.

Lo strumento che risponde a metà di questa domanda è di due righe:

```bash
python scripts/artefatto.py
# verimem 0.7.5 · mcp 1.29.0 · da pacchetto · git n/d (misuri il pacchetto, non l'albero)
```

**Caveat**: una sera, un rilascio, un sistema operativo. Le sette voci sono generalizzazioni da un
caso ciascuna, tranne la 1, la 2 e la 7, che ne hanno due. Nessuna è stata verificata su un
secondo rilascio, perché un secondo rilascio non c'è ancora stato. Le voci 6 e 7 non provengono
dallo stesso fronte delle altre: sono state formulate da chi misurava altre superfici, e sono
riportate nella loro forma originale.
