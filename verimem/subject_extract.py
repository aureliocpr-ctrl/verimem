"""Subject-based domain/agent classifier for L1 precision (design (d), 2026-07-22).

Pure, deterministic, no external deps. The L1 keyword anti-confab detectors
fire on verbs (completed/tested/deployed/secure/approved) that are ambiguous
between an AGENT's self-claim about its own software work and a third-party
PROFESSIONAL fact. The discriminator is the SUBJECT HEAD, not the verb:
'the service was deployed' (software → agent) vs 'the bridge joint was deployed'
(physical → domain).

``is_domain_professional`` returns True only for a third-person fact whose
subject head is NOT a software/work artifact. Fail-safe: first person, empty,
pronoun, or uncertain subject → False (the L1 anti-confab keeps escalating).

Used ONLY behind an env-gated, default-off carve-out in the write gate — this
module never changes behavior on its own.
"""
from __future__ import annotations

import re

# Determiners stripped from the front of a subject NP.
_DET = {"the", "a", "an", "this", "that", "these", "those", "il", "lo", "la",
        "le", "gli", "un", "una", "uno", "i"}

# First-person / agent-voice markers → never a third-party domain fact.
_FIRST_PERSON = re.compile(r"\b(?:I|we|We|my|My|our|Our|us|me)\b")

# Finite verbs / copulas that terminate the leading subject NP.
_VERB_MARK = re.compile(
    r"\b(?:is|are|was|were|has|have|had|expires?|expired|remains?|resolved|"
    r"reports?|reported|leads?|led|runs?|ran|opened|closed|migrated|reached|"
    r"spans?|monitors?|monitored|documented|confirmed|tested|deployed|added|"
    r"approved|completed|finished|scheduled|planned|works?|holds?|caught|"
    r"got|became|plays?|lives?|crashed|went|switched|adopted|shipped|passed|"
    r"succeeded|rated|meets?|auto-renews?|renews?|renewed|does|do|did|can|will|"
    r"would|should|may|might|must)\b",
    re.IGNORECASE)

#: Adverbs that sit between the subject NP and its verb ('the team STILL runs') —
#: stripped from the NP tail so they never become a bogus head noun.
_TRAIL_ADV = {"still", "now", "already", "currently", "also", "just", "often",
              "usually", "recently", "never", "always", "typically"}

#: Honorific abbreviations whose trailing dot is NOT sentence punctuation —
#: without this, 'Dr. Rossi confirmed …' tripped the punct guard in
#: ``subject_of`` and the fact fail-safed to escalate (corpus residual,
#: 2026-07-22). The dot is stripped ONLY for these known titles; any other
#: mid-NP period still reads as sentence structure (fail-safe unchanged).
_HONORIFIC = re.compile(
    r"\b(Dr|Mr|Mrs|Ms|Prof|Dott|Ing|Avv|St)\.", re.IGNORECASE)

#: Subject heads that mark an AGENT's own software / work artifact — the register
#: the L1 detectors exist to police. A subject with one of these heads is NOT a
#: domain fact (it escalates). Kept deliberately software/work-scoped; ordinary
#: physical/legal/medical/financial nouns are absent on purpose.
SOFTWARE_HEADS = frozenset({
    "service", "services", "migration", "migrations", "build", "builds",
    "deployment", "deployments", "feature", "features", "endpoint", "endpoints",
    "api", "apis", "app", "apps", "application", "applications", "codebase",
    "code", "module", "modules", "function", "functions", "pipeline",
    "pipelines", "job", "jobs", "task", "tasks", "release", "releases",
    "patch", "patches", "database", "databases", "server", "servers",
    "backend", "frontend", "model", "models", "script", "scripts",
    "container", "containers", "cluster", "clusters", "pod", "pods",
    "commit", "commits", "branch", "branches", "repository", "repositories",
    "repo", "repos", "pr", "prs", "schema", "schemas", "query", "queries",
    "cache", "config", "rollout", "refactor", "merge", "sdk", "cli", "ui",
    "gateway", "webhook", "daemon", "worker", "workers", "workflow",
    "workflows", "test", "tests", "suite", "integration", "component",
    "components", "handler", "handlers", "middleware", "binary", "package",
    # software SYSTEM + performance metrics/attributes (the register of an
    # agent's own-work perf claims: 'throughput reached...', 'the system works').
    # Measured leak-closers (real test corpus, 2026-07-22) — a category, not the
    # two literal words: 'system' is mildly ambiguous (ventilation/immune system)
    # but never a subject head in the vertical corpus, and the carve-out is
    # observe-first behind an env, so the residual FP is measurable not shipped.
    "system", "systems", "throughput", "latency", "uptime", "downtime",
    "qps", "rps", "availability", "performance", "bandwidth", "response",
    "responses", "runtime", "load", "memory", "cpu",
    # ADVERSARIAL leak-closers — the critic-orchestrator counterexample worker
    # (job 8f6d0ec5, 2026-07-22) proved the denylist above was NOT exhaustive:
    # these software/ML/web-register heads were absent, so an agent self-claim
    # ('the algorithm was tested and passed') read as domain and had its L1
    # escalation wrongly suppressed. Only CLEARLY-software heads are added; a few
    # genuinely dual-use heads (protocol/transformer/network/agent/driver/site)
    # are LEFT OUT on purpose — adding them would quarantine legitimate clinical/
    # legal/engineering facts (a false positive), and a lexical denylist cannot be
    # exhaustive either way. This is the proven ceiling of lexical subject
    # classification; the honest promotion gate is the measured corpus + default
    # OFF + observe-first, NOT the completeness of this frozenset.
    "algorithm", "algorithms", "platform", "platforms", "product", "products",
    "website", "websites", "portal", "portals", "parser", "parsers",
    "compiler", "compilers", "heuristic", "heuristics", "dashboard",
    "dashboards", "page", "pages", "library", "libraries", "framework",
    "frameworks", "plugin", "plugins", "widget", "widgets", "kernel", "kernels",
    "microservice", "microservices", "lambda", "dataset", "datasets",
    "embedding", "embeddings", "tokenizer", "tokenizers", "classifier",
    "classifiers", "checkpoint", "checkpoints", "optimizer", "optimizers",
    "prompt", "prompts", "chatbot", "chatbots", "bot", "bots", "crawler",
    "crawlers", "scraper", "scrapers", "indexer", "indexers", "orchestrator",
    "orchestrators",
})

