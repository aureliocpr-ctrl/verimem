# Distribuzione — come si scoprono, si installano e si pubblicano gli strumenti di memoria per agenti (letture del 02/09/2026)

> **Cos'è**: la sezione D dello stato dell'arte, chiusa da un secondo ricercatore
> (Claude Opus, sola lettura) con misure dirette: il registry MCP ufficiale paginato
> per intero, le wheel scaricate e lette, gli endpoint di download interrogati. Ogni
> numero ha URL e ora; «non trovato» dove manca. Sostituisce la D provvisoria di
> `2026-09-02-stato-dell-arte-prodotti-e-benchmark.md`.
> **Le quattro righe operative**: (1) per `uvx` serve un console script in
> `[project.scripts]` — `mem0ai` non ce l'ha; (2) il registry MCP ha 26.376 server, si
> entra con una riga `mcp-name:` nel README e la latenza dopo PyPI è 78 secondi;
> (3) il marketplace community di Claude Code ha 2.282 plugin e un form di submission
> (`claude plugin validate` prima); l'ufficiale è a discrezione di Anthropic, senza
> application; (4) l'unico conteggio pubblico di installazioni reali è claude.com/plugins
> (il plugin di memoria «Remember»: 51.442 install).

---

## D.0 — Il quadro in una riga

