# Machbarkeits-Report — Datenquellen für „Spenden-Transparenz", Vertical Slice Nepal

**Stand:** 2026-08-28 (2 Tage nach der Trishuli-Flut vom 26.08.) · **Frage:** Kriegen wir für Nepal Org- und Geldfluss-Daten in verwertbarer Qualität, mit Provenienz pro Datenpunkt? · **Methode:** jede Quelle wirklich angezapft (Skripte in `scripts/`, Rohdaten mit Abrufzeitstempel in `data/raw/<quelle>/`, Kennzahlen in `data/raw/<quelle>/_summary.json`). Jede Zahl hier steht in einer dieser Dateien.

## 0. Kurzantwort

**Ja, für den Dauerbetrieb (kuratierte Org-Datenbank) trägt die Datenlage — für internationale Orgs. Für lokale nepalesische Orgs trägt sie strukturell nicht, und das ist messbar: 7 % der IATI-Publisher mit Nepal-Aktivitäten sind nepalesisch registriert, und von den 1.233 Aktivitäten, die eine nationale NGO als Umsetzer nennen, tragen nur ~20 eine `NP-`-Kennung — lokale Orgs sind genannt, nicht identifiziert; das amtliche Register (SWC) ist von hier aus nicht erreichbar und publiziert keine Finanzdaten. Gegenstück: UK-Charities mit Nepal als Einsatzgebiet sind 1.150, davon 347 mit exaktem Ausgaben-Split.**

**Für den Katastrophenmodus (48–72h) liefern heute genau zwei Quellen: ReliefWeb (38 Flut-Updates binnen 48h über die Disaster-Seite, ohne API, alle von internationalen Akteuren) und die US-Watchdogs (Listen binnen 24h, 0 lokale Orgs). Die Geldfluss-Quellen (FTS, IATI) liefern 2 Tage nach dem Ereignis nichts — und werden es strukturell erst nach Monaten tun (FTS-Meldeverzug median 95–142 Tage).**

Konsequenz für das Produkt: Der Katastrophenmodus ist ein *Text-Extraktions*-Produkt (SitReps → strukturierte Aktivitäten), nicht ein Geldfluss-Produkt. Die Geldflüsse werden Wochen später als „Was ist aus den Zusagen geworden?"-Layer nachgeliefert — pledge/commitment/paid ist in FTS sauber unterscheidbar.

## 1. Ergebnis auf einen Blick

