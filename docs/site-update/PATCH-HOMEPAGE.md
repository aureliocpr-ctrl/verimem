# Patch homepage verimem.com — correzioni oneste + strategia GEO
> Preparato da lead-audit il 28/08 su mandato di Aurelio («controllalo,
> giudicalo, modificalo dove va modificato, non spariamo cazzate»).
> Il sorgente del sito NON è né sul disco né su GitHub: vive sul VPS nginx.
> Questo file è il pacchetto pronto; il deploy richiede l'accesso al server.

## Giudizio sintetico del sito attuale
Il sito è GIÀ onesto in un modo raro (sezione "WHAT VERIMEM IS NOT",
"0 adoption", "parity, not a win"). Voto: buono nel tono, da correggere in
4 punti dove le misure di questa settimana l'hanno superato, e da armare
per la ricerca AI (GEO), dove ha già le basi (llms.txt, JSON-LD) ma
incomplete e in parte stantie.

## A. CORREZIONI DI VERITÀ (priorità 1 — "non spariamo cazzate")
1. **§03/01 «since July it is multilingual … calibrated at 0 false
   positives»** → il 28/08 l'esame ha trovato che il layer semantico
   multilingue NON si attiva nel percorso SDK dell'utente (difetto di
   giuntura, cura in corso con doppia firma). RIGA NUOVA: "multilingual
   semantic screen calibrated at 0 FP on the bench; a delivery-path defect
   found by our own exam on Aug 28 is being fixed — tracked in the public
   exam." (Quando la cura è verde con 2 firme: rimuovere la nota.)
2. **«v0.7.0 live on PyPI … green CI»** → aggiungere il known issue vero:
   "Known issue (0.7.0): MCP entrypoint crashes with mcp>=2 — install with
   `pip install verimem \"mcp<2\"`; pinned release coming." E togliere
   «green CI» finché la coda CI non torna a dare verdetti (oggi ferma).
3. **«Latency 38ms / 166–237ms»** → il numero è vero ma senza regime
   (lezione Q5). RIGA NUOVA: "38 ms p50 write (warm, single process);
   shared-service mode: ~258 ms write / ~102 ms read at 14.3 ops/s, zero
   errors; first call in a throwaway process pays ~26 s of model load —
   an anti-pattern, use the service." (Numeri misurati 28/08, commit
   cbbee0c1/f8836233.)
4. **llms.txt live è STANTIO e contraddice la homepage** (dice 6,064 test
   e QA 0.739/0.553 dell'era precedente): sostituirlo con
   `docs/site-update/llms.txt` (allineato + sezione memory poisoning +
   known issue + link al registro).

## B. ARMAMENTO GEO (priorità 2 — dalla rassegna del 28/08)
Perché: l'AI search premia chi è CITABILE — Q&A machine-readable,
definizioni nette, numeri con fonte. ChatGPT ~70% dell'AI search; solo
l'11% dei domini è citato da più piattaforme; FAQPage schema = il tipo di
structured data a più alto impatto; llms.txt è lo standard de facto dei
dev-tools AI-native (Anthropic, Vercel, Cursor lo usano).
1. **FAQPage JSON-LD**: inserire `docs/site-update/faq-jsonld.html`
   nell'<head> — 7 Q&A vere, inclusa la domanda che il mercato sta
   iniziando a fare: "what is memory poisoning" (OWASP Agentic 2026).
   È LA query emergente e nessun competitor la presidia con misure.
2. **sitemap.xml**: manca (404). File pronto: `docs/site-update/sitemap.xml`.
3. **Sezione visibile "Memory poisoning" sulla homepage** (non solo
   schema): 4 righe — OWASP la riconosce, un'iniezione persiste e si
   amplifica, il gate+screen+firma+lineage sono la risposta, link ai
   paper. Tutto già vero nel prodotto.
4. **Il registro pubblico come pagina** (quando C8 chiude): "The only
   memory layer that publishes its own exam" — è il contenuto più
   citabile che abbiamo: le AI citano chi mostra i dati, e nessuno
   mostra anche i propri rossi.
5. Su llms.txt teniamo aspettative oneste: nessun grande provider si è
   impegnato a leggerlo in produzione (adozione 5–15%), ma il NOSTRO
   pubblico è esattamente quello dei coding assistants che lo usano.

## C. COSA NON FARE
- Niente numeri nuovi in vetrina senza cella verde a 2 firme nel registro.
- Niente "green CI" / contatori vivi nel testo statico (pattern ws7: i
  numeri che invecchiano si tolgono o si generano, non si scrivono).
- Niente promesse sul non-latino (roadmap dichiarata, non feature).

## D. DEPLOY
Il sito è servito da nginx (headers: HSTS preload, nosniff, DENY — buona
igiene). Sorgente non trovato in locale/GitHub ⇒ serve da Aurelio: path
sul VPS o accesso, oppure il repo privato se esiste. I file pronti:
- `docs/site-update/llms.txt` → sostituisce `/llms.txt`
- `docs/site-update/faq-jsonld.html` → blocco da inserire nell'<head>
- `docs/site-update/sitemap.xml` → nuovo `/sitemap.xml`
- le 3 righe di §A da applicare all'index.html live.
