# -*- coding: utf-8 -*-
"""`doctor` dichiara il moat ACCESO guardando i PESI, o solo i metadati?

Il 17/08 avevo misurato che `verimem doctor` diceva «local CE gate model
installed - the grounding moat is ON» con EXIT=0 su una cartella che conteneva
il solo `config.json` — cioe' cio' che un'estrazione interrotta lascia — mentre
un `verimem save` reale sulla stessa macchina tornava `judged=False`,
`grounding_score=None`, e AMMETTEVA un claim smentito dalla propria fonte.

Da allora ho citato quel rosso per undici giorni SENZA RIMISURARLO. Oggi,
28/08, leggendo il sorgente trovo `holds_the_weights()` (local_grounding.py:68)
e un commento che cita la mia stessa data. Ma leggere il sorgente NON e'
misurare: la lezione di casa dice che il livello a cui misuri decide il
verdetto — regex interna < funzione pubblica < LA PORTA CHE IL PRODOTTO USA — e
che ogni salto puo' ribaltare, in entrambe le direzioni. Quindi si misura alla
porta, con l'eseguibile.

LA PREDIZIONE, scritta prima di eseguire:

  (A) cartella VUOTA            -> doctor NON dice «moat is ON»   (era gia' cosi')
  (B) SOLO config.json          -> doctor NON dice «moat is ON»   <- LA CELLA
  (C) cartella REALE coi pesi   -> doctor dice «moat is ON»

CONDIZIONE DI FALSIFICAZIONE, e riguarda solo la cella (B): se con il solo
`config.json` `doctor` dice ancora «the moat is ON», la cura e' cosmetica e il
rosso del 17/08 RESTA. Se invece (C) non dicesse piu' «ON», la cura sarebbe
andata troppo in la' e avrebbe spento un vero.

CONTROLLO CHE DEVE POTER FALLIRE: le tre celle devono DIFFERIRE. Se le tre
righe fossero identiche, la variabile non sta arrivando al prodotto (per
esempio `ENGRAM_LOCAL_GATE_MODEL` ignorata) e il banco non misura niente:
allora non c'e' verdetto, c'e' uno strumento da riparare.

REGIME: ogni cella e' un PROCESSO separato che esegue l'eseguibile `verimem`
(non un import), con `HIPPO_DATA_DIR` in una cartella temporanea — cosi' lo
store di Aurelio non viene toccato e le tre celle vedono lo stesso corpus
vuoto. Unica variabile: `ENGRAM_LOCAL_GATE_MODEL`.
NON viene eseguito `verimem warmup`: nessun download, nessun modello caricato.

    python docs/stato-reale/banchi/ws3-doctor-dice-il-vero-sui-pesi-o-solo-sui-metadati.py
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ENV_MODELLO = "ENGRAM_LOCAL_GATE_MODEL"
# le due frasi che il prodotto usa per dire acceso / spento (doctor.py:730, :674)
ACCESO = re.compile(r"moat is ON", re.I)
SPENTO = re.compile(r"moat does NOT run|moat OFF", re.I)


def _riga_del_moat(testo: str) -> str:
    for l in testo.splitlines():
        if "moat" in l.lower() and ("gate model" in l.lower() or "moat is" in l.lower()
                                    or "moat does" in l.lower()):
            return re.sub(r"\s+", " ", l).strip()[:150]
    return "(nessuna riga sul moat)"


def _doctor(model_dir: Path | None, data_dir: Path) -> tuple[int, str]:
    env = dict(os.environ)
    env["HIPPO_DATA_DIR"] = str(data_dir)
    env["PYTHONUTF8"] = "1"
    if model_dir is None:
        env.pop(ENV_MODELLO, None)
    else:
        env[ENV_MODELLO] = str(model_dir)
    p = subprocess.run([sys.executable, "-m", "verimem.cli", "doctor"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env, timeout=300)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    vuota = tmp / "vuota"
    vuota.mkdir()
    solo_meta = tmp / "solo_config"
    solo_meta.mkdir()
    (solo_meta / "config.json").write_text('{"model_type": "bert"}', encoding="utf-8")
    dati = tmp / "dati"
    dati.mkdir()

    print("  REGIME, dichiarato E misurato:")
    print(f"    PYTHONUTF8=1 · processo SEPARATO per cella · eseguibile "
          f"`python -m verimem.cli doctor`")
    print(f"    HIPPO_DATA_DIR={dati} (store temporaneo, quello di Aurelio NON "
          f"e' toccato)")
    print(f"    unica variabile: {ENV_MODELLO} · nessun warmup, nessun download")

    celle = [
        ("A vuota      ", vuota, "NON deve dire ON"),
        ("B solo config", solo_meta, "NON deve dire ON  <- LA CELLA"),
        ("C reale      ", None, "deve dire ON"),
    ]
    esiti = []
    print(f"\n  {'cella':<14} {'exit':>4}  {'ON?':<5} {'OFF?':<5} riga del prodotto")
    print("  " + "-" * 92)
    for nome, d, _atteso in celle:
        code, out = _doctor(d, dati)
        on = bool(ACCESO.search(out))
        off = bool(SPENTO.search(out))
        esiti.append((nome.strip(), code, on, off, _riga_del_moat(out)))
        print(f"  {nome:<14} {code:>4}  {str(on):<5} {str(off):<5} {_riga_del_moat(out)}")

    # ---- controllo: le tre celle devono DIFFERIRE ------------------------
    firme = {(on, off) for _n, _c, on, off, _r in esiti}
    print(f"\n  CONTROLLO: firme (ON,OFF) distinte fra le tre celle: {len(firme)}")
    if len(firme) == 1:
        print(f"     CONTROLLO CADUTO: tutte e tre identiche {firme} ⇒ la variabile")
        print(f"     {ENV_MODELLO} non arriva al prodotto. NESSUN VERDETTO.")
        return 1

    _a, _ca, on_a, _fa, _ra = esiti[0]
    _b, _cb, on_b, _fb, _rb = esiti[1]
    _c, _cc, on_c, _fc, _rc = esiti[2]

    print("\n  VERDETTO")
    if on_b:
        print("     ROSSO CONFERMATO E ANCORA VIVO: con il solo `config.json`")
        print("     doctor dice ancora «the moat is ON». La cura e' cosmetica.")
        return 0
    if not on_c:
        print("     LA CURA E' ANDATA TROPPO IN LA': nemmeno la cartella REALE")
        print("     coi pesi fa dire «ON». Un vero e' stato spento.")
        return 0
    print("     ROSSO CURATO, e lo ritiro. Con il solo `config.json` doctor NON")
    print("     dice piu' «the moat is ON» (era il caso del 17/08: estrazione")
    print("     interrotta), e con i pesi veri lo dice. La distinzione fra")
    print("     METADATI e PESI e' arrivata alla porta, non solo nel sorgente.")
    print("     ⇒ il rosso che ho citato per undici giorni NON esiste piu'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
