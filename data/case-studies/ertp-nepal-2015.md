# Case Study: Earthquake Response Transparency Portal (Nepal, 2015)

Research notes compiled 2026-08-28. Every factual claim below carries a source URL. Statements with no locatable source are explicitly marked "not found." My own inferences (not sourced) are explicitly marked "INFERENCE."

---

## 1. Launch, URL, builders, funders

- **Trigger event**: Nepal earthquake of 25 April 2015 (magnitude 7.8) and the 12 May 2015 aftershock. The portal tracked response to both. [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html)
- **Launch speed**: Built and operational within ~24 hours of the first earthquake. Young Innovations CEO Bibhusan Bista: "On April 26, the day after the earthquake, five or six of my colleagues and I gathered in the carpark at our office, since the ground was still shaking and we couldn't go inside. And we asked ourselves: what can we do?" [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html)
- **URL**: `earthquake.opennepal.net`, publicly branded as the "Earthquake [Response] Transparency Portal" ("Earthquake Transparency Response Portal" on its own About page title). [earthquake.opennepal.net/about](http://earthquake.opennepal.net/about) (indexed copy via search; direct fetch failed — domain did not resolve for me on 2026-08-28, see §3)
- **Built by**: **Open Nepal** and **Young Innovations (YIPL)** jointly. Young Innovations (founded 2007, Lalitpur/Kathmandu, CEO Bibhusan Bista) did the primary technical development. [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html)
- **Wider partnership**: Open Nepal itself is described as a four-organization partnership: **Young Innovations, Freedom Forum, NGO Federation of Nepal, and Development Initiatives**, and these four are named as (co-)owners of the earthquake data platform. [WebSearch summary citing odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html) / [Development Initiatives search summary](https://reliefweb.int/report/nepal/aid-data-needs-and-use-cases-nepal)
- **Funding**: Funded entirely by Young Innovations itself, "from the proceeds of its more commercial activities" — i.e. the company cross-subsidized the civic-tech build from its commercial software/consulting revenue rather than from a grant. [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html)
- **Government relationship**: Not a funder, but an enabling backer — Nepal's National Planning Commission (NPC) and the then Prime Minister's office publicly supported the independent, non-state portal. [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html)
- **Infrastructure support**: The portal drew on and was informed by UN OCHA's Financial Tracking Service (FTS) infrastructure. [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html)
- A **separate but related** World Bank/DFID-funded government portal, `eq2015.npc.gov.np`, was also launched by the National Planning Commission — see §5, do not conflate the two. [ReliefWeb](https://reliefweb.int/report/nepal/open-data-portal-2015-earthquake-launched-national-planning-commission)

---

## 2. What it did mechanically

### Data sources
Per the portal's own About page and the ODI Impact case study, the portal ingested data from multiple primary and secondary sources:
- UN OCHA Financial Tracking Service (FTS) data [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html)
- Donor **press releases** — unstructured text, scraped and manually cleaned [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html)
- National and international **media reports** [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html)
- The **Prime Minister's Disaster Relief Fund** (government fund) — appears in the portal itself as a listed organization/data source. [earthquake.opennepal.net/organization/details/14933](https://earthquake.opennepal.net/organization/details/14933)
- Corporate donation data collected by the **US Chamber of Commerce Foundation** [WebSearch summary of earthquake.opennepal.net/about]
- The **IATI (International Aid Transparency Initiative) repository**, and donors were encouraged/enabled to publish via **AidStream**, a IATI-format publication tool. [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html)
- **Crowdsourced / self-submitted data**: organizations could submit their own transaction and/or project information directly into the portal via a form; submissions were then checked by the portal team and either published or sent back with clarifying questions before publication. [WebSearch summary of earthquake.opennepal.net/about] / [earthquake.opennepal.net/getInvolveForm](https://earthquake.opennepal.net/getInvolveForm)
- Ministry of Home Affairs (MoHA) data is also referenced as a source in a contemporaneous World Bank blog post. [World Bank blog, Deepa Rai, 13 Oct 2015](https://blogs.worldbank.org/en/endpovertyinsouthasia/post-earthquake-nepal-open-data-accountability)

### Data cleaning
Data was "scraped, cleaned, and standardized before publication." [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html) Beyond this general description, no source gives a step-by-step technical account of the cleaning pipeline — **not found**.

### Double-counting / donor-vs-implementer handling
This is the best-documented mechanical detail, via the portal's "2.0" upgrade:
- **Version 1** (launched within 24 hours) tracked only how much money was **coming into** Nepal — i.e. inflows/pledges. [Medium — "Earthquake Response Transparency Portal 2.0 launched"](https://medium.com/earthquake-response-transparency-portal/earthquake-response-transparency-portal-2-0-launched-90fcd7101871)
- **Version 2** expanded scope to also track **use of funds**, and — critically for double-counting — differentiated captured transactions by type: non-binding **"pledges"** vs. contractually agreed **"commitments"** vs. actual **"expenditures"** (disbursements), both in total and per organization. [Medium](https://medium.com/earthquake-response-transparency-portal/earthquake-response-transparency-portal-2-0-launched-90fcd7101871)
- To avoid double-counting money as it passed from a primary donor through intermediaries to the organization actually spending it on the ground, v2 let transactions carry **references** so a user could "browse along a funding chain from the primary provider, through potential intermediaries, to the organization that spends the funds on the ground" — i.e. traceability was handled by explicitly linking chained transactions rather than by deduplicating aggregate totals. [Medium](https://medium.com/earthquake-response-transparency-portal/earthquake-response-transparency-portal-2-0-launched-90fcd7101871)
- Exact launch date of v2.0 — **not found** (only that it followed v1 and expanded scope as above).

### UI / what it showed
- Organization-level pages (e.g. an org's total received/given, contribution list) and project-level pages (individual relief/reconstruction projects with details). Example live-indexed pages: [organization list](http://earthquake.opennepal.net/organization), [project list](http://earthquake.opennepal.net/project), a sample project — [RELRP – Rapid Enterprise Livelihood Recovery Programme](https://earthquake.opennepal.net/project/details/92), a sample organization — [1004 Foundation Inc.](http://earthquake.opennepal.net/organization/details/16340)
- A **"Get Involved" form** letting organizations submit their own data. [earthquake.opennepal.net/getInvolveForm](https://earthquake.opennepal.net/getInvolveForm)
- **CSV download** of the underlying dataset was offered for accessibility/reuse. [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html)
- Aggregated **infographics** summarizing pledged/allocated/spent relief money. [World Bank blog](https://blogs.worldbank.org/en/endpovertyinsouthasia/post-earthquake-nepal-open-data-accountability)
- Coverage included private, government, and multilateral funders; NGOs, UN agencies, and the Red Cross; both national and international entities. [WebSearch summary of earthquake.opennepal.net/about]

---

## 3. What happened afterward

- **Longevity confirmed to at least September 2016**: In an interview conducted for the ODI Impact case study, Bista describes the portal as still active as of around September 2016, saying reconstruction (and hence the portal's usefulness) "will go on for the next five years." [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html)
- **Reported scale/impact figures** (interview-sourced, no independent audit found): tracked ~US$3.85bn against a reported ~US$4.4bn in promised aid, i.e. the portal itself surfaced a pledge-vs-tracked-disbursement gap of roughly $550m. [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html)
- **When/why it ended — not conclusively found.** No source states an explicit shutdown date, a funding-ran-out announcement, or a "we are discontinuing this" post. What the research did find, which is suggestive but circumstantial:
  - On 2026-08-28, direct fetch attempts to `earthquake.opennepal.net` failed at the DNS level (`ENOTFOUND`) even though the domain and its subpages (About, project list, organization list, individual org/project pages) are still indexed by search engines. This is consistent with the site being offline/decommissioned, but I could not independently confirm via the Wayback Machine (my fetch tool was blocked from reaching `web.archive.org` in this session) — **treat "the portal is currently offline" as a probable-but-unverified inference, not a sourced fact.**
  - Young Innovations' **current** company portfolio site (younginnovations.com.np) lists a 2020s-era "Open Nepal" **redesign** project but does **not** list the Earthquake Response Transparency Portal among its current works — suggesting the earthquake portal itself is no longer treated as an active, maintained flagship product by the company, as of 2026. [younginnovations.com.np/works/all](https://younginnovations.com.np/works/all)
  - Nepal's government reconstruction body, the **National Reconstruction Authority (NRA)** — the main institutional client for "is reconstruction money being spent well" questions — was formally **dissolved on 24 December 2021** after completing its mandated tenure (at dissolution: 92% of private housing, 85% of archaeological sites, 92% of government buildings, 85% of educational buildings, 80% of health institutions reconstructed). Its remaining responsibilities passed to the Department of Urban Development and Building Construction and to the National Disaster Risk Reduction and Management Authority (NDRRMA). [Spotlight Nepal, 24 Dec 2021](https://www.spotlightnepal.com/2021/12/24/nepal-reconstruction-authority-dissolved-after-completing-tenure/) — **INFERENCE**: this dissolution is a plausible natural end-point for demand on a *reconstruction-specific* transparency tool, since the institution it was implicitly holding accountable ceased to exist, but no source directly links the NRA's dissolution to the portal's fate.
  - A GitHub repository at `younginnovations/UN-Transparency-Portal` was **archived (made read-only) on 11 May 2021**. However, on inspection its README describes it as a fork/variant of the **d-portal** project (a generic IATI data search tool), not specifically the Nepal earthquake portal — **I could not confirm this repo is the ERTP codebase; treat the name match as coincidental/unconfirmed, not evidence.** [GitHub search result](https://github.com/younginnovations/UN-Transparency-Portal)
- **Evaluation / lessons-learned documents found:**
  - **Primary**: "Nepal Earthquake Recovery," Open Data's Impact case study by Juliet McMurren and Saroj Bista, published July 2017 — the most substantial dedicated write-up located, including an explicit Enablers/Barriers framework (see §6). [odimpact.org/case-nepal-earthquake-recovery.html](https://odimpact.org/case-nepal-earthquake-recovery.html) (full PDF also exists at [odimpact.org/files/case-nepal.pdf](https://odimpact.org/files/case-nepal.pdf) but I could only retrieve it as an un-parseable binary stream, not extract additional text beyond the HTML case-study page)
  - **World Bank blog**, "In post-earthquake Nepal, open data accountability," Deepa Rai (World Bank consultant), 13 October 2015 — an early (5.5-month-out) account of impact, including a claim that Nepali journalists published investigations into aid-spending gaps using open data within about four months of the earthquake. [blogs.worldbank.org](https://blogs.worldbank.org/en/endpovertyinsouthasia/post-earthquake-nepal-open-data-accountability)
  - **Development Initiatives discussion paper**, "Aid data needs and use cases in Nepal," Conrad Zellmann (Development Initiatives) and Kishor Pradhan (independent consultant), 11 April 2018 — discusses the broader post-quake aid-data platform landscape but does **not** name or analyze ERTP specifically in the sections I could retrieve (paywalled/partial access). [devinit.org / iatistandard.org](https://iatistandard.org/en/news/discussion-paper-aid-data-needs-in-nepal/)
  - **YIPL company blog**, "YoungInnovations meets Journalists: Talk about the Earthquake Response Transparency Portal," Saroj Bista — describes a media-training/engagement event but I could not retrieve its full text (fetch failed with no output on 2026-08-28). Title and existence confirmed via search only. [blog.yipl.com.np](https://blog.yipl.com.np/yipl-meets-journalists-talk-about-the-earthquake-response-transparency-portal-c0b98490ecb6)
  - No IATI/aidtransparency.net dedicated evaluation post, no Publish What You Fund report, and no peer-reviewed academic paper specifically about ERTP were located — **not found** for all three, despite targeted searching.
  - The ODI case study reports the ERTP experience "illuminated some of the limitations of IATI reporting in emergencies" and fed into discussions at the **World Humanitarian Summit (May 2016)**, after which IATI set up a data-standardization team that included Young Innovations representatives. [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html)

---

## 4. People and organizations involved

| Name | Role | Still exists (2026)? | Source |
|---|---|---|---|
| **Bibhusan Bista** | CEO, Young Innovations; the portal's primary public spokesperson and (per his own account) initiator | Active — recent podcast/conference appearances found (2025-era) | [Nepal Entrepreneurship Forum](https://nepalentrepreneurshipforum.org/speaker/bibhusan-bista/), [YouTube interviews](https://www.youtube.com/watch?v=CIApKVRNYfs) |
| **Young Innovations Pvt. Ltd. (YIPL)** | Lead technical builder and sole funder of ERTP | **Yes, active.** Now branded "YoungInnovations," a digital agency in Lalitpur, Nepal (UI/UX, software dev, mobile, DevOps/cloud, AI/data engineering). 2025 news: shipped a Judicial Affairs Management System (JAMS) for local governments. Website: younginnovations.com.np; older/company profile: yipl.com.np; contact info@yipl.com.np, +977 1-5536093. LinkedIn exists: np.linkedin.com/company/young-innovations-pvt.-ltd. | [younginnovations.com.np/works/all](https://younginnovations.com.np/works/all), [company search summary](https://profile.yipl.com.np/) |
| **Open Nepal** | Co-creator of ERTP; described as "a hub for organizations and individuals using data for development" | **Yes, active.** Site opennepal.net is live; a "Redesigning Open Nepal" project appears in Young Innovations' current portfolio, implying ongoing/recent investment. | [opennepal.net/about-open-nepal](https://www.opennepal.net/about-open-nepal), [opennepal.net/members](https://opennepal.net/members) |
| **Freedom Forum** | Named partner in the Open Nepal coalition | **Yes, active.** Independent Nepali press-freedom/media NGO, founded 2005; website freedomforum.org.np; currently listed on Open Nepal's members page. | [freedomforum.org.np](https://freedomforum.org.np/), [opennepal.net/members](https://opennepal.net/members) |
| **NGO Federation of Nepal (NFN)** | Named partner in the Open Nepal coalition | **Yes, active.** Umbrella body of 6,781 member NGOs, established 1991, ECOSOC special consultative status. Website ngofederation.org; LinkedIn exists. Note: did **not** appear on Open Nepal's current members page when I checked it directly (see caveat below). | [ngofederation.org](https://www.ngofederation.org/) |
| **Development Initiatives (DI)** | Named partner in the Open Nepal coalition; global aid-data organization | **Yes, active** globally (devinit.org), but **does not maintain a permanent Nepal office** — works in Nepal via local partners, including the "Data for Development (D4D)" programme (with The Asia Foundation, UK-aid funded). Also did **not** appear on Open Nepal's current members page when I checked it directly. | [devinit.org — Our work in Nepal](https://devinit.org/what-we-do/where-we-work/our-work-nepal/) |
| **UN OCHA** | Provided/inspired the Financial Tracking Service (FTS) data backbone ERTP drew on | Yes, active (not further researched — outside scope) | [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html) |
| **National Planning Commission (NPC), Government of Nepal** | Publicly supported ERTP; separately ran its own portal (see §5) | Yes, active government body | [ReliefWeb](https://reliefweb.int/report/nepal/open-data-portal-2015-earthquake-launched-national-planning-commission) |

**Caveat on current Open Nepal composition**: When I fetched Open Nepal's live members page directly on 2026-08-28, it listed Young Innovations and Freedom Forum but **not** NGO Federation of Nepal or Development Initiatives — even though multiple secondary sources describe all four as the founding/owning coalition circa 2015. This could mean the partnership's formal membership list has narrowed since 2015, or simply that the members page is not exhaustive/current. **Not resolved — flagging as an open discrepancy rather than asserting either reading.**

---

## 5. Related efforts (one paragraph each, sourced)

**Nepal government's own 2015 earthquake open-data portal — `eq2015.npc.gov.np`.** Distinct from ERTP: launched by Nepal's National Planning Commission and focused on damage/needs survey data rather than donor-fund tracking. The underlying survey — covering 1.05 million buildings and 5.08 million people across 31 districts, collecting "10 TB of data and 10 million photographs" over 120 days via 3,000 surveyors — was run by Nepal's Central Bureau of Statistics together with Kathmandu Living Labs, UNOPS, HERD, and Real Solutions, funded by the **World Bank and DFID**; the NPC portal was built to make that anonymized survey dataset usable by technical and general audiences, and the system was later adapted by the NRA for reconstruction grievance-handling and informed CBS's plan to use tablets for the 2021 census. [ReliefWeb](https://reliefweb.int/report/nepal/open-data-portal-2015-earthquake-launched-national-planning-commission), [Kathmandu Living Labs](http://kathmandulivinglabs.org/our-work/earthquake-data-portal), [OECD Observatory of Public Sector Innovation](https://oecd-opsi.org/innovations/post-earthquake-digital-revolution-in-nepal/)

**National Reconstruction Authority (NRA) and its data-visualization page.** The NRA (formed 25 December 2015) was the legally mandated agency running Nepal's earthquake reconstruction; it maintained a district-level map/data-visualization page on its own site (nra.gov.np) — I located the page's existence via search but did not fetch/verify its live content in this session (fetch not attempted; scope/detail — **not found** beyond the URL). The NRA was dissolved 24 December 2021 after completing most of its mandate (see §3 for completion percentages). [Wikipedia — National Reconstruction Authority (Nepal)](https://en.wikipedia.org/wiki/National_Reconstruction_Authority_(Nepal)), [Spotlight Nepal](https://www.spotlightnepal.com/2021/12/24/nepal-reconstruction-authority-dissolved-after-completing-tenure/)

**HRRP 4W ("Who's doing What, Where") — Housing Recovery and Reconstruction Platform.** Established December 2015 to take over post-earthquake shelter-sector coordination from the Nepal Shelter Cluster. Not a donor-money tracker like ERTP, but an activity-tracking system: partner organizations submitted biweekly district-level data on what housing-reconstruction activity they were doing, where (down to the old VDC level), when, and how many beneficiaries/units, across the 14 most-affected districts; data is hosted on the UN's Humanitarian Data Exchange (HDX). [HDX dataset page](https://data.humdata.org/dataset/160625-hrrp-4w-national?force_layout=desktop)

**Aid Management Platform / Aid Management Information System (AMIS), `amis.mof.gov.np`.** Nepal's general (not earthquake-specific) government aid-tracking system, run by the Ministry of Finance. Originally set up in **2010** as the "Aid Management Platform" with UNDP, DFID, and Danish government support, and built by **Development Gateway**; tracks aid commitments, disbursements, and project activity across development partners. By the time of an AidData.org write-up, more than 40 development partners had reported nearly 700 projects into it, representing over US$6 billion in aid disbursements. It later added a COVID-19 assistance sub-portal. I was unable to directly fetch the live site during this session (connection refused from my environment) so cannot independently confirm its 2026 operating status beyond what search results show — treat "still running" as likely but not freshly verified. [AidData.org blog](https://www.aiddata.org/blog/nepal-aid-management-platform-goes-public), [amis.mof.gov.np/covid-19 (indexed)](https://amis.mof.gov.np/covid-19)

**2024/2025 Nepal flood dashboards.** Nepal suffered major flooding in **2024** (a series of monsoon floods in July, August, and September 2024 killing 300+ people, Rs 17bn+ in damage, 71 municipalities across 20 districts declared disaster zones) and further flood/GLOF events in **2025** (a Humla glacial-lake-outburst flood in May 2025; a flash flood destroying the Rasuwagadi Friendship Bridge on the Trishuli River in July 2025, with fatalities). I could **not find** a dedicated donation/fund-transparency portal analogous to ERTP for either event. What exists instead is disaster-mapping/data-exchange infrastructure: ReliefWeb disaster pages, the Humanitarian Data Exchange (HDX), OpenStreetMap community mapping activations, satellite-derived flood-extent data from UNOSAT, and Nepal's general Disaster Risk Reduction Portal/NDRRMA (the NRA's institutional successor for disaster matters) — none of which I verified specifically tracks *donation money* the way ERTP did. **This is a real gap worth flagging for a 2026 effort**, not just an absence of search results — see §6. [Wikipedia — 2024 Nepal floods](https://en.wikipedia.org/wiki/2024_Nepal_floods), [Wikipedia — 2025 Nepal floods](https://en.wikipedia.org/wiki/2025_Nepal_floods), [OpenStreetMap Wiki — Nepal Floods 2026 organised editing](https://wiki.openstreetmap.org/wiki/Organised_Editing/Activities/Nepal_Floods_2026)

---

## 6. Learnings for a 2026 donation-transparency effort

### Sourced (from the ODI Impact case study's explicit Enablers/Barriers framework, [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html), and other cited sources)

**Enablers that made ERTP possible:**
- Prior awareness of the Haiti 2010 earthquake response's transparency failures (notably the widely-reported "$500 million missing from Red Cross Haiti funds" controversy) directly motivated the Nepali team to prioritize traceability from day one. [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html)
- Government support (National Planning Commission, PM's office) for an *independent, non-state* transparency initiative — rather than the government trying to own/gatekeep the transparency function itself — appears to have been important. [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html)
- Access to existing infrastructure (UN OCHA's FTS) meant the team didn't have to build a financial-tracking data model from scratch. [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html)
- An already-existing ecosystem of data users (journalists, diaspora donors) ready to consume the data drove real usage, not just publication. [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html)

**Barriers the team hit:**
- Organizational reluctance among donors/implementers to adopt transparency standards (i.e. getting orgs to actually report/publish was harder than building the portal). [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html)
- A persistent gap between pledged, committed, and actually-disbursed funds (this is *why* v2's pledge/commitment/expenditure typing existed — it was a response to a real measurement problem, not a nice-to-have). [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html)
- Limited institutional culture around open data inside international aid organizations generally. [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html)
- Data-standardization limitations specific to emergency/crisis reporting contexts (this is also what fed back into IATI's own post-2016 reforms). [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html)

**On replicability:** Bista himself characterized the ERTP *concept* as "highly replicable," while noting the *software* would need local adaptation for a new context. [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html)

**On unexpected users:** The diaspora used the portal to vet NGOs before donating — i.e. the audience wasn't only journalists/oversight bodies but also individual donors doing due diligence, which is directly relevant to a donation-transparency product aimed at donors. [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html)

### My own inferences (unsourced — clearly marked)

- **INFERENCE**: Sequencing "launch fast on pledges/inflows only, then add the harder disbursement/use-of-funds layer once the simpler system has traction" (which is literally what v1→v2 did) is a defensible pattern to copy — it gets a usable, trust-building product live immediately after a disaster (when attention and donation velocity are highest) without waiting to solve the harder deduplication/traceability problem first.
- **INFERENCE**: Self-funding the build out of a company's own commercial revenue is a plausible explanation for both ERTP's fast launch (no grant-approval lag) and its apparent quiet fade-out later (no dedicated funding line meant no obligation or budget to formally maintain, archive, or wind it down publicly). A 2026 effort that wants to *outlast* the disaster news cycle should budget for maintenance/sunset costs from the start, not just build costs.
- **INFERENCE**: ERTP appears to have ended without a public retrospective, dataset archive, or handover note (I found none). That's a real loss of institutional knowledge and of the underlying dataset's future usability. A 2026 effort should plan its *own* eventual sunset in advance — e.g. committing to hand the dataset and a written retrospective to a permanent body (an IATI-aligned registry, a university, a national statistics office) rather than letting the domain simply lapse.
- **INFERENCE**: The clearest "successor" institutions for money-tracking in Nepal today are general-purpose government systems (AMIS/AMP at the Ministry of Finance) rather than any earthquake- or disaster-specific transparency tool. This suggests that for lasting impact, a crisis-specific transparency portal should aim to either (a) explicitly integrate with/feed data into the general-purpose national aid-tracking platform from the outset, or (b) be built by/for that platform's owner, rather than as a fully separate NGO-run site that has no institutional afterlife once the crisis fades from the news.
- **INFERENCE**: The 2024/2025 Nepal flood response's apparent lack of an ERTP-style donation-transparency portal (see §5) — despite comparable death tolls and infrastructure damage — suggests the 2015 effort was not institutionalized into a repeatable disaster-response playbook for Nepal, even domestically. This is worth investigating further before assuming "Nepal already has a template for this" — the ERTP was reportedly a bespoke, from-scratch effort in 2015 and evidently was not simply reactivated nine years later.

---

## Sources

1. [Earthquake Transparency Response Portal — About page](http://earthquake.opennepal.net/about)
2. [Earthquake Transparency Response Portal — Home](http://earthquake.opennepal.net/)
3. [Earthquake Transparency Response Portal — Project list](http://earthquake.opennepal.net/project)
4. [Earthquake Transparency Response Portal — Organization list](http://earthquake.opennepal.net/organization)
5. [Earthquake Transparency Response Portal — sample project (RELRP)](https://earthquake.opennepal.net/project/details/92)
6. [Earthquake Transparency Response Portal — sample org (1004 Foundation Inc.)](http://earthquake.opennepal.net/organization/details/16340)
7. [Earthquake Transparency Response Portal — Prime Minister's Disaster Relief Fund org page](https://earthquake.opennepal.net/organization/details/14933)
8. [Earthquake Transparency Response Portal — Get Involved form](https://earthquake.opennepal.net/getInvolveForm)
9. [Medium — "Earthquake Response Transparency Portal 2.0 launched"](https://medium.com/earthquake-response-transparency-portal/earthquake-response-transparency-portal-2-0-launched-90fcd7101871)
10. [Open Data's Impact — "Nepal Earthquake Recovery" case study (McMurren & Bista, July 2017)](https://odimpact.org/case-nepal-earthquake-recovery.html)
11. [Open Data's Impact — full case study PDF](https://odimpact.org/files/case-nepal.pdf)
12. [OECD Observatory of Public Sector Innovation — "Post-earthquake digital revolution in Nepal"](https://oecd-opsi.org/innovations/post-earthquake-digital-revolution-in-nepal/)
13. [ReliefWeb — "Public calls for better data and traceability in response to Nepal earthquake"](https://reliefweb.int/report/nepal/public-calls-better-data-and-traceability-response-nepal-earthquake)
14. [ReliefWeb — "Open Data Portal for 2015 Earthquake, launched by National Planning Commission"](https://reliefweb.int/report/nepal/open-data-portal-2015-earthquake-launched-national-planning-commission)
15. [Kathmandu Living Labs — Nepal Earthquake Data Portal](http://kathmandulivinglabs.org/our-work/earthquake-data-portal)
16. [2015 Nepal Earthquake Open Data Portal — eq2015.npc.gov.np](https://eq2015.npc.gov.np/)
17. [World Bank Blog — "In post-earthquake Nepal, open data accountability" (Deepa Rai, 13 Oct 2015)](https://blogs.worldbank.org/en/endpovertyinsouthasia/post-earthquake-nepal-open-data-accountability)
18. [IATI Standard — "Discussion paper: Aid data needs in Nepal"](https://iatistandard.org/en/news/discussion-paper-aid-data-needs-in-nepal/)
19. [Development Initiatives — "Aid data use at country level: The example of Nepal"](https://devinit.org/blog/aid-data-use-country-level-example-nepal/)
20. [Development Initiatives — "Our work in Nepal"](https://devinit.org/what-we-do/where-we-work/our-work-nepal/)
21. [Open Nepal — About](https://www.opennepal.net/about-open-nepal)
22. [Open Nepal — Members page](https://opennepal.net/members)
23. [Open Nepal — Young Innovations member page](https://opennepal.net/index.php/members/younginnovations)
24. [Young Innovations — current company site, Works](https://younginnovations.com.np/works/all)
25. [Young Innovations — company profile](https://profile.yipl.com.np/)
26. [Freedom Forum Nepal — homepage](https://freedomforum.org.np/)
27. [NGO Federation of Nepal — homepage](https://www.ngofederation.org/)
28. [GitHub — younginnovations/UN-Transparency-Portal](https://github.com/younginnovations/UN-Transparency-Portal)
29. [AidData.org — "Nepal Aid Management Platform Goes Public"](https://www.aiddata.org/blog/nepal-aid-management-platform-goes-public)
30. [AMIS (Aid Management Information System) — COVID-19 sub-portal, indexed](https://amis.mof.gov.np/covid-19)
31. [HDX — HRRP 4W National dataset](https://data.humdata.org/dataset/160625-hrrp-4w-national?force_layout=desktop)
32. [Wikipedia — National Reconstruction Authority (Nepal)](https://en.wikipedia.org/wiki/National_Reconstruction_Authority_(Nepal))
33. [Spotlight Nepal — "Nepal Reconstruction Authority Dissolved After Completing Tenure" (24 Dec 2021)](https://www.spotlightnepal.com/2021/12/24/nepal-reconstruction-authority-dissolved-after-completing-tenure/)
34. [Wikipedia — 2024 Nepal floods](https://en.wikipedia.org/wiki/2024_Nepal_floods)
35. [Wikipedia — 2025 Nepal floods](https://en.wikipedia.org/wiki/2025_Nepal_floods)
36. [OpenStreetMap Wiki — Organised Editing/Activities/Nepal Floods 2026](https://wiki.openstreetmap.org/wiki/Organised_Editing/Activities/Nepal_Floods_2026)
37. [YIPL Blog — "YoungInnovations meets Journalists: Talk about the Earthquake Response Transparency Portal" (title/existence only, full text not retrieved)](https://blog.yipl.com.np/yipl-meets-journalists-talk-about-the-earthquake-response-transparency-portal-c0b98490ecb6)

**Not found despite targeted search**: exact ERTP v2.0 launch date; an explicit shutdown/discontinuation announcement or date for ERTP; any dedicated IATI/aidtransparency.net evaluation post about ERTP specifically; any Publish What You Fund report on ERTP; any peer-reviewed academic paper specifically analyzing ERTP; live-content verification of amis.mof.gov.np and nra.gov.np's data-visualization page in 2026 (both fetch attempts failed from my environment); a donation-transparency portal for the 2024/2025 Nepal floods analogous to ERTP.
