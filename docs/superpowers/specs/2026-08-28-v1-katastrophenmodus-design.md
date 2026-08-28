# Spec: Spenden-Transparenz v1 — „Katastrophenmodus Nepal" (Design, 2026-08-28)

## Context

Research-Phase ist abgeschlossen und gepusht (github.com/ChristianMLux/spenden-transparenz, public, MIT): Datenquellen geprobt, 44-Org-Pilotdatensatz mit Provenienz pro Wert, Case-Studies. Verdict: „Wer reagiert wo, mit welcher Quelle" ist binnen 48h aus ReliefWeb + Org-Recherche belastbar; Geldflüsse kommen Monate später; lokale Orgs sind genannt, nicht identifiziert. Jetzt wird das erste Produkt gebaut.

**Entscheidungen (Chris, 28.08.):** Stack Next.js ≥ 16.3.x + FastAPI + Postgres · v1 = Katastrophenmodus Nepal · UI DE + EN ab Tag 1 · PO-Mandat „nur Gates, sonst frei" · Hosting auf Chris' privaten Accounts (Vercel „Chris' projects" Hobby, Railway „Christian M. Lux's" Hobby) · Teams: UI/UX (Opus-Lead + 3 Sonnet), Backend (Opus-Lead + 3 Sonnet + Opus-Security-Reviewer), ich = PO mit 1 Sonnet + 1 Opus Unterstützung.

**Kein AthenaRun-Produkt:** keine Vault-Session, kein AthenaRun-Branding/UIKit/AppShell, keine Orange. Skills werden aus dieser Session (AthenaRun-rooted) geladen, weil der Skill-Hook an `AthenaRun/.claude/settings.json` hängt; das neue Repo bekommt eine eigene `CLAUDE.md`.

## Produktkern (Capabilities — stack-unabhängig)

- **Response Board** für eine Krise: Liste der reagierenden Organisationen mit Aktivität, Ort (Distrikt), Datum, wörtlichem Beleg und Quelle. Filter: Distrikt, Org-Typ, lokal/international, Verifizierungsgrad, „hat Reaktion". Sortierung Aktualität/Name. **Keine Rankings, keine Empfehlungen, keine Overhead-Charts.**
- **Org-Detailseite**: Identität, Registrierungen, Nepal-Präsenz, aktuelle Reaktionen, Finanztransparenz — jeder Wert als `datum` mit Quelle/Datum/Verifizierungsgrad; „nicht gefunden" ist ein sichtbarer, nicht-bestrafender Zustand.
- **Vertrauensflächen**: Methodik, Quellen/Lizenzen, „Stand der Daten", Korrekturen.
- **Ingestion**: ReliefWeb-Disaster-Listing → Volltext → LLM-Extraktion von Aussagen (Org × Aktivität × Ort × Datum × Zitat) mit **Verbatim-Gate** (Zitat muss wörtlich im Quelltext stehen, sonst verworfen) → Org-Matching über Aliasse → Distrikt-Auflösung (aus Aussage oder vom Report vererbt, markiert).
- **Provenienz-Invarianten** (mechanisch geprüft): jeder Wert ≠ null hat `source_url`; jeder Gap hat `note`; `data_gaps ⊇ {null-Pfade}`; Zitat ≤ 40 Wörter; kein Org-Score irgendwo.
- **Nicht in v1** (benannt, damit es nicht versehentlich gebaut wird): FTS-„Zusage→Auszahlung"-Layer, UK-CC-Peer-Verteilung/Programmquote, Statement-Review-UI, Auth, Nutzerkonten, Spenden-Buttons.

## Stack Decisions (getrennt von der Architektur)

