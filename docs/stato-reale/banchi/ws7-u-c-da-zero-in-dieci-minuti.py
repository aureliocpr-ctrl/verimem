"""U-C — «da zero in dieci minuti», con l'ambiente RIPULITO invece che sperato pulito.

    python ws7-u-c-da-zero-in-dieci-minuti.py

⏱️ **FINESTRA DICHIARATA: 900 s** (atteso ~7 min: 6,8 misurati da Tara). ≥ 2x.

━━ PERCHE' ESISTE, e perche' la prima riga e' `os.environ.pop` ━━━━━━━━━━━━━━━
Il numero di U-C in `PERCORSI-UTENTE.md` e' dichiarato **«DA RIFARE»**: i 6,8
minuti giravano con `ENGRAM_DATA_DIR` **ereditata**, la stessa variabile che ha
fatto ritirare il ticket 8.

🔴 **E controllando PRIMA di misurare — che e' l'unica ragione per cui questo
banco ha senso — l'ambiente non aveva UNA variabile sporca: ne aveva NOVE.**

    HIPPO_DATA_DIR=C:\\Users\\aurel\\.engram      <- lo store di Aurelio
    ENGRAM_DATA_DIR=C:\\Users\\aurel\\.engram     <- idem
    HIPPO_ENCODE_DELEGATE_ONLY=1                  <- la variabile di T1
    ENGRAM_ADMISSION_GATE=1 · ENGRAM_DECAY_ENABLED=1
    ENGRAM_BRIEFING_MIN_MATCHED=4 · ENGRAM_BRIEFING_THRESHOLD=0.40
    ENGRAM_TELEMETRY_PREFIXES=builtin · HIPPO_EXPOSE_TOOLS=...

⇒ **Un utente che installa oggi non ha NESSUNA di queste.** Misurare «da zero»
in questo ambiente misura noi, non lui. Qui si toglie **tutto** il prefisso, non
solo quella che ci ha gia' morso: **la trappola nota si evita, la trappola nuova
si evita solo togliendo la classe.**

━━ IL CRITERIO, gia' scritto in PERCORSI-UTENTE e non riscritto qui ━━━━━━━━━━
«In dieci minuti l'utente ha visto con i suoi occhi il prodotto rifiutare una
falsita', e sa dire a voce cosa fa e a chi serve — senza aver aperto le altre
780 righe del README.»
Il banco misura la prima meta' (il tempo e l'assert). **La seconda meta' — "sa
dire a voce cosa fa" — nessun banco la misura**, e resta il buco dichiarato.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# ── LA PRIMA COSA CHE FA QUESTO BANCO: ripulire, e DIRE cosa ha tolto ────────
SPORCHE = {k: v for k, v in os.environ.items()
           if any(s in k.upper() for s in ("HIPPO", "ENGRAM", "VERIMEM"))}
AMBIENTE = {k: v for k, v in os.environ.items() if k not in SPORCHE}

PASSI: list[dict] = []


def passo(nome: str, cmd: list[str], cwd: Path, atteso: str) -> dict:
    t0 = time.time()
    p = subprocess.run(cmd, cwd=str(cwd), env=AMBIENTE, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=900)
    dt = time.time() - t0
    d = {"passo": nome, "secondi": round(dt, 1), "exit": p.returncode,
         "atteso": atteso,
         "coda": (p.stdout or p.stderr).strip().splitlines()[-2:][:2],
         # ⚠️ l USCITA INTERA, non due righe: su `doctor` mi sono mancate
         # proprio le righe che dicevano QUALE check dava il warning.
         "uscita_intera": (p.stdout or "") + (p.stderr or "")}
    PASSI.append(d)
    print(f"  {nome:38s} {dt:7.1f}s  exit={p.returncode}   ({atteso})")
    for r in d["coda"]:
        print(f"       {r[:110]}")
    return d


def main() -> None:
    print(f"  finestra dichiarata: 900 s · atteso ~7 min (6,8 misurati da Tara)")
    print(f"  variabili TOLTE dall'ambiente: {len(SPORCHE)}")
    for k in sorted(SPORCHE):
        print(f"      - {k}={str(SPORCHE[k])[:60]}")
    if not SPORCHE:
        print("      (nessuna: l'ambiente era gia' pulito)")

    base = Path(tempfile.mkdtemp(prefix="iris-uc-"))
    venv = base / "venv"
    store = base / "store"
    AMBIENTE["HIPPO_DATA_DIR"] = str(store)     # store SUO, non quello di Aurelio
    AMBIENTE["ENGRAM_DATA_DIR"] = str(store)
    print(f"  cartella di lavoro: {base}")
    print()

    t_inizio = time.time()
    passo("0 · creo il venv", [sys.executable, "-m", "venv", str(venv)], base,
          "pochi secondi")
    py = venv / "Scripts" / "python.exe"
    if not py.exists():
        py = venv / "bin" / "python"
    exe = py.parent / ("verimem.exe" if os.name == "nt" else "verimem")

    passo("1 · pip install verimem (da PyPI)",
          [str(py), "-m", "pip", "install", "--quiet", "verimem"], base,
          "~5 min, ~1.0 GB su disco")
    passo("2 · verimem warmup", [str(exe), "warmup"], base,
          "746 MB: il giudice. Senza, il cancello e' SPENTO")
    passo("3 · verimem doctor", [str(exe), "doctor"], base,
          "0 su installazione nuova (ticket 8 ritirato)")

    # ── il Quickstart del README: scrive una falsita' e l'assert non la trova ──
    quick = base / "quickstart.py"
    # ⚠️ L'ASSERT GUARDA LO STATUS, NON L'ASSENZA DELLA STRINGA. Alla prima
    # esecuzione controllavo solo che il testo non tornasse: **passava anche con
    # ZERO risultati per qualunque ragione** (store vuoto, indice assente, errore
    # muto). «Risultati serviti: 0» non prova che il gate abbia fermato qualcosa.
    # La verifica mirata poi lo ha confermato — `status=quarantined`,
    # `quarantined_by=moat`, `grounding=0.69` — cioe' **il prodotto fa la cosa
    # giusta e il mio assert non la misurava**.
    quick.write_text('''from verimem import Memory
m = Memory("memoria.db")
r = m.add("Il servizio di pagamento ha superato il collaudo.",
          source="Verbale del 3 settembre: il collaudo del servizio di pagamento "
                 "e stato rinviato a data da destinarsi.")
assert r.get("status") == "quarantined", f"IL GATE NON HA FERMATO: {r.get('status')}"
trovati = m.search("collaudo del servizio di pagamento", k=5)
testi = " ".join(str(x.get("text", "")) for x in trovati)
assert "ha superato il collaudo" not in testi, "LA FALSITA E TORNATA"
print("OK: fermata dal", r.get("quarantined_by"), "grounding",
      round(r.get("grounding_score") or 0, 2), "serviti", len(trovati))
''', encoding="utf-8")
    passo("4 · il Quickstart, con il suo assert", [str(py), str(quick)], base,
          "la falsita' non torna: l'utente VEDE la promessa")

    # ── il passo 5, che ho aggiunto io: una scrittura SUA ──────────────────────
    mio = base / "mio.py"
    mio.write_text(
        'from verimem import Memory\n'
        'm = Memory("memoria.db")\n'
        'r = m.add("Il fornitore di pagamenti del checkout e Stripe.",\n'
        '          source="Verbale del 3 settembre: il servizio checkout usa '
        'Stripe come fornitore di pagamenti dal 2024.")\n'
        'print("status:", r.get("status"), "grounding:", r.get("grounding_score"))\n'
        'print("richiamo:", [str(x.get("text",""))[:50] for x in '
        'm.search("fornitore di pagamenti", k=3)])\n',
        encoding="utf-8")
    passo("5 · una scrittura SUA, e il richiamo", [str(py), str(mio)], base,
          "ha capito cosa ci farebbe (passo che ho aggiunto io)")

    totale = time.time() - t_inizio
    print()
    print(f"  ⇒ TOTALE: {totale/60:.1f} minuti ({totale:.0f} s)")
    print(f"  ⇒ dentro i dieci minuti? {'SI' if totale < 600 else 'NO'}")
    print("  ⚠️ la SECONDA META' del criterio — «sa dire a voce cosa fa» —")
    print("     nessun banco la misura, e resta il buco dichiarato.")

    fuori = Path(__file__).with_suffix(".json")
    fuori.write_text(json.dumps(
        {"finestra_s": 900, "variabili_tolte": sorted(SPORCHE),
         "totale_s": round(totale, 1), "dentro_i_dieci_minuti": totale < 600,
         "passi": PASSI}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  scritto {fuori}")
    # ⚠️ NON cancello piu: alla prima esecuzione ho rimosso la cartella e
    # non ho potuto ispezionare il `doctor` uscito 1. Si ripulisce DOPO
    # aver letto il json.
    print(f"  ⚠️ cartella LASCIATA per l ispezione: {base}")


if __name__ == "__main__":
    main()
