"""Phase-1 graded confabulation suite — does the write-path gate catch SUBTLE confab TYPES?

R10/R11 showed the source⊢fact gate separates faithful from confabulated facts (0.97/0.99),
but on coarse constructions. The real question: does it hold per CONFABULATION TYPE, on
SUBTLE corruptions — the kind an extractor actually produces? Five types, each a plausible,
on-topic falsehood the source does NOT state:

  entity_swap      : right role, a plausible WRONG entity (similar domain/name)
  numeric          : right quantity, a plausible WRONG value (same order of magnitude)
  temporal_drift   : right event, a near WRONG date (adjacent years)
  overgeneralization: a true specific claim widened to an unsupported universal
  plausible_inference: a plausible conclusion the source never states

Each scenario is FICTIONAL (prior ≈ 0, so only the source can ground a fact) and yields one
(faithful, confab) pair per type. Per-type AUROC + bootstrap CI via benchmark.stats.
Falsification: AUROC < 0.80 on any type = a real blind spot to characterize and fix.
Pure construction; the bench's run() makes the claude -p calls. O5.
"""
from __future__ import annotations

import argparse
import json
from typing import Any

from benchmark.stats import auroc, bootstrap_ci
from verimem.grounding_gate import fact_grounding_score

TYPES = ["entity_swap", "numeric", "temporal_drift", "overgeneralization",
         "plausible_inference"]

