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

Wheel: `verimem-0.7.6-py3-none-any.whl`, artefatto `dist` del run **`33785809525`**
(`#3072`, sha `d0a248a1`).
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
