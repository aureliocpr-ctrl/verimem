# ⑧ — Cosa ci ha insegnato un rilascio: sette cose sugli artefatti

> **ws2 «Vega» · 09/08 ore 22:10 · `origin/main` `34d4d272`, worktree separato, `git status` vuoto**
> In quattro ore, otto istanze hanno portato la 0.7.5 dal bloccante alla pubblicabilità. Le misure
> stanno nei referti; **queste sette righe stanno solo nei messaggi**, e domani si ripetono.
> Ogni voce ha il caso che l'ha prodotta, misurato — nessuna è una massima.

---

## 1. Lo `sha256` identifica il FILE, non il CONTENUTO

Alle 21:39 ne avevamo **cinque** wheel «0.7.5 diversi», e due di noi ne avevano collaudati due
senza accorgersene. La regola nata sul momento — *chi nomina un wheel dichiara sha256 + ora* — è
giusta e **non basta**:

```
wheel A (da 84a4a706)   sha256 d7e81cdc…
wheel B (da ec411ac1)   sha256 8370de61…
contenuto: 458 file contro 458 · solo in A: 0 · solo in B: 0 · DIVERSI: 0
```

**Contenuto identico, impronte diverse**: lo zip incorpora i timestamp, quindi l'sha cambia a
ogni build anche se non cambia una virgola. Due persone possono collaudare wheel con sha diversi
ed essere d'accordo — ed è proprio il caso che ci ha spaventati.
👉 **Per dire «è lo stesso» serve confrontare i file dentro**, ed è una quindicina di righe.

## 2. Anche un verdetto di merge scade — non solo un conteggio

ws4 aveva usato `ws2/abstention` come controllo negativo: *«ne dà 1, quindi il metodo
distingue»*. Venti minuti dopo:

```
ws2/abstention        x main         → 0 conflitti
ws2/abstention        x origin/main  → 0 conflitti
origin/ws2/abstention x main         → 0 conflitti
origin/ws2/abstention x origin/main  → 0 conflitti
```

Non era cambiato il ramo (stesso SHA, `ec75d0c6`): era cambiato **main**, tre volte in pochi
minuti (`ec411ac1` → `661b364a` → `34d4d272`).
🔑 **`git merge-tree` è una misura su due oggetti che si muovono, non una proprietà del ramo.**
Il verdetto su ws7 restava valido; il controllo negativo no — e un risultato senza il suo opposto
vale meno di quanto sembri.

## 3. Il README è **dentro** il pacchetto, ed è permanente quanto il numero di versione

`Description-Content-Type: text/markdown`, e il corpo del METADATA **è** il README: quello che si
vede su pypi.org. Nel primo wheel 0.7.5 c'era, testuale:

```
- **the CLI cannot delete at all.** `verimem forget` is not a command — of the
```

una riga che ws1 aveva appena ritirato come falsa, **su un tema GDPR**. E PyPI non riusa un
filename nemmeno dopo la cancellazione della release (ws8, documentazione warehouse): un README
sbagliato nella 0.7.5 non si corregge, si passa alla 0.7.6.
🔑 **«Correggere dopo» non era un'opzione: una delle due strade non esisteva.**
⇒ **Ogni riga di README è una riga di prodotto**, non di documentazione. Il banco controlla i
*comandi* che il README insegna; le *affermazioni* può verificarle solo chi misura la porta.

## 4. Un numero in un documento immutabile va ancorato a due estremi fissi

Il CHANGELOG diceva «419 commits since 0.7.0»: esatto alle 21:30, falso un'ora dopo (430, poi
433). Il secondo estremo era HEAD, che cresce.

E il numero *giusto* era un terzo ancora — per un difetto del metodo di conteggio: cercare il bump
con `git log -1 -S 'version = "0.7.0"'` trova, dopo il bump, **il commit che quella riga l'ha
tolta**, non quello che l'aveva introdotta. Serve `--reverse`.

| | |
|---|---|
| 0.7.0 → HEAD alle 21:59 | 430 |
| 0.7.0 → HEAD alle 22:05 | 433 |
| **0.7.0 → il commit del bump** | **420** ← non si muove più |

