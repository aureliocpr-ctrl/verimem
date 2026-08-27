# Un verde locale non è un verde in CI — dieci variabili che abbiamo e la CI no

*ws3 (Galileo), 27/08 sera, ~19:10. Misurato, non dedotto.*

## Il fatto

L'ambiente in cui eseguiamo i test — la shell della macchina di Aurelio —
esporta **dieci variabili** che governano il prodotto e che la CI non ha:

    ENGRAM_ADMISSION_GATE=1              ← accende il gate di ammissione
    ENGRAM_DECAY_ENABLED=1
    ENGRAM_BRIEFING_MIN_MATCHED=4
    ENGRAM_BRIEFING_THRESHOLD=0.40
    ENGRAM_TELEMETRY_PREFIXES=builtin
    ENGRAM_DATA_DIR=C:\Users\aurel\.engram
    HIPPO_DATA_DIR=C:\Users\aurel\.engram
    HIPPO_ENCODE_DELEGATE_ONLY=1
    HIPPO_EXPOSE_TOOLS=hippo_status,hippo_recall,…
    PYTHONUTF8=1

Non sono nel comando: sono **nell'ambiente**. Chi lancia `pytest` le eredita
senza saperlo, e chi riporta «è verde» sta riportando un verde **in quel
regime**, non in generale.

## Perché l'ho scoperto, e la forma dell'errore

Cercavo perché tre test che la CI riporta rossi fossero verdi da me. Il nome di
due di essi — «*un accento non decide se il gate scatta*», caso `[La latenza è
40 ms.]` — puntava alla codifica, e in memoria abbiamo già un rosso del 20/08
spiegato da `PYTHONUTF8`.

Ho tolto `PYTHONUTF8=1` **dalla riga di comando** e ho stampato il regime:
`utf8mode: 1`. Invariato. La variabile era già esportata, quindi credevo di
misurare «senza» e stavo **rimisurando lo stesso regime**.

> 🔑 **Togliere una guardia dal comando non è toglierla dall'ambiente.** Serve
> `X=0` (o `env -u X`), non l'assenza. Un controllo negativo che non spegne
> niente non controlla niente — e sembra un controllo riuscito.

È la nostra regola di casa («la prova che un criterio conta è che togliendolo il
numero cambi») applicata al livello che nessuno guardava: **l'ambiente**.

## Cosa ho misurato sui nove bloccanti

I nove test che @ws7 riporta come rossi (3 `FAILED` + 6 `errors at setup of`):

| regime | esito |
|---|---|
| normale (tutte le variabili) | **EXIT=0** — 1 + 9 + 6 passed |
| `PYTHONUTF8=0` (`utf8mode: 0`, `cp1252`) | **EXIT=0** — 10 passed |
| gate, decay, delegate-only, briefing, telemetry, expose-tools, utf8 **tutte spente** | **EXIT=0** — 16 passed |

Contesto raccolto nella stessa esecuzione: `date` 27/08 18:56 · HEAD
`63a7d129` · `git status --porcelain -- verimem/ tests/` **pulito**.

📌 I 6 «errors at setup of» sono **tutti nello stesso file**,
`tests/test_quanti_fatti_ho.py` — che ne contiene esattamente sei. «At setup»
significa che fallisce la **fixture**: una causa sola, non sei.

⚠️ **Non ho tolto le due `DATA_DIR`**: puntano allo store di Aurelio e
toglierle rischia una scrittura là dentro. Quella cella resta non misurata, ed
è dichiarata.

## Cosa ne segue, e cosa NON ne segue

**Non ne segue** che il rosso della CI non esista. Il mio albero contiene già le
cure del 26/08 sera (`16599716` delle 20:14 di ws8; il commit delle 22:30 di
Paragone), e ho già pagato una volta l'errore di «falsificare» una diagnosi
giusta perché il mio albero conteneva la cura altrui. Restano due letture, e il
dato per scegliere ce l'ha chi legge i run:

1. il run analizzato è **precedente** alle cure ⇒ rosso storico, già chiuso;
2. è **successivo** ⇒ rosso reale, e la differenza è nell'ambiente CI — ma
   **non** nella codifica né in queste sette variabili, che ho appena escluso.

⚠️ **Limite grosso e dichiarato**: io misuro su **Windows**, la CI su **Linux**.
Ho escluso *queste* variabili, non l'ambiente.

## Il presidio, e costa tre secondi

> **Prima di riportare un verde, dichiara il regime:**
> `env | grep -E "^(HIPPO|ENGRAM|VERIMEM|PYTHONUTF8)"`

Un verde senza il suo regime non è più informativo di un numero senza la sua
unità. E vale per tutte e otto, perché queste variabili stanno nella macchina,
non nelle nostre sessioni.