| Quelle | Zugang | Nepal-Coverage (28.08.) | Aktualität | Lokal-Anteil | Provenienz-Grad | Katastrophen-tauglich (72h)? | Verdict |
|---|---|---|---|---|---|---|---|
| **OCHA FTS** | offen, kein Key | 30 Flows 2026, $3,9M eingehend; **0 Flut-Flows, kein Emergency-Objekt für 2026** | Meldeverzug median **95 d** (2026) / **142 d** (Flut-Plan 2024) | Ziel-Orgs: 20 NGO / 7 multilateral / 2 Gov | selbstgemeldet von Gebern, OCHA-kuratiert | nein | 🟡 stark für „Zusage → Auszahlung" später, wertlos in Woche 1 |
| **IATI** (d-portal + HDX + Datastore) | d-portal/HDX offen; **Datastore mit Chris' Key läuft** | 4.494 aktive Aktivitäten (d-portal) / 4.029 (Datastore), 242 Publisher; **106 humanitarian-geflaggt**; 155 Transaktionen 2026 (111 Auszahlungen, 27 Commitments) | täglich; **2 Transaktionen seit der Flut** (Schweden→UNICEF, 28.08., nicht flutbezogen) | Publisher: 7 % NP-registriert — aber **1.233 Aktivitäten nennen eine nationale NGO als Beteiligte** (580 Refs, nur ~20 mit sauberer `NP-`-Kennung) | selbstpubliziert, Doppelzählung sichtbar (23 Titel-Dubletten); USAID schwärzt Empfänger | nein | 🟡→🟢 Dauerbetrieb: Umsetzer-Ebene ist da, aber ohne Identifier |
| **ReliefWeb** | API v2 nur mit appname für Orgs mit eigener Mail-Domain (für uns nicht möglich) → **ohne API gelöst**: Disaster-Seite + Listing-Pagination + RSS | **Disaster `ff-2026-000162-npl`: 38 Updates in 48h, 35 Volltexte** (24 Press Releases, 9 SitReps; IOM, Oxfam, Save, UNICEF, IFRC, WVI, Plan, CARE, MSF, WFP, Qatar Charity, Islamic Relief, PDC, IRDR, UNDRR …); Länder-Listing 12.950 Einträge | Stunden | 0 lokale Orgs als Publisher | third-party (Sitrep) bzw. self-reported (Org-PR) | **ja** | 🟢 die Quelle für den Katastrophenmodus — als Text |
| **HDX HAPI** | offen, selbstgenerierter Identifier | Org-Taxonomie 2.533 Orgs (1.476 National NGO), **Operational Presence Nepal = 0 Zeilen**, Funding 38 (Appeal-Ebene), Needs 0 | – | Taxonomie ja, Nepal-Daten nein | – | nein | 🔴 für Nepal leer außer Admin-Grenzen (7 Provinzen / 77 Distrikte) |
| **UK Charity Commission** | Bulk-Extracts offen (5 Dateien); **API mit Chris' Key läuft** (7 Endpunkte) | **1.150 Charities mit Nepal als Einsatzgebiet** (Area-of-Operation-Extract; Namens-Match fand nur 172), Median-Einnahmen £37k, 193 über £1M; **347 mit Ausgaben-Split (Part B)** | jährlich; 5 Jahre Historie | Diaspora-/UK-Orgs | **register_confirmed**; Programmquote exakt: Median 0,96, p10 0,70 | nein | 🟢 beste Finanzquelle **und** die Peer-Basis für Overhead-im-Kontext |
| **ProPublica / IRS 990** | offen, kein Key | 409 Treffer „nepal" | neueste Filings **2023** (4/5 Stichproben) = 1,5–2,5 Jahre alt | US-Orgs | register_confirmed | nein | 🟡 Einnahmen/Ausgaben ja; **Programmquote nicht aus API ableitbar** (kein Part-IX-Split) |
| **SWC Nepal** | **Site von hier unerreichbar** (Timeout http/https); Wayback vorhanden | strukturierte NGO-Suche existiert (`/ngo/…?ngoaff=`) mit Distrikt/Sektor/Aff-Nr.; PDF-Liste „bis FY 2075/76" (12,4 MB) | Liste 2018/19 (Snapshot 2024) | **das** Register für lokale NGOs — aber nur SWC-affiliierte, keine DAO-only-Orgs | register_confirmed (Existenz), **keine Finanzdaten öffentlich** (Quartalsberichte werden eingesammelt, nicht publiziert) | nein | 🔴 heute; 🟡 wenn erreichbar |
| **DZI / ITZ** (DE) | HTML, kein API/Download | DZI: A–Z-Liste + Org-Seiten mit Gesamteinnahmen, Sammlungseinnahmen, Verwaltungskosten-**Kategorie**, Länderschwerpunkte; ITZ: 2.048 Unterzeichner, nur Links | jährlich | DACH-Geberseite | register_confirmed (DZI prüft) | nein | 🟡 Geberland-Layer; Overhead nur als Klasse (<10 % / 10–20 % / 20–30 %) |
| **Watchdogs US** | HTML | CharityWatch (27.08., 6 Orgs), Give.org/BBB (27.08., 10 Orgs) | **< 24 h** | **0 lokale Orgs** | third-party kuratiert | ja, aber nur US-Sicht | 🟢 beweist Bedarf + Geschwindigkeit; DACH-Lücke bestätigt |
| **CERF** | Website JS-gerendert, keine API gefunden | Handoff-Zahl „$2,5M" **nicht verifizierbar** (weder cerf.un.org-HTML noch FTS noch in 17 Sitrep-Texten) | – | – | – | – | ⚪ offen |

## 2. Befunde pro Quelle

### 2.1 OCHA FTS — `scripts/probe_fts.py` → `data/raw/fts/`
- Endpunkte `/v1/public/fts/flow?countryISO3=NPL&year=2026`, `/plan/country/NPL`, `/emergency/country/NPL`. Alle Felder zu 100 % befüllt (`status`, `amountUSD`, `decisionDate`, `firstReportedDate`, Quell-/Ziel-Orgs), `budgetYear` 83 %.
- **Status-Trennung funktioniert:** 2026 = 14 paid / 12 commitment / 4 pledge. Das ist genau das Feature „Zusage ≠ Auszahlung".
- **Meldeverzug gemessen** (`firstReportedDate − decisionDate`): 2026-Flows median 95 Tage, p90 419; Vergleichskrise „Nepal Floods Response Plan 2024" (Plan 1265, 39 Flows, $27,2M): median **142 Tage**, p90 352. → In Woche 1 nach einer Katastrophe steht in FTS strukturell nichts.
- Letztes Emergency-Objekt für Nepal: **Erdbeben 2015**. Die Flut 2024 existiert nur als Plan, nicht als Emergency. Für 2026: nichts.
- Summe `amountUSD` über die 30 Flows ($59,6M) ≠ `meta.incoming.fundingTotal` ($3,9M) — die Jahres-Filterung erfasst mehrjährige Flows; für Berichte muss man `meta` benutzen, nicht summieren.

