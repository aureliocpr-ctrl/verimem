# F1 · FIRMA ESTERNA — ws4 «Paragone»

**Richiesta**: DIREZIONE di `lead-audit` del 28/08 ore 20:09, punto 1 — «*serve
UNA firma ESTERNA (ws4 o ws6, a claim) sul doc AGGIORNATO, poi si passa al
codice*». Claim `1bdfc338b38f` sullo scope `firma-esterna/F1`, zero conflitti.

**Oggetto**: `docs/stato-reale/F1-DESIGN-DOC-strato-soggetto-valore.md`, 407
righe, ultimo commit `1d5ffd81` delle 20:15.

**Come l'ho fatta**: una firma che non esegue non è una firma. Ho eseguito io il
banco della baseline — `banchi/ws3-F1-la-baseline-regge-su-una-fonte-vera.py` —
in un processo mio, e ho confrontato riga per riga con la tabella «oggi» del
design doc.

---

## ✅ ESITO: FIRMO. I cinque numeri della baseline reggono alla mia esecuzione

```
     famiglia         +0fr     +2fr     +4fr     +8fr
     SCAMBIO          7/12    10/12    10/12    10/12
     NUMERALE          1/3      1/3      2/3      2/3
     OMISSIONE         3/3      3/3      3/3      2/3
     (cifra→ctrl)      0/3      0/3      0/3      0/3
```

| il doc dichiara | la mia esecuzione | esito |
|---|---|---|
| SCAMBIO 930ch = **10/12** | 10/12 | ✅ |
| SCAMBIO 453ch = **7/12** | 7/12 | ✅ |
| NUMERALE **1/3 · 2/3** | 1/3 · 2/3 | ✅ |
| OMISSIONE **3/3 · 2/3** | 3/3 · 2/3 | ✅ |
| cifra assente **verde** | 0/3 a tutte e quattro le lunghezze | ✅ |

⇒ **La predizione di §2 è scritta contro numeri che esistono e che ho
riprodotto.** Non è ritarabile a posteriori, ed è la proprietà che rende il
design falsificabile invece che persuasivo.

🤝 **E c'è una convergenza indipendente che vale la pena registrare**: il mio
controllo «cifra assente, verde a ogni lunghezza fino a 3516 caratteri» e la
riga `(cifra→ctrl) 0/3` del banco di @ws3 sono **la stessa misura fatta con due
banchi diversi, da due mani diverse, su fonti diverse**. Regge da entrambe le
parti.

---

## Cosa firmo, oltre ai numeri

✅ **Il perimetro è dichiarato e non tocca ciò che ho misurato io.** «Non tocca
il giudice, né i pesi, né le soglie; il passo 1 rende `L4.3` e `L4.1` disgiunti
per costruzione.» ⇒ le celle W7-12 e W7-19 del registro non sono a rischio di
regressione **per costruzione**, non per promessa.

✅ **Il documento si autocorregge tre volte, e lo scrive.** «È la terza volta che
restringo quella mia frase: la frase originale era mia e non regge, va tolta dal
punto.» ⇒ un design doc che restringe la propria promessa **prima** di scrivere
codice è la cosa che stasera è mancata di più a me, non a lui.

✅ **Il passo 5 (astieniti sul silenzio) ha una predizione che lo può uccidere**:
«se ne segnala anche UNA [omissione], il passo 5 non fa ciò che dico». Un
criterio di fallimento scritto contro se stessi.

---

## 🔴 DUE RILIEVI, entrambi sulla MISURABILITÀ del criterio di fallimento

Non bloccano la firma, ma **vanno risolti prima del banco**, perché senza di
essi il verdetto finale sarà contestabile — e il mio mestiere è dire quando un
numero non potrà essere letto.

### R-ws4-1 — «≤ 3/12» non ha lo stesso significato nelle due zone

La tabella predice **`≤ 3/12` in entrambe le zone**, ma la baseline è **10/12 a
930 caratteri** e **7/12 a 453**. La colonna «se sbaglio» dice «*sotto i 7
segnalati, il meccanismo non funziona*» — che è un criterio scritto **per la
zona 930**. A 453 caratteri, passare da 7/12 a ≤3/12 richiede di segnalarne
**≥4 su 7**, non ≥7.

⇒ **Serve una soglia di fallimento per zona**, o al banco si potrà dire che la
predizione è stata «rispettata» in una zona e «mancata» nell'altra usando lo
stesso numero. **È la classe «un criterio unico su una grandezza che varia per
regime», e stasera mi è costata tre restrizioni.**

### R-ws4-2 — «OMISSIONE INVARIATO» non è misurabile su una baseline che varia da sola

La predizione dice **«INVARIATO, 0 segnalazioni»**. Ma la baseline dell'omissione
**non è costante**: `3/3 · 3/3 · 3/3 · 2/3`. **Invariato rispetto a quale
valore?** Se dopo `L4.3` esce `2/3` in zona C, non si potrà distinguere «lo
strato non ha toccato nulla» da «lo strato ha segnalato una omissione **e** la
baseline è calata da sola».

⇒ **La parte forte della predizione — «0 segnalazioni» — è verificabile e va
tenuta come criterio unico**; «invariato» va **abbandonato** o ancorato a una
zona sola. 📌 La misura giusta non è il conteggio finale ma **quante volte
`L4.3` ha parlato**: quella è zero o non è zero, e non dipende dalla baseline.

---

## Limiti della mia firma, dichiarati

- Ho verificato **la baseline**, non il meccanismo: `L4.3` non esiste ancora come
  codice, quindi **nessuno può firmarne il comportamento** — solo la coerenza fra
  ciò che promette e ciò che i numeri di partenza consentono di promettere.
- Ho eseguito **un** banco, quello della baseline. Non ho eseguito il banco delle
  R (`ws3-F1-regola-v2-le-risposte-alle-R-misurate.py`) né la popolazione B di
  @ws5 — e **la popolazione B è la riga che può respingere il design**, come il
  doc stesso dichiara. La mia firma **non la copre**.
- Sono **firma esterna al design, non al fronte**: lo scambio di attribuzione
  l'ho misurato io, quindi sul *problema* non sono neutrale. Sono neutrale sulla
  *cura*, che non ho contribuito a disegnare.

---

**Firmato**: ws4 «Paragone» · 28/08/2026, 20:23 · baseline eseguita in processo
proprio, codice `Code/HippoAgent`, fuori da pytest.
