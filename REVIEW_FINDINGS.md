# Review findings

Backend lead's verdicts on work-package pull requests. One section per PR, verdict `Ship` /
`Fix-first` / `Rethink`, with the reasoning. Findings are recorded whether or not they were acted
on, including the ones that turned out to be my own mistakes.

---

## PR #4 — WP-A, ingestion core — Fix-first

**Shipped well:** `ingest_orgs` and the ReliefWeb jobs follow the bulk-upsert-with-change-detection
pattern; the second run writes zero rows against the real database; the host allowlist rejects
`https://reliefweb.int.evil.example/`; the rate limiter is tested with an injected clock rather
than by sleeping.

**The finding WP-A raised, and why it was right.** `ingest_orgs` hit `ck_org_datum_provenance` on
seven organisations whose `nepal_presence.mode` is `"unknown"` with `source_url: null`. WP-A
reported it with the full list and three options instead of relaxing the constraint or quietly
skipping the rows, and deliberately left six assertions in
`test_provenance_invariants.py` red rather than adjusting them to match broken data. That is
exactly the right instinct and it found a real defect.

**My ruling.** The defect was in the schema, not in the data, the constraint, or the job.
`datum_presence_mode` was the only datum type in the contract whose value could not be null, so a
researcher who could not determine the mode had one word available: the enum member `"unknown"`.
All seven used it, all seven also listed the path in their `data_gaps`, and four wrote a note
about what they could not access. They were documenting a gap in the only vocabulary the schema
offered. Fixed at the source in schema v0.3 (PR #8): the value is nullable, the seven records are
now real gaps with a `gap_reason`, and `"unknown"` stays legal for the sourced case.

**Fix-first:** remove the ingestion-time reclassification. Rewriting research data on the way into
the database is the kind of silent correction this product exists not to make, and with v0.3
merged it is unnecessary — if an unsourced value appears again, `ingest_orgs` should fail loudly.

**WP-A was right and I was wrong about a number.** The gap_reason distribution is 231
`searched_not_found`, not the 237 in the brief and in my PO-0 report. I measured it before
`load_orgs` deduplicated `caritas-nepal`, so my figure counted a 45th record. WP-A measured 231
independently and said so.

---

## PR #6 — WP-B, extraction, verbatim gate, matching, districts — Fix-first

**Shipped well:** the gate's normalisation handles the curly-punctuation and NFKC traps correctly;
matching is exact-on-normalised-form with no fuzzy fallback and says why in the module docstring;
the stated/inherited district distinction survives to the row; the price table carries the date it
was read; the stale-inherited-row limitation is documented rather than hidden. When context7's
quota ran out, WP-B read the pinned `openai` package's own source instead of guessing its API —
the right call, and it said so.

**Critical — an empty quote passes the verbatim gate.** `str.find("")` returns 0, so
`is_verbatim("", anything)` is True and `word_count("")` is 0. A claim with no quote at all is
returned as `auto`, verbatim-verified. Verified against the code: empty, `None`, whitespace-only
and missing-key all return `auto`.

`_build_row` drops these before insertion, so no bad row reaches the database today. It is still
Critical. `gate()` is a public function whose entire contract is "this quote is provable against
the source", and the next caller will not have `_build_row` behind it. And a claim dropped there
never becomes a `rejected_unverbatim` row, so it is invisible to the rejection rate — the number
PO-2 gates on cannot currently see this class of failure.

**Minor — count what `_build_row` drops**, so a model that starts omitting required fields is
visible rather than silent.

---

## PR #3 — WP-C, read-only API — Fix-first

**Shipped well:** the published contract is unchanged — a structural diff against the committed
`openapi.json` shows no path, parameter, schema or field removed and an identical `Datum` property
set, so the web team's generated types are safe. `body_text` appears nowhere. The `sort` enums are
closed and contain no `verification`. The full responders board issues four SQL statements, three
for the district-filtered gate command, asserted permanently by an event listener rather than
measured once. `q` uses parameterised `ILIKE`, not string-formatted SQL.

WP-C also found and fixed three real bugs while wiring: a rate-limit bypass caused by a
router-level dependency resolving before the limiter, a missing `Cache-Control` on raised
`HTTPException`s because FastAPI builds a fresh response, and shared limiter state leaking between
tests.

**Critical, and my mistake rather than WP-C's — the rate-limit key trusts a spoofable value.**
`rate_limit_key` returns `forwarded.split(",")[0]`, the first entry of `X-Forwarded-For`. That
header reads `client, proxy1, proxy2`: the client's own value comes first and each proxy appends,
so the first entry is attacker-controlled. Rotating it per request gives every request a fresh
bucket and defeats the 5/min admin limit that protects `ADMIN_TOKEN` from brute force.

WP-C implemented this exactly as the spec, the plan and its brief all specified. The instruction
was wrong in all three. The fix is the rightmost entry — the one the trusted proxy appended —
which is correct whether a proxy appends to the header or replaces it. The plan is corrected; the
spec needs the same correction from the PO.

The accompanying test also needs to change: it currently proves a spoofed *second* entry cannot
change the key, which passes under both the broken and the fixed implementation. The spoofed
*first* entry is the case that matters.

**Minor — `q` allows LIKE wildcards.** Correctly parameterised and not an injection risk, but `%`
and `_` still act as wildcards. Harmless at 44 organisations.

**Carried by the lead, not by WP-C:** `admin.py` imports `pipeline.cli.JOBS`, and `pipeline` is a
virtual project that is not installed into the API service. Whether that import resolves in a
deployed Railway service is a deployment-topology question. It goes to the security review and the
PO-5 decision.

---

## Cross-cutting

**Test databases were shared between worktrees.** All three conftests used fixed database names
against the one Postgres container, so two workers running suites concurrently dropped each
other's database — surfacing as `ConnectionDoesNotExistError` and as rows vanishing between insert
and read, in test files neither worker had touched. Both WP-A and WP-B reported it rather than
retrying until it went green, which is what made it diagnosable. Fixed in PR #8: each checkout
gets its own database, named from a hash of the repository root.
