# Smoke pre-tag — il registro delle prove sul wheel candidato

> Una riga qui vale solo se lo smoke **è stato eseguito**. Il cancello
> `scripts/cancelli_del_tag.py` pretende, per ogni campo, **nome + esito
> (`EXIT=n`) + data**: un blocco che elenca i campi senza esito non lo chiude —
> è stato rafforzato apposta, perché la prima versione si sarebbe accontentata
> di trovare la parola «windows».
>
> Comando: `bash scripts/smoke_wheel_pre_tag.sh <run-id> <versione-attesa>`
> Esiti: `0` tutti i passi · `1` almeno uno fallito · `2` prerequisito mancante
> (che **non** è un verdetto).

---

## 0.7.6

> **Tre blocchi, e vanno letti come tre cose diverse.** Il primo è lo smoke
> **valido per il tag**, sul wheel del commit candidato; il secondo è lo stesso
> smoke su un candidato **superato** — verde, e inutile; il terzo è la **prova
> generale** su un run rosso, che è servita a far sbagliare lo strumento quando
> lo sbaglio non costava niente. Solo il primo conta per i cancelli.
>
> 🔑 **L'intestazione di ogni blocco porta lo sha del commit, e non è
> decorazione**: il cancello riconosce il blocco pertinente da lì. Se lo sha
> stesse solo nella prosa, un blocco che *parla* del candidato senza esserlo
> verrebbe scambiato per suo — misurato il 2026-09-04, e il cancello si chiudeva
> con la riga `windows` di un altro pacchetto.

### Candidato `30b46361` — braccio **windows** passato, e NON basta per il tag della 0.7.7

Run **`34012404761`** (`#3118`, sha completo
`30b463615ccfb2e36116a4db9cda9394894544a0`), `completed/success`, **9 job su 9**.
Wheel `verimem-0.7.6-py3-none-any.whl`, **sha256
`fa8850e0366b83c7ee6862b53d45d0eadf59dd668f8d3a5db289819876da7734`**.

⚠️⚠️ **QUESTO BLOCCO NON CHIUDE IL CANCELLO DEL TAG 0.7.7, e lo dico qui perche'
il cancello da solo non se ne accorgerebbe.** Il commit `30b46361` porta
`pyproject = 0.7.6`, quindi il suo wheel e' una **0.7.6** e il cancello lo cerca
sotto `## 0.7.6`. Il tag della 0.7.7 sara' su un commit **che non esiste ancora**
— quello che alza le sei superfici — e il suo wheel avra' un'altra impronta.
**Quello smoke va rifatto li'.** Questo blocco prova una cosa piu' modesta e
comunque utile: *il codice di `30b46361`, impacchettato dalla CI, si installa e
fa quello che promette da utente vero*.

