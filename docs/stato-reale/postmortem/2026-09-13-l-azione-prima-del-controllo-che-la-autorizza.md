# 2026-09-13 — tre effetti irreversibili partiti prima del controllo che li autorizzava

* **Cosa** — in una giornata, tre volte, un'azione con effetto permanente è
  stata eseguita **prima** della verifica che avrebbe dovuto permetterla. Nessuna
  delle tre è stata trovata da un presidio: due si sono viste dall'esito, una
  quando la prova che serviva non c'era più.

  ```
  push dopo un commit fallito    il ramo pubblicato non conteneva il lavoro
  write prima del parse AST      un file del pacchetto rotto in un albero condiviso
  store cancellato a fine banco  la misura non riproducibile non aveva più prove
  rm di un file «mio»            era tracciato sul ramo, cancellato davvero
  ```

  La quarta è arrivata dopo che le prime tre erano già scritte qui, ed è la più
  istruttiva proprio per quello: un file estratto da un altro ramo per usarlo un
  minuto sembrava una copia di lavoro, e `git status` — consultato *dopo* la
  rimozione — l'ha mostrato come ` D` di un file tracciato.

* **Classe** — **l'ordine fra effetto e verifica**, non tre errori distinti. In
  tutti e tre i casi la verifica esisteva ed era corretta: contare le righe del
  messaggio, parsare il file, leggere l'esito del banco. Stava **dopo**. Una
  catena di comandi in cui il secondo non dipende dal primo li esegue entrambi
  anche quando il primo fallisce, e la scrittura di un file non aspetta che
  qualcuno ne verifichi la sintassi.

* **Causa** — la forma `fai && verifica` (o `fai; verifica`) legge come se la
  verifica proteggesse, e protegge solo il *lettore*: l'effetto è già avvenuto.
  Nel caso del file rotto la conseguenza non era locale — l'albero è raggiungibile
  da altre istanze, e un modulo del pacchetto che non compila ferma chiunque lo
  importi, non solo chi lo ha scritto.

* **Controlli aggiunti** — tre, uno per luogo, tutti *prima*:
  1. **il commit e il push sono due comandi separati**, e il secondo si dà dopo
     aver letto l'esito del primo — mai nella stessa catena;
  2. **`ast.parse` prima di ogni `write`** negli sweep automatici, e il file non
     viene toccato se il parse fallisce (il rifiuto stampa il nome e la riga);
  3. **uno store di banco non si cancella finché il pari non l'ha letto** —
     scritto nel docstring di `scripts/stato_della_misura.py`, dove lo legge chi
     sta per eseguire un banco;
  4. **`git status` sul percorso PRIMA di rimuoverlo**, non dopo: un file
     comparso nell'albero per una copia temporanea non è per forza non
     tracciato, e la differenza si legge in un comando.

* **Quello che resta aperto** — i tre controlli sono *pratiche*, non cricchetti:
  nessuno di loro è un test che diventa rosso se qualcuno torna alla forma
  vecchia. Renderli automatici non è gratis (un presidio sui comandi di una shell
  non ha una superficie ovvia), e finché non lo sono **il registro sono queste
  righe**.

* **Misura che mancava** — nessuna delle tre azioni lasciava traccia del proprio
  esito accanto all'effetto: il push non diceva cosa stava pubblicando, lo sweep
  non diceva quali file avrebbe toccato, il banco non diceva in quali condizioni
  aveva misurato. La terza ora la stampa uno strumento; le prime due no.
