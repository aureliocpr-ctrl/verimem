"""LA PROMESSA: «UN NUMERO = UNA FONTE E' STATA GIUDICATA, `null` = MAI GIUDICATA».

E' scritta nelle **istruzioni del server MCP** — cioe' nel testo che l'agente
che usa il prodotto legge PRIMA di chiamarlo, e che nessuno di noi ha ancora
messo alla prova::

    That separation is NOT readable in `status`, which stays `model_claim`
    either way: it is `grounding_score` that carries it — a number means a
    source was judged, `null` means never judged.

E' una **biiezione dichiarata**, ed e' esattamente il genere di frase che il mio
mestiere deve verificare: dice a chi legge **su quale colonna fidarsi** per
sapere se un fatto e' stato controllato. Se la colonna e' disallineata dalla
fonte, chi si fida di `grounding_score` legge il contrario di com'e' andata.

LE DUE DIREZIONI, e non e' la stessa cosa:

  🅐 **fonte SI', punteggio `null`** — c'era qualcosa da giudicare e il numero
     dice «mai giudicata». Il fatto sembra non verificato **anche se una fonte
     c'era**: il prodotto si sottovaluta, e l'utente scarta materiale buono.

  🅑 **fonte NO, punteggio non-`null`** — un numero di giudizio su niente.
     Questa e' la direzione **pericolosa**: l'utente legge «giudicato» su un
     fatto che non aveva nulla contro cui esserlo.

ATTESA DICHIARATA PRIMA DI GUARDARE: 🅐 esiste e non e' minuscola (una fonte
puo' arrivare per una via che non fa girare il moat), 🅑 e' **rara o nulla**
(scrivere un punteggio senza fonte richiederebbe un difetto vero). ⚠️ **Se
fosse 🅑 la grande, la promessa e' rotta nel verso che conta** e lo dico con
quella forza. Se sono entrambe minuscole, **la promessa REGGE e lo dico con la
stessa forza**: e' un paragone, non un'accusa.

CONTROLLI CHE POSSONO FALLIRE — e sono tutti lezioni gia' pagate in casa:

 (1) 🪞 **DUE COLONNE PORTANO LA FONTE**, non una: `grounding_span` (il testo) e
     `source_signature` (l'impronta). Chiamare «senza fonte» un fatto che ha la
     seconda e non la prima e' la classe ① — *una copia invece della superficie
     unica*. Quindi «ha una fonte» = **almeno una delle due**, e conto anche il
     disaccordo FRA LE DUE, che e' un reperto a se'.
 (2) 🪞 **ENTRAMBE LE POPOLAZIONI**: stampo anche gli ALLINEATI. Su un banco che
     mostra solo i disallineati ogni difetto sembra enorme.
 (3) ⏱️ **L'ERA**: se i disallineati sono tutti vecchi, la promessa e' vera OGGI
     e falsa sullo storico — **due frasi diverse**, e vanno dette separate.
     (`created_at` e' float epoch, non ISO: gia' sbagliato una volta oggi.)
 (4) ✅ **controllo positivo**: la maggioranza DEVE essere allineata. Se non lo
     e', sto leggendo la colonna sbagliata e il numero sopra non vale.

    python -u docs/stato-reale/banchi/il-numero-che-dice-giudicato-e-la-fonte-che-c-era.py
"""

from __future__ import annotations

import datetime as _dt
import sqlite3
import sys


def _era(epoch: float | None) -> str:
    """Il giorno ISO. `created_at` e' un float epoch — leggerlo come stringa
    darebbe zero righe e un banco che sembra pulito (lezione: una misura che
    non c'e' si legge come perfetta)."""
    if not epoch:
        return "(senza data)"
    try:
        return _dt.datetime.fromtimestamp(float(epoch)).strftime("%Y-%m")
    except (ValueError, OSError, TypeError):
        return "(data illeggibile)"