_LEXICAL_CAP = 8192


def subject_of(text: str) -> str:
    """Leading noun-phrase subject: tokens before the first finite-verb marker,
    minus a leading determiner. '' when no clear subject NP is present."""
    t = (text or "")[:_LEXICAL_CAP].strip()
    if not t:
        return ""
    t = _HONORIFIC.sub(lambda m: m.group(0)[:-1], t)
    m = _VERB_MARK.search(t)
    if not m or m.start() == 0:
        return ""
    np = t[:m.start()].strip().rstrip(",;:")
    toks = np.split()
    if toks and toks[0].lower() in _DET:
        toks = toks[1:]
    while toks and toks[-1].lower() in _TRAIL_ADV:
        toks = toks[:-1]
    if not toks or len(toks) > 6 or any(c in np for c in ".!?"):
        return ""
    return " ".join(toks)


def subject_head(text: str) -> str:
    """The head noun of the subject NP (rightmost content token). '' if none."""
    subj = subject_of(text)
    toks = [re.sub(r"[^\w-]", "", t).lower() for t in subj.split()]
    toks = [t for t in toks if t and t not in _DET]
    return toks[-1] if toks else ""


#: pronoun heads carry no domain identity → uncertain → fail-safe to NOT-domain.
_PRONOUNS = frozenset({"it", "they", "he", "she", "this", "that", "you",
                       "i", "we", "one", "someone", "something"})


def _subject_tokens(text: str) -> list[str]:
    """Lowercased content tokens of the subject NP (determiners stripped;
    possessives normalized: "Tom's" -> "tom", so the entity matches its bare
    mention on the other side)."""
    subj = re.sub(r"'s\b", "", subject_of(text))
    toks = [re.sub(r"[^\w-]", "", t).lower() for t in subj.split()]
    return [t for t in toks if t and t not in _DET]


def same_subject(a: str, b: str) -> bool:
    """True iff the two propositions are ABOUT the same subject — the L3-semantic
    NLI pre-filter (P2, 2026-07-22). Rule: same HEAD noun (rightmost content
    token) AND modifier agreement (overlap, subset, or one side bare). An
    empty/pronoun/uncertain subject is a WILDCARD -> True (fail-open: a conflict
    we cannot attribute must still reach the judge, never be silently skipped).
    Measured motivation: the cosine 0.7 pre-filter is inert (595/595 corpus
    pairs clear it) and the NLI over-flags different-subject pairs. Pure and
    symmetric; the gate wiring is separate and env-gated default-off."""
    ta, tb = _subject_tokens(a), _subject_tokens(b)
    if not ta or not tb or ta[0] in _PRONOUNS or tb[0] in _PRONOUNS:
        return True                      # wildcard -> compare (fail-open)
    ha, ma = ta[-1], set(ta[:-1])
    hb, mb = tb[-1], set(tb[:-1])
    if ha != hb:
        # cross-entity containment ("Tom's startup" ~ "Tom"): heads differ but
        # one side's head is a token of the other's subject -> same subject
        # sphere, compare. Applies ONLY on differing heads, so shared-head
        # pairs ('payments team' vs 'design team') still take the modifier
        # branch below and stay separated.
        return ha in tb or hb in ta
    if not ma or not mb:
        return True                      # bare head on one side -> assume same
    return bool(ma & mb) or ma <= mb or mb <= ma


def is_domain_professional(text: str) -> bool:
    """True iff ``text`` reads as a THIRD-PARTY professional/domain fact that the
    L1 keyword anti-confab should treat as advisory rather than escalate.

    True requires ALL of: not first-person; a resolvable subject NP; a subject
    head that is NOT a software/work artifact and NOT a bare pronoun. Any
    uncertainty resolves to False so the anti-confab keeps escalating (the safe
    default). Pure and deterministic."""
    t = (text or "")[:_LEXICAL_CAP]
    if not t.strip() or _FIRST_PERSON.search(t):
        return False
    head = subject_head(t)
    if not head or head in _PRONOUNS or head in SOFTWARE_HEADS:
        return False
    # A numeric head carries NO domain identity ('Cycle 999', 'Sprint 42' — the
    # agent's own work register). Flip-delta find 2026-07-22: '999' classified
    # domain and suppressed L1 on the exact dogfood self-claim. Fail-safe.
    if head.isdigit() or head.replace("-", "").replace(".", "").isdigit():
        return False
    return True
