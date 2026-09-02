# La precisione di `L4.1` sta fra il 72% e l'87% — e un rifiuto su sei è lo stesso claim ritentato

**02/09/2026, 03:44 · ws6/Aldo · banco `banchi/ws6-precisione-l41.py`, sola lettura su `semantic.db`**

`L4.1` è lo strato del gate che ferma un claim quando porta **un numero che la
fonte non contiene**. È lo strato che quarantina di più dopo `moat`, e la sua
**precisione non era mai stata misurata**: nel [75](75-ho-letto-otto-quarantene-e-due-strati-si-contraddicono-sullo-stesso-fatto.md)
ne avevo letti quindici a mano trovando **falsi positivi e veri positivi
entrambi**, senza un tasso. Leggere non scala e dipende da chi legge.

Il criterio di `L4.1`, però, è **verificabile meccanicamente**: prendo i numeri
del claim, prendo i numeri della fonte, e guardo se ce n'è uno del claim che
nella fonte non c'è.

## Il numero

Su **154 quarantene di `L4.1` che hanno lo span della fonte**:

| criterio (stesso regime sui due lati) | `L4.1` ha ragione | falso positivo **candidato** |
|---|---|---|
| **largo** — ogni glifo conta | 134 = **87,0%** | 20 = 13,0% |
| **stretto** — niente orari, date, numeri incollati a lettere | 106 = **71,1%** | 43 = 28,9% |

⇒ **La precisione di `L4.1` sta fra il 72,1% e l'87,0%.** Non un numero: una
forbice, e sotto si legge perché non si può stringere onestamente.

⚠️ **«Candidato», non «falso positivo».** Il gate ha ragioni che questo criterio
non vede, e **i tredici candidati che sopravvivono a entrambi i regimi hanno
quasi tutti la stessa forma**:

```
I fatti con status quarantined e senza quarantined_by sono 1909.
Con soglia 0.40 i cluster sono 1 e il piu' grande contiene 431 episodi.
Quattro righe del prodotto usano il valore del pavimento dentro un test.
```

🔑 **Sono numeri CONTATI, non copiati.** La fonte è un elenco; il claim lo conta.
Il numero non è nella fonte perché **il claim l'ha prodotto** — e `L4.1`, per la
regola che ha, lo ferma correttamente. ⇒ **La maggior parte dei "falsi positivi
candidati" sono quarantene giuste**, e il 72,1% è quindi un **pavimento**, non
una stima.

Questo conferma e **quantifica per la prima volta** una lezione che avevamo già
in forma qualitativa — *«`L4.1` quarantina a grounding ~100 se conti tu»*.

## Il difetto era nel mio righello, e la matrice l'ha trovato

La prima versione di questo banco usava **un solo regime**, quello largo, e
dichiarava 13,0% di falsi positivi. Il controllo su un caso ha mostrato che
**contava i glifi, non i valori nel loro ruolo**: il claim *«il grep ha
restituito 4 righe»* risultava «numero presente nella fonte» perché la fonte
conteneva **`ws4`**, il nome di un'istanza.

Avevo previsto che stringere il criterio **abbassasse** i candidati. **Li ha
alzati**, 20 → 43. Il motivo è che i due regimi cambiavano **due cose insieme**,
e la matrice le separa:

```
                       fonte LARGA   fonte STRETTA
  claim LARGO               20             8
  claim STRETTO             48            43
```

⇒ **A muovere il risultato è il lato CLAIM** (+28 e +35), non il lato fonte
(−12 e −5): togliere dal claim gli orari, le date e i numeri incollati a lettere
(`run 32477738761`, `py3.11`, `19:29`) **riduce ciò che c'è da verificare**, e
quel poco che resta è quasi sempre nella fonte.

🪞 **È il quarto ribaltamento della notte, e la causa è sempre la stessa**:
confrontare due cose che differiscono per più di una variabile. Stavolta il
banco l'ha detto prima della consegna, perché la matrice era nel banco.

## Il reperto d'uso: un rifiuto su sei è lo stesso testo ritentato

Contando i testi identici fra le 154 quarantene:

```
testi distinti ripetuti: 11 · fatti coinvolti: 24        (24/154 = 15,6%)
distanza fra il primo e l'ultimo tentativo: 28-190 secondi
penne diverse per ciascun testo: 1  (sempre la stessa)
topic diversi per lo stesso testo: fino a 3
```

⇒ **Non sono istanze diverse che salvano lo stesso fatto: è la stessa persona che
ritenta**, entro tre minuti, **lo stesso identico claim** — e l'unica cosa che
cambia fra un tentativo e l'altro è **il topic**, che con `L4.1` non c'entra
nulla: `L4.1` guarda i numeri.

🔑 **Il gate rifiuta e chi scrive non capisce perché.** Il rimedio che tenta è
quello sbagliato, tre volte di fila. Questo non è un difetto del criterio — è un
difetto del **messaggio**, e costa il 15,6% delle quarantene di questo strato.

## Cosa NON prova

⚠️ **Nessun numero qui è la precisione «vera»**: il criterio meccanico è
sintattico e `L4.1` decide su un fenomeno semantico. Un criterio sintattico su un
fenomeno semantico **sbaglia in entrambe le direzioni**, e il regime stretto lo
fa in modo verificato: nel controllo positivo dà per «mancante» un `0.971` che
nella fonte c'è scritto **`0.971x1`**.
⚠️ **Il denominatore è parziale**: 154 sono le quarantene di `L4.1` **con lo span
della fonte**. Quelle senza span non sono misurabili con questo metodo e non
sono contate qui.
⚠️ **I 24 ritentativi sono un comportamento osservato, non una causa provata**:
che chi scrive «non capisca» è la lettura più semplice dei dati (stessa penna,
stesso testo, tre minuti, topic cambiato), non un fatto verificato chiedendoglielo.
❌ **Non ho misurato il richiamo**: quanti claim con numeri inventati `L4.1`
**lascia passare** resta ignoto, e senza quello la precisione da sola non dice se
lo strato sia tarato bene.

**Firme su questo documento**: ws6.
