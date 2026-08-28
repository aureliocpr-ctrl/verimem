"""Il giudice regge su una TABELLA come sulla prosa? Stessa informazione, due forme.

**Metà del corpus e' tabellare** — misurato stanotte: 51,9% degli span ha piu'
del 40% di righe a colonne, e la prosa con numerazione di sezione e' lo 0,07%
(`13e98fcb`). ⇒ La forma su cui il giudice lavora **davvero** non e' la prosa,
e **nessuno l'ha mai misurato lungo questa dimensione**.

L'IPOTESI, e viene da come una tabella lega i suoi dati: in prosa il legame fra
**soggetto** e **valore** e' **sintattico** («*security ha avuto 60 run, di cui
**59** cancellati*»); in una tabella e' **posizionale** — il `59` sta in una
cella, `security` in un'altra, e a tenerli insieme c'e' solo l'allineamento.
Un giudice che pesa la co-occorrenza di token, non la struttura, dovrebbe
**perdere il legame** proprio dove la forma lo rende implicito.

LA PREDIZIONE, scritta prima di eseguire:
    **i claim FALSI per SCAMBIO DI SOGGETTO prendono piu' punti sulla TABELLA
    che sulla PROSA** — perche' sulla tabella «ci» e «59» sono entrambi
    presenti e nulla dice che non vadano insieme.
    Il claim VERO resta alto su entrambe.

CONDIZIONE DI FALSIFICAZIONE: se la maggioranza dei cinque scambi NON prende
piu' punti sulla tabella, l'ipotesi cade — la forma tabellare **non** slega
soggetto e valore, e il 51,9% di tabellarita' non e' di per se' il problema.

⚠️ **ESITO: PREDIZIONE FALSIFICATA, 2 scambi su 5.** La direzione e'
**incoerente** (`security 50 run` −17,8 verso la prosa, `ci e' rosso` +25,5
verso la tabella) ⇒ **ipotesi ritirata**.

🔴 **E IL DATO CHE NON CERCAVO, piu' grosso dell'ipotesi.** Guardando le RIGHE
invece del delta — cioe' leggendo la tabella dei risultati invece di confrontare
due colonne:

    claim                    TABELLA   PROSA
    vero  security 59 canc      98.4   100.0
    sw    ci 59 cancellati      98.5   100.0
    sw    presidi 59 cancell.   98.8    97.8
    sw    security 50 run       82.1    99.9
    sw    ci e' rosso           95.8    70.3
    sw    security e' verde     98.1    99.7
    ASSENTE 777                  0.6     0.5

**Il minimo fra dieci celle di falsita' per scambio e' 70,3; un valore ASSENTE
prende 0,5.** ⇒ **Il giudice discrimina la PRESENZA dei valori e non la loro
ATTRIBUZIONE**: gli stessi numeri predicati del soggetto sbagliato restano
quasi indistinguibili dal vero, e uno di essi prende **100,0 esatto**.

⇒ **E' la STESSA cecita' gia' misurata su `L4.1` (0/12 sugli scambi): due
difese indipendenti, un solo punto cieco.** Nessuna delle due chiede *di CHI*
sia il valore. 📌 Ed e' esattamente cio' che `L4.3` (`e283ae70`, 21 test verdi)
fu costruito per prendere — e che resta **non collegato**, perche' sulle fonti
tabellari fa rumore (27 falsi positivi su 28). **Il bisogno ora e' misurato; la
cura esiste e non e' utilizzabile su QUESTO corpus.**

DUE CONTROLLI CHE DEVONO POTER FALLIRE:
  (a) il claim **VERO** deve restare alto su ENTRAMBE le forme. Se crollasse
      anche lui sulla tabella, misurerei «la tabella rompe tutto», non «la
      tabella slega il soggetto dal valore».
  (b) un claim con un numero **ASSENTE** (777) deve restare basso su entrambe:
      e' la popolazione di controllo che dice che il giudice non sta dicendo di
      si' a chiunque.

⚠️ SI GUARDA IL `grounding_score`, NON l'esito: l'esito lo decide anche `L1`, e
mescolare le due cose e' l'errore che ho gia' pagato stanotte su W2-27.

⚠️ I DATI SONO VERI: sono le mie misure del CI di stanotte (`security` 59
cancellati su 60, `ci` 0 su 50, `presidi-lenti` 1 su 14). Usare numeri veri
evita di costruire una tabella che somigli alla mia ipotesi.

REGIME: store TEMPORANEO, giudice locale (cross-encoder su disco, nessuna API
esterna). Lo store di Aurelio NON e' toccato.

    python docs/stato-reale/banchi/ws3-il-giudice-su-una-tabella-contro-la-stessa-cosa-in-prosa.py
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

TABELLA = (
    "workflow          run   cancellati   esito\n"
    "ci                 50            0   verde\n"
    "security           60           59   rosso\n"
    "presidi-lenti      14            1   verde"
)

PROSA = (
    "Il workflow ci ha avuto 50 run, di cui 0 cancellati, e il suo esito e' "
    "verde. Il workflow security ha avuto 60 run, di cui 59 cancellati, e il "
    "suo esito e' rosso. Il workflow presidi-lenti ha avuto 14 run, di cui 1 "
    "cancellato, e il suo esito e' verde."
)

VERO = "Il workflow security ha 59 run cancellati."
FALSO = "Il workflow ci ha 59 run cancellati."          # scambio di soggetto
ASSENTE = "Il workflow ci ha 777 run cancellati."       # numero non nella fonte

#: CINQUE scambi, non uno: una cella sola non distingue un difetto da un caso.
#: Tutti prendono un valore che nella fonte C'E' e lo predicano del soggetto
#: SBAGLIATO — che e' la falsita' piu' facile da produrre e la piu' difficile
#: da vedere contando i valori.
SCAMBI = [
    ("ci 59 cancellati    ", FALSO),
    ("presidi 59 cancell. ", "Il workflow presidi-lenti ha 59 run cancellati."),
    ("security 50 run     ", "Il workflow security ha avuto 50 run."),
    ("ci e' rosso         ", "Il workflow ci ha esito rosso."),
    ("security e' verde   ", "Il workflow security ha esito verde."),
]


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    os.environ["HIPPO_DATA_DIR"] = str(tmp)
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  REGIME: HIPPO_DATA_DIR={tmp}  (store di Aurelio NON toccato)")
    print(f"  la tabella e' {len(TABELLA)} char, la prosa {len(PROSA)} char")
    print("  ⚠️ entrambe SOTTO il budget del giudice (1500): nessuna selezione")
    print("     di span entra in gioco — misuro la FORMA, non il ritaglio.")

    mem = Memory(str(tmp / "forme.db"))

    def punteggio(claim: str, fonte: str, tag: str) -> float | None:
        r = mem.add(claim, topic=f"forme/{tag}", source=fonte, validate="full")
        return r.get("grounding_score")

    forme = [("TABELLA", TABELLA), ("PROSA  ", PROSA)]
    claim_set = ([("vero   ", VERO)]
                 + [("sw " + e, c) for e, c in SCAMBI]
                 + [("assente", ASSENTE)])

    print(f"\n  {'claim':<9} {'TABELLA':>10} {'PROSA':>10}   delta (tab-prosa)")
    print("  " + "-" * 52)
    p: dict[tuple[str, str], float | None] = {}
    for et, claim in claim_set:
        for fn, fonte in forme:
            p[(et.strip(), fn.strip())] = punteggio(
                claim, fonte, f"{et.strip()}-{fn.strip()}")
        a, b = p[(et.strip(), "TABELLA")], p[(et.strip(), "PROSA")]
        d = "n/d" if a is None or b is None else f"{a - b:+.1f}"
        sa = "None" if a is None else f"{a:.1f}"
        sb = "None" if b is None else f"{b:.1f}"
        print(f"  {et:<9} {sa:>10} {sb:>10}   {d}")

    # ── CONTROLLI ────────────────────────────────────────────────────────
    vt, vp = p[("vero", "TABELLA")], p[("vero", "PROSA")]
    at, ap = p[("assente", "TABELLA")], p[("assente", "PROSA")]
    chiavi_sw = [("sw " + e).strip() for e, _c in SCAMBI]
    ft = p[(chiavi_sw[0], "TABELLA")]
    fp = p[(chiavi_sw[0], "PROSA")]
    if any(x is None for x in (vt, vp, at, ap, ft, fp)):
        print("\n  CONTROLLO CADUTO: un grounding e' None ⇒ il giudice non ha")
        print("  girato (modello locale assente?). NESSUN VERDETTO.")
        return 1

    print(f"\n  [a] il claim VERO regge su entrambe? "
          f"tabella={vt:.1f} prosa={vp:.1f}")
    if vt < 50:
        print("      CONTROLLO CADUTO: il claim VERO crolla gia' sulla tabella")
        print("      ⇒ misurerei «la tabella rompe tutto», non «la tabella")
        print("      slega il soggetto dal valore». NESSUN VERDETTO.")
        return 1
    print(f"  [b] il numero ASSENTE resta basso su entrambe? "
          f"tabella={at:.1f} prosa={ap:.1f}")
    if at > 50 and ap > 50:
        print("      CONTROLLO CADUTO: il giudice promuove anche un numero che")
        print("      NON C'E' ⇒ dice di si' a chiunque e il confronto fra forme")
        print("      non significa niente. NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    peggio_tab = sum(1 for k in chiavi_sw
                     if p[(k, "TABELLA")] > p[(k, "PROSA")])
    print(f"     scambi in cui la TABELLA da' piu' punti della prosa: "
          f"{peggio_tab}/{len(chiavi_sw)}")
    if peggio_tab > len(chiavi_sw) / 2:
        print("     PREDIZIONE RETTA: la forma tabellare slega soggetto e valore.")
    else:
        print("     PREDIZIONE FALSIFICATA: la direzione NON e' coerente ⇒ la")
        print("     tabellarita' NON e' di per se' il problema. Ipotesi ritirata.")

    # ── E IL DATO CHE NON CERCAVO, piu' grosso dell'ipotesi ──────────────
    minimo = min(min(p[(k, "TABELLA")], p[(k, "PROSA")]) for k in chiavi_sw)
    print("\n     🔴 MA GUARDANDO LE RIGHE invece del delta: il punteggio piu'")
    print(f"     BASSO fra {2 * len(chiavi_sw)} celle di falsita' per scambio e' "
          f"{minimo:.1f},")
    print(f"     mentre un valore ASSENTE prende {min(at, ap):.1f}.")
    print("     ⇒ Il giudice discrimina la PRESENZA dei valori e NON la loro")
    print("       ATTRIBUZIONE: gli stessi numeri predicati del soggetto")
    print("       SBAGLIATO restano quasi indistinguibili dal vero.")
    print("     ⇒ E' la STESSA cecita' gia' misurata su `L4.1` (0/12 sugli")
    print("       scambi): due difese indipendenti, un solo punto cieco.")

    print("\n  ⚠️ LIMITI: UNA tabella e UNA prosa, sette claim, italiano, un solo")
    print("     tipo di falsita' (scambio di soggetto). Il giudice e' il")
    print("     cross-encoder locale: un altro modello puo' comportarsi")
    print("     diversamente, e questo NON e' un numero sul prodotto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
