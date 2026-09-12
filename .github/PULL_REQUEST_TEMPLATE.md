<!--
DUE RIGHE, POI LE CASELLE. Non è uno stile: è la forma da cui si compone il
messaggio con cui questa PR entra nel ramo principale.

Le impostazioni del repository dicono `squash_merge_commit_message:
COMMIT_MESSAGES`, cioè il corpo del commit di fusione è la CONCATENAZIONE dei
messaggi dei commit. Misurato il 12/09 alle 13:55, su 20 PR aperte: 70 messaggi
su 130 non erano presentabili, e una PR ne aveva 48. Lasciando fare, quel muro
di testo finisce nel `git log` pubblico.

⇒ `scripts/messaggio_dello_squash.py <numero>` compone il messaggio da queste
due righe più il titolo, e lo passa dal controllo. Con il corpo in questa forma
esce di tre righe e pulito; senza, si scrive a mano e si sbaglia.

Riga 1 = COSA CAMBIA PER CHI USA IL PRODOTTO. Non cosa hai fatto: cosa cambia
per chi non ha letto il codice.
Riga 2 = COME È PROVATO. Il comando e il numero, non l'aggettivo.
-->

<!-- riga 1: cosa cambia per chi usa il prodotto -->

<!-- riga 2: come è provato -->

### Definition of Done

- [ ] RED at the port, with the output in the PR
- [ ] GREEN
- [ ] map entry updated
- [ ] README claim linked or removed
- [ ] docstring carries the date and the command
- [ ] reviewer is not the author
- [ ] QA sign-off
- [ ] fact saved with its source
- [ ] CI green on the tip
- [ ] no new copies

<!--
⚠️ QUESTE CASELLE ESISTONO IN DUE POSTI E NON SONO LE STESSE, misurato il
12/09: qui sono dieci, e `scripts/dod.py` — il righello che controlla da solo
quelle meccaniche — ne ha dieci diverse. Non ha «GREEN» né «QA sign-off», e ha
in più «il lavoro NON è su main».

📌 Quel righello NON è ancora nel ramo principale: arriva con la sua PR, e
finché non arriva `python scripts/dod.py` qui non esiste — detto perché un
modello che prescrive un comando assente insegna a ignorare il modello. Quando
entra, le due liste vanno fatte diventare una sola: due liste sono due criteri.

⚠️ E il vecchio modello chiedeva «`HIPPO_OFFLINE=1 pytest` passes locally».
La suite non si esegue più così: si esegue a fette, e l'esito si legge dal file,
non dall'uscita di una pipe (che sostituisce il codice di uscita della suite).

    python scripts/suite_a_fette.py --fette 3
-->
