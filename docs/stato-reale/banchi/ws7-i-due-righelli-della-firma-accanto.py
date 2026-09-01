"""I due righelli della firma, uno accanto all'altro, sulle stesse celle.

PERCHE'. Il 01/09 alle 20:07 @ws2 ha trovato che il SUO criterio non vedeva le
firme decorate con due emoji (`✅⚠️ **firma @…`): 5 celle risultavano non
firmate. Ha curato il suo. ⇒ **Cerco su di me la forma che ha appena trovato**
— e il mio criterio (`scripts/celle_load_bearing.py:53`) e' DIVERSO dal suo:
io cerco le PAROLE, lui il MARCATORE.

    mio   (?:2ª |seconda )?firma @|controfirm            (re.I, niente marcatore)
    ws2   (?:✅|✍️|_)[^A-Za-z0-9|]{0,6}(?:\\*\\*)?(?:2ª |seconda )?firma @(\\w+)

Il mio script DICHIARA tre classi di falsi POSITIVI (menzione, alias,
autofirma) e **non ha mai misurato i falsi NEGATIVI**: e' la lezione «misura
ENTRAMBE le popolazioni», che sui soli negativi fa sembrare ottimo ogni
criterio.

COSA MISURA. Le quattro caselle (solo-mio / solo-ws2 / entrambi / nessuno) e —
la casella che conta — **le celle che NESSUNO dei due vede ma che contengono un
segno di passaggio di un'altra istanza** (`@wsN` accanto a un marcatore di
esito). Quelle sono i CANDIDATI a falso negativo: il verdetto lo do' leggendo,
non contando (il 01/09 un mio classificatore automatico ha dato tre esiti
diversi in dieci minuti).

CONTROLLO POSITIVO. Due stringhe costruite, che DEVONO accendersi: se non si
accendono il banco e' rotto e il silenzio e' mio, non del registro. ⚠️ Il
controllo NON usa la stessa funzione del criterio — il 01/09 un mio controllo
positivo condivideva il difetto del criterio e non vedeva niente.
"""
import re
import sys
from pathlib import Path

ESAME = Path("docs/stato-reale/00-ESAME.md")
COLONNE = re.compile(r"(?<!\\)\|")

MIO = re.compile(r"(?:2ª |seconda )?firma @|controfirm", re.I)
WS2 = re.compile(r"(?:✅|✍️|_)[^A-Za-z0-9|]{0,6}(?:\*\*)?"
                 r"(?:2ª |seconda )?firma @([A-Za-z0-9_-]+)")

#: un segno che QUALCUN ALTRO e' passato: la sigla di un'istanza vicino a un
#: marcatore di esito. Volutamente LARGO: serve a produrre candidati da
#: leggere, non a dare un verdetto.
PASSAGGIO = re.compile(r"@(?:ws\d|lead-audit)\b")
ESITO = re.compile(r"(?:✅|🔴|🟢|conferm|ritir|verific|riprodott|rifatt)", re.I)


def _celle(testo: str) -> dict[str, str]:
    out = {}
    for riga in testo.splitlines():
        if not riga.startswith("| ") or not riga.rstrip().endswith("|"):
            continue
        col = COLONNE.split(riga)
        if len(col) < 10:
            continue
        m = re.match(r"\s*((?:LANT|W\d)-\d+[a-z]?)\s*$", col[1])
        if m:
            out[m.group(1)] = riga
    return out


def main() -> int:
    #: --- controllo positivo, PRIMA di tutto e senza passare dal criterio ---
    canoniche = [
        "✅ **firma @ws2 03:12** — rifatta, stessi numeri.",
        "✅🪞 **firma @ws6 19:40** — decorata con due emoji.",
    ]
    acceso_mio = [bool(MIO.search(s)) for s in canoniche]
    acceso_ws2 = [bool(WS2.search(s)) for s in canoniche]
    print("  CONTROLLO POSITIVO (deve accendersi, altrimenti il banco e' rotto)")
    for s, a, b in zip(canoniche, acceso_mio, acceso_ws2):
        print(f"     mio={'SI' if a else 'NO':<3} ws2={'SI' if b else 'NO':<3} · {s[:52]}")
    if not all(acceso_mio) or not all(acceso_ws2):
        print("  🔴 un righello non vede una firma canonica: NON leggo oltre.")
        return 1
    print("  ✅ entrambi accesi su entrambe.\n")

    if not ESAME.exists():
        print(f"  {ESAME} non trovato (esegui dalla radice del repo)")
        return 2
    celle = _celle(ESAME.read_text(encoding="utf-8"))

    solo_mio, solo_ws2, entrambi, nessuno = [], [], [], []
    for cid, riga in celle.items():
        verdetto = COLONNE.split(riga)[6]
        m, w = bool(MIO.search(verdetto)), bool(WS2.search(verdetto))
        (entrambi if m and w else solo_mio if m else solo_ws2 if w else nessuno).append(cid)

    tot = len(celle)
    print(f"  {tot} celle lette da {ESAME}\n")
    print(f"     entrambi i righelli   {len(entrambi):>4}")
    print(f"     SOLO il mio           {len(solo_mio):>4}   <- lui non le vede")
    print(f"     SOLO quello di ws2    {len(solo_ws2):>4}   <- IO non le vedo")
    print(f"     nessuno dei due       {len(nessuno):>4}")

    #: la casella che conta: fra le «nessuno», quali portano un segno di
    #: passaggio altrui? Sono CANDIDATI, e vanno letti.
    cand = [c for c in nessuno
            if PASSAGGIO.search(COLONNE.split(celle[c])[6])
            and ESITO.search(COLONNE.split(celle[c])[6])]
    print(f"\n  fra le «nessuno», con segno di passaggio altrui: {len(cand)}"
          f"  ({100*len(cand)/max(1,len(nessuno)):.1f}% delle «nessuno»)")
    print("  ⚠️ CANDIDATI, non falsi negativi: il verdetto si da' LEGGENDO.")
    if solo_ws2:
        print(f"\n  le SOLO-ws2 (il mio buco certo): {', '.join(solo_ws2[:12])}")
    for cid in cand[:6]:
        v = COLONNE.split(celle[cid])[6]
        print(f"\n     {cid}: …{v[-160:].strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
