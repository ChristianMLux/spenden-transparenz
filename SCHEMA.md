# Datenmodell v0.5 — Organisations-Record (Pilot „Nepal Flut 2026")

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

### Warum jede Organisation einen `donation_channel` bekommt (v0.5)

Ein Nutzertest hat die Lücke gefunden, die keine Datenqualitätsprüfung findet: jemand hat über
Google in Minuten eine offizielle nepalesische Kontonummer gefunden, während diese Seite — voller
belegter Information — keinen einzigen Weg zum Handeln anbot. „Keine Empfehlung" war als „keine
Spendenbuttons" umgesetzt worden. Das sind zwei verschiedene Dinge.

`donation_channel` ist deshalb ein `datum` wie jedes andere, mit einer harten Regel im Loader:

**Die registrierbare Domain der URL muss die der Organisations-Website sein** (oder eine
Subdomain davon). `donation.nrcs.org` zu `nrcs.org` ist in Ordnung, `oxfam.org` zu
`nepal.oxfam.org` ebenfalls — dieselbe registrierte Domain, derselbe Inhaber. Alles andere wird
abgelehnt, geloggt und als Lücke gespeichert. Beim ersten Lauf über die recherchierte Datei traf
das genau einen Eintrag: CARE Nepal (`carenepal.org`) mit einem Link auf `care.org` — das ist
CARE USA, eine andere juristische Person in einem anderen Land. Wer diesem Link folgt, spendet an
eine Organisation, die diese Seite nie genannt hat.

Die abgelehnte URL landet **nirgends** in der Datenbank: nicht als Wert, nicht als Quelle, und
auch nicht zitiert in der Notiz. Sie steht im Log, wo ein Betreiber sie sieht und niemand sie
anklicken kann.

**Kontonummern werden nirgends gespeichert.** Ein `donation_channel` ist ein Link, keine
Zahlungsdaten — auch dann nicht, wenn die Quellseite eine IBAN oder ein QR-Bild zeigt. Ein Test
prüft das gegen jedes Feld jedes Datums.

| Feld | Bedeutung |
|---|---|
| `value` | URL der offiziellen Spendenseite, oder `null` |
| `channel_type` | `donation_page` (Online-Formular) · `bank_transfer_page` (Seite mit Überweisungsdaten, nicht die Daten) · `platform_page` (eigene Seite auf einer Spendenplattform, von der eigenen Domain aus verlinkt) |
| `flood_specific` | `true` = Kampagne zu genau dieser Katastrophe, `false` = laufende Spendenseite |
| `verification` | immer `self_reported` — es ist die eigene Seite der Organisation |

34 der 45 Records tragen eine URL. Die übrigen 11 sind Lücken mit `gap_reason`, und sie stehen auf
dem Board an derselben Stelle und mit demselben Gewicht wie ein Link. Es gibt keine Sortierung und
keine Reihung danach, ob eine Organisation einen Spendenweg hat: das Feld ist ein Weg zum Handeln,
keine Empfehlung.

Neu als Record: der **Prime Minister Disaster Relief Fund** (`org_type: government`, HQ NP). Der
staatliche Fonds war das offensichtlichste Ziel überhaupt und das einzige, das diese Seite nie
genannt hat. Er steht jetzt als Record wie jeder andere da — mit denselben Lücken, derselben
Provenienz, ohne Sonderbehandlung.

### Warum die Klassifikation im Record steht (v0.4)

`current_response`-Einträge tragen jetzt optional `activity_type` und `amount_basis` — dieselben
Enums wie die Datenbank. Vorher leitete der Loader beides aus Stichwörtern im Aktivitätssatz ab.
Beim Gegenlesen aller 44 Einträge waren **14 falsch**, und drei davon erfanden Geld:

| Record | Satz | abgeleitet | richtig |
|---|---|---|---|
| malteser-international | „Aktivitäten vorübergehend eingestellt" | `appeal_launched` | `presence_declared` |
| mercy-corps | „koordiniert mit Behörden" | `medical` | `coordination` |
| world-vision-nepal | „bereitet Hilfe vor" | `wash` | `presence_declared` |
| plan-international-nepal | öffentliches Statement, **kein Betrag** | `amount_basis: disbursed` | `reported` |
| wfp-nepal | Lebensmittel verteilt, **kein Betrag** | `amount_basis: released` | `reported` |
| the-rising-youth-club | „würde ausrücken", **kein Betrag** | `amount_basis: pledged` | `reported` |

`amount_basis` steht auf dem Board neben der Zahl. „disbursed" bei einer Aussage ohne Betrag ist
also die Behauptung einer Zahlung, die niemand gemeldet hat — genau die Sorte Aussage, die dieses
Produkt drei Dateien weiter im Verbatim-Gate der KI verweigert. Kein Stichwort-Mapping ist dieses
Risiko wert.

Deshalb ist die Klassifikation jetzt Daten: ein Mensch liest den Satz, der Wert steht neben dem
Satz, aus dem er stammt, und der Loader nimmt was dasteht oder fällt auf `other` / `reported`
zurück — beides behauptet nichts. Er rät nie.

Neu in `ACTIVITY_TYPE`: `coordination`. Zwei Records beschreiben Koordination mit Behörden oder
Partnern; das ist weder `logistics` noch ein Achselzucken Richtung `other`.

### Warum `nepal_presence.mode` null sein darf (v0.3)

`datum_presence_mode` war der einzige Datum-Typ im Vertrag, dessen `value` nicht null sein durfte.
Wer nicht ermitteln konnte, wie eine Organisation in Nepal arbeitet, hatte genau ein Wort dafür:
das Enum-Mitglied `unknown`. Sieben Records nutzten es — alle sieben mit `source_url: null`, alle
sieben mit `nepal_presence.mode` in ihren `data_gaps`, vier mit einer Notiz, was nicht erreichbar
war. Sie haben eine Lücke dokumentiert, im einzigen Vokabular, das das Schema hergab.

Die Datenbank hat das zu Recht abgelehnt (`ck_org_datum_provenance`: ein Wert ohne Quelle ist kein
Wert). Falsch war nicht die Regel und nicht die Recherche, sondern das Schema. Seit v0.3 ist
`value` hier nullable; die sieben Records sind echte Lücken mit `gap_reason`.

`unknown` bleibt ein gültiger Wert: „die Quelle sagt selbst, dass die Rolle unklar ist" ist eine
belegte Aussage und muss weiterhin ausdrückbar sein. Der Unterschied ist die Quelle.

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
