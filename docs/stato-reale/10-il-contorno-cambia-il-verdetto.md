# ⑩ Il contorno cambia il verdetto — e non sappiamo perché

*ws4 Paragone, misurato il 26-27/08 fra le 21:30 e le 00:10. Tutte le celle fuori
da pytest, store nuovo per ogni misura, `validate="full"`, CE locale, mai col
giudice llm.*

**In una riga:** su una stessa coppia (claim falso, fonte che lo smentisce),
aggiungere alla fonte del testo **privo di significato** ribalta il verdetto del
moat — e lo fa in modo **non monotono**, in entrambe le lingue, senza che
nessuna delle sei variabili provate lo spieghi.

---

## 1. Il caso più nudo

```
fonte  «Verbale: il direttore ha rassegnato le dimissioni il 4 maggio.»
claim  «Il direttore è ancora in carica il 4 maggio.»          (falso)

    la fonte scritta UNA volta   →  TRATT   0.9
    la fonte scritta DUE volte   →  passa  97.2
```

Tre giri con store nuovo: `0.9/97.2 · 0.9/97.2 · 0.9/97.2`. La fonte raddoppiata
è **logicamente identica a sé stessa**.

E la forma deterministica ridotta — riempimento neutro che non nomina né il
direttore né la carica né la data:

```
    riempimento x1     191 char   TRATT   1.2   avvisi=1
    riempimento x10   1433 char   passa  99.2   avvisi=0
    riempimento x60   8333 char   passa  99.2   avvisi=0
```

## 2. Le sei spiegazioni provate

| spiegazione | esito | la misura che la chiude |
|---|---|---|
| il MAX su finestre | **esclusa** | `g(A+B)=99.9` con `max(g(A),g(B))=1.6` — il punteggio del tutto non è derivabile dalle parti |
| il troncamento a 512 token | **esclusa** | gli ultimi 1500 char, sotto la finestra **e** con la smentita, passano lo stesso a 99.0 |
| la sovrapposizione lessicale | **esclusa** | presenza costante 0.500 in tutte le righe; col contorno neutro la frequenza *relativa* crolla di 80× e il punteggio **sale** |
| la posizione della smentita | **esclusa** | testa · quarto · mezzo · tre quarti · coda → `99.9` ovunque |
| la natura del contorno | **esclusa** | numeri 99.9 · pseudo-parole 99.3 · prosa IT 98.4 · prosa DE 84.2 · prosa EN 25.2 |
| la lunghezza in caratteri | **conta, ma non monotona** | `74→0.5 · 263→1.2 · 473→85.4 · 893→99.9 · 1733→1.0` — passa in una finestra e torna a reggere sopra e sotto |

⚠️ L'ultima riga è un **ritiro**: alle 23:10 l'avevo dichiarata esclusa su un
solo punto (83 char → 0.7). Un punto non è un'esclusione.

## 3. Su una fonte vera non è nemmeno ordinato

Output di `pytest` di un file del repo, 57 righe, la smentita nell'ultima. Al
crescere del contorno che la precede:

```
    0 righe    79 char   TRATT   0.4
    2 righe   794 char   TRATT   0.1
    5 righe  1531 char   passa  88.7
   10 righe  2634 char   TRATT   2.4
   20 righe  4488 char   TRATT   2.4
   40 righe  7073 char   passa  99.5
   58 righe  9462 char   passa  99.8
```

**L'esito si ribalta tre volte su sette.** Non è una soglia da alzare: è
instabile. Con questo cade anche «tarare il parametro»: non c'è grandezza
monotona da tarare.

## 4. Quanto è esteso — il numero onesto

Su una popolazione **non selezionata** (i dieci casi di ws3, IT ed EN appaiati):

```
    ribaltamenti per ripetizione     italiano 1/10     inglese 1/10
```

**Non è un difetto italiano.** E contare i soli ribaltamenti lo **sottostima**:
in altri due casi il punteggio esplode senza che l'esito cambi — IT
`TRATT 1.8 → TRATT 99.3`, EN `TRATT 0.4 → TRATT 79.1` — perché un layer
lessicale tiene il fatto mentre il giudice ha già ceduto.

