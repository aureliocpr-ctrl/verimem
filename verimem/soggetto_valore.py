"""`L4.3` — il legame SOGGETTO-VALORE: il valore c'è nella fonte, ma è di un altro.

Copre lo **scambio di attribuzione**: un claim che riporta un valore che la
fonte contiene davvero, ma **riferito a un'altra entità**. `L4.1` non lo vede
per costruzione — confronta *insiemi di valori*, e chiede «*questo numero c'è
nella fonte?*», non «*è predicato di QUESTO soggetto?*» ⇒ la ricerca riesce e
il layer tace. Misurato il 27-28/08: su 12 scambi `L4.1` parla **0 volte**, e
la separazione fra ammessi e fermati la produce **solo** il giudice neurale,
la cui protezione **si sgretola con la lunghezza della fonte** (7/12 ammessi a
453 caratteri, 10/12 a 930) mentre quella di `L4.1` **non cambia** (0/3 a ogni
lunghezza).

PERIMETRO, e le tre esclusioni sono deliberate:

- **Non copre l'omissione.** La regola scatta solo dove la fonte
  **CONTRADDICE**, mai dove **TACE**; l'omissione *è* silenzio. Segnalare il
  silenzio inonda di falsi positivi — e il pavimento non parte da zero: una
  parafrasi fedele è già quarantinata a 0.37 senza questo layer.
- **Non copre i numerali scritti a parole.** Serve un normalizzatore, che è un
  pezzo separato: se non c'è un glifo 0-9 l'estrattore non vede il valore.
- **Non copre le percentuali**, finché `extract_quantities` le restituisce
  senza unità (`('', 5.0)`). La guardia G1 esclude i valori senza unità, e
  senza di essa un claim VERO viene segnalato: la numerazione degli articoli
  («Art. 3») finisce nello stesso secchio delle percentuali. È un **costo
  dichiarato**, non un difetto di questo layer.

AVVISO, NON VETO. La coda di revisione è a **1057 contro una soglia di 500** e
cresce **cinque volte** più in fretta di quanto si svuoti (misura di ws6,
28/08): un veto nuovo alimenta una coda che nessuno drena, e il prodotto stesso
avverte che «*a queue nobody drains turns 'held for review' into 'silently
dropped'*» (`review_queue.py:190`). Promuoverlo a veto è una decisione che vuole
una misura su corpus, non un default.
"""

from __future__ import annotations

import re
import unicodedata

#: Segmentazione: punteggiatura **e** a-capo **e** punto e virgola. Il regime a
#: sola punteggiatura dimezza il segnale: A/B misurato sul corpus vero, 3030
#: giudicabili — falsi allarmi 65,7% con `.!?` contro 31,2% aggiungendo newline
#: e `;`, **con gli scambi colti invariati a 15/16**. Curare la segmentazione
#: non costa sensibilità.
_FRASE = re.compile(r"(?<=[.;!?])\s+|\n+")

#: Parole funzionali IT+EN. ⚠️ Deliberatamente LOCALE e non `query_intent._STOP`:
#: quella lista è di 76 parole dichiarate per un altro scopo (i termini di
#: contenuto di una query di conteggio) e **non contiene** `il lo la al alla per
#: con su da e` né `and for` — misurato il 28/08. Usandola, un ARTICOLO diventa
#: un'ancora e un caso vero cambia esito. Resta incompleta: è un limite
#: dichiarato, non una lista definitiva.
_FUNZIONALI = frozenset({
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "di", "a", "da",
    "in", "con", "su", "per", "tra", "fra", "del", "dello", "della", "dei",
    "degli", "delle", "al", "allo", "alla", "ai", "agli", "alle", "dal",
    "dallo", "dalla", "dai", "dagli", "dalle", "nel", "nello", "nella", "nei",
    "negli", "nelle", "sul", "sullo", "sulla", "sui", "sugli", "sulle",
    "col", "coi", "e", "ed", "o", "od", "che", "non", "ne", "si", "ci", "vi",
    "essere", "sono", "era", "erano", "stato", "stata", "risulta", "risultano",
    "art", "articolo", "comma", "pari", "ogni", "come", "piu", "meno",
    "presente", "presenti", "questo", "questa", "quello", "quella",
    "the", "of", "an", "and", "or", "for", "to", "on", "at", "by",
    "is", "are", "was", "were", "be", "been", "this", "that", "these", "those",
    "with", "from", "as", "it", "its",
})

#: I token d'unità non sono soggetti. Senza questa esclusione «mg» finisce fra
#: le ancore e una fonte che nomina il dosaggio in una frase separata produce
#: un falso `ok` — misurato il 28/08 mentre scrivevo il banco.
_UNITA_TOK = frozenset({
    "mg", "ml", "kg", "gr", "grammi", "euro", "eur", "giorni", "mesi", "anni",
    "settimane", "ore", "percento", "cento", "days", "months", "years",
})

_PAROLA = re.compile(r"[a-zA-Zà-ùÀ-Ù']{2,}")


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _frasi(testo: str) -> list[str]:
    return [f.strip() for f in _FRASE.split(testo) if f and f.strip()]


def ancore(testo: str) -> set[str]:
    """I token che possono identificare un SOGGETTO: né funzionali né unità."""
    return {n for n in (_norm(x) for x in _PAROLA.findall(testo))
            if n not in _FUNZIONALI and n not in _UNITA_TOK}


