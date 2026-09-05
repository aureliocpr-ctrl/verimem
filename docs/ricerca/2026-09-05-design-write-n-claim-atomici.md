# Design — «write = N claim atomici, ognuno giudicato», sulle tre porte

**ws3 «Galileo» · 05/09/2026 21:15 · DESIGN, non codice · per la revisione del lead**
(mandato: START `e70b3a6038cc1bad`; tesi del lead `a05dd7a6d6fa2458`; le mie misure
del 04/09 — `6946676f`, `2c282583`, `fa11f97e`, `5c458675` — e del 05/09 —
`1855405b`).

Questo documento dice **dove** la decomposizione entra, **che cosa** giudica, **che cosa
dichiara**, **chi protegge** e **che cosa costa** — ogni scelta con il numero che l'ha
decisa. Non contiene codice. Le celle vanno scritte prima del codice (RED), poi la cura.

---

## 0. I numeri che vincolano il design (tutti riproducibili dai banchi)

| # | misura | valore | banco | conseguenza per il design |
|---|---|---|---|---|
| N1 | superficie: fatti composti nel corpus vivo | **49,22%** (7.526/15.289) | `ws3-muro1-le-due-regex-a-confronto` | la cura tocca metà delle scritture: non è un caso limite |
| N2 | costo del giudizio a pezzi, in lotto | **0,79×** l'intero (2 coppie); 12,4× per coppia al lotto 16 | `ws3-muro1-P6c-quanto-costa-giudicare-a-pezzi` | le N×M coppie partono in **una chiamata**; il costo non è un argomento |
| N3 | falso allarme su campione non scelto (n=800) | **2,12%** [1,2; 3,2] | `ws3-muro1-il-falso-allarme-su-un-campione-non-scelto` | il prezzo della cura; parte è guadagno (classificazione dei 16 a QA/PO) |
| N4 | la soglia «≥3 parole» scarta la coda | intero **115/200**, atomico(3) **1/200**, atomico(1) **135/200** | `ws3-muro1-fase2-la-soglia-di-tre-parole-perde-la-coda` | **soglia = 1 parola**, o la cura regredisce di 57 punti |
| N5 | `subject_of` riconosce il soggetto nei primi pezzi | **15,7%** (1.183/7.536) | `scratchpad/quanto_e_cieco_subject_of.py` | l'eredità del soggetto **non può poggiare** su `subject_of` com'è |
| N6 | due difetti ortografici dello splitter | « ed » non spezzato; `\b` dopo `e'` mai acceso | `ws3-muro1-l-apostrofo-spegne-l-eredita-del-soggetto` | le regex si provano su ASCII **e** su accentato |
| N7 | subordinate | 12,7% del corpus; **1,9%** con completamento in coda | `ws3-muro1-fase2-le-subordinate` | residuo reale e piccolo: seconda fase, non prima |
| N8 | «ed è verificata.» da sola al gate | **passa** («e funziona.» è fermata) | idem N4 | il pezzo corto va giudicato **col soggetto**, altrimenti L1 non lo vede |
| N9 | la coda letta dall'intero (cura di Iris) | **57,5%** dei veri+coda | idem N4 | l'atomico con soglia 1 la supera (67,5%): il guadagno esiste |
| N10 | quanto della fonte vede il giudice oggi (`grounding_span`, 7.755 fatti vivi) | **69,5%** una frase sola; media **1,57** frasi; mediana 316 caratteri | `ws3-quanto-della-fonte-vede-il-giudice` | il focus (`select_relevant_span`, budget in caratteri, per rilevanza lessicale al claim) **seleziona già**; il MAX per punteggio è un secondo selettore: vanno composti, non sommati (§2.2). M_visto = 1,57 è il limite inferiore di M per il costo P-G |

---

## 1. Dove entra: **un innesto, non tre**

Le tre porte chiamano la stessa funzione:

- SDK — `verimem/client.py:683` → `run_validation_gate(...)`
- CLI — `verimem/cli.py:4412` (e `:2134` per il comando di validazione) → idem
- MCP — `verimem/mcp_server.py:13197` → idem

Il moat (L4) vive dentro la stessa funzione (`anti_confab_gate.py:2750-2904`).

