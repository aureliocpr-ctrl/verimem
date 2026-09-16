# 2026-09-09 — quattordici fatti scritti senza vettore, e la ricevuta diceva `stored: true`

* **Cosa** — fra le `23:35:46` e le `23:53:52` quattordici fatti sono entrati nello
  store con `embedding` di **zero byte** e `embedding_model` **stringa vuota**;
  nove sono del lotto DoD di ws8, gli altri di ws1 e ws2. Sono trovabili per
  parola chiave e **fuori dal recall semantico**. Misurato in sola lettura su
  `CONFIG.data_dir/semantic/semantic.db`:

  ```
   18107  emb=  3072  modello='intfloat/multilingual-e5-base'  08/05 10:43:03 -> 09/09 23:55:03
      14  emb= VUOTO  modello=''                               09/09 23:35:46 -> 09/09 23:53:52
  ```

* **Classe** — **guardiano che mente**. Non è un rosso e non è un `except`
  sciatto: il vettore differito è un comportamento *voluto* e documentato
  (`verimem facts backfill --help`: «persists the row instantly with an
  empty-blob embedding so it never cold-blocks ~22s»). Il difetto è che **chi
  scrive non lo sa**: la ricevuta stampa `stored=True judged=True` e non dice
  che il vettore manca, così nove scritture di fila sono passate per riuscite.

* **Causa** — provata da ws5 (Piattaforma) passo per passo, e ricontrollata qui: il
  servizio di encoding è morto e rinato con **un altro modello**
  (`e5-base`/768 → `MiniLM`/384); il client lo rifiuta, ed è giusto; in
  `HIPPO_ENCODE_DELEGATE_ONLY=1` non c'è ripiego locale, quindi
  `EncodeDelegateUnavailable`; `semantic.py:3303` cattura quell'eccezione e
  scrive la riga senza vettore con un solo `_LOG.warning`. Alle `00:10` del
  10/09 il daemon era **ancora giù**: `embedding.encode("prova")` →
  `EncodeDelegateUnavailable`.

  **…e la causa A MONTE** (trovata da ws5 alle 00:38 del 10/09, dopo la prima
  stesura di questo postmortem; testo suo, innestato qui perché **un incidente
  ha un postmortem solo**): il daemon non era caduto per caso. **Discovery e
  lock del daemon stanno in `Path.home()`, mai nella data dir**
  (`encode_service.py:41`, `:573`, `:583`), quindi **un banco che isola
  `ENGRAM_DATA_DIR` non isola il daemon**: legge la discovery globale, trova un
  daemon che non dichiara il *suo* modello, ne spawna uno col proprio e lo
  registra per tutti. Il colpevole del 09/09 è stato un banco isolato di ws2 su
  T49 (`ENGRAM_DATA_DIR = …\Temp\ws2-t49-…`, `ENGRAM_EMBEDDING_MODEL =
  …MiniLM…`, letto dal suo `environ`) — che **non aveva sbagliato niente**:
  isolare la data dir è ciò che ci è stato chiesto. ⇒ Il ripristino manuale del
  daemon fatto da ws5 alle 00:13 è durato **12 minuti**: alle 00:25:08 un altro
  banco l'aveva già rimpiazzato.

* **Cura** — **esiste già nel prodotto**: `python -m verimem.cli facts backfill`,
  idempotente. **Non è stata eseguita**, e l'ordine conta: prima il daemon deve
  tornare e dichiarare `e5-base`/768, poi il backfill. Lanciarlo mentre il
  daemon serve 384 scriverebbe quattordici vettori a 384 in uno store a 768 —
  che è T-MAP-9 (la mesh filtra a 384 mentre lo store scrive 768: **0 righe in
  silenzio su 18.092 fatti**) — e passeremmo da «fuori dal recall» a «il recall
  li trova e non li capisce».

* **Controllo** — `scripts/vettori_vuoti.py`, aggiunto con questo postmortem:
  conta i fatti per **forma** del vettore (`NULL` / `VUOTO` / lunghezza) e
  fallisce se i vuoti restano sopra zero. Serve perché il controllo ovvio è
  cieco, e ci è cascata anche chi aveva appena dichiarato lo store pulito:

  ```
  WHERE embedding IS NULL     -> 0        <- il controllo ovvio non ne vede nessuno
  WHERE length(embedding)=0   -> 14       <- ci sono tutti
  ```

  Un blob di zero byte **non è `NULL`**, e la stringa vuota **non è `NULL`**: il
  criterio ovvio non distingue «nessun vettore» da «vettore vuoto», e quella
  differenza era tutto il reperto.

  Ma questo controllo **rileva, non previene**: dice che è successo, non impedisce
  che risucceda. Con la causa a monte in mano, i controlli che chiudono davvero
  l'incidente sono due, e nessuno dei due è mio:

  1. **T60** — discovery e lock del daemon dentro la data dir, così che un banco
     che isola `ENGRAM_DATA_DIR` isoli anche il daemon. È la prevenzione: senza,
     il ripristino manuale dura dodici minuti (misurato: 00:13 → 00:25:08).
  2. **la riga della ricevuta** — il `save` deve dire che l'embedding è
     differito, come già dice `judged` e `withheld_despite_judge`. È la
     dichiarazione: senza, chi scrive continuerà a leggere `stored: true` e ad
     andare avanti.

* **Owner** — la causa a monte e T60: **ws5 Piattaforma**. Il rilevatore
  (`vettori_vuoti.py`) e questa cartella: **ws8 Release**. La riga della
  ricevuta: da assegnare (il CTO).

---

## La forma, per chi legge fra un mese

È la terza volta in due giorni che troviamo la stessa cosa sotto tre facce
diverse: **il prodotto sa una cosa, la registra per sé, e non la dice a chi ha
appena scritto.** T26a/a (il `judged` che non arrivava alla porta), T49 (i
quarantenati serviti come veri), e ora l'embedding differito. Il presidio giusto
non è ricordarselo: è che **ogni ripiego silenzioso compaia nella ricevuta della
scrittura che l'ha subìto**.

E una nota di metodo che vale quanto il resto: il primo controllo di stanotte ha
detto «store vuoto» perché leggeva `semantic.db` alla **radice** (0 fatti)
invece di `semantic/semantic.db` (18.121). È una riga già scritta in casa da
settimane. Averla scritta non basta: **la composizione si stampa prima di
misurare**, sempre, ed è per questo che il cricchetto qui sopra stampa le forme
e non solo un numero.
