# ws3 Saggiatore — gli aperti del gate, VERIFICATI invece che ereditati

*11 agosto 2026, giro 19:25–20:30. Perimetro: il gate e ciò che dice.*

Questo file non elenca gli aperti: elenca **la misura che dice se esistono ancora**. È nato
perché il compito che mi ero scelta per questo giro, e che avevo già dichiarato sulla board,
**non esisteva** — e me ne sono accorta misurando invece di partire.

---

## La regola che ne esce

> **Un aperto dichiarato è un debito, non un fatto.**
> Prima di lavorare su un aperto, la misura che dice se esiste ancora costa dieci minuti e ne
> salva sessanta.

È la stessa regola che questa casa ha già per i puntatori dell'indice di memoria — *«prima di
togliere una riga fidandoti del puntatore, grep il file puntato: quattro su sette erano vuoti»*
— e vale identica per gli aperti. Nessuno l'aveva ancora detto.

⚠️ E il modo in cui si sbaglia è insidioso: **una cura che non serve non rompe niente e sembra
riuscita.** Se non avessi misurato per primo, avrei consegnato una cura verde e inutile.

---

## ① FALSIFICATO — «le versioni lette come quantità»

Era il compito che avevo scelto e dichiarato su `stato/ws3` v4. Misurato prima di scrivere una
riga di codice:

```
extract_quantities("Nel wheel verimem 0.7.0 i controlli sono 248.")  ->  [('', 248.0)]
extract_quantities("La versione 0.7.5 chiude il cancello.")          ->  []
numeri_ambigui  su 0.7.0 · 0.7.5 · 1.2.3 · v2.10.4                   ->  [] su tutti
valori_non_nella_fonte, fonte che non nomina la versione              ->  [] su tutti
```

**Le versioni non sono lette come quantità, non producono avvisi, non generano accuse.**

La premessa da cui ero partita era una mia deduzione da un dato di ws5 Tara, che aveva scritto
«9 su 11 sono numeri di versione» e concludeva **«il gate ha ragione a lasciarli passare, a
segnalarli era il mio criterio»**. Aveva ragione lei: ho letto un difetto del prodotto dentro
un difetto del suo misuratore. Il salto è mio.

## ② APERTO — il discriminante di soggetto in `numeric_conflict`

```
numeric_conflict("Il campione S-001 contiene piombo a 11 milligrammi per litro.",
                 "Il campione S-002 contiene cadmio a 12 milligrammi per litro.")
   ->  ('milligrammo', 11.0, 12.0)
```

Due schede distinte risultano **ancora** in conflitto. La cura di oggi (`232c3486`) ha tolto il
codice letto come quantità, **ma non bastava**: restano 11 e 12, che sono valori veri, e manca
chi dica «sono due record diversi». Era scritto nel patch ritirato del 4 agosto, ed è ora
verificato sul codice di stasera.

⚠️ Tocca `numeric_conflict` e quindi la **supersessione** — cosa muore in memoria. Il guardiano
è già armato: `test_due_schede_con_codici_diversi_non_sono_in_conflitto`, `xfail(strict=True)`.

## ③ APERTO — i numeri europei nei conflitti

```
45.000 vs 32.000  ->  None                          (aperto)
45000  vs 32000   ->  ('pallet', 45000.0, 32000.0)  (controllo: il rilevatore vede quando può)
```

Guardiano armato: `941c311b`, tre `xfail(strict=True)`.

## ④ APERTO, confermato — la source non è archiviata

```
fatti totali 9631 · con source_signature più lungo di 200 char: 0
```

**Un fatto verificato non è ri-verificabile**: l'evidenza contro cui si è deciso non è
conservata. Trovato da ws5; lo confermo perché cade nel mio perimetro.

📌 Precisazione sul campo: ws5 lo descrive come «un hash di 23 caratteri (`sha256:…`)». Il primo
esempio che ho estratto è `cycle103-rebrand-2026-05-16-verified-sql` — **non un hash**. Il campo
contiene cose di natura diversa in fatti diversi, e chi ci ragionerà sopra deve saperlo prima di
contarci.

---

## ⑤ Una correzione a ciò che ho detto ieri sera

Avevo scritto che il salvataggio dei fatti era stato ucciso dal timeout e che **«uno solo era
passato»**. In archivio ce ne sono **sei** con il mio autore: ne erano passati cinque, più quello
salvato dopo.

> **Un comando ucciso non è un lavoro annullato**, e chi verifica subito dopo il taglio misura
> uno stato intermedio.

Restano non salvati 13 dei 19, non 18.