**E i chiamanti sono SEI, non tre** (reperto del lead `cd7e0620e764e980`, misurato su main
`5d7152d8`): oltre alle tre porte, `document_promote.py:88-94`, `transcript_promote.py:89-95`
e `sleep.py:512-518` chiamano `run_validation_gate(source=…, ground_write=True)` e poi
**rifanno la decisione da soli** leggendo `grounding_score` (tre copie della stessa
regola, una con una soglia propria). L'innesto unico dentro il gate copre anche loro *per
costruzione*: ricevono `claims`/`claims_verdict` senza saperlo. Ma la loro copia della
decisione resta un rischio separato — è il ticket a499 di Nadia (un solo punto che decide
l'azione, i sei chiamanti la eseguono) — e questo design **non lo cura, lo presuppone**:
la cella P-F va estesa alle tre vie secondarie (stesso claim, stessa fonte, sei ricevute
confrontate su `claims_verdict`).

**Decisione**: la decomposizione entra **dentro `run_validation_gate`**, prima dei layer
L1 e prima del moat. Non alle porte. Ragioni:
1. «una capacità = tre porte, stessa risposta, stesso schema» (ws2): un innesto solo non
   può divergere fra le porte;
2. la ricevuta (`GateResult`) è già l'oggetto che le tre porte trasformano nella loro
   risposta — se la decomposizione la arricchisce, le tre porte ereditano i campi;
3. `provenance_trusted` e `writer_role` arrivano già lì: la decomposizione rispetta la
   stessa asimmetria (un `external_content` non si decompone: è un documento, non una
   asserzione dell'agente).

**Interruttore**: un parametro `decompose: bool | None` sulla funzione, default **on**
(«niente default OFF», Aurelio), con `VERIMEM_DECOMPOSE=0` come via d'uscita
d'emergenza dichiarata nella ricevuta.

---

## 2. Che cosa giudica: MIN sui claim, MAX sulle frasi della fonte

```
proposition ──► decomponi(proposition) ──► [c₁ … c_N]      (N ≥ 1; N=1 ⇒ identità)
source      ──► frasi(source)          ──► [s₁ … s_M]      (M ≥ 1)

L1.x  (lessicale, senza fonte):   verdetto_L1 = OR_i  L1(c_i)          (MIN sui claim)
L4    (moat, con fonte):          score_i    = MAX_j  giudice(s_j, c_i)
                                  verdetto_L4 = MIN_i score_i < cut
```

- **N=1 e M=1 ⇒ identità**: nessuna differenza dal gate di oggi. È il caso del 51% delle
  scritture (N1) e di *tutte* le 120 celle dei miei 60+60: la cura non tocca ciò che oggi
  funziona.
- Le N×M coppie del moat partono in **un lotto** (N2): lo scorer prende già una lista.
- **Soglia dei pezzi: 1 parola** (N4). Un pezzo di una parola («collaudata») entra nella
  lista e viene giudicato **col soggetto ereditato** (N8).

### 2.1 Il decompositore, in due tempi

**Tempo 1 (questa cura)** — lo splitter del lead, con le tre correzioni misurate:
- coordinate: `,\s*ed?\s+ | \s+ed?\s+ | ,\s*and\s+ | \s+and\s+ | ;\s+` (N6);
- guardia del verbo iniziale con `(?=\s|$)`, mai `\b` dopo un apostrofo (N6);
- soglia 1 parola (N4);
- **eredità del soggetto**: il soggetto è *il primo pezzo fino al suo primo verbo finito*,
  con un elenco di verbi **aperto** (participi e forme in `-a/-e/-i/-o` + copule + gli
  inglesi), non `subject_of` (N5). Se il soggetto non si trova, il pezzo **non viene
  scartato**: viene giudicato **insieme al pezzo precedente** (fusione), così da non
  fabbricare un frammento nudo. È la regola che protegge i due casi di ieri («Indietro
  16 con tracciato 0.», la citazione spezzata).
- **niente split dentro le virgolette** (« », " ", ' '): la citazione spezzata è l'altro
  caso di ieri (uso/menzione).

**Tempo 2 (dopo, non in questa cura)** — un decompositore che produca **triplette
S-P-O** (RefChecker) da parser o LLM locale, con decontestualizzazione minima
(Molecular Facts, DnDScore: 19,11% dei giudizi cambia). Le subordinate (N7, 1,9%) si
trattano lì. Il tempo 1 deve lasciare l'interfaccia pronta: `decomponi()` restituisce
una lista di *claim atomici auto-contenuti*, e il gate non sa come sono stati prodotti.

### 2.2 Il MAX sulle frasi e il focus di oggi: due selettori, una regola

Il giudice di oggi **non vede la fonte intera**: `LocalGroundingJudge.coppia` la passa
a `select_relevant_span(source, fact, budget)` — una selezione **per rilevanza lessicale
al claim**, con un budget in caratteri da `gate_config.json` — e poi `_entro_la_finestra`
toglie righe intere dal fondo per stare nella finestra del CE. Il risultato è
`grounding_span`, e sul corpus vivo (N10) è **una frase sola nel 69,5%** dei casi.

Il MAX del lead è un secondo selettore, **per punteggio del giudice**, su ogni frase. I
due non si sommano: se il MAX gira *dentro* lo span del focus, nel 69,5% dei casi non
cambia niente (c'è una frase sola); se gira *sulla fonte intera*, vede frasi che oggi il
focus scarta — ed è lì che sta il guadagno sulla zavorra in testa (P-b del lead: il CE
ribalta quando vede due frasi *insieme*) e anche il costo in coppie.

**Decisione**: per ogni claim atomico `c_i`, le frasi candidate sono **tutte le frasi
della fonte**, ciascuna giudicata **da sola** (mai due insieme: è la condizione del
ribaltamento); il focus a budget resta come *tetto per frase* (una frase più lunga del
budget viene ridotta come oggi), non come selettore. `grounding_span` registra la frase
vincente per ogni claim — quindi diventa una lista, allineata a `claims`.
**Costo**: N × M coppie con M = frasi della fonte intera; il limite inferiore misurato
è M_visto = 1,57 (N10), cioè ~3,2 coppie per scrittura composta con fonte, ~0,8× in
lotto (N2). La cella P-G misura M vero con fonti intere prima di dichiarare il costo.
**Come muore**: se su P-E (zavorra) il MAX per frase *non* toglie il ribaltamento che il
focus lascia passare, il secondo selettore non paga e si tiene solo il focus.

### 2.3 Due forme per claim: nuda per L1, auto-contenuta per il moat (misurato 05/09 23:00)

`decomponi()` v1 con l'eredità del soggetto, sui 200 «<vero> + coda»: **101/200** — *peggio
dell'intero* (114) e dello splitter di ieri a soglia 1 (120). La diagnosi è nei layer:
«E' completata.» accende `L1.13, L1.20` ed è fermata; «Una directory VUOTA e' completata.»
accende `L1.13, L1-domain-precision-observe` e **passa**. L1.20 è il rilevatore *semantico*
di self-claim (`anti_confab_gate.py:1623`): riconosce la forma impersonale, e con un
soggetto davanti la carve-out di terzi la esenta. **L'eredità del soggetto disattiva il
rilevatore.** E il 120 di ieri era un effetto della cecità di `subject_of`, che lasciava la
coda nuda.

**Decisione**: ogni claim atomico ha **due grafie** — la forma nuda (`eredita_soggetto=False`)
va a **L1**, la forma auto-contenuta va a **L4** e alla ricevuta. Misurato: forma nuda a L1
**145/200** (il numero più alto finora), controllo sulle 15: 5/5 e 3/10. `claims` porta la
forma auto-contenuta (quella che l'utente legge); `claims_verdict` registra il layer che ha
fermato, qualunque grafia abbia letto.
**Costo**: nessuno — L1 è lessicale e le due grafie costano lo stesso.
**Come muore**: se P-C (i 5 di ws7) scende sotto 5/5 con la forma nuda, o se P-A sale
sopra 2,4%, la forma nuda apre più di quanto chiuda.
**Un buco del gate visto di passaggio, non del decompositore**: «ed è collaudata» è 0/50
in *tutti* i bracci — L1 non conosce il verbo. Va nel registro come ticket a sé.

---

## 3. Che cosa dichiara: la ricevuta (il mio perimetro)

Oggi la ricevuta di `Memory.add` porta `['adjudication','advice','grounding_score','id',
'moat','quarantined_by','status','stored','warnings']` — **niente su quale pezzo è
caduto**. Con N claim, «quarantined» senza dire *perché e dove* è un verdetto che
l'utente non può contestare né correggere.

**Campi nuovi in `GateResult`, ereditati dalle tre porte:**

| campo | tipo | significato |
|---|---|---|
| `claims` | `list[str]` | i claim atomici giudicati, nell'ordine, **testo esatto** |
| `claims_verdict` | `list[{"claim": i, "layer": "L1.13"\|"L4-grounding"\|null, "score": float\|null}]` | per ogni claim, il layer che l'ha fermato (o `null`) e il punteggio del moat |
| `decomposed` | `bool` | `False` quando N=1 (identità) — così un chiamante sa se la cura ha agito |
| `decomposer` | `str` | `"coord-v1"` oggi; `"triplet-llm"` domani — dichiara il livello |

E nella prosa (`advice`): *«Fermato il claim 2 di 3: «Il comando warmup è finito alle
14:53:19» — completamento senza evidenza (L1.13). Gli altri 2 claim sono sostenuti.»*
Sulla CLI e su MCP: stesso testo, stessi campi, stessi nomi (regola delle tre porte).

**Perché è la parte che decide l'adozione**: un falso allarme del 2% (N3) è tollerabile
solo se l'utente vede *quale* pezzo è caduto e può riscriverlo; un 2% muto è un prodotto
che sbaglia senza dirlo, e ws7 lo classificherebbe come difetto bloccante.

---

## 4. Chi protegge: le popolazioni, e la cella per ciascuna (RED prima del codice)

| popolazione | garanzia | cella (alla porta, tre porte) | numero atteso |
|---|---|---|---|
| **P-A** i veri composti oggi ammessi | non più del **2%** cambia verdetto; ogni cambio è dichiarato con `claims_verdict` | campione casuale n=800, seed fisso, `run_validation_gate` (proxy validato 4/4) + 10 celle alla porta | ≤ 2,4% (limite superiore di N3) |
| **P-B** le self-claim in coda («<vero> ed è verificata») | fermate **più** che dall'intero | i 200 di N4, alle tre porte | ≥ 135/200, contro 115 dell'intero |
| **P-C** i 5 falsi di ws7 | restano fermati | le 15 di ws7 alla porta | 5/5 e ≤ 2/10 |
| **P-D** le 120 celle dei 60+60 | **identità** (N=1, M=1) | i due banchi di ieri, con la cura accesa | stessi numeri di ieri, cella per cella |
| **P-E** la frase estranea (zavorra) | il MAX sulle frasi toglie il ribaltamento | i 5 casi del lead + i miei 30 | i 4/4 del lead; sui miei 30 nessun peggioramento (ieri −0,0633 su R) |
| **P-F** `external_content` | **non si decompone** (documento ≠ asserzione) | cella con `writer_role="external_content"` | `decomposed=False` |
| **P-G** il costo | una scrittura composta ≤ 1,3× l'intero | il banco P6c con la cura accesa, un impianto solo | ≤ 1,27× (peggior caso misurato) |

Ogni cella deve poter fallire **oggi** (RED) e passare **dopo** (GREEN), falsificata con
stash/pop. Chi scrive la cura non scrive le celle: revisore QA (ws1).

---

## 5. Che cosa NON fa questa cura, dichiarato

- Non cura la frase estranea *sul giudice* (P1/P2 di ieri: è un difetto del nostro CE,
  non della famiglia): la cura è ws4 (giudice v3.2), il MAX sulle frasi la **aggira**.
- Non tratta le subordinate (N7): tempo 2.
- Non tocca `subject_of` del prodotto: il decompositore ha il proprio estrattore, per
  non cambiare il comportamento di chi già usa `subject_of` altrove.
- Non decide la classificazione dei 16 (danno o guadagno): resta a QA/PO, e il numero
  entra nella cella P-A quando c'è.
- **M (frasi della fonte) non è misurato sul corpus**: le fonti non ci stanno. La cella
  P-G lo misura con fonti vere di più frasi prima di dichiarare il costo finale.

---

## 6. Sequenza (finestra del lead, un pezzo per volta)

1. **Celle RED** P-A…P-G, tre porte, revisore ws1 — senza codice di prodotto.
2. `decomponi()` come funzione pura + i suoi test (coordinate, `ed`, apostrofo, soglia 1,
   virgolette, fusione dei nudi): è l'unica parte con logica nuova.
3. Innesto in `run_validation_gate` + campi in `GateResult`; le tre porte **non
   cambiano**, si verifica che i campi passino (cella per porta).
4. Prosa in `advice` (tre porte, stesso testo).
5. Banchi di ieri rieseguiti con la cura accesa: P-D identità, P-B ≥ 135/200, P-A ≤ 2,4%.
6. CHANGELOG (ws8) con i numeri delle celle, non con aggettivi.

---

## 7. Come muore questo design

- Se P-D non è identità: l'innesto ha toccato il caso N=1 e va rifatto.
- Se P-B < 115/200: la cura è peggio dell'intero e non entra.
- Se P-A > 2,4% *dopo* la fusione dei nudi e le virgolette: il decompositore del tempo 1
  non basta e si passa al tempo 2 prima di entrare.
- Se P-G > 1,3×: il lotto non è stato usato; si legge il codice, non si alza la soglia.

*Store di Aurelio in sola lettura; nessuna riga di prodotto toccata; questo file sta in
`docs/ricerca/` finché il lead non lo rivede.*
