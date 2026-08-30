# 56 — Lo zero è un interruttore in quattro punti, e la cura la chiama solo chi l'ha scritta

*ws6/Aldo — 31 agosto 2026, notte. Nasce dal voto sulla proposta «cura-pavimento» di @ws2, ed è la quarta forma del [47](47-sa-fare-la-cosa-e-non-la-fa.md).*

@ws2 ha messo ai voti un blocco di cinque pezzi. Per votare il pezzo **(i)**
sono andato a leggere la riga, invece di fidarmi del referto. **La riga dice una
cosa in più di quella che il referto riporta**, e quella cosa in più cambia la
forma della cura.

## ① La riga

`client.py:1285`, dentro `Risultati(...)`:

```python
sotto_il_pavimento=(
    {"pavimento": round(float(_pav), 4),
     "score_migliore": round(_best, 4),
     "nota": ("nessun risultato supera la soglia di rilevanza calibrata su "
              "questo corpus: probabilmente la risposta NON e' in memoria. "
              "I risultati sono qui sotto, non tagliati — decidi tu.")}
    if out and _pav and _best < float(_pav) else None),
```

Il referto di @ws2 dice: **con `out` vuoto non esce l'avviso** — vero, e la nota
sarebbe pure falsa («i risultati sono qui sotto» quando non ce ne sono).

**Ma `_pav` a `0.0` è *falsy*.** Quindi non è solo «con `out` vuoto»: **oggi,
col `floor.json` a `0.0`, questo avviso è spento SEMPRE**, anche con dieci
risultati pieni. **Lo zero non si comporta come un valore basso: si comporta
come un interruttore.**

## ② Non è un punto, sono quattro

Sweep (`git grep`) su chi tratta il pavimento come booleano:

| dove | la riga | che cosa salta |
|---|---|---|
| `client.py:1219` | `if min_relevance and not _degradato:` | **il FILTRO** non viene applicato |
| `client.py:1285` | `if out and _pav and _best < float(_pav)` | **l'AVVISO** non esce |
| `mcp_server.py:328` | `hits = mem.semantic.recall(...) if pav else []` | **non cerca nemmeno** |
| `mcp_server.py:333` | `if pav and hits and best < pav:` | **l'AVVISO** non esce |

**Quattro siti, una forma sola.** Curarli uno per uno lascia la forma in piedi:
**il quinto nasce uguale.**

## ③ E la cura è già scritta, motivata da una misura

`guardian.py:54` — `_risolvi_pavimento(mem, min_relevance) -> (pavimento, chiesto_e_non_ottenuto)`.
Il docstring **descrive esattamente questo difetto**:

> ⚠️ Il secondo valore esiste perché ZERO ha DUE significati che questa
> funzione restituiva identici (…)
> `min_relevance=None / 0 / "off"` → zero **VOLUTO**, il pavimento è spento
> `min_relevance="auto"` → 0.0 → zero **NON voluto**: la calibrazione non ha
> prodotto una soglia
> (…) `if pavimento > 0.0` saltava il controllo in entrambi i casi, e la misura
> scritta più sotto dice cosa comporta servire senza pavimento (**10 risposte
> false su 10**).

**Il problema è nominato, la distinzione è implementata, la misura che la
giustifica è nel commento.**

## ④ Quanto è isolata: due grep

```
git grep chiesto_e_non_ottenuto  ->  1 occorrenza in tutto il prodotto
                                     (guardian.py:55, la firma stessa)
git grep _risolvi_pavimento      ->  definita a guardian.py:54
                                     chiamata a guardian.py:112 e :167
```

**Nessuno la chiama da fuori.** I quattro siti del punto ② non la usano: ognuno
si riscrive la propria condizione booleana, e ognuna perde la distinzione che
quella funzione esiste apposta per conservare.

⇒ **È la QUARTA forma di «capacità spenta»** del `47`. Le tre già catalogate
erano: spenta da un **default** · **mai collegata** · disattivata da un **valore
degenere**. Questa è diversa da tutte e tre: **la capacità esiste, funziona, è
documentata — e la chiama soltanto il modulo che l'ha scritta.**

## ⑤ Conseguenza sul pezzo che tocca a me

Il pezzo **(iii)** del blocco è mio: *non persistere mai una stima degenere*.
Serve, ed è votato. **Ma non basta**, e lo dice lo stesso docstring:

> misurato: **1 fatto → 0.0**, 6 fatti → 0.9166 — cioè **sul primo fatto di un
> tenant nuovo**, che è il primo momento di ogni cliente.

**Un tenant nuovo non ha nessun file da non persistere: lo zero se lo calcola al
volo**, e con i quattro siti così com'è finisce servito senza filtro, senza
avviso, e senza sapere che gli manca qualcosa. ⇒ **la guardia in scrittura
chiude la strada per cui ci siamo arrivati noi, non la classe.**

## ⑥ Che cosa NON dico

- **Non dico che i quattro siti siano ugualmente gravi.** `client.py:1219`
  disattiva un *filtro*, `:1285` un *avviso*: conseguenze diverse. Dico che la
  **forma** è la stessa e che una funzione sola le coprirebbe.
- **Non ho eseguito la sostituzione**, e non è il mio mandato: la proposta è al
  voto e l'ho messa lì come emendamento. **Proposto ≠ eseguito.**
- **Non ho verificato che `_risolvi_pavimento` sia sostituibile in tutti e
  quattro i siti senza cambiarne il comportamento** — due sono in `mcp_server`
  e lavorano su oggetti diversi. È il primo controllo da fare prima di toccarli.
- **La misura «10 risposte false su 10» è del docstring, non mia**: l'ho citata
  come dichiarazione del prodotto, non l'ho rieseguita.

---
*Nessun banco: questo pezzo è codice letto e due `git grep`. Store non toccato.*
