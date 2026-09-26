# External datasets — data we did not write (TRUST-CORE block B)

These splits exist so the trust numbers stop grading our own homework
(benchmark/TRUST_CORE.md). Discipline: `dev` may be inspected during
development; `heldout` is RUN, never read; `unanswerable` items provide
probe questions whose knowledge is never ingested.

## HaluEval QA (`halueval_qa_{dev,heldout,unanswerable}.jsonl`)

- Source: RUCAIBox/HaluEval `data/qa_data.json` (10k items built on HotpotQA),
  fields `knowledge` / `question` / `right_answer` / `hallucinated_answer`.
- License: **MIT** — Copyright (c) RUCAIBox/HaluEval authors (Junyi Li,
  Xiaoxue Cheng, Wayne Xin Zhao, Jian-Yun Nie, Ji-Rong Wen, 2023).
  Redistributed samples keep this notice. https://github.com/RUCAIBox/HaluEval
- Cut: `python -m benchmark.external_readpath --make-samples`
  (seed 42, disjoint 100/200/100; full dump cached in `.cache/`, gitignored).
- Source sha256:
  `89ed139ec5e3a3169a0b30e45569ac1283846f76f27f7bb5e908ee6deed57e88`

## SQuAD 2.0 (`squad_v2_{dev,heldout,unanswerable}.jsonl`)

- Source: SQuAD 2.0 (Rajpurkar, Jia and Liang, 2018, "Know What You Don't Know:
  Unanswerable Questions for SQuAD"), the `squad_v2` validation split from the
  Hugging Face hub, reshaped into the `{knowledge, question}` shape of HaluEval.
  https://rajpurkar.github.io/SQuAD-explorer/
- License: **CC BY-SA 4.0** — attribution to the SQuAD authors; these samples
  are an adaptation and stay under CC BY-SA 4.0 (ShareAlike), whatever the
  licence of the code around them. https://creativecommons.org/licenses/by-sa/4.0/
- Cut: `python -m benchmark.make_squad_corpus` (seed 42, the same disjoint
  dev/heldout/unanswerable split as HaluEval).

## TruthfulQA (`truthfulqa_pairs_{dev,heldout}.jsonl`)

- Source: TruthfulQA (Lin, Hilton and Evans, 2021, "TruthfulQA: Measuring How
  Models Mimic Human Falsehoods"), `TruthfulQA.csv` from
  https://github.com/sylinrl/TruthfulQA, reshaped into pairs by
  `benchmark/external_grounding.py`.
- License: **Apache-2.0** — the TruthfulQA authors; redistributed samples keep
  this notice. https://www.apache.org/licenses/LICENSE-2.0
- Cut: `make_samples_tqa` in `benchmark/external_grounding.py` (seed 42,
  100 dev / 300 heldout).

None of these files ships in the sdist or the wheel (`MANIFEST.in` prunes
`benchmark`): they reach whoever clones or forks this repository.
