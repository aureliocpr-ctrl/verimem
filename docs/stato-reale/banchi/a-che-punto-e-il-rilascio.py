#!/usr/bin/env python
"""I sette cancelli del rilascio, eseguiti tutti, in un comando.

PERCHE' ESISTE
  Cinque dei sette cancelli girano **solo dentro `publish.yml`, e solo DOPO che
  il primo si e' aperto**. Il primo non si apre da giorni, quindi gli altri
  cinque non li ha eseguiti nessuno — e il 2026-08-29 due di loro erano fuori
  dallo stato che il workflow documenta in un commento:

      controlla_registro WHEEL   cablato «EXIT=0 pulito»   misurato **EXIT=1**
      controlla_registro SDIST   cablato «321 in 129 file» misurato **6 in 3**

  Non erano numeri sbagliati: erano numeri **veri quando furono misurati**, su
  un altro commit, rimasti in un commento mentre l'albero si muoveva. Un
  cancello che si puo' guardare solo attraversandolo si scopre chiuso nel
  momento peggiore.

COSA FA, e cosa NON fa
  Esegue i controlli e stampa un verdetto per ciascuno. **Non pubblica, non
  tagga, non tocca `dist/`**: costruisce in una cartella temporanea e la
  rimuove. E' un termometro, non un interruttore.

  Il settimo cancello **non e' automatico** nemmeno qui, perche' non lo e' nel
  processo: e' un blocco di commento nel README che qualcuno deve leggere. Qui
  se ne misura l'unica parte misurabile — se i numeri che dichiara sono ancora
  quelli veri — e si dice a voce alta che il resto e' una lettura umana.

    python docs/stato-reale/banchi/a-che-punto-e-il-rilascio.py
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RADICE = Path(__file__).resolve().parents[3]


def _esegui(*argomenti: str, cwd: Path | None = None, timeout: int = 900) -> tuple[int, str]:
    """Esegue e restituisce (codice, output). Nessuna pipe fra il comando e il
    codice di uscita: con una pipe si legge il codice del FILTRO, e un veto si
    legge verde. Misurato su questo stesso banco il 2026-08-29."""
    fatto = subprocess.run(argomenti, cwd=str(cwd or RADICE), capture_output=True,
                           text=True, errors="replace", timeout=timeout)
    return fatto.returncode, (fatto.stdout or "") + (fatto.stderr or "")


def _riga(numero: str, nome: str, aperto: bool | None, dettaglio: str,
          veto: bool = True) -> None:
    """`veto=False` per i controlli che NON fermano il rilascio.

    La prima versione di questo banco stampava «CHIUSO» anche sugli avvisi e poi
    li escludeva dal totale: quattro righe «CHIUSO» sopra un «CHIUSI: 3 su 7».
    Chi legge crede al conteggio o alle righe, e le due cose dicevano il
    contrario. Un termometro che si contraddice non e' un termometro."""
    if aperto is None:
        segno = "?"
    elif aperto:
        segno = "passa"
    else:
        segno = "FERMA" if veto else "avvisa"
    print(f"  {numero}  {nome:<34} {segno:<7} {dettaglio}")


