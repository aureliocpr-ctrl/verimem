# Engram v1 — Definition of Done (FROZEN)

> Scopo: **spezzare il cerchio**. v1 si spedisce quando OGNI box qui sotto è ✅
> con una ricevuta verificabile (commit / CI / output). **Niente si aggiunge a
> questa lista.** Ogni idea nuova → backlog v1.1, NON blocca v1. Non dirò "pronto"
> finché i box non sono verdi; la pubblicazione è la TUA decisione.

## Blocker v1 (devono essere ✅ per spedire)

- [ ] **B1 — Nome scelto.** Non "engram"/"engram-memory" (presi/vietati).
      → decisione di Aurelio. Blocca B2.
- [ ] **B2 — Pubblicato e installabile.** `pip install <nome>` su macchina pulita
      → `import` funziona. Aurelio autorizza il publish; io eseguo la release.
      *È la linea letterale tra "pronto" e "in produzione".*
- [ ] **B3 — Quickstart cold VERIFICATO.** Uno sconosciuto segue il README
      install→save→recall su venv pulito + corpus vuoto e FUNZIONA. (Lo verifico
      a freddo, con transcript come prova.)
- [ ] **B4 — Coverage sui path core.** save / recall / write-screen coperti
      abbastanza che una regressione faccia fallire la CI. (Misura il % reale e
      alza i path core; oggi 46% overall = troppo basso per "produzione".)
- [ ] **B5 — Doc oneste.** README senza claim falsi + SECURITY.md presenti.
      (Largamente fatto questa sessione: 4 claim falsi fixati, 16× rimosso,
      SECURITY.md. → confermare zero claim falsi residui.)

## Esplicitamente FUORI da v1 (v1.1+, NON bloccano)

- entity-KG popolato (backfill OpenIE via LLM)
- immagine Docker slim
- split del monolite `mcp_server.py` (11.8k LOC)
- meccanismi neuro aggiuntivi / feature di ricerca
- benchmark paper / demo pubblica / adoption

## Stato onesto OGGI (2026-06-07)

| Box | Stato | Nota |
|---|---|---|
| B1 nome | ❌ | aspetta la tua scelta |
| B2 publish | ❌ | rinviato da te (PyPI è permanente — giusto non affrettare) |
| B3 cold-start | ⚠️ non verificato a freddo | il review dice che il path fresh funziona, ma NON l'ho testato cold io |
| B4 coverage core | ⚠️ da rimisurare a freddo | `semantic.py` 57.2% era un FLOOR FUORVIANTE (solo i file test_semantic_*+test_recall_*). Verificato: blocchi "scoperti" (es. `supersede_chain` 2273-2371) SONO testati da file dedicati (`test_supersede_chain.py`) esclusi dalla misura → coverage reale più alta. Il numero VERO richiede full-suite `--cov=engram.semantic` (pesante → quando Aurelio idle). |
| B5 doc oneste | ✅ | questa sessione |

## Regola anti-cerchio
Nessuna feature nuova entra in "v1". Quando TUTTI i blocker sono ✅ con ricevuta,
**è pronto** — e il publish è il tuo unico click. Fino ad allora: solo questi box.
