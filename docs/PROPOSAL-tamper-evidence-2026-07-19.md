# Tamper-evidence for the audit trail — scope decision (task #24)

Decision owner: **Aurelio**. This picks the *external anchor*; the cryptographic core
is already built and tested (`verimem/tamper_evidence.py`, commit a8ecf57).

## Threat model

The audit trail (`adjudications.db`, opt-in, commit b720867) records every write's
verdict. The threat is an **insider / DB-writer** who edits or deletes a past record to
hide a bad decision — e.g. flips a `quarantined` row to `admitted`, or deletes the row
that shows a confabulation was let through. File permissions don't help against the
very party that runs the process.

## What is already built (needs no decision)

`tamper_evidence.py` hash-chains entries (`entry_hash = sha256(prev_hash‖canonical(entry))`).
`verify_chain` pinpoints the first edited / deleted / reordered / inserted entry. 8
tests. This is the tamper-**detection** half.

**It is not enough on its own** — and the module says so out loud. An attacker who can
write the DB can recompute the whole chain after editing it. Detection only bites if you
hold a **trusted head** from *before* the tampering, kept somewhere the DB-writer can't
rewrite. That external anchor is the decision.

## The decision — pick the anchor (A / B / C, increasing strength + cost)

| | anchor | detects | needs | effort |
|--|--------|---------|-------|--------|
| **A** | periodic head-hash **exported to a file/stream the operator ships to their own log pipeline (SIEM)** | any past-record edit/delete, given one archived head | operator has a log sink (everyone does) | ~½ day: chain columns on the log + `verify()` + a `head()` accessor + export hook |
| **B** | A **+ head signed with an EXTERNAL private key** (key never in the DB/process that writes the log) | + forgery of the head itself by the DB-writer | operator manages a signing key (KMS/HSM/file) | +½ day: sign/verify, key config |
| **C** | B **+ head submitted to a public transparency/timestamp service** (RFC 3161 TSA / a transparency log) | + collusion / retroactive backdating | network egress + a chosen TSA; **conflicts with air-gapped deployments** | +1 day, + an external dependency |

Cross-cutting, regardless of choice:
- chained rows add `prev_hash`/`entry_hash` columns to `adjudications.db` — needs a
  schema-version bump (the log is young; low risk).
- **honesty rule:** whatever we ship, the README states exactly which threat it covers.
  "Tamper-evident audit log" unqualified implies C; A/B must be qualified
  ("tamper-evident **given an archived head** / **under an external key**").

## Recommendation

**A now, B behind a flag.** A is the honest 80/20 — most compliance asks ("prove this
record wasn't altered") are met by a chain + a head your SIEM already retains, and it
keeps air-gap deployments working. B is a small, opt-in add for customers who want the
head unforgeable. C only for a specific customer ask — it drags in a network dependency
that fights the offline-first design.

**Blocked on your pick.** Say A / B / C (or "not now") and I wire the chosen scope onto
the foundation + qualify the README claim accordingly. Until then the foundation stays
unwired — no half-built tamper-evidence claiming more than it detects.
