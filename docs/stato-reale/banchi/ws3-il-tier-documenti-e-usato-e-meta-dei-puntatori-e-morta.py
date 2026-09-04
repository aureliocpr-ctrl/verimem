"""LIVELLO: lo store vivo, in sola lettura — non il gate.

Il tier Documents esiste, e' usato, e meta' dei suoi puntatori non si riapre.

    python docs/stato-reale/banchi/ws3-il-tier-documenti-e-usato-e-meta-dei-puntatori-e-morta.py

⚡ COSTO ZERO: nessun modello, nessuna scrittura. Apre lo store con `mode=ro`,
quindi non crea nemmeno il journal.

━━ PERCHE' ESISTE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
In memoria condivisa c'e' scritto: «documents.db non esiste: la via che
raccomandiamo per i fatti lunghi funziona e non l'ha mai usata nessuno». Se
fosse vero sarebbe un argomento per togliere il tier. E' **falso su entrambe le
meta'**, e l'errore e' la trappola gia' documentata: *il file alla radice non e'
quello vero*. `documents.db` sta in `.engram/documents/`, non alla radice — la
stessa cosa che il 03/09 mi ha fatto trovare un `semantic.db` da 73 KB accanto a
quello vero da 131 MB.

━━ MISURATO IL 2026-09-04 alle 19:45, sullo store vivo ━━━━━━━━━━━━━━━━━━━━━━
    documents.db          5.378.048 byte   73 righe (tutte le versioni)
    document_index.db     3.485.696 byte  683 chunk
    documenti DISTINTI                     59

    il file di origine esiste ancora     30-31 / 59   (~51%)
    puntatori MORTI                      28-29

    da dove vengono: 31 altro · 23 scratchpad di sessione · 5 temp di sistema

    righe con file PRESENTE  31 · contenuto vuoto in 0 · mediana 8.417 caratteri
    righe con file SPARITO   41-42 · contenuto vuoto in 0 · mediana 4.909 caratteri

⚠️ IL CONTEGGIO DEI VIVI SI MUOVE, e va dichiarato invece che arrotondato: due
esecuzioni a due minuti di distanza danno 30 e 31. Non e' rumore di misura, e'
che la grandezza dipende dal FILESYSTEM ALL'ISTANTE — e ventitre di quei
percorsi sono scratchpad di sessioni che in questo momento stanno lavorando,
compresa la mia. Chi rilancia questo banco otterra' un numero vicino, non lo
stesso: la percentuale (~51%) e' il dato, il conteggio esatto no.

━━ IL VERDETTO, e ho cercato il difetto prima di non trovarlo ━━━━━━━━━━━━━━━
⇒ **LIMITE, NON BUCO.** Per OGNI documento il cui file e' sparito il contenuto
e' ancora nel DB: zero righe vuote su 73. Il tier e' dichiarato come «raw
versioned-by-hash snapshots» e fa esattamente quello. Cio' che si perde e' la
possibilita' di RIAPRIRE l'originale, non il testo.

⚠️ Resta una cosa vera e scomoda: **il 49% dei documenti e' indicizzato con un
percorso in una cartella temporanea o in uno scratchpad di sessione**, cioe' per
costruzione effimero. Chi cita un documento di questo tier puo' mostrare il
testo ma non far riaprire la fonte. Non e' una promessa tradita — il prodotto
non promette di riaprirla — ma chi progetta una citazione verificabile deve
saperlo prima, non dopo.

⇒ E L'ARGOMENTO PER TOGLIERE IL TIER CADE: e' usato (59 documenti, 683 chunk),
e la ragione per cui sembrava morto era che si guardava il percorso sbagliato.

🔴 COME MUORE QUESTO BANCO: se un domani `documents` avesse righe con contenuto
VUOTO e file sparito, allora quelle righe promettono un testo che non possono
mostrare, e il verdetto passa da «limite» a «buco».
"""
from __future__ import annotations

import sqlite3
from collections import Counter
from pathlib import Path

BASE = Path(r"C:\Users\aurel\.engram\documents")


def conta_tabelle(db: Path) -> None:
    print(f"\n── {db.name}  ({db.stat().st_size:,} byte)".replace(",", "."))
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        for (t,) in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]  # noqa: S608
            print(f"   {t:24s} {n:>6d} righe")
    finally:
        con.close()


def main() -> None:
    print("IL TIER DOCUMENTS: esiste? e' usato? i suoi puntatori si riaprono?")
    for nome in ("documents.db", "document_index.db"):
        p = BASE / nome
        if p.exists():
            conta_tabelle(p)
        else:
            print(f"\n── {nome}: NON esiste  🔴 (la memoria avrebbe ragione)")
            return

    con = sqlite3.connect(f"file:{BASE / 'documents.db'}?mode=ro", uri=True)
    try:
        righe = con.execute(
            "SELECT source_id, LENGTH(COALESCE(content,'')) FROM documents").fetchall()
    finally:
        con.close()

    distinti = sorted({s for s, _ in righe if s})
    vivi = [s for s in distinti if Path(s).exists()]
    print(f"\ndocumenti distinti        : {len(distinti)}")
    print(f"il cui file esiste ancora : {len(vivi)}  "
          f"({100.0 * len(vivi) / max(1, len(distinti)):.1f}%)")
    print(f"puntatori MORTI           : {len(distinti) - len(vivi)}")

    fam = Counter()
    for s in distinti:
        b = s.lower()
        if "\\temp\\claude\\" in b or "/temp/claude/" in b:
            fam["scratchpad di sessione"] += 1
        elif "\\temp\\" in b or "/temp/" in b:
            fam["temp di sistema"] += 1
        else:
            fam["altro"] += 1
    print("\nda dove vengono:")
    for k, v in fam.most_common():
        print(f"   {k:26s} {v:>4d}")

    #: LA DOMANDA CHE SEPARA IL LIMITE DAL BUCO: il testo sopravvive al file?
    morti = [(s, n) for s, n in righe if s and not Path(s).exists()]
    vuoti = sum(1 for _, n in morti if n == 0)
    print(f"\nrighe con file sparito    : {len(morti)}  ·  di cui a contenuto "
          f"VUOTO: {vuoti}")
    if morti and vuoti == 0:
        print("\n⇒ LIMITE, non buco: il contenuto sopravvive sempre. Si perde la")
        print("  possibilita' di riaprire l'originale, non il testo.")
    elif vuoti:
        print(f"\n🔴 BUCO: {vuoti} righe promettono un testo che non possono mostrare.")


if __name__ == "__main__":
    main()
