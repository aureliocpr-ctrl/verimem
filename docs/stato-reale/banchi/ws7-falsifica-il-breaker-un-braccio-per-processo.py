"""Il divario IT/EN di @ws1 sopravvive se il breaker non puo' scattare fra i bracci?

COSA VERIFICO. @ws1 il 02/09 alle 19:13 ha trovato che lo stesso banco, invertendo
l'ordine dei bracci, da' numeri diversissimi:

  ordine IT -> EN     ITALIANO 20,0%   INGLESE 40,0%   divario 20,0 punti
  ordine EN -> IT     ITALIANO 60,0%   INGLESE 67,5%   divario  7,5 punti

e il prodotto stampa la causa da solo:
  «rerank breaker TRIPPED — 5 of the last 7 reranks overran their budget
   — CE rerank disabled for this process»
⇒ il breaker scatta A META' BANCO: il primo braccio gira COL rerank, il secondo
SENZA. La variabile «lingua» era confusa con lo stato del rerank.

PERCHE' NON RIPETO I DUE ORDINI. Rifare i suoi due ordini sarebbe la sua stessa
misura: duplicare non e' verificare. E soprattutto NESSUNO DEI SUOI DUE BRACCI E'
PULITO — in ogni esecuzione uno gira col rerank e l'altro senza.

IL CAMPO DIVERSO: ELIMINARE IL CONFONDENTE INVECE DI OSSERVARLO.
Il messaggio del prodotto dice «disabled for THIS PROCESS». ⇒ Un braccio per
processo: il breaker di uno non puo' toccare l'altro, e ogni braccio vede lo
stesso stato del rerank dall'inizio alla fine.

🔑 E NON RISCRIVO LA SUA MISURA: importo `campiona` e `misura` dal suo script e
le chiamo intatte. Cambio l'ORCHESTRAZIONE, non il metodo.

  python ws7-falsifica-il-breaker-un-braccio-per-processo.py it
  python ws7-falsifica-il-breaker-un-braccio-per-processo.py en
  (due processi separati, MAI insieme: un giudice per volta)

═══ PREDIZIONE, depositata prima ═══
P1 con un solo braccio il breaker NON scatta: sono meta' delle query, e il suo
   messaggio dice 5 sforamenti sugli ultimi 7.
P2 i due valori isolati NON coincideranno con nessuno dei suoi quattro, perche'
   nessuno dei suoi bracci era pulito.
🔑 P3, LA PIU' IMPORTANTE: il divario IT/EN misurato in isolamento sara' PIU'
   PICCOLO di 20,0 punti. Se fosse >= 15 il divario di lingua esisterebbe
   davvero; se <= 5, la lingua non e' la variabile del recall e cade la premessa
   di T2.1 — che e' la conclusione a cui @ws1 stava arrivando per altra via.
COME MUORE P1: se il breaker scatta anche con un braccio solo, l'isolamento non
basta e il verdetto e' «non riproducibile» con questo disegno.

⚠️ Sola lettura sullo store vivo. Un processo per volta per il vincolo di RAM.
"""
import io
import sys
from contextlib import redirect_stderr
from pathlib import Path

RADICE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RADICE / "scripts"))


def main() -> int:
    quale = (sys.argv[1] if len(sys.argv) > 1 else "").lower()
    if quale not in ("it", "en"):
        print("  uso: <banco> it   oppure   <banco> en   (un braccio per processo)")
        return 2

    from banco_lingua_store_vivo import campiona, misura  # il SUO codice, intatto
    from verimem.config import CONFIG
    from verimem import Memory

    it, en = campiona()
    fatti, nome = (it, "ITALIANO") if quale == "it" else (en, "INGLESE")
    print(f"  braccio SOLO {nome} — {len(fatti)} fatti, processo dedicato")

    mem = Memory(CONFIG.semantic_db)
    err = io.StringIO()
    with redirect_stderr(err):
        buoni, tot = misura(mem, fatti, nome)
    rumore = err.getvalue()

    pct = buoni / (tot or 1) * 100
    print(f"\n  {nome}: {buoni}/{tot} = {pct:.1f}%")

    # CONTROLLO che decide se la misura e' pulita: il breaker e' scattato?
    scattato = "breaker" in rumore.lower() or "TRIPPED" in rumore
    print(f"  breaker del rerank: {'🔴 SCATTATO' if scattato else '✅ non scattato'}")
    if scattato:
        for r in rumore.splitlines():
            if "breaker" in r.lower() or "TRIPPED" in r:
                print(f"     {r.strip()[:96]}")
        print("  ⇒ l'isolamento per processo NON basta: verdetto «non")
        print("     riproducibile» con questo disegno, e lo dico io per primo.")
    print(f"\n  📌 confronto con @ws1: nel suo ordine IT->EN {nome} valeva "
          f"{'20,0%' if quale == 'it' else '40,0%'}, "
          f"nell'ordine EN->IT {'60,0%' if quale == 'it' else '67,5%'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