def _valori(testo: str) -> set[tuple[str, float]]:
    from .quantity_match import extract_quantities  # noqa: PLC0415

    return extract_quantities(testo, come_fonte=True)


def _e_identificativo(testo: str, valore: float) -> bool:
    """Un identificativo SEGUE il suo sostantivo, una quantità lo PRECEDE.

    La distinzione è **posizionale, non lessicale**, e non è mia: è già del
    prodotto (`vicinato_del_valore.py:36-37`, dichiarata su IT/EN/DE/FR/ES).
    «ordine 77» è un identificativo, «3 anni» una quantità — e uno scambio fra
    identificativi non è uno scambio di attribuzione.
    """
    testo_n = _norm(testo)
    ago = str(int(valore)) if float(valore).is_integer() else str(valore)
    ago_re = r"(?<![\d.,])" + re.escape(ago) + r"(?![\d.,])"
    for m in re.finditer(ago_re, testo_n):
        prima = testo_n[max(0, m.start() - 40):m.start()].split()
        dopo = testo_n[m.end():m.end() + 40].split()
        d = dopo[0] if dopo else ""
        if d and d not in _FUNZIONALI:
            return False                      # quantità: il nome SEGUE il numero
        p = prima[-1] if prima else ""
        if p and p not in _FUNZIONALI:
            return True                       # identificativo: il nome PRECEDE
    return False


def avviso_soggetto_valore(proposition: str, source: str) -> dict | None:
    """L'avviso `L4.3`, oppure ``None`` quando il layer non ha nulla da dire.

    Si ASTIENE ogni volta che non può distinguere i soggetti: l'astensione è
    l'esito sicuro, e la segnalazione va prodotta solo dove la fonte lega il
    soggetto del claim a un valore **diverso**.
    """
    if not proposition or not source:
        return None
    v_claim = _valori(proposition)
    if not v_claim:
        return None
    v_fonte = _valori(source)
    frasi = _frasi(source)
    ancore_claim = ancore(proposition) & ancore(source)

    for unita, num in sorted(v_claim, key=lambda x: (x[0], x[1])):
        # ① il valore non è nella fonte: è `L4.1`, non nostro. Disgiunti per
        #    costruzione, così la ricevuta non porta due referti sullo stesso
        #    difetto.
        if (unita, num) not in v_fonte:
            continue
        # G1 — senza unità non si accoppia. `extract_quantities` restituisce
        #    `('', 5.0)` sia per «5%» sia per il «5» di «Art. 5»: accoppiarli
        #    segnala claim VERI. Vale il 61,8% dei falsi allarmi sul corpus
        #    reale. Le percentuali rientrano quando l'estrattore darà
        #    loro un'unità.
        if not unita:
            continue
        # ② un identificativo non è una quantità.
        if _e_identificativo(proposition, num) and _e_identificativo(source, num):
            continue
        if not ancore_claim:
            continue
        # ③ contano solo le ancore DISCRIMINANTI: un token presente in più
        #    frasi candidate non identifica nulla. Senza questo, uno scambio su
        #    due viene assolto perché il sostantivo di testa è comune per
        #    costruzione (penale/penale, canone/canone).
        candidate = [f for f in frasi if any(u == unita for u, _n in _valori(f))]
        occorrenze: dict[str, int] = {}
        for f in candidate:
            for a in ancore(f):
                occorrenze[a] = occorrenze.get(a, 0) + 1
        discriminanti = {a for a in ancore_claim if occorrenze.get(a, 0) == 1}
        if not discriminanti:
            continue
        # ④ il valore sta in una frase che porta un'ancora discriminante ⇒ è
        #    attribuito al soggetto giusto. Se però quella frase porta DUE
        #    valori della stessa unità la finestra è ambigua: si ASTIENE, e
        #    non si prosegue — proseguire troverebbe l'altro valore della
        #    stessa frase e segnalerebbe un VERO (diagnosi misurata in review).
        ambigua = False
        attribuito = False
        for f in frasi:
            if (unita, num) in _valori(f) and discriminanti & ancore(f):
                if len({n for u, n in _valori(f) if u == unita}) >= 2:
                    ambigua = True
                else:
                    attribuito = True
                break
        if ambigua or attribuito:
            continue
        # ⑤ la fonte lega il soggetto del claim a un valore DIVERSO della
        #    stessa unità ⇒ contraddizione, non silenzio.
        for f in frasi:
            if not (discriminanti & ancore(f)):
                continue
            altri = [n for u, n in _valori(f) if u == unita and n != num]
            if not altri:
                continue
            # G2 — se il claim cita ANCHE l'altro valore non sta scambiando:
            #      sta riportando entrambi. 27,6% dei falsi allarmi misurati.
            if any((unita, n) in v_claim for n in altri):
                continue
            # G3 — stesso numero a precisione diversa (97.6 / 97.5968).
            if any(abs(n - num) <= abs(num) * 0.01 for n in altri):
                continue
            soggetto = ", ".join(sorted(discriminanti & ancore(f))[:3])
            return {
                "layer": "L4.3",
                "reason": (f"the source gives {soggetto} the value {altri[0]:g} "
                           f"{unita}, while the claim says {num:g} {unita}: the "
                           f"number is in the source but attached to something "
                           f"else"),
                "advice": ("check which subject the number belongs to — quoting "
                           "a value the source states about a DIFFERENT entity "
                           "is the one error the grounding judge does not catch"),
            }
        # ⑥ la fonte TACE sul valore di quel soggetto: non è una contraddizione.
    return None
