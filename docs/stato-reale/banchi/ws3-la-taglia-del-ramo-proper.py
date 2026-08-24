"""La taglia del ramo proper sulla POPOLAZIONE VERA.

Vera = le coppie che il prodotto valuta davvero: `_l3_check` marca la
scrittura `contradicted` e restituisce `evidence_facts`, che diventano gli
`ids` passati a `_route_evolutions` (anti_confab_gate.py:1936-1948). NON le
coppie adiacenti nello stesso topic — quelle sono fatti scorrelati e il
prodotto non le incontra mai.

Campione ANCORATO a un rowid massimo, non «i più recenti»: siamo otto a
scrivere e un `ORDER BY rowid DESC LIMIT n` cambia sotto la misura (@ws1 ha
visto 7 → 6 in 15 minuti). L'ancora è stampata: chi rimisura ottiene lo
stesso campione — verificato con due run consecutivi, numeri identici.

═══ ESITO 24/08 20:01, ancora rowid <= 21112 ═══

    proposizioni esaminate .................. 60
    ...marcate `contradicted` .............. 37     (61,7%)
    COPPIE (nuovo, vecchio) valutate ....... 156
    ...in cui il RAMO PROPER decide DA SOLO . 26     (16,7%)

**Letti tutti e 26 uno per uno: NESSUNO è una contraddizione.** Sono misure su
file diversi, campioni diversi (4000 contro 400), regimi opposti, o serie
storiche. Il caso peggiore è un A/B spezzato:

    NUOVO   Con ENTRAMBE le guardie spente il file da EXIT=1  1 failed, 1 passed.
    VECCHIO Il file test_due_guardie_si_coprono da EXIT=0  2 passed con le guardie accese.

Sono le due metà dello stesso esperimento: ritirarne una non aggiorna niente,
distrugge la falsificazione. ⇒ Su questa popolazione il ramo ferma 26 ritiri
che sarebbero stati sbagliati.

⛔ IL LIMITE SOSPENDE LA GENERALITÀ, non l'accompagna. I 60 più recenti sono i
referti di misura scritti dalle otto istanze in un'ora: SHA, nomi di file,
conteggi di test — una popolazione DENSA di nomi propri, dove il ramo scatta
molto più che nel corpus tipico. Il 16,7% **non si generalizza**, e si vede:
con `n=8` lo stesso banco dà 25,0%. Serve un campione stratificato, e non c'è.

⚖️ E NON ASSOLVE IL RAMO. Su `SIB_SAME` (banco gemello
`ws3-il-ramo-proper-decide-da-solo.py`) il soggetto è IDENTICO e il ramo
sopprime una contraddizione vera: resta un difetto. Le due misure insieme
dicono che il ramo va ristretto a guardare DOVE sta il nome proprio, non
tolto né lasciato com'è.

═══ AGGIORNAMENTO 20:12 — DUE CORREZIONI, entrambe contro di me ═══

① IL CAMPIONE STRATIFICATO SALE, NON SCENDE. Questo banco ora campiona a
   passo fisso su tutto il corpus, non «i più recenti»:

       recenti (60)         contradicted 61,7%   il ramo decide 16,7%
       STRATIFICATO (100)   contradicted 56,0%   il ramo decide 23,4%  (218 coppie)

   Il limite che avevo dichiarato — «i recenti sono densi di nomi propri,
   quindi il ramo scatta più che nel corpus tipico» — puntava dalla parte
   SBAGLIATA. Era in buona fede, e un limite dichiarato resta un debito.

② ⛔ IL LIMITE CHE QUESTO BANCO NON PUÒ TOGLIERSI, e va letto prima dei
   numeri: la proposizione passata come «nuova» è **un fatto già nel
   corpus**, non una scrittura nuova. Il prodotto giudica una scrittura
   fresca contro fatti vecchi; qui si confrontano due fatti vecchi, e
   l'ordine temporale NON è garantito. Visto sui testi interi:

       "NUOVO"  ...sono entrambe 0.7.0 e i commit dopo il bump sono 375.
       VECCHIO  Il file pyproject.toml dichiara version = "0.7.5".
       VECCHIO  In pyproject.toml la versione dichiarata e' 0.7.6.

   È una serie storica (0.7.0 → 0.7.5 → 0.7.6) e il «nuovo» è il più
   VECCHIO in contenuto.
   ⇒ REGGE il conteggio: il ramo scatta o no indipendentemente dall'ordine.
   ⇒ CADE la frase «sarebbero stati ritiri sbagliati»: non si sa quale dei
     due sarebbe stato ritirato. Resta vero solo dove le due frasi sono
     scorrelate in QUALUNQUE direzione, che è la maggioranza dei casi.
   ⇒ E si vede che il ramo blocca ANCHE aggiornamenti legittimi (le serie
     di versione): non distingue una serie storica da due misure slegate.

③ Il troncamento era a 82 caratteri e mi ha fatto classificare frasi
   mozzate. Ora è 240. **Chi legge i casi li legga interi.**
"""
from __future__ import annotations