Su main la cura è stata *«Over 400 commits»*: risolve pure, per un'altra strada. **La differenza
resta utile a sapersi**: la forma vaga non scade mai ma dirà la stessa cosa anche per la 0.8; la
forma ancorata dice cosa contiene *questa* release e resta vera.

## 5. `twine check` verifica che il markup RENDA, non che renda BENE

Il controllo che PyPI fa prima di accettare — e che ci mancava — è una riga:

```bash
python -m twine check dist/*.whl
```

Ma ha un limite, misurato e non dedotto: due wheel dello stesso giorno, uno con **7 righe di
tabella indentate dentro un bullet** e uno con **0**, passano **entrambi**. Una tabella indentata
non è un errore di sintassi: PyPI la accetta e la mostra male.
⇒ Copre «l'upload viene RIFIUTATO», non «la pagina viene bene». Scritto nel test, perché senza
quella riga verrebbe letto come una garanzia che non dà.

## 6. Un ramo già assorbito non può fare da controllo negativo

ws4 aveva usato `ws2/abstention` come caso che *deve* fallire, per dimostrare che il metodo
distingue. Poco dopo dava 0 conflitti in tutte le combinazioni — e la ragione non era
«main si muove», che è la mia formulazione generica, ma la sua, precisa:

> **Un ramo mergiato dà zero per costruzione.**

⇒ Il controllo negativo va scelto fra i rami **non ancora assorbiti**, e va **ri-scelto** quando
vengono assorbiti. Un verdetto positivo senza un negativo vivo accanto vale meno di quanto sembri.
📌 E la sua regola gemella: *chi usa un controllo negativo ne dichiari l'SHA*, come per i wheel.

## 7. L'errore che nasce mettendo accanto due misure **giuste**

La formulazione è di ws1, dopo aver ritirato un allarme suo — ed è la più utile della serata:

> Non «ho misurato male»: l'errore nasce nel **mettere accanto due misure giuste con metodi
> diversi**. E sembra più solido, perché ha due misure vere dietro.

Il suo caso: `419` (moduli ricorsivi, da git) accanto a `384` (primo livello, dal wheel) →
«35 mancanti», di cui 4 sarebbero stati quelli di governo. Nessuno dei due numeri era sbagliato.
Misurati con lo stesso metodo: git 388/419, wheel 388/419, **zero mancanti**.

Lo stesso è successo a me un'ora dopo, sui comandi: **52** (parser del sorgente), **40**
(`--help`), **37** (ws4) — tre insiemi diversi con lo stesso nome. Lì il confronto sbagliato non
ha prodotto un falso allarme ma **un test cieco**: verificava i comandi del README contro il
sorgente, e avrebbe approvato `verimem tui`, che è definito e invisibile.

🔑 **Un numero non è confrontabile con un altro finché non è confrontabile il metodo.** È la
forma più insidiosa perché non ha l'aspetto di un errore: ha due fonti, due misure e una
conclusione — e la conclusione è falsa.

---

## La forma comune, che è una sola

Tre volte in una sera due di noi hanno avuto ragione **entrambe** — sui cinque wheel, sui tre
conteggi, sul controllo negativo. Mai per un errore di misura: sempre perché **l'oggetto misurato
era diverso**, o lo stesso oggetto in un istante diverso.

> Un artefatto non è il suo nome. `verimem 0.7.5` sono stati sei file diversi in un'ora;
> `main` è stato quattro SHA in venti minuti. **Chi consegna un verdetto dichiari su cosa
> l'ha misurato — e chi lo verifica usi lo stesso.**

Lo strumento che risponde a metà di questa domanda esiste ed è di due righe:

```bash
python scripts/artefatto.py
# verimem 0.7.5 · mcp 1.29.0 · da pacchetto · git n/d (misuri il pacchetto, non l'albero)
```

**Caveat**: una sera, otto istanze, un rilascio, un sistema operativo. Le sette voci sono
generalizzazioni da un caso ciascuna — tranne la 1, la 2 e la 7, che ne hanno due. Nessuna è
stata verificata su un secondo rilascio, perché un secondo rilascio non c'è ancora stato.
**Le voci 6 e 7 non sono mie**: sono di ws4 e ws1, formulate meglio di come le avevo scritte io,
e le riporto con il loro nome perché una lezione senza autore si ricorda peggio.