# Each scenario: source + true/wrong slots. Wrong values are deliberately SUBTLE (plausible,
# close) — the hard case, not a blatant mismatch.
SCENARIOS: list[dict[str, str]] = [
    dict(subj="the Zorvex-9 reactor",
         source="The Zorvex-9 reactor was commissioned in 2019, sustains a core temperature "
                "of 4200 kelvin, and is operated by the Helmsdale Institute.",
         role="is operated by", ent_true="the Helmsdale Institute",
         ent_wrong="the Hartwell Institute",
         num_pred="sustains a core temperature of", num_true="4200 kelvin",
         num_wrong="4600 kelvin",
         date_pred="was commissioned in", date_true="2019", date_wrong="2018",
         specific="sustains a core temperature of 4200 kelvin",
         overgen="every Zorvex reactor sustains a core temperature of 4200 kelvin",
         inference="is the most thermally efficient reactor of its generation"),
    dict(subj="the Nyx-3 satellite",
         source="The Nyx-3 satellite, launched in 2021, orbits at 540 km altitude and "
                "carries a hyperspectral imager built by Caldera Optics.",
         role="carries an imager built by", ent_true="Caldera Optics",
         ent_wrong="Calder Optics",
         num_pred="orbits at an altitude of", num_true="540 km", num_wrong="580 km",
         date_pred="was launched in", date_true="2021", date_wrong="2022",
         specific="orbits at 540 km altitude",
         overgen="all Nyx satellites orbit at 540 km altitude",
         inference="provides the sharpest civilian imagery currently available"),
    dict(subj="the Qel-7 protocol",
         source="The Qel-7 protocol, ratified in 2017, uses AES-256 encryption and was "
                "designed by the Brindle Working Group.",
         role="was designed by", ent_true="the Brindle Working Group",
         ent_wrong="the Bramley Working Group",
         num_pred="uses an encryption key size of", num_true="256-bit",
         num_wrong="192-bit",
         date_pred="was ratified in", date_true="2017", date_wrong="2016",
         specific="uses AES-256 encryption",
         overgen="every Qel protocol uses AES-256 encryption",
         inference="is immune to all known cryptographic attacks"),
    dict(subj="Dr. Vesna Korh",
         source="Dr. Vesna Korh, who joined Aldous University in 2015, studies deep-sea "
                "bioluminescence and has published 47 papers.",
         role="is affiliated with", ent_true="Aldous University",
         ent_wrong="Aldridge University",
         num_pred="has published", num_true="47 papers", num_wrong="42 papers",
         date_pred="joined her university in", date_true="2015", date_wrong="2014",
         specific="studies deep-sea bioluminescence",
         overgen="studies all forms of marine biology",
         inference="is the leading authority on deep-sea bioluminescence"),
    dict(subj="Project Lumen",
         source="Project Lumen began in 2020 with a budget of 12 million euros and is led "
                "by the Veraud Foundation.",
         role="is led by", ent_true="the Veraud Foundation",
         ent_wrong="the Verault Foundation",
         num_pred="has a budget of", num_true="12 million euros",
         num_wrong="15 million euros",
         date_pred="began in", date_true="2020", date_wrong="2021",
         specific="has a budget of 12 million euros",
         overgen="every Lumen project has a budget of 12 million euros",
         inference="is the best-funded research effort in its field"),
    dict(subj="the Klyx language",
         source="The Klyx language, spoken by about 80,000 people, belongs to the Uralic "
                "family and was first written down in 1890.",
         role="belongs to the language family", ent_true="Uralic",
         ent_wrong="Altaic",
         num_pred="is spoken by", num_true="80,000 people", num_wrong="90,000 people",
         date_pred="was first written down in", date_true="1890", date_wrong="1895",
         specific="is spoken by about 80,000 people",
         overgen="is spoken by the majority of people in its region",
         inference="is the oldest surviving language in its family"),
    dict(subj="the Tarn-5 alloy",
         source="The Tarn-5 alloy, developed in 2018, has a tensile strength of 950 MPa "
                "and was patented by Orrin Metallurgy.",
         role="was patented by", ent_true="Orrin Metallurgy",
         ent_wrong="Orran Metallurgy",
         num_pred="has a tensile strength of", num_true="950 MPa", num_wrong="1050 MPa",
         date_pred="was developed in", date_true="2018", date_wrong="2019",
         specific="has a tensile strength of 950 MPa",
         overgen="all Tarn alloys have a tensile strength of 950 MPa",
         inference="is the strongest lightweight alloy ever produced"),
    dict(subj="the Veil Observatory",
         source="The Veil Observatory, opened in 2012, houses a 4.1-meter telescope and is "
                "funded by the Dunmere Trust.",
         role="is funded by", ent_true="the Dunmere Trust",
         ent_wrong="the Dunmore Trust",
         num_pred="houses a telescope of diameter", num_true="4.1 meters",
         num_wrong="4.5 meters",
         date_pred="opened in", date_true="2012", date_wrong="2013",
         specific="houses a 4.1-meter telescope",
         overgen="houses the largest telescope on its continent",
         inference="produces the most cited astronomical data in the world"),
    dict(subj="the drug Calvenir",
         source="Calvenir, approved in 2016, is dosed at 50 mg daily and was developed by "
                "Pell Therapeutics.",
         role="was developed by", ent_true="Pell Therapeutics",
         ent_wrong="Bell Therapeutics",
         num_pred="is dosed daily at", num_true="50 mg", num_wrong="60 mg",
         date_pred="was approved in", date_true="2016", date_wrong="2017",
         specific="is dosed at 50 mg daily",
         overgen="every drug by its maker is dosed at 50 mg daily",
         inference="has the fewest side effects of any drug in its class"),
    dict(subj="Mount Sennar",
         source="Mount Sennar, first summited in 1954, rises to 6,210 meters and lies "
                "within Calbry National Park.",
         role="lies within", ent_true="Calbry National Park",
         ent_wrong="Calbray National Park",
         num_pred="rises to a height of", num_true="6,210 meters",
         num_wrong="6,410 meters",
         date_pred="was first summited in", date_true="1954", date_wrong="1956",
         specific="rises to 6,210 meters",
         overgen="is taller than every other mountain in its range",
         inference="offers the most technically difficult climb in the region"),
    dict(subj="the Aster festival",
         source="The Aster festival, established in 1998, draws 120,000 visitors and is "
                "organized by the Lindholm Society.",
         role="is organized by", ent_true="the Lindholm Society",
         ent_wrong="the Lindholt Society",
         num_pred="draws an attendance of", num_true="120,000 visitors",
         num_wrong="150,000 visitors",
         date_pred="was established in", date_true="1998", date_wrong="1999",
         specific="draws 120,000 visitors",
         overgen="is the largest festival in the entire country",
         inference="is the most profitable cultural event in its city"),
    dict(subj="the spacecraft Orrel-2",
         source="The Orrel-2 spacecraft, launched in 2014, weighs 1,800 kg and was built by "
                "the Mersk Agency.",
         role="was built by", ent_true="the Mersk Agency",
         ent_wrong="the Merrick Agency",
         num_pred="has a mass of", num_true="1,800 kg", num_wrong="2,100 kg",
         date_pred="was launched in", date_true="2014", date_wrong="2015",
         specific="weighs 1,800 kg",
         overgen="every Orrel spacecraft weighs 1,800 kg",
         inference="was the most ambitious mission its agency ever attempted"),
]


