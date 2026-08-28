# Datenmodell v0.2 — Organisations-Record (Pilot „Nepal Flut 2026")

**Stand:** 2026-08-28 · **Status:** Entwurf, entstanden aus dem Pilot-Datensatz. Feldnamen EN (Handoff-Entscheidung 4, als Annahme übernommen). Maschinenlesbar: `schema/org.schema.json` (JSON Schema 2020-12), Beispiel: `schema/example-org.json`.

## Grundprinzip: jeder Fakt ist ein `datum`

```json
{ "value": ..., "source_url": "...", "retrieved_at": "YYYY-MM-DD", "verification": "...", "quote": "...", "note": "..." }
```

| Feld | Bedeutung |
|---|---|
| `value` | der Fakt; `null` wenn nach echter Suche nicht gefunden (dann zusätzlich Pfad in `data_gaps`) |
| `source_url` | URL, unter der der Wert steht. Nie eine Homepage, wenn ein tieferer Link existiert |
| `retrieved_at` | Abrufdatum. Daten altern; das Datum ist Teil der Information |
| `verification` | `self_reported` (eigene Website/Bericht) · `register_confirmed` (amtliches Register: SWC, Charity Commission, IRS, DZI) · `externally_audited` (Wirtschaftsprüfer-Testat / geprüfter Abschluss) · `third_party_reported` (Medien, OCHA, Watchdog) · `unverified` (gefunden, aber Quelle trägt den Wert nicht wirklich) |
| `quote` | wörtlicher Beleg ≤ 40 Wörter, wenn der Wert aus Fließtext stammt |
| `note` | Einschränkungen, Formel, Kontext |
| `gap_reason` | **neu in v0.2**, nur wenn `value: null`: *warum* der Wert fehlt. `not_searched` · `searched_not_found` · `source_unreachable` · `not_public` |

### Warum `gap_reason` (v0.2)

`data_gaps` sagt, **dass** etwas fehlt. `gap_reason` sagt, **warum**. Ohne das Feld rendern vier
verschiedene Ehrlichkeits-Aussagen identisch als leere Zelle:

| Wert | Aussage | Beispiel aus dem Pilotdatensatz |
|---|---|---|
| `not_searched` | Wir haben nicht gesucht. Kein Befund über die Organisation. | `names.local_script` bei US-Orgs ohne Devanagari-Namen |
| `searched_not_found` | Wir haben gesucht und nichts gefunden. | „No published expenditure split found within research budget." |
| `source_unreachable` | Die Quelle hat nicht geantwortet. Aussage über die **Quelle**, nicht über die Organisation. | „swc.org.np was unreachable during this research session." |
| `not_public` | Die Quelle sagt selbst, dass sie den Wert nicht veröffentlicht. Aussage über das **Register**. | Register ohne Einnahmen-Split unter der Meldeschwelle |

Die Reihenfolge ist bewusst: eine unerreichbare Quelle kann uns nicht sagen, was sie veröffentlicht,
deshalb gewinnt `source_unreachable` gegen `not_public`, wenn beides auf eine Notiz zutrifft.

`gap_reason` ist **nicht** required. Ein Datum mit Wert trägt keinen Grund, und ein Pflichtfeld
hätte jeden bestehenden Record ungültig gemacht. Erzwungen wird es dort, wo es zählt: die
Datenbank (`org_datum`) lässt eine Lücke ohne `note` **und** `gap_reason` nicht zu.

Die Konvention (`source_url`, ISO-Datum, typisiertes Verifizierungs-Enum, Zitat + Locator) ist bewusst an die Haus-Konvention aus ProofRun (`source`/`claim`/`evidence`) und `idea-package.schema.json` (`source_url`, `evidence_quality`) angelehnt, damit ein späterer Umzug in eine gemeinsame Vault-Struktur ohne Umbenennung geht.

## Record-Struktur

```
Org
├ org_id                 slug, stabil
├ names                  {common, legal°, local_script°, aliases[]}
├ org_type               un_agency | red_cross_movement | ingo | national_ngo | community_org |
│                        diaspora_charity | foundation | government | platform | alliance | unknown
├ hq                     {country ISO-2, city, source_url}
├ website
├ registrations[]        {registry, identifier, url, status, retrieved_at, verification, note}
│                        registry ∈ NP_SWC, NP_DAO, NP_CDO, UK_CC, UK_OSCR, US_IRS, DE_VEREINSREGISTER,
│                        DE_DZI, DE_ITZ, CH_ZEWO, AT_OSGS, IATI, UN, OTHER
├ nepal_presence         {since_year°, mode° (own_staff|partners|both|none|unknown), staff_count°, partners[]°}
├ current_response[]     {what, where[], date, amount, currency, source_url, quote, retrieved_at, verification, note}
│                        leeres Array = keine Reaktion gefunden (ist selbst Information)
├ financial_transparency {annual_report{available,url,fiscal_year,fiscal_year_end,retrieved_at},
│                         audited_financials°, iati_publisher{is_publisher,publisher_ref,source_url,retrieved_at},
│                         income°(+currency,fiscal_year,scope), expenditure°(…), program_ratio°, peer_group}
├ warnings[]             {type, source_url, date, note, retrieved_at}   — neutral gelistet, mit Quelle
├ data_gaps[]            JSON-Pfade, die nach Suche leer blieben
├ research_notes         was gesucht wurde, was mehrdeutig war
└ last_updated
```
`°` = ist ein `datum` (value + Provenienz).

## Bewusste Entscheidungen im Entwurf

1. **Overhead nur als `program_ratio` mit Formel in `note`** — nie ohne die Rechnung; Peer-Vergleich (`peer_group`) ist vorbereitet, aber in v0.1 leer. Erste belastbare Quelle: UK Charity Commission Part B / API `charityfinancialhistory` → `expenditure_charitable_expenditure / expenditure_total` (Peer-Verteilung über 347 Nepal-aktive Charities: Median 0,96, p10 0,70 — `data/raw/ukcc_bulk_extra/_summary.json`). Unter £500k Einnahmen gibt es keinen Split → `null`, kein Malus.
2. **`scope` bei Geldwerten** (`global` / `nepal_only`) — INGO-Gesamtbudget und Nepal-Länderbudget dürfen nicht verwechselt werden.
3. **`warnings[]` statt Ausschluss** — Handoff-Entscheidung 2 als Annahme: dubiose Orgs werden gelistet, Warnhinweis mit Quelle sichtbar.
4. **`current_response` ohne Wertung** — nur Was/Wo/Wann/Quelle. „Appell gestartet" ≠ „ausgezahlt"; das steht in `note`.
5. **`fiscal_year_end`** — nepalesische Orgs schließen zum Ashad-Ende (Mitte Juli), UK/US-Orgs abweichend. Ohne das Feld sind Vergleiche schief.
6. **Registrierungen als Liste** — eine Org hat oft mehrere (UK-Charity + SWC-Affiliierung + IATI-Publisher). Der IATI-Publisher-Ref (`NP-SWC-…`, `GB-CHC-…`, `US-EIN-…`) ist der beste Join-Schlüssel über Quellen hinweg.

## Was das Schema noch nicht kann (bewusst v0.1)

- Keine Zeitreihen (nur „aktuellster Wert"); für Dauerbetrieb braucht es `history[]` pro datum.
- Keine Projekt-/Aktivitätsebene (IATI-Aktivitäten als Kindobjekte) — kommt, wenn Task 1 zeigt, dass IATI für lokale Orgs trägt.
- Keine Feldbelege (Fotos/GPS) — Phase 2+ (siehe `case-studies.md`, GlobalGiving).
