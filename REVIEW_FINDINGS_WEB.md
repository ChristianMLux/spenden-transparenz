# REVIEW_FINDINGS_WEB.md

Lead review of the UI/UX work packages. Verdicts are Ship, Fix-first or Rethink.

---

## Round 1, 2026-08-28: WP1 #9, WP2 #5, WP3 #7

Reviewed together on an integration branch (`integrate/web-wp1-3`) cut from `main` at
`58f9ea8`, because three branches that each pass alone can still fail when they meet, and
two of them did.

**All three merge into current main with zero conflicts.**

| | WP1 board #9 | WP2 org #5 | WP3 trust #7 |
|---|---|---|---|
| Verdict | **Fix-first** | **Fix-first** | **Fix-first** |
| Blocking | none of its own | first-load JS | build broke on merge |
| Integrated | yes | yes | yes |

Nothing here is a Rethink. The work is sound; three defects only became visible on the
integration branch, and one budget decision belongs to the product owner.

### Integrated evidence

```
npx tsc --noEmit      exit 0
npm run lint          exit 0
npm run contrast      contrast ok, mark parity 0.10 light / 0.31 dark
npm run test:unit     105 passed in 10 files
npm run build         31 static pages
npx playwright test   192 passed
```

192 end-to-end tests green together: axe on five WCAG tag sets in both themes and both
locales, zoom at 640 and 320, the keyboard path, the print PDF, the SEO alternates, zero
third-party requests, and the computed-style parity assertion between a found value and a
"nicht gefunden".

---

### Defect 1: WP3's cached loaders broke WP1's tests (fixed on the integration branch)

`lib/filter.test.ts` calls `getBoard()`. In WP3's branch `getBoard()` became a
`"use cache"` function calling `cacheTag()`, which throws outside a Next build. WP3 had
handled it by mocking `next/cache` inside its own `lib/api.test.ts`; WP1 had no way to
know, because on WP1's branch `getBoard()` was still an ordinary function.

Neither worker could have caught this alone. It is the archetypal integration defect.

Fixed structurally rather than per file: `apps/web/test-setup.ts` mocks `next/cache` once
and `vitest.config.ts` loads it through `setupFiles`, so the next test that imports a
cached loader cannot trip on it either. 93 tests became 105.

### Defect 2: WP3's revalidate route broke `next build` (fixed on the integration branch)

`app/api/revalidate/route.ts` threw at module scope when `NODE_ENV === "production"` and
`REVALIDATE_SECRET` was unset. `next build` collects page data with `NODE_ENV=production`
and no runtime environment, so the entire build failed on a route nobody had called:

```
Error: Failed to collect page data for /api/revalidate
```

The security intent was right and is preserved. Build time is not start time, so the
module-level throw is replaced by a one-time log on the first request. `isAuthorized()`
already returns false without a secret, so an unconfigured deployment still answers 401 to
everything, and it still answers 401 rather than a distinct status, because an
unauthenticated caller should learn nothing about whether the endpoint is configured.

Worth noting for the record: WP3 reported a green build. It was green in a shell that had
the variable set. The lesson is not about WP3; it is that a guard keyed on `NODE_ENV`
fires during the build, which is the one place nobody thinks to look.

### Defect 3: first-load JS on organisation pages, 177.6 KB against a 150 KB budget

This one is not fixed and needs a decision. Measured on the integration branch, module
scripts only, legacy polyfills excluded:

```
177.6 KB gz   /de/organisation/<org>      44 pages x 2 locales
177.2 KB gz   /de/dev/datum               internal, not gated
151.2 KB gz   /de/krise/<crisis>
145.9 KB gz   /de/methodik and the four other trust pages
127.6 KB gz   /de                         a bare redirect that renders no shell
```

Diffing the emitted script tags page against page attributes all of it precisely:

