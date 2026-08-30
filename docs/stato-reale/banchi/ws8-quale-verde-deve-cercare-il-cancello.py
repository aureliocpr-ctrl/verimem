#!/usr/bin/env python
"""Il cancello del rilascio cerca il verde sul commit SBAGLIATO — quale sarebbe quello giusto.

IL PROBLEMA
  `publish.yml` (righe 116-125) chiede `ci` verde su `github.sha`, cioe' sul commit del
  tag. Finche' OGNI commit fa girare `ci`, e' corretto. Ma il 2026-08-30 la coda della CI
  ha 882 run in attesa, il tempo di attraversamento e' passato da 2h38m a ~46 ore, e
  **l'84% del carico e' documentazione**. L'unica leva sull'ingresso e' `paths-ignore` —
  che pero' **da solo CHIUDE il cancello**: un commit che non fa girare `ci` non produce
  nessun esito da leggere, e il gate blocca.

LA FORMA CHE REGGE
  Il cancello non deve chiedere «il verde su QUESTO commit», ma «il verde sull'ultimo
  commit che ha toccato CIO' CHE SPEDIAMO». Non e' un surrogato: se il commit del tag
  cambia solo `docs/`, l'artefatto e' quello gia' verificato, e quel verde **e' il verde
  giusto**.

  ⚖️ La strada che questo banco NON propone: un job "sentinella" che riporti `success`
  senza aver eseguito niente. Sarebbe **un verde ottenuto spegnendo qualcosa**, e costa
  piu' di un rosso onesto.

COSA FA
  Legge le radici spedite da `pyproject.toml` (non una lista scritta a mano: una lista a
  mano invecchia — vedi `ws8-tutto-cio-che-spediamo-e-controllato.py`), calcola quale
  commit il cancello dovrebbe interrogare, e **verifica la premessa**: fra quel commit e
  HEAD i file spediti devono essere IDENTICI. Se non lo sono, la premessa cade e il banco
  lo dice.

COSA NON FA
  Non costruisce il wheel e **non afferma che sia byte-identico**: i timestamp interni
  all'archivio non sono verificati. Verifica cio' che si puo' verificare — che nessun file
  spedito sia cambiato, che la versione sia cablata e che il build non inietti sha o date.

    python docs/stato-reale/banchi/ws8-quale-verde-deve-cercare-il-cancello.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[3]


def git(*a: str) -> str:
    return subprocess.run(["git", *a], cwd=str(RADICE), capture_output=True,
                          text=True, errors="replace", timeout=120).stdout.strip()


def radici_spedite() -> list[str]:
    """I nomi di cartella che il pacchetto impacchetta, letti da `pyproject.toml`."""
    testo = (RADICE / "pyproject.toml").read_text(encoding="utf-8")
    blocco = re.search(r"^include\s*=\s*\[([^\]]*)\]", testo, re.M)
    if not blocco:
        return []
    return [p.rstrip("*") for p in re.findall(r'"([^"]+)"', blocco.group(1))]


def main() -> int:
    print("QUALE VERDE DEVE CERCARE IL CANCELLO DEL RILASCIO?\n")
    radici = radici_spedite()
    if not radici:
        print("  ?  `pyproject.toml` non dichiara `include`: non so cosa viene spedito.")
        print("     Astensione, non un «va bene». EXIT=1.")
        return 1
    paths = [*radici, "pyproject.toml"]
    print(f"  cio' che spediamo (da pyproject.toml): {', '.join(paths)}\n")

    head = git("rev-parse", "origin/main") or git("rev-parse", "HEAD")
    rilevante = git("log", "-1", "--format=%H", head, "--", *paths)
    if not rilevante:
        print("  ?  nessun commit tocca quei percorsi: storia troppo corta o clone superficiale.")
        return 1

    distanza = git("rev-list", "--count", f"{rilevante}..{head}")
    print(f"  il cancello OGGI interroga  : {head[:12]}  {git('log','-1','--format=%s',head)[:56]}")
    print(f"  dovrebbe interrogare        : {rilevante[:12]}  {git('log','-1','--format=%s',rilevante)[:56]}")
    print(f"  distanza                    : {distanza} commit\n")

    # ── la PREMESSA, e va verificata, non assunta ────────────────────────────
    diversi = [r for r in git("diff", "--name-only", rilevante, head, "--", *paths).splitlines() if r]
    tutti = [r for r in git("diff", "--name-only", rilevante, head).splitlines() if r]
    print("  PREMESSA — fra i due commit i file SPEDITI devono essere identici:")
    print(f"    file spediti diversi : {len(diversi)}   {'✅' if not diversi else '🔴 LA PREMESSA CADE'}")
    for r in diversi[:5]:
        print(f"        {r}")
    print(f"    file diversi in tutto: {len(tutti)}   "
          f"{'⚠️ zero: il filtro non sta filtrando, il controllo e cieco' if not tutti else '(il filtro sta filtrando)'}")

    # ── e le due condizioni che rendono l'artefatto indipendente dal commit ──
    py = (RADICE / "pyproject.toml").read_text(encoding="utf-8")
    cablata = re.search(r'^version\s*=\s*"([^"]+)"', py, re.M)
    derivata = re.search(r"setuptools[-_]scm|^dynamic\s*=", py, re.M)
    inietta = re.search(r"SOURCE_DATE_EPOCH|git rev-parse|__commit__", py)
    print("\n  L'ARTEFATTO dipende solo dai sorgenti?")
    print(f"    versione cablata     : {'si, ' + cablata.group(1) if cablata else 'NO'}"
          f"{'   🔴 ma e anche derivata da git' if derivata else ''}")
    print(f"    sha/date iniettati   : {'🔴 SI' if inietta else 'no'}")

    esito = 1 if (diversi or not tutti or derivata or inietta) else 0
    print(f"\n  ⇒ EXIT: {esito}   (0 = il verde di {rilevante[:8]} e' il verde giusto per {head[:8]})")
    print("  ⚖️  NON si afferma che il wheel sia byte-identico: i timestamp interni")
    print("      all'archivio non sono verificati. Si afferma che nessun file spedito e'")
    print("      cambiato e che il build non introduce nulla che vari col commit.")
    print("  ⛔ Questo banco NON modifica `publish.yml`: e' una misura, non una cura.")
    return esito


if __name__ == "__main__":
    sys.exit(main())
