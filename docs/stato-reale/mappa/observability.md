# `verimem/observability.py` — 310 righe, 22 funzioni

*«Observability: structured logging, event bus, metrics registry.»* Tre meccanismi in un
file. Mappato su `7b9e8ca1`.

---

## 1. Tre meccanismi, e ciascuno ha il suo pezzo

| meccanismo | funzioni |
|---|---|
| **logging strutturato** | `_resolve_log_level` (43) · `route_logs_to_stderr` (66) · `get_log` (265) |
| **event bus** | `subscribe` (117) · `unsubscribe` (124) · `emit` (146) · `history` (165) · i cinque `_on_*` (233-254) |
| **metrics registry** | `inc` (188) · `observe` (192) · `gauge` (196) · `snapshot` (200) · `reset` (221) |

📌 `route_logs_to_stderr` (66): *«Re-route every structlog line to **stderr** (colors off)»* —
è la funzione che rende usabile un server MCP, dove **stdout è il protocollo**: una riga di
log su stdout romperebbe la comunicazione. Un dettaglio che vale un incidente.

📌 `unsubscribe` (124): *«No-op if absent»* — togliersi da un bus a cui non si è iscritti
non è un errore. Piccola cortesia che evita try/except ai chiamanti.

---

## 2. `_estratto` (275) — il campo tagliato senza mutilare ciò che porta

> *«Taglia un campo dichiarato ESTRATTO senza mutilare il graf[ema]…»*

⇒ Un troncamento **consapevole della codifica**: tagliare a byte in mezzo a un carattere
multi-byte produce un mojibake, e in un log italiano (o in un fatto con accenti) succede
subito. Il nome del campo dice **che è un estratto**, quindi chi legge non crede di avere
il testo intero.

🔑 È la stessa disciplina della mappa: **un valore parziale deve dichiarare di esserlo.**

---

## 3. Quello che questa mappa NON dice — dichiarato

- **`history` (165)**: c'è uno storico degli eventi in memoria. **Non so quanto è grande né
  se abbia un limite** — un bus con storico illimitato in un processo lungo è una perdita
  lenta, e questa è una domanda da porre, non un'accusa.
- **I cinque `_on_*`** (`_on_any_event`, `_on_episode_completed`, `_on_skill_synthesized`,
  `_on_skill_promoted`, `_on_skill_retired`) sono letti **solo di nome**: non so cosa fanno
  né chi li registra.
- **Non ho verificato** che `route_logs_to_stderr` sia chiamata da tutte le porte che ne
  hanno bisogno: sarebbe un grep, e il fatto che una sola porta se ne dimentichi
  romperebbe *quella* porta in modo difficile da diagnosticare.

---

*Mappato da ws5 (Tara) su `7b9e8ca1`.*