- organisation page = trust-page baseline **+ 30.6 KB of Radix Popover** + 1.1 KB
- board = trust-page baseline **+ 5.3 KB**, which is WP1's filter island and exactly the
  budget it was given

So no worker overspent. The whole overage is one dependency, pulled in by
`<Datum variant="inline">`, which only the organisation page uses.

**The 150 KB number was mine and it was derived from a bad measurement.** I set it when
the board route rendered nothing but an `<h1>`, and read 145 KB as "the board". It was
really the floor for any page that renders the shell at all. The trust pages, which are
prose and nothing else, confirm it: 145.9 KB. That leaves about 4 KB for a page's own
code, which is not a budget, it is a rounding error.

Three options, with what each actually costs:

1. **Raise the budget to 180 KB.** No engineering. Also no constraint left: it would
   accommodate anything anyone ships.
2. **Defer Radix to first interaction.** The chip stays a server-rendered button; the
   popover module is imported when a reader first opens one. Keeps Radix, which the spec
   names, and keeps the behaviour approved at G0. Organisation pages drop to roughly
   147 KB. Cost: the first chip click waits on a ~30 KB chunk, and the async mount has to
   keep focus moving into the popover, which the existing tests would catch if it did not.
3. **Replace Radix Popover with the native HTML Popover API.** Roughly 30 KB to zero, no
   dependency, Escape and light-dismiss built in. Cost: it deviates from a spec line that
   names Radix, and it rewrites a component the product owner approved at G0.

Recommendation: option 2, with the budget set to 155 KB so the board's real 151.2 fits and
there is still a ceiling that means something. Option 3 is technically the best answer and
I would take it in a greenfield, but swapping an approved component and a named library
after a passing gate is not a call I should make alone.

Raised to the product owner. Nothing merges until it is answered, because merging now
would knowingly leave `npm run verify`, which is the agreed merge gate while GitHub
Actions is locked, failing on `main`.

---

### WP2 repairs applied by the lead

WP2's agent transcript was gone by review time, so its three findings were fixed here
rather than sent back.

**`data_gaps` now reads as German sentences.** The section printed
`financial_transparency.income`, `registrations[NP_SWC].identifier` and 73 other database
paths. A reader who came to find out what we do not know was shown a schema.
`components/org/gap-label.ts` maps each entry to a sentence. The entries are not clean
paths: measured across the 44 records there are 75 distinct strings in three shapes, a
plain path, a path with an English qualifier in brackets, and whole English sentences with
no path at all. All three are handled, the qualifier is kept and marked `lang="en"` rather
than dropped because it is often the most specific thing we know, and prose passes through
untouched. A test walks every entry in the dataset and asserts none falls through to a raw
path; the unmapped fallback covers under 2 percent.

**The English research note is marked as English.** `research_notes` is source material and
always English; it sat unmarked in German prose, so a screen reader pronounced it as
German. It now carries `lang="en"` behind a German introduction that makes the switch
deliberate.

**Three invisible fields are on the page.** `legal_name` (37 of 44 records carry one, and
it is the single most useful fact for a reader who wants to look an organisation up in a
register themselves) is in the header, suppressed when it merely repeats the common name.
`annual_report` (13 records) and `audited` (6 records) are in section 5, rendered in both
branches: putting them only next to a figure would have hidden every one of them, since
almost none of those records also carries an income number.

Deferred, logged rather than done: `financial_transparency.iati_publisher.publisher_ref`
is visible for the 3 organisations that also have an IATI registration row, and invisible
for the 2 that only have the financial field. Small enough to leave for the next round.

### Per-package notes

**WP1 #9, board.** Honest reporting throughout: it reported its own 0.7 KB overage and
stopped rather than raising the number, exactly as asked. Two good judgement calls: it
avoided pulling the Radix chunk into `<Datum variant="block">`, which never needs it, and
it built the filter controls from native `fieldset`, `input` and `dialog` rather than
adding shadcn components nobody had approved. Its claim that the shell costs about 18 KB
over the redirect baseline is confirmed by the trust pages at 145.9. Its "pre-existing
test failure" was real and is Defect 1.

