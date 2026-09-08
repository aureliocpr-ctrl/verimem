# I difetti, e le pagine che li avevano già descritti

> **ws8 (Corrado), 08/09/2026.** Il contratto del rilascio completo chiede che ogni difetto
> noto sia **chiuso** (cura in main, RED/GREEN, perimetro) **oppure accettato per nome**,
> col numero che lo misura. Questo file serve a una cosa sola: **legare ogni ticket alle
> pagine che lo descrivevano già**, in ordine di data.
>
> Non è un indice per data né per autore: è **per difetto**. Nasce da un fatto misurato —
> T26a e T29 erano scritti in cinque pagine **un mese prima** che i ticket esistessero.

## T26a · T29 — la porta che non dice di non aver giudicato

| data | pagina | cosa dice |
|---|---|---|
| **08/08** | `02i-i-fatti-dei-primi-minuti-restano-non-verificati.md` | *«`warmup` risolve per il futuro; i fatti dei primi minuti restano non verificati **per sempre**»* — SHA `332a2f73`, HOME fredda, cache vuota |
| **30/08** | `39-le-finestre-cieche-della-memoria.md` | *«ventitré minuti, cinquantaquattro fatti»* — senza encode daemon il moat non gira, e i fatti scritti in quella finestra entrano `model_claim` mai giudicati |
| **30/08** | `48-ventitre-minuti-senza-daemon-hanno-spento-una-promessa-del-readme.md` | *«…e **resterà spenta**»* — **la prima metà è T26a, la seconda è T29** |
| **30/08** | `21-le-due-porte-gemelle-non-si-somigliano.md` | *«e quella sbagliata **tace**»* — misure alla porta MCP sullo store reale |
| **09/26** | `CHANGELOG.md`, voce `T26a` | il ticket, aperto **quasi un mese dopo** |

🔑 **Le misure c'erano. Mancava il filo.** Se questa tabella fosse esistita il 31 agosto, T26a
sarebbe stato aperto allora — e la **0.7.6**, pubblicata il 04/09, non sarebbe uscita con
dentro un difetto che quattro pagine avevano già descritto.

## 🧬 E non è una catena: è una CLASSE

Leggendo i titoli della famiglia «qualcosa tace» viene fuori che il difetto non è di una
porta, è **di forma**:

| pagina | l'asimmetria |
|---|---|
| `21` · `48` · `02i` · `39` | la porta MCP **non dice** di non aver giudicato — mentre la ricevuta lo saprebbe (`layers=['L4-skipped']`) |
| `31-la-porta-dei-documenti-dice-quello-che-quella-dei-fatti-tace` | **fra due porte**: quella dei documenti dichiara ciò che quella dei fatti tace |
| `38-il-regime-lo-dice-alla-risposta-e-lo-tace-alla-telemetria` | **fra due canali**: il regime arriva nella risposta e non nella telemetria |
| `70-la-cura-copre-il-caso-raro-e-tace-su-quello-frequente` | **fra due casi**: la cura parla del raro e tace sul frequente — «0 su 3» |

⇒ **La forma è una sola: il prodotto sa qualcosa e non lo dice sul canale dove qualcuno
guarda.** T26a ne è l'istanza più costosa perché il canale è `admitted`, che è quello che un
utente legge. Ma sono **quattro istanze indipendenti**, misurate da persone diverse in giorni
diversi, e nessuna delle quattro le nomina come la stessa cosa.

📌 **Questo è il pezzo che una mappa può dare e un ticket no**: il difetto non è «la porta MCP
tace», è «**questo prodotto ha l'abitudine di sapere e non dire, e succede su almeno quattro
superfici**».

## Come si continua

Per gli altri ticket (T14, T16, T24, T25, T27, T39, T40, D-1) la tabella è **da compilare**:
per ognuno, `grep` dei termini del difetto sui 287 documenti, poi **lettura** delle pagine che
escono — perché il grep trova i candidati e non li conta, ed è la lezione che questa mappa ha
pagato sette volte in una sera.
