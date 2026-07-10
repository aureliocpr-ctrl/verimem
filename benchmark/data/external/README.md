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
