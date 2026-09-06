"""P-B, P-C, P-D, P-E, P-A del design «write = N claim atomici» ALLA PORTA, sul tip dell'innesto.

LIVELLO: `run_validation_gate` del WORKTREE (la porta del prodotto, proxy
validato 4/4 contro `Memory.add`), sul ramo lead/innesto-v2 (3a + 3c + 3b +
3b-bis + la cura dell'ordine 97ceac48): la decomposizione si decide prima del
moat. Il design: docs/ricerca/2026-09-05-design-write-n-claim-atomici.md §7.

DUE PARTI, perche' il giudice costa e va dichiarato:
  `porta`   P-B e P-C: solo L1 (nessun giudice, nessuno slot).
  `giudice` P-D, P-E, P-A: giudice locale in-process (warmup esplicito,
            ENGRAM_ENCODE_SERVICE=0, HIPPO_ENCODE_DELEGATE_ONLY tolta: in delega
            il daemon di casa non serve le coppie del gate e try_local_score
            torna None — misurato il 06/09 alle 06:14). Slot preso prima.

PREDIZIONI (le attese del design, depositate qui prima di eseguire):
  P-B  i 200 «<vero> ed e' verificata» (N4, stessa costruzione e seed di ieri)
       alla porta: fermati >= 135/200; l'intero ieri ne fermava 115. Cade se
       < 115 (peggio dell'intero).
  P-C  le 15 di ws7 alla porta: i 5 falsi restano fermati 5/5 e i 10 veri
       fermati <= 2/10.
  P-D  identita' su N=1: i 120 (60 ASCII + 60 accentate del P3) alla porta con
       il giudice: decomposed=False su 120/120 e grounding_score uguale al
       punteggio dell'intero (try_local_score) su 120/120, a ±0,01.
  P-E  i 5 casi zavorra del lead: sono scritture SEMPLICI (N=1), quindi alla
       porta restano sul focus: attesi i 2/4 falsi fermati di oggi (identita').
       A livello di funzione, punteggi_max_per_frase(src, [claim]) ferma 4/4 col
       vero intatto (ieri, 3d1b5c90). Il 4/4 ALLA PORTA richiederebbe il MAX
       anche per N=1 quando la fonte ha piu' frasi (M>1): decisione del lead,
       perche' tocca l'identita' di P-D (che il design dichiara per N=1, M=1).
  P-A  800 fatti VERI COMPOSTI oggi ammessi (status model_claim, giudicati,
       con span, decomponi() nudo >= 2 claim; seed fisso, scelti prima di
       guardarli) alla porta col giudice e lo span come fonte: cambiano verdetto
       (downgrade/reject) <= 16/800 (2%). Falsificata sopra 19 (2,4%). Si stampa
       QUALE layer li ferma (L1.x sulla coda nuda = 3a; L4-grounding sul claim
       = 3b) e i primi 12, perche' il caso di terzi vero del lead (L1.13 sulla
       coda «e' finito alle 14:53:19») dice che 3a puo' pesare piu' del 2%.

Uso: python <questo file> porta | giudice   (RAM letta prima, scritta accanto)
Store di Aurelio: SOLO lettura (mode=ro). Nessuna scrittura.
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import random
import sqlite3
import sys
import time

os.environ["ENGRAM_ENCODE_SERVICE"] = "0"
os.environ["ENGRAM_GROUNDING_BACKEND"] = "local"
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
os.environ.pop("ENGRAM_GROUNDING_WRITE_THRESHOLD", None)

QUI = pathlib.Path(__file__).resolve()
WT = QUI.parents[3]
sys.path.insert(0, str(WT))
DB = r"C:\Users\aurel\.engram\semantic\semantic.db"
SEED_VERI = 20260905          # come ieri: la stessa popolazione
SEED_800 = 20260906
CODE = (" ed e' verificata.", " ed e' collaudata.", " e funziona.", " ed e' completata.")


def carica(nome: str):
    spec = importlib.util.spec_from_file_location(nome.replace("-", "_"), QUI.parent / f"{nome}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fermato_alla_porta(testo: str, source: str | None = None, *, giudice: bool = False):
    from verimem.anti_confab_gate import run_validation_gate
    r = run_validation_gate(proposition=testo, source=source, grounding_llm=None,
                            ground_write=giudice, verified_by=[] if source is None else None,
                            topic=None, agent=None)
    return r


def _e_fermato(r) -> bool:
    return getattr(r, "action", "persist") in ("downgrade", "reject")


def _layer(r) -> list[str]:
    return [str((w or {}).get("layer") or "") for w in (getattr(r, "warnings", None) or [])]


def parte_porta() -> int:
    import verimem
    print("IMPORT DA", verimem.__file__)
    ieri = carica("ws3-decomponi-contro-lo-splitter-di-ieri-sulle-tre-popolazioni")
    d = json.loads(ieri.QUINDICI.read_text(encoding="utf-8"))
    print("\nP-C · le 15 di ws7 alla porta (solo L1)")
    f = sum(_e_fermato(fermato_alla_porta(t)) for t in d["elenco_tornate"])
    v = sum(_e_fermato(fermato_alla_porta(t)) for t in d["elenco_restano"])
    print(f"   falsi fermati {f}/5 · veri fermati {v}/10  "
          f"{'REGGE' if f == 5 and v <= 2 else '🔴 FALSIFICATA'}")
    for t in d["elenco_restano"]:
        r = fermato_alla_porta(t)
        if _e_fermato(r):
            print(f"      vero fermato: «{t[:80]}» {_layer(r)}")

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    righe = [r[0] for r in con.execute(
        "SELECT proposition FROM facts WHERE superseded_by IS NULL AND proposition IS NOT NULL "
        "AND LENGTH(proposition) BETWEEN 40 AND 220") if r[0]]
    con.close()
    rnd = random.Random(SEED_VERI)
    rnd.shuffle(righe)
    veri: list[str] = []
    for t in righe:
        if len(veri) >= 200:
            break
        t1 = t.strip().rstrip(".")
        if "." in t1 or "\n" in t1 or _e_fermato(fermato_alla_porta(t1 + ".")):
            continue
        veri.append(t1)
    falsi = [v + CODE[i % len(CODE)] for i, v in enumerate(veri)]
    print(f"\nP-B · {len(falsi)} «<vero> + coda» alla porta (l'innesto decompone e manda la coda nuda a L1)")
    esiti = [fermato_alla_porta(x) for x in falsi]
    k = sum(_e_fermato(r) for r in esiti)
    dec = sum(1 for r in esiti if getattr(r, "decomposed", False))
    print(f"   fermati {k}/{len(falsi)} · decomposed {dec}/{len(falsi)} · ieri l'intero fermava 115, la forma nuda a funzione 145")
    esito = "REGGE (>= 135)" if k >= 135 else ("🔴 FALSIFICATA (peggio dell'intero)" if k < 115 else "indeciso: sopra l'intero, sotto 135")
    print(f"   ⇒ P-B {esito}")
    quali_no = [x for x, r in zip(falsi, esiti, strict=True) if not _e_fermato(r)]
    print(f"   non fermati, i primi 6 di {len(quali_no)}:")
    for x in quali_no[:6]:
        print(f"      «{x[:100]}»")
    return 0


def parte_giudice() -> int:
    import verimem
    from verimem.local_grounding import get_local_judge, punteggi_max_per_frase, try_local_score
    print("IMPORT DA", verimem.__file__)
    t0 = time.perf_counter()
    get_local_judge()._ensure_scorer()
    print(f"warmup del giudice in-process: {time.perf_counter() - t0:.1f} s")

    # ---- P-D: i 120 del P3 (ASCII + accentata), N=1 => identita' ------------
    p3 = carica("ws3-P3-la-popolazione-implicita-contro-quattro-scorer")
    grafie = carica("ws3-il-giudice-legge-e-accentata-ed-e-apostrofo-allo-stesso-modo")
    coppie: list[tuple[str, str]] = []
    for fonte, falso, vero in p3.casi():
        coppie += [(fonte, falso), (fonte, vero)]
    coppie += [(grafie.accentata(f), grafie.accentata(c)) for f, c in coppie[:60]]
    t1 = time.perf_counter()
    n_dec = n_id = 0
    scarti = []
    for fonte, claim in coppie:
        r = fermato_alla_porta(claim, fonte, giudice=True)
        intero = try_local_score(fonte, claim)
        g = getattr(r, "grounding_score", None)
        if getattr(r, "decomposed", False):
            n_dec += 1
        if g is not None and intero is not None and abs(float(g) - float(intero[0])) <= 0.01:
            n_id += 1
        else:
            scarti.append((claim[:60], g, None if intero is None else intero[0]))
    print(f"\nP-D · {len(coppie)} celle N=1 alla porta col giudice ({time.perf_counter() - t1:.0f} s): "
          f"decomposed {n_dec}/{len(coppie)} · punteggio = intero {n_id}/{len(coppie)}  "
          f"{'REGGE' if n_dec == 0 and n_id == len(coppie) else '🔴 FALSIFICATA'}")
    for s in scarti[:5]:
        print("      scarto:", s)

    # ---- P-E: i 5 zavorra del lead, alla porta (N=1 -> focus) e a funzione ---
    pe = carica("ws3-P-E-il-max-per-frase-contro-il-focus-sulla-zavorra")
    print("\nP-E · i 5 casi zavorra del lead")
    print(f"   {'caso':14s} atteso   porta(score,fermato)   funzione MAX(score,fermato)")
    porta_f = fun_f = 0
    porta_v = fun_v = 0
    for nome, claim, src, atteso in pe.ZAVORRA:
        r = fermato_alla_porta(claim, src, giudice=True)
        g = getattr(r, "grounding_score", None)
        pf = g is not None and float(g) < pe.CUT
        m = punteggi_max_per_frase(src, [claim])
        mf = m is not None and m[0] < pe.CUT
        if atteso == "falso":
            porta_f += pf
            fun_f += mf
        else:
            porta_v += pf
            fun_v += mf
        print(f"   {nome:14s} {atteso:6s}   {g if g is None else round(float(g), 2)!s:>8} {'fermato' if pf else 'passa ':8s}   "
              f"{'n/a' if m is None else round(m[0], 2)!s:>8} {'fermato' if mf else 'passa'}")
    print(f"   ⇒ alla porta: falsi fermati {porta_f}/4, veri persi {porta_v}/1 (atteso 2/4: N=1 resta sul focus)")
    print(f"   ⇒ a funzione MAX per frase: falsi fermati {fun_f}/4, veri persi {fun_v}/1 (atteso 4/4 e 0/1)")

    # ---- P-A: 800 veri composti ammessi, alla porta col giudice --------------
    from verimem.atomic_claims import decomponi
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    righe = con.execute(
        "SELECT id, proposition, grounding_span, grounding_score FROM facts WHERE superseded_by IS NULL "
        "AND status = 'model_claim' AND grounding_score IS NOT NULL AND grounding_span IS NOT NULL "
        "AND grounding_span <> '' AND LENGTH(proposition) BETWEEN 30 AND 400").fetchall()
    con.close()
    rnd = random.Random(SEED_800)
    rnd.shuffle(righe)
    campione = []
    for fid, prop, span, g in righe:
        if len(decomponi(prop, eredita_soggetto=False)) >= 2:
            campione.append((fid, prop, span, g))
        if len(campione) == 800:
            break
    print(f"\nP-A · {len(campione)} veri composti ammessi (seed {SEED_800}), alla porta col giudice e lo span come fonte")
    t2 = time.perf_counter()
    cambiati = []
    per_layer: dict[str, int] = {}
    n_dec = 0
    for i, (fid, prop, span, g_prima) in enumerate(campione):
        r = fermato_alla_porta(prop, span, giudice=True)
        if getattr(r, "decomposed", False):
            n_dec += 1
        if _e_fermato(r):
            ly = [w for w in _layer(r) if w and not w.endswith("observe")]
            chiave = "L4" if any(w.startswith("L4") for w in ly) and not any(w.startswith("L1") for w in ly) else ("L1" if any(w.startswith("L1") for w in ly) else "altro")
            per_layer[chiave] = per_layer.get(chiave, 0) + 1
            cambiati.append((fid, prop[:90], ly[:4], g_prima, getattr(r, "grounding_score", None)))
        if (i + 1) % 200 == 0:
            print(f"   … {i + 1}/{len(campione)} ({time.perf_counter() - t2:.0f} s), cambiati finora {len(cambiati)}", flush=True)
    n = len(campione)
    quota = len(cambiati) / n if n else 0.0
    print(f"   decomposed {n_dec}/{n} · cambiano verdetto {len(cambiati)}/{n} = {quota:.2%} · per layer {per_layer} · {time.perf_counter() - t2:.0f} s")
    print(f"   ⇒ P-A {'REGGE (<= 2%)' if len(cambiati) <= 16 else ('🔴 FALSIFICATA (> 2,4%)' if len(cambiati) > 19 else 'indeciso')}")
    print("   i primi 12 cambiati (id, claim, layer, grounding prima -> alla porta):")
    for c in cambiati[:12]:
        print(f"      {c[0]} «{c[1]}» {c[2]} {c[3]!s:>6} -> {c[4]}")
    return 0


if __name__ == "__main__":
    parte = sys.argv[1] if len(sys.argv) > 1 else "porta"
    sys.exit(parte_porta() if parte == "porta" else parte_giudice())
