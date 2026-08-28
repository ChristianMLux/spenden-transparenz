# scripts/

The research probes moved to [`pipeline/probes/`](../pipeline/probes/) when the pipeline was built.
They are frozen there: they document how the pilot dataset was produced, and re-running one must
reproduce the same raw files under `data/raw/<source>/`.

Run a probe from the repository root:

```
python pipeline/probes/probe_reliefweb.py
python pipeline/probes/validate_orgs.py --spotcheck 0.12
```

Exactly one line changed in the move: `common.ROOT` now resolves two directories up instead of one,
so `data/raw/` still means the repository's `data/raw/`.

`scripts/validate_orgs.py` stays here as a four-line shim because that path is named in the project
documentation and in the gate commands. Everything else is gone from this directory on purpose -
a dozen forwarding stubs in a public repository is noise, not compatibility.

`validate_orgs.spotcheck()` fetches source URLs over the network. It is a command-line tool only and
is never reachable from the API.