def main() -> int:
    print("A CHE PUNTO E' IL RILASCIO — i sette cancelli, eseguiti\n")
    codice, testo = _esegui("git", "rev-parse", "HEAD")
    print(f"  albero: {testo.strip()[:12]}   (i controlli girano su QUESTO albero,")
    print("          non sull'artefatto che costruirebbe la CI)\n")
    chiusi = 0

    # ① la CI e' verde sull'ultimo commit di main?
    _, uscita = _esegui("gh", "api", "repos/:owner/:repo/actions/runs?per_page=1",
                        "--jq", ".workflow_runs[0].head_sha", timeout=300)
    sha = uscita.strip().strip('"')
    _, uscita = _esegui("gh", "api", f"repos/:owner/:repo/actions/runs?head_sha={sha}",
                        "--jq", '[.workflow_runs[] | select(.name=="ci" and .head_branch=="main")] '
                                '| .[0].conclusion // "NESSUN RUN"', timeout=300)
    esito = uscita.strip().strip('"') or "NESSUN RUN"
    aperto = esito == "success"
    chiusi += not aperto
    _riga("①", "ci verde sul commit", aperto, f"esito = {esito}")

    # ② la scappatoia e' spenta? (qui APERTO significa «spenta», cioe' sano)
    _, uscita = _esegui("gh", "api", "repos/:owner/:repo/actions/variables",
                        "--jq", ".total_count", timeout=300)
    quante = uscita.strip()
    _riga("②", "PUBLISH_ANYWAY spenta", quante == "0",
          f"variabili di repository = {quante or '?'}"
          "   (un elenco vuoto e uno fallito si scrivono uguale: qui si legge il NUMERO)")

    cartella = Path(tempfile.mkdtemp())
    try:
        codice, uscita = _esegui(sys.executable, "-m", "build", "--outdir", str(cartella))
        if codice != 0:
            _riga("③-⑥", "costruzione del pacchetto", False, f"`python -m build` EXIT={codice}")
            print("\n  Senza pacchetto i quattro cancelli sull'artefatto non sono misurabili.")
            print(uscita[-800:])
            return 1
        wheel = next(iter(cartella.glob("*.whl")))
        sdist = next(iter(cartella.glob("*.tar.gz")))

        codice, _ = _esegui(sys.executable, "-m", "twine", "check", str(wheel), str(sdist))
        chiusi += codice != 0
        _riga("③", "twine check", codice == 0, f"EXIT={codice}")

        codice, uscita = _esegui(sys.executable, "scripts/controlla_registro.py", str(wheel))
        trovato = re.search(r"BLOCCA\s+(.+?)\s{2,}(\d+)\s+in\s+(\d+)\s+file", uscita)
        chiusi += codice != 0
        _riga("④", "registro pulito nel wheel (VETO)", codice == 0,
              f"EXIT={codice}" + (f"  — {trovato.group(2)} «{trovato.group(1)}» in "
                                  f"{trovato.group(3)} file" if trovato else ""))

        codice, _ = _esegui(sys.executable, "scripts/controlla_promesse.py", str(wheel))
        _riga("⑤", "promesse nel wheel (avviso)", codice == 0, f"EXIT={codice}",
              veto=False)

        codice, uscita = _esegui(sys.executable, "scripts/controlla_registro.py", str(sdist))
        trovato = re.search(r"BLOCCA\s+(.+?)\s{2,}(\d+)\s+in\s+(\d+)\s+file", uscita)
        _riga("⑥", "registro nell'sdist (avviso)", codice == 0,
              f"EXIT={codice}" + (f"  — {trovato.group(2)} in {trovato.group(3)} file"
                                  if trovato else ""), veto=False)
    finally:
        shutil.rmtree(cartella, ignore_errors=True)

    # ⑦ il README e' la pagina di PyPI: i numeri che dichiara sono ancora veri?
    testo_readme = (RADICE / "README.md").read_text(encoding="utf-8")
    blocco = "⛔ RILASCIO" in testo_readme
    dichiarati = re.search(r"\*\*(\d+) commits\*\* ahead", testo_readme)
    _, uscita = _esegui("git", "rev-list", "--count", "v0.7.0..origin/main")
    veri = uscita.strip()
    if dichiarati and veri.isdigit():
        scarto = int(veri) - int(dichiarati.group(1))
        aperto = scarto == 0
        chiusi += not aperto
        _riga("⑦", "pagina PyPI aggiornata", aperto,
              f"dichiara {dichiarati.group(1)}, sono {veri}  (scarto {scarto:+d})")
    else:
        _riga("⑦", "pagina PyPI aggiornata", None, "numeri non leggibili")
    print(f"\n  blocco «⛔ RILASCIO» presente nel README: {'si' if blocco else 'NO'}"
          "   — va tolto o aggiornato da chi pubblica")

    print(f"\n  ⇒ cancelli che FERMANO il rilascio: {chiusi}"
          "   (⑤ e ⑥ sono avvisi: segnalano e lasciano passare)")
    print("  ⚖️  ⑦ NON e' un controllo automatico nemmeno in `publish.yml`: e' un blocco di")
    print("      commento che qualcuno deve leggere. Qui se ne misura solo la parte")
    print("      numerica — il resto resta una lettura umana, e si puo' attraversare")
    print("      senza accorgersene, a differenza di ④ che ferma il job.")
    print("  ⚠️  Il pacchetto e' costruito da QUESTO albero, non dall'artefatto della CI:")
    print("      profondita' del clone, ambiente e versione di `build` possono differire.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