Non esiste **un** canale. Ne esistono cinque, e sono disgiunti: il **registry ufficiale MCP** (metadati, in *preview*), i **marketplace di plugin di Claude Code** (l'unico canale che pubblica numeri di installazione reali), le **directory di terze parti** (Glama/Smithery/mcp.so/PulseMCP), i **package manager** (npm/PyPI, dove si misura la trazione vera) e la **directory connettori di Anthropic**. Il registry ufficiale **dichiara esplicitamente di non essere il canale di installazione**.

---

## D.1 (a) — MCP Registry ufficiale

### Stato: PREVIEW, non GA

| Fatto | Testo verbatim | URL |
|---|---|---|
| Stato | «The MCP Registry is currently in preview. Breaking changes or data resets may occur before general availability.» | https://raw.githubusercontent.com/modelcontextprotocol/registry/main/docs/modelcontextprotocol-io/about.mdx |
| Stato (README) | «this is still a preview release and breaking changes or data resets may occur» | https://github.com/modelcontextprotocol/registry |
| API freeze | «The Registry API has entered an API freeze (v0.1)… the API will remain stable with no breaking changes» | https://github.com/modelcontextprotocol/registry |
| Cos'è | «the official centralized metadata repository for publicly accessible MCP servers, backed by major trusted contributors to the MCP ecosystem such as Anthropic, GitHub, PulseMCP, and Microsoft» | about.mdx (URL sopra) |
| **Chi lo deve consumare** | «The MCP Registry is **not** intended to be directly consumed by host applications. Instead, host applications should consume other MCP registries, such as downstream marketplaces, via a REST API.» | about.mdx |
| Aggregatori | «scrape data on a regular but infrequent basis (e.g., once per hour)»; «does not provide uptime or data durability guarantees» | https://raw.githubusercontent.com/modelcontextprotocol/registry/main/docs/modelcontextprotocol-io/registry-aggregators.mdx |
| Repo GitHub | 7.214 stelle, ultimo push 2026-08-26T23:33:36Z | https://api.github.com/repos/modelcontextprotocol/registry |
| Release `mcp-publisher` | tag **v1.8.1**, pubblicata 2026-08-06T23:35:18Z (asset darwin/linux amd64+arm64, con SBOM e sigstore) | https://api.github.com/repos/modelcontextprotocol/registry/releases/latest |

Nota di dissonanza: il **tool** è a v1.8.1, l'**API** è congelata a v0.1, il **servizio** è in preview. Sono tre versioni di tre cose diverse.

### Quanti server sono listati oggi — MISURATO

**Non esiste un endpoint di conteggio.** L'OpenAPI (https://raw.githubusercontent.com/modelcontextprotocol/registry/main/docs/reference/api/openapi.yaml) espone solo `/v0.1/servers`, `/v0.1/servers/{name}/versions`, `/v0.1/publish` e gli endpoint di stato: nessun `/stats`.

Il ricercatore ha **paginato l'intera API** (`GET /v0/servers?limit=100&version=latest`, cursore su `nextCursor`):

| Misura | Valore | Metodo |
|---|---|---|
| Pagine percorse | 264 (terminate su `nextCursor` assente) | script con rilevamento errori HTTP |
| **Server unici (`version=latest`)** | **26.376** | estratti i campi `"name"`, filtrati sul pattern reverse-DNS dello schema, deduplicati |
| Controllo di coerenza | 264 × 100 = 26.400 (limite superiore) vs 26.376 misurati | coerente |
| Errori transitori | 1 (HTTP code=000 a pagina 170), ritentato | `err_latest.txt` |
| Finestra di misura | 2026-09-02, ~10:44 → 10:55 UTC | `date -u` nella stessa esecuzione |
| Con `memor|recall|remember` nel nome | **245** (0,93%) | stesso file |
| Namespace `io.github.*` | **17.997** (68,2%) | stesso file |
| Stato incluso | `active` **e** `deprecated` (1 su 100 in un campione) | `grep '"status"'` su due pagine |

⚠️ **Trappola verificata**: il **primo** conteggio ha dato **5.841** e si è fermato a 55 pagine. Causa: una risposta vuota transitoria non contiene `nextCursor`, e un loop ingenuo la legge come «fine lista». Un conteggio di questo registry **senza rilevamento errori HTTP produce un numero silenziosamente troncato**. Il 26.376 viene dalla versione con retry.

Nessun **conteggio ufficiale pubblicato** dal progetto (FAQ, about, README: nessun numero). Un articolo di terze parti citato dai motori di ricerca riportava «9.652 latest server records al 24/05/2026», ma **fetchando l'articolo (safedep.io, datato 2025-12-20) quel numero non c'è**: attribuzione non verificata ⇒ **non usato**.

### Come si pubblica

Fonte: https://raw.githubusercontent.com/modelcontextprotocol/registry/main/docs/modelcontextprotocol-io/quickstart.mdx

```bash
# 1. install
brew install mcp-publisher
#    (oppure tarball da github.com/modelcontextprotocol/registry/releases/latest)

# 2. marcatore di proprietà nel package (vedi tabella sotto)
# 3. pubblica il package su npm/PyPI/...
# 4. genera il manifest
mcp-publisher init
# 5. autentica
mcp-publisher login github
# 6. pubblica
mcp-publisher publish
```

### `server.json` — campi obbligatori (dallo schema, non dalla prosa)

Schema letto: https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json

| Livello | `required` | Altri campi |
|---|---|---|
| `ServerDetail` (radice) | **`name`, `description`, `version`** | `$schema`, `_meta`, `icons`, `packages`, `remotes`, `repository`, `title`, `websiteUrl` |
| `Package` | **`registryType`, `identifier`, `transport`** | `environmentVariables`, `fileSha256`, `packageArguments`, `registryBaseUrl`, `runtimeArguments`, **`runtimeHint`**, `version` |

`name` — verbatim dallo schema: «Server name in reverse-DNS format. Must contain exactly one forward slash separating namespace from server name.» — pattern `^[a-zA-Z0-9.-]+/[a-zA-Z0-9._-]+$`, minLength 3, maxLength 200, esempio `io.github.user/weather`.

`registryType` — valori: `npm`, `pypi`, `nuget`, `cargo`, `oci`, `mcpb` (https://raw.githubusercontent.com/modelcontextprotocol/registry/main/docs/modelcontextprotocol-io/package-types.mdx).

### Namespace e verifica

Fonte: https://raw.githubusercontent.com/modelcontextprotocol/registry/main/docs/modelcontextprotocol-io/authentication.mdx

| Metodo | Comando | Namespace concesso | Prova richiesta |
|---|---|---|---|
| GitHub OAuth | `mcp-publisher login github` | `io.github.<user>/*`, `io.github.<org>/*` | device flow; per l'org serve ruolo **Owner**; PAT con scope `read:org`, «Either way the token needs no repository scopes» |
| GitHub OIDC | `./mcp-publisher login github-oidc` | idem, da GitHub Actions | `permissions: id-token: write`, `contents: read` (https://raw.githubusercontent.com/modelcontextprotocol/registry/main/docs/modelcontextprotocol-io/github-actions.mdx) |
| DNS | `mcp-publisher login dns --domain <D>` | `com.example.*/*` (reverse-DNS) | TXT `v=MCPv1; k=ed25519; p=${PUBLIC_KEY}`; verbatim: «The TXT record must be placed on the apex of your domain». Ed25519 / ECDSA P-384; supporto Google KMS e Azure Key Vault |
| HTTP | `mcp-publisher login http --domain <D>` | idem | file su `/.well-known/mcp-registry-auth`, stesso formato |

⚠️ verbatim da `authentication.mdx`: un token di namespace d'organizzazione «can publish — and overwrite — **any** server under `io.github.<org>/*`».

### Proprietà del pacchetto (npm / PyPI / NuGet / OCI)

Fonte: `package-types.mdx`

| Registry | Marcatore | Regola verbatim |
|---|---|---|
| npm | `mcpName` in `package.json` | «MUST match the server name from `server.json`» |
| **PyPI** | stringa **`mcp-name: $SERVER_NAME`** nel **README** | «The string may be hidden in a comment, but the `$SERVER_NAME` portion MUST match the server name from `server.json`» — serve un boundary (newline, whitespace, tag HTML o chiusura commento), non attaccata a punteggiatura |
| NuGet | `mcp-name: $SERVER_NAME` nel README | idem |
| OCI/Docker | annotation `io.modelcontextprotocol.server.name` | «MUST match the server name» |
| MCPB | URL deve contenere `mcp` + `fileSha256` con lo SHA-256 dell'artefatto | — |

**Verifica su un caso reale** — `@modelcontextprotocol/server-memory` v2026.8.31 (npm) **dichiara** `mcpName: "io.github.modelcontextprotocol/server-memory"` (https://registry.npmjs.org/@modelcontextprotocol%2Fserver-memory/latest). Ma il registry ufficiale risponde **0 versioni** per quel nome e **0 server** sotto tutto il namespace `io.github.modelcontextprotocol`. Controllo positivo sullo stesso endpoint: `io.github.basicmachines-co/basic-memory` restituisce **9 versioni** ⇒ il metodo funziona. **Il server memory di riferimento ha il marcatore ma non è nel registry ufficiale.**

---

## D.2 (b) — Claude Code plugin marketplace

### Creare un marketplace

File: `.claude-plugin/marketplace.json` — https://code.claude.com/docs/en/plugin-marketplaces

Campi **obbligatori**: `name` (kebab-case, senza spazi/caratteri di controllo/bidi; «Each user can register only one marketplace per name»), `owner` (oggetto con `name` obbligatorio; `email`/`url` opzionali), `plugins` (array; ogni voce richiede `name` e `source`).

```json
{
  "name": "my-plugins",
  "owner": { "name": "Your Name" },
  "plugins": [
    { "name": "quality-review-plugin",
      "source": "./plugins/quality-review-plugin",
      "description": "Adds a quality-review skill for quick code reviews" }
  ]
}
```

Nomi **riservati** ad Anthropic (impersonation): `claude-code-marketplace`, `claude-code-plugins`, `claude-plugins-official`, `claude-plugins-community`, `anthropic-marketplace`, `anthropic-plugins` e altri.

### Requisiti di un plugin

`.claude-plugin/plugin.json` — https://code.claude.com/docs/en/plugins-reference

- **Unico campo obbligatorio: `name`** (e il manifest stesso è opzionale se i componenti stanno nelle posizioni di default).
- Struttura: `skills/<nome>/SKILL.md`, `commands/*.md`, `agents/*.md`, `hooks/hooks.json`, `.mcp.json`, `.lsp.json`, `monitors/monitors.json`, `bin/`, `settings.json`.
- ⚠️ verbatim: «Don't put `commands/`, `agents/`, `skills/`, or `hooks/` inside the `.claude-plugin/` directory. Only `plugin.json` goes inside `.claude-plugin/`.»
- Un server MCP si distribuisce come plugin mettendo `.mcp.json` alla radice del plugin: «Start automatically when plugin is enabled».
- Test locale: `claude --plugin-dir ./my-plugin` (accetta anche uno `.zip`), `claude --plugin-url <zip>`, ricarica con `/reload-plugins`.

### Aggiungere un marketplace

```
/plugin marketplace add owner/repo          # GitHub shorthand
/plugin marketplace add owner/repo@v2.0.0   # pin a tag/branch
/plugin marketplace add https://gitlab.com/team/plugins.git
/plugin marketplace add ./my-marketplace
/plugin marketplace add https://example.com/marketplace.json
/plugin install <nome>@<marketplace>
```
https://code.claude.com/docs/en/discover-plugins

### Marketplace ufficiali di Anthropic — ed è QUI il numero interessante

Fonte primaria: https://code.claude.com/docs/en/plugins#submit-your-plugin-to-the-community-marketplace

| Marketplace | Come si aggiunge | Plugin listati (letti 2026-09-02) |
|---|---|---|
| `claude-plugins-official` (curato) | registrato **automaticamente** al primo avvio interattivo; altrimenti `claude plugin marketplace add anthropics/claude-plugins-official` | **291** — https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/.claude-plugin/marketplace.json |
| `claude-community` | `/plugin marketplace add anthropics/claude-plugins-community`, install come `@claude-community` | **2.282** — https://raw.githubusercontent.com/anthropics/claude-plugins-community/main/.claude-plugin/marketplace.json |
| `claude-code-plugins` (demo) | `/plugin marketplace add anthropics/claude-code` | non contato |

Di quelli, con `memory|recall|knowledge graph` in nome o descrizione: **151 su 2.282** nel community, **3 su 291** nell'ufficiale (conteggio del ricercatore, keyword match su `name`+`description`, quindi ampio e non curato).

**Come si entra**:
- **Community**: form in-app — https://claude.ai/admin-settings/directory/submissions/plugins/new (richiede org Team/Enterprise e directory management access) **oppure** https://platform.claude.com/plugins/submit (Console, per autori individuali). Prima: `claude plugin validate ./your-plugin` (stampa `✔ Validation passed`; `--strict` tratta i warning come errori). Verbatim: «Approved plugins are pinned to a specific commit SHA in the `anthropics/claude-plugins-community` catalog, and CI bumps the pin automatically as you push new commits»; «The public catalog syncs nightly from the review pipeline».
- **Ufficiale**: verbatim — «The official marketplace, `claude-plugins-official`, is curated separately. **Anthropic decides which plugins to include at its discretion. There is no application process, and the submission form does not add plugins to the official marketplace.**»

### L'altro canale: `claude mcp add` e la directory connettori

https://code.claude.com/docs/en/mcp — `claude mcp add --transport http <name> <url>`, `claude mcp add --transport stdio <name> -- npx -y <pkg>`, `claude mcp add-json`, `/mcp`, `.mcp.json` di progetto, `claude mcp add-from-claude-desktop`, scope `local|project|user`. Verbatim: «Browse reviewed connectors in the **Anthropic Directory** (https://claude.ai/directory). Directory connectors use the same MCP infrastructure as Claude Code». **Claude Code non naviga il registry ufficiale MCP.**

Il contenuto di claude.ai/directory: **non trovato** — la pagina risponde HTTP 403 a fetch non autenticato, e il tool `search_mcp_registry` disponibile nella sessione del ricercatore ha restituito `{"results":[]}` anche sul **controllo positivo** `["github","slack","notion"]` ⇒ il canale non risponde da lì, e **l'assenza di risultati non è evidenza di assenza di connettori**.

---

## D.3 (c) — Directory di terze parti

| Directory | N. server (letto 2026-09-02) | Come si viene listati | Metriche pubblicate |
|---|---|---|---|
| **Glama** https://glama.ai/mcp/servers | **81.643** («Updated 2026-09-02 10:21»); il `<title>` letto alle ~10:52 UTC diceva **81.661** | **Non automatico**, per la pagina metodologia: «Before a server is listed, the submitting maintainer authenticates through GitHub OAuth»; «Glama verifies that the submitter has write or admin access to the repository»; «Servers cannot be submitted on behalf of someone who does not control the source» — https://glama.ai/mcp/methodology ⚠️ i riassunti di terzi dicono «auto-indexes from GitHub»: **contraddetto dalla fonte primaria**, che descrive un modello a claim | UI ordinabile per Weekly downloads / GitHub stars / Recent usage; la metodologia dichiara invece di **non** puntare sulla popolarità ma su TDQS (Tool Definition Quality Score), profili comportamentali, drift. Numeri dichiarati nella metodologia: «over one million scans» in 12 mesi, 856 tool su 103 server nello studio TDQS, 10.831 server esaminati per difetti di documentazione |
| **PulseMCP** https://www.pulsemcp.com/servers | **21.979** («Showing 1 - 42 of 21,979 servers») | ⛔ **Sospeso.** Verbatim da https://www.pulsemcp.com/submit: «Apologies, submissions and changes are temporarily paused… Until mid-August, we are not accepting new MCP server or client submissions… if you have a server to share, **publish it to the Official MCP Registry**. That is the best first step even when we are not paused, and we will pick it up automatically once we are back.» (pagina ancora così il 2026-09-02, © 2026) | «Est Visitors (Week)» per server. ⚠️ **sono stime modellate, non misure**: «Derived from a blend of SEO signals, web presence indicators, and calibration against known adoption data. Certainly not perfect»; i download sono «Composed of a blend of registry download counters, social signals, web traffic, and more» — https://www.pulsemcp.com/statistics. I valori numerici della pagina statistiche sono renderizzati in JS: **non trovati** nell'HTML |
| **Smithery** https://smithery.ai | **«Browse 17.710+ MCPs»** | https://smithery.ai/docs/build/publish: «Go to smithery.ai/new», «Enter your server's public HTTPS URL». **Nessun `smithery.yaml` richiesto** nella via URL; per i locali serve un bundle `.mcpb`; opzionale `/.well-known/mcp/server-card.json`. **Nessun collegamento GitHub obbligatorio**, e l'hosting resta tuo: «Bring your own hosting — Smithery Gateway proxies to your upstream server» | **Sì**: «uses» per server visibili in home (es. OneSignal «22.49k uses», Agent News «43.39k uses») |
| **mcp.so** https://mcp.so/servers | **18.151** (campo `total:18151` nel payload della pagina) | Form su https://mcp.so/submit?type=server (Repository URL + tipo). Due vie, verbatim dalla meta description: «Choose **free review** or publish immediately with **Premium**». Premium = **$39 one-time publishing fee**: publish immediately without review, verified badge, featured/priority placement, dofollow link | Pubblicano il **traffico del sito**, non gli install: Domain Rating 72, Backlinks 57,16K, Ref. Domains 2,58K, Unique visitors (12 mo) 2,2M, Pageviews (12 mo) 6M, Monthly active users 266K (↑ 11,2%). I campi `installCount`/`stars` esistono nel payload ma erano `void 0` (non popolati) nelle voci ispezionate |
| **awesome-mcp-servers** https://github.com/punkpeye/awesome-mcp-servers | **93.780 stelle**, 15.463 fork, ultimo push 2026-09-01T07:26:30Z (https://api.github.com/repos/punkpeye/awesome-mcp-servers) | Pull request. Regole (CONTRIBUTING.md): «The server name, linked to its repository», «A brief description», «Categorize the server appropriately», «One server per line», ordine alfabetico. **Nessun requisito** di open source o README | Nessuna |

---

## D.4 (d) — PyPI e npm: misurare la trazione, ed essere installabili con `uvx`

### Come si misura

| Canale | Endpoint | Note operative verificate oggi |
|---|---|---|
| PyPI | `https://pypistats.org/api/packages/<pkg>/recent` → `last_day`/`last_week`/`last_month`; `/overall?mirrors=false` → serie giornaliera | **Rate limit aggressivo e non documentato numericamente**: `429 RATE LIMIT EXCEEDED` per ~40 minuti su richieste sporadiche. L'etiquette (https://pypistats.org/api/) non dichiara una soglia; dice «All download stats exclude known mirrors», «Time series data is retained only for 180 days», «updated once daily» |
| npm | `https://api.npmjs.org/downloads/point/last-week/<pkg>` (e `last-month`) | Nessun rate limit incontrato. Restituisce `start`/`end` espliciti: **la finestra è dichiarata**, usarla |
| npm (search) | `https://registry.npmjs.org/-/v1/search?text=…` restituisce anche `downloads.weekly` | **Validato**: `@letta-ai/letta-client` = 86.817 sia via search sia via downloads API |

### Cosa serve per essere installabile con `uvx`

Fonte: https://docs.astral.sh/uv/guides/tools/ — «When `uvx ruff` is invoked, uv installs the `ruff` package which provides the `ruff` command»; se il nome del comando ≠ nome del pacchetto serve `--from` («`http` which is provided by `httpie`» → `uvx --from httpie http`); «Unlike `uvx`, `uv tool install` operates on a _package_ and will install all executables provided by the tool».

⇒ Il requisito concreto è **un console script**: `[project.scripts]` in `pyproject.toml`, che finisce in `<dist-info>/entry_points.txt` nella wheel.

**Verifica empirica su due wheel scaricate oggi**:

| Pacchetto | Wheel | `entry_points.txt` | Conseguenza |
|---|---|---|---|
| `basic-memory` 0.23.2 | `basic_memory-0.23.2-py3-none-any.whl` | `[console_scripts]`<br>`basic-memory = basic_memory.cli.main:app`<br>`bm = basic_memory.cli.main:app` | `uvx basic-memory mcp` funziona |
| `mem0ai` 2.0.19 | `mem0ai-2.0.19-py3-none-any.whl` | **assente** | **nessun eseguibile** ⇒ `uvx mem0ai` non ha un comando da lanciare |

Lato registry, ciò che va dichiarato in `server.json` è `runtimeHint` — verbatim dallo schema: «A hint to help clients determine the appropriate runtime for the package. This field should be provided when `runtimeArguments` are present», esempi `npx`, **`uvx`**, `docker`, `dnx`.

**Esempio reale, letto dall'API** (`?search=basic-memory`):

```json
"packages": [{
  "registryType": "pypi",
  "identifier": "basic-memory",
  "version": "0.23.2",
  "runtimeHint": "uvx",
  "transport": { "type": "stdio" },
  "runtimeArguments": [
    { "value": "basic-memory", "type": "positional" },
    { "value": "mcp",          "type": "positional" }
  ]
}]
```

**Latenza di pubblicazione misurata** su quel pacchetto: upload su PyPI `2026-08-25T20:44:42Z` (https://pypi.org/pypi/basic-memory/json) → `publishedAt` nel registry `2026-08-25T20:46:00Z` = **78 secondi**. Il registry ha tutte e 9 le versioni, l'ultima è `isLatest: true`. Cioè: pubblicare sul registry è automatizzabile in pipeline, e in questo progetto lo è.

---

## D.5 (e) — Quale canale porta più installazioni?

**Non esiste un dato pubblico che attribuisca le installazioni di un server MCP a un canale di scoperta.** Nessun registry o directory pubblica «N installazioni provenienti da noi». Il registry ufficiale *per progetto* non è il canale di installazione («not intended to be directly consumed by host applications»), e le directory pubblicano visite/stime, non install.

I dati pubblici che **esistono davvero**, in ordine di solidità:

| Dato | Numero | Natura | URL |
|---|---|---|---|
| **Install per plugin Claude Code** (marketplace ufficiale) | Frontend Design **1.134.112** · Superpowers **1.009.371** · Code Review **438.525** · Context7 **417.801** · Skill Creator **385.083** · Code Simplifier **346.763** · Playwright **319.887** · GitHub **319.381** · CLAUDE.md Management **287.247** · Feature Dev **256.017** | **Conteggio reale di installazioni**, il solo trovato | https://claude.com/plugins (pagina 1 di 4) |
| — di cui memoria | **Remember 51.442** installs («Continuous memory for Claude Code: extracts, summarizes, compresses conversations into tiered daily logs») · Circleback 12.396 | idem | idem |
| Download SDK MCP | «Across our Tier 1 SDKs, we're seeing **close to half-a-billion downloads a month**» e «both TypeScript and Python SDKs crossing the **1 billion total downloads** threshold» | annuncio ufficiale, 2026-07-28 | https://blog.modelcontextprotocol.io/posts/2026-07-28/ |
| Uso per server | Smithery «uses» (es. 22.49k, 43.39k) | conteggio di chiamate sul loro gateway, quindi **solo del loro traffico** | https://smithery.ai |
| Visite stimate | PulseMCP «Est Visitors (Week)» | **stima modellata**, per loro stessa ammissione | https://www.pulsemcp.com/statistics |
| Traffico directory | mcp.so: 2,2M unique visitors / 6M pageviews (12 mesi), 266K MAU | traffico web del sito, non install | https://mcp.so/submit?type=server |

**Il segnale direzionale più forte è comportamentale, non numerico**: PulseMCP, con submission sospese, rimanda i manutentori al registry ufficiale — «That is the best first step **even when we are not paused**, and we will pick it up automatically once we are back» (https://www.pulsemcp.com/submit). E la doc ufficiale posiziona il registry come sorgente per gli aggregatori, non per i client. Cioè: **si pubblica una volta sul registry e si viene ridistribuiti**, ma l'installazione avviene altrove.

Il roadmap MCP del 2026-08-22 (https://blog.modelcontextprotocol.io/posts/mcp-roadmap/) elenca cinque priorità — agentic messaging primitives, unificazione del transport HTTP, agent identity, primitive migliori, DX degli SDK — e **non menziona il registry né una data di GA**.

---

## D.6 (f) — Numeri di trazione dei pacchetti di memoria

**PyPI** — fonte `https://pypistats.org/api/packages/<pkg>/recent`, letti 2026-09-02 tra le 10:20 e le 11:00 UTC. Esclusi i mirror noti, aggiornati una volta al giorno.

| Pacchetto | last_day | last_week | last_month | Ultima versione (PyPI JSON API) |
|---|---:|---:|---:|---|
| `mem0ai` | 74.235 | 422.043 | **3.598.595** | 2.0.19 — 2026-08-24T13:16:44Z |
| `graphiti-core` | 20.995 | 124.547 | **1.092.635** | 0.30.1 — 2026-09-01T19:15:05Z |
| `cognee` | 3.553 | 25.073 | **191.787** | 1.5.3 — 2026-08-23T18:30:35Z |
| `letta` | 366 | 2.301 | **198.311** ⚠️ | 0.16.8 — 2026-05-14T17:14:47Z |
| `basic-memory` | 1.080 | 9.560 | **49.498** | 0.23.2 — 2026-08-25T20:44:42Z |

⚠️ **`letta`: il dato mensile inganna se letto da solo.** `last_week` è l'1,2% di `last_month`. Serie giornaliera (`/overall?mirrors=false`, 181 righe, 2026-03-05 → 2026-09-01):

```
2026-08-21  4017     2026-08-26   263
2026-08-22  2726     2026-08-27   379
2026-08-23  4072     2026-08-28   427
2026-08-24  3204     2026-08-29   342
2026-08-25   266  ←  rottura      2026-08-31   278
                     2026-09-01   366
```

Caduta di ~92% il 2026-08-25, poi stabile sui nuovi valori. **Il regime corrente di `letta` su PyPI è ~250-430 download/giorno, non ~6.600.** Causa: **non trovata** (non indagata, non ipotizzata).

**npm** — fonte `https://api.npmjs.org/downloads/point/…`, finestre dichiarate dall'API.

| Pacchetto | last-week (2026-08-23 → 08-29) | last-month (2026-07-31 → 08-29) | Note |
|---|---:|---:|---|
| `@modelcontextprotocol/server-memory` | **73.646** | **364.588** | v2026.8.31; `bin: mcp-server-memory`; dichiara `mcpName: io.github.modelcontextprotocol/server-memory` **ma non è nel registry ufficiale** (D.1) |
| `@letta-ai/letta-client` | **86.817** | non richiesto | SDK TypeScript, non un server MCP |
| `@letta-ai/memory-mcp` | **83** | **294** | **questo** è il server MCP di memoria di Letta; è nel registry ufficiale come `com.letta/memory-mcp` v2.0.2 |

**Presenza nel registry MCP ufficiale** (query `?search=…&version=latest`, 2026-09-02):

| Progetto | Nel registry | Dettaglio |
|---|---|---|
| mem0 | ✅ | `io.github.mem0ai/mem0` v1.0.0 — **remote-only**, nessun package |
| letta | ✅ | `com.letta/memory-mcp` v2.0.2 — npm `@letta-ai/memory-mcp` (namespace `com.letta` ⇒ verifica DNS o HTTP) |
| basic-memory | ✅ | `io.github.basicmachines-co/basic-memory` v0.23.2 — pypi + `runtimeHint: uvx` |
| graphiti | ❌ 0 risultati | — |
| cognee | ❌ 0 risultati | — |
| `server-memory` (riferimento) | ❌ 0 versioni, 0 server nel namespace | vedi D.1 |

**Osservazione, non spiegazione**: i due pacchetti con più download mensili su PyPI (`mem0ai` 3,6M, `graphiti-core` 1,1M) sono rispettivamente **remote-only** e **assente** dal registry. La correlazione tra presenza nel registry e trazione, sui 6 casi qui, **non c'è**.

---

## D.7 — Avvertenze sui dati

1. **Il conteggio del registry va fatto con retry** o si tronca in silenzio (5.841 vs 26.376, stesso endpoint, stesso giorno).
2. **`pepy.tech` non è intercambiabile con `pypistats`**: su `cognee` dà 211,3k negli ultimi 30 giorni contro 191.787 di pypistats (~+10%); e sul metadato ha sbagliato — dichiarava `basic-memory` 0.21.4 «released May 23, 2026» mentre PyPI lo stesso giorno dava **0.23.2** del 2026-08-25. Nella tabella (f) sono usati **solo pypistats e npm**.
3. **Tre metriche diverse, tre nomi simili**: «installs» (claude.com/plugins, conteggio reale), «uses» (Smithery, chiamate sul loro gateway), «Est Visitors» (PulseMCP, stima modellata). Non sono confrontabili.
4. Le pagine di Glama, PulseMCP, Smithery e mcp.so sono renderizzate in JS: i numeri riportati vengono dal `<title>`/payload letto via curl o dal rendering di WebFetch, con l'ora indicata.
5. `claude.com/plugins` mostra 4 pagine; i conteggi di installazione riportati sono della **pagina 1**.

**Non trovato / non ottenibile**: conteggio ufficiale pubblicato di server nel registry MCP · contenuto e conteggio di claude.ai/directory (403; il tool connettori restituisce 0 anche sul controllo positivo) · valori numerici della pagina statistiche PulseMCP (JS) · qualunque dataset pubblico che attribuisca installazioni di server MCP a un canale di scoperta · causa della caduta dei download di `letta` del 2026-08-25.
