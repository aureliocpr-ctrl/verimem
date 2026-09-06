# Il 6 settembre dal lato di chi usa verimem

**ws7 Iris · Product Owner · scritto per il resoconto delle 15:55**
Filtro applicato, testuale da Aurelio alle 13:42: *«solo ciò che un utente di verimem
paga o sente, con i numeri»*. Quello che non lo passa **non è in questa pagina**.

---

## 1 · Quello che oggi è MIGLIORATO per chi installa

| cosa | prima | oggi | dove |
|---|---|---|---|
| **scrivi con la libreria, rileggi dalla riga di comando** | `no facts found`, `exit 0`, **nessuna spiegazione** | `--db` su cinque comandi **e** `recall` stampa **il percorso in cui ha cercato** | main `ab2f45c5` |
| **la prima schermata del README** | *«finché non esegui `warmup` il moat è OFF»* — **misurato falso** | dice il vero, con il numero: **85,7 s** la prima scrittura senza `warmup`, `moat: judged 100.0` | main `b2c20080` |
| **quel testo può tornare falso?** | nessun presidio: era rimasto sbagliato **due release** | presidio nuovo, **RED 5 / GREEN 7**, con un controllo che si accende se il banner sparisce | main `b2c20080` |

🔑 **Il numero che dice perché serviva**: rimettendo il banner falso, dei **15** presidi che
il README aveva **se ne accendevano 0**. Il testo più letto del prodotto non era guardato
da nessuno.

## 2 · Quello che oggi abbiamo scoperto, e che l'utente PAGA

| | quanto | chi l'ha misurato |
|---|---|---|
| 🔴 **sulla porta MCP, in default, una scrittura con fonte entra SENZA giudizio** | **13 su 275 nelle ultime 24 h = 4,7%** (0,7% storico: **sette volte**) | A/B di @ws1 Marie · peso di @ws6 Aldo · livello mio |
| **la 0.7.6 che è pubblicata adesso** | **non risponde affatto: 360 s** | @ws1 Marie |
| il rimedio, oggi | **24,5 s invece di 20,3 — 4,2 s comprano il giudizio** | @ws1 Marie |

⇒ **Questo ha fermato il tag alle 14:38**, e poi l'ha rimesso in moto: **fermarlo lasciava
in produzione la versione che non risponde**. *(Ho votato prima contro e poi a favore: la
seconda volta avevo il numero della 0.7.6, la prima no.)*

## 3 · Quello che NON sappiamo, e che va detto prima di pubblicarlo

· **T1 — quanto aspetta oggi la prima scrittura sulla porta MCP: non lo sappiamo.** Le tre
  cure sono in `main`, il numero che pubblichiamo (**313-903 s**) è di **prima**. Marcato
  nella scheda; la misura l'ho chiesta alle 13:48 e non è stata fatta.
· **T22 — quanto costa una sessione del server MCP: senza livello.** La fonte esiste
  (`banchi/ws5-chi-importa-torch-nel-client.py`, predizione depositata), **l'esito no**. Se
  il server importa `torch`, il costo **si moltiplica per il numero di agenti**.
· **La prova dei dieci minuti misura un percorso che non prescriviamo più**: entrambe le
  esecuzioni fanno `warmup`, che oggi è facoltativo. Va rifatta.

## 4 · I difetti aperti, per chi decide il rilascio

**P0: sei** (erano sette; **T16 è stato chiuso oggi, in entrambe le metà**).

| | dove morde |
|---|---|
| **T26** il moat non gira sulla porta MCP in default | la promessa centrale |
| **T19** il fatto entra cieco e la ricerca fabbrica un'assenza | tutte e tre le porte |
| **D-1** una self-claim preceduta da una frase vera passa | la promessa centrale |
| **D-6** `as_of` accettato e ignorato | curato in main, **da riverificare** |
| **T14** su MCP il verdetto del conflitto non arriva | il pezzo che lo cura è **revertato** |
| **T1** la prima scrittura con fonte via MCP | **numero da rimisurare** |

## 5 · Una cosa che è successa oggi e che vale come le altre

La riga con cui volevamo dire all'utente come rimediare a T26 **ha acceso un nostro
presidio**: il comando è `HIPPO_PRELOAD_BACKGROUND`, in un prodotto che si chiama
**verimem**, e nel codice quello è **l'unico nome che funziona**.

⇒ Il debito del nome vecchio — 248 strumenti su 249 — **non era più solo estetica: era
arrivato a una riga che diciamo a qualcuno di digitare.** L'ho lasciato aperto invece di
scrivere il nome bello e inservibile.
