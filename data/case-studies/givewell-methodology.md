# Case Study: GiveWell's Evaluation Methodology

Research notes compiled 2026-08-28. Every factual statement below carries a source URL. Statements not backed by a fetched/found source are explicitly marked **[not found]**. Anything that is this researcher's synthesis rather than a sourced claim is marked **[INFERENCE]**.

---

## 1. GiveWell's stated argument against overhead ratios

GiveWell's current top-charity criteria page does **not** foreground overhead ratios at all — it simply doesn't use them as a criterion. The four stated criteria are evidence of effectiveness, cost-effectiveness, room for more funding, and transparency ("open to our intensive investigation process and to public discussion of their track record and progress"). Source: [Our Criteria | GiveWell](https://www.givewell.org/how-we-work/criteria).

The explicit *argument against* overhead ratios lives in GiveWell's blog archive, not the current criteria pages. Key quotes:

- **The "doctor" analogy** (2009): *"Picking charities based on the 'overhead ratio' is like picking your doctor by the percentage of revenue spent on medicine."* GiveWell adds that the reported ratio is "vaguely defined and generally up to the charities reporting it," that minimizing it "discourages a lot of good and necessary spending," and that it is "ultimately irrelevant to the question of whether a charity is changing lives." Source: [The worst way to pick a charity – GiveWell Blog, 2009-12-01](https://blog.givewell.org/2009/12/01/the-worst-way-to-pick-a-charity/).
- **"Pitfalls of the overhead ratio"** (2009): GiveWell argues the accounting categories are gameable — "many evaluation and planning expenses can be and are classified as program expenses" — and that donor pressure to keep overhead low causes charities to under-invest in exactly the evaluation/planning work that would make them more effective, even independent of what the Form 990 numbers show. Source: [Pitfalls of the overhead ratio – GiveWell Blog, 2009-05-21](https://blog.givewell.org/2009/05/21/pitfalls-of-the-overhead-ratio/).
- There is a whole [Overhead ratio tag on the GiveWell Blog](https://blog.givewell.org/category/overhead-ratio/) with further posts on the topic — not individually fetched here.

**Broader field consensus, same argument, different authors:** the 2013 "Overhead Myth" open letter from the three major U.S. watchdogs states outright: *"The percent of charity expenses that go to administrative and fundraising costs—commonly referred to as 'overhead'—is a poor measure of a charity's performance."* Source: [BBB Wise Giving Alliance, Charity Navigator, and GuideStar Join Forces to Dispel the Charity "Overhead Myth"](https://finance.yahoo.com/news/bbb-wise-giving-alliance-charity-132604554.html) (press release text; original GuideStar URL now redirects to candid.org — [confirmed dead redirect](https://learn.guidestar.org/news/news-releases/2013/2013-06-17-overhead-myth)). Full letter PDF located but the fetch could not extract the letter's text (image-based PDF) — [PDF source](https://mb.cision.com/Main/501/9429255/133588.pdf), content **[not found]** in extractable form.

**[INFERENCE]** The shared logic across GiveWell and the 2013 letter is: overhead ratio conflates *spending discipline* with *impact*, is easy to game via accounting classification, and actively punishes investment in the M&E/planning capacity that produces impact — so it should be replaced by outcome-per-dollar measurement, not by a different financial ratio.

---

## 2. What the cost-effectiveness model actually computes

**Core metric:** "cost per life or life-year changed" — GiveWell converts disparate outcomes (deaths averted, income increases, illness avoided) into one comparable unit. Source: [Cost-Effectiveness | GiveWell](https://www.givewell.org/how-we-work/our-criteria/cost-effectiveness).

**Inputs**, per the same page:
- Effectiveness data drawn from studies, explicitly discounted for external validity: *"we generally draw effectiveness estimates from studies, and we would guess that studies often involve particularly well-executed programs in particularly suitable locations."*
- Cost data: *"Planning costs, management costs, and distribution costs are all included in our estimates. We also try to account for the counterfactual value of resources provided by other funders."*
- Moral weights (see below), described as *"subjective inputs, such as the relative value of increasing an individual's income compared to averting a death."*
- Supplemental up/down percentage adjustments "that capture a wide range of [hard-to-quantify] effects."

**Uncertainty representation:** Not formally probabilistic on the public-facing page — described qualitatively via caveats ("Estimates are often based on limited information and are therefore extremely rough") plus point estimates (e.g., "save a life for roughly every $3,500–$5,500 in donations," 2021 figures) rather than published confidence intervals. Source: same [Cost-Effectiveness](https://www.givewell.org/how-we-work/our-criteria/cost-effectiveness) page.

**"X times cash" framing — confirmed, actively used.** GiveWell benchmarks every funding opportunity against unconditional cash transfers (GiveDirectly): an opportunity rated "10x cash" is judged ten times as cost-effective as a cash transfer of equivalent size. As of the 2022 criteria change, the bar for a full top-charity recommendation is roughly 10x cash for global-health interventions (about 6x cash for GiveWell's "livelihoods" category). Sources: [Changes to our top charity criteria, and a new giving option – GiveWell Blog, 2022-08-17](https://blog.givewell.org/2022/08/17/changes-to-top-charity-criteria/); [Re-evaluating the Impact of Unconditional Cash Transfers – GiveWell Blog, 2024-11-12](https://blog.givewell.org/2024/11/12/re-evaluating-the-impact-of-unconditional-cash-transfers/); [Direct cash looks 3-4x more cost-effective in a new GiveWell assessment – GiveDirectly](https://www.givedirectly.org/givewell-2024) (explains the cash benchmark itself was revised upward 3-4x after a 2022 Egger et al. study on local economic multiplier effects).

**Update frequency:** Rolling/continuous. *"We routinely update these models of top charity cost-effectiveness whenever we have new information that will affect our inputs."* The models page shows a version history (May 2026, November 2025, December 2024, September 2023, etc.), i.e. multiple updates per year. Source: [GiveWell's Cost-Effectiveness Analyses | GiveWell](https://www.givewell.org/how-we-work/our-criteria/cost-effectiveness/cost-effectiveness-models).

**Spreadsheet transparency — genuinely high.** The models page links directly to editable Google Sheets per top charity/intervention (e.g., Malaria Consortium, Against Malaria Foundation), and separately links "an extensive document about our cost-effectiveness analysis, primarily intended for staff members at GiveWell" that is nonetheless publicly accessible. GiveWell explicitly invites outsiders to copy the sheet and substitute their own moral weights: *"Anyone can make a copy of GiveWell's cost-effectiveness analysis and input their own moral weights to determine which charity is most cost-effective, given their values."* Sources: [GiveWell's Cost-Effectiveness Analyses | GiveWell](https://www.givewell.org/how-we-work/our-criteria/cost-effectiveness/cost-effectiveness-models); moral-weights copy-and-edit claim per WebSearch summary of [Cost-Effectiveness | GiveWell](https://www.givewell.org/how-we-work/our-criteria/cost-effectiveness).

**Moral weights — the specific numbers (2020-era, still current as of the fetched Moral Weights page):**
- Doubling one person's consumption for one year = **1 unit** (the baseline)
- Averting the death of a child under 5 = **~116–134 units** (figure varies slightly by source year; **134** appears on the fetched page)
- Averting one year of disability = **2.3 units**
- Consumption-to-mortality implied ratio ≈ 1:100

Source: [Moral Weights | GiveWell](https://www.givewell.org/how-we-work/our-criteria/cost-effectiveness/moral-weights).

**How the weights are set — three inputs, explicitly acknowledged as subjective:**
1. GiveWell staff's own values (considering life expectancy, "development of personhood over time," grief at different ages of death).
2. A 2019 beneficiary survey: GiveWell funded IDinsight to survey ~2,000 people in Ghana and Kenya on trade-offs between averting deaths at different ages and increasing income.
3. A 2020 donor survey of ~70 of GiveWell's largest donors on how they valued deaths averted at different ages.

GiveWell's own self-assessment, quoted directly: *"Though we believe moral weights are ultimately subjective, we've worked to ground ours empirically."* And more pointedly: *"We do not believe our current approach is satisfactory: it is based on a number of ad hoc projects and practical adjustments rather than being grounded in a clear rationale."* Source: [Moral Weights | GiveWell](https://www.givewell.org/how-we-work/our-criteria/cost-effectiveness/moral-weights).

GiveWell also publishes a page contrasting its approach with standard health-economics practice: mainstream government/WHO "value of a statistical life" work implies a healthy year is roughly 2-3x as valuable as a year of doubling someone's income, and the standard DALY framework deliberately does *not* weight deaths by age — whereas GiveWell staff often deviate from both, valuing adult deaths "about 1-5x more than infant deaths relative to 'standard' approaches," and states plainly there is little revealed- or stated-preference research from low/middle-income contexts to ground these choices in. Source: [Approaches to Moral Weights: How GiveWell Compares to Other Actors | GiveWell](https://www.givewell.org/how-we-work/our-criteria/cost-effectiveness/comparing-moral-weights).

---

## 3. Evidence standards

**RCTs are the explicit gold standard.** *"Many, including us, consider the randomized controlled trial to be the 'gold standard' in terms of causal attribution."* GiveWell runs standing Google Scholar alerts to catch newly published RCTs on programs it tracks. Source: [Research on Programs | GiveWell](https://www.givewell.org/research/research-on-programs).

An older (2010, explicitly flagged by GiveWell itself as possibly outdated) methodology page on U.S. programs adds detail on how studies are screened: preference for RCTs plus "large sample size, low attrition, and clear/credible measures of impact," reliance on established evidence intermediaries (Coalition for Evidence-Based Policy, Campbell Collaboration), and an instruction to read "formal evaluations... skeptically and critically, due in large part to our concerns about selection bias and publication bias." Source: [Criteria for Evaluating U.S. Programs | GiveWell](https://www.givewell.org/united-states/process/sources-of-evidence) (page self-flagged as from 2010 and "likely to be no longer fully accurate").

**Self-reported charity data — accepted conditionally, not independently audited.** Per a WebSearch-sourced characterization (not a direct primary-source quote, flagged accordingly): GiveWell speaks with charity staff and reviews financial documents, monitoring data, and plans; when a charity's reported figures are specific enough that "there is little room for interpretation" (making fabrication implausible), GiveWell generally accepts them, while watching site visits and conversations for anomalies or inconsistencies. GiveWell does not claim to conduct full field audits (e.g., being present during data collection) and instead sometimes funds meta-charities that strengthen a grantee's own M&E capacity. Source characterization drawn from WebSearch summary; primary GiveWell page making this explicit was **[not found]** in this pass — flag for follow-up if the primary "how we evaluate a study" or grant-page language is needed verbatim.

**Site visits** are real and ongoing (visits logged from 2010 through July 2025 to Kenya, Malawi, India, Uganda, and others) but the site-visits index page itself is a photo/log directory, not a methodology statement — it does not explain what verification activity happens on a visit or how findings are weighed against self-reports. Source: [Site Visits | GiveWell](https://www.givewell.org/research/site-visits). **[not found]**: an explicit primary-source statement of how a site-visit finding would override or adjust a charity's self-reported numbers.

**[INFERENCE]** Net picture: GiveWell's evidence pyramid is (1) independent academic RCTs/quasi-experimental studies for *whether the intervention works in principle*, discounted for external validity to the actual implementation context, layered under (2) charity-reported implementation/monitoring data for *whether this specific charity is delivering it*, spot-checked but not independently audited, layered under (3) explicit, labeled subjective inputs (moral weights, adjustment factors) for converting outcomes into one comparable number.

---

## 4. Known criticisms and GiveWell's own "Our Mistakes" page

**GiveWell's self-reported mistakes** (from the current [Our Mistakes | GiveWell](https://www.givewell.org/about/our-mistakes) page and version history at [December 2024 version](https://www.givewell.org/about/our-mistakes/december-2024-version), [April 2024 version](https://www.givewell.org/about/our-mistakes/april-2024-version), [2019 version](https://www.givewell.org/about/our-mistakes/2019-version), [August 2015 version](https://www.givewell.org/about/shortcomings-august-27-2015)):

- **Research/data-quality errors (through Nov 2023):** plugged raw data "at face value without subjecting the numbers to common-sense scrutiny" — e.g. averaging insecticide-resistance bioassay results ranging 0–100% with no adjustment, and initially modeling a rotavirus vaccine in India as "almost completely ineffective" despite it being part of the national immunization schedule. Fix: added a data sense-checking step.
- **Underestimated counterfactual coverage (through June 2024):** assumed only 5% of people would get insecticide-treated nets through routine (non-mass-campaign) distribution, based on 30-year-old trial data, when newer evidence suggests 25–50% for children under 3 — potentially overstating cost-effectiveness by 15–30%. Fix: updated counterfactual assumptions.
- **Grantmaking spreadsheet error (Nov 2018):** double-counted one funding gap, over-recommending $100,000 to Deworm the World and under-recommending $480,000 to Malaria Consortium. Fix: redesigned spreadsheet with built-in error checks.
- **Overstated fundraising projections (2020–2022):** publicly predicted $1B/year raised by 2025, which was far off; this led to under-investment in fundraising outreach. Fix: public correction (mid-2022) plus new senior outreach hires.
- **Donor-privacy misstep (July 2020):** used donor emails to build Facebook Custom Audiences for ad targeting without offering opt-out first. Fix: deleted the audience, notified donors, formalized a project-scoping review process.
- **Insufficient external expert engagement (through Jan 2024):** external red-teamers caught assumptions (e.g. overly optimistic bednet durability) that GiveWell's internal process had missed. Fix: more conference attendance and dedicated expert-consultation time per grant.
- **Communication tone (2006–2011):** early blog posts about non-recommended charities read as more confidently negative than the underlying (limited) evidence justified. Fix: now runs potentially negative write-ups by the charity before publishing.
- **Hiring/diversity (2007–2014):** failed to prioritize diverse hiring, under-representing women and staff from low/middle-income countries. Fix: specialized recruiters, blinded work-sample review since 2014.
- **Delayed specialist hire (2014–2016):** assigned intervention reports to junior staff rather than hiring an economist sooner, slowing research output.
- **Accidental publication of confidential material (2009–2012, twice):** pre-approval conversation notes leaked. Fix: separate private/publishable folders, weekly audits.

GiveWell's framing: *"We expect the same of ourselves"* as of the organizations it funds, regarding transparency about failure.

**Third-party criticism:**

- **Moral-weights methodology critiques** are the most substantive recurring line of attack. The EA Forum piece "Hard Problems in GiveWell's Moral Weights Approach" and GiveWell's own "Change Our Mind Contest" surfaced concerns that preference-survey respondents are poor judges of small-probability, high-stakes trade-offs; that respondents without lived experience of the relevant hardship give less reliable answers; and that abstract survey questions don't capture real moral intuitions. Sources: [Hard Problems in GiveWell's Moral Weights Approach – EA Forum](https://forum.effectivealtruism.org/posts/dHZZirCrKgyhb3NEZ/hard-problems-in-givewell-s-moral-weights-approach); [The winners of the Change Our Mind Contest – GiveWell Blog, 2022-12-15](https://blog.givewell.org/2022/12/15/change-our-mind-contest-winners/).
- **Happier Lives Institute's "A dozen doubts about GiveWell's numbers"** is the most detailed line-by-line technical critique found. Twelve specific objections across malaria prevention, cash transfers, and deworming cost-effectiveness models — e.g. an inconsistent generalizability discount (30% for malaria vs. 90% for deworming despite comparable evidence gaps), outdated 2013 baseline-consumption data for cash-transfer comparisons (HLI recalculates using more recent GiveDirectly RCTs and finds transfers should look ~70% less relatively impactful than GiveWell's model implies), and a uniform household-spillover multiplier that ignores country-specific household size. HLI states that implementing all twelve adjustments together would cut AMF's (Against Malaria Foundation's) estimated cost-effectiveness by roughly 26%. Source: [A dozen doubts about GiveWell's numbers – Happier Lives Institute](https://www.happierlivesinstitute.org/report/a-dozen-doubts/). Note: HLI itself advocates a subjective-wellbeing (rather than income/mortality) metric, so this is a critique from a specific rival methodological camp, not a neutral audit — flagged as such.
- **Philosophical/scope critique:** some critics argue GiveWell's mortality/income framework misses unintended negative consequences of funded interventions and doesn't systematically fold those into headline cost-effectiveness numbers; others argue for pivoting to subjective-wellbeing metrics entirely (the HLI position). Source: WebSearch summary referencing EA Forum discussion; primary text **[not found]** in this pass.
- **Organizational critique:** commentary alleging under-staffing and slow responsiveness in GiveWell's research/hiring process. Source: [Givewell, and its hiring process, needs serious reform – EA Forum](https://forum.effectivealtruism.org/posts/qJMjbHp9HKxT8XEhp/givewell-and-its-hiring-process-needs-serious-reform) (title/topic only verified via search; not fetched in full).
- Benjamin Ross Hoffman's multi-part "GiveWell: a case study in effective altruism" series is a lengthy independent critical case study; only its existence and URL are confirmed here, content **[not found]** (not fetched). Source: [part 1](https://benjaminrosshoffman.com/givewell-case-study-effective-altruism-1/), [part 6](https://benjaminrosshoffman.com/givewell-case-study-effective-altruism-6/).

---

## 5. Alternative evaluators, for contrast

**Charity Navigator (Encompass Rating System).** Still partly financial-ratio based, but less so than its pre-2020 "one-star-if-your-overhead-is-high" system. Encompass scores ~49 metrics across four "beacons" — Accountability & Finance, Impact & Results, Culture & Community, Leadership & Adaptability — combined into a 0–100% score and 0–4 stars. Accountability & Finance alone is reported to be ~32.5% of the overall score and still includes a program-expense ratio and a liabilities-to-assets ratio. However, Charity Navigator has also been dropping some of the old ratio metrics: sources indicate "administrative expense ratio, fundraising expense ratio, and program expense growth" have been or are being removed from evaluation. Net effect: financial ratios remain present but are now one of four co-equal pillars rather than the whole rating, and an "Impact & Results" beacon (built substantially from the acquired ImpactMatters methodology, see below) now exists alongside them. Sources: [Our Methodology - Charity Navigator](https://www.charitynavigator.org/about-us/our-methodology/); [Accountability & Finance - Charity Navigator](https://www.charitynavigator.org/about-us/our-methodology/ratings/accountability-finance/); [Rating Methodology Guide, March 2026 PDF](https://www.charitynavigator.org/content/dam/cn/cn/landing-pages/Rating%20Methodology%20Guide%20(Updated%20March%202026).pdf).

**The 2013 "Overhead Myth" open letter.** Jointly issued by BBB Wise Giving Alliance, Charity Navigator, and GuideStar (now part of Candid) on 2013-06-17. Its core claim: "the percent of charity expenses that go to administrative and fundraising costs... is a poor measure of a charity's performance," and it urges donors toward transparency, governance, leadership, and results instead. It was released roughly three months after Dan Pallotta's viral TED talk "The way we think about charity is dead wrong," which argued donors reward charities for spending little rather than for achieving big outcomes, and that the "overhead ratio" obsession suppresses the very investment (professional fundraising, marketing, talent) that lets effective nonprofits scale. Sources: [BBB/CN/GuideStar press release](https://finance.yahoo.com/news/bbb-wise-giving-alliance-charity-132604554.html); [Correcting the overhead myth: how Dan Pallotta's TED Talk has begun to change the conversation](https://ideas.ted.com/correcting-the-overhead-myth-how-dan-pallottas-ted-talk-has-begun-to-change-the-conversation/).

**ImpactMatters (acquired by Charity Navigator, Oct 2020).** A startup applying "rigorous methodology to assess nonprofit impact" (cost-per-outcome style analysis, closer in spirit to GiveWell than to ratio-based watchdogs); acquired with $375,000 in support from the Bill & Melinda Gates Foundation, its team forming Charity Navigator's Impact Unit and feeding the Impact & Results beacon of Encompass. Source: [Charity Navigator Rates Nonprofits' Impact for First Time with Acquisition of Ratings Startup, ImpactMatters – PR Newswire](https://www.prnewswire.com/news-releases/charity-navigator-rates-nonprofits-impact-for-first-time-with-acquisition-of-ratings-startup-impactmatters-301151727.html); [A Charity Rating Service Looks Closer at Impact – Inside Philanthropy](https://www.insidephilanthropy.com/home/2020-10-14-a-charity-rating-service-looks-closer-at-impact-with-a-new-merger-and-support-from-gates).

**Founders Pledge.** Impact-first, GiveWell-adjacent methodology: cost-effectiveness analysis, RCTs, Bayesian inference, and judgmental forecasting across a three-stage process (problem prioritization by scale/tractability/neglectedness → solution evaluation → organizational assessment); roughly 20 days of research per recommended charity; explicitly frames its guiding question as "given the limited resources available... how can we do the most good possible?" No mention of overhead/financial-ratio metrics as an evaluation criterion. Source: [Our methodology | Founders Pledge](https://www.founderspledge.com/our-methodology).

**Giving What We Can (GWWC).** Does not evaluate individual charities itself; instead evaluates and defers to "impact-focused" evaluators (GiveWell, Longview Philanthropy, EA Funds, etc.), publishing its own reasoning for which evaluator to trust in which cause area. Its stated contrast with traditional evaluators is explicit: older evaluators "tended to focus on measures like overhead spending, transparency, and the financial health of an organisation... [but] don't take into account differences in the impact of a program" — illustrated with the line "even if 100% of your donation goes directly to a charity's program, if that program isn't accomplishing a lot compared to others, then your money won't be either." Source: [What are impact-focused charity evaluators? | Giving What We Can](https://www.givingwhatwecan.org/what-are-impact-focused-charity-evaluators); process for picking evaluators at [How we choose which charities to recommend](https://www.givingwhatwecan.org/how-we-choose-which-charities-to-recommend) and [Why and how GWWC evaluates the evaluators](https://www.givingwhatwecan.org/why-and-how-gwwc-evaluates-the-evaluators) (titles/URLs confirmed via search, not individually fetched).

**DZI Spenden-Siegel (Germany/DACH) — the direct contrast case.** Standard 4 of DZI's "7 Siegel-Standards" caps *Werbe- und Verwaltungsausgaben* (advertising + administrative expenses) at **30% of total annual expenditure**, with an internal banding of 0–10% ("niedrig"/low), 10–20% ("angemessen"/appropriate), 20–30% ("vertretbar"/acceptable). DZI reserves the right to a separate qualitative judgment of "Wirtschaftlichkeit und Sparsamkeit" (economy and frugality) regardless of the computed ratio, but the ratio itself remains the primary, quantifiable gatekeeping mechanism for seal award. This is **structurally the overhead-ratio model that GiveWell and the 2013 U.S. letter explicitly reject** — DACH's dominant "trust mark" for donors is built on exactly the metric the English-language effective-altruism-adjacent evaluator ecosystem spent the last ~15 years arguing against. Sources: [Die 7 Siegel-Standards – DZI](https://www.dzi.de/spendenberatung/spenden-siegel/die-7-siegel-standards/); [DZI-Konzept Werbe- und Verwaltungsausgaben (PDF)](https://www.dzi.de/wp-content/pdfs_Spenderberatung/DZI-Konzept_W+V_2019.pdf).

---

## 6. What a non-recommending information layer should take — and should not

**Sourced building blocks a platform can lean on (each traceable to above):**
- Overhead/admin ratios are contested as a primary signal by essentially the entire English-language charity-evaluation field, including the three major U.S. watchdogs themselves (2013 letter) — this is not a fringe position; presenting a bare "Verwaltungskostenquote" as *the* efficiency signal (the DZI/status-quo DACH pattern) means importing a critique that the source field itself has already made against that exact metric. [Section 1, Section 5-DZI]
- GiveWell shows that a ratio-free system can still be legible if it (a) publishes the actual model/spreadsheet, (b) states its update history and version dates, (c) explicitly labels which inputs are subjective (moral weights) versus evidence-derived (RCT effect sizes), and (d) benchmarks everything against one common reference point (cash transfers) so numbers are comparable across very different program types. [Section 2]
- GiveWell explicitly treats self-reported charity data as provisionally trustworthy but spot-checked, not audited — and says so. A platform that also can't independently audit self-reported data should say exactly that, rather than implying verification it hasn't done. [Section 3]
- A public "mistakes log" (GiveWell's "Our Mistakes" page) is a specific, replicable transparency mechanism — not just a value statement but a maintained, dated, versioned artifact. [Section 4]
- Deferring to (and periodically re-evaluating) other evaluators, as GWWC does, is a viable alternative to building primary cost-effectiveness research in-house, and is explicitly designed as a check on any single evaluator's blind spots. [Section 5-GWWC]

**[INFERENCE] — what an information-only, non-recommending platform should adopt:**
- Contextualize any ratio it does show (overhead, admin cost, whatever) by sector and organization size rather than a single universal threshold — DZI's flat 30% cutoff treats a €50k local Verein and a €50M international NGO identically, which is exactly the kind of category error GiveWell's "doctor" analogy is pointing at.
- Make uncertainty a first-class, visible property of every number — ranges or explicit caveats, not just a point estimate — and make "we don't know" or "insufficient data" a legitimate, non-penalizing state for an organization to be shown in, rather than defaulting to a low score when data is simply missing.
- Show its own reasoning/model where feasible (GiveWell's public, copyable spreadsheets are the ceiling to aim for) rather than a black-box score.
- Mark every input as either sourced (with a citation/provenance trail) or a judgment call — never blend the two silently into one output number.
- Maintain a visible, dated changelog of corrections — normalizing "we got this wrong, here's the fix" as routine rather than reputationally catastrophic.

**[INFERENCE] — what it should explicitly NOT take from GiveWell:**
- A single aggregate "recommendation" or ranked "top charities" list — that's GiveWell's actual product and is exactly the step a non-recommending platform is choosing not to take.
- Presenting moral weights (the relative value of a death vs. a year of income, etc.) as settled fact rather than a disclosed value judgment — GiveWell itself calls its own approach "not satisfactory" and "ad hoc," which is a strong signal that baking equivalent judgment calls into a supposedly neutral information layer would misrepresent them as objective.
- Silent methodology changes — GiveWell version-dates its criteria and models precisely because a moving target framed as fixed and authoritative erodes trust; equivalent versioning discipline applies to any scoring logic a transparency platform runs, even non-recommending descriptive scoring.
- Treating a single evaluator's critique of GiveWell (e.g. Happier Lives Institute's) as neutral ground truth rather than one methodological camp's position — the DACH platform should apply the same "camp-aware" labeling to any comparative claims it surfaces.

---

## Sources

**GiveWell primary pages**
- [Our Criteria | GiveWell](https://www.givewell.org/how-we-work/criteria)
- [Cost-Effectiveness | GiveWell](https://www.givewell.org/how-we-work/our-criteria/cost-effectiveness)
- [GiveWell's Cost-Effectiveness Analyses | GiveWell](https://www.givewell.org/how-we-work/our-criteria/cost-effectiveness/cost-effectiveness-models)
- [Moral Weights | GiveWell](https://www.givewell.org/how-we-work/our-criteria/cost-effectiveness/moral-weights)
- [Approaches to Moral Weights: How GiveWell Compares to Other Actors | GiveWell](https://www.givewell.org/how-we-work/our-criteria/cost-effectiveness/comparing-moral-weights)
- [Research on Programs | GiveWell](https://www.givewell.org/research/research-on-programs)
- [Criteria for Evaluating U.S. Programs | GiveWell](https://www.givewell.org/united-states/process/sources-of-evidence) (2010, self-flagged as possibly outdated)
- [Site Visits | GiveWell](https://www.givewell.org/research/site-visits)
- [Our Mistakes | GiveWell](https://www.givewell.org/about/our-mistakes)
- [Our Mistakes – December 2024 version](https://www.givewell.org/about/our-mistakes/december-2024-version)
- [Our Mistakes – April 2024 version](https://www.givewell.org/about/our-mistakes/april-2024-version)
- [Our Mistakes – 2019 version](https://www.givewell.org/about/our-mistakes/2019-version)
- [Our Mistakes as of August 27, 2015](https://www.givewell.org/about/shortcomings-august-27-2015)

**GiveWell blog**
- [The worst way to pick a charity, 2009-12-01](https://blog.givewell.org/2009/12/01/the-worst-way-to-pick-a-charity/)
- [Pitfalls of the overhead ratio, 2009-05-21](https://blog.givewell.org/2009/05/21/pitfalls-of-the-overhead-ratio/)
- [Overhead ratio tag archive](https://blog.givewell.org/category/overhead-ratio/)
- [Changes to our top charity criteria, and a new giving option, 2022-08-17](https://blog.givewell.org/2022/08/17/changes-to-top-charity-criteria/)
- [Re-evaluating the Impact of Unconditional Cash Transfers, 2024-11-12](https://blog.givewell.org/2024/11/12/re-evaluating-the-impact-of-unconditional-cash-transfers/)
- [The winners of the Change Our Mind Contest, 2022-12-15](https://blog.givewell.org/2022/12/15/change-our-mind-contest-winners/)

**Overhead myth / Pallotta**
- [BBB Wise Giving Alliance, Charity Navigator, and GuideStar Join Forces to Dispel the Charity "Overhead Myth" (press release)](https://finance.yahoo.com/news/bbb-wise-giving-alliance-charity-132604554.html)
- [2013 letter PDF (text not extractable in this pass)](https://mb.cision.com/Main/501/9429255/133588.pdf)
- [Correcting the overhead myth: How Dan Pallotta's TED Talk has begun to change the conversation](https://ideas.ted.com/correcting-the-overhead-myth-how-dan-pallottas-ted-talk-has-begun-to-change-the-conversation/)

**Criticism**
- [Hard Problems in GiveWell's Moral Weights Approach – EA Forum](https://forum.effectivealtruism.org/posts/dHZZirCrKgyhb3NEZ/hard-problems-in-givewell-s-moral-weights-approach)
- [A dozen doubts about GiveWell's numbers – Happier Lives Institute](https://www.happierlivesinstitute.org/report/a-dozen-doubts/)
- [Givewell, and its hiring process, needs serious reform – EA Forum](https://forum.effectivealtruism.org/posts/qJMjbHp9HKxT8XEhp/givewell-and-its-hiring-process-needs-serious-reform) (title confirmed only)
- [GiveWell: a case study in effective altruism, part 1](https://benjaminrosshoffman.com/givewell-case-study-effective-altruism-1/) (existence confirmed only)
- [GiveWell: a case study in effective altruism, part 6](https://benjaminrosshoffman.com/givewell-case-study-effective-altruism-6/) (existence confirmed only)

**Alternative evaluators**
- [Our Methodology - Charity Navigator](https://www.charitynavigator.org/about-us/our-methodology/)
- [Accountability & Finance - Charity Navigator](https://www.charitynavigator.org/about-us/our-methodology/ratings/accountability-finance/)
- [Rating Methodology Guide, March 2026 (PDF)](https://www.charitynavigator.org/content/dam/cn/cn/landing-pages/Rating%20Methodology%20Guide%20(Updated%20March%202026).pdf)
- [Charity Navigator Rates Nonprofits' Impact for First Time with Acquisition of Ratings Startup, ImpactMatters](https://www.prnewswire.com/news-releases/charity-navigator-rates-nonprofits-impact-for-first-time-with-acquisition-of-ratings-startup-impactmatters-301151727.html)
- [A Charity Rating Service Looks Closer at Impact, with a New Merger Backed by Gates – Inside Philanthropy](https://www.insidephilanthropy.com/home/2020-10-14-a-charity-rating-service-looks-closer-at-impact-with-a-new-merger-and-support-from-gates)
- [Our methodology | Founders Pledge](https://www.founderspledge.com/our-methodology)
- [What are impact-focused charity evaluators? | Giving What We Can](https://www.givingwhatwecan.org/what-are-impact-focused-charity-evaluators)
- [How we choose which charities to recommend | Giving What We Can](https://www.givingwhatwecan.org/how-we-choose-which-charities-to-recommend) (URL confirmed only)
- [Why and how GWWC evaluates the evaluators | Giving What We Can](https://www.givingwhatwecan.org/why-and-how-gwwc-evaluates-the-evaluators) (URL confirmed only)
- [Die 7 Siegel-Standards – DZI](https://www.dzi.de/spendenberatung/spenden-siegel/die-7-siegel-standards/)
- [DZI-Konzept Werbe- und Verwaltungsausgaben (PDF)](https://www.dzi.de/wp-content/pdfs_Spenderberatung/DZI-Konzept_W+V_2019.pdf)