| Bereich | Wahl | Grund |
|---|---|---|
| Web | Next.js 16.3.3 (App Router, TS), Tailwind, shadcn 4.19, next-intl 4.14 (de/en), Vercel Hobby | Chris' Default; ISR/`revalidate: 60` |
| API | FastAPI 0.141, Python 3.13, async SQLAlchemy 2, Alembic, uvicorn; Railway | Probe-Skripte werden Pipeline |
| DB | **Railway Postgres** im selben Railway-Projekt, Region EU-West | eine Rechnung, ein Dashboard; CI mit Postgres-Service-Container (kein SQLite — JSONB/generated columns) |
| Pipeline | Python-Jobs als Railway-Cron-Service, `claude-sonnet-5` für Extraktion (Anthropic API, Key von Chris) | Extraktionstest: 21/21 verbatim mit Sonnet; Opus bringt nichts |
| Tooling | `uv` lokal, hash-gepinnte `requirements.txt` pro Service, ruff (120), pytest+httpx, `python-json-logger`, keine Emojis in Logs | boring, baut auf Railway-Nixpacks |
| Repo | dasselbe Repo; Trunk = `main`; Feature-Branches → PR → CI → Merge; Railway/Vercel deployen `main`, Vercel-Previews pro PR | kein `dev`-Branch nötig (Ein-Personen-Repo) |

## Repo-Layout (Ziel)

```
spenden-transparenz/
├── CLAUDE.md                      Projektkonventionen für Agents (neu)
├── docs/superpowers/specs/2026-08-28-v1-katastrophenmodus-design.md   (Spec = dieser Plan, committed)
├── apps/web/                      Next.js  [UI/UX-Team]
├── apps/api/                      FastAPI: app/{main,config,db,deps,schemas}.py, app/routers/*.py, alembic/, tests/  [Backend WP-C]
├── packages/core/                 core/{models,enums,datum,settings}.py — NUR der Backend-Lead schreibt hier
├── pipeline/                      pipeline/{cli,db,runs}.py, jobs/*.py, extract/{client,prompt,validate}.py, probes/ (bisherige scripts/, unverändert), tests/fixtures/
├── data/ schema/ machbarkeit-report.md case-studies.md orgs-nepal-2026.json   unverändert; schema/org.schema.json bleibt der Vertrag
```

## Datenmodell (Postgres, 13 Tabellen — Kurzform; Details im Spec)

