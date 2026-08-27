# 00 — L'ESAME DEL PRODOTTO

> **Registro unico delle celle misurate.** Istituito dalla direttiva di Aurelio del
> 27/08 (trasmessa da `lead-audit`, messaggio A2A `d2d5c2944c8f457e`), nelle sue parole:
> *«cosa dovrebbe avere teoricamente un progetto del genere? Le ha? Rispetta quello che
> promette? **Lo fa davvero?**»*
>
> Questo file **non giudica il codice: registra le misure**. È il posto dove un referto
> smette di essere un messaggio sul canale e diventa una riga che qualcun altro può
> attaccare.

## I quattro livelli di ogni domanda

| livello | domanda | chi lo può dire |
|---|---|---|
| ① | dovrebbe averlo? | discussione |
| ② | ce l'ha? | `git grep` |
| ③ | lo **promette**? | README / CLI / docstring |
| ④ | **lo fa davvero**, misurato **alla porta**? | solo un'esecuzione |

> 🔴 **Una promessa senza il livello ④ verde è marketing.** Questa è la riga che
> l'esame esiste per far rispettare, e vale anche per le righe scritte qui dentro.

## Come si scrive una riga — le regole pagate, non inventate

1. **Il regime sta nell'intestazione, non nella memoria di chi ha misurato.** Macchina,
   variabili d'ambiente, versione, `n`. *(Un verde senza regime vale come un numero senza
   unità: misurato il 20/08, due istanze hanno contato «caduto» un bersaglio che nel
   regime giusto era verde **prima** della cura.)*
2. **Niente numeri nei titoli.** Un titolo con una cifra invecchia e nessuno lo rilegge;
   la cifra sta nella cella, dove ha accanto il suo denominatore.
3. **Il denominatore accanto alla cifra, sempre.** *(Dei sei difetti di vetrina trovati
   in due giorni, **cinque erano la stessa cosa**: un numero corretto sotto un'etichetta
   che non definisce la popolazione.)*
4. **Dichiara il livello a cui hai misurato.** Regex interna < funzione pubblica < porta
   che il prodotto usa — e ogni salto può ribaltare il verdetto, **in entrambe le
   direzioni**.
5. **Un controllo che DEVE fallire**, o «4 su 4» non distingue un presidio che funziona
   da uno spento.
6. **Chi riporta la misura di un altro lo scrive.** La colonna `misurata da` non è un
   credito: è il modo di sapere a chi chiedere quando la riga verrà attaccata.

## Le celle misurate

Legenda verdetto: 🟢 fa quello che promette · 🔴 non lo fa · 🟡 lo fa in parte / con limite
· ⚪ non misurato.

| # | domanda | classe | lingua | porta | verdetto | misurata da | regime / limite |
|---|---|---|---|---|---|---|---|
| 1 | i comandi che il README pubblicato promette esistono nel pacchetto? | — | EN | CLI | 🟢 **14 su 14** | ws7 | `git show v0.7.0:` — **il codice *etichettato* 0.7.0, non il wheel su PyPI**; il tag è posteriore di 1h27 all'upload (ws6) |
| 2 | il server MCP parte, per chi installa da PyPI? | — | — | MCP | 🔴 **no** | ws1 | venv pulito, `pip install verimem==0.7.0` → `mcp 2.1.1` → `verimem mcp` **exit 1**, `AttributeError`. **Controllo positivo**: forzando `mcp<2` nello stesso venv → **exit 0** |
| 3 | il gate vede un numero inventato dentro una fonte lunga? | C4 | — | — | 🔴 **no, se il numero è comune** | ws5 | A/B a fonte fissa: `3`,`7`,`9` collidono a **200 parole**; `47`,`617`,`4291` mai in 7000. **Non è la lunghezza: è la rarità** |
| 4 | il gate vede un numero scritto all'italiana? | C4 | IT | — | 🔴 **no** | ws8 | 3 famiglie su 3 spente dalla virgola (`512,5MB` · `4291,7ms` · `97,5%`), controllo positivo 3/3 |
| 5 | l'unità di misura entra nel confronto? | C4 | IT | — | 🔴 **no** | ws5 | una «penale del **7%**» nella fonte valida «**7 giorni**» nel claim; il campo `.unita` esiste e viene ignorato. Bastano due frasi |
| 6 | il punteggio di grounding cresce con il contesto? | — | — | — | 🔴 **non è monotono** | ws4 | stesso claim falso, stesso documento: **0.3** a 1000 char e **99.3** a 6000, **deterministico su due esecuzioni** |
| 7 | le due porte restituiscono gli avvisi con lo stesso nome? | — | — | SDK vs MCP | 🔴 **no** | ws2 | SDK → `warnings` · MCP → `anti_confab_warnings`. Chi cambia porta legge una lista vuota e conclude che il gate taceva |
| 8 | quanto costa davvero una scrittura? | — | — | — | 🟡 **il costo è di NASCERE, non di scrivere** | ws3, ws6, ws2 | primo write ~26 s / 1,9 GB · dal terzo **0,4–0,5 s** (**23,7×**). ⚠️ Il numero finale di ws3 è stato corretto **due volte in venti minuti**: vale l'ultimo referto, non questa riga |
| 9 | il banco del regime che un utente userebbe è mai stato eseguito? | — | — | gateway | 🔴 **mai, dal 21/07** | ws7 | `benchmark/concurrency_shared_server.py`: **1 commit · 0 artefatti che lo nominano · 0 file che lo citano**. Il suo docstring chiamava i «24 s» **anti-pattern** già allora |

### Celle dichiarate scoperte

- ⚪ **porta SDK**: nessuna misura di conformità alle promesse (il costo sì, ws2).
- ⚪ **gateway HTTP**: nessuna cella.
- ⚪ **classi C1, C2, C3, C5, C6, C7, C8**: stasera è stata misurata **solo C4**
  (quantità e formati). Sette classi su otto sono scoperte, ed è il buco più grande
  di questo registro.
- ⚪ **il vertice della piramide** — «un agente con verimem sbaglia meno di uno senza» —
  **non ha ancora una riga qui**, ed è il numero che tutto il resto dovrebbe sostenere.

---

📌 **Chi aggiunge una riga**: aggiorna anche la lista delle celle scoperte. Un registro
che cresce solo dal lato verde racconta una bugia per omissione.

📌 **Provenienza**: le righe 1 e 9 sono misurate da chi scrive (ws7). Le righe 2–8 sono
**riportate dai referti A2A della sera del 27/08** — chi scrive non ha eseguito quei
banchi, e ogni riga nomina l'autore proprio perché la si possa contestare a lui.
