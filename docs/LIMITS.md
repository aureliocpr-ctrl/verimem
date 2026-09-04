# Limits — measured, with the number and the date

> Every limit here comes with the measurement that produced it. The README keeps one
> line and points here: a user should read what the product does first, and what it
> does not do second — but both must be true and both must be public.

## Judge (the moat) and the write gate

Three limits belong next to those numbers. **Length**: they are measured on short
sources — adding unrelated sentences raises the judge's score sharply (one case
went 9.6 → 35.9 against a cut of 40) and on some phrasings flips the verdict. Measured again on 2026-09-03/04 with stronger numbers: the same contradiction that scores 1.8 alone scores 99.9 with one unrelated sentence beside it, while the base model, a large NLI and MiniCheck are not moved (LANT-172); on 60 direct Italian contradictions our judge is at AUROC 0.87 where those two are at 1.00, and loses 0.063 with the extra sentence against 0 for them — the cause is our fine-tuning, not the model family, and the fix is scheduled for 0.8.0. **Order**: a self-claim («the feature works and is verified») is quarantined on its own but ADMITTED when it follows a true third-party sentence in the same write («the technician tested the plant and signed the report, and the feature is verified»), on all three ports, in Italian and English, 7 phrasings out of 7 (2026-09-04): the domain carve-out reads the subject of the first clause only. Write one claim per call until it is fixed.
**Script**: beyond IT/EN the first guarantee degrades rather than stopping at a
border — on entity substitution ZH and JA hold as well as EN (1–2 in 10), KO 3,
AR 5, HI 7, and Thai fails outright at 10/10; on the implicit class the shape holds but the
order does not — there AR is the worst (4 in 5), not HI. Negation alone is
still unmeasured outside IT/EN; in Thai it fails 6/10. **Figures**: the 8/10–9/10 above is an average over two halves that behave in opposite ways. An added detail that contains a **figure** is caught **0/18** — every case, across EN, ZH, JA, KO, AR and HI — because the check is lexical and looks for the digit in the source, so it has no reason to depend on the script and does not. The same detail **without a figure** slips through **16/18**, and is already 3/3 in English: here there is no gradient to speak of. Read that row as «almost always stopped if there is a number, almost never if there isn't», not as «2 in 10 stopped» (`docs/stato-reale/banchi/ws3-la-seconda-garanzia-fuori-da-it-en.py`; no true claim was wrongly rejected in any script, 0/1 each).
