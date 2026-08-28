# apps/web — DESIGN.md

**Stand:** 2026-08-28 · **Status:** bindend für WP0 bis WP3 · **Autor:** UI/UX-Lead

Dieses Dokument ist die Umsetzung des Abschnitts „Frontend (IA/UX)" aus
`docs/superpowers/specs/2026-08-28-v1-katastrophenmodus-design.md`. Der Spec gewinnt bei
Widerspruch, außer wo hier unter „Abweichungen" eine Abweichung mit Begründung und Messung
protokolliert ist. Worker lesen zuerst den Spec, dann dieses Dokument, dann ihren Plan-Abschnitt.

Alle Entscheidungen tragen ihre Quelle. Bibliotheks-APIs wurden vor dem Schreiben nachgeschlagen
(context7 / Herstellerdoku), nicht aus dem Gedächtnis übernommen.

---

## 1. Entwurfsthese

**Das Produkt ist ein Register, kein Ratgeber.** Es beantwortet „wer hat öffentlich gemeldet,
etwas zu tun, wo, seit wann, mit welchem Beleg" und beantwortet ausdrücklich nicht „wem soll ich
spenden". Der visuelle Referenzrahmen ist die gedruckte Amtsseite: Linien statt Kästen, Ziffern
mit fester Breite, Fußnoten die man drucken kann.

**Das Signature-Element ist die Beleg-Marke.** Jeder Wert und jede Leerstelle trägt eine
handgezeichnete 12-px-Marke plus ein ausgeschriebenes Wort. Die Marke für „nicht gefunden" ist
genauso stark gezeichnet wie die für „Register" — ein leerer, aber vorhandener Rahmen, nie ein
Strich, nie ein Kreuz, nie ein blasses Grau. Das ist die eine Stelle, an der dieses Produkt
Haltung zeigt, und alles andere bleibt still. Es wird **keine Icon-Bibliothek installiert**
(Begründung 6.3).

**Das eine Risiko, das ich eingehe:** Die Org-Seite wird um die Abwesenheit herum gebaut, nicht um
eine Tabelle. Bei 75 % leerer Registrierungs-Kennungen (gemessen, Abschnitt 4) wäre eine Tabelle
voller Striche die ehrliche Datenlage in der unehrlichsten Form. Stattdessen ist jede leere Zeile
ein ganzer Satz darüber, wo gesucht wurde. Das kostet vertikalen Platz und ist Absicht.

---

## 2. Recherche: was die Referenzseiten lösen und was sie falsch machen

