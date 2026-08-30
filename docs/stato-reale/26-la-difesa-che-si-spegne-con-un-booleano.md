# ㉖ La difesa che si spegne con un booleano — e perché su questo corpus è una compensazione, non un buco

**Misurato il 30/08/2026 fra le 14:12 e le 15:49** · celle **`W7-69` · `W7-70` · `W7-71`**
del registro, ognuna col comando per rifarla · tutte le misure **fuori da pytest**.

Questo documento non ripete le misure: le cita col numero e dice **cosa se ne ricava per
decidere**. Ha una particolarità che va detta subito — **la sua conclusione si è capovolta
due volte durante la giornata**, e le due inversioni sono la parte più utile.

---

## In una riga

**Un booleano del chiamante spegne l'intera famiglia `L1`, senza token, sul 65,1% del
corpus.** Leggendo i fatti che ne approfittano non è emerso **nessun** self-claim nudo: sono
resoconti di lavoro e misure, e senza quell'eccezione la porta ne declasserebbe **21 su 24**.
⇒ **Su questo traffico l'eccezione è una compensazione, non un buco.** ⚠️ Ma è tarata sul
*nostro* traffico, non su quello che la vetrina promette.

---

## 1. La catena, letta nel codice

```
   client.py:533    narrative_l1_skip = meta_narrative
   client.py:658    if meta_narrative: fact.writer_role = "user"      ← FORZATO
   anti_confab_gate.py:1946
                    warnings = [] if narrative_l1_skip or …
```