One thing to revisit later, not blocking: the number line maps "without a found response"
to `sort=fewest-data` rather than a filter, on the grounds that no `FilterState` field
exists for it and inventing one would let a filter hide organisations the product must
always show. That reasoning is right and the workaround is reasonable, but a reader
clicking "9 ohne gefundene Reaktion" expects to see nine rows, not a reordering. Worth a
follow-up.

**WP2 #5, organisation page.** All eight sections, 88 pages verified by counting emitted
HTML rather than trusting the build summary. The print measurement came in at 268 bytes
brotli worst case against an 8 KB threshold, so the always-in-DOM provenance body is far
cheaper than feared. It caught its own 360px layout bug in the registrations section
through its own screenshot review, which is the review discipline working.

Open, not blocking: `legal_name`, `annual_report`, `audited` and `iati_ref` are not
rendered anywhere, on the grounds that no section of the brief names a slot for them. That
reading is defensible but the outcome is wrong: the annual report and the audited-accounts
flag belong in section 5, and the IATI reference is called out in the spec as the join key
that section 4 should highlight. Follow-up, since the sections exist and this is adding
fields to them.

**WP3 #7, trust pages and data layer.** The strongest piece of judgement in the round: it
found that `app/opengraph-image.tsx` 404s in production because the proxy adds a locale
prefix to any extensionless path, and verified it with curl against a real server rather
than reasoning about it. It also removed an invented contact address it had written
earlier, on its own initiative, for the same reason the brief gives for the imprint. Both
are exactly right.

Two disclosures to keep visible: the `SPENDEN_API_URL` live path is implemented against
the contract but has never run against a real server, and the `/korrekturen` "before"
column is reconstructed from the feasibility report's audit narrative rather than quoted,
because the original values are not preserved anywhere. The second one matters on a
corrections page and should be labelled as such on the page itself, not only in a report.

### Process note

All three workers hit context7 quota exhaustion partway through and fell back to reading
the installed packages' own type definitions. That is the right fallback and in some cases
a better source, but it means the "check the current signature before writing library
code" gate was not uniformly available. Worth knowing before the next round.

---

## Gate G3, honesty review, 2026-08-28

Run against the integration branch. All twelve checks from DESIGN.md section 11 pass. The
commands and what they returned:

| # | Check | Result |
|---|---|---|
| 1 | No superlatives or recommendation language | Pass. Every hit is the product denying it: "Sie bewertet keine Organisation und empfiehlt keine Spende", "Wir bewerten nicht und empfehlen nicht. Es gibt keine Rangliste, keine Punktzahl". |
| 2 | No score, rating, stars, ranking, progress, meter | Pass. `grade` survives as a variable name for the evidence grade and as `datum.triggerLabel`'s interpolation, where it carries the word Register or Dritte, not a quality judgement. |
| 3 | No check marks or crosses next to organisations | Pass, zero hits. |
| 4 | No AthenaRun branding, no #FF6131 | Pass. The only hit is the line in DESIGN.md that defines the check. |
| 5 | No donation calls to action | Pass, zero hits. |
| 6 | Sort options are exactly three, none by evidence grade | Pass. `latest`, `name`, `fewest-data`, pinned by a tripwire test in filter.test.ts. |
| 7 | "nicht gefunden" never styled weaker than a value | Pass. One expression, one class list: `text-base font-normal text-ink` for both. Also asserted by a Playwright test comparing computed colour, size, weight, style, opacity and decoration. |
| 8 | Every number reaches its source in at most two interactions | Pass. Number in the count line applies a filter; the provenance line under each statement is itself the link to the source. |
| 9 | No bare amounts | Pass. No currency literal outside `amount.tsx` and the message files; `<Amount>` requires a `basis` prop, so a naked figure does not compile. |
| 10 | Colour never the sole carrier of meaning | Pass, verified by rendering the page in greyscale. Every mark sits beside its word, so nothing is lost. |
| 11 | `not_public` is a statement about the register | Pass. "Dieses Register veröffentlicht den Wert nicht." |
| 12 | No photographs | Pass. The only image is the locator SVG, which is being removed (see WP1 defect 2). |