import inspect
import os
import sqlite3
import sys
import time

os.environ.setdefault("HIPPO_RERANK_PRELOAD", "0")

from verimem import Memory                       # noqa: E402
import verimem.anti_confab_gate as G             # noqa: E402

DB = os.environ.get("VERIMEM_BANCO_DB") or str(
    __import__("verimem.config", fromlist=["CONFIG"]).CONFIG.semantic_db)
#: ⚠️ SOLA LETTURA. Passa VERIMEM_BANCO_DB con una COPIA del corpus:
#:   cp ~/.engram/semantic/semantic.db /tmp/copia.db
#:   VERIMEM_BANCO_DB=/tmp/copia.db python <questo file> 60

RAMO = "    if ea or eb:\n        return True\n"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 60


def senza_il_ramo():
    src = inspect.getsource(G._entita_diverse)
    if src.count(RAMO) != 1:
        raise SystemExit("IL BANCO SI RIFIUTA: il ramo non e' isolabile")
    ns = dict(G.__dict__)
    exec(compile(src.replace(RAMO, ""), "<senza-ramo>", "exec"), ns)
    return ns["_entita_diverse"]


def controllo_positivo(senza) -> bool:
    """Il caso noto DEVE essere riconosciuto, o il numero non vale."""
    cand = "The payments team migrated to Stripe in 2025."
    sib = "The checkout squad reverted to the legacy processor."
    return G._entita_diverse(cand, sib) is True and senza(cand, sib) is False


def main() -> None:
    senza = senza_il_ramo()
    if not controllo_positivo(senza):
        raise SystemExit("IL RIGHELLO NON DISCRIMINA: nessun numero da qui.")
    print("controllo positivo: OK")

    c = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
    ancora = c.execute("SELECT MAX(rowid) FROM facts").fetchone()[0]
    print("ANCORA rowid <= %d   (campione riproducibile)" % ancora)
    # STRATIFICATO: N proposizioni distribuite su TUTTO il corpus a passo
    # fisso, non le N piu' recenti. Deterministico => riproducibile.
    tutti = [r[0] for r in c.execute(
        "SELECT rowid FROM facts WHERE rowid <= ? AND superseded_by IS NULL "
        "AND length(proposition) BETWEEN 40 AND 300 ORDER BY rowid",
        (ancora,)).fetchall()]
    passo = max(1, len(tutti) // N)
    scelti = tutti[::passo][:N]
    print("candidati totali: %d   passo: %d   scelti: %d"
          % (len(tutti), passo, len(scelti)))
    righe = c.execute(
        "SELECT proposition, topic FROM facts WHERE rowid IN (%s)"
        % ",".join("?" * len(scelti)), scelti).fetchall()
    print("proposizioni nel campione: %d\n" % len(righe))

    m = Memory(path=DB)
    contraddette = coppie = decise = 0
    esempi = []
    t0 = time.time()
    for prop, _topic in righe:
        try:
            r = G._l3_check(m, prop, None)
        except Exception:
            continue
        if not r or r.get("verdict") != "contradicted":
            continue
        contraddette += 1
        for fid in (r.get("evidence_facts") or []):
            try:
                old = m.semantic.get(str(fid))
            except Exception:
                old = None
            if old is None:
                continue
            coppie += 1
            o, s = G._entita_diverse(prop, old), senza(prop, old)
            if o and not s:
                decise += 1
                if len(esempi) < 60:
                    esempi.append((prop[:240],
                                   str(getattr(old, "proposition", ""))[:240]))
    dt = time.time() - t0

    print("=== POPOLAZIONE VERA (cio' che il prodotto valuta) ===")
    print("  proposizioni esaminate .................. %d" % len(righe))
    print("  ...marcate `contradicted` da _l3_check .. %d" % contraddette)
    print("  COPPIE (nuovo, vecchio) valutate ........ %d" % coppie)
    print("  ...in cui il RAMO PROPER decide DA SOLO . %d" % decise, end="")
    print("   (%.1f%% delle coppie)" % (100.0 * decise / coppie) if coppie else "")
    print("  tempo: %.1fs" % dt)
    print()
    print("=== I CASI, da leggere uno per uno ===")
    for a, b in esempi:
        print("  NUOVO   : %s" % a)
        print("  VECCHIO : %s" % b)
        print()


if __name__ == "__main__":
    main()