- **windows** — 2026-09-06 09:33, **`EXIT=0`**, 9 passi su 9 (ws8).

  | passo | misura |
  |---|---|
  | 3 · `pip install` del wheel | **341 s**; il pacchetto importato viene **dal venv** (`…\smoke-wheel\.venv\Lib\site-packages\verimem\__init__.py`) |
  | 4b · versione installata == attesa | `0.7.6`, con `mcp = 1.29.1` (tetto `mcp<2` rispettato) |
  | 7 · una fonte data viene **giudicata** | `grounding_score=99.35625457763672`, `judged=True`, `status=model_claim` |
  | 8 · un claim che la fonte smentisce è **fermato** | `grounding_score=1.0627778768539429`, `layers=['L4-grounding', 'L4.1']`, `status=quarantined` |
  | 9 · il server dichiara la **propria** versione | `server.version=0.7.6  verimem=0.7.6  mcp=1.29.1` |

  **Condizioni della macchina, lette PRIMA di lanciare** (regola del 06/09, perche'
  una misura presa su una macchina satura non e' la stessa misura): RAM libera
  **11,4 GB**, `AvailableMBytes` **11,43 GB**, **margine di commit 7,13 GB**
  (commit 54,43 su 61,56), **56 processi python** per 3397 MB.

  **Con quale script**: `scripts/smoke_wheel_pre_tag.sh` del ramo
  `ws8/smoke-dice-perche-pip-fallisce` (commit `f57731aa`), che rispetto a main
  cambia **solo** come riporta un fallimento di `pip` — nessun passo, nessuna
  soglia. Lo dichiaro perche' un registro che non dice con quale strumento e'
  stata presa la misura lascia la domanda a chi legge fra un mese.

- **wsl** — *non fatto*: il secondo braccio non e' mio. Il cancello li pretende
  **entrambi**, e sullo **stesso** wheel: si confronta lo `sha256` qui sopra, non
  il nome del file. I due bracci esistono perche' il 2026-09-02 lo stesso
  pacchetto dava `moat MISSING` su uno e `moat ON` sull'altro.

### Candidato `04911425` — smoke VALIDO per il tag

Run **`33802751438`** (`#3097`, sha completo
`049114259e5123516d76eec8148b5a9ab6f2646b`), `completed/success`, **9 job su 9**,
zero job non riusciti. Wheel `verimem-0.7.6-py3-none-any.whl`,
**sha256 `a99f64bc7a4a8267067dede9bb3fcc412f6f9dbdc3a64540f4aa1e1ec4411ee7`**.

⚠️ **L'impronta è il legame fra i due bracci, e cambia a ogni candidato.** Lo
stesso nome di file esce da ogni run: il candidato di ieri dava `76258b05…`, la
prova generale `f22259a4…`, questo `a99f64bc…`. Un braccio che riporta
un'impronta diversa **non ha provato questo pacchetto**, e la sua riga non vale
— anche se dice `EXIT=0`.

- **windows** — 2026-09-04 18:55, **`EXIT=0`**, 9 passi su 9 (ws8).

  | passo | misura |
  |---|---|
  | 7 · una fonte data viene **giudicata** | `grounding_score=99.35625457763672`, `judged=True`, `status=model_claim` |
  | 8 · un claim che la fonte smentisce è **fermato** | `grounding_score=1.0627778768539429`, `layers=['L4-grounding','L4.1']`, `status=quarantined` |
  | 9 · il server dichiara la **propria** versione | `server.version=0.7.6` con `mcp=1.29.1` |

  Prerequisiti: importato **dal venv** e non dal repo
  (`…\smoke-wheel\.venv\Lib\site-packages\verimem\__init__.py`), versione
  installata `0.7.6` uguale all'attesa, tetto `mcp<2` rispettato (`1.29.1`),
  `pip install` in 391 s.

- **wsl** — 2026-09-04 18:45, **`EXIT=0`**, 9 passi su 9 (lead-audit). Stesso wheel, **sha256 `a99f64bc7a4a8267067dede9bb3fcc412f6f9dbdc3a64540f4aa1e1ec4411ee7`** (scaricato con `gh run download 33802751438 -n dist`).

  | passo | misura |
  |---|---|
  | 7 · una fonte data viene **giudicata** | `status=model_claim grounding_score=99.35625457763672` |
  | 8 · un claim che la fonte smentisce è **fermato** | `status=quarantined grounding_score=1.0627774000167847` |
  | 9 · il server dichiara la **propria** versione | `server.version=0.7.6 verimem=0.7.6 mcp=1.29.1` |

  Prerequisiti: importato **dal venv** (`…/smoke-wheel/.venv/lib/python3.12/site-packages/verimem/__init__.py`), versione `0.7.6` uguale all'attesa, tetto `mcp<2` rispettato (`1.29.1`), `pip install` in 243 s. Ambiente: WSL Ubuntu 24.04, python3 3.12.3; il venv è stato creato senza `ensurepip` (assente e non installabile senza sudo) e popolato con `pip3 --python <venv>/bin/python install pip` tramite uno shim di `python` fuori dallo script, che è quello di `main` intatto (`--wheel`).

- **wsl, wheel SERVITO da PyPI** — 2026-09-04 19:18, **`EXIT=0`**, 9 passi su 9 (lead-audit), dopo il tag. File scaricato con `pip download verimem==0.7.6 --no-deps --no-cache-dir` da `files.pythonhosted.org/packages/4d/1b/0ce11179…/verimem-0.7.6-py3-none-any.whl`, **sha256 `a4c1125ad7140e5c25c09f4ecd3fe21b315ff1e82937a3b1d1ebc631830c1fe1`** — DIVERSO dall'artefatto provato (`a99f64bc…`) perché `publish.yml` ricostruisce il wheel invece di caricare l'artefatto della CI (LANT-175): confronto file per file, 465 file, 0 con contenuto diverso, 465 con solo il timestamp zip diverso. `pip install` in 144 s; passi 7/8/9 identici ai bracci sopra (99,356 · 1,063 quarantined · `server.version=0.7.6`). Un primo tentativo era caduto al passo 3 in 1 s perché il file era stato rinominato: pip esige il nome standard del wheel; lo script installava con `--quiet` e l'errore di pip usciva PRIMA della riga di esito, senza etichetta, in mezzo agli altri otto passi. 🪞 **Correzione del 06/09**: qui avevo scritto «non stampa l'errore di pip», e provandolo con un finto interprete che scrive su stderr ed esce 1 e' risultato FALSO — `--quiet` sopprime l'output informativo, non stderr, e l'errore usciva comunque. Avevo letto «non l'ho visto» come «non lo stampa». Curato lo stesso (`f57731aa`), ma per la ragione vera: adesso esce DOPO la riga di esito e con l'etichetta «pip dice», e resta su file per chi esegue lo smoke dentro un wrapper che redirige stderr.

### Candidato `8fca33f0` — SUPERATO, verde e inutile per questo tag

Run `33793094834` (`#3090`), `completed/success`, 9 job su 9. Wheel
`verimem-0.7.6-py3-none-any.whl`,
sha256 `76258b0542557fba4325e8c8644c59132b9fb53b14364974ca0f11878f4ea0f1`.

- **windows** — 2026-09-03 22:14, `EXIT=0`, 9 passi su 9 (ws8). Stesse tre
  misure ai passi 7-8-9, `pip install` in 393 s.
- **wsl** — *(mai eseguito: il candidato è cambiato prima)*

⚠️ **Questo blocco è verde e non serve a niente per il tag.** Il commit da
taggare ha un altro sha, e questo wheel un'altra impronta. Resta scritto perché
un registro che cancella le prove superate insegna a fidarsi dell'ultima riga
invece che dello sha — l'errore preciso che l'impronta serve a impedire.

### Prova generale — wheel di un run ROSSO, NON valida per il tag

Wheel: `verimem-0.7.6-py3-none-any.whl`, artefatto `dist` del run **`33785809525`**
(`#3072`, sha `d0a248a1`), **sha256 `f22259a4fbba85542d1935bb2ebb2359f530b3e14cb384f8ad572c696c7d47c6`**.
⚠️ Quel run è `completed/failure` **nel complesso** — sei job `test` rossi — ma i
tre job che producono e provano il pacchetto sono verdi: `build (sdist + wheel)`,
`wheel install-from-scratch (windows-latest)`, `wheel install-from-scratch
(ubuntu-latest)`. **Lo smoke prova il pacchetto, non sostituisce il verde della
suite**: il cancello «CI verde sul commit del tag» resta aperto e va chiuso a
parte.

- **windows** — 2026-09-03 21:11, **`EXIT=0`**, 9 passi su 9 (ws8, prova generale).
  Dettaglio dei tre passi che provano le cure della release:

  | passo | misura |
  |---|---|
  | 7 · una fonte data viene **giudicata** | `grounding_score=99.35625457763672`, `judged=True` |
  | 8 · un claim che la fonte smentisce è **fermato** | `grounding_score=1.0627778768539429`, `layers=['L4-grounding','L4.1']`, `status=quarantined` |
  | 9 · il server dichiara la **propria** versione | `server.version=0.7.6` con `mcp=1.29.1` |

  E i prerequisiti: pacchetto importato **dal venv** e non dal repo
  (`…\smoke-wheel\.venv\Lib\site-packages\verimem\__init__.py`), versione
  installata `0.7.6` uguale all'attesa, tetto `mcp<2` rispettato (`1.29.1`),
  `pip install` del wheel in 389 s.

- **wsl** — *(da eseguire: braccio di @lead-audit)*

### Cosa questo blocco NON dice

Un solo sistema operativo. I due bracci esistono perché il 2026-09-02 **lo stesso
pacchetto** dava `moat-judge MISSING` su WSL e `moat is ON` su Windows: un braccio
solo non è una prova, è metà di una. Finché manca `wsl` con il suo esito e la sua
data, il cancello resta aperto — ed è giusto che lo sia.

### Difetti trovati dalla prova generale, prima che servisse davvero

Lo smoke ha fallito **due volte** prima di girare, e in entrambi i casi il difetto
era nello strumento, non nel pacchetto:

1. `gh run download` girava nella cartella temporanea, **fuori dal repo**, dove
   `gh` non sa quale repository interrogare. L'errore («no such file or
   directory» sulla cartella degli artefatti) sembrava «non ci sono artefatti».
2. Aggiunto `-R`, il repository veniva risolto come `owner/nome.git`: l'API
   rispondeva **404 sugli artefatti** — di nuovo un errore che sembra «artefatti
   mancanti» ed è un nome sbagliato. Il `.git` va tolto con una sostituzione sua,
   perché dentro un solo regex il gruppo se lo mangia.

🔑 Entrambi si presentavano come **«l'artefatto non c'è»**. Se avessimo eseguito
questo smoke la prima volta il giorno del tag, avremmo concluso che la CI non
produce artefatti — e sarebbe stato falso. **Una prova generale serve a far
sbagliare lo strumento quando lo sbaglio non costa niente.**
