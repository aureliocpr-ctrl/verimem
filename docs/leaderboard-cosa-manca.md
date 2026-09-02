# Agent Memory Leaderboard — che cosa ci manca davvero, in una pagina

> Secondo ciclo annunciato per il **20/09/2026**. Requisito riportato: **due
> endpoint pubblici, Add e Search, più uno smoke test**.
> Questa pagina risponde a una domanda sola: *quanto lavoro c'è fra noi e
> l'iscrizione?* La risposta breve è **meno di quanto sembra**, e il motivo è che
> la parte che di solito si costruisce — il servizio — è già scritta.

---

## Quello che c'è già, verificato nel pacchetto pubblicato

Non è un progetto: è un comando. Sul wheel `verimem 0.7.1` scaricato da PyPI:

| serve alla leaderboard | c'è | dove |
|---|---|---|
| **Add** | `POST /v1/memories` | `verimem/gateway.py:1047` |
| **Search** | `GET /v1/search` | `verimem/gateway.py:1178` |
| liveness per lo smoke | `GET /v1/health` | `verimem/gateway.py:956` |
| avvio | `verimem gateway serve` | documentato nel README |

E c'è **più** del minimo richiesto, già nel `--help` del comando pubblicato:

- `--host` — di default sta su loopback, e l'help dice da sé come va esposto:
  *«expose remotely behind a TLS reverse-proxy»*;
- `--rate-limit N` — massimo richieste al minuto per chiave, con `429` e
  `Retry-After` oltre la soglia;
- `verimem gateway keys create --tenant <slug>` — **ogni tenant ha uno store
  isolato**, quindi il valutatore non vede né tocca altri dati;
- `--plan free|pro|enterprise|self_host` sulla chiave.

Altri undici endpoint esistono e non servono per iscriversi (`/v1/answer`,
`/v1/explain`, `/v1/quarantine`, `/v1/stats`, `/v1/tiers`, `/v1/correct`…).

---

## Quello che manca, in ordine di rischio

**① La corrispondenza di forma fra i nostri Add/Search e i loro.** È l'unica voce
che potrebbe richiedere codice, e **non posso ancora valutarla: non ho la loro
specifica**. Le due possibilità sono un adattatore sottile (rinominare campi,
tradurre la risposta) oppure niente del tutto. Finché la specifica non è sul
tavolo, chiunque dica «bastano due giorni» sta indovinando — io compresa.
⇒ **Azione che sblocca tutto il resto: procurarsi la loro specifica di Add e
Search.** Con quella in mano il resto di questa pagina si chiude in un turno.

**② Un host pubblico con TLS.** Il prodotto non lo fornisce e lo dichiara
(«behind a TLS reverse-proxy»). Serve una macchina raggiungibile, un nome, un
certificato. Il dimensionamento non è un'incognita, perché lo abbiamo misurato:

| risorsa | quanto, misurato |
|---|---|
| disco, pacchetto | **~1,0–1,2 GB** (venv; `torch` da solo è ~527 MB) |
| disco, modelli al primo `warmup` | **~2,3 GB** (di cui il giudice 746 MB) |
| disco, totale primo avvio | **~3,3 GB** |
| tempo, `pip install` | 466 s (Windows) · 1315 s (WSL) — la differenza è `torch` |
| tempo, warmup senza giudice | 2 min 45 s a cache fredda |
| latenza, scrittura a regime | **~0,1–0,2 s** (processo vivo) |
| latenza, ricerca | **~0,3 s** |

Il gateway è un processo vivo, quindi la riga che conta è l'ultima coppia: **non**
i ~20 s della CLI, che sono avvio ripetuto e non riguardano un servizio.

**③ Lo smoke test.** Da scrivere, ma è la voce più economica: `GET /v1/health`,
una scrittura, una ricerca che la ritrova, esito dal codice d'uscita. La forma
esiste già in `scripts/smoke_utente_wsl.sh` e va solo puntata a un URL invece che
a un processo locale.

**④ Una decisione che non è tecnica: con quale giudice gira il servizio.** Se
l'host non ha il modello da 746 MB, il moat non ha giudice — e allora quello che
la leaderboard misura non è il prodotto che descriviamo. Questa non è una nota a
piè di pagina: è la differenza fra iscriversi e iscriversi *con la cosa che ci
distingue accesa*.

---

## Il rischio che porterei io al tavolo

La leaderboard misura **recall**: quanto ritrovi. Il nostro argomento è **quanto
di ciò che ritrovi regge**. Sono due grandezze diverse, e su un banco che premia
la prima un gate che trattiene può *costare* posizioni: i «veri persi» sono la
faccia B che pubblichiamo da soli, e lì si vedrebbe.

Non è un motivo per non iscriversi — è un motivo per **decidere prima cosa
diremmo di un risultato mediocre**. Se la risposta è «lo pubblicheremmo con la
faccia B accanto», allora l'iscrizione è coerente con tutto il resto di quello che
facciamo. Se la risposta è «dipende da come va», meglio saperlo adesso che il 20
settembre.

---

    rifallo con:
    verimem gateway serve --help
    verimem gateway keys create --help
    grep -n '@app\.\(post\|get\)' verimem/gateway.py
