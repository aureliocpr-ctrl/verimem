# Una risposta che cita la fonte — runbook

**Chi è.** Un assistente che risponde a una domanda e deve mostrare **su che cosa
si regge**, e che quando non sa **lo dice invece di inventare**. È il caso in cui
l'utente non può controllare da sé: o la risposta porta la sua prova, o è
un'opinione con l'aria di un fatto.

Eseguito dal wheel `verimem 0.7.6` da PyPI, in un ambiente pulito, il 18/09.
Le righe con `✅` e `🔴` portano l'output vero, non l'attesa.

## Il preambolo, come in `01`

```bash
python -m venv .venv-verimem
.venv-verimem/Scripts/activate      # linux/macos: source .venv-verimem/bin/activate
pip install verimem
verimem doctor
```

⏱️ `pip install` **618 s** su questa macchina il 17/09 (la pagina `01` ne
dichiara 280,8: il numero dipende dalla rete, e va riscritto accanto al proprio).
`verimem doctor` **9 s, EXIT=0**.

## I passi

### 1 · Metti in memoria un fatto con la sua fonte
```bash
verimem save "<il fatto>" --topic <un/tuo/argomento> --source "<la fonte>"
```
✅ **Ricevuta attesa**: `admitted`, `grounding_score` presente e non nullo,
`judged=True`.

### 2 · Fai la domanda
```bash
verimem ask "<la domanda in lingua naturale>"
```
✅ **Misurato**, 5 s:
```
intento: find
- Il capannone 12 misura 450 metri quadri. [0.00] moat 99.6
```

🔴 **DUE COSE CHE LA RICEVUTA NON DÀ, e che un assistente che cita avrebbe:**

1. **Il testo della fonte non c'è.** La risposta porta il *punteggio* del giudice
   (`moat 99.6`) — cioè quanto la fonte sostiene il fatto — ma **non la fonte**.
   Chi legge sa che qualcosa l'ha giudicato, non **su che cosa** si regge. Per
   citare serve il testo, non il voto.
2. **`[0.00]` non è un errore tuo.** Sopra la risposta compare:
   `encode exceeded 2.0s budget → degrading (save defers / recall falls back to
   keyword)`. Il richiamo è **degradato a ricerca per parole** e il punteggio di
   somiglianza è azzerato. La risposta resta giusta, ma **non è stata trovata nel
   modo che la pagina promette**: se ti serve la via semantica, scalda prima il
   demone (`verimem warmup`) e rifai.

### 3 · Chiedi qualcosa che la memoria NON sa
```bash
verimem ignorance "<una domanda senza risposta nello store>"
```
✅ **Misurato**, ed è la parte migliore del percorso:
```
no_evidence  qual e' il fatturato del 2027?
    → a source about: 2027, fatturato, qual
no_evidence=1   decide 0.800 (floor dichiarato) — floor=0.800 noise_floor=0.883 (measured)
```
⇒ Dice la **classe** dell'ignoranza (`no_evidence`), **che cosa servirebbe** per
curarla, e **i due pavimenti** — quello dichiarato e quello misurato. Un'astensione
con la sua ragione vale più di una risposta senza fonte.

## Tre modi di cadere
1. **Il comando non esiste** → la pagina è sbagliata. *(Successo: `verimem explain`
   NON esiste in `0.7.6`; il comando è `ask`.)*
2. **La risposta arriva senza la fonte** → difetto del prodotto: apri un ticket
   con l'output. **È il punto 1 del passo 2, ed è aperto.**
3. **L'astensione arriva senza motivo** → idem. Al 18/09 **non** succede:
   `ignorance` la ragione la dà.

## Sei arrivato quando
1. la domanda riceve una risposta **con il testo della fonte accanto**;
2. una domanda senza risposta riceve **la classe dell'ignoranza**;
3. le tre porte rispondono **uguale**.

Al 18/09: **(2) è verde**, **(1) è rosso** (c'è il punteggio, non la fonte), **(3)
non è misurato** — una porta su tre.
