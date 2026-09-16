# Postmortem — il registro dei rossi (regola R7)

Ogni rosso su main, ogni revert, ogni perdita di dati, ogni degrado visibile
all'utente e **ogni misura che mancava** lascia qui un file di sei righe. Senza
colpe: il nome dell'autore non compare, il nome del *controllo aggiunto* sì.

Il lead non apre la finestra su main finché il postmortem dell'ultimo rosso non
è qui. La cartella è il registro: se è vuota, o non ci sono stati rossi, o non
li stiamo scrivendo — e il secondo caso è quello che questa cartella esiste per
rendere impossibile.

## Quando si scrive (i cinque inneschi)

Dal *Postmortem Culture* del SRE book di Google, adattati a noi:

1. **degrado visibile all'utente** — il prodotto fa una cosa diversa da quella
   che promette, e chi lo usa può accorgersene;
2. **perdita di dati di qualunque tipo** — un fatto scritto e non più servito
   conta (il 21% di oggi è nato così);
3. **un rosso su main o un revert** — compreso il rosso che al secondo
   tentativo diventa verde: quello *soprattutto*, vedi sotto;
4. **tempo al verde oltre la giornata** — se un rosso resta acceso più a lungo,
   la causa non era quella che pensavamo;
5. **una misura che mancava** — abbiamo scoperto una grandezza che nessuno
   stava guardando. Non è un incidente, è la prova che eravamo ciechi lì.

## Il formato: sei righe, e nessuna in più

```markdown
# <data> — <titolo di una riga: cosa si è visto, non cosa era>

* **Cosa**       — cosa si è visto, con il comando o il link che lo prova.
* **Classe**     — rosso vero · trappola armata · sensore scollegato · guardiano che mente.
* **Causa**      — perché è successo, alla profondità che è stata *provata*, non a quella immaginata.
* **Cura**       — cosa è cambiato nel codice, con lo sha; «nessuna» è una risposta valida se è vera.
* **Controllo**  — cosa fallirebbe DA SOLO se la stessa cosa tornasse. Se è «nessuno», è un debito e va detto.
* **Owner**      — chi tiene il controllo, non chi ha scritto il bug.
```

La riga che decide il valore del file è **Controllo**: un postmortem senza un
controllo aggiunto è un racconto. Il racconto serve a chi c'era; il controllo
serve a chi arriverà dopo, che qui cambia a ogni sessione.

## Le quattro classi di un rosso

Prima di spiegare un rosso, **classificalo**: se il codice che accusi, letto, è
corretto, il sospetto passa al banco.

| classe | cos'è | come si riconosce |
|---|---|---|
| **rosso vero** | il prodotto è rotto | si riproduce a comando |
| **trappola armata** | il test dipende da qualcosa che non ha dichiarato (l'orologio, l'ordine, la macchina, la rete) | cambia esito senza che il prodotto cambi |
| **sensore scollegato** | il test non tocca ciò che dice di toccare | resta verde anche spegnendo il codice che prova |
| **guardiano che mente** | il presidio riporta un esito che non ha misurato | il suo output non contiene la prova |

## ⚠️ Un rosso guarito da un rerun diventa INVISIBILE

`gh run list` e la pagina Actions mostrano la conclusione **dell'ultimo
tentativo**. Un run rosso ri-eseguito e diventato verde compare come `success`,
e sparisce da qualunque conteggio di «rossi su main» fatto così.

Misurato il 09/09/2026 sul rosso dell'08/09:

```
$ gh run list --workflow=ci.yml            # 34221255060  5ac8d9f1  success
$ gh api .../actions/runs/34221255060 --jq '{run_attempt, conclusion}'
{"conclusion":"success","run_attempt":2}   # <- due tentativi
$ gh api .../actions/runs/34221255060/attempts/1 --jq '{conclusion}'
{"conclusion":"failure"}                   # <- il rosso è QUI
```

Quindi il numero dei rossi si conta **per tentativo**, non per run, e questa
cartella è l'unico posto dove un rosso guarito da un rerun resta scritto.
