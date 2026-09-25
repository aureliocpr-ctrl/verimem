"""Reproducible receipt for the moat's multilingual claim — the confusion matrix
behind README's "measured EN/IT/FR/ES".

Runs 100 entailed + 100 contradiction confabs (25 each per language) across four
verticals (legal / medical / cadastral / engineering) through the REAL gate
(``Memory.add``, no llm) and prints per-language false-block and escape rates.

Measured 2026-07-18 (gate CE v2): entailed 112/112 admitted (0 false-block);
confabs 104/112 quarantined — all 8 escapes are the SAME shape, an
entity-substitution contradiction (allergen swap) in Spanish that the CE scores
mid-range (~61 vs the ~0.6 of value/numeric contradictions). Value/numeric
contradictions: 0 escapes in any language. This is why the README bounds the
CE-only judge to value/numeric + off-topic, and points entity-substitution and
plausible-added-inference confabs at an injected llm judge.

Run:  python -m benchmark.moat_multilingual_matrix
Exit: 0 if false-block <= 5% and value/numeric escapes == 0 (the shipped bound);
      the Spanish entity-substitution escape is EXPECTED and reported, not failed.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

os.environ["ENGRAM_ENCODE_SERVICE"] = "0"
os.environ.setdefault("VERIMEM_HOSTED", "1")


# (lang, source, entailed, confab, confab_kind)
CASES = [
    ("EN", "Section {s}: either party may terminate with {x} days written notice.",
           "Clause {s} allows termination with {x} days notice.",
           "Clause {s} allows termination with {y} days notice.", ("30", "90"), "numeric"),
    ("IT", "L'articolo {s} prevede il recesso con preavviso scritto di {x} giorni.",
           "La clausola {s} consente il recesso con {x} giorni di preavviso.",
           "La clausola {s} consente il recesso con {y} giorni di preavviso.", ("30", "90"), "numeric"),
    ("FR", "L'article {s} prévoit la résiliation avec un préavis écrit de {x} jours.",
           "La clause {s} permet la résiliation avec {x} jours de préavis.",
           "La clause {s} permet la résiliation avec {y} jours de préavis.", ("30", "90"), "numeric"),
    ("ES", "La sección {s} permite la rescisión con {x} días de preaviso por escrito.",
           "La cláusula {s} permite la rescisión con {x} días de preaviso.",
           "La cláusula {s} permite la rescisión con {y} días de preaviso.", ("30", "90"), "numeric"),
    ("EN", "Patient record {s}: documented allergy to {x} since 2019.",
           "Patient {s} is allergic to {x}.",
           "Patient {s} is allergic to {y}.", ("penicillin", "latex"), "entity"),
    ("IT", "Cartella clinica {s}: allergia documentata a {x} dal 2019.",
           "Il paziente {s} è allergico a {x}.",
           "Il paziente {s} è allergico a {y}.", ("penicillina", "lattice"), "entity"),
    ("FR", "Dossier médical {s} : allergie documentée à la {x} depuis 2019.",
           "Le patient {s} est allergique à la {x}.",
           "Le patient {s} est allergique au {y}.", ("pénicilline", "latex"), "entity"),
    ("ES", "Historia clínica {s}: alergia documentada a la {x} desde 2019.",
           "El paciente {s} es alérgico a la {x}.",
           "El paciente {s} es alérgico al {y}.", ("penicilina", "látex"), "entity"),
    ("EN", "Cadastral sheet {s}: registered area {x} square meters.",
           "Parcel {s} has an area of {x} square meters.",
           "Parcel {s} has an area of {y} square meters.", ("420", "2300"), "numeric"),
    ("IT", "Visura catastale {s}: superficie registrata {x} metri quadrati.",
           "La particella {s} ha una superficie di {x} metri quadrati.",
           "La particella {s} ha una superficie di {y} metri quadrati.", ("420", "2300"), "numeric"),
    ("FR", "Fiche cadastrale {s} : superficie enregistrée {x} mètres carrés.",
           "La parcelle {s} a une superficie de {x} mètres carrés.",
           "La parcelle {s} a une superficie de {y} mètres carrés.", ("420", "2300"), "numeric"),
    ("ES", "Ficha catastral {s}: superficie registrada {x} metros cuadrados.",
           "La parcela {s} tiene una superficie de {x} metros cuadrados.",
           "La parcela {s} tiene una superficie de {y} metros cuadrados.", ("420", "2300"), "numeric"),
    ("EN", "Structural report {s}: the beam is rated for a maximum load of {x} kN.",
           "Beam {s} is rated for {x} kN.", "Beam {s} is rated for {y} kN.", ("140", "500"), "numeric"),
    ("IT", "Relazione strutturale {s}: la trave è certificata per un carico massimo di {x} kN.",
           "La trave {s} è certificata per {x} kN.", "La trave {s} è certificata per {y} kN.", ("140", "500"), "numeric"),
    ("FR", "Rapport structurel {s} : la poutre est certifiée pour une charge maximale de {x} kN.",
           "La poutre {s} est certifiée pour {x} kN.", "La poutre {s} est certifiée pour {y} kN.", ("140", "500"), "numeric"),
    ("ES", "Informe estructural {s}: la viga está certificada para una carga máxima de {x} kN.",
           "La viga {s} está certificada para {x} kN.", "La viga {s} está certificada para {y} kN.", ("140", "500"), "numeric"),
]


def main(reps: int = 7, out: str | None = None) -> int:
    from verimem import Memory
    m = Memory(str(Path(tempfile.mkdtemp(prefix="verimem_matrix_")) / "m.db"))
    stats: dict = {}
    for r in range(reps):
        for lang, src_t, ok_t, bad_t, (x, y), kind in CASES:
            s = f"{lang.lower()}{r}{len(stats)}"
            src = src_t.format(s=s, x=x)
            st = stats.setdefault((lang, kind),
                                  {"ok": 0, "fb": 0, "quar": 0, "esc": 0})
            st["ok" if m.add(ok_t.format(s=s, x=x), source=src)["status"] != "quarantined"
               else "fb"] += 1
            st["quar" if m.add(bad_t.format(s=s, y=y), source=src)["status"] == "quarantined"
               else "esc"] += 1

    s = summarize(stats)
    print(f"{'lang/kind':<14} {'entailed adm':>13} {'false-block':>11} "
          f"{'confab quar':>12} {'escape':>7}")
    for cell, st in s["cells"].items():
        n_ok = st["ok"] + st["fb"]
        n_bad = st["quar"] + st["esc"]
        print(f"{cell:<14} {st['ok']:>8}/{n_ok:<4} {st['fb']:>11} "
              f"{st['quar']:>8}/{n_bad:<3} {st['esc']:>7}")
    print(f"\nTOTAL entailed {s['entailed_admitted']}/{s['entailed_n']} "
          f"(false-block {s['false_block_pct']:.1f}%) · "
          f"confab {s['confab_quarantined']}/{s['confab_n']} quarantined "
          f"(escape {s['escape_pct']:.1f}%; numeric escapes {s['numeric_escapes']})")
    print("VERDICT:", "PASS — value/numeric moat holds across languages; "
          "entity-substitution gap is the documented llm-judge case" if s["pass"]
          else "FAIL — a value/numeric contradiction escaped or entailed over-blocked")
    if out:
        s.update(bench="moat_multilingual_matrix", reps=reps, commit=_commit(),
                 measured_on=time.strftime("%Y-%m-%d"), runs="one run of the whole matrix")
        Path(out).write_text(json.dumps(s, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print("written:", out)
    return 0 if s["pass"] else 1


def summarize(stats: dict) -> dict:
    """The numbers the matrix publishes, computed in ONE place from the per-cell counts:
    main() prints them, ``--out`` writes them for the registry (benchmark/repro_all.py,
    T218), and a matrix rebuilt from two runs uses the same function."""
    cells = {f"{lang}/{kind}": dict(st) for (lang, kind), st in sorted(stats.items())}
    tot = {"ok": 0, "fb": 0, "quar": 0, "esc": 0}
    num_esc = num_bad = 0
    for (_lang, kind), st in stats.items():
        for k in tot:
            tot[k] += st[k]
        if kind == "numeric":
            num_esc += st["esc"]
            num_bad += st["quar"] + st["esc"]
    n_ok, n_bad = tot["ok"] + tot["fb"], tot["quar"] + tot["esc"]
    fb_pct = 100 * tot["fb"] / max(1, n_ok)
    return {"cells": cells,
            "entailed_admitted": tot["ok"], "entailed_n": n_ok, "false_block_pct": fb_pct,
            "confab_quarantined": tot["quar"], "confab_n": n_bad, "escapes": tot["esc"],
            "escape_pct": 100 * tot["esc"] / max(1, n_bad),
            "numeric_escapes": num_esc, "numeric_confab_n": num_bad,
            "pass": fb_pct <= 5.0 and num_esc == 0}


def _commit() -> str | None:
    """The commit of the checkout the bench runs from, or None: the bench never fails for it."""
    try:
        import subprocess
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parent,
                           capture_output=True, encoding="utf-8", timeout=10)
        return r.stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="write the published numbers as JSON (for benchmark/repro_all.py)")
    sys.exit(main(out=ap.parse_args().out))
