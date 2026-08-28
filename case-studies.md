# Case-Studies — was wir von ERTP 2015, GiveWell und GlobalGiving übernehmen

**Stand:** 2026-08-28. Konsolidiert aus drei Recherche-Notizen mit Quell-URL pro Aussage (`data/case-studies/*.md`, englisch, ~170 Zeilen je). Die drei Kernbehauptungen (ERTP-Verbleib, GlobalGiving-Reportpflicht, GiveWell-Overhead-Argument) habe ich selbst gegengeprüft — Ergebnis jeweils unter „Gegencheck". Eigene Schlussfolgerungen sind als **[Inferenz]** markiert.

---

## 1. Earthquake Response Transparency Portal (Nepal, 2015)

### Fakten (belegt)
- **Entstehung:** 26.04.2015, einen Tag nach dem Beben, im Parkplatz vor dem Büro von Young Innovations (YIPL, Lalitpur) — Bibhusan Bista und 5–6 Kollegen; binnen ~24h live unter `earthquake.opennepal.net`. Träger: Open Nepal (Koalition aus Young Innovations, Freedom Forum, NGO Federation of Nepal, Development Initiatives). **Finanziert ausschließlich von YIPL aus eigenen kommerziellen Einnahmen**, kein Grant. Politische Rückendeckung durch National Planning Commission und PM-Office. [odimpact.org](https://odimpact.org/case-nepal-earthquake-recovery.html)
- **Datenquellen:** OCHA FTS, Geber-Pressemitteilungen (gescraped, manuell bereinigt), Medien, PM Disaster Relief Fund, US Chamber of Commerce Foundation (Corporate-Spenden), IATI/AidStream, **Selbst-Einreichung per Formular mit redaktioneller Prüfung vor Veröffentlichung**. [ERTP About](http://earthquake.opennepal.net/about), [odimpact](https://odimpact.org/case-nepal-earthquake-recovery.html)
- **Doppelzählung — die Lösung kam erst mit v2.0:** v1 zählte nur Zuflüsse; v2 trennte **pledge / commitment / expenditure** und verkettete Transaktionen mit Referenzen, so dass man „von Primärgeber über Intermediäre bis zur umsetzenden Org" entlang der Kette browsen konnte — Traceability statt Aggregat-Deduplizierung. [Medium: ERTP 2.0 launched](https://medium.com/earthquake-response-transparency-portal/earthquake-response-transparency-portal-2-0-launched-90fcd7101871)
- **UI:** Org-Seiten (erhalten/gegeben), Projekt-Seiten, CSV-Download, Infografiken. Reichweite lt. Interview: ~$3,85 Mrd. erfasst gegenüber ~$4,4 Mrd. zugesagt — das Portal machte die Lücke selbst sichtbar. Nutzer, die niemand geplant hatte: **die Diaspora, die NGOs vor der Spende prüfte.** [odimpact](https://odimpact.org/case-nepal-earthquake-recovery.html)
- **Nachwirkung:** floss in den World Humanitarian Summit 2016 ein; IATI setzte danach ein Standardisierungsteam mit YIPL-Beteiligung auf. Journalisten nutzten die Daten binnen ~4 Monaten für Recherchen zu Ausgabenlücken. [World Bank Blog 13.10.2015](https://blogs.worldbank.org/en/endpovertyinsouthasia/post-earthquake-nepal-open-data-accountability)
- **Verbleib — Gegencheck (Wayback CDX, 28.08.2026):** 1.188 Captures, erste 09.05.2015, **letzte HTTP-200-Capture 17.01.2025**; Aktivität pro Jahr 2018–2019 ~200, 2022 sogar 241, 2024 nur 11, 2025 2. Domain löst im August 2026 nicht mehr auf. → **Das Portal lief fast zehn Jahre und ist irgendwann zwischen Jan 2025 und Aug 2026 still verschwunden** — ohne Abschaltmitteilung, ohne Retrospektive, ohne Datenarchiv (nichts gefunden). Die Recherche-Notiz hatte „wahrscheinlich offline" nur als Inferenz; der Wayback-Verlauf ist der Beleg.
- **Kontextwechsel:** Die National Reconstruction Authority — das Gegenüber, das das Portal implizit kontrollierte — wurde am 24.12.2021 aufgelöst. [Spotlight Nepal](https://www.spotlightnepal.com/2021/12/24/nepal-reconstruction-authority-dissolved-after-completing-tenure/) **[Inferenz]**: Mit dem Wegfall der NRA fiel die Nachfrage nach einem wiederaufbau-spezifischen Werkzeug; das Wayback-Profil (Abfall ab 2023) passt dazu.
- **Keine Wiederholung 2024/2025:** Für die Fluten 2024 (300+ Tote) und 2025 (Humla-GLOF, Rasuwagadhi-Brücke) existiert **kein** ERTP-Nachfolger, nur Mapping-/Datenaustausch-Infrastruktur (ReliefWeb, HDX, OSM, UNOSAT). [Wikipedia 2024](https://en.wikipedia.org/wiki/2024_Nepal_floods), [2025](https://en.wikipedia.org/wiki/2025_Nepal_floods)
- **Verwandte Systeme, nicht verwechseln:** `eq2015.npc.gov.np` (Regierungsportal, Schadens-/Bedarfsdaten, WB/DFID-finanziert, mit Kathmandu Living Labs); HRRP-4W (Shelter-Sektor, wer macht was wo, auf HDX); **AMIS `amis.mof.gov.np`** (allgemeines Aid-Tracking des Finanzministeriums seit 2010, Development Gateway, 40+ Partner, ~700 Projekte, >$6 Mrd.) — von hier nicht erreichbar, Status 2026 unverifiziert. [AidData](https://www.aiddata.org/blog/nepal-aid-management-platform-goes-public)

### Learnings
1. **Schnell live, dann tiefer** — v1 in 24h nur mit Zuflüssen, v2 mit Auszahlungen und Ketten. Genau die Sequenz, die unser Katastrophenmodus → Dauerbetrieb braucht.
2. **Das Hauptproblem war nie das Bauen, sondern das Melden** — Orgs zur Transparenz zu bewegen war schwerer als das Portal. (ODI-Barrieren: Zurückhaltung der Orgs, pledge/commitment/disbursed-Lücke, fehlende Open-Data-Kultur, Standardisierungslücken in Notlagen.)
3. **Selbstfinanzierung erklärt Start und Ende** **[Inferenz]**: kein Grant-Lag beim Start, aber auch kein Budget für Pflege, Archivierung, Sunset. Wer den Newszyklus überleben will, budgetiert Betrieb und Abschaltung von Anfang an.
4. **Es gibt keinen Nachlass.** Zehn Jahre Daten, keine Übergabe. Ein 2026-Projekt sollte seinen eigenen Sunset vorab festlegen (Datensatz + Retrospektive an eine dauerhafte Stelle).
5. **Ohne institutionelles Zuhause kein Nachleben** **[Inferenz]**: Die bleibenden Systeme sind die allgemeinen (AMIS beim Finanzministerium). Entweder von Anfang an dorthin einspeisen oder akzeptieren, dass das Produkt krisenzyklisch ist.

### Übernehmen / Nicht übernehmen
| Übernehmen | Nicht übernehmen |
|---|---|
| Transaktionsketten mit Referenzen statt Aggregat-Dedup (ist genau unser IATI-Funder-Ref-Join) | Rein pressemitteilungs-getriebene Erfassung ohne Provenienz-Feld pro Wert |
| Selbst-Einreichung mit Prüfung vor Veröffentlichung (skalierbarer Weg zu lokalen Orgs) | Start ohne Betriebs-/Sunset-Plan |
| pledge/commitment/expenditure als Drei-Stufen-Status (deckt sich mit FTS) | Bindung an eine Krise/Behörde als einzigen Nutzungsgrund |
| Diaspora als Erstnutzer explizit adressieren | — |

### Personen / Partner (alle 2026 aktiv)
- **Bibhusan Bista**, CEO Young Innovations — Initiator, öffentlicher Sprecher, weiterhin auf Konferenzen (2025). YIPL: younginnovations.com.np, info@yipl.com.np, +977 1-5536093; IATI-Publisher `NP-CRO-45995/063/064`. Aktuelles Portfolio nennt ein „Open Nepal Redesign", aber nicht mehr ERTP.
- **Open Nepal** (opennepal.net; Mitgliederseite nennt heute nur YIPL + Freedom Forum — Diskrepanz zur 2015-Koalition, offen).
- **Freedom Forum** (freedomforum.org.np, Presse-NGO, IATI `NP-DAO-27-127/062/063`).
- **NGO Federation of Nepal** (ngofederation.org, 6.781 Mitglieder, IATI `NP-DAO-27-689/063/064`) — der Schlüssel zu lokalen Orgs.
- **Development Initiatives** (devinit.org, ohne Nepal-Büro, D4D-Programm mit Asia Foundation).
- Nicht gefunden: v2.0-Launchdatum, Abschaltmitteilung, IATI-/PWYF-Evaluation, Paper. Das GitHub-Repo `younginnovations/UN-Transparency-Portal` (archiviert 05/2021) ist ein d-portal-Fork, **nicht** der ERTP-Code.

---

## 2. GiveWell — warum Cost-Effectiveness statt Overhead

### Fakten (belegt)
- **Kriterien heute:** Evidenz der Wirksamkeit, Cost-Effectiveness, Room for more funding, Transparenz. Overhead kommt **nicht vor**. [Our Criteria](https://www.givewell.org/how-we-work/criteria)
- **Das Argument gegen die Quote — Gegencheck bestätigt (Blog 01.12.2009):** *„Picking charities based on the ‚overhead ratio' is like picking your doctor by the percentage of revenue spent on medicine."* Die Quote sei vage definiert, von den Orgs selbst gemeldet, bestrafe notwendige Ausgaben (Evaluation, Planung) und sei „ultimately irrelevant to the question of whether a charity is changing lives". [The worst way to pick a charity](https://blog.givewell.org/2009/12/01/the-worst-way-to-pick-a-charity/), [Pitfalls of the overhead ratio](https://blog.givewell.org/2009/05/21/pitfalls-of-the-overhead-ratio/)
- **Branchenkonsens:** Der „Overhead Myth"-Brief 2013 von BBB Wise Giving Alliance, Charity Navigator und GuideStar: Overhead ist „a poor measure of a charity's performance". [Pressemeldung](https://finance.yahoo.com/news/bbb-wise-giving-alliance-charity-132604554.html) — also nicht EA-Randposition, sondern die drei größten US-Watchdogs selbst.
- **Was das Modell rechnet:** „cost per life or life-year changed"; Inputs = Studien-Effekte (mit External-Validity-Abschlag), volle Kosten inkl. Planung/Management/Verteilung, **Moral Weights** (explizit subjektiv), Auf-/Abschläge für Unquantifizierbares. Benchmark: **„x-mal so kosteneffektiv wie Cash Transfers"**, Schwelle für Top-Charity ~10× Cash (seit 2022). Modelle als **offene, kopierbare Google Sheets** mit Versionshistorie (Mai 2026, Nov 2025, Dez 2024 …). [Cost-Effectiveness](https://www.givewell.org/how-we-work/our-criteria/cost-effectiveness), [Models](https://www.givewell.org/how-we-work/our-criteria/cost-effectiveness/cost-effectiveness-models)
- **Moral Weights (Zahlen):** Verdopplung des Konsums einer Person für ein Jahr = 1; Tod eines Kindes < 5 abgewendet ≈ 116–134; ein Jahr Behinderung abgewendet = 2,3. Grundlage: Staff-Werte + IDinsight-Befragung (~2.000 Personen, Ghana/Kenia, 2019) + Großspender-Umfrage (~70, 2020). GiveWells eigenes Urteil: *„We do not believe our current approach is satisfactory: it is based on a number of ad hoc projects and practical adjustments rather than being grounded in a clear rationale."* [Moral Weights](https://www.givewell.org/how-we-work/our-criteria/cost-effectiveness/moral-weights)
- **Unsicherheit:** keine formalen Konfidenzintervalle auf den Publikumsseiten, sondern Punktschätzungen mit Bandbreiten („$3.500–5.500 pro gerettetem Leben") + ausdrückliche Caveats („extremely rough").
- **Evidenz-Pyramide:** RCTs als Goldstandard; Selbstberichte der Orgs werden **bedingt akzeptiert, stichprobenartig geprüft, nicht auditiert** — Site Visits existieren (2010–2025), aber ohne dokumentierte Methodik, wie ein Besuch Selbstberichte übersteuert. [Research on Programs](https://www.givewell.org/research/research-on-programs), [Site Visits](https://www.givewell.org/research/site-visits)
- **„Our Mistakes"** — gepflegte, datierte, versionierte Fehlerliste: Rohdaten ungeprüft übernommen (Bioassays 0–100 % gemittelt), Counterfactual-Abdeckung unterschätzt (15–30 % Überschätzung), Spreadsheet-Doppelzählung ($100k/$480k), Fundraising-Prognose $1 Mrd. verfehlt, Donor-E-Mails für Facebook-Audiences ohne Opt-out. [Our Mistakes](https://www.givewell.org/about/our-mistakes)
- **Kritik:** Moral-Weights-Methodik (EA-Forum, Change-Our-Mind-Contest); Happier Lives Institute „A dozen doubts" (12 technische Einwände, zusammen −26 % für AMF — aber aus dem konkurrierenden Wellbeing-Lager). [HLI](https://www.happierlivesinstitute.org/report/a-dozen-doubts/)
- **Der DACH-Kontrast:** DZI-Standard 4 deckelt Werbe- und Verwaltungsausgaben bei **30 %** mit Klassen niedrig (<10 %), angemessen (10–20 %), vertretbar (20–30 %). Das ist strukturell genau das Modell, das GiveWell und der 2013er-Brief verwerfen — **und das dominante Vertrauenssiegel im deutschen Spendenmarkt.** [DZI 7 Standards](https://www.dzi.de/spendenberatung/spenden-siegel/die-7-siegel-standards/), [DZI-Konzept W+V](https://www.dzi.de/wp-content/pdfs_Spenderberatung/DZI-Konzept_W+V_2019.pdf)
- Andere Evaluatoren: Charity Navigator Encompass (Finanzquoten noch ~32,5 % des Scores, als eine von vier Säulen; ImpactMatters 2020 übernommen), Founders Pledge (CEA/RCT/Bayes, ~20 Tage pro Org), Giving What We Can (evaluiert die Evaluatoren).

### Learnings
1. Overhead ist als **Primär**-Signal international verworfen, im DACH-Markt aber institutionalisiert. Eine reine Quote zu zeigen importiert eine Kritik, die die Quelle des Signals selbst formuliert hat. Kontext (Sektor × Größe) ist das Minimum; DZIs flache 30 % behandeln einen 50k-Verein wie eine 50M-INGO.
2. Legitimität ohne Ranking ist möglich, wenn (a) das Modell offen liegt, (b) Versionen datiert sind, (c) subjektive Inputs als solche beschriftet sind, (d) ein gemeinsamer Bezugspunkt existiert.
3. **„Wir wissen es nicht" muss ein erlaubter Zustand sein**, kein schlechter Score. GiveWell sagt offen, was nicht auditiert ist.
4. Ein **Fehlerlog** ist ein konkreter, kopierbarer Mechanismus, kein Wert-Statement.

### Übernehmen / Nicht übernehmen
| Übernehmen | Nicht übernehmen |
|---|---|
| Quoten nur kontextualisiert (Peer-Gruppe Sektor + Größe) — passt zu unserem `peer_group`-Feld | Ein aggregierter Empfehlungs-Score oder eine „Top-Liste" |
| Unsicherheit als sichtbare Eigenschaft jeder Zahl; `null` + `data_gaps` als legitimer Zustand | Moral Weights (oder irgendeine Werte-Gewichtung) als Fakt |
| Provenienz pro Input: „belegt" vs. „Einschätzung" nie stillschweigend vermischt — ist unser `verification`-Enum | Stille Methodikänderungen — Scoring-Logik (auch deskriptive) muss versioniert sein |
| Datierter, öffentlicher Korrektur-Changelog | Kritik eines Lagers (HLI) als neutrale Wahrheit |
| Selbstberichte als „provisorisch, stichprobengeprüft" kennzeichnen — exakt so, wie es ist | — |

---

## 3. GlobalGiving — wie Last-Mile-Verifizierung mechanisch funktioniert

### Fakten (belegt)
- **Vetting (Compliance-Ebene):** Dokumentenprüfung, länderabhängig. International: Programmmaterial, **Referenzschreiben** (Funder/Community-Partner, nicht Familie/Board, < 3 Monate alt), **staatliche Registrierungsbescheinigung**, Gründungsdokument mit Auflösungsklausel, **2 Jahre Finanzberichte** (auditiert oder nicht) + Budget, Bankkonto auf Org-Namen, Staff/Board-Liste. Anti-Terror-Screening, Prüfung der Funder-Historie. Entscheidung in 2–3 Wochen. **Re-Vetting mindestens alle 2 Jahre.** 175+ Länder. Ablehnungsquote: nicht publiziert. [Application Documents](https://www.globalgiving.org/nonprofit-application-documents/), [How we vet](https://www.globalgiving.org/learn/how-globalgiving-vets-nonprofits/), [Legitimacy FAQ](https://support.globalgiving.org/hc/en-us/articles/360026413511-How-can-I-be-sure-a-project-is-legitimate)
- **Projektberichte — Gegencheck bestätigt (Support-Artikel, 28.08.2026):** *„organizations are required to post an update for each project at least once every three months. If an organization does not meet this requirement, GlobalGiving will first issue a warning. Continued noncompliance may result in the project being removed from search results."* Berichte gehen per Mail an Spender und stehen auf der Projektseite. Reportfrequenz fließt ins Suchranking. Inhaltliche Mindeststruktur (Fotos, Kennzahlen): **nicht gefunden**. [Reporting requirements](https://support.globalgiving.org/hc/en-us/articles/360026175992-What-are-GlobalGiving-s-reporting-requirements)
- **Feldverifizierung:** „Field Travelers" (angestellt in DC, 3–6 Monate pro Einsatz, 20–50 Site Visits, plus Trainings/Workshops); kumulativ 60+ Länder, 1.000+ Besuche. Badge **„Site Visit Verified"** = jemand von GlobalGiving war dort. **GPS-/Foto-Standard: nicht gefunden.** Weitere Badges (Vetted, Effective Nonprofit ≥ 12 Effectiveness Points, Top Ranked) sind punktebasiert (GG Rewards: Engagement Points für Plattformverhalten, Effectiveness Points für Feedback-Lernschleifen; Tiers Partner 0–17 / Leader 18–35 / Superstar 36+ über 12 Monate). [Field Travelers](https://www.globalgiving.org/aboutus/who-we-are/field-travelers/), [GG Rewards](https://support.globalgiving.org/hc/en-us/articles/360026176852-What-is-GG-Rewards)
- **Disaster-Fund-Mechanik:** Nepal Flood Relief Fund 2026, Ziel $1,5 Mio., am 28.08. **$174.819 von 1.433 Spendern**; Mittel gehen an „local organizations", **keine Grantees benannt**, Zeitpunkt der ersten Grants nicht angegeben. **Gebühr Disaster Funds 15 %** (12 % + 3 %) vs. 8–10 % bei normalen Projekten. 2015-Fonds: $5,1 Mio. von 44.000+ Spendern an **86 → 89 lokale Partner**; Beispiel Tewa: 22 Freiwillige lieferten $100-Bargeld-Grants an 120 Gemeinden in 15 Distrikten **binnen 70 Tagen**. Dokumentierte Lektion: unkoordinierte Verteilung → ungleiche Versorgung. Eine konsolidierte Lessons-Learned-PDF: nicht gefunden. [Nepal Flood Relief Fund](https://www.globalgiving.org/projects/nepal-flood-relief-fund/), [Fee disaster funds](https://support.globalgiving.org/hc/en-us/articles/360033823391-What-is-the-fee-on-GlobalGiving-s-disaster-funds), [2015 reports](https://www.globalgiving.org/projects/nepal-earthquake-relief-fund/reports/)
- **IATI:** Publisher `US-EIN-300108263` seit 2012, **27.015 Aktivitäten**, 7.070 laufend, täglich aktualisiert, Commitment-Beträge pro Projekt — aber **0 % mit exakten Standorten**; ob Auszahlungen (nicht nur Commitments) publiziert werden: unbestätigt. In unserer d-portal-Zählung ist GlobalGiving mit 147 aktiven Nepal-Aktivitäten der fünftgrößte Publisher. [d-portal](https://d-portal.org/ctrack.html?publisher=US-EIN-300108263)

### Learnings
1. **Fast alles bei GlobalGiving ist Compliance-Verifizierung** (Org existiert, ist registriert, berichtet pünktlich). Echte Last-Mile-Evidenz gibt es nur episodisch (Site Visit, irgendwann, ohne Evidenzstandard) und über **Selbstberichte alle 3 Monate**, die nicht auditiert werden.
2. Der 3-Monats-Rhythmus mit Sanktion „aus der Suche entfernt" ist der eigentliche Mechanismus — nicht die Prüfung des Inhalts, sondern die **Kontinuität des Berichtens** als Signal.
3. Der Disaster-Fund-Weg zu lokalen Orgs ist real (86–89 lokale Partner 2015), aber **die Grantee-Liste wird nicht zeitnah veröffentlicht** — genau die Lücke, die unser Katastrophenmodus füllen könnte, wenn GlobalGiving die Namen liefert (IATI-Feed, täglich).
4. 15 % Gebühr auf Disaster Funds ist ein Datenpunkt, den ein Informations-Layer neutral zeigen kann — es ist öffentlich.

### Übernehmen / Nicht übernehmen
| Übernehmen | Nicht übernehmen |
|---|---|
| Die Dokumenten-Checkliste (Registrierung + Gründungsdokument + 2 Jahre Finanzen + unabhängige Referenz + 2-Jahres-Re-Vetting) als definierten Compliance-Standard — direkt als `registrations`/`financial_transparency`-Felder abbildbar | Site-Visit-Programm nachbauen (HR/Logistik aus DC — nicht reproduzierbar, Phase 2+ wenn überhaupt) |
| GlobalGivings IATI-Feed **verlinken statt neu erfassen** — mit Hinweis „Commitments, nicht verifizierte Outcomes" | Badges, die Plattformverhalten messen, als Wirkungsnachweis lesen |
| Berichtskontinuität als eigenes Signal (`last_report_date`, Frequenz) — in v0.2 des Schemas | „Vetted" als Synonym für „wirksam" |
| Gebühren/Overhead der Plattform selbst offenlegen | — |

---

## 4. Querschnitt: was die drei Fälle zusammen sagen

1. **Doppelzählung und pledge/commitment/paid** sind seit 2015 gelöst — konzeptionell. Wir müssen es nur von Tag 1 als Datenmodell haben (FTS liefert die Stufen, IATI den Funder-Ref, ERTP zeigt die Ketten-Referenz).
2. **Verifizierung ist ein Spektrum, kein Bit.** GiveWell sagt „stichprobengeprüft, nicht auditiert", GlobalGiving „Dokumente + Berichtsrhythmus + gelegentlich Besuch". Unser `verification`-Enum (`self_reported / register_confirmed / externally_audited / third_party_reported / unverified`) ist genau diese Skala — und muss so bleiben, statt zu einem Score zu kollabieren.
3. **Das Ende planen.** ERTP hatte zehn Jahre und keinen Nachlass. GiveWell versioniert alles und führt ein Fehlerlog. Wer Vertrauen aufbauen will, muss zeigen, was er falsch hatte und wo die Daten hingehen, wenn es vorbei ist.
4. **Lokale Orgs sind über Netzwerke erreichbar, nicht über Register:** NGO Federation of Nepal (6.781 Mitglieder, IATI-Publisher, ERTP-Mitträger) und GlobalGivings 89 Nepal-Grantees sind die zwei realistischen Einstiege — nicht das SWC-Register.