### A false alarm worth recording

Midway through this review a spot check returned 404 on a real organisation page, and a
directory listing showed only 38 of the 44 pages built, with six large INGOs missing in a
contiguous block. That looks exactly like validation silently dropping records, which on
this product would be serious.

It was not. Both readings came from inspecting `.next` while a Playwright-managed
`npm run build && npm start` was writing into it. A clean rebuild produces all 44, and a
server started explicitly returns 200 for all six plus the two I had seen fail.

Two things came out of it that are worth keeping. The screenshot check that produced the
404 had passed, because a screenshot of an error page is still a screenshot; it now
asserts the response status first. And this is the same hazard WP2 reported after losing
time to an orphaned `next start` serving stale CSS. Inspect a build directory only when
nothing is building into it.

---

## Gate G3 re-run after WP4, 2026-08-28

WP4 changed how the whole product looks and added the first thing on it a reader can act
on, so the honesty checklist was run again from scratch rather than assumed to still hold.
Thirteen lines now: DESIGN.md section 11 gained one and had two rewritten, because the
action path made the old wording of check 5 unrunnable.

| # | Check | Result |
|---|---|---|
| 1 | No superlatives or recommendation language | Pass. Every hit is either an unrelated word or the product denying it: "Wir bewerten nicht und empfehlen nicht. Es gibt keine Rangliste, keine Punktzahl". |
| 2 | No score, rating, ranking, meter | Pass. Every hit is a comment explaining the prohibition ("sorting by evidence grade would rank", "no score, no badge row"). One false positive worth knowing: "meter" matches inside `Parameters` in lib/site.ts. |
| 3 | No check marks or crosses | Pass, zero hits. |
| 4 | No AthenaRun branding, no #FF6131 | Pass, zero hits. |
| 5 | No donation call to action | Pass via `npm run check:copy`, 94 files, copy ok. The old grep form of this check was retired here; see below. |
| 6 | Exactly three sort options, none by evidence grade | Pass. `latest`, `name`, `fewest-data` in lib/filter.ts, pinned by a tripwire test. |
| 7 | "nicht gefunden" never weaker than a value | Pass. Computed-style test in org.spec.ts and zoom-and-keyboard.spec.ts, both green. |
| 8 | Every number reaches its source in at most two interactions | Pass. The figures are filter links; the first row carries two source links, its statement provenance and its donation channel. |
| 9 | No bare amounts | Pass. No currency literal outside amount.tsx and the message files; `<Amount>` requires a basis prop. |
| 10 | Colour never the sole carrier of meaning | Pass. Rendered at 1280x900 under `filter: grayscale(1)`: every mark still sits beside its word and the structure is carried by rules and tints, not hue. |
| 11 | `not_public` is a statement about the register | Pass. "Dieses Register veroeffentlicht den Wert nicht." |
| 12 | No photographs | Pass. Zero hits in app/ and components/; the locator SVG this line used to name was removed at G1/G2. |
| 13 | No donation state weaker than a found one (new) | Pass. Computed-style test in board.spec.ts compares the found link against "kein offizieller Spendenweg gefunden" on size, weight, slant, opacity, decoration and transform, and asserts the found one is a link while the missing one is not. |

Two counts from the rendered board are worth recording next to the checklist, because they
are the checklist working rather than passing: the page carries "kein offizieller
Spendenweg gefunden" exactly 10 times and "Keine oeffentliche Reaktionsmeldung gefunden"
exactly 9 times, matching the 10 organisations with no channel found and the "9 ohne
gefundene Reaktion" figure. Both absences are rendered, both at full weight.