⚠️ La prima misura che avevo pubblicato («3 casi su 4») era su casi **che avevo
scelto perché ribaltavano**: descriveva la mia ricerca, non il prodotto.

## 5. Cosa regge, e va detto con la stessa forza

* La **contraddizione esplicita** regge anche col contorno: `0/10` in italiano e
  `0/10` in inglese, e il punteggio *scende* in 8 casi su 10. La misura di ws3
  non è scalfita.
* La promessa «*quarantined — kept OUT of default recall*» regge **end-to-end**:
  su cinque interrogazioni i quarantinati non compaiono mai.
* Il prodotto **dichiara** i propri limiti in tre punti che avevo dato per
  mancanti: `L4.1` nomina i numeri assenti uno per uno, `L4-relazione` avvisa
  «*the CE scored 100 — not verified as a stated fact*», `trust_report.scope`
  dice cosa **non** certifica.

## 6. Un difetto separato, e facile

Su una fonte che eccede la finestra del giudice, `transformers` avvisa su stderr
(«Token indices sequence length … 607 > 512») e **la ricevuta non riporta
nulla**: `avvisi=0`. Chi scrive vede `moat: passed` e `99.81` e non ha modo di
sapere che il giudice ha letto un pezzo. Non chiede di capire il meccanismo:
chiede di propagare un avviso che esiste già.

## 7. Dove sono i presidi

* `tests/test_una_frase_estranea_puo_ribaltare_il_moat.py` — le sei spiegazioni
  e il ritiro sono scritti nel docstring, perché nessuno le riprovi
* `tests/test_ripetere_la_fonte_ribalta_il_verdetto.py`
* `tests/test_una_frase_estranea_fa_entrare_la_contraddizione_implicita.py`
* `docs/stato-reale/banchi/la-stabilita-separa-dove-la-soglia-no.py` — l'unica
  cosa costruttiva emersa: sotto perturbazione neutra i **veri** si muovono di
  2.2 in media, i **falsi** di 15.7 (max 98.7). Non regge come veto — un vero
  scende di 12,8 — ma come **avviso** è un'altra cosa.

Tutti con `--runxfail` verificato.

---

## 8. ⚠️ Il fenomeno è più largo di quanto dice questo documento (27/08, 22:15)

Questo dossier descriveva il contorno come qualcosa che ribalta **il claim che
la fonte non menziona**. Misurato il 27/08: ribalta anche una classe diversa,
lo **scambio di attribuzione** — una cifra vera della fonte attribuita alla cosa
sbagliata, dove `L4.1` tace per costruzione perché il valore c'è.

```
  contorno           car.        VERO     cauzione=148000    importo=22000
  nessuno             453     OK  99.9      ferm    4.9        ferm    0.9
  prosa IT            696     OK 100.0        OK   99.4        ferm   62.4
  numeri              575     OK 100.0      ferm   15.4          OK   99.8
  pseudo-parole       584     OK 100.0        OK   93.4        ferm    1.6
```

⇒ **Tre ribaltamenti su sei.** Uno scambio fermato a **4.9** entra a **99.4**
con della prosa neutra; un altro fermato a **0.9** entra a **99.8** con del
contorno numerico. **Il claim VERO resta ammesso con tutti e quattro i
contorni** (99.9–100.0), quindi il contorno non rompe la fonte: sposta il
giudizio **solo sui falsi**.

E come nella §2, la natura del contorno **non predice** l'esito: prosa e
pseudo-parole ribaltano il primo claim, i numeri il secondo. Le sei spiegazioni
escluse qui e le quattro escluse sullo scambio (specie, verso, rapporto fra i
valori, struttura sintattica) sono **dieci** su una superficie sola.

🔑 **La conseguenza pratica riguarda ogni numero di copertura che pubblichiamo**:
una misura fatta su fonti *nude* è un **limite inferiore**, perché un documento
vero — un contratto con le sue premesse, un referto con le sue formule — porta
contorno per costruzione.

Banco: `banchi/il-contorno-ribalta-anche-lo-scambio.py`, con il controllo che
poteva fallire (il VERO ammesso con ogni contorno) retto. Fonte costruita, due
claim, quattro contorni: la **direzione** è netta, la **quota 3/6** no.
