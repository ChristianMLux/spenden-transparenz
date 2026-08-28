# apps/web

Public web frontend for Spenden-Transparenz: who is responding to the Nepal 2026
flood, where, since when, and with which source.

Read before changing anything here:

1. `../../docs/superpowers/specs/2026-08-28-v1-katastrophenmodus-design.md`, section
   "Frontend (IA/UX)".
2. `DESIGN.md` in this directory. It is binding for tokens, the `<Datum>` contract,
   page skeletons and copy rules.
3. `../../docs/superpowers/plans/2026-08-28-web-v1.md` for the task breakdown and
   file ownership.

No ratings, no scores, no rankings, no donation buttons. Every displayed value
carries its provenance, and "nicht gefunden" is a designed state that is never
styled weaker than a found value.

## Commands

```
npm run dev            development server
npm run build          production build
npm start              serve the production build
npx tsc --noEmit       type check
npm run lint           eslint
```