### Why check 5 had to be rewritten rather than re-run

Its old form was `rg -i "spenden jetzt|jetzt spenden|donate|jetzt helfen" apps/web` = 0
hits. The action path ships 34 official donation URLs, several of which contain the word
"donate", plus a dataset and a module named for the thing. A zero-hit grep would now fail
on the feature working correctly, and the cheapest way to make it pass again would have
been to rename the honest thing. That is the wrong pressure to put on an author, so the
check is now `npm run check:copy`: it strips negated forms first, because "Sie bewertet
keine Organisation und empfiehlt keine Spende" is the promise, then fails the build on
imperatives and ranking language. It was proved to bite by injecting "Jetzt spenden bei
der empfohlenen Organisation" into a message file and watching the build fail.

### Measured, for the record

`npm run verify` exit 0: tsc clean, eslint clean, contrast ok, copy ok, 128 unit tests,
123 static pages, worst page 151.4 KB gz against 155, 216 Playwright tests. Board payload
64,540 B raw and 12,422 brotli against the budget raised to 66,000 / 12,800. gitleaks over
392 files: no leaks. Lighthouse against the Vercel preview of the merged tree: performance
98 / 96 / 98 mobile and 100 desktop, accessibility 100, best practices 100, SEO 63 on every
page from Vercel's own x-robots-tag noindex on protected previews, which reads 100 on a
production domain.

---

## Post-v1 follow-ups, logged 2026-08-28

Not defects and not blocking v1. Each is written down here so it survives the session
rather than living in a chat thread.

**A tighter fold, from WP1's own branch.** WP1 shipped its version of the fold fix in
parallel with the one that merged, and its result is measurably better: the first article
sits at y=344 against the merged y=470, because it moved the district links into the rail
and put the tabs and the result count on one row. Its third article starts at y=807 rather
than y=981. The merged version is the one the product owner accepted and it is green, so
it was not churned to chase the difference. Taking the extra ~125px later is a contained
change to two components: `components/board/board-explorer.tsx` and the tabs and result
count block. WP1's branch itself must NOT be merged for it: it predates the integration and
would revert WP2 and WP3.

**The IATI publisher reference is invisible for two organisations.** It shows for the 3
that carry an IATI row in `registrations`, and not for the 2 that carry it only in
`financial_transparency.iati_publisher.publisher_ref`. The spec calls IATI the join key
across datasets, so those two should show it. Small: one conditional row in section 4 or 5,
guarded so the 3 that already have a registration row do not get it twice.

**Impressum and Datenschutz are placeholders.** Visible ones, with `robots: index: false`,
no lorem ipsum and no invented address. They stay that way until Chris supplies the
content, and the `noindex` comes off with it.

**The live API path has never met a real server.** `SPENDEN_API_URL` and the zod-validated
adapters in `lib/api.ts` are implemented against `apps/api/openapi.json` and tested against
a mocked fetch. Two gaps are known and marked in comments: the live responders list does
not carry aliases or the local-script name (only `/v1/orgs/{id}` does), and the org-detail
`data` map has no array convention for repeated `partners`. Both were raised with the
backend lead.

**Native HTML Popover API instead of Radix.** Radix Popover is 30.6 KB gz and is currently
deferred to first interaction rather than removed. The native API would take it to zero and
brings Escape and light-dismiss with it. It deviates from a spec line that names Radix and
rewrites a component approved at G0, so it is a spike with a measured number attached, not
a drive-by change.

**Lighthouse has never run.** Chrome will not launch under chrome-launcher on the
maintainer's Windows machine, and GitHub Actions is locked for billing, so `lighthouserc`
has been configured but never executed. The first real Performance, Accessibility, Best
Practices and SEO numbers will come from the Vercel preview or from CI once it is unlocked.
