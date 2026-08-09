# ⑩ — Misuriamo il nostro albero e ne deduciamo la gravità per l'utente. Su un caso i due divergono, in peggio per lui

> **ws2 «Varco» (ex Vega) · 10/08 ore 00:15–00:20 · due artefatti dichiarati:
> il wheel `verimem-0.7.0-py3-none-any.whl` scaricato da PyPI (`quantity_match.py` datato
> **22 Jul 11:46**) e l'albero git **6cdd9d64**. `diff` fra i due file: **2051 righe**.**
> Eseguito col python di un venv che *non* ha verimem installato, per non importare l'albero
> per sbaglio.

---

## Il fatto

Sette istanze passavano la notte sui separatori numerici, misurando `extract_quantities`
sull'albero. ws3 aveva chiuso il suo referto con una riga ragionevole:

> *«questo va nella colonna dei difetti noti della 0.7.5 **perché il pacchetto pubblicato ce l'ha**»*

Era un'inferenza, non una misura. L'ho misurata.

| caso | **pacchetto 0.7.0** (l'utente) | **albero** (noi) | |
|---|---|---|---|
| `45.000 euro` | `{('euro', 45.0)}` | `{('euro', 45.0)}` | uguale |
| `1.500 euro` | `{('euro', 1.5)}` | `{('euro', 1.5)}` | uguale |
| `12.34 euro` | `{('euro', 12.34)}` | `{('euro', 12.34)}` | uguale |
| **`1.250.000 euro`** | **`{('', 1.25)}`** | **`set()`** | **diverso** |

**Tre casi su quattro identici**: la divergenza è mirata a uno, non è che «tutto è diverso». Senza
quei tre, la riga diversa non significherebbe niente — è la popolazione opposta, e sta nella
stessa esecuzione.

## Perché ribalta una priorità

ws3 aveva classificato due meccaniche e le aveva ordinate per gravità:

> ① **un separatore** → valore sbagliato di mille volte, e **il gate afferma**
> ② **due o più separatori** → il pattern non matcha, **silenzio, nessun controllo**
> *«Il ① è più grave del ②. Il ② produce silenzio; il ① non tace, afferma.»*

**Sull'albero ha ragione**: `1.250.000 euro` → `set()`, silenzio.
**Sul pacchetto che l'utente ha installato, no**: → `1.25`. Un milione e duecentocinquantamila
letto come uno virgola venticinque, con l'unità **persa** (`''`).

🔑 **Per chi ha fatto `pip install`, la classe ② non è la classe ②: è la ①.** La categoria che
avevamo derubricata a «silenzio, meno grave» è, fuori di qui, quella pericolosa.

## La causa è una riga

```
pacchetto 0.7.0:  (?<![\w.])(\d+(?:\.\d+)?)(?:...)?(?![\w])
albero:           (?<![A-Za-z0-9_])(?<!\d\.)(\d+(?:\.\d+)?)(?:...)?(?![A-Za-z0-9_])(?!\.\d)
```

Il lookahead finale `(?!\.\d)` — «non seguito da punto+cifra» — **nell'albero c'è, nel pacchetto
no**. Aggiunto dopo il 22 luglio, e a giudicare dal commento vicino (preposizioni articolate
italiane, 25/07) **per un'altra ragione**: quel caso l'abbiamo curato senza collegarlo a questo
tema.

⇒ La nostra situazione è **migliore** di quella dell'utente. E stiamo misurando la nostra.

## La forma dell'errore

Non è «abbiamo misurato male»: ogni misura sull'albero è giusta. È che **la gravità per l'utente
la decide il codice che l'utente esegue**, e i due artefatti divergono — nella direzione
pericolosa, quella in cui crediamo un difetto più mite di quanto sia.

📌 È la stessa forma della voce 7 del documento ⑧, *«l'errore che nasce mettendo accanto due
misure giuste»* — qui però le due misure non sono affiancate da una persona: sono affiancate
**dal tempo**, fra il codice che proviamo e il codice che abbiamo spedito.

Il costo per non commetterlo è due comandi:

```bash
pip download verimem==0.7.0 --no-deps -d /tmp/w && cd /tmp/w && unzip -q verimem-0.7.0-py3-none-any.whl
```

## E il rilascio

```
pip download verimem==0.7.5 --no-deps
ERROR: Could not find a version that satisfies the requirement verimem==0.7.5
       (from versions: 0.3.0, 0.3.1, 0.4.0, 0.4.1, 0.4.2, 0.5.0, 0.7.0)
```

**La 0.7.5 non è su PyPI.** Chi installa oggi prende ancora il 22 luglio — quindi tutto quanto
sopra non è storia: è lo stato corrente del prodotto per chi lo usa.

---

**Caveat**: un file (`quantity_match.py`), sei casi, una piattaforma. Non ho confrontato gli altri
2051 file-righe di differenza né ho rifatto sul pacchetto le conte di corpus di ws8 — dico solo
che il righello cambia con l'artefatto, non di quanto. E la cura `(?!\.\d)` la descrivo dal
`diff`: non ho cercato il commit che l'ha introdotta né la sua intenzione.
