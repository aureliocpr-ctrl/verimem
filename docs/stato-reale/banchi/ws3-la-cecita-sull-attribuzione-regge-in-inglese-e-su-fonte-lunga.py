"""Provo a FALSIFICARE il mio reperto delle 01:34 prima che qualcuno lo usi.

Alle 01:34 ho misurato (`a43bd32e`) che il giudice da' **~98-100 a una falsita'
per scambio di soggetto** e **0,5 a un valore assente** ⇒ discrimina la
**presenza** dei valori, non la loro **attribuzione**. Era su **una** tabella,
**una** prosa, **sette** claim, **in italiano**, con **un solo** tipo di
falsita'. Prima che entri in un contratto di uscita, provo a **romperlo** io.

TRE ATTACCHI, ognuno una via per cui il reperto potrebbe essere un artefatto:

  ① INGLESE — le liste monolingui sono una nostra classe nota di difetto. Se
    la cecita' fosse un fatto dell'italiano, in inglese dovrebbe sparire.
  ② FONTE LUNGA (>1500 char) — sopra il budget entra `select_relevant_span`
    (`grounding_gate.py:371`), che sotto i 1500 **non gira affatto**
    (`5bd11563`). Lo span potrebbe togliere la riga che rende falso lo scambio
    — o tenerla, e allora il reperto peggiora.
  ③ ALTRO TIPO DI FALSITA' — non solo scambio di soggetto: **negazione** e
    **ordine di grandezza**. Se il giudice le prendesse, la sua cecita' sarebbe
    specifica dell'attribuzione e non una generica compiacenza.

LA PREDIZIONE, scritta prima di eseguire:
    ① la cecita' REGGE in inglese (non e' un fatto della lingua)
    ② REGGE anche su fonte lunga
    ③ il giudice PRENDE l'ordine di grandezza (il valore non c'e') e NON prende
      la negazione (i valori ci sono tutti, cambia solo il segno logico)

⚠️ Sono TRE predizioni distinte: se ne cade una, cade quella, non il reperto.
E se cadono ① o ②, **il reperto delle 01:34 va ridotto alla sua popolazione.**

🔴 **ESITO — ① È CADUTA, ED È LA PIU' IMPORTANTE.**

    blocco                    vero   SCAMBIO   assente
    ① ITALIANO               100.0     100.0       0.5
    ① INGLESE                 99.8       5.3       0.8   <- la cecita' SPARISCE
    ② FONTE LUNGA (>1500)    100.0     100.0       0.2   <- regge sopra il budget
    ③ negazione 34.6  ·  ordine di grandezza 0.5  ·  UNITA' SBAGLIATA 99.9

**Stesso errore logico, stessa struttura di fonte, stessi numeri: cambia solo
la LINGUA e il punteggio passa da 100,0 a 5,3** — 94,7 punti di scarto.
⇒ **La cecita' sull'attribuzione NON e' una proprieta' del giudice: e' una
proprieta' del giudice IN ITALIANO.** Il titolo che avevo dato alle 01:34
(«il giudice non vede l'attribuzione») era **piu' largo dei miei dati**, e va
ristretto: **in inglese la vede benissimo.**

🔑 E la conseguenza pesa piu' della correzione: **la protezione del gate dipende
dalla LINGUA, e la lingua in cui scriviamo di piu' e' quella debole.** Un
cliente italiano e' protetto meno di uno inglese dallo stesso prodotto, sulla
falsita' piu' facile da produrre.

🔴 **E ③ HA TROVATO UNA SECONDA CECITA' CHE NON CERCAVO**: «*59 run cancellati
**al minuto**» prende **99,9**. Il giudice non vede l'**unita' sbagliata** — un
valore giusto con la grandezza sbagliata passa come vero. Invece prende
l'ordine di grandezza (590 -> 0,5) e prende in parte la negazione (34,6).
⇒ Il profilo vero e': **vede i valori ASSENTI, non vede a CHI appartengono
(in italiano) ne' in QUALE unita' sono espressi.**

⚠️ ② regge: sopra il budget, con `select_relevant_span` in gioco, lo scambio
prende ancora **100,0**. Lo span non salva.

CONTROLLO CHE DEVE POTER FALLIRE: in ogni blocco, il claim **vero** deve stare
alto e il valore **assente** basso. Senza questi due, un punteggio alto sullo
scambio non distingue «cecita' sull'attribuzione» da «giudice che dice sempre
si'».

REGIME: store TEMPORANEO, cross-encoder locale su disco (nessuna API esterna).
Lo store di Aurelio NON e' toccato.

    python docs/stato-reale/banchi/ws3-la-cecita-sull-attribuzione-regge-in-inglese-e-su-fonte-lunga.py
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

IT = (
    "Il workflow ci ha avuto 50 run, di cui 0 cancellati, e il suo esito e' "
    "verde. Il workflow security ha avuto 60 run, di cui 59 cancellati, e il "
    "suo esito e' rosso. Il workflow presidi-lenti ha avuto 14 run, di cui 1 "
    "cancellato, e il suo esito e' verde."
)

EN = (
    "The ci workflow had 50 runs, 0 of them cancelled, and its outcome is "
    "green. The security workflow had 60 runs, 59 of them cancelled, and its "
    "outcome is red. The presidi-lenti workflow had 14 runs, 1 of them "
    "cancelled, and its outcome is green."
)

#: riempitivo per superare il budget di 1500: prosa VERA e non ripetuta a caso,
#: cosi' lo span selector ha di che scegliere invece di vedere N copie.
_ZAVORRA = "\n".join(
    f"La nota numero {i} del registro operativo riguarda una revisione "
    f"periodica della documentazione interna e non contiene misure."
    for i in range(1, 15)
)
IT_LUNGA = _ZAVORRA + "\n" + IT + "\n" + _ZAVORRA


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    os.environ["HIPPO_DATA_DIR"] = str(tmp)
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  REGIME: HIPPO_DATA_DIR={tmp}  (store di Aurelio NON toccato)")
    print(f"  fonte lunga: {len(IT_LUNGA)} char"
          f"  (budget giudice 1500 ⇒ lo span selector ENTRA in gioco)")
    mem = Memory(str(tmp / "falsif.db"))

    def s(claim: str, fonte: str, tag: str) -> float | None:
        return mem.add(claim, topic=f"fx/{tag}", source=fonte,
                       validate="full").get("grounding_score")

    blocchi = [
        ("① ITALIANO (controllo)", IT, [
            ("vero     ", "Il workflow security ha 59 run cancellati."),
            ("SCAMBIO  ", "Il workflow ci ha 59 run cancellati."),
            ("assente  ", "Il workflow ci ha 777 run cancellati."),
        ]),
        ("① INGLESE", EN, [
            ("vero     ", "The security workflow had 59 cancelled runs."),
            ("SCAMBIO  ", "The ci workflow had 59 cancelled runs."),
            ("assente  ", "The ci workflow had 777 cancelled runs."),
        ]),
        ("② FONTE LUNGA (>1500)", IT_LUNGA, [
            ("vero     ", "Il workflow security ha 59 run cancellati."),
            ("SCAMBIO  ", "Il workflow ci ha 59 run cancellati."),
            ("assente  ", "Il workflow ci ha 777 run cancellati."),
        ]),
        ("③ ALTRE FALSITA' (it)", IT, [
            ("NEGAZIONE", "Il workflow security non ha run cancellati."),
            ("ORD.GRAND", "Il workflow security ha 590 run cancellati."),
            ("UNITA    ", "Il workflow security ha 59 run cancellati al minuto."),
        ]),
    ]

    esiti: dict[str, dict[str, float | None]] = {}
    for titolo, fonte, claim_set in blocchi:
        print(f"\n  ── {titolo}")
        esiti[titolo] = {}
        for et, claim in claim_set:
            v = s(claim, fonte, f"{titolo[:4]}-{et.strip()}")
            esiti[titolo][et.strip()] = v
            print(f"     {et}  {'None' if v is None else f'{v:>6.1f}'}   "
                  f"{claim[:58]}")

    # ── CONTROLLI, uno per blocco che ne ha bisogno ──────────────────────
    print("\n  [1] CONTROLLI (vero alto E assente basso, per blocco):")
    ok = True
    for titolo in [b[0] for b in blocchi[:3]]:
        v, a = esiti[titolo].get("vero"), esiti[titolo].get("assente")
        if v is None or a is None:
            print(f"      {titolo}: giudice non ha girato ⇒ NESSUN VERDETTO")
            return 1
        buono = v > 50 and a < 50
        ok = ok and buono
        print(f"      {titolo:<24} vero={v:5.1f}  assente={a:5.1f}  "
              f"{'ok' if buono else 'CADUTO'}")
    if not ok:
        print("      CONTROLLO CADUTO in almeno un blocco ⇒ un punteggio alto")
        print("      sullo scambio non distingue la cecita' dalla compiacenza.")
        print("      NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO, predizione per predizione ══")
    for n, titolo in ((1, "① INGLESE"), (2, "② FONTE LUNGA (>1500)")):
        sc = esiti[titolo]["SCAMBIO"]
        regge = sc > 50
        print(f"     {n}) {titolo:<22} scambio={sc:5.1f}  -> "
              f"{'la cecita REGGE' if regge else 'CECITA ASSENTE: predizione FALSIFICATA'}")

    t = esiti["③ ALTRE FALSITA' (it)"]
    neg, ordg, uni = t["NEGAZIONE"], t["ORD.GRAND"], t["UNITA"]
    print(f"     3) negazione={neg:5.1f}   ordine di grandezza={ordg:5.1f}   "
          f"unita' sbagliata={uni:5.1f}")
    print("        atteso: ordine di grandezza BASSO (il valore non c'e'),")
    print("        negazione ALTA (i valori ci sono tutti, cambia il segno).")
    if ordg < 50 and neg > 50:
        print("        -> PREDIZIONE RETTA: la cecita' e' SELETTIVA — il giudice")
        print("           vede i valori assenti e non vede la LOGICA.")
    else:
        print("        -> PREDIZIONE FALSIFICATA su questo punto: il profilo")
        print("           non e' quello atteso, e va riletto caso per caso.")

    print("\n  ⚠️ LIMITI: una fonte per lingua, tre claim per blocco, un solo")
    print("     giudice (cross-encoder locale). NON e' un numero sul prodotto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