| Quelle | Übernommen | Verworfen |
|---|---|---|
| **ProPublica Nonprofit Explorer** (`projects.propublica.org/nonprofits/organizations/131760110`) | Der Satz für fehlende Daten nennt, **was es stattdessen gibt**: „Extracted financial data is not available for the forms filed in this tax period, but Form 990 documents are available for download." Genau dieses Muster für unseren Finanz-Leerfall. Außerdem: Geschäftsjahr immer ausgeschrieben („Fiscal Year Ending June"), Quelle als Satz („Form 990 data is from the IRS"), Tabellen statt Karten. | Kein Hinweis, dass die Seite nicht bewertet. Wir sagen es explizit im Scope-Satz. |
| **ICIJ Offshore Leaks** (`offshoreleaks.icij.org/nodes/80000001`) | Provenienz hängt an jeder Zeile, nicht an der Seite (Spalte „Data source", z. B. „Paradise Papers"). Datenstand als Satz: „Appleby data is current through 2014". | **Fehlende Felder als „-" oder leere Zelle.** Das ist der Fehlermodus, den unser Spec ausdrücklich verbietet. Wir schreiben aus, warum das Feld leer ist. |
| **OpenSanctions Statements** (`opensanctions.org/docs/statements/`) | Das Statement-Modell: eine atomare Aussage trägt `dataset`, `first_seen`, `last_seen`. Unser `retrieved_at` ist `last_seen`. Bestätigt, dass Provenienz pro Wert und nicht pro Datensatz gehört. | Keine sichtbare Konfliktdarstellung für widersprechende Quellen. Für v1 nicht nötig (ein Wert pro Pfad), aber die Historie-Route `/{org_id}/history?path=` hält den Platz frei. |
| **OpenSanctions Datasets** (`opensanctions.org/datasets/`) | Aktualisierungstakt rechtsbündig als Wort („daily", „monthly"), Zählungen als nackte Ziffer, Trennung durch Haarlinien, Farbe fast nur für Links. | Karten-Layout für die Sammlungen. Wir haben 44 Zeilen, keine 12 Kacheln. |
| **GOV.UK Type Scale** (`design-system.service.gov.uk/styles/type-scale/`) | Wenige, weit auseinanderliegende Stufen (48/36/27/24/19/16 px Desktop) und ein Body, der auf Mobil **nicht** kleiner wird (19/25 auf beiden Breiten). Unsere Skala übernimmt das Prinzip. | Die konkreten Werte. Unser Spec gibt 13/15/17/21/28/40 vor. |
| **GOV.UK Checkboxes** (`design-system.service.gov.uk/components/checkboxes/`) | „Group checkboxes together in a `<fieldset>` with a `<legend>` that describes them." Hinweistext „Select all that apply" per `aria-describedby`. Keine Vorauswahl. Alphabetische Reihenfolge als Default. `govuk-checkboxes--small` als Beleg, dass dichte Informationsseiten eine kleinere Variante brauchen. | — |
| **GOV.UK Colour** (`design-system.service.gov.uk/styles/colour/`) | Kontrast-Pflicht WCAG 2.2 AA 1.4.3, funktionale Farben nur im vorgesehenen Kontext. Der Fokus-Gelbton `#ffdd00` zeigt, dass der Fokusring bewusst außerhalb der Palette liegen darf. | Die Palette selbst. |
| **GOV.UK Summary List** (`design-system.service.gov.uk/components/summary-list/`) | `<dl>/<dt>/<dd>` für Schlüssel-Wert-Fakten, ausdrückliche Warnung „Do not use it for tabular data". Bei unvollständigen Zeilen steht ein **Satz** in der Wert-Spalte, keine leere Zelle. Genau unser Org-Detail. | Die „Change"-Aktionsspalte (wir haben keine Bearbeitung). |
| **MoJ Filter** (`design-patterns.service.justice.gov.uk/components/filter/`) | Aktive Filter als entfernbare Tags, Bereichsüberschrift „Selected filters", „Clear filters". | **Der „Apply filters"-Button.** Die MoJ-Doku räumt den Fehler selbst ein: „Users have to navigate to the top of the component to apply filters after selecting their options. This can make the component hard to use for a keyboard user." Bei 44 Zeilen filtern wir sofort, ohne Absenden. Das ist der bessere Tastaturpfad, kein Abkürzen. |

Zur Kalibrierung: Die Skill-Anleitung `frontend-design` warnt, dass „broadsheet mit Haarlinien,
Radius 0, dichte Spalten" ein KI-Default ist. Der Spec fordert genau diese Richtung ausdrücklich,
und der Brief gewinnt. Die frei gebliebenen Achsen (Schriftpaarung, Beleg-Marken, Aufbau des
Leerfalls) werden deshalb nicht auf Defaults verschwendet.

---

## 3. Verifizierte Bibliotheks-Fakten

Alle am 2026-08-28 geprüft. Versionen aus `npm view`, APIs aus context7 bzw. Herstellerdoku.

| Fakt | Wert | Quelle |
|---|---|---|
| Next.js | `16.3.3` existiert auf npm | `npm view next@16.3.3 version` |
| **`middleware.ts` heißt in Next 16 `proxy.ts`** | Benannter Export `middleware` -> `proxy`. `skipMiddlewareUrlNormalize` -> `skipProxyUrlNormalize`. **Edge-Runtime wird in `proxy` NICHT unterstützt**, Runtime ist fest `nodejs`. Codemod: `npx @next/codemod@canary middleware-to-proxy .` | context7 `/vercel/next.js`, `docs/01-app/02-guides/upgrading/version-16.mdx` |
| next-intl | `4.14.1`, Peer `next: ^16.0.0` erfüllt | `npm view next-intl version` / `peerDependencies` |
| next-intl + Next 16 | Doku sagt wörtlich: „`proxy.ts` was called `middleware.ts` up until Next.js 16." Import bleibt `next-intl/middleware`, Factory bleibt `createMiddleware`. Matcher: `'/((?!api|trpc|_next|_vercel|.*\\..*).*)'` | `next-intl.dev/docs/routing/middleware` |
| **`setRequestLocale` entfällt** | „When you follow the setup instructions with `next/root-params` above, your app is automatically eligible for static rendering." `next/root-params` ist „available by default in Next.js 16.3 and later". `generateStaticParams` bleibt nötig. | `next-intl.dev/docs/getting-started/app-router/with-i18n-routing` |
| next-intl `i18n/request.ts` | Neue Signatur mit `locale` statt `requestLocale`; Fallback über `await rootParams.locale()` + `hasLocale(routing.locales, ...)` sonst `notFound()` | ebd. |
| `localePrefix: 'always'` | `defineRouting({ ..., localePrefix: 'always' })` | context7 `/amannn/next-intl`, `docs/routing/configuration.mdx` |
| Lokalisierte Pfade | `pathnames: { '/krise/[crisis]': { en: '/crisis/[crisis]' } }` — dynamische Segmente in eckigen Klammern werden unterstützt, Nicht-ASCII wird automatisch kodiert | ebd. |
| **`revalidateTag` in Next 16** | Braucht ein **zweites Argument** mit einem `cacheLife`-Profil. Die Einargument-Form ist deprecated. Verhalten ist stale-while-revalidate. | context7 `/vercel/next.js`, `version-16.mdx`, Abschnitt „Caching APIs > revalidateTag" |
| `use cache` | Braucht `cacheComponents: true` in `next.config.ts`. In Route Handlern **nicht direkt im Body** verwendbar, muss in eine async Hilfsfunktion ausgelagert werden. | context7 `/vercel/next.js`, `use-cache-private.mdx`, `15-route-handlers.mdx` |
| Tailwind | `4.3.3`. `@theme` erzeugt Variable **und** Utility. `@theme inline` wenn die Variable eine andere Variable referenziert (nötig für `--font-*` aus `next/font`). `--*: initial` setzt Namespaces zurück. Breakpoints über `--breakpoint-*`. | `tailwindcss.com/docs/theme` |
| shadcn | CLI `4.19.0`. `npx shadcn@latest init`, `npx shadcn@latest add <name>`. `components.json` mit `tailwind.cssVariables: true`. Tailwind v4: Farben als `hsl(...)` in `:root`/`.dark`, Registrierung über `@theme inline`. | context7 `/shadcn-ui/ui` |
| Radix Popover | Folgt dem **Dialog**-WAI-ARIA-Muster. `Root.modal` Default `false`. `Content` Props u. a. `side` (Default `bottom`), `sideOffset` (`0`), `align` (`center`), `collisionPadding`, `avoidCollisions` (`true`), `onOpenAutoFocus`, `onCloseAutoFocus`, `onEscapeKeyDown`. Tastatur: Space/Enter öffnet und schließt, Tab/Shift+Tab navigiert, **Esc schließt und gibt den Fokus an den Trigger zurück**. `[data-state]` auf Trigger und Content. CSS-Variablen `--radix-popover-content-available-width/-height`. | context7 `/websites/radix-ui_primitives` |
| **Radix vergibt keinen Namen für den Dialog** | Die Doku dokumentiert kein automatisches `aria-label`/`aria-labelledby` auf `Content`. Wir setzen den Namen selbst (Abschnitt 7.6). | ebd. |
| `next/font/google` | Lädt zur **Buildzeit herunter und hostet selbst**; `subsets`, `display: 'swap'`, `variable: '--font-x'`, Anwendung als `className` auf `<html>`. `next/font/local` für eigene Dateien. | context7 `/vercel/next.js`, `font.mdx` |
| `@axe-core/playwright` | `4.13.0`. `new AxeBuilder({ page }).analyze()`, `.withTags(['wcag2a','wcag2aa'])`, `.include()/.exclude()`, `.disableRules()`. Keine eingebaute Assertion, `expect(results.violations).toEqual([])` selbst schreiben. | `github.com/dequelabs/axe-core-npm` (packages/playwright README) |
| `@lhci/cli` | `0.15.1`. `lighthouserc.json` mit `ci.collect` (`url`, `startServerCommand`, `numberOfRuns`, `settings.preset`) und `ci.assert.assertions` im Format `"categories:performance": ["error", {"minScore": 0.95}]`. Level `off|warn|error`. Desktop über `settings.preset: "desktop"`, Mobil ist der Default. | `github.com/GoogleChrome/lighthouse-ci/blob/main/docs/configuration.md` |
| Node | lokal `v23.7.0`, npm `10.9.2` | `node -v` |

**Konsequenz für WP0:** Datei heißt `proxy.ts` mit `export default createMiddleware(routing)`.
`setRequestLocale` wird **nicht** verwendet. `revalidateTag` wird **nur** mit zweitem Argument
aufgerufen.

---

## 4. Gemessene Datenfakten (treiben das Layout)

Gemessen in `orgs-nepal-2026.json` und `data/raw/hapi/admin2_NPL.json` am 2026-08-28. Zahlen im
UI werden **immer aus den Daten berechnet**, nie hart geschrieben.

```
44 Organisationen · 44 Aussagen (current_response) · 9 Orgs ohne Aussage
Sitz: NP 14 · DE 10 · US 8 · CH 5 · GB 4 · IT/FR/CZ je 1
Org-Typ: ingo 20 · national_ngo 5 · community_org 5 · diaspora_charity 5 ·
         red_cross_movement 3 · un_agency 2 · alliance 2 · platform 1 · foundation 1
Beleggrad der Aussagen: self_reported 27 · third_party_reported 17 · sonst 0
Aussagen mit Betrag: 9 von 44
Zitate: 39 von 44 Aussagen, 3 bis 27 Wörter (Median 17), 0 über 40 Wörter
Aktivitätstext: 60 bis 275 Zeichen (Median 179)  <- ist ein Absatz, kein Label
Ortsangaben (roh, unnormalisiert): Rasuwa 21 · unspecified 17 · Nuwakot 15 · Dhading 6
         + "Rasuwa district" 2, "Nuwakot district" 2, "Timure" 2, "Rasuwagadhi" 2,
           "Syabrubesi" 2, "Chitwan"/"Chitwan district"/"Chitwan district (Mugling)" je 1,
           "Gorkha"/"Gorkha district" je 1, "Kavrepalanchok" 1, "Dhading district" 1,
           "Nepal" 1, zwei Fluss-Formulierungen
Registrierungen: 75 Zeilen, davon 56 ohne Kennung (75 %) und 50 ohne Register-URL
Register-Verteilung: NP_SWC 28 · IATI 13 · US_IRS 6 · DE_DZI 6 · OTHER 4 · DE_ITZ 4 ·
                     DE_VEREINSREGISTER 4 · NP_DAO 3 · UK_CC 3 · UN 2 · CH_ZEWO 2
Finanzen: 30 von 44 ohne Einnahmen, 38 ohne Ausgaben, 1 mit program_ratio,
          13 mit Jahresbericht, 5 IATI-Publisher
          **0 von 14 nepalesischen Orgs hat eine öffentliche Einnahmenzahl**  (Spec bestätigt)
warnings[]: 0 in allen 44 Records
Devanagari-Name vorhanden: 4 Orgs
Längster Org-Name: "Médecins Sans Frontières (MSF) / Doctors Without Borders" (55 Zeichen)
Aliasse: bis 5 pro Org · Registrierungen: 0 bis 3 pro Org · data_gaps: 5 bis 15, Summe 452
Board-Datenprojektion: 40 027 B roh / 11 720 B gzip (mit notes)
                       30 518 B roh /  8 183 B gzip (ohne notes)
```

Was daraus folgt:

1. **Der Aktivitätstext ist ein Absatz.** Board-Zeilen dürfen keine einzeilige Tabellenzelle
   sein. Layout: Aktivität als Fließtext mit `max-width: 68ch`, darunter die Beleg-Zeile.
2. **Der Beleggrad-Filter hat in v1 nur zwei besetzte Werte.** Er darf nicht kaputt aussehen:
   leere Optionen werden mit Anzahl `(0)` angezeigt und sind deaktiviert, nicht ausgeblendet —
   sonst sieht es aus, als gäbe es die Kategorie nicht.
3. **Die Registrierungs-Sektion ist überwiegend leer** (75 %). Sie wird als Satzliste gestaltet,
   nicht als Tabelle mit Strichen. Siehe 8.2.
4. **Die Finanz-Sektion ist der Normalfall-Leerfall.** Der Spec-Satz „von den 14 nepalesischen
   Orgs hat keine eine öffentliche Einnahmenzahl" ist mit 0/14 belegt und darf wörtlich stehen.
5. **`warnings[]` ist überall leer.** Die Sektion „Öffentliche Hinweise" rendert in v1 nie. Sie
   wird trotzdem gebaut und in `/dev/datum` bzw. einer Fixture getestet, sonst ist sie beim ersten
   echten Warnhinweis ungetestet.
6. **Budget bestätigt.** 40 KB roh / ~11,7 KB gzip liegt unter dem Spec-Budget (60 KB roh /
   12 KB brotli) **inklusive** `note`. Notes bleiben also im Board-Payload. Der RSC-Flight-Payload
   ist größer als die reine Datenprojektion und wird bei G1 gemessen, nicht geschätzt.

### 4.1 Zwei Zahlen im Spec, die die Daten nicht hergeben (an PO gemeldet)

- Der Spec nennt **46 Aussagen**; gemessen sind es **44** `current_response`-Einträge. Die
  Zahlenzeile wird berechnet, deshalb blockiert das nichts, aber der Spec-Text stimmt nicht.
- Der Spec nennt **3 Distrikte**; nach Normalisierung sind **6** benannt (Rasuwa, Nuwakot,
  Dhading, Chitwan, Gorkha, Kavrepalanchok). Die Konzentrationsaussage „42 von 46 in 3
  Distrikten" bleibt inhaltlich richtig, die Anzahl distinkter Distrikte nicht.
- **`NP0301` existiert nicht.** Der Spec und das Backend-Gate PO-3 verwenden
  `/responders?district=NP0301`. Die echten Codes sind **Rasuwa `NP0329`**, Nuwakot `NP0328`,
  Dhading `NP0330`, Chitawan `NP0335` (HAPI schreibt „Chitawan", die Org-Daten „Chitwan" —
  Alias-Fall), Gorkha `NP0436`, Kavrepalanchok `NP0324`. Bagmati läuft von `NP0320` bis `NP0331`
  plus `NP0335`; die Codes sind landesweit fortlaufend, nicht je Provinz bei 01 beginnend.

---

## 5. Design-Tokens

### 5.1 Farbe, hell — mit gemessenen Kontrasten

Kontraste nach WCAG 2.x relativer Luminanz berechnet (Skript in Abschnitt 12.1), nicht geschätzt.

| Token | Hex | auf `bg` #FCFCFA | auf `surface` #FFFFFF | Verwendung |
|---|---|---:|---:|---|
| `--bg` | `#FCFCFA` | — | — | Seitengrund |
| `--surface` | `#FFFFFF` | 1,04 | — | Popover, Tabellenkopf-Zebra |
| `--ink` | `#1A1A18` | **16,97** | 17,43 | **Jeder Wert und jedes „nicht gefunden"** |
| `--muted` | `#4A4A46` | 8,67 | 8,90 | Sekundärtext, Beleg-Zeile, Datumsangaben |
| `--rule` | `#E2E1DC` | 1,27 | 1,31 | Nur Trennlinien, nie Text, nie Fokus |
| `--accent` | `#1F3A5F` | **11,18** | 11,48 | Links, Fokusring, aktive Filter-Tags |
| `--mark-doc` | `#2E4A62` | 9,00 | 9,24 | Marke+Wort: register_confirmed, externally_audited |
| `--mark-doc-tint` | `#EDF1F5` | 1,10 | — | Fläche hinter `--mark-doc` |
| `--mark-open` | `#544529` | **9,04** | 9,28 | Marke+Wort: unverified, not_found, not_searched, source_unreachable, not_public |
| `--mark-open-tint` | `#F5F1E8` | 1,10 | — | Fläche hinter `--mark-open` |
| `--warn` | `#7A3B2E` | 8,20 | 8,43 | **Ausschließlich `warnings[]`** |

Text auf Marken-Fläche: `--mark-doc` auf `--mark-doc-tint` = **8,14:1**,
`--mark-open` auf `--mark-open-tint` = **8,24:1**. Differenz 0,10 — praktisch nicht wahrnehmbar.
Das ist der Punkt (siehe 5.3).

### 5.2 Farbe, dunkel

| Token | Hex | auf `bg` #16161A | Anmerkung |
|---|---|---:|---|
| `--bg` | `#16161A` | — | Spec |
| `--surface` | `#1E1E23` | 1,09 | abgeleitet |
| `--ink` | `#EDEDE8` | **15,36** | Spec |
| `--muted` | `#A9A9A2` | 7,63 | abgeleitet, über dem 7:1-Ziel |
| `--rule` | `#33333A` | 1,44 | nur Linien |
| `--accent` | `#7FA6D4` | **7,14** | Spec; als Fokusring weit über 3:1 |
| `--mark-doc` | `#A8C4DE` | 9,98 | abgeleitet |
| `--mark-doc-tint` | `#1C2530` | 1,17 | abgeleitet |
| `--mark-open` | `#D6C49B` | 10,51 | abgeleitet |
| `--mark-open-tint` | `#2A251A` | 1,18 | abgeleitet |
| `--warn` | `#E39684` | 7,70 | abgeleitet |

Text auf Marken-Fläche dunkel: `--mark-doc` auf Tint = **8,56:1**, `--mark-open` auf Tint =
**8,87:1**. Differenz 0,31.

**Theme-Umschaltung:** `.dark` auf `<html>`, gesteuert von `prefers-color-scheme` plus einem
Schalter im Footer, der die Wahl in `localStorage` merkt. Der Schalter ist die **einzige** Stelle
mit clientseitigem Skript im Layout-Shell; er wird mit einem winzigen Inline-Skript vor dem
ersten Paint gesetzt, damit es kein Umspringen gibt.

### 5.3 Abweichungen vom Spec (Protokoll)

**A1 — `--mark-open` von `#6B5B3E` auf `#544529` abgedunkelt.**
Mit dem Spec-Wert misst die Marke für „offen / nicht gefunden" **5,84:1** auf ihrer Fläche,
die Marke für „dokumentiert" **8,14:1**. Das sind 2,3 Stufen Unterschied, und der
Nicht-gefunden-Zustand wäre damit sichtbar schwächer als ein gefundener Wert. Der Spec nennt
genau das „die wichtigste Stilregel des Produkts". Wenn zwei Spec-Regeln kollidieren, gewinnt die
als wichtigste bezeichnete. Farbton und Sättigung bleiben unverändert (HSL 39°, 34 %), nur die
Helligkeit sinkt von 33 % auf 24,5 %. Ergebnis: 8,24 gegen 8,14. Belegt in 5.1.

**A2 — `--ink` #1A1A18 auf #FCFCFA misst 16,97:1, nicht die 7 bis 9:1, die
`eye-friendly-light-mode` empfiehlt.**
Der Spec-Wert bleibt. Begründung: (a) der Referenzrahmen ist gedruckte Tinte auf Papier,
(b) es gibt **einen** Ink-Token, weil ein Wert und ein „nicht gefunden" exakt gleich aussehen
müssen — zwei Tinten wären eine Hintertür für genau die Abwertung, die verboten ist,
(c) der Spec fordert Body ≥ 7:1, 16,97 erfüllt das. Die Maßnahmen, die die Skill-Anleitung
gegen Blendung wirklich nennt, sind umgesetzt: kein reines Weiß als Grund (#FCFCFA),
Zeilenhöhe 1,6 im Fließtext, `max-width: 68ch`, keine Schriftstärke unter 400 unter 24 px,
keine gesättigten Akzente.

**A3 — `not_searched` als Label-Variante von `not_found`.**
Der Spec nennt 6 Zustände, das Schema v0.2 nennt 4 `gap_reason`-Werte. `not_searched` und
`searched_not_found` teilen sich **einen** visuellen Zustand (`not_found`, identische Tinte und
Stärke), unterscheiden sich aber in Wort und Popover-Satz — sonst behauptet die Seite, gesucht
zu haben, wo nicht gesucht wurde. `/dev/datum` zeigt die 6 Zustände in der geforderten Matrix
plus eine klar markierte Extrazeile für die Label-Variante.

**A4 — Keine Icon-Bibliothek.** Siehe 6.3.

### 5.4 Typografie

**Schriftpaarung: Source Serif 4 (Überschriften) + Public Sans (Fließtext, UI, Ziffern).**

Der Spec lässt „Source Serif 4 oder Literata" und „Inter oder Public Sans" offen. Entscheidung
und Begründung:

- **Public Sans statt Inter.** Public Sans ist die Schrift des U.S. Web Design System, also
  buchstäblich eine Registerschrift. Inter ist die Default-Sans praktisch jeder
  KI-generierten Oberfläche; sie würde die Positionierung „kein SaaS-Produkt" unterlaufen.
  Public Sans ist außerdem schmaler als Inter, was bei deutschen Komposita auf 360 px
  messbar weniger Umbrüche bedeutet, und bringt Tabellenziffern mit.
- **Source Serif 4 statt Literata.** Literata ist eine Buchschrift mit großer Laufweite;
  Source Serif 4 hat eine `opsz`-Achse und bleibt bei 21 px in Zeilen dichter Daten ruhiger.
- **Kein Mono außer für die GLIDE-ID.** Die GLIDE-ID (`ff-2026-000162-npl`) und
  Distriktcodes (`NP0329`) laufen in `ui-monospace, SFMono-Regular, Menlo, monospace` — ein
  Systemstack, keine geladene vierte Schrift.
- **Devanagari.** 4 Orgs haben einen Devanagari-Namen (`द राइजिङ युवा क्लब`). Weder Source
  Serif 4 noch Public Sans decken Devanagari ab; ohne Vorkehrung springt der Browser in eine
  beliebige Systemschrift. Deshalb `Noto_Sans_Devanagari` über `next/font/google` mit
  `subsets: ['devanagari']`, `preload: false` und `variable: '--font-devanagari'`, angewendet
  ausschließlich über `:lang(ne)`. Damit ist die Datei selbst gehostet, fällt aber nicht ins
  Budget der Seiten, die sie nicht brauchen.

Alle drei über `next/font/google` — lädt zur Buildzeit und hostet selbst, also **null
Drittanbieter-Requests** und kein Cookie-Banner. Ob die Familien als Variable-Font ausgeliefert
werden, wird im WP0-Build gegen die tatsächlich erzeugten `.woff2` geprüft und hier
nachgetragen; Google liefert je nach User-Agent statisch oder variabel aus, eine Fetch-Antwort
allein ist kein Beleg.

**Skala (6 Größen, Spec):**

| Token | px | Zeilenhöhe | Schnitt | Einsatz |
|---|---:|---:|---|---|
| `--text-xs` | 13 | 18 | Public Sans 400 | Beleg-Zeile, Marken-Wort, Fußnoten, Tabellenkopf |
| `--text-sm` | 15 | 23 | Public Sans 400 | Filterlabels, Tabellenzellen, Metazeilen |
| `--text-base` | 17 | 27 | Public Sans 400 | Fließtext, Aktivitätstext |
| `--text-lg` | 21 | 28 | Source Serif 4 600 | Abschnittsüberschrift (h3) |
| `--text-xl` | 28 | 34 | Source Serif 4 600 | Seitenüberschrift (h2), Org-Name |
| `--text-2xl` | 40 | 44 | Source Serif 4 600 | Krisentitel (h1), nur Board |

Auf `base` (unter 768 px) fällt nur `--text-2xl` auf 30/34 und `--text-xl` auf 24/30. Der Body
bleibt auf allen Breiten 17 px — Prinzip von GOV.UK übernommen.

Weitere Regeln: `font-variant-numeric: tabular-nums` auf `body`. `hyphens: auto` mit `lang="de"`.
**Keine Versalien** (`text-transform` ist verboten), **kein `letter-spacing`** (deutsche
Komposita), keine Schriftstärke unter 400. Kursiv nur im `<blockquote>` nicht — Zitate sind
aufrecht mit Anführungszeichen, damit englische Zitate im deutschen Satz nicht wie Betonung
wirken.

### 5.5 Raster, Abstände, Bewegung

- **4-px-Raster.** Tailwind `--spacing: 4px`, alle Abstände Vielfache.
- **Abschnittstrennung:** 1-px-Linie `--rule` + 32 px Abstand. **Keine Karten, keine Schatten.**
  `--radius: 0` global; einzige Ausnahme sind 2 px an der Marken-Fläche und am Filter-Tag,
  damit sie nicht wie Tabellenzellen aussehen.
- **Breakpoints:** `base` / `md: 768px` / `xl: 1280px`. Nur diese drei.
- **Maximalbreite:** Inhaltsspalte 76ch, Fließtext-Absätze 68ch, Board-Zeilenspalte volle
  Inhaltsbreite.
- **Einzige horizontale Scrollbox:** die Registrierungstabelle, mit
  `overflow-x: auto; overscroll-behavior-x: contain` und sichtbarem Rand.
- **Bewegung:** praktisch keine. Popover 120 ms `opacity`, sonst nichts. Alles unter
  `@media (prefers-reduced-motion: reduce)` auf 0 ms.
- **Fokus:** `outline: 2px solid var(--accent); outline-offset: 2px`. Nie `outline: none` ohne
  Ersatz. 11,18:1 hell und 7,14:1 dunkel, also weit über den geforderten 3:1.

### 5.6 `globals.css` — verbindliches Gerüst

```css
@import "tailwindcss";

:root {
  --bg: #FCFCFA;  --surface: #FFFFFF;  --ink: #1A1A18;  --muted: #4A4A46;
  --rule: #E2E1DC; --accent: #1F3A5F;
  --mark-doc: #2E4A62;  --mark-doc-tint: #EDF1F5;
  --mark-open: #544529; --mark-open-tint: #F5F1E8;
  --warn: #7A3B2E;
}
.dark {
  --bg: #16161A;  --surface: #1E1E23;  --ink: #EDEDE8;  --muted: #A9A9A2;
  --rule: #33333A; --accent: #7FA6D4;
  --mark-doc: #A8C4DE;  --mark-doc-tint: #1C2530;
  --mark-open: #D6C49B; --mark-open-tint: #2A251A;
  --warn: #E39684;
}

@theme inline {
  --color-bg: var(--bg);
  --color-surface: var(--surface);
  --color-ink: var(--ink);
  --color-muted: var(--muted);
  --color-rule: var(--rule);
  --color-accent: var(--accent);
  --color-mark-doc: var(--mark-doc);
  --color-mark-doc-tint: var(--mark-doc-tint);
  --color-mark-open: var(--mark-open);
  --color-mark-open-tint: var(--mark-open-tint);
  --color-warn: var(--warn);

  --font-serif: var(--font-source-serif), Georgia, "Times New Roman", serif;
  --font-sans: var(--font-public-sans), system-ui, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, monospace;
  --font-deva: var(--font-noto-devanagari), sans-serif;
}

@theme {
  --spacing: 4px;
  --radius-*: initial;
  --shadow-*: initial;          /* Schatten sind im Projekt verboten */
  --breakpoint-*: initial;
  --breakpoint-md: 48rem;       /* 768 */
  --breakpoint-xl: 80rem;       /* 1280 */
  --text-xs: 13px;   --text-xs--line-height: 18px;
  --text-sm: 15px;   --text-sm--line-height: 23px;
  --text-base: 17px; --text-base--line-height: 27px;
  --text-lg: 21px;   --text-lg--line-height: 28px;
  --text-xl: 28px;   --text-xl--line-height: 34px;
  --text-2xl: 40px;  --text-2xl--line-height: 44px;
}

@layer base {
  html { color-scheme: light dark; }
  body {
    background: var(--bg); color: var(--ink);
    font-family: var(--font-sans);
    font-variant-numeric: tabular-nums;
    -webkit-font-smoothing: antialiased;
  }
  :lang(ne) { font-family: var(--font-deva); }
  h1, h2, h3 { font-family: var(--font-serif); font-weight: 600; text-wrap: balance; }
  :lang(de) p, :lang(de) li, :lang(de) dd { hyphens: auto; }
  :where(a, button, [tabindex]):focus-visible {
    outline: 2px solid var(--accent); outline-offset: 2px;
  }
  ::selection { background: var(--mark-doc-tint); color: var(--ink); }
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration: .01ms !important; transition-duration: .01ms !important; }
  }
}
```

`--radius-*: initial` und `--shadow-*: initial` löschen die Tailwind-Defaults, damit
`rounded-2xl` oder `shadow-lg` im Code gar nicht erst existieren. Das ist der billigste
mechanische Schutz gegen die verbotenen Muster.

---

## 6. Komponenteninventar

### 6.1 shadcn — erlaubt

`button`, `checkbox`, `popover`, `sheet`, `input`, `badge`, `separator`, `table`, `tabs`,
`dropdown-menu`. Mehr nicht. Jede weitere shadcn-Komponente ist eine Änderung an diesem
Dokument und braucht meine Freigabe.

Anpassungen bei der Übernahme: `badge` flach (kein Radius außer 2 px, keine Füllung außer
den Marken-Tints), `button` ohne Schatten, `table` ohne Zebra außer im Tabellenkopf,
`tabs` als Textreiter mit Unterstrich statt Pillen.

### 6.2 shadcn — verboten

`card`, `accordion` (stattdessen natives `<details>`), `dialog`, `alert`, `avatar`, `carousel`,
`chart`, `tooltip` für Provenienz, `skeleton`, `progress`, `sonner`.

### 6.3 Keine Icon-Bibliothek

Es wird **kein** `lucide-react`, `@phosphor-icons/react` oder ähnliches installiert. Begründung:

1. Der Spec verbietet „Icon pro Listeneintrag". Der einzige Icon-Bedarf sind die Beleg-Marken
   plus vier Steuer-Glyphen (Schließen, Chevron, Extern-Link, Theme). Das sind acht Pfade.
2. Ein Icon-Set einer bekannten Bibliothek ist eine der Signaturen des generischen KI-UI.
   Eigene 12-px-Marken sind das, was diese Seite unterscheidbar macht.
3. First-Load-JS-Budget: 110 KB gz. Jede vermiedene Abhängigkeit ist Reserve.
4. Kein Risiko durch umbenannte Icon-Exporte zwischen Versionen.

Alle Marken liegen in `components/datum/marks.tsx` als reine Inline-SVG-Funktionen,
12x12 viewBox, `stroke-width: 1.25`, `stroke: currentColor`, `fill: none`,
`aria-hidden="true"`, `focusable="false"`, ohne eigene `<title>`.

Marken-Zeichnung (die Marke trägt nie allein die Bedeutung, es steht immer das Wort daneben):

| Zustand | Marke | Zeichnung |
|---|---|---|
| `register_confirmed` | Register | Rechteck mit Siegelpunkt unten rechts |
| `externally_audited` | Testat | Rechteck mit Haken **innerhalb** des Rechtecks |
| `self_reported` | Eigenangabe | Rechteck mit Sprechlinie am Rand |
| `third_party_reported` | Dritte | zwei versetzte Rechtecke |
| `unverified` | ungeprüft | Rechteck mit gestrichelter Unterkante |
| `not_found` / `not_searched` | nicht gefunden / nicht gesucht | **vollständiger Rahmen, leer** — gleiche Strichstärke wie alle anderen |
| `source_unreachable` | Quelle nicht erreichbar | Rahmen mit Lücke in der rechten Kante |
| `not_public` | wird nicht veröffentlicht | Rahmen mit horizontalem Balken (verschlossen) |
| `stale` | älterer Stand | kleiner Kreis mit Zeiger |

Kein Haken und kein Kreuz **neben einer Organisation**. Der Haken in „Testat" steht im Rahmen
und bezeichnet ein Dokument, keine Bewertung.

### 6.4 Eigene Komponenten (Eigentümer in Klammern)

| Komponente | Pfad | Eigentümer |
|---|---|---|
| `<Datum>` + `<DatumBody>` + `<Mark>` | `components/datum/*` | **Lead, WP0. Worker konsumieren, ändern nie.** |
| `<Amount>` | `components/datum/amount.tsx` | Lead, WP0 |
| `<SiteHeader> <SiteFooter> <SkipLink> <ThemeToggle>` | `components/shell/*` | Lead, WP0 |
| `<SourceLine>` | `components/datum/source-line.tsx` | Lead, WP0 |
| Board-Zeile, Tabs, Filterleiste, Zahlenzeile, Locator-SVG | `components/board/*` | WP1 |
| Org-Sektionen | `components/org/*` | WP2 |
| Prosa-Bausteine der Vertrauensseiten | `components/pages/*` | WP3 |

**`<Amount>` ist eine Sperre, kein Komfort.** Es rendert keinen nackten Betrag: die Prop
`basis: 'appeal' | 'released' | 'disbursed' | 'reported'` ist erforderlich, und die Ausgabe
lautet z. B. „CHF 25.000.000 zugesagt (Appell, nicht als Auszahlung belegt)". Ohne `basis`
kompiliert es nicht. Damit ist die Spec-Regel „Beträge nie nackt" typgeprüft statt
Review-abhängig.

---

## 7. `<Datum>` — vollständige Spezifikation

### 7.1 Datenvertrag

```ts
export type Verification =
  | 'register_confirmed' | 'externally_audited'
  | 'self_reported' | 'third_party_reported' | 'unverified';

export type GapReason =
  | 'not_searched' | 'searched_not_found' | 'source_unreachable' | 'not_public';

export interface Datum<T = unknown> {
  value: T | null;
  is_gap: boolean;
  source_url: string | null;
  retrieved_at: string | null;    // ISO 8601 date
  verification: Verification;
  quote: string | null;
  note: string | null;
  gap_reason: GapReason | null;   // nur wenn value === null
}
```

Der Schlüssel fehlt nie. Ein Gap ist `{ value: null, is_gap: true, ... }`, kein fehlendes Feld
und kein `undefined`. `lib/types.ts` wird aus `apps/api/openapi.json` erzeugt, sobald der Stub
da ist; bis dahin ist die Datei handgeschrieben und gegen `schema/org.schema.json` geprüft.

**Gemessene Realität, die der Code aushalten muss:** in `orgs-nepal-2026.json` gibt es Gaps mit
`note: null` (z. B. `the-rising-youth-club` -> `names.legal`). Ist `note` leer, fällt der
Popover auf den `gap_reason`-Satz zurück; es entsteht kein leerer Absatz und kein „null".

### 7.2 Zustandsmaschine

Reine Funktion `datumState(d, opts)` in `components/datum/state.ts`, mit Unit-Tests für jeden
Pfad (TDD, rot zuerst).

```
value !== null:
  verification === 'unverified'                 -> 'value_unverified'
  isStale(retrieved_at, staleAfterDays)         -> 'stale'
  sonst                                         -> 'value'
value === null:
  gap_reason === 'source_unreachable'           -> 'source_unreachable'
  gap_reason === 'not_public'                   -> 'not_public'
  gap_reason === 'not_searched'                 -> 'not_found'   (Label „nicht gesucht")
  sonst (searched_not_found | null)             -> 'not_found'   (Label „nicht gefunden")
```

`staleAfterDays` Default 30. `isStale` vergleicht gegen ein **übergebenes** `now` (Prop bzw.
Modulparameter), nie gegen `Date.now()` im Render — sonst ist die Seite nicht statisch
reproduzierbar und Screenshot-Tests flackern.

`stale` rendert den Wert in `--ink` wie `value` und setzt **zusätzlich** eine zweite Marke
„älterer Stand". Es ist kein abgeschwächter Wert, sondern ein Wert mit einer zweiten Aussage.

### 7.3 Vokabular

Namespace `common.datum`. Nie eine Abkürzung, nie nur ein Icon, nie nur eine Farbe.

| Zustand / Grad | DE Wort | EN Wort | Marken-Farbe |
|---|---|---|---|
| `register_confirmed` | Register | Register | `--mark-doc` |
| `externally_audited` | Testat | Audited | `--mark-doc` |
| `self_reported` | Eigenangabe | Self-reported | `--ink` |
| `third_party_reported` | Dritte | Third party | `--ink` |
| `unverified` | ungeprüft | Unverified | `--mark-open` |
| `not_found` (searched) | nicht gefunden | Not found | `--mark-open` |
| `not_found` (not_searched) | nicht gesucht | Not searched | `--mark-open` |
| `source_unreachable` | Quelle nicht erreichbar | Source unreachable | `--mark-open` |
| `not_public` | wird nicht veröffentlicht | Not published | `--mark-open` |
| `stale` (Zusatzmarke) | älterer Stand | Older reading | `--mark-open` |

Grad-Sätze im Popover (Zeile 1), Namespace `common.datum.sentence`:

| Zustand | DE |
|---|---|
| `register_confirmed` | In einem amtlichen Register bestätigt. |
| `externally_audited` | Aus einem geprüften Abschluss oder einem Testat. |
| `self_reported` | Angabe der Organisation selbst. |
| `third_party_reported` | Von Dritten berichtet, etwa Medien oder OCHA. |
| `unverified` | Gefunden, aber die Quelle trägt den Wert nicht eindeutig. |
| `not_found` (searched) | Gesucht und nicht gefunden. |
| `not_found` (not_searched) | In dieser Runde nicht gesucht. |
| `source_unreachable` | Das Register war beim Abruf nicht erreichbar. |
| `not_public` | Dieses Register veröffentlicht den Wert nicht. |

Der Satz zu `not_public` ist bewusst eine Aussage **über das Register**, nicht über die
Organisation. Das ist im Review wörtlich zu prüfen.

### 7.4 Varianten

**`variant="block"` — Board, Fußzeile jeder Aussage. Provenienz immer sichtbar, kein Popover.**

```
┌ ganze Zeile ist ein <a> (bzw. ein <p>, wenn es keine Quelle gibt) ─────────┐
│ [Marke] Dritte · reliefweb.int · 27.08.2026                               │
└───────────────────────────────────────────────────────────────────────────┘
```

13 px, `--muted` für die Trennpunkte und das Datum, das Marken-Wort in seiner Marken-Farbe.
Externe Links: `rel="noopener"`, kein `target="_blank"` (der Nutzer entscheidet), sichtbare
Domain als Linktext. Gibt es keine Quelle (Gap), rendert dieselbe Zeile ohne Link:
`[Marke] nicht gefunden · gesucht am 28.08.2026`. Gleiche Größe, gleiche Stärke, gleiche
Position.

**`variant="inline"` — Org-Seite. Wert + Marke als Popover-Trigger.**

```
Einnahmen   12.400.000 EUR  [Marke Register ▸]
Einnahmen   nicht gefunden  [Marke nicht gefunden ▸]      <- identische Tinte und Stärke
```

Der Wert steht in `--ink`, 17 px, Gewicht 400. **Der Text „nicht gefunden" steht ebenfalls in
`--ink`, 17 px, Gewicht 400.** Nicht kursiv, nicht kleiner, nicht `--muted`, nicht durchgestrichen,
keine reduzierte Deckkraft. Das ist die Regel, die im Review als Erstes geprüft wird.

### 7.5 Popover-Inhalt, feste Reihenfolge

```
Beleg: Einnahmen                              <- 13px, --muted, ist der Dialogname
────────────────────────────────────────────  <- 1px --rule
In einem amtlichen Register bestätigt.       <- 15px, --ink        (1) Grad als Satz
Abgerufen am 28.08.2026 (heute)               <- 13px, --muted      (2) absolut + relativ
"quote wie im Original, höchstens 40 Wörter" <- 15px blockquote lang="en"  (3)
Währung EUR, Geschäftsjahr 2024, Umfang global  <- 13px, --muted (4) note
reliefweb.int                                 <- 15px Link          (5) Quelle
https://reliefweb.int/report/nepal/...        <- 13px --muted, overflow-wrap:anywhere
```

Fehlt ein Block, entfällt er ersatzlos; es bleibt keine leere Zeile stehen. Reihenfolge ist
fest und wird nicht pro Feld variiert. Breite: `min(320px, var(--radix-popover-content-available-width))`.

### 7.6a Radix wird erst bei der ersten Interaktion geladen

Der Popover kostet 30,6 KB gz, und nur die Org-Seite zieht ihn über
`<Datum variant="inline">` überhaupt herein. Ein Popover ist per Definition etwas, das eine
Leserin bewusst öffnet, also gehört nichts davon in den ersten Ladevorgang.

`datum-trigger.tsx` rendert bis zur Aktivierung einen einfachen `<button>` mit eigenem
`aria-haspopup="dialog"` und `aria-expanded="false"`; erst beim Klick wird
`datum-popover.tsx` per `lazy()` nachgeladen. Ergebnis: Org-Seiten von 177,6 auf 147,4 KB gz.

Die nachgeladene Komponente klickt beim Mounten einmal ihren eigenen Trigger. Das sieht
seltsam aus, und die naheliegende Alternative, gleich mit `open={true}` zu rendern, war der
erste Versuch: Radix sieht dann keinen Übergang von geschlossen auf offen, führt seine
Fokus-Verwaltung nicht aus, und der Fokus bleibt auf einem gerade entfernten Button liegen.
Ein Playwright-Test hat das gefunden. Über den echten Trigger macht Radix alles wie sonst,
inklusive Fokus in den Inhalt und Fokus-Rückgabe bei Escape.

### 7.6 Barrierefreiheits-Vertrag

- Trigger ist ein echtes `<button type="button">` über `Popover.Trigger asChild`. Radix folgt
  dem Dialog-WAI-ARIA-Muster; `[data-state]` liegt auf Trigger und Content, Esc schließt und
  gibt den Fokus an den Trigger zurück (belegt in Abschnitt 3).
- **Zugänger Name des Triggers.** Das Marken-Wort allein reicht nicht — „Register" steht auf
  einer Org-Seite bis zu achtmal. Der Trigger bekommt
  `aria-label={t('datum.triggerLabel', { field, grade })}`, also z. B.
  „Beleg für Einnahmen: Register. Quelle und Datum anzeigen." Das `field` kommt als Pflicht-Prop.
- **Zugänger Name des Dialogs.** Radix vergibt keinen. Der Popover rendert eine sichtbare
  Überschrift („Beleg: Einnahmen") mit `id`, und `Popover.Content` bekommt
  `aria-labelledby={id}`.
- `modal={false}` (Radix-Default), damit der Seiten-Scroll nicht gesperrt wird.
- Trefferfläche: das sichtbare Marken-Chip ist 24 px hoch, die Trefferfläche wird über ein
  `::after` mit `position:absolute; inset:-10px -8px; content:''` auf **44 px** erweitert, ohne
  das Layout zu verändern. Damit sich Trefferflächen benachbarter Zeilen nicht überlappen,
  gilt: **jede Zeile, die ein inline-Datum enthält, hat `min-height: 44px`.** Das ist eine
  verbindliche Layout-Regel für WP2, keine Empfehlung.
- Das Zitat ist `<blockquote lang="en">` (die Quellen sind englisch), damit Screenreader nicht
  englischen Text mit deutscher Aussprache lesen.
- Datumsangaben: `<time dateTime="2026-08-27">27.08.2026</time>`, absolut zuerst, relativ in
  Klammern. Relative Angaben werden gegen ein übergebenes `now` gebildet.

### 7.7 Props

```ts
interface DatumProps<T> {
  datum: Datum<T>;
  field: string;                    // Pflicht. Feldname für den a11y-Namen, bereits lokalisiert.
  variant: 'block' | 'inline';
  render?: (value: T) => ReactNode; // Formatierung des Werts; Default: String(value)
  staleAfterDays?: number;          // Default 30
  now?: Date;                       // Default: Build-Zeitstempel aus lib/now.ts
}
```

`render` ist der einzige Weg, einen Wert zu formatieren. Zahlen laufen über `<Amount>`.

### 7.8 „Alle Quellen anzeigen" und Druck

Der Popover-Inhalt wird **immer** ins DOM gerendert, als
`<div class="datum-expanded" data-expanded={...}>`, und ist auf dem Bildschirm per CSS
ausgeblendet, solange nicht expandiert. Unter `@media print` ist er sichtbar. Grund: Journalisten
drucken mit Strg+P, ohne vorher einen Schalter zu suchen; eine reine Client-State-Lösung wäre
beim Druck leer. Der Popover selbst rendert denselben `<DatumBody>` nur während er offen ist.

Der Schalter „Alle Quellen anzeigen" liegt im Kopf der Org-Seite und im Board, setzt
`?quellen=alle` in den `searchParams` (teilbar) und schaltet die Bildschirm-Sichtbarkeit.

**Kosten:** wird in WP2 gemessen (HTML-Zuwachs pro Org-Seite). Bleibt der Zuwachs unter 8 KB
brotli, bleibt es so; sonst kommt der Block nur unter `@media print` per `content-visibility`
ins Rendering und ich entscheide neu. Diese Messung ist ein Gate-Punkt, keine Fußnote.

---

## 8. Seiten-Skelette

Routen (next-intl `pathnames`, `localePrefix: 'always'`, Default `de`):

| intern | de | en |
|---|---|---|
| `/` | `/de` -> Weiterleitung auf die aktive Krise | `/en` -> dito |
| `/krise/[crisis]` | `/de/krise/[crisis]` | `/en/crisis/[crisis]` |
| `/organisation/[orgId]` | `/de/organisation/[orgId]` | `/en/organisation/[orgId]` |
| `/methodik` | `/de/methodik` | `/en/methodology` |
| `/quellen` | `/de/quellen` | `/en/sources` |
| `/korrekturen` | `/de/korrekturen` | `/en/corrections` |
| `/impressum` | `/de/impressum` | `/en/imprint` |
| `/datenschutz` | `/de/datenschutz` | `/en/privacy` |
| `/dev/datum` | nur intern, `noindex`, nicht in `sitemap.ts` | — |

### 8.1 Layout-Shell (WP0)

```
[Skip-Link: "Zum Inhalt springen"  — sichtbar bei Fokus, 13px, --accent]
┌─────────────────────────────────────────────────────────────────────────┐
│ Spenden-Transparenz            Nepal: Flash Floods, Aug 2026   [DE|EN] │  <- 15px
│                                ff-2026-000162-npl (mono, 13px, --muted)│
├─────────────────────────────────────────────────────────────────────────┤  <- 1px --rule
│ <main id="inhalt">                                                      │
│ ...                                                                     │
├─────────────────────────────────────────────────────────────────────────┤
│ Daten-Stand: 28.08.2026, 14:57 (vor 2 Stunden)                          │  <- 13px
│ Methodik · Quellen · Korrekturen · Impressum · Datenschutz   [Hell/Dunkel]│
│ Keine Bewertung, kein Ranking. Jeder Wert trägt seine Quelle.           │
└─────────────────────────────────────────────────────────────────────────┘
```

Header ist **nicht** sticky (kostet Höhe auf 360 px und bringt bei einer Leseseite nichts).
Sprachumschalter behält den Pfad bei (`usePathname` aus `i18n/navigation`). Kein Logo, keine
Suche, kein Menü.

### 8.2 Response Board (WP1) — `/de/krise/[crisis]`

```
Nepal: Sturzfluten, August 2026                                    <- h1, 40/44 Serif
ff-2026-000162-npl                                                 <- mono 13, --muted

Diese Seite zeigt, wer öffentlich eine Reaktion gemeldet hat.     <- 17px, max 68ch
Sie bewertet keine Organisation und empfiehlt keine Spende.

44 Organisationen · 44 belegte Meldungen · 6 Distrikte · 9 ohne     <- 17px; JEDE Zahl
gefundene Reaktion                                                    ist ein Filterlink
                                                                      (<a>, kein Button)
Daten-Stand 28.08.2026, 14:57 · Quellen und Lizenzen                <- 13px

┌──────────────────────────────────┬──────────────────────────────┐
│ [Nepal-Umriss, statisches SVG,   │  Filterleiste                │  xl: zwei Spalten
│  3 Distrikte markiert,           │  <fieldset><legend>...       │  md/base: gestapelt,
│  aria-hidden, 180x140, keine     │                              │  Filter im Bottom-Sheet
│  Interaktion, kein Tooltip]      │                              │
└──────────────────────────────────┴──────────────────────────────┘
──────────────────────────────────────────────────────────────────  1px --rule

Nach Organisation   |   Chronologisch          <- Tabs, Textreiter mit Unterstrich
──────────────────────────────────────────────────────────────────
Gewählt: Rasuwa ×   Sitz in Nepal ×   Alle Filter löschen   <- Tags, nur wenn aktiv
44 von 44 Organisationen                        <- aria-live="polite", 15px

┌ <article> ───────────────────────────────────────────────────────┐
│ Nepal Red Cross Society                        Nepal · Rotkreuz  │  21px Serif / 13px
│ NRCS                                                             │  Aliasse 13px --muted
│                                                                  │
│  IFRC hat Mittel aus dem Katastrophenfonds (DREF) freigegeben,  │  17px, max 68ch
│  um die Sturzflut-Reaktion der Nepal Red Cross Society zu       │
│  unterstützen.                                                 │
│  CHF 1.000.000 freigegeben (Mittelfreigabe, nicht als           │  <Amount basis="released">
│  Auszahlung belegt) · ohne Ortsangabe · 27.08.2026              │
│  [Marke] Dritte · radionepalonline.com · 27.08.2026             │  <- <Datum variant=block>
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │  gestrichelt, 1px
│  Nepal Red Cross Society verteilt Trinkwasser, ...              │  zweite Aussage
│  [Marke] Dritte · radionepalonline.com · 27.08.2026             │
│                                                                  │
│  Alle Angaben zu dieser Organisation ansehen                    │  15px Link
└──────────────────────────────────────────────────────────────────┘
──────────────────────────────────────────────────────────────────  1px --rule
┌ <article> ───────────────────────────────────────────────────────┐
│ Caritas Nepal                                  Nepal · NGO       │
│                                                                  │
│  Keine öffentliche Reaktionsmeldung gefunden (Stand 28.08.2026).│  17px --ink 400
│  Gesucht wurde: ReliefWeb-Meldungen zur Flut, die eigene         │  15px --ink
│  Website und nepalesische Presse.                               │
│  Alle Angaben zu dieser Organisation ansehen                    │
└──────────────────────────────────────────────────────────────────┘
```

Die Zeile ohne Reaktion hat **dieselbe** Rahmung, dieselbe Überschriftgröße, dieselbe
vertikale Präsenz wie eine Zeile mit drei Aussagen. Kein „0"-Badge, keine Ausgrauung, keine
Sortierung ans Ende.

**Tab B (chronologisch)** teilt den Filterzustand über dieselben `searchParams`, gruppiert nach
Tag (`<h3>28. August 2026</h3>`), und jede Aussage nennt die Organisation als Link.

**Filter:** `<fieldset>` je Gruppe mit `<legend>` (GOV.UK-Regel), Checkboxen, OR innerhalb einer
Gruppe, AND zwischen Gruppen. Gruppen: Distrikt (inkl. „ohne Ortsangabe", mit Anzahl),
Sitz (Nepal / international), Org-Typ, Beleggrad der Meldung, Namenssuche (`<input type="search">`).
**Kein Absenden-Button** (Begründung in Abschnitt 2, MoJ). Kein Debounce, kein Spinner: 44 Zeilen
werden synchron gefiltert. Zustand in `searchParams` über `history.replaceState` via
`useRouter` aus `i18n/navigation`, damit Links teilbar sind. Optionen mit Anzahl 0 werden
`disabled` **angezeigt**, nicht entfernt.

**Sortierung:** „Zuletzt gemeldet" (Default), „A bis Z", „Zuerst mit den wenigsten Daten".
**Nie nach Beleggrad** — das würde nach unserer Recherchetiefe ranken.

**Locator-SVG:** statisch, im Repo, `aria-hidden="true"`, keine Interaktion, kein Text darin,
Füllung `--rule`, markierte Distrikte `--mark-doc-tint` mit `--mark-doc`-Kontur. Es ersetzt
keine Karte und behauptet keine Vollständigkeit; die Bildunterschrift sagt das in einem Satz.

**Mobil (base):** Filter in einem `sheet` (Bottom-Sheet), ausgelöst von einer Schaltfläche
„Filter (2)" mit der Anzahl aktiver Filter. Zahlenzeile bricht auf zwei Zeilen. Tabs bleiben.

### 8.3 Org-Detail (WP2) — 8 Abschnitte

Getrennt durch 1-px-Linie + 32 px, jeder Abschnitt eine `<section aria-labelledby>` mit `<h2>`.

```
1  Kopf         Name (28px Serif) · Devanagari-Name <span lang="ne"> · Aliasse ·
                Typ · Sitz · Website (Domain sichtbar) · zuletzt aktualisiert.
                KEIN Score, keine Badge-Reihe, keine Zusammenfassung.
                Rechts: [Alle Quellen anzeigen] Schalter.

2  Reaktion auf die Flut
                Chronologisch, gleiche Aussage-Bausteine wie das Board,
                <Datum variant="block"> je Aussage.
                Leerfall: "Keine öffentliche Reaktionsmeldung gefunden (Stand ...)"
                plus "Gesucht wurde: ..." aus research_notes.

3  Präsenz in Nepal
                <dl> mit: seit Jahr · Arbeitsweise · Beschäftigte · Partner.
                Jede Zeile <Datum variant="inline">, Zeilenhöhe >= 44px.

4  Registrierungen und Kennungen
                75 Zeilen im Datensatz, 56 ohne Kennung. Deshalb KEINE Tabelle
                voller Striche, sondern eine Satzliste:

                Social Welfare Council (Nepal)
                  Keine Registriernummer gefunden. Quelle nicht erreichbar
                  (swc.org.np, 28.08.2026).                      [Marke ▸]

                IATI
                  NP-SWC-12345                                   [Marke ▸]
                  Verbindungsschlüssel zu anderen Datensätzen.

                Die IATI-Zeile ist hervorgehoben (nicht farblich, sondern durch
                den erklärenden Satz), weil sie der Join-Schlüssel ist.
                Die einzige horizontale Scrollbox der Seite liegt hier, falls
                lange Kennungen auf 360px nicht passen.

5  Finanzielle Transparenz — der leere Fall IST der gestaltete Fall
                Wenn keine Zahl: ein Absatz Fließtext, 17px, --ink, max 68ch:
                "Für diese Organisation wurden keine öffentlichen Finanzdaten
                 gefunden. Gesucht wurde in: <Liste>. Von den 14 nepalesischen
                 Organisationen in diesem Datensatz hat keine eine öffentliche
                 Einnahmenzahl. Das ist der Normalfall und kein Mangel dieser
                 Organisation."  -> Link auf /methodik
                Wenn Zahlen: <Amount> mit Währung, Geschäftsjahr und Umfang
                ausgeschrieben; program_ratio nur mit der Formel in der Notiz.
                Kein Balken, kein Ring, kein Prozent-Donut.

6  Öffentliche Hinweise
                Nur wenn warnings[] nicht leer (in v1: nie, siehe 4).
                --warn als einziges echtes Signal, optisch klar getrennt von
                "ungeprüft". Jeder Hinweis mit Quelle und Datum.

7  Was wir nicht wissen
                data_gaps + research_notes, offen ausgeschrieben, KEIN Accordion.
                Als <ul> mit einem Satz je Lücke, gruppiert nach gap_reason.
                Dieser Abschnitt wird nie eingeklappt und nie verkürzt.

8  Fehler gefunden?
                Ein Satz + Link auf /korrekturen + mailto mit vorbefülltem Betreff
                (org_id und Datum im Betreff, damit Meldungen zuordenbar sind).
```

**Druck:** `@page { margin: 18mm }`, Header/Footer/Schalter `display: none`, alle
`.datum-expanded` sichtbar, URLs unter jedem Link ausgeschrieben, `break-inside: avoid` je
`<section>`.

### 8.4 Vertrauensseiten (WP3)

- **`/methodik`** — die fünf Grade je ein Satz (identisch mit 7.3), dazu: was „nicht gefunden"
  bedeutet und was nicht, die vier `gap_reason`-Fälle, die Grenzen aus
  `machbarkeit-report.md`, und der Satz „Wir bewerten nicht und empfehlen nicht."
- **`/quellen`** — je Quelle: Name, Lizenz, letzter Abruf, Link. Plus Download des Datensatzes
  als JSON (statische Datei, kein Endpunkt).
- **`/korrekturen`** — am Tag 1 mit den zwei realen Stichprobenfehlern gefüllt (NRNA
  `since_year`, UNICEF `income`). Tabelle: Datum · Organisation · Feld · vorher · nachher ·
  Quelle. Keine leere Seite, kein „Bisher keine Korrekturen".
- **`/impressum`, `/datenschutz`** — Inhalte kommen von Chris. Bis dahin steht dort ein
  sichtbarer Platzhalter „Angaben werden vor der Veröffentlichung ergänzt", kein Lorem ipsum
  und keine erfundene Anschrift. Beide Seiten werden bis dahin mit `noindex` ausgeliefert.

---

## 9. i18n

**Locales:** `de` (Default), `en`. `localePrefix: 'always'`. Dateien:
`messages/de/<ns>.json`, `messages/en/<ns>.json`.

| Namespace | Eigentümer | Inhalt |
|---|---|---|
| `common` | **Lead, WP0. Kein Worker ändert diese Datei.** | Shell, Footer, Sprachumschalter, Theme, Skip-Link, `datum.*` (Wörter, Grad-Sätze, a11y-Labels), `verification.*`, `gapReason.*`, `orgType.*`, `amount.*`, Datums- und Zahlenformate |
| `board` | WP1 | Board, Tabs, Filter, Zahlenzeile, Locator-Bildunterschrift, Board-Metadaten |
| `org` | WP2 | Die acht Abschnitte, Leerfall-Absätze, Registrierungsnamen, Org-Metadaten |
| `pages` | WP3 | Methodik, Quellen, Korrekturen, Impressum, Datenschutz, `sitemap`/`robots`-nahe Texte |

Braucht ein Worker einen neuen Schlüssel in `common`, schickt er mir eine Einzeiler-Anfrage;
ich lande sie, er rebased. Das ist dieselbe Kollisionsregel wie beim Backend für
`packages/core`.

**Client-Payload:** `NextIntlClientProvider` bekommt **nur** die Namespaces, die
Client-Komponenten wirklich brauchen (`common.datum`, `board.filter`), nicht das ganze
Nachrichtenobjekt. Alles andere wird serverseitig gerendert.

**Copy-Regeln (gelten für DE und EN):**

1. Keine Gedankenstriche in nutzersichtbarem Text. Komma oder Punkt.
2. Keine Versalien-Überschriften, kein `letter-spacing`, keine Emojis.
3. Satzform statt Stichwort, wo eine Aussage gemacht wird. „Gesucht und nicht gefunden."
   statt „n/a".
4. Aussagen über Register nie als Aussagen über Organisationen formulieren.
5. Kein Superlativ, kein Werbewort, kein „vertrauenswürdig", „geprüft" im Sinne von Gütesiegel.
6. Beträge nie ohne Basis. Immer über `<Amount>`.
7. Deutsche Strings sind im Schnitt 25 bis 35 % länger als englische. Jeder Screenshot-Test
   läuft in beiden Sprachen; der deutsche String-Überlauf ist ausdrücklich Fehlermodus Nr. 1
   bei G2.

---

## 10. Performance- und A11y-Budget

| Größe | Grenze | Wie geprüft |
|---|---|---|
| Board-Datenprojektion | ≤ 60 KB roh, ≤ 12 KB brotli | Vitest-Test serialisiert die Projektion und misst; heute 40,0 KB / ~11,7 KB gzip |
| First Load JS | ≤ 155 KB gz (öffentliche Seiten) | `scripts/check-bundle.mjs` summiert die Modul-Skripte jeder vorgerenderten Seite. **Korrigiert am 28.08.:** die 110 KB aus dem Spec sind auf diesem Stack nicht erreichbar. Gemessen kostet Next 16 mit `cacheComponents` plus next-intl rund 127 KB auf einer reinen Weiterleitung und 145,9 KB auf einer Vertrauensseite, die nur die Shell und Prosa rendert. Der PO hat 155 KB gesetzt. Board 151,2, Org-Seiten 147,4. `/dev/*` zählt nicht mit. |
| Drittanbieter-Requests | **0** | Playwright zählt `page.on('request')` nach Host; jeder Host außer `localhost` ist ein Fehler |
| Clientseitiges Daten-Fetching | **0** | dito: kein `fetch` nach `load` |
| LCP mobil | ≤ 1,5 s | Lighthouse CI |
| CLS | ≤ 0,02 | Lighthouse CI |
| INP | ≤ 150 ms | Lighthouse CI |
| Lighthouse | Perf ≥ 95, A11y 100, BP ≥ 95, SEO ≥ 95 | `lighthouserc.json`, Board de + en + eine Org-Seite, mobiler Default-Preset, `numberOfRuns: 3` |
| axe | 0 Violations, Tags `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, `wcag22aa` | `@axe-core/playwright`, hell und dunkel, de und en |
| Kontrast | Body ≥ 7:1, Fokusring ≥ 3:1 | gemessen in 5.1/5.2, plus axe |
| Zoom | 200 % ohne horizontales Scrollen (außer Registrierungstabelle) | Playwright bei 1280x720 mit `deviceScaleFactor` bzw. 640 px Breite |

Renderstrategie: alles statisch. `generateStaticParams` liefert 2 Locales x 44 Orgs = 88 Org-Seiten
plus 2 Board-Seiten. `use cache` mit `cacheTag('crisis:<glide_id>')` bzw. `cacheTag('org:<id>')`,
`cacheComponents: true` in `next.config.ts`. On-demand-Invalidierung über einen einzigen Route
Handler `app/api/revalidate/route.ts`, der ein Bearer-Secret prüft und
**`revalidateTag(tag, 'hours')` mit zweitem Argument** aufruft (Next 16 verlangt es).
Der Handler ist die einzige nicht-statische Route der Anwendung.

**Hot Path** (performance-spotter Level 0): der Board-Filter. Er läuft bei jedem Tastendruck
über 44 Zeilen mit bis zu 3 Aussagen, also maximal ~130 Objekte. Zugriffsmuster ist
Mengenzugehörigkeit (`district ∈ ausgewählt`), deshalb werden die aktiven Filter **einmal** in
`Set`s überführt und nicht je Zeile mit `Array.includes` durchsucht; die Normalisierung der
Namenssuche (`toLowerCase`, Diakritika) passiert **einmal beim Build** in einem vorbereiteten
`search_key`-Feld, nicht je Tastendruck. Bei 44 Zeilen wäre beides auch naiv schnell genug;
es wird trotzdem so gebaut, weil die Struktur den Unterschied macht, wenn Krise Nr. 2 kommt
(100x-Test: 4 400 Zeilen bleiben unter 16 ms).

Kein `useMemo`-Streuen: es gibt genau eine memoisierte Ableitung (gefilterte Liste) und einen
`useDeferredValue` für das Suchfeld. Sonst nichts.

---

## 11. Anti-Ranking-Checkliste (Gate G3)

Jede Zeile ist maschinell oder mit einer konkreten Handlung prüfbar. Ergebnis kommt in
`REVIEW_FINDINGS_WEB.md`.

1. `rg -i "beste|top|führend|empfohlen|vertrauenswürdig|best|leading|recommended|trusted" apps/web/messages apps/web/app apps/web/components` = 0 Treffer.
2. `rg "score|rating|grade|stars?|ranking|progress|meter|gauge" apps/web/components apps/web/lib` = 0 Treffer außer in Kommentaren, die das Verbot erklären.
3. `rg -P "[\x{2713}\x{2714}\x{2717}\x{2718}\x{274C}\x{2705}]" apps/web` = 0 Treffer.
4. `rg -i "ff6131|athenarun" apps/web` = 0 Treffer.
5. Kein Spendenaufruf. Der Link tragt ein neutrales Substantiv ("Offizieller
   Spendenweg"), nie eine Aufforderung. Maschinell: `npm run check:copy` (Teil von
   `verify`). Das Skript entfernt zuerst verneinte Formen, weil "Sie bewertet keine
   Organisation und empfiehlt keine Spende" und "Wir bewerten nicht und empfehlen nicht"
   das Versprechen des Produkts sind, und prueft dann auf Imperative ("jetzt spenden",
   "spenden Sie", "donate now") und Rangsprache ("empfohlen", "recommended", "beste
   Organisation"). Die alte Form dieser Zeile war `rg -i "...|donate|..." = 0 Treffer`;
   sie ist mit dem Aktionspfad unbrauchbar geworden, weil das Wort in 34 fremden
   Spenden-URLs, im Datensatz und im Modulnamen `lib/donation.ts` vorkommt. Ein
   Null-Treffer-Grep haette dort das Umbenennen des ehrlichen Dings erzwungen statt das
   Entfernen eines unehrlichen.
6. Sortier-Optionen enthalten keine Option nach Beleggrad. Manuell in `lib/filter.ts` gelesen.
7. Kein `text-muted`, `opacity-`, `italic`, `line-through`, `text-sm` an einem
   Nicht-gefunden-Wert: `rg "not_found|notFound" -A4 apps/web/components` gelesen, plus der
   Screenshot-Vergleich value gegen not_found aus `/dev/datum`.
8. Jede Zahl der Zahlenzeile führt in ≤ 2 Interaktionen zur Quelle: Zahl -> gefilterte Liste ->
   Beleg-Zeile ist ein Link. Manuell durchgeklickt, im Gate-Bericht protokolliert.
9. Kein Betrag ohne `basis`: `<Amount>` erzwingt es typseitig; `rg "€|EUR|CHF|USD|NPR" apps/web/components apps/web/app`
   findet keine Währung außerhalb von `amount.tsx` und den Nachrichten-Dateien.
10. Keine Farbe und keine Position tragen allein eine Qualitätsaussage: Screenshot in
    Graustufen (Playwright `filter: grayscale(1)`) muss vollständig lesbar bleiben.
11. `not_public` ist als Aussage über das Register formuliert. Der String wird wörtlich gelesen.
12. Keine Fotos: `rg -i "<Image|<img|\.jpg|\.jpeg|\.png|\.webp" apps/web/app apps/web/components`
    findet nur `opengraph-image.tsx`. (Das fruher hier genannte Locator-SVG wurde in
    G1/G2 entfernt, weil seine Geometrie erfunden war.)

13. Kein Zustand des Spendenwegs wird schwacher dargestellt als ein gefundener. "kein
    offizieller Spendenweg gefunden" tragt dieselbe Groesse, Staerke, Neigung, Deckkraft
    und Textdekoration wie ein gefundener Link; nur die beiden belegten Farbtoene
    unterscheiden sich, und die halt `scripts/contrast.mjs` innerhalb von 0,1. Geprueft
    im Computed-Style-Test in `e2e/board.spec.ts` ("a missing donation channel reads with
    the same weight as a found one"). Der Zustand selbst kommt aus `lib/donation.ts`,
    damit keine Ansicht ihn eigenmaechtig anders formuliert.

---

## 12. Anhang

### 12.1 Kontrast-Messung

Alle Werte in 5.1 und 5.2 stammen aus einem WCAG-Luminanz-Skript (sRGB-Linearisierung,
`(L1+0.05)/(L2+0.05)`). Es liegt als `apps/web/scripts/contrast.mjs` im Repo und läuft in CI
mit, damit eine Token-Änderung, die einen Kontrast unter die Grenze zieht, den Build bricht.
Insbesondere wird geprüft: `mark-doc` auf `mark-doc-tint` und `mark-open` auf `mark-open-tint`
dürfen **maximal 0,5 Stufen** auseinanderliegen. Das ist Regel A1 als Test.

### 12.2 Offene Punkte

**An den PO:**
1. Die drei Zahlen-Abweichungen aus 4.1 (44 statt 46 Aussagen, 6 statt 3 Distrikte,
   `NP0301` existiert nicht). Für das Frontend nicht blockierend, für den Spec-Text und das
   Backend-Gate PO-3 schon.
2. Impressum und Datenschutz: bis Chris die Angaben liefert, stehen sichtbare Platzhalter mit
   `noindex`. Bestätigung, dass das der gewünschte Zwischenstand ist.
3. Abweichung A1 (Marken-Farbe abgedunkelt) und A2 (Ink-Kontrast bleibt) zur Kenntnis.

**An das Backend:**
1. `apps/api/openapi.json`, auch als Stub, mit der exakten Serialisierung eines `datum`.
2. `gap_reason` (Schema v0.2) ist Voraussetzung für WP2, nicht für WP1.
3. Gaps mit `note: null` existieren in den Pilotdaten; der Invariant „Gap ⇒ note" hält heute
   nicht. Frontend fängt es ab, aber die Migration sollte es beheben.
4. `nepal-red-cross-society -> current_response[0].note` enthält ein U+FFFD an der Stelle eines
   Gedankenstrichs (Kodierungsfehler in der Quelldatei).
5. Distrikt-Aliasse, die die Daten brauchen: `Rasuwa district`/`Timure`/`Syabrubesi`/
   `Rasuwagadhi` -> `NP0329`; `Nuwakot district` -> `NP0328`; `Dhading district` -> `NP0330`;
   `Chitwan`/`Chitwan district`/`Chitwan district (Mugling)` -> `NP0335` (HAPI schreibt
   „Chitawan"); `Gorkha district` -> `NP0436`; `Nepal` und die zwei Fluss-Formulierungen ->
   „ohne Ortsangabe".

### 12.3 Quellenliste

- `design-system.service.gov.uk/styles/type-scale/`
- `design-system.service.gov.uk/styles/colour/`
- `design-system.service.gov.uk/components/checkboxes/`
- `design-system.service.gov.uk/components/summary-list/`
- `design-patterns.service.justice.gov.uk/components/filter/`
- `projects.propublica.org/nonprofits/organizations/131760110`
- `offshoreleaks.icij.org/nodes/80000001`
- `opensanctions.org/docs/statements/`
- `opensanctions.org/datasets/`
- `next-intl.dev/docs/getting-started/app-router/with-i18n-routing`
- `next-intl.dev/docs/routing/middleware`
- context7 `/vercel/next.js` (version-16.mdx, proxy.mdx, font.mdx, use-cache-*.mdx, route-handlers)
- context7 `/amannn/next-intl` (routing/configuration.mdx, navigation, middleware factory)
- context7 `/shadcn-ui/ui` (tailwind-v4.mdx, customization.md)
- context7 `/websites/radix-ui_primitives` (popover.md)
- `tailwindcss.com/docs/theme`
- `github.com/dequelabs/axe-core-npm` (packages/playwright)
- `github.com/GoogleChrome/lighthouse-ci/blob/main/docs/configuration.md`
