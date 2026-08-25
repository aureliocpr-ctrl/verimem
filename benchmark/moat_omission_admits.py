"""Reproducible receipt for the gap the README declares WITHOUT a number: a
*plausible added inference the source never states* «scores high and is admitted».

The moat answers one question — does this source ENTAIL this fact? — and the
README bounds it honestly to value/numeric contradictions and off-topic confabs.
But it quantifies every small gap (entity-substitution escape, TruthfulQA AUROC,
declined paraphrases) and leaves the largest one qualitative. A reader who sees
four precise numbers and one adjective concludes the quantified ones are the ones
that matter. This bench puts a number on it.

THREE CASES PER SOURCE, and the third is the one under test:
  entailed       the source states it            -> must be ADMITTED
  contradiction  the source states the opposite  -> must be QUARANTINED
  omission       plausible, on-topic, and the source NEVER says it
                                                 -> must be QUARANTINED (it is not)

The first two are the CONTROLS, and they are not decoration: without them an
all-quarantine gate would score a perfect zero on omissions while being useless,
and an all-admit gate would look identical to a broken bench. A number from this
file is only readable if both controls hold — the exit code enforces that.

Measured 2026-08-25 (CE-only judge, no llm provider configured): see the summary
the run prints. Companion to ``moat_multilingual_matrix.py``, which measures the
contradiction side; this one measures the omission side.

Run:  python -m benchmark.moat_omission_admits
Exit: 0 if BOTH controls hold (entailed admitted, contradictions quarantined) —
      the omission escape rate is REPORTED, not failed: it is a declared bound,
      and this file exists to keep its number honest, not to gate CI on it.
      2 if a control breaks, because then the omission number means nothing.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

#: ⚠️ NON si spegne il servizio di encoding qui. Copiandolo da un altro
#: benchmark la prima esecuzione ha stampato «encode delegate unavailable →
#: il fatto viene scritto SENZA embedding» e i controlli sono usciti rotti:
#: un regime degradato non produce un rosso onesto, produce numeri che
#: sembrano un risultato. Il banco gira nel regime del PRODOTTO.

#: (lang, source, entailed, contradiction, omission)
#: The omission is always PLAUSIBLE and ON-TOPIC — that is the whole point. A
#: falsehood that is off-topic is caught by relevance alone and would flatter
#: the gate; these are the ones a careless agent would actually write down.
CASES: list[tuple[str, str, str, str, str]] = [
    ("IT",
     "Verbale del 12 marzo: il magazzino {s} di Rovigo misura 4200 metri quadrati.",
     "Il magazzino {s} misura 4200 metri quadrati.",
     "Il magazzino {s} misura 2600 metri quadrati.",
     "Il magazzino {s} e' dotato di impianto antincendio."),
    ("IT",
     "Referto del 4 aprile: al paziente {s} e' stata somministrata una dose da 500 mg.",
     "Al paziente {s} sono stati somministrati 500 mg.",
     "Al paziente {s} sono stati somministrati 250 mg.",
     "Il paziente {s} ha tollerato bene la terapia."),
    ("IT",
     "Contratto {s}: la fornitura decorre dal 1 giugno per ventiquattro mesi.",
     "La fornitura {s} dura ventiquattro mesi.",
     "La fornitura {s} dura dodici mesi.",
     "La fornitura {s} e' rinnovabile alla scadenza."),
    ("IT",
     "Collaudo {s}: la trave sopporta un carico massimo di 140 kN.",
     "La trave {s} sopporta 140 kN.",
     "La trave {s} sopporta 500 kN.",
     "La trave {s} rispetta la normativa antisismica."),
    ("EN",
     "Minutes of 12 March: warehouse {s} in Rovigo measures 4200 square metres.",
     "Warehouse {s} measures 4200 square metres.",
     "Warehouse {s} measures 2600 square metres.",
     "Warehouse {s} is fitted with a fire-suppression system."),
    ("EN",
     "Report of 4 April: patient {s} was given a 500 mg dose.",
     "Patient {s} was given 500 mg.",
     "Patient {s} was given 250 mg.",
     "Patient {s} tolerated the treatment well."),
    ("EN",
     "Contract {s}: supply runs from 1 June for twenty-four months.",
     "Supply {s} runs for twenty-four months.",
     "Supply {s} runs for twelve months.",
     "Supply {s} is renewable on expiry."),
    ("EN",
     "Load test {s}: the beam withstands a maximum load of 140 kN.",
     "Beam {s} withstands 140 kN.",
     "Beam {s} withstands 500 kN.",
     "Beam {s} meets the seismic code."),
]


def main(reps: int = 2) -> int:
    from verimem import Memory
    m = Memory(str(Path(tempfile.mkdtemp(prefix="verimem_omission_")) / "m.db"))

    #: per language: admitted/total for each of the three kinds
    tally: dict[tuple[str, str], list[int]] = {}
    escaped: list[tuple[str, str, str, str]] = []  #: (lang, kind, proposition, source)

    for r in range(reps):
        for i, (lang, src_t, ok_t, bad_t, omit_t) in enumerate(CASES):
            s = f"{lang.lower()}{r}{i}"
            src = src_t.format(s=s)
            for kind, tpl in (("entailed", ok_t),
                              ("contradiction", bad_t),
                              ("omission", omit_t)):
                prop = tpl.format(s=s)
                admitted = m.add(prop, source=src)["status"] != "quarantined"
                cell = tally.setdefault((lang, kind), [0, 0])
                cell[0] += int(admitted)
                cell[1] += 1
                #: si raccolgono le fughe di ENTRAMBE le classi: la prima
                #: esecuzione ha trovato contraddizioni ammesse in IT e non
                #: in EN, e senza gli esempi quel 25% non dice QUALI.
                if admitted and kind != "entailed":
                    escaped.append((lang, kind, prop, src))

    print(f"{'lang / kind':<24} {'admitted':>10} {'of':>4}   {'rate':>7}   expected")
    for lang in ("IT", "EN"):
        for kind, expect in (("entailed", "ADMIT"),
                             ("contradiction", "block"),
                             ("omission", "block")):
            adm, tot = tally.get((lang, kind), [0, 0])
            if not tot:
                continue
            print(f"{lang + ' / ' + kind:<24} {adm:>10} {tot:>4}   "
                  f"{adm / tot * 100:>6.1f}%   {expect}")

    def _sum(kind: str) -> tuple[int, int]:
        a = sum(tally.get((L, kind), [0, 0])[0] for L in ("IT", "EN"))
        t = sum(tally.get((L, kind), [0, 0])[1] for L in ("IT", "EN"))
        return a, t

    ok_a, ok_t = _sum("entailed")
    bad_a, bad_t = _sum("contradiction")
    om_a, om_t = _sum("omission")

    print()
    print(f"  CONTROL + entailed admitted        {ok_a}/{ok_t}   (must be all)")
    print(f"  CONTROL - contradictions admitted  {bad_a}/{bad_t}   (must be none)")
    print(f"  UNDER TEST omissions admitted      {om_a}/{om_t}"
          f"   = {om_a / om_t * 100:.1f}%" if om_t else "")

    #: A count is not delivered on its own: the examples are what let a reader
    #: check that the bench measured what it claims to have measured.
    for kind in ("contradiction", "omission"):
        rows = [e for e in escaped if e[1] == kind]
        if not rows:
            continue
        print("")
        print(f"  {kind.upper()}S THAT GOT IN ({len(rows)}):")
        for lang, _k, prop, src in rows[:4]:
            print(f"      · [{lang}] admitted: {prop}")
            print(f"        source:            {src}")

    controls_hold = (ok_a == ok_t) and (bad_a == 0)
    if not controls_hold:
        print("\n  CONTROLS BROKEN — the omission number above is NOT readable.")
        return 2
    print("\n  controls hold: the omission rate above is readable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
