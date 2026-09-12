# La Definition of Done, e le trappole che la fanno sembrare chiusa

**Owner** QA · **12/09/2026** · regola R1 dello `STUDIO-METODO-09-09.md`.

Una casella si spunta in due modi: guardando, oppure credendo di aver guardato.
Questo documento elenca le nove caselle **e, per ognuna, il modo specifico in cui
si può spuntarla a vuoto**. Ogni trappola qui sotto è costata a qualcuno di noi
almeno mezza giornata: sono scritte al passato perché sono successe.

Il controllo meccanico di cinque caselle sta in `scripts/dod.py`
(`--autotest` prova che la casella dei numeri morde ancora). Le altre quattro le
chiude una persona, e il documento dice **dove guardare**.

---

## Le nove caselle

| # | casella | chi la chiude | la trappola |
|---|---|---|---|
| 1 | **RED alla porta**, con l'output nel ticket | l'autore scrive, **il pari ESEGUE** | un RED che l'autore esegue da sé può essere **nato verde**: il pari lo rimette sull'albero PRE-cura e guarda se si accende |
| 2 | **GREEN** | il pari | un verde su un file scelto dall'autore non è il verde della suite: vedi trappola ⑤ |
| 3 | **riga della mappa** aggiornata | `scripts/dod.py` | il righello confronta i **nomi**, non i numeri di riga: una riga che punta al posto sbagliato resta verde |
| 4 | **claim del README** collegato o tolto | chi rivede | `grep` sul **nome del modulo** dà zero quando il claim parla del **concetto**: si cerca il concetto |
| 5 | **docstring con data e comando** | `dod.py` | un numero in un commento **invecchia in silenzio**; un numero citato a memoria è un'ipotesi travestita da misura |
| 6 | **revisore ≠ autore** | il lead | «ho guardato il diff» non è una revisione: la revisione **esegue** o dichiara di non averlo fatto |
| 7 | **fatto salvato con `--source`** | l'autore | la ricevuta va **letta**: `admitted` o `quarantined`, e il campo `moat` se torna `not run` |
| 8 | **CI verde sul tip** | chi merge | vedi le quattro trappole della CI, sotto: è la casella dove si sbaglia di più |
| 9 | **zero copie nuove** | i cricchetti in CI | il tetto di un cricchetto è un **numero**: se ogni PR lo alza di uno, in un mese è un contatore |

---

## Le trappole della CI — la casella 8, che è quella che inganna

1. **Il `conclusion` di un run è la PEGGIORE delle sue parti.** Un job
   `report-only` cancellato tinge di «cancelled» un run i cui gate sono tutti
   passati. **Si legge per JOB**, mai per riga di riepilogo.
   ⚠️ E un livello più sotto: **`gh pr checks` stampa `fail` anche per un job
   `cancelled`**. Misurato il 12/09 su una PR data per rossa: il job era
   `conclusion: cancelled` dopo 51 minuti, lo step `Tests` interrotto, e su
   quel commit **non è mai esistito un verdetto**. «Rosso», «verde» e «nessun
   verdetto» sono tre stati, e la colonna ne mostra due. Si chiede al job:
   `gh api repos/<o>/<r>/actions/jobs/<id> --jq .conclusion`.
2. **Una PR la cui base non è `main` non fa partire niente.** I trigger sono
   `pull_request: branches: [main]`: una PR impilata su un altro ramo **non ha
   `ci` né `security`**, e il vuoto si legge come un verde. Serve
   `gh workflow run <file> --ref <ramo>`, oppure il rebase su main.
