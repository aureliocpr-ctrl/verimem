# Lotto 3 — le conferme (50 file, 4.935 righe, 91 funzioni)

Su `7b9e8ca1`. Bozze da `scripts/mappa_bozza.py`; qui c'è ciò che ho confermato **eseguendo**.

    righe di tabella      96
    senza TEST che le nomini   17   (18%)   ← lotto 2: 41%
    senza CHIAMANTI             1
    codice morto                0

## 1. 🔑 Delle 17 senza test, **SEDICI sono helper privati**

    _safe_div · _compute_lineage_metrics · _safe_size · _dir_size · _format_suffix (×4)
    _sig_tokens · _fact_id_for · _confidence_from_evidence · _proposition_for
    _key · _snapshot · _content_tokens · _bucket_floor

⇒ Non sono porte: sono funzioni di servizio dentro il proprio modulo. **Una porta pubblica
non provata pesa più di un helper non nominato**, e qui il conto cambia molto la lettura del
18%.

## 2. L'UNICA porta pubblica senza test: `dashboard_overview`

    verimem/mcp_server.py:6314   name="hippo_dashboard_overview"        ← tool REGISTRATO
    verimem/mcp_server.py:11292  payload = dashboard_overview(agent=a)  ← chiamata corretta
    test che lo nominano: NESSUNO

⇒ **Un tool MCP pubblico che nessun test esercita.** La chiamata rispetta la firma
(`dashboard_overview(*, agent)`), quindi non c'è un difetto visibile — ma **non c'è nemmeno
niente che se ne accorgerebbe** se cambiasse.

## 3. ⚠️ Un falso positivo dello strumento, con la CAUSA

Uno strumento di analisi mi aveva segnalato `mcp_server.py:15011` — *«dashboard_overview
chiamata con 1 arg posizionale, ne accetta 0»*. **È falso, e la ragione è istruttiva:**

    14968   from verimem.dashboard_overview_v2 import dashboard_overview_v2 AS dashboard_overview
    14971   result = dashboard_overview(a.semantic, project_globs=…)   ← è la V2
    15011   # Stessa ragione delle soglie di `dashboard_overview`: …   ← un COMMENTO

⇒ L'`import … as` **riusa il nome di una funzione che esiste davvero**, con una firma
diversa. Lo strumento ha confrontato la chiamata della **v2** con la firma della **v1**, e
la riga 15011 che citava non è nemmeno una chiamata: è un commento.

📌 **Il reperto vero non è il falso positivo: è l'alias.** Un modulo che importa
`dashboard_overview_v2 as dashboard_overview` rende ambiguo, nello stesso file, **quale
delle due si sta chiamando** — per chi legge e per gli strumenti. Costa una riga cambiarlo
(`as dashboard_overview_v2`), e toglie una trappola a chiunque passi di lì.

## 4. Quello che questa mappa NON dice

- **Le 79 righe con un test che le nomina non sono state verificate una per una**: «nominata»
  resta un righello lessicale.
- **Non ho eseguito nessuno dei tool** del lotto: la prova qui è documentale (registrazione +
  firma + presenza di test), non un giro vero.
- `facts_conflict` (563 righe, 11 fn) è il file più grande del lotto e l'ho trattato come gli
  altri: **merita un giro suo**, non l'ha avuto.

---

*ws5 (Piattaforma), 08/09.*
