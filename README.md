# Spenden-Transparenz — Research-Phase (Vertical Slice Nepal)

Informations-Layer für Spender: Organisationen vergleichen anhand aggregierter, **provenienz-markierter** Daten — keine Empfehlungen. Katastrophenmodus als Vertrauens-Bootstrap. Auslöser: Trishuli-Flut Nepal, 26.08.2026.

**Stand 2026-08-28: Machbarkeitsfrage beantwortet.** Kein Frontend, kein Backend, keine Architektur — das folgt in einer eigenen Scoping-Runde.

| Datei | Inhalt |
|---|---|
| [`machbarkeit-report.md`](machbarkeit-report.md) | 9 Datenquellen wirklich angezapft: Zugang, Nepal-Coverage, Aktualität, Lokal-Anteil, Provenienz-Grad, Katastrophen-Tauglichkeit; Extraktionstest; Datenqualität des Pilot-Datensatzes |
| [`orgs-nepal-2026.json`](orgs-nepal-2026.json) | 44 Organisationen, die auf die Flut reagieren (14 nepalesisch), jeder Wert mit Quelle, Abrufdatum, Verifizierungsgrad |
| [`SCHEMA.md`](SCHEMA.md) + [`schema/`](schema/) | Datenmodell v0.1 (JSON Schema) — das `datum`-Prinzip: `{value, source_url, retrieved_at, verification}` |
| [`case-studies.md`](case-studies.md) | Earthquake Response Transparency Portal 2015, GiveWell, GlobalGiving — was übernommen wird und was nicht |
| [`scripts/`](scripts/) | Re-runnable Probes pro Quelle (FTS, IATI, ReliefWeb, HAPI, ProPublica, UK Charity Commission, SWC) + Validierung/Provenienz-Stichprobe |
| `data/raw/<quelle>/` | Rohantworten mit Zeitstempel; Kennzahlen in `_summary.json`. Große Bulk-Dateien (UK-CC-Zips, IATI-CSVs) sind nicht eingecheckt — die Skripte laden sie nach |

## Reproduktion

```
python -m pip install requests jsonschema
cp .env.example .env.spenden   # Keys eintragen (IATI Datastore, UK Charity Commission; Firecrawl/ScraperAPI optional)
cd scripts
python probe_fts.py && python probe_iati.py && python probe_hapi.py && python probe_propublica.py
python probe_ukcc.py && python probe_ukcc_bulk_extra.py && python probe_ukcc_api.py
python probe_iati_datastore.py && python probe_reliefweb.py && python probe_swc.py
python validate_orgs.py --spotcheck 0.12
```

Python 3.13. Keys werden aus Umgebung → `.env.spenden` gelesen; `.env*` ist gitignored.

## Lizenz

Code, Schema, Datensatz (`orgs-nepal-2026.json`) und Texte dieses Repos: [MIT](LICENSE). Nutzen, kopieren, verändern — nur der Hinweis bleibt drin.

Rohdaten in `data/raw/` stammen von Dritten und bleiben unter deren Bedingungen: UK Charity Commission (Open Government Licence v3), IATI / d-portal / HDX (CC BY), OCHA FTS und HAPI (CC BY), ProPublica Nonprofit Explorer (IRS-Daten, gemeinfrei), ReliefWeb-Texte (Urheberrecht der jeweils genannten Quelle, hier nur als Recherche-Beleg gespeichert), SWC-Snapshots via Wayback Machine. Jeder Datenpunkt im Datensatz trägt seine `source_url`.