### 2.2 IATI — `scripts/probe_iati.py` → `data/raw/iati/`
- **Datastore-API:** 401 ohne Subscription-Key (kostenlos „Exploratory", Registrierung nötig). Nicht gebraucht: `d-portal.org/q.json` (kein Key) und HDX-Dataset `iati-npl` (2 CSVs, täglich, Stand 27.08. 10:18 UTC) decken alles ab.
- **Coverage:** 4.494 aktive Aktivitäten (`status_code=2`) von 242 Publishern. Top: Finnland MFA 1.060, SDC 880, AidData 296, USAID 212, **GlobalGiving 147**, Schweden 117, UNDP 88, Norad 82, BMZ 79, FCDO 78 — also Geber, nicht Umsetzer.
- **Lokal-Anteil messbar über den Publisher-Ref-Prefix:** 17 von 242 Publishern beginnen mit `NP-` (7 %): `NP-SWC-<AffNr>` (12), `NP-DAO-…`, `NP-IRD-…`, `NP-CRO-…`. IATI-Registry gesamt: 2.088 Publisher, 26 mit NP-Kennung (u. a. NGO Federation of Nepal `NP-DAO-27-689/063/064`, PHASE Nepal, CARE Nepal, Young Innovations). **Der SWC-Affiliierungs-Nr. ist der Join-Schlüssel** zwischen IATI und SWC-Register.
- **Feld-Coverage (HDX-CSV, 15.784 Zeilen):** Titel/Datum/Beträge 100 %, Beschreibung 99,8 %, `sector_code` 94,5 %; Locations-CSV 21.243 Zeilen: lat/long 100 %, `location_name` 87 %, Gazetteer-Ref **0 %** (keine Admin-Codes → Distrikt-Zuordnung nur über Koordinaten/Namen).
- **Doppelzählung sichtbar:** 23 Titel-Gruppen bei ≥ 2 Publishern (z. B. PLGSP bei SDC + Norad; USAID vs. US-GOV-11). Handhabbar per Titel-/Funder-Ref-Match, aber nur, wenn man es explizit tut.
- **Katastrophen-Reaktion:** 4 Aktivitäten mit Start ≥ 26.08. — alle EU-INTPA-Routine („under preparation"). Nichts zur Flut.
- Datenqualitäts-Artefakt: ein Publisher-Name kommt als rohes XML (`<reporting-org ref="NP-IRD-201252183"…>`) — Parser müssen damit rechnen.
- `humanitarian`-Flag ist über d-portal nicht abfragbar (0 Treffer) — dafür wäre der Datastore nötig.

**Nachtrag Datastore-API (mit Key, `scripts/probe_iati_datastore.py` → `data/raw/iati_datastore/`):**
- Solr-Endpunkte `activity/select`, `transaction/select`; Facets statt Row-Dumps, 6 Requests für alles. 4.029 aktive Nepal-Aktivitäten (Zählweise ≠ d-portal).
- **`humanitarian`: 106 true / 566 false** (Rest ohne Flag) — die 106 sind die Kandidatenliste für den Dauerbetrieb-Humanitär-Layer.
- **Publisher-Typ:** Regierung 2.383, INGO 676, Multilateral 542, nationale NGO 123. **Beteiligte (participating orgs):** 1.233 Aktivitäten nennen eine nationale NGO (Typ 22), 2.366 Aktivitäten haben einen Umsetzer (Rolle 4). 580 distinkte Refs auf diesen Aktivitäten, aber **nur ~20 mit `NP-`-Präfix** (ASK Nepal `NP-SWC-8220` allein 39×). Lokale Orgs sind in IATI also **genannt, aber nicht identifiziert** — der Join zu SWC scheitert am fehlenden Identifier, nicht an der Nennung. `NP-COA-…` ist der Regierungs-Kontenplan (org-id.guide), keine NGO-Kennung.
- **Transaktionen 2026 nach Nepal: 155** — 111 Auszahlungen (Typ 3), 27 Commitments (2), 14 Incoming (1), 3 Expenditure (4). Empfänger-Refs: `XM-DAC-21000` (EU) 27, `XM-DAC-41122` (UNICEF) 17, `NP-COA-370` 10. USAID schwärzt Empfängernamen („redacted … Foreign Aid Transparency and Accountability Act"). **Seit der Flut: 2** (Schweden → UNICEF $214k und eine Korrektur, beide 28.08., nicht flutbezogen).
- `last_updated_datetime ≥ 26.08.`: 955 Treffer — praktisch alles ADB-Massen-Republish; als „neuer Inhalt"-Signal unbrauchbar.

### 2.3 ReliefWeb — `scripts/probe_reliefweb.py` → `data/raw/reliefweb/`
- API: v1 abgeschaltet (HTTP 410), **v2 verweigert nicht freigeschaltete appnames (403)**. Der appname-Antrag (Google-Formular, seit 1.11.2025 Pflicht) verlangt eine **Org-Mailadresse** — Gmail wird explizit nicht bearbeitet, und das Projekt hat weder eine eigene Org noch läuft es unter AthenaRun. **Die API ist damit für uns keine Option — und wird nicht gebraucht.**
- **Produktiver Weg ohne API (im Skript umgesetzt):** Länderseite `/country/npl` → Disaster-Seite (`/disaster/ff-2026-000162-npl`) → Disaster-ID `D52684` → Listing `/updates?advanced-search=(D52684)&page=N` (20 pro Seite, bis leer) → pro Eintrag **Titel, Format, Quelle(n), Datum, URL strukturiert aus dem Listing** (Fill 100 %) → Report-Seite für den Volltext. Nepal-Länder-ID `PC168` (12.950 Einträge, paginierbar = volle Historie). RSS (`/updates/rss.xml?advanced-search=(PC168)`) nur für Frische, auf 20 Items gedeckelt.
- Ergebnis 28.08.: **38 Updates zur Flut, 35 distinkte Reports, alle 35 Volltexte geholt**; 24 News/Press Releases, 9 Situation Reports, 2 Sonstige; Zeitraum 26.08. 06:13 UTC bis 28.08. 12:19 UTC. Kleinere Parser-Notiz: Mehrfach-Quellen kommen als ein String („ETC / Logistics Cluster / WFP") — beim Übernehmen splitten.
- **Was binnen 48h da war:** OCHA-artige Sitreps (IOM #1, Project HOPE #1, PDC), IFRC **CHF-25-Mio-Emergency-Appeal** (27.08.; das Handoff hatte „CHF 1M" — vermutlich der DREF-Vorschuss, jetzt überholt), World Vision Category-I-Response, Oxfam (Rasuwa/Nuwakot), UNICEF („17.000 Kinder"), Save the Children, Islamic Relief, Qatar Charity ERP, Logistics-Cluster-Minutes, Australiens Zusage, IRDR/UNOSAT-Satellitendaten.
- **Extraktionstest** (5 Reports → strukturierte `{org, activity, where, date, amount, quote}`): siehe Abschnitt 3.

### 2.4 HDX HAPI — `scripts/probe_hapi.py` → `data/raw/hapi/`
- Identifier = base64(`appname:email`), selbst generiert, keine Registrierung. Paginierung sauber.
- `metadata/org`: 2.533 Orgs mit Typ (National NGO 1.476, INGO 497, unbekannt 403, Gov 72, UN 35, Local NGO 13, RC 13) — eine brauchbare **Org-Typ-Taxonomie**, global.
- Nepal: `operational-presence` (3W) **0 Zeilen**, `humanitarian-needs` 0, `funding` 38 Zeilen (nur Appeal-Ebene, zurück bis 2005), `idps` 185, Admin1 7 / Admin2 77 (Distrikt-Stammdaten mit Codes — nützlich als Referenz für `where`). Datenverfügbarkeit Nepal: IDPs, Refugees, Regen-Hazards, Konflikt-Events, Funding, Risiko, Nahrungsmittelpreise, Armut, Bevölkerung — nichts zu „wer ist wo tätig".

### 2.5 UK Charity Commission — `scripts/probe_ukcc.py` → `data/raw/ukcc/`
- API: 401 ohne Key (kostenlos, Registrierung). **Bulk-Extract ohne Key**: `publicextract.charity.zip` (398.105 Zeilen, 185.555 registriert) + `charity_annual_return_history.zip` (1.246.861 Zeilen). Einmal laden, per Nummer indexieren.
- **172 Nepal-bezogene registrierte Charities** (Namens-Match auf nepal/himalay/sherpa/gurkha/everest; Gurkha-Wohlfahrt ist darunter). Größenverteilung: 75 unter £10k, 73 unter £100k, 23 unter £1M, 1 über £1M (Gurkha Welfare Trust, £26,6M). → Die Diaspora-Charity-Welt ist **klein und lang**.
- Feld-Coverage: `latest_income`/`latest_expenditure`/Geschäftsjahresende **93 %**, Reporting-Status 100 %, Tätigkeitsbeschreibung 95 %, Website 74 %. Historie: 5 Jahre pro Charity (median 5), mit `accounts_qualified`, `date_accounts_received`, `reporting_due_date` → **Termintreue und eingeschränkte Testate sind ableitbar** — ein echtes Transparenz-Signal jenseits der Overhead-Quote.
- Nicht im Haupt-Extract: der Programm-/Verwaltungs-Split — **aber im Part-B-Extract** (siehe Nachtrag).

**Nachtrag API + weitere Bulk-Extracts (`scripts/probe_ukcc_api.py`, `scripts/probe_ukcc_bulk_extra.py`):**
- **API (Key `UK_CHARITY_COMMISSION_API_KEY`, Header `Ocp-Apim-Subscription-Key`, Pfad `/register/api/<endpoint>/<regno>/0`):** funktionieren `allcharitydetails`, `charitydetails`, `charityfinancialhistory` (5 Jahre mit **`exp_charitable_activities`, `exp_raising_funds`, `exp_governance`, `exp_grants_institution`**, `inc_donations_and_legacies`, `income_from_govt_grants/contracts` …), `charitytrusteeinformation` (Name, Ernennungsdatum, Chair), `charityareaofoperation` (Länderliste), `charitygoverningdocument` (Zwecke), `charityoverview` (Mitarbeiterzahl, Gehaltsbänder > £60k, Profi-Fundraiser-Verträge, Trustee-Vergütung). **404:** Accounts-Dokumente, Policies, Published Reports, Classification, Event History, Suche. → API = Einzel-Lookup mit Governance-Signalen; kein Suchindex.
- **Weitere Bulk-Extracts ohne Key:** `charity_area_of_operation.zip` (540.085 Zeilen), `charity_annual_return_partb.zip` (79.351 Zeilen, voller Ausgaben-/Einnahmen-Split, Assets, Reserves, `count_employees`), `charity_trustee.zip`, `charity_classification.zip`.
- **Nepal richtig gezählt:** 1.150 registrierte Hauptcharities führen **Nepal als Einsatzgebiet** — der Namens-Match (172) hatte 85 % übersehen. Median-Einnahmen £37k, 193 über £1M.
- **Programmquote exakt ableitbar:** 347 der 1.150 haben einen Part-B-Split (Pflicht nur über £500k Einnahmen); `expenditure_charitable_expenditure / expenditure_total` → Median 0,96, p10 0,70, p90 1,00. Das ist **die Peer-Verteilung für „Overhead im Kontext"** — für kleine Orgs (< £500k) gibt es keinen Split, nur Einnahmen/Ausgaben; genau das muss das Produkt als „nicht verfügbar" zeigen, nicht als schlechten Wert.

### 2.6 ProPublica / IRS 990 — `scripts/probe_propublica.py` → `data/raw/propublica/`
- 409 Treffer „nepal" (PA 69, CA 43, NY 37 …; NTEE überwiegend A23 Kultur/Ethnie, X20 religiös, Q33 internationale Hilfe).
- Stichprobe (America Nepal Medical Foundation, Nepal Youth Foundation, Himalayan Healthcare, Nepal SEEDS, Direct Relief): `totrevenue`, `totfuncexpns`, `totcntrbgfts`, `totassetsend` vorhanden; **neuestes Steuerjahr 2023 bei 4/5** → 1,5–2,5 Jahre alt. **Kein Part-IX-Split (Programm/Management/Fundraising) in der API** → Programmquote nur aus PDF/XML. `pdf_url` bei 3/5.

### 2.7 SWC Nepal — `scripts/probe_swc.py` → `data/raw/swc/`
- **Live: unerreichbar** von Deutschland aus am 28.08. (Connect-Timeout auf http/https, www/non-www). Ob Geo-Block, Überlast oder Ausfall: unbekannt.
- Wayback (837 URLs seit 2022, 136 Dokumente) zeigt, was es gibt: eine **strukturierte NGO-Suche** `swc.org.np/ngo/…?ngoaff=<Nr>` mit Filtern Distrikt (75, inkl. Rasuwa/Nuwakot), Sektor (10 Klassen), SWC-Aff-Nr., Name; eine **PDF-Liste „NGOs affiliated with SWC up to FY 2075/76"** (= 2018/19, 12,4 MB, Snapshot Feb 2024); Formulare für **Quartals-Finanzberichte NGO/INGO (XLSX)** — SWC sammelt Finanzdaten ein, publiziert sie aber nicht; SWC-Jahresbericht 2080.
- Strukturell: SWC-Affiliierung ist für nationale NGOs freiwillig (DAO-Registrierung ist das Minimum) → die Liste ist per Konstruktion eine Teilmenge. **Findability-Bias ist kein Recherche-Problem, sondern Registerdesign.**

### 2.8 DZI / ITZ (DACH-Geberseite) — `data/raw/de_watchdogs/`
- **DZI**: A–Z-Liste (HTML, paginiert; nur erste Seite geparst) + Org-Seiten `dzi.de/organisation/<slug>/` mit *Bezugsjahr, Gesamteinnahmen, Sammlungseinnahmen, Anteil Werbe- und Verwaltungskosten als **Kategorie** („niedrig" = unter 10 %), Länderschwerpunkte, Rechtsform, Gründungsjahr, Sitz*. Kein API, kein Download. Nepal auf Seite 1: ANDHERI HILFE e.V. → Overhead ist hier eine Klasse, keine Zahl — passt zum Prinzip „ein Signal unter mehreren".
- **ITZ**: 2.048 Unterzeichner, Liste nach Anfangsbuchstabe/Jahr filterbar, verlinkt auf die Transparenzseiten der Orgs. Selbst keine Finanzdaten, kein Länderfeld (0 Treffer „Nepal").

### 2.9 Watchdog-Kuration US — `data/raw/watchdogs_us/`
- **CharityWatch** (Blog, 27.08.): All Hands and Hearts, CARE, Catholic Relief Services, Direct Relief, Mercy Corps, US Fund for UNICEF.
- **Give.org / BBB** (27.08.): American Red Cross, CRS, Direct Relief, GlobalGiving, International Medical Corps, Oxfam America, Project HOPE, Save the Children, UNICEF USA, World Relief.
- Beide binnen 24h, beide **ohne eine einzige nepalesische Org**, beide mit „give to established organizations"-Rahmung. Der Katastrophenmodus existiert — als US-Produkt mit US-Blickwinkel.

### 2.10 CERF
`cerf.un.org/what-we-do/allocation/2026/country/nepal` ist JS-gerendert (HTML ohne Daten); zwei API-Vermutungen 404. Die Handoff-Zahl „$2,5M" taucht weder in FTS noch in einem der 17 ReliefWeb-Texte auf. **Status: unverifiziert.**

## 3. Extraktionstest (ReliefWeb-Text → strukturierte Aktivitäten)

Setup: 5 Flut-Reports (World Vision, Project HOPE Sitrep #1, PDC, IFRC-Appeal, Oxfam; 1.200–4.000 Zeichen) aus `data/raw/reliefweb/extraction_test_inputs.json`; ein Sonnet-Agent ohne Webzugriff extrahiert `{org, org_role, activity, activity_type, where, date, amount, currency, quote, confidence}` → `extraction_test_output.json`. Prüfung per String-Match gegen den Quelltext.

| Kennzahl | Ergebnis |
|---|---|
| Extrahierte Aussagen | 21 (WVI 6, IFRC 6, Oxfam 7, Project HOPE 1, PDC 1) |
| Zitat wörtlich im Quelltext | **21 / 21** |
| Org-Name wörtlich im Quelltext | **21 / 21** |
| Beträge belegt | 19 / 21 direkt; die 2 „Fehler" sind Formatierung („CHF 25 million" → 25000000, „$1 million" → 1000000), inhaltlich korrekt |
| Distinkte Orgs | 11 |
| `where` befüllt (nicht „unspecified") | 8 / 21 — Reports nennen Distrikte oft nur im Titel/Kontext, nicht pro Aktivität |
| `activity_type` = `other` | 7 / 21 — die Taxonomie (assessment/search_rescue/distribution/medical/shelter/wash/cash/appeal_launched/funding_committed/coordination/logistics) ist zu grob für PR-Texte |

**Verdict: Extraktion ist zuverlässig (keine Halluzination, alles zitatbelegt), das Schema braucht Nacharbeit** — Ort muss vom Report-Kontext vererbt werden (`where` = Report-Distrikte, wenn Aktivität keinen nennt), und `activity_type` braucht Klassen wie `presence_declared`, `staff_deployed`, `needs_statement`. Wichtig für die Provenienz: `appeal_launched` (IFRC CHF 25M, Oxfam $1M) wurde korrekt **nicht** als Distribution klassifiziert.

## 4. Was das für das Produkt heißt

| Frage | Antwort aus den Daten |
|---|---|
| Kann der Katastrophenmodus in 72h etwas Belastbares zeigen? | Ja — **wer hat was angekündigt/gemeldet, wo, wann, mit Quelle** (ReliefWeb-Texte + Org-PR + Watchdog-Listen). Nicht: wer hat wie viel Geld bekommen (FTS/IATI leer). |
| Wann kommt die Geld-Ebene? | FTS: median 3–5 Monate nach Entscheidung. Das ist kein Bug des Produkts, sondern ein Feature: „Von den Zusagen der ersten Woche ist nach 90 Tagen X % als paid verbucht." |
| Overhead-Quote als Signal? | **Exakt aus UK CC** (Part-B-Extract + API `charityfinancialhistory`: 347 Nepal-aktive Charities, Median 0,96) — für UK-registrierte Orgs über £500k. Darunter, bei DZI (Klasse) und US 990 (nur PDF) nur grob oder gar nicht. Peer-Kontext (Sektor + Größe) ist aus UK CC sofort baubar; für alle anderen ist „kein Split veröffentlicht" der ehrliche Wert. |
| Lokale Orgs? | IATI-Datastore: **1.233 Aktivitäten nennen eine nationale NGO** — aber fast ohne Identifier; über SWC (wenn erreichbar) Existenz + Distrikt + Sektor, **nie Finanzen**. Ehrliches Feld: „keine öffentlichen Finanzdaten auffindbar" bleibt für die Mehrheit der lokalen Orgs der Normalfall; der realistische Weg zu ihnen ist die Namens-Nennung in IATI + NGO Federation + GlobalGiving-Grantees. |
| Provenienz pro Datenpunkt? | Alle Quellen liefern URL + Datum; Verifizierungsgrad ist quellenweise festlegbar (FTS/IATI = selbstgemeldet, UK CC/IRS/DZI = register, ReliefWeb = third-party). |
| Doppelzählung? | In IATI sichtbar (23 Dubletten-Gruppen) und mit Funder-Ref auflösbar; in FTS über Flow-Ketten. Muss von Tag 1 als eigener Schritt gebaut werden — das war 2015 das Hauptproblem (siehe `case-studies.md`). |
| Was fehlt komplett? | 3W/Operational Presence für Nepal (HAPI leer), Distrikt-Codes in IATI-Locations, Finanzdaten nepalesischer NGOs, ein DACH-Watchdog-Äquivalent. |

## 5. Keys — Stand nach Rücksprache

| Dienst | Status | Was es bringt |
|---|---|---|
| ReliefWeb appname | **nicht möglich** (Org-Mail-Pflicht) und **nicht nötig** — API-freier Weg in `probe_reliefweb.py` (siehe 2.3) | – |
| IATI Datastore „Exploratory" | **läuft** — `IATI_EXPLORATORY_KEY` in `spenden-transparenz/.env.spenden` | `humanitarian`-Flag (106), Transaktionsebene (111 Auszahlungen / 27 Commitments 2026), Participating-Orgs (1.233 Aktivitäten mit nationaler NGO) — siehe 2.2 Nachtrag |
| UK Charity Commission API | **läuft** — `UK_CHARITY_COMMISSION_API_KEY` in `.env.spenden` | Einzel-Lookup: 5-Jahres-Finanzhistorie mit Ausgaben-Split, Trustees, Einsatzländer, Governance-Signale — siehe 2.5 Nachtrag. Für Statistik reichen die Bulk-Extracts |

Alle Keys werden über `common.platform_key()` gelesen: Umgebung → `./.env.spenden` → `../AthenaRun/.env.platform`. `.gitignore` deckt `.env*` ab.

## 6. Task-2-Datenqualität (Pilot-Datensatz `orgs-nepal-2026.json`)

Vier parallele Recherche-Agents (Sonnet, ≤ 6 Fetches pro Org, Regel „nichts erfinden, null + data_gap"), Batches in `data/orgs/`; zwei Records danach von mir aus vorhandenen Probe-Daten nachgetragen (GlobalGiving-Fund-Seite, IATI-Ref der NGO Federation); Merge + JSON-Schema-Validierung + Provenienz-Stichprobe via `scripts/validate_orgs.py` → `data/raw/orgs/_validation.json`.

**Bestand:** 44 Orgs (45 recherchiert, 1 Dublette Caritas Nepal), **0 Schema-Fehler**. 14 nepalesisch (HQ NP), 30 international. Typen: INGO 20, National NGO 5, Community Org 5, Diaspora-Charity 5, Red-Cross-Movement 3, UN 2, Alliance 2, Foundation 1, Platform 1. HQ: NP 14, DE 10, US 8, CH 5, GB 4, IT/FR/CZ je 1. 420 Provenienz-Knoten, 157 mit Wert.

**Feld-Coverage — lokal vs. international ist der Befund:**

| Feld | alle (44) | nepalesisch (14) | international (30) |
|---|---|---|---|
| Rechtlicher Name belegt | 84 % | 64 % | 93 % |
| Irgendeine Registernummer | 39 % | **7 %** | 53 % |
| SWC-Affiliierungsnummer | 2 % | 7 % | 0 % |
| Nepal-Präsenz seit (Jahr) | 45 % | 43 % | 47 % |
| Präsenzmodus bekannt | 82 % | 79 % | 83 % |
| **Aktuelle Flut-Reaktion belegt** | **80 %** | **79 %** | 80 % |
| Jahresbericht als Dokument | 30 % | 14 % | 37 % |
| Geprüfter Abschluss belegt | 14 % | **0 %** | 20 % |
| IATI-Publisher | 11 % | 7 % | 13 % |
| Einnahmen (Zahl + Jahr + Quelle) | 32 % | **0 %** | 47 % |
| Ausgaben | 14 % | 0 % | 20 % |
| Programmquote ableitbar | 2 % | 0 % | 3 % |
| Warnhinweise gefunden | 0 % | 0 % | 0 % |

Verifizierungsgrad über alle Knoten: unverified 266, self_reported 98, register_confirmed 35, third_party_reported 18, externally_audited 3 (unverified = überwiegend leere Werte). Häufigste Lücken: Staff-Zahl 42, Devanagari-Name 36, Programmquote 36, geprüfter Abschluss 34, Ausgaben 34, IATI 33.

**Provenienz-Stichprobe (12 %, 17 Knoten, Seed 26; direkt, bei Bot-Block Firecrawl → ScraperAPI):** 12 Seiten direkt, 5 über Firecrawl geholt (0 unerreichbar). Ergebnis: **13 Werte wörtlich auf der Quellseite, 1 über das Zitat, 3 nicht per String-Match** — manuell nachgeprüft:
- `ifrc / nepal_presence.mode = both` — Enum-Wert; die Seite belegt 343 Staff + 127.637 Volunteers + 77 Branches → **inhaltlich gestützt**, String-Match für Klassifikationen ungeeignet.
- `unicef-nepal / income = 8.263 Mrd.` — die Zahl steckt auf der Seite in einem Infogram-iframe, nicht im Text → **an dieser URL nicht maschinell verifizierbar**; Quelle zu grob (Jahresbericht-Landingpage statt PDF-Seite).
- `non-resident-nepali-association / since_year = 2003` — Homepage nennt **kein** Gründungsjahr → **Provenienz falsch** (Wert mag stimmen, die URL trägt ihn nicht).

→ **15 / 17 belegt, 1 unverifizierbar an der URL, 1 echter Provenienz-Fehler (≈ 6 %).** Das ist die Fehlerrate, die ein Review-Schritt vor Veröffentlichung abfangen muss; die Prüfung selbst ist automatisierbar (`validate_orgs.py --spotcheck`).

**Was der Datensatz zeigt:**
1. **Die Reaktion ist sichtbar, das Geld nicht.** 79 % der lokalen Orgs haben eine belegte Flut-Aktivität (Presse, eigene Posts), 0 % eine Einnahmenzahl. Bei internationalen: 77 % Reaktion, 47 % Einnahmen. Das Produktversprechen „Provenienz-markierte Information" hält; das Versprechen „Finanztransparenz" hält nur für die Hälfte der internationalen und keine der lokalen Orgs — und das *ist* die Information.
2. **Registernummern sind der Engpass** — 7 % lokal. Ohne erreichbares SWC-Register bleibt der Join IATI↔SWC↔Org theoretisch.
3. **22 von 44 Orgs ohne jede Finanzzahl** (`orgs_without_any_financial_figure`), darunter auch Malteser International, Helvetas, alle vier deutschen Nepal-Vereine und Save the Children International — teils echte Lücke, teils Recherche-Budget (≤ 6 Fetches). Für den Dauerbetrieb heißt das: die zweite Recherche-Runde pro Org muss gezielt die Register (DZI-Seite, Bundesanzeiger, UK-CC-Accounts) ansteuern, nicht die Websites.
4. **Programmquote: 1 von 44.** Overhead als „ein Signal unter mehreren" ist nur mit Registerarbeit (Accounts-PDFs) zu haben; als Massendatum existiert es nicht.
5. **Keine Warnhinweise gefunden** — keine der 44 Orgs hat eine öffentliche Regulator-/Watchdog-Warnung. Entscheidung 2 (listen + warnen) ist damit nicht getestet, nur implementiert.
6. Bekannte Unschärfen: HQ-Land bei föderierten Orgs (World Vision → CH, UNICEF → US) ist Ermessen; `scope` global vs. nepal_only ist bei INGO-Zahlen entscheidend und nicht überall gesetzt; 5 Provenienz-URLs sind für Bots gesperrt, für Menschen erreichbar.

**Verdict Task 2:** Das Schema trägt (0 Fehler, Provenienz pro Knoten funktioniert, Nulls sind ehrlich). Die Datenqualität trägt für „Wer reagiert, wo, mit welcher Quelle" — und dokumentiert für „Wie transparent ist die Org finanziell" die Lücke messbar statt sie zu verstecken.

## 7. Reproduktion

```
cd spenden-transparenz/scripts
python probe_fts.py; python probe_iati.py; python probe_hapi.py; python probe_propublica.py
python probe_ukcc.py        # lädt 2 Bulk-Zips, cached in data/raw/ukcc/
python probe_ukcc_bulk_extra.py   # + area_of_operation + Part B (Programmquote)
python probe_ukcc_api.py          # braucht UK_CHARITY_COMMISSION_API_KEY
python probe_iati_datastore.py    # braucht IATI_EXPLORATORY_KEY
python probe_swc.py         # Wayback, langsam (~10 min)
python probe_reliefweb.py   # ohne API: Disaster-Seite + Listing-Pagination
python validate_orgs.py --spotcheck 0.12
```
Kennzahlen: `data/raw/<quelle>/_summary.json`. Python 3.13, `requests`, `jsonschema`. Die Stichprobe nutzt bei Bot-Block `FIRECRAWL_API_KEY` bzw. `SCRAPER_API_KEY` aus der Umgebung oder `../AthenaRun/.env.platform` (Keys werden nicht in `data/` geschrieben).