- `organisations` (org_id slug PK, name_common, org_type CHECK, hq_country/city, website) — nur Filterachsen als Spalten.
- **`org_datum`** = die Provenienz-Tabelle: (org_id, path, value jsonb, value_type, currency/fiscal_year/scope, source_url, retrieved_at, quote, note, verification CHECK, **gap_reason CHECK** (`not_searched|searched_not_found|source_unreachable|not_public`, nur bei value NULL), content_hash, valid_from, superseded_at, ingestion_run_id, `is_gap` generated = value IS NULL). Unique auf (org_id, path) WHERE superseded_at IS NULL. Historie append-only per Hash-Vergleich. Loader = `validate_orgs.walk_datums()` (existiert).
- `org_alias` (alias_norm, org_id, kind) — macht Extraktion joinbar („WV Nepal" → world-vision-nepal). `org_registration`, `org_warning`.
- `disaster` (glide_id PK `ff-2026-000162-npl`, reliefweb_id `D52684`), `district` (77 Admin2 aus `data/raw/hapi/admin2_NPL.json`, Codes `NP0301`), `district_alias` (timure/syabrubesi → NP0301), `source` (Lizenz, default_verification).
- `report` (url unique, title, format, published_at, **body_text intern — nie ausgeliefert**, body_sha256, extraction_attempts), `report_source` (Publisher gesplittet), **`response_statement`** (report_id, org_id nullable = genannt-aber-unbekannt bleibt sichtbar, org_name_raw, activity, activity_type CHECK inkl. neuer Klassen `presence_declared/staff_deployed/needs_statement`, where_raw[], happened_on, amount, currency, quote, quote_offset, confidence, verification, model, prompt_version, status `auto|needs_review|approved|rejected_unverbatim`, content_hash; unique (report_id, content_hash)), `statement_district` (resolution `stated|inherited_from_report`), `ingestion_run` (job, status, counts, cost_usd, tokens, git_sha).
- Enums als TEXT + CHECK (Alembic-transaktionssicher, Enums werden wachsen). Kein Org-Score, keine Grade-Spalte — Verifizierungsfilter sind SQL über Datums.

## Pipeline (idempotente Jobs, Railway-Cron)

| Job | Quelle → Ziel | Takt |
|---|---|---|
| `seed_reference` | HAPI admin1/2 JSON + Quellenkatalog → district, source | on deploy |
| `ingest_orgs` | `data/orgs/batch-*.json` (JSON-Schema-validiert) → organisations, org_datum, registration, warning, alias | manuell/Admin |
| `ingest_reliefweb_listing` | `probe_reliefweb.current_disasters()` + `listing("(D52684)")` → disaster, report (Metadaten) | */30 min |
| `fetch_report_bodies` | reports ohne body → body_text + sha256; ≤ 1 req/2 s, ehrlicher UA | 5,35 * * * * |
| `extract_statements` | body → LLM (Sonnet, tool-schema = response_statement, prompt_version v2, Report-Distrikte als Kontext) → Verbatim-Gate (Normalisierung Whitespace/Entities/Unicode; Zahl-Tokens im Zitat, sonst amount NULL) → statements | 15 * * * * |
| `match_orgs`, `resolve_districts` | getrennt, damit neue Aliasse/Ortsnamen ohne LLM-Kosten neu matchen | nach extract |

Idempotenz-Vertrag: jeder Job öffnet `ingestion_run`, schreibt nur per Upsert auf natürliche Schlüssel, löscht nie, schließt den Run auch bei Exception; **zweiter Lauf schreibt 0 Zeilen** (E2E-Test). Gating: `MAX_REPORTS_PER_RUN=25`, `MAX_RUN_COST_USD=1.00`, `extraction_attempts ≥ 3` = dauerhaft ausgeschlossen, Cache-Key (body_sha256, prompt_version). Kosten: ~35 Reports × 4k Zeichen = Cents pro Lauf.

## API (FastAPI, ein Router pro Datei, `/v1`, read-only, public)

`health.py` (`/health`, `/health/ready`) · `disasters.py` (`/v1/disasters`, `/{glide_id}`) · `responders.py` (**`/v1/disasters/{glide_id}/responders`** — Hauptseite; Params district `^NP\d{4}$` wiederholbar, org_type, verification, hq local|international, has_response, q ≤ 80, sort latest|name, limit ≤ 100, offset) · `orgs.py` (`/v1/orgs`, `/{org_id}` inkl. Gaps, `/{org_id}/history?path=`) · `statements.py` · `meta.py` (`/districts`, `/sources`, `/enums`, `/freshness`) · `admin.py` (`POST /v1/admin/ingest/{job}` mit `X-Admin-Token`, `GET /v1/admin/runs`).

Jeder provenienztragende Wert serialisiert exakt als `datum`-Objekt des JSON-Schemas + `is_gap`; ein Gap ist `{"value": null, "is_gap": true, "note": …}` — der Key fehlt nie. Responder-Item: `{org|null, org_name_raw, statements[{activity, activity_type, districts[], happened_on, amount, quote, source{url, publisher, published_at, verification}}], counts, flags{has_register_confirmed, has_audited_financials, has_warnings}}`. Statements tragen Zitat + Link, **nie body_text**. Pagination offset/limit + `X-Total-Count` (Cursor erst > 10k). Caching: Listen `max-age=60, swr=600`, Org `300`, Meta `3600`, Admin/Health `no-store`; ETag-Middleware → 304. CORS: exakte Origins, nur GET/OPTIONS.

## Security-Minimum (Read-only-API) — Prüfliste für den Opus-Reviewer

1. Admin-Token: `secrets.compare_digest`, ≥ 32 Bytes, kein Default, Start verweigert ohne Token in `ENV=production`; kein Ingestion-Trigger ohne Token erreichbar. 2. SSRF: serverseitige Fetcher nur mit Host-Allowlist (reliefweb.int, Register-Domains); `validate_orgs.spotcheck()` bleibt CLI-only. 3. `body_text`-Leak: jedes Response-Model greppen. 4. SQL: `q` nur parametrisiert (ILIKE), kein dynamisches ORDER BY aus Strings, ruff S608. 5. Rate-Limit (`slowapi`, 60/min GET, 5/min admin, Key = erster Hop `X-Forwarded-For`, Railway-Proxy als trusted dokumentiert). 6. CORS nie `*`. 7. **Keine natürlichen Personen**: UK-CC-Trustee-Namen werden nicht ingestiert; die 7 Dateien `data/raw/ukcc_api/charitytrusteeinformation_*.json` werden aus dem öffentlichen Repo entfernt (Phase 0). 8. Secrets: `gitleaks` + `pip-audit` in CI, Railway-Variablen-Scope. Header: nosniff, no-referrer, kein Server-Banner; `/docs` bleibt öffentlich (Open-Data-API).

## Tests (Gate-Kriterium: existieren, laufen in CI auf jedem PR)

`pipeline/tests/test_extract_validate.py` (Normalisierung, Beträge, Golden-Fixture 5 Reports → 21/21 verbatim, LLM gestubbt) · `test_provenance_invariants.py` (gegen `orgs-nepal-2026.json`, 420 Knoten) · `apps/api/tests/test_contract.py` (ASGITransport gegen Postgres-Container: datum-Shape, Gap-Serialisierung, limit=1000 → 422, admin ohne Token → 401, ETag → 304, CORS, kein body_text) · `test_e2e_ingest.py` (gespeichertes Listing-HTML + Report-Seite via pytest-httpserver, gestubbter LLM; Kette läuft, zweiter Lauf = 0 neue Zeilen).

## Frontend (IA/UX)

**Datenfakten, die das Design treiben** (gemessen in `orgs-nepal-2026.json`): 46 Aussagen, 42 davon in 3 Distrikten (Rasuwa 21, Nuwakot 15, Dhading 6), 17 ohne Ortsangabe; 9 von 44 Orgs ohne Aussage; 22 von 44 ohne Finanzzahl; Programmquote 1 von 44. → **Keine Karte, keine Org×Distrikt-Matrix** (3 von 77 Distrikten gefüllt liest sich als „nichts passiert"); die Org-Seite wird um die Abwesenheit herum gestaltet, nicht um eine Tabelle voller Striche.

**Routen** (next-intl, `localePrefix: always`, default `de`; 7 Routen, ~100 statische Seiten): `/[locale]` → 308 auf die aktive Krise · `/de/krise/[crisis]` = `/en/crisis/[crisis]` (Response Board, SSG + ISR 900 s, kanonische URL — teilbare Links müssen überleben, wenn Krise #2 kommt) · `/de/organisation/[orgId]` (SSG 44×2, ISR 3600 s) · `/methodik` · `/quellen` (inkl. JSON-Download) · `/korrekturen` · `/impressum`, `/datenschutz` (Pflicht für deutschen Betreiber — **Inhalte von Chris**). Kein Suchindex, keine About-Seite, keine Auth; einzige Next-Route-Handler: `revalidateTag` (Push aus der Pipeline mit Secret).

**Response Board:** Tab A (default) = org-gruppierte Liste, 44 Zeilen mit 0–3 verschachtelten Aussagen; Tab B = chronologischer Aussagen-Stream (gleicher Filterzustand, Journalisten-Frage „was ist seit gestern passiert"). Above the fold: Krisen-Identität + GLIDE-ID mono · ein Satz Scope („zeigt, wer öffentlich eine Reaktion gemeldet hat — bewertet keine Organisation") · **Zahlenzeile** (44 Organisationen / 46 belegte Meldungen / 3 Distrikte / 9 ohne gefundene Reaktion — jede Zahl ist ein Filterlink, keine Cards, keine Icons) · Daten-Stand + Quellen-Link · Filterleiste + erste 3 Zeilen. Kleiner statischer Inline-SVG-Locator (Nepal-Umriss, 3 Distrikte, aria-hidden) statt Karte. Filter: Distrikt (inkl. „ohne Ortsangabe"), Sitz (Nepal/international), Org-Typ, Beleggrad **der Meldung**, Namenssuche; OR innerhalb, AND zwischen Gruppen; 100 % client-seitig über 44 Zeilen (nie Spinner, nie Debounce); Zustand in `searchParams` (teilbar); Chips für aktive Filter; Mobile = Bottom-Sheet. Sort: „Zuletzt gemeldet" (default), A–Z, „zuerst mit den wenigsten Daten" — **nie nach Beleggrad** (das würde nach unserer Recherchetiefe ranken). Appell vs. Durchführung: lexikalisch + filterbar, nie farblich/positionell; Beträge nie nackt („CHF 25.000.000 zugesagt — Appell, nicht als Auszahlung belegt"). Orgs ohne Reaktion bleiben in voller visueller Stärke in der Liste („Keine öffentliche Reaktionsmeldung gefunden (Stand …)" + was gesucht wurde), nie ein „0"-Badge.

**`<Datum>`-Komponente** (eine, zwei Varianten): `block` (Board, Fußzeile jeder Aussage, Provenienz immer sichtbar: „reliefweb.int · 27.08.2026 · Dritte", ganze Zeile = Link) und `inline` (Org-Seite: Wert + Chip **Icon + lokalisiertes Wort** — „Register", „Testat", „Eigenangabe", „Dritte", „ungeprüft", „nicht gefunden"; nie Icon-only, nie farb-only, nie Abkürzung — öffnet Radix **Popover**, kein Tooltip). Popover-Inhalt in fester Reihenfolge: Grad als Satz / Abrufdatum absolut + relativ / ≤ 40-Wort-Zitat als `<blockquote lang="en">` / Notiz / Quelle mit sichtbarer Domain. **Sechs Zustände:** value · value_unverified · **not_found (gleicher Kontrast und gleiche Schriftstärke wie ein gefundener Wert — die wichtigste Stilregel des Produkts)** · source_unreachable („Register nicht erreichbar (swc.org.np, 28.08.)") · not_public („wird nicht veröffentlicht" — Aussage über das Register, nicht die Org) · stale. **Kein Score, kein Meter, kein Fortschrittsring — je.** A11y: `aria-expanded`, `role="dialog"`, Escape, Fokus-Rückgabe, 44 px Touch; „Alle Quellen anzeigen"-Toggle expandiert jedes Datum (= Print-Default, Journalisten drucken).

**Schema-Folge (Backend-Phase 0):** `gap_reason` ∈ `not_searched | searched_not_found | source_unreachable | not_public` pro Datum (org.schema.json v0.2 + `org_datum.gap_reason`); ohne das Feld rendern drei verschiedene Ehrlichkeits-Aussagen identisch.

**Org-Detail (8 Abschnitte):** Header (Name, Devanagari `lang="ne"`, Aliasse, Typ, Sitz, Website, zuletzt aktualisiert — kein Score) · Reaktion auf die Flut (chronologisch, block-Datum) · Präsenz in Nepal · Registrierungen & Kennungen (Tabelle; **Zeilen mit `identifier: null` bleiben stehen** — die SWC-unerreichbar-Zeile ist die ehrlichste der Seite; IATI-Ref hervorgehoben als Join-Schlüssel) · Finanzielle Transparenz (**der leere Fall ist der gestaltete Fall**: ein Absatz „keine öffentlichen Finanzdaten gefunden; gesucht wurde …; von den 14 nepalesischen Orgs hat keine eine öffentliche Einnahmenzahl — Normalfall, kein Mangel dieser Organisation" → /methodik; wenn Daten: Währung + Geschäftsjahr + Scope ausgeschrieben, Programmquote nur mit Formel) · Öffentliche Hinweise (nur wenn `warnings[]` nicht leer; optisch klar von „ungeprüft" getrennt) · **Was wir nicht wissen** (`data_gaps` + `research_notes`, offen, kein Accordion) · „Fehler gefunden?" → /korrekturen + mailto.

**Vertrauensflächen v1:** Methodik (5 Grade je ein Satz, „keine Bewertung", Grenzen aus dem Machbarkeitsreport) · Daten-Stand-Stempel · **Korrekturen-Seite am Tag 1 mit den zwei realen Stichproben-Fehlern gesät** (NRNA since_year, UNICEF income) — PO-Entscheidung: ja · Quellen mit Lizenz + letztem Abruf + Datensatz-Download. **Null Third-Party-Requests** (selbst gehostete Fonts, keine Analytics) → kein Cookie-Banner. Später: Historie/Diffs, RSS/JSON-Feed, Fehlerformular, CSV, FTS-Layer.

**Performance/A11y-Budget:** vollstatisch, `generateStaticParams` 2×44, `use cache` + `cacheTag('crisis:…')`, on-demand `revalidateTag` aus der Pipeline; **kein Client-Fetching** (Board-Daten im RSC-Payload); Board-Payload ≤ 60 KB roh / ≤ 12 KB brotli; First-Load-JS ≤ 110 KB gz (keine Chart-/Map-/Animations-Lib, Icons einzeln importiert); LCP ≤ 1,5 s mobil, CLS ≤ 0,02, INP ≤ 150 ms; Lighthouse Perf ≥ 95 / A11y 100 / BP ≥ 95 / SEO ≥ 95 auf Board de+en + einer Org-Seite; Facets in `fieldset/legend`, `aria-live` Ergebniszahl, Skip-Link, Fokusring ≥ 3:1, Body ≥ 7:1, `hyphens:auto lang="de"`; Breakpoints base/md 768/xl 1280; einzige horizontale Scrollbox = Registrierungstabelle.

**Visual Brief (für das UI/UX-Team):** Referenzrahmen = gedrucktes Register / Zeitungs-Datenseite (OpenSanctions, ICIJ Offshore Leaks, ProPublica Nonprofit Explorer, gov.uk) — nicht Charity-Site, nicht SaaS-Landing. Typografie: Überschriften Source Serif 4 oder Literata, Fließtext/UI/Zahlen Inter oder Public Sans, `tabular-nums` überall, 6 Größen (13/15/17/21/28/40), keine Versalien, kein Letter-Spacing (deutsche Komposita). Raster 4 px; Abschnitte durch 1-px-Linie + 32 px, **keine Cards, keine Schatten**. Farben (light): bg `#FCFCFA`, surface `#FFFFFF`, ink `#1A1A18`, muted `#4A4A46`, rule `#E2E1DC`, **ein Akzent** Tinten-Blau `#1F3A5F`; Beleg-Tints **nicht als Ampel**: dokumentiert Slate `#2E4A62/#EDF1F5` (register/audited), offen Sand `#6B5B3E/#F5F1E8` (unverified/not_found), neutral = Ink (self/third_party); einziges echtes Signal Brick `#7A3B2E` ausschließlich für `warnings[]`. Dark: bg `#16161A`, ink `#EDEDE8`, Akzent `#7FA6D4`, Kontrast neu messen. Bewegung: praktisch keine (Popover 120 ms). shadcn-Inventar: button, checkbox, popover, sheet, input, badge (flach), separator, table, tabs, dropdown-menu. **Verboten:** card, accordion (→ `<details>`), dialog, alert, avatar, carousel, chart, tooltip-für-Provenienz, Gradient-Blobs, Hero-Illustration, Drei-Feature-Karten, rounded-2xl überall, Emoji, Icon pro Listeneintrag, große Akzent-Zahl mit Sparkline, Glassmorphism, Qualitäts-Pills, Fortschrittsringe, Trust-Score, **Fotos der Katastrophe oder Betroffener**.

**UI/UX Work Packages:** WP0 (Opus-Lead, vor allen Workern): Tokens, Layout-Shell, `<Datum>`, i18n-Gerüst, Typen (`lib/types.ts` aus OpenAPI), `messages/{de,en}/common.json`; interne Route `/dev/datum` mit 6 Zuständen × 2 Varianten × 2 Themes. WP1 (Sonnet A) Board: `app/[locale]/krise/[crisis]/`, `components/board/*`, `lib/filter.ts`, `board.json`. WP2 (Sonnet B) Org-Detail: `app/[locale]/organisation/[orgId]/`, `components/org/*`, `org.json`. WP3 (Sonnet C) Vertrauensseiten + Datenlayer + SEO: `methodik|quellen|korrekturen|impressum|datenschutz`, `lib/api.ts` (typed fetch + zod + cacheTag + Distrikt-/Namensnormalisierung; **Fallback auf `orgs-nepal-2026.json`/`disaster_updates.json`, solange die API nicht live ist**), `sitemap.ts`, `robots.ts`, `opengraph-image.tsx`, `pages.json`. Kollisionsregel: ein i18n-Namespace pro Worker, `common.json` nur Lead.

**UI/UX-Gates:** G0 nach WP0 — ich prüfe die 6 Datum-Zustände in beiden Themes, DE + EN, 200 % Zoom, Tastatur-Durchlauf. G1 pro WP — `next build`, `tsc --noEmit`, eslint, `@axe-core/playwright`, Lighthouse-CI-Budget. G2 Integration — DE/EN nebeneinander (deutscher String-Überlauf = Fehlermodus Nr. 1), 360 px, Tastatur-Pfad Filter → Datum → Org-Seite, Print/PDF einer Org-Seite. G3 Ehrlichkeits-Review — jede Zeichenkette gegen die Anti-Ranking-Checkliste: keine Superlative, keine Häkchen/Kreuze an Orgs, keine Sortierung/Farbe, die Qualität impliziert, „nicht gefunden" nie schwächer gestylt, jede Zahl in ≤ 2 Interaktionen bis zur Quelle.

## Team-Orchestrierung (wie ich es fahre)

**Modelle:** Leads + Security-Reviewer = `opus`; Worker = `sonnet` (Bake-off-Regel); ich (Fable) spawne nur, urteile und verifiziere Gates — nie Fable-Subagents. Meine Unterstützung: `po-scout` (sonnet: Recherche, Lesen großer Outputs, Gate-Vorprüfungen) und `po-judge` (opus: adversarial Review von Team-Lieferungen vor meinem Gate — Sceptic-Rolle).

**Vertrag Lead → Worker** (übernommen aus `agent-swarm/teams.md`): Lead bekommt Spec + Work-Package-Liste + Datei-Eigentümerschaft, spawnt Worker mit `name`, `model`, vollständiger Aufgabe, exakten Pfaden, Pflicht-Skills (Datei, die zuerst zu lesen ist) und `context7`-Gate für jede Library-API; Worker arbeiten in **eigenen git worktrees + Branches** (nie im Haupt-Checkout, nie `git stash`); Lead reviewt (Ship / Fix-first / Rethink in `REVIEW_FINDINGS.md`), merged nach `main` per PR nur nach grünem CI; Phase N+1 startet nicht vor Gate N. Kommunikation: `SendMessage`; Ergebnisse als Dateien, nicht als Prosa.

**Skills pro Rolle (aus AthenaRun geladen, absolute Pfade in den Prompts):**
- Alle: `context7-mcp` (Pflicht vor jeder Library-Nutzung), `performance-spotter`, `superpowers:test-driven-development`, `superpowers:verification-before-completion`, `superpowers:systematic-debugging`.
- UI/UX: `frontend-design:frontend-design`, `ui-quality`, `mobile-responsive`, `eye-friendly-light-mode`, `neo-victorian` **nur Layer 1 ohne Brand-Zeilen**, `dataviz` (falls Charts — v1 keine), `vercel:nextjs`, `vercel:shadcn`, `app-implementer/frontend-principles.md`. **Ausgeschlossen:** `athenarun-uikit`, `branding`, der AppShell-Schritt in `app-implementer`.
- Backend: `app-implementer` (ohne AppShell-Schritt), `app-reviewer`, `security-hardening` (`references/fastapi.md`, `nextjs.md`), `railway-deploy`, `safe-refactor`.
- Security-Reviewer: `security-hardening` (BREACH-Audit), `app-reviewer/anti-patterns.md`, obige Prüfliste.

**Datei-Eigentümerschaft (Kollisionsregel):** nur der Backend-Lead schreibt `packages/core/**` und `apps/api/alembic/versions/**`; Worker stellen Model-Änderungen als Einzeiler-Request, Lead landet Migration, Worker rebasen. UI/UX-Team schreibt nur `apps/web/**`; API-Vertrag = OpenAPI-Schema aus `apps/api` (Phase 0 liefert es als Stub, damit das Web-Team parallel starten kann).

## Phasen & Gates

**Schritt 0 (ich, sofort nach Freigabe):** `railway login` + `vercel login` (Browser-Tab, Chris klickt Authorize) · Spec-Datei aus diesem Plan nach `docs/superpowers/specs/…` committen · `CLAUDE.md` im Repo · Trustee-JSONs entfernen · `ANTHROPIC_API_KEY` und `ADMIN_TOKEN` in `.env.spenden` (Chris liefert den Anthropic-Key oder ich nutze den aus `.env.platform` — **Kostenfrage → Chris**).

**Backend-Phase 0 (Lead allein):** Skeleton, `packages/core`, initiale Migration, `/health`, CI (ruff, pytest gegen Postgres-Container, gitleaks, pip-audit), `seed_reference`, OpenAPI-Stub, **Schema v0.2 (`gap_reason`) + Migration der 44 Records** (Notes → gap_reason, „SWC unerreichbar" → source_unreachable, „nicht veröffentlicht" → not_public, Rest searched_not_found).

**UI/UX-Phase 0 startet parallel** zur Backend-Phase 0 gegen den OpenAPI-Stub + JSON-Fallback; Research-Auftrag des Leads (context7 + Web): next-intl 4 App-Router-Routing, Next 16.3 `use cache`/`cacheTag`, shadcn 4 Theming ohne Cards, Radix-Popover-A11y, Lighthouse-CI-Budgets, Referenzseiten (OpenSanctions, ICIJ, ProPublica, gov.uk) — Ergebnis als `apps/web/DESIGN.md`, bevor WP0 codiert. **Gate PO-0:** `alembic upgrade head` gegen Railway-Postgres, `/health` 200, CI grün.

**Backend-Phase 1 (3 Worker parallel):** WP-A Ingestion-Core (`pipeline/jobs/{orgs,reliefweb}.py`, `runs.py`, Provenienz-Invarianten-Test) · WP-B Extraktion (`pipeline/extract/**`, `jobs/{extract,match,districts}.py`, E2E-Test) · WP-C API (`apps/api/**`, Contract-Tests).
**Gate PO-1:** `ingest_orgs` → 44 Orgs, 14 NP/30 intl, 420 Knoten, 157 mit Wert, 0 Fehler; zweiter Lauf 0 Zeilen. **PO-2:** Fixture 21/21 verbatim; Live-Lauf über die 35 Flut-Reports, `rejected_unverbatim` < 5 %; ich prüfe 10 Aussagen gegen ihre URL. **PO-3:** `/responders?district=NP0301` — jedes Feld source_url oder is_gap; bekannter Gap (NRCS income) explizit; kein body_text; 401 ohne Token; 304 beim zweiten Request. **PO-4:** Security-Review, nur blockierende Findings vor Deploy. **PO-5:** Railway-Deploy beider Services, Healthcheck grün, ein Cron-Lauf in `ingestion_run`, `/meta/freshness` < 1 h.

**UI/UX-Phasen** (Details nach Frontend-Entwurf): FE-0 Research + Designsystem-Tokens + Komponenten-Inventar gegen OpenAPI-Stub · FE-1 Response Board + `<Datum>` + i18n · FE-2 Org-Detail + Vertrauensseiten · Gates: Lighthouse ≥ 95 Perf/A11y, axe 0 Violations, visueller Review DE+EN durch mich (Screenshots), keine AI-Generik-Muster (ui-quality-Checkliste).

**Inputs von Chris (nicht blockierend für den Build, blockierend für den Launch):** Impressum-/Datenschutz-Angaben (Betreiber, Anschrift, Kontakt), Anthropic-API-Key-Quelle (eigener Key oder `.env.platform`), Domain/Naming, Freigabe zur Veröffentlichung — das einzige, was ich nicht selbst entscheide.

## Kosten (vor Start)

Anthropic Extraktion: ~35 Reports × ~5k Tokens ≈ < $0,50/Lauf, Cron 1×/h mit Cache → wenige $/Monat. Railway Hobby ~$5/Monat (API + Cron + Postgres). Vercel Hobby $0. Agent-Teams: ~9 Agents, Sonnet-Worker ~100–200k Tokens je WP, Opus-Leads mehr — Chris' Claude-Kontingent.

## Mandatory Skill Loading (vor dem ersten Edit in der Ausführung)

Ich: `superpowers:writing-plans` (Spec → Implementierungsplan), `app-architect` (geladen), `performance-spotter` (geladen), `security-hardening` beim Security-Gate, `superpowers:verification-before-completion` an jedem Gate. Team-Skills wie oben in den Prompts zitiert.

## Verification (Definition of Done v1)

1. Alle vier Testdateien laufen grün in CI; zweiter Ingestion-Lauf schreibt 0 Zeilen.
2. Gates PO-0…PO-5 mit den genannten Zahlen von mir selbst ausgeführt (Befehl + gelesene Ausgabe), nicht vom Lead berichtet.
3. Response Board auf Vercel-Preview zeigt reale Aussagen der Flut mit anklickbarer Quelle; 10 Stichproben-Zitate von mir auf der Quellseite gefunden.
4. `orgs-nepal-2026.json`-Gaps erscheinen auf Org-Seiten als „nicht gefunden", nie als 0 oder leer.
5. Lighthouse/axe-Werte protokolliert; DE und EN Screens geprüft.
6. Scope-Check: keine Ratings, keine Scores, keine Spendenbuttons, kein AthenaRun-Branding im Code (`grep -ri "FF6131\|athenarun" apps/web` = 0).
