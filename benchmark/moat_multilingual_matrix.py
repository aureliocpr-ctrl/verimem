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

import os
import sys
import tempfile
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


def main(reps: int = 7) -> int:
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

    print(f"{'lang/kind':<14} {'entailed adm':>13} {'false-block':>11} "
          f"{'confab quar':>12} {'escape':>7}")
    tot = {"ok": 0, "fb": 0, "quar": 0, "esc": 0}
    num_esc = 0
    for (lang, kind), st in sorted(stats.items()):
        n_ok = st["ok"] + st["fb"]
        n_bad = st["quar"] + st["esc"]
        print(f"{lang+'/'+kind:<14} {st['ok']:>8}/{n_ok:<4} {st['fb']:>11} "
              f"{st['quar']:>8}/{n_bad:<3} {st['esc']:>7}")
        for k in tot:
            tot[k] += st[k]
        if kind == "numeric":
            num_esc += st["esc"]
    n_ok = tot["ok"] + tot["fb"]
    n_bad = tot["quar"] + tot["esc"]
    fb_rate = 100 * tot["fb"] / max(1, n_ok)
    print(f"\nTOTAL entailed {tot['ok']}/{n_ok} (false-block {fb_rate:.1f}%) · "
          f"confab {tot['quar']}/{n_bad} quarantined "
          f"(escape {100*tot['esc']/max(1, n_bad):.1f}%; numeric escapes {num_esc})")
    ok = fb_rate <= 5.0 and num_esc == 0
    print("VERDICT:", "PASS — value/numeric moat holds across languages; "
          "entity-substitution gap is the documented llm-judge case" if ok
          else "FAIL — a value/numeric contradiction escaped or entailed over-blocked")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