⇒ **`meta_narrative=True` spegne tutta la famiglia `L1` e riscrive il ruolo a `user`**,
sovrascrivendo qualsiasi `writer_role` il chiamante avesse dichiarato (il commento a `:653`
lo dice: *«resta l'ultima parola»*).

🔑 **E non chiede nessun token.** Il bypass *totale* del gate (`:1894`) esige
`verify_trusted_writer` **più** un segreto server-side, fail-closed. Questo — che spegne
«solo» la famiglia `L1` — è un booleano e basta.

⚖️ **Non è un difetto nascosto**: l'orientamento del prodotto lo dichiara — *«it is
deliberate… the screen is not literally universal»*. **È un limite dichiarato che nessuno
aveva misurato.**

## 2. Quanto è larga: 65,1% (e non 99,8%)

**`W7-69`**, su **13561 fatti vivi**: `narrative` **8822 (65,1%)**, normali **4739 (34,9%)**.

🪞 **Il primo numero che avevo era 99,8%**, ed era la quota su una **fetta** — i soli fatti
con fonte conservata. Sul denominatore giusto sono **65,1%**: **35 punti di claim gonfiato**,
evitati solo perché la distribuzione si stampa prima di dividere.

## 3. Il prezzo apparente: 551 fatti, e la domanda sbagliata

Sempre `W7-69`: **551 su 8822 (6,2%)** avrebbero acceso un layer — `L1.13` **278**, `L1.15`
123, `L1.10` 86, `L1.20` 66. *(Controllo positivo: sui normali **2849 su 4739** accendono,
quindi non è un layer spento ovunque. Per era: **7,2%** prima del 21/08, **3,6%** dopo.)*

🔄 **Poi ho chiesto «quanti sono checkpoint?» e ho risposto 42 (7,6%)**, concludendo che nove
su dieci erano «lavoro ordinario». 🎯 **Era la domanda sbagliata**: *«non è un checkpoint»*
non vuol dire *«è un self-claim»*. **Avevo classificato per FORMA — la marca nel testo —
invece che per NATURA.**

## 4. 🔑 Cosa sono davvero: letti, non contati

**`W7-70`**, 24 casi presi **uno ogni 14** lungo tutta la popolazione (non i primi — i primi
quattro erano tutti handoff e mi avevano quasi fatto concludere il falso):

| | | |
|---|---|---|
| **A** | resoconto di sessione/lavoro | **11** |
| **B** | misura o osservazione verificabile | **13** |
| **C** | **self-claim nudo** — ciò che `L1` esiste per fermare | **0** |

```
   A   «RELEASE 0.8.0 PREPARATA, PyPI NON PUBBLICATO … suite 417 passed»
   B   «La CI sul commit 2f2c667e e' completed success con 15 check pass su 15»
```

🔑 **E il motivo per cui `L1` si accenderebbe si legge nelle parole**: *CONFERMATA ·
COMPLETE · CHIUSO · shipped · completa · verificata · testato* — **il vocabolario con cui si
parla di CI, test e cicli di lavoro.** Il nostro dominio.

## 5. ⚖️ Il controfattuale, che quantifica la tesi

**`W7-71`**, sugli **stessi 24**, A/B nella stessa esecuzione cambiando **un solo
parametro**:

```
   con l'eccezione ATTIVA      24 su 24  persist      ← controllo: misuro l'eccezione
   con `grounding_span`         4 su 24               ← 20 senza: L1 decide DA SOLO
   SENZA l'eccezione           21 su 24  downgrade
```

⇒ **Senza quel booleano, 21 record di lavoro veri su 24 finirebbero in quarantena.**
Combinato col punto 4 — zero self-claim nudi — **sarebbero falsi allarmi su lavoro vero**.

⚖️ **E «fermerebbe» va inteso nel senso esatto**, perché un'altra istanza ha contestato la
parola prima di controfirmare: `downgrade` **non è** `reject` — il fatto viene scritto lo
stesso. Ma il codice prosegue: *«force `status` … so the suspect claim is **hidden from
default recall** yet preserved for audit»*. ⇒ **Per chi legge la memoria, declassato e
quarantinato sono la stessa cosa: non vengono serviti.** Il fatto non è perso, è invisibile
— ed è la distinzione che conta per l'utente, non quella fra i due verbi.

🧭 **E i 3 che sopravvivono lo devono a `L1-domain-precision-observe`**: la carve-out che in
**`W7-60`** *non* copriva i verbali d'ufficio (il classificatore diceva **0 su 8**) e che
**qui funziona**. ⇒ **Non è rotta: è tarata sul dominio tecnico, non su quello d'ufficio.**

## 6. ⚠️ Cosa questo NON assolve

La misura difende **l'effetto** dell'eccezione su questo corpus. **Non difende il disegno**:

**① La difesa è spenta da un booleano senza token.** Il prodotto ha già deciso, altrove, che
un privilegio non può pendere da un campo che il chiamante controlla — è la ragione per cui
`verified_by` non decide più la provenienza (`gate_router.py:76-98`) e per cui il bypass
totale è token-gated. **Qui quel ragionamento non è stato applicato.**

**② La taratura è sul NOSTRO traffico.** I 24 letti sono resoconti e misure perché **li
scriviamo noi, che misuriamo un gate**. La vetrina promette memoria verificata **per agenti
AI**: se da quella porta scrivesse un agente, il materiale sarebbe diverso — e allora lo
stesso silenzio **costerebbe** invece di risparmiare. **La compensazione non è una proprietà
del codice: è una coincidenza fra il codice e chi lo usa oggi.**

**③ Il rimedio non è togliere l'eccezione.** `W7-71` dice cosa succederebbe: 21 falsi allarmi
su 24. Il rimedio è **rendere `L1` capace di distinguere un resoconto da un self-claim**, che
è la stessa cura di cui parla il dossier ㉕ — e nessuna delle due si compra con una riga.

## 7. ⛔ Cosa non so

- **La classificazione A/B/C è mia, a mano, su 24 casi**: un giudizio dichiarato, non una
  misura. Un caso (*«GRAFICA V3 FUNZIONANTE E VERIFICATA A SCHERMO»*) è **al confine** e
  l'ho contato A; chi lo conta C ha un argomento.
- **«non è un self-claim nudo» ≠ «è vero»**: la verità dei 24 non l'ho verificata.
- **24 e 24 sono lo stesso campione** (uno ogni 14 su 348): `W7-70` e `W7-71` **non sono due
  conferme indipendenti**, sono due misure sugli stessi fatti.
- **`W7-69` misura al detector**, non alla porta ⇒ il 6,2% è un **limite superiore**.
- **Il pre-filtro di `W7-70`** trova 385 accesi dove `W7-69` ne contava 551: per **leggere**
  va bene, per **contare** no.
- ⛔ **«normali 60,1% contro narrative 6,2%» non dice «le note sono più pulite»**: sono
  popolazioni diverse, e non l'ho misurato.

---

## Le celle, per rifare tutto

`W7-69` l'ampiezza e il prezzo apparente (~13 min) · `W7-70` i 24 letti nel merito (~2 min) ·
`W7-71` il controfattuale. Ognuna porta la riga `🔎 rifallo con` e i controlli che potevano
farla cadere. Si compone con il reperto di un'altra istanza sulle **due porte** (SDK e MCP
danno garanzie diverse sul *moat*): **per porta** là, **per flag** qui.