def main() -> int:
    try:
        from verimem.config import CONFIG
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    print(f"  db letto: {CONFIG.semantic_db}")
    c = sqlite3.connect(str(CONFIG.semantic_db))
    righe = c.execute(
        "select grounding_span, source_signature, grounding_score, status,"
        " created_at from facts where superseded_by is null").fetchall()
    print(f"  fatti vivi: {len(righe)}  (popolazione INTERA, e' SQL puro)")
    if len(righe) < 100:
        print("NON RIUSCITO: meno di cento fatti, non misuro una quota.")
        return 1

    def _pieno(v: object) -> bool:
        return v is not None and str(v).strip() != ""

    # (1) le DUE colonne che portano la fonte, e il loro disaccordo
    quadri: dict[str, int] = {}
    ere: dict[str, dict[str, int]] = {}
    solo_span = solo_firma = 0
    for span, firma, punteggio, _st, quando in righe:
        ha_span, ha_firma = _pieno(span), _pieno(firma)
        if ha_span and not ha_firma:
            solo_span += 1
        if ha_firma and not ha_span:
            solo_firma += 1
        fonte = ha_span or ha_firma
        giudicato = punteggio is not None
        k = ("fonte SI" if fonte else "fonte NO") + " / " + (
            "punteggio numero" if giudicato else "punteggio null")
        quadri[k] = quadri.get(k, 0) + 1
        if fonte != giudicato:
            e = _era(quando)
            ere.setdefault(e, {}).setdefault(k, 0)
            ere[e][k] += 1

    print("\n  -- (1) LE DUE COLONNE DELLA FONTE non dicono la stessa cosa")
    print(f"     solo `grounding_span` (niente firma) : {solo_span}")
    print(f"     solo `source_signature` (niente span): {solo_firma}")
    print("     ⇒ per questo «ha una fonte» = ALMENO UNA delle due:"
          " contarne una sola")
    print("       spaccerebbe per «senza fonte» chi la fonte ce l'ha.")

    print("\n  -- (2) LE QUATTRO CASELLE, entrambe le popolazioni")
    tot = sum(quadri.values())
    for k in ("fonte SI / punteggio numero", "fonte NO / punteggio null",
              "fonte SI / punteggio null", "fonte NO / punteggio numero"):
        n = quadri.get(k, 0)
        segno = "✅" if ("SI / punteggio numero" in k
                        or "NO / punteggio null" in k) else "🔴"
        print(f"     {segno} {k:<30}{n:>7}  ({100.0 * n / tot:.1f}%)")

    allineati = (quadri.get("fonte SI / punteggio numero", 0)
                 + quadri.get("fonte NO / punteggio null", 0))
    if allineati < tot / 2:
        print("\n     CADUTO (controllo 4): meno della meta' e' allineata.")
        print("     Sto leggendo la colonna sbagliata: il numero non vale.")
        return 1

    a = quadri.get("fonte SI / punteggio null", 0)
    b = quadri.get("fonte NO / punteggio numero", 0)

    print("\n  -- (3) L'ERA dei disallineati (mese di `created_at`)")
    for e in sorted(ere):
        det = "  ".join(f"{k.split('/')[1].strip()}={v}"
                        for k, v in sorted(ere[e].items()))
        print(f"     {e}   {sum(ere[e].values()):>6}   {det}")

    print("\n  == LA RIGA CHE CONTA")
    qa, qb = 100.0 * a / tot, 100.0 * b / tot
    if b > 0:
        print(f"     🔴 **{b} fatti ({qb:.1f}%) portano un PUNTEGGIO senza"
              " avere una fonte.** Chi")
        print("     legge `grounding_score` per sapere se il fatto e' stato"
              " controllato")
        print("     legge «giudicato» su un fatto che non aveva nulla contro"
              " cui esserlo.")
    else:
        print("     ✅ **ZERO punteggi senza fonte**: nel verso pericoloso la"
              " promessa REGGE.")
    if a > 0:
        print(f"     🟡 **{a} fatti ({qa:.1f}%) hanno una FONTE e punteggio"
              " `null`**: il prodotto")
        print("     si sottovaluta — c'era qualcosa da giudicare e la colonna"
              " dice di no.")
    else:
        print("     ✅ **ZERO fonti non giudicate.**")
    if a == 0 and b == 0:
        print("     ⇒ **LA PROMESSA E' VERA**, e lo dico con la stessa forza"
              " con cui avrei")
        print("     detto il contrario. E' un paragone, non un'accusa.")

    print("\n  cinque esempi della casella piu' numerosa fra le due rotte:")
    peggiore = "fonte NO / punteggio numero" if b >= a else \
        "fonte SI / punteggio null"
    n = 0
    for span, firma, punteggio, st, quando in righe:
        fonte = _pieno(span) or _pieno(firma)
        giudicato = punteggio is not None
        k = ("fonte SI" if fonte else "fonte NO") + " / " + (
            "punteggio numero" if giudicato else "punteggio null")
        if k == peggiore:
            print(f"     [{_era(quando)}] status={st!r} score={punteggio!r}"
                  f" span={'SI' if _pieno(span) else 'no'}"
                  f" firma={'SI' if _pieno(firma) else 'no'}")
            n += 1
            if n >= 5:
                break
    if n == 0:
        print("     (nessuno: la casella e' vuota)")

    print("\n  ⚠️ COSA NON DICE: **non ho chiesto al prodotto**, ho letto le"
          " colonne.")
    print("  Un fatto potrebbe essere stato giudicato e il punteggio scritto"
          " altrove;")
    print("  in quel caso il difetto e' la COLONNA che la promessa cita, non"
          " il giudizio.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
