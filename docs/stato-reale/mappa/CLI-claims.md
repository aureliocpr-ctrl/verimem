# La CLI riga per riga — `cli.py`, `tui.py`, `doctor.py`

> ws7 «Iris», product owner. Seguito di [README-claims.md](README-claims.md)
> (811/811 righe mappate). Mandato Aurelio 08/09 20:33: *«tutta la superficie
> mappata»*. Qui: **7.921 righe** — `cli.py` 5.997, `doctor.py` 1.478,
> `tui.py` 446 — e **88 comandi** su 13 gruppi Typer.

⚠️ **Cosa NON fa questa mappa.** Non esegue il prodotto. Verifica che il codice
esista e che un presidio lo **invochi**. Un `✅` dice *«la promessa ha
un'implementazione e qualcuno la chiama»*, non *«l'ho vista funzionare»*: dove
ho eseguito, la riga lo dice.

---

## 1. La prima domanda dell'utente: se rinomino un comando, chi se ne accorge?

Il righello è `docs/stato-reale/banchi/ws7-quali-comandi-della-cli-nessun-test-invoca.py`,
e il criterio è **strutturale**, non lessicale: raccoglie le liste letterali di
argomenti nei test (`invoke(cli.app, ["facts", "retirement-log"])`) invece di
cercare il nome del comando. Cercare il nome non funziona: `serve` compare in
**672** file di test e `code` in **462**, quasi sempre come parola inglese.

```
$ python docs/stato-reale/banchi/ws7-quali-comandi-della-cli-nessun-test-invoca.py
cli.py:                         5997 righe
comandi dichiarati:             88
invocazioni viste nei test:     4956
controllo positivo (warmup):    visto
comandi che NESSUN test invoca: 22
EXIT=0
```

### 🔴 Il righello ha sbagliato due volte prima di dare questo 22

Lo scrivo per primo perché **il primo numero che aveva prodotto era 32**, e l'ho
quasi pubblicato.

**① Tre nomi falsi.** La prima versione risolveva **un solo livello** di
`add_typer` e chiamava gli orfani `keys create`, `keys list`, `keys revoke`.
Quei comandi si chiamano **`gateway keys create`**: `gateway_keys_app` sta dentro
`gateway_app`, che sta dentro `app`. Chi fosse andato a cercare `verimem keys
create` non avrebbe trovato niente — e avrebbe dato ragione all'accusa.

**② Dieci falsi orfani, per un punto.** La seconda versione dichiarava che
nessun test invoca `warmup`, mentre `tests/test_cli_warmup.py:36` fa esattamente:

```python
res = runner.invoke(cli.app, ["warmup", "--no-daemon"])
```

La mia regex chiedeva `invoke\(\s*\w+` e **`cli.app` contiene un punto**, che
`\w` non copre: *ogni* invocazione scritta in quella forma era invisibile.
Corretto il parser, gli orfani sono scesi **da 32 a 22**: dieci comandi
(`chat`, `benchmark`, `console`, `episodes show`, `providers models`,
`providers scan`, `skills dedup`, `skills show`, `sleep-now`, `warmup`) erano
accusati a torto. **Il primo numero sovrastimava del 45%.**

🔑 **E il controllo positivo di allora non poteva accorgersene.** Diceva: *«se
raccolgo meno di 20 invocazioni, il parser è rotto»*. Ne raccoglieva **135** e
taceva. Verificava che il righello dicesse *qualcosa*, non che vedesse *tutte le
forme*. Quello di adesso è un **caso che DEVE rispondere**: `warmup` è invocato
alla lettera in un file noto; se non risulta visto, **il numero non si stampa**
(exit 2). Sta in memoria dal 01/09 — *«un'interrogazione vuota si prova su un
caso che DEVE rispondere»* — e oggi ho dovuto sbagliarlo per applicarlo.

### I 22 comandi che nessun test invoca

Il criterio finale è **largo** (raccoglie qualsiasi lista di stringhe nei test),
quindi questi 22 sono un **limite inferiore**: non compaiono in *nessuna* lista
di *nessun* test. Raggruppati per che cosa significano per un utente:

| gruppo | comandi | perché conta |
|---|---|---|
| 🔴 **il self-host al completo** | `gateway serve` · `gateway keys create` · `gateway keys list` · `gateway keys revoke` · `gateway backup` · `gateway restore` | sono **le sei righe che il README insegna** per il server di squadra (`README:580-582`, `632-637`). L'HTTP dietro è testato a fondo (`test_gateway*.py`, decine di file); **la porta CLI che il README mette in prima pagina, no** |
| 🔴 **il backup** | `backup-all` · `facts backup` · `facts restore` | `test_backup_*.py` sono cinque e coprono le **funzioni**; `test_cli.py:85` verifica che `backup-all` sia **registrato**. Nessuno lo **esegue** |
| ⚠️ la diagnosi | `health` · `metrics` · `introspect` · `reset` | `doctor` è invocato, questi no |
| ⚠️ la manutenzione dei fatti | `facts capability` · `facts safety` · `facts archive-narration` | l'unica menzione di `archive-narration` in `tests/` è **una frase in un docstring** (`test_il_rimedio_dice_su_quale_porta_e_eseguibile.py:15`) |
| ⚠️ il resto | `tui` · `code` · `lab live` · `sleep` · `wake` · `providers check` | `tui` è l'ingresso di **446 righe** di `tui.py` |

---

## 2. 🪞 La correzione che devo alla mia mappa di un'ora fa

Alle 22:07 ho chiuso `README-claims.md` dando **✅** a due righe:

| riga del README | che cosa avevo scritto | perché era troppo generoso |
|---|---|---|
| 580-582 (`gateway keys create`, `gateway serve`) | *«`cli.py:106-107` (il gruppo `keys` esiste) … presidi `test_gateway_local_tenant_collision.py`»* | il gruppo **esiste**, i presidi provano **il gateway HTTP**. Nessun test invoca i **comandi** |
| 632-637 (`gateway backup` / `restore`) | *«🌟 **cinque** file, e uno porta il nome della promessa»* | quei cinque provano `backup` come **funzione**. Il comando `gateway backup` non è invocato da nessuno |

Il difetto è **esattamente quello che ho passato la giornata a nominare**: *il
livello a cui misuri decide il verdetto*. Avevo misurato «esiste il gruppo
Typer» e «esiste un test sul backup», e ho scritto ✅ su una promessa che è
**«questo comando funziona»**. Un test sulla funzione non tiene fermo il nome
del comando, il suo gruppo, le sue opzioni: rinomina `gateway backup` in
`gateway snapshot` e la suite resta verde mentre il README diventa falso.

⇒ **Le due righe scendono a ⬜** in `README-claims.md`, con il rimando qui.
*Ritirare per prima la propria riga* è una regola che si applica anche quando la
riga l'hai scritta un'ora fa e ti costa due ✅ su 121.

---

## 3. Il conto, e che cosa significa

**22 comandi su 88 (25%) non sono invocati da nessun test.** Non vuol dire che
siano rotti: vuol dire che **se si rompono, lo scopre l'utente**. E la
concentrazione non è casuale — sei dei ventidue sono la superficie del
**self-host**, cioè quella che il README propone a chi installa il prodotto per
una squadra.

Il contrappeso, e va detto con la stessa prontezza: **66 comandi su 88 sono
invocati**, e la macchina che li invoca è vera (4.956 liste di argomenti nei
test). La CLI non è una superficie abbandonata: ha un buco con una forma
precisa, ed è il gruppo `gateway`.
