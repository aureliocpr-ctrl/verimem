r"""`PYTHONUTF8=1` cambia i verdetti del gate, o solo l'aspetto dei log?

@ws7 (28/08 20:27) ha segnalato che `PYTHONUTF8` **tocca dieci celle verdi** del registro
e che **nessuno l'ha mai rimisurata**. Non e' una variabile del prodotto: e' di Python, e
governa l'encoding di default. Ma e' accesa nel nostro ambiente e spenta in CI, ed e' gia'
stata la causa di un rosso che il 20/08 non si riproduceva.

La domanda giusta non e' «e' accesa?» ma **«un utente senza quella variabile ottiene gli
stessi verdetti?»**.

RISULTATO (28/08 21:29) — LA VARIABILE TOCCA I VERDETTI, MA SOLO PASSANDO DAI FILE:

  REGIME A, `PYTHONUTF8=1` (stdout utf-8)        REGIME B, rimossa (stdout cp1252)
  ------------------------------------------     --------------------------------------
  memoria  accenti IT       99.244987            memoria  accenti IT       99.244987
  memoria  accenti misti    99.973267            memoria  accenti misti    99.973267
  memoria  simboli          99.942078            memoria  simboli          99.942078
  memoria  non-latino       99.880829            memoria  non-latino       99.880829
  memoria  ASCII (contr.)   98.503616            memoria  ASCII (contr.)   98.503616
  file     accenti IT       99.244987  fonte =   file     accenti IT       99.253014  DIVERSA
  file     accenti misti    99.973267  fonte =   file     accenti misti    99.831306  DIVERSA
  file     simboli          99.942078  fonte =   file     simboli          99.859505  DIVERSA
  file     non-latino       99.880829  fonte =   file     non-latino  **0.680241 QUARANTINED**
  file     ASCII (contr.)   98.503616  fonte =   file     ASCII (contr.)   98.503616  fonte =

=> STRINGHE IN MEMORIA: i due regimi coincidono **a sei decimali su cinque casi su cinque**.
=> FONTE LETTA DA FILE senza `encoding=`: nel regime B il testo riletto e' DIVERSO da quello
   scritto, e su `温度` il verdetto **si ribalta**: da `model_claim` 99.88 a **`quarantined`
   0.68**. Non e' una sfumatura di punteggio: e' l'esito opposto.
=> CONTROLLO POSITIVO SUPERATO NEI DUE VERSI: il caso ASCII puro da' `fonte =` e lo stesso
   punteggio in ENTRAMBI i regimi ⇒ il banco non fabbrica differenze dal nulla; e i due
   regimi sono davvero distinti (`stdout encoding` utf-8 contro cp1252).

=> IL CRITERIO OPERATIVO, che e' la parte utile: **una cella dipende da `PYTHONUTF8` se e
   solo se il suo banco LEGGE la fonte da un file senza dichiarare `encoding=`.** Chi passa
   le stringhe in memoria - come fa la maggior parte dei nostri banchi - e' salvo. La
   preoccupazione di @ws7 sui dieci verdi e' FONDATA e si restringe a quel criterio, che si
   verifica con un `grep` su `open(` / `read_text(` senza `encoding`.

DISEGNO, identico all'A/B gia' girato per `HIPPO_ENCODE_DELEGATE_ONLY`:
  stesso banco, due processi separati - `PYTHONUTF8=1` contro variabile RIMOSSA - e si
  confrontano **status e punteggio, cifra per cifra**.
  I casi portano accenti italiani e caratteri fuori ASCII nel claim E nella fonte, perche'
  e' li' che l'encoding puo' mordere.

CONTROLLO POSITIVO, dichiarato prima: un caso **puramente ASCII** deve dare **identico**
nei due regimi. Se cambia anche quello, il banco misura rumore e va buttato.

REGIME: store temporaneo isolato via `HIPPO_DATA_DIR` (⚠️ `ENGRAM_DATA_DIR` non isola),
FUORI da pytest, un processo per regime cosi' la seconda misura non eredita lo stato della
prima. Corpus di Aurelio mai toccato.

RIPRODUCI:  python docs/stato-reale/banchi/ws6-pythonutf8-tocca-i-verdetti.py
"""
from __future__ import annotations

import os
from pathlib import Path

CASI = [
    # (etichetta, claim, fonte che SOSTIENE)
    ("accenti IT", "La società è già accreditata presso l'ente.",
     "La società è già accreditata presso l'ente regionale."),
    ("accenti misti", "Il perché del ritardo è nell'unità di misura sbagliata.",
     "Il perché del ritardo è nell'unità di misura sbagliata, non nel calcolo."),
    ("simboli", "Il costo è 45 € più il 12% di IVA.",
     "Il costo è 45 € più il 12% di IVA, come da preventivo."),
    ("non-latino", "Il documento cita 温度 come parametro.",
     "Il documento cita 温度 come parametro di controllo."),
    ("ASCII puro (controllo)", "The warehouse holds 41 pallets.",
     "The warehouse holds 41 pallets on the north side."),
]


def _fonte_da_file(testo: str) -> str:
    """Rilegge la fonte DA DISCO senza dichiarare l'encoding.

    E' il punto dove `PYTHONUTF8` puo' davvero mordere: passare le stringhe in
    memoria non tocca l'encoding, LEGGERE UN FILE si'. `open()` senza `encoding=`
    usa `locale.getpreferredencoding()`, che la variabile cambia (utf-8 contro
    cp1252 su questa macchina). Un utente che passa una fonte letta da disco sta
    esattamente qui.
    """
    import tempfile
    p = Path(tempfile.mkdtemp()) / "fonte.txt"
    p.write_text(testo, encoding="utf-8")   # scritta SEMPRE in utf-8
    try:
        return p.read_text()                 # riletta con il default del regime
    except UnicodeDecodeError as e:
        return f"[NON LEGGIBILE IN QUESTO REGIME: {e.__class__.__name__}]"


def main() -> None:
    from verimem.client import Memory
    from verimem.config import CONFIG
    print(f"PYTHONUTF8 = {os.environ.get('PYTHONUTF8')!r}   "
          f"stdout encoding = {__import__('sys').stdout.encoding}")
    mem = Memory(str(Path(CONFIG.semantic_db)))
    for i in range(2):  # warm-up: i due caricamenti, buttati
        mem.add(f"Il registro W{i} elenca le misure.", topic="utf/warm",
                source=f"Il registro W{i} elenca le misure.")
    for i, (et, claim, fonte) in enumerate(CASI):
        r = mem.add(claim, topic=f"utf/{i}", source=fonte) or {}
        g = r.get("grounding_score")
        gs = f"{g:.6f}" if isinstance(g, (int, float)) else str(g)
        lay = [w.get("layer") for w in (r.get("warnings") or []) if isinstance(w, dict)]
        print(f"  memoria {et:<22} {str(r.get('status'))[:12]:<12} {gs:>14}  {lay}")

    print("  --- la stessa fonte, ma RILETTA DA FILE col default del regime ---")
    for i, (et, claim, fonte) in enumerate(CASI):
        letta = _fonte_da_file(fonte)
        uguale = "=" if letta == fonte else "DIVERSA"
        r = mem.add(claim, topic=f"utf/file-{i}", source=letta) or {}
        g = r.get("grounding_score")
        gs = f"{g:.6f}" if isinstance(g, (int, float)) else str(g)
        print(f"  file    {et:<22} {str(r.get('status'))[:12]:<12} {gs:>14}  "
              f"fonte {uguale}")


if __name__ == "__main__":
    main()