3. **Un rerun cancella il rosso dalla lista.** Un rosso guarito da un rerun
   **sparisce da `gh run list`**: il tasso vero di un test intermittente è più
   alto di quello che la lista mostra. **Mai un rerun per far diventare verde
   una cosa**: si classifica il rosso, non lo si nasconde.
   🔀 **Ma il rerun non è sempre la cosa sbagliata, e la differenza è netta**:
   su un job **`failure`** il rerun *nasconde* un verdetto che c'è; su un job
   **`cancelled`** *produce* il verdetto che non c'è mai stato. Prima di
   rilanciare si scrive dove sta il rosso (id del job, nome del test, messaggio
   dell'assert): un rerun non può cancellare ciò che è già stato trascritto.
4. **Un verde è di un COMMIT, non di una PR.** Se qualcuno pusha mentre leggi,
   il verde che stai guardando è di un altro albero. **Un VIA vale sullo SHA**,
   e va riscritto quando il tip cambia.
5. **Un numero fisso di check non è un criterio.** «15/15» era il conteggio di
   un commit in cui giravano anche le wheel; su un altro i check sono 12. Il
   criterio robusto è *«zero check non-verdi quando nessuno è più pending»*.

---

## Le trappole del lavoro locale

6. **Il worktree di revisione va FUORI da `%TEMP%`.** Uno sotto la cartella
   temporanea viene ripulito dal sistema o dal riavvio **mentre lo stai usando**,
   e un `git worktree list` che nomina una cartella sparita blocca `git` finché
   non fai `prune`. Tienilo accanto al repo.
7. **Niente `git stash` per provare un PRE-cura.** Con più istanze sullo stesso
   indice, uno `stash` prende **anche il lavoro di un'altra** e lo rimette dove
   capita. Il modo giusto: un worktree separato, `git checkout -f -q <ref>`,
   `git show "<ref>:<file>" > <file>` e `git clean` alla fine. `git status`
   deve tornare **a zero righe**: si verifica, non si presume.
8. **`MSYS_NO_PATHCONV=1` davanti a `git show "<ref>:<path>"`.** Senza,
   `origin/x:.github/workflows/y.yml` diventa `origin\x;.github\...` e `git`
   risponde «ambiguous argument».
9. **Niente heredoc bash per il Python.** I backtick vengono eseguiti e `\n`
   diventa un newline vero dentro una f-string: il file nasce con un
   `SyntaxError`. Codice e testi si scrivono con lo strumento di scrittura, e
   i messaggi lunghi si passano come file (`--body-file`).
10. **Niente `/tmp` per i file che rileggerai da Python.** La shell lo traduce,
    l'interprete no: `FileNotFoundError: '\\tmp\\x.py'`. Si usa la cartella di
    lavoro della sessione.

---

## Le trappole delle PR e dello squash

11. **`gh pr edit` fallisce per lo scope `read:org`.** Titolo e corpo si
    cambiano con `gh api -X PATCH repos/<owner>/<repo>/pulls/<n> -f title=…
    -f body=…` (REST, esce 0).
12. **Il corpo della PR NON è il messaggio di squash.** Al merge, l'interfaccia
    propone il **titolo della PR** e il **concatenato dei commit di ramo**: se
    nessuno lo sostituisce, i messaggi lunghi del ramo entrano comunque nella
    storia pubblica. **Il messaggio di squash si scrive a mano, al momento del
    merge**, nel formato:
    ```
    <area>: <what, in inglese, una riga>

    What:   che cosa cambia per chi usa il prodotto.
    Why:    che cosa non funzionava, con il numero.
    Proof:  il comando e l'esito (RED→GREEN, o l'output del righello).
    Ticket: T<n>, R<n>.
    ```
    ≤ 10 righe, **nessun nome di istanza, nessun ruolo, nessun path locale,
    nessun numero di macchina**.
13. **Dopo uno squash, `--is-ancestor` dice NO su una cosa che c'è.** Lo squash
    crea un commit **nuovo**: stesso albero, SHA diverso. Quindi lo SHA del ramo
    non è antenato di `main`, e `git merge-base --is-ancestor <tip> main`,
    `git branch --merged` e `git log <sha>..main` rispondono tutti «non c'è» su
    una cura che è entrata. Misurato il 12/09: una cura mergiata in squash
    risultava assente per parentela e presente per contenuto, riga per riga.
    **Si verifica il CONTENUTO** (`git show main:<file> | grep <la riga>`),
    non la parentela — e vale anche per la domanda «questa PR è già dentro?».

---

## Le tre domande che un revisore fa e una checklist non contiene

- **«Se questo numero fosse sbagliato, chi ne uscirebbe bene?»** Un numero che
  dà ragione a chi lo misura non fa attrito, quindi nessuno lo urta.
- **«Questo controllo può diventare rosso?»** Un presidio che non si è mai
  acceso non è un presidio. Si prova rompendo **una riga sola** del prodotto —
  e se l'effetto ha **due barriere**, romperne una non basta: si guarda
  l'effetto, non la riga.
- **«Su quale albero e con quale interprete è stata presa questa misura?»** La
  stessa riga dà due risposte a 156.000× di distanza fra due versioni
  dell'interprete, e uno script lanciato da fuori misura un altro albero.

---

## Che cosa questo documento NON copre

- **Non dice se una cura è giusta**: dice se è stata *verificata*. Una cura
  sbagliata può avere tutte e nove le caselle verdi.
- **Le caselle 1, 4, 6 e 8 non sono meccanizzabili oggi**, e `dod.py` le stampa
  come «👁️ NON MECCANICA» con l'indirizzo di dove guardare, invece di fingerle
  verdi. Un gate che dice sempre «passa» è il modo più efficace di rendere una
  regola inutile mentre sembra applicata.