def _cap(s: str) -> str:
    """Capitalize the FIRST character only (subjects are proper nouns; str.capitalize
    would wrongly lowercase the rest — 'Mount Sennar' -> 'Mount sennar')."""
    return s[:1].upper() + s[1:]


def _pairs(sc: dict[str, str]) -> dict[str, tuple[str, str]]:
    s = sc["subj"]
    og = sc["overgen"]
    # over-gen confab: universal-quantifier forms ("every/all X…") stand alone; predicate
    # forms ("is taller than…") get the subject prepended. Either way a full sentence.
    og_sentence = (f"{_cap(og)}." if og.split()[0] in ("every", "all")
                   else f"{_cap(s)} {og}.")
    return {
        "entity_swap": (f"{_cap(s)} {sc['role']} {sc['ent_true']}.",
                        f"{_cap(s)} {sc['role']} {sc['ent_wrong']}."),
        "numeric": (f"{_cap(s)} {sc['num_pred']} {sc['num_true']}.",
                    f"{_cap(s)} {sc['num_pred']} {sc['num_wrong']}."),
        "temporal_drift": (f"{_cap(s)} {sc['date_pred']} {sc['date_true']}.",
                           f"{_cap(s)} {sc['date_pred']} {sc['date_wrong']}."),
        "overgeneralization": (f"{_cap(s)} {sc['specific']}.", og_sentence),
        "plausible_inference": (f"{_cap(s)} {sc['specific']}.",
                                f"{_cap(s)} {sc['inference']}."),
    }


def run(llm: Any, *, model: str | None = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for sc in SCENARIOS:
        for typ, (faithful, confab) in _pairs(sc).items():
            sf = fact_grounding_score(llm, sc["source"], faithful, model=model)
            scf = fact_grounding_score(llm, sc["source"], confab, model=model)
            rows.append({"type": typ, "faithful_score": sf, "confab_score": scf})
    per_type: dict[str, Any] = {}
    for typ in TYPES:
        tr = [r for r in rows if r["type"] == typ]
        s = [r["faithful_score"] for r in tr] + [r["confab_score"] for r in tr]
        y = [1] * len(tr) + [0] * len(tr)
        point, lo, hi = bootstrap_ci(s, y, b=2000, seed=0)
        mf = sum(r["faithful_score"] for r in tr) / len(tr)
        mc = sum(r["confab_score"] for r in tr) / len(tr)
        per_type[typ] = {"auroc": round(point, 3), "ci95": [round(lo, 3), round(hi, 3)],
                         "mean_faithful": round(mf, 1), "mean_confab": round(mc, 1),
                         "n_pairs": len(tr), "blind_spot": bool(point < 0.80)}
    alls = [r["faithful_score"] for r in rows] + [r["confab_score"] for r in rows]
    ally = [1] * len(rows) + [0] * len(rows)
    op, olo, ohi = bootstrap_ci(alls, ally, b=4000, seed=0)
    return {"n_scenarios": len(SCENARIOS), "overall_auroc": round(op, 3),
            "overall_ci95": [round(olo, 3), round(ohi, 3)],
            "overall_plain_auroc": round(auroc(alls, ally), 3),
            "per_type": per_type,
            "blind_spots": [t for t in TYPES if per_type[t]["blind_spot"]], "rows": rows}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Graded confabulation-type suite (Ph1).")
    p.add_argument("--model", type=str, default="claude-sonnet-4-6")
    p.add_argument("--out", type=argparse.FileType("w"), default=None)
    args = p.parse_args(argv)
    from benchmark.qa_runner import LeanClaudeCLILLM
    res = run(LeanClaudeCLILLM(model=args.model, timeout_s=60), model=None)
    res["model"] = args.model
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=2))
    if args.out:
        json.dump(res, args.out, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["SCENARIOS", "TYPES", "run", "main"]
