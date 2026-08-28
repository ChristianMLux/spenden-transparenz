# Spenden-Transparenz — Agent-Konventionen

Privates Open-Source-Projekt (MIT, public). **Kein AthenaRun-Produkt**: kein AthenaRun-Branding, keine Orange (#FF6131), kein UIKit/AppShell, keine Vault-Sessions.

## Was gebaut wird
Informations-Layer für Spender: wer reagiert auf eine Katastrophe, wo, seit wann, mit welcher Quelle. **Keine Bewertungen, keine Empfehlungen, keine Scores, keine Rankings — nie.** Jeder angezeigte Wert trägt Provenienz (`source_url`, `retrieved_at`, `verification`); „nicht gefunden" ist ein sichtbarer, gleichwertig gestalteter Zustand. Spec: `docs/superpowers/specs/2026-08-28-v1-katastrophenmodus-design.md`. Datenvertrag: `schema/org.schema.json` + `SCHEMA.md`.

## Layout
- `apps/web` — Next.js ≥ 16.3 (App Router, TS, Tailwind, shadcn, next-intl de/en). Nur das UI/UX-Team schreibt hier.
- `apps/api` — FastAPI (Python 3.13, async SQLAlchemy 2, Alembic). Ein Router pro Datei.
- `packages/core` — geteilte Models/Enums/Settings. **Nur der Backend-Lead schreibt hier und in `apps/api/alembic/versions/`.**
- `pipeline` — Ingestion-Jobs (idempotent, `ingestion_run` pro Lauf), `pipeline/probes/` = die Research-Skripte, unverändert.
- `data/`, `schema/`, `*.md` im Root — Research-Artefakte, nicht anfassen außer über Jobs.

## Regeln
1. **Provenienz-Invarianten** (Tests erzwingen sie): Wert ≠ null ⇒ `source_url`; Gap ⇒ `note` + `gap_reason`; `data_gaps ⊇ null-Pfade`; Zitat ≤ 40 Wörter und wörtlich im Quelltext; kein Org-Score irgendwo.
2. `report.body_text` ist fremdes Urheberrecht: intern, nie ausliefern. Ausgeliefert werden Zitat + Link.
3. Keine natürlichen Personen in der DB (keine Trustee-Namen, keine Autoren-Mails).
4. Serverseitige Fetcher nur mit Host-Allowlist; ReliefWeb ≤ 1 Request / 2 s, ehrlicher User-Agent.
5. Secrets nur über Env / `.env.spenden` (gitignored); `common.platform_key()` / `core.settings`. Nie in Logs, nie in `data/`.
6. Logs: JSON, eine Zeile pro Event, **keine Emojis**. Windows: Dateien mit `newline="\n"` schreiben.
7. Enums in Postgres als TEXT + CHECK. Migrationen nur vom Lead.
8. Vor jeder Library-API: Doku nachschlagen (context7). Vor „fertig": Befehl ausführen, Ausgabe lesen, dann behaupten.
9. Git: eigener Worktree + Branch pro Agent, nie `git stash`, PR gegen `main`, Merge nur nach grünem CI. Commit-Trailer wie vom Harness vorgegeben.
10. UI: keine Cards, keine Schatten, keine Ampelfarben, keine Fotos der Katastrophe, keine Tooltips für Provenienz (Popover), „nicht gefunden" nie schwächer als ein Wert. Details im Spec (Visual Brief).

## Befehle
```
# Python (uv lokal, requirements.txt pro Service für Railway)
uv sync            # in apps/api bzw. pipeline
ruff check . && ruff format --check .
pytest
alembic upgrade head          # apps/api, DATABASE_URL_SYNC
python -m pipeline.cli run <job>

# Web
cd apps/web && npm ci && npm run dev | npm run build | npx tsc --noEmit | npm run lint
```

## Skills (aus dem AthenaRun-Workspace, absolute Pfade in Agent-Prompts)
Generisch nutzbar: `ui-quality`, `performance-spotter`, `mobile-responsive`, `eye-friendly-light-mode`, `context7-mcp`, `security-hardening` (references/fastapi.md, nextjs.md), `app-implementer` (ohne AppShell-Schritt), `app-reviewer`, `safe-refactor`. **Nicht verwenden:** `athenarun-uikit`, `branding`.
