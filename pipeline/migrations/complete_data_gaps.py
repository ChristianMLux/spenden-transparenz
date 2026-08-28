"""Make data_gaps agree with the datums it summarises.

Run once:  python -m pipeline.migrations.complete_data_gaps
Idempotent: a second run changes nothing.

Found by WP-A's provenance-invariant test. Five datums are classified `searched_not_found` -
the researcher's own note says they looked and found nothing - but their path is missing from the
record's `data_gaps` list. CLAUDE.md's first invariant requires `data_gaps` to be a superset of the
null paths, so the record contradicts itself.

`data_gaps` is a hand-maintained summary of what the datums already say. Adding the paths the notes
already claim were searched asserts nothing new: the evidence is the note, and it is already there.
Which is why this migration only ever adds. It never removes a declared gap, because `data_gaps`
also legitimately names paths that are not datum nodes at all - `registrations[NP_SWC].identifier`,
`website`, `hq.city`, `current_response` - and those declarations are the researcher's, not ours to
tidy away.

`not_searched` paths are deliberately left out. `SCHEMA.md` defines `data_gaps` as "paths that
stayed empty after a real search", so listing something nobody searched for would make the list
claim more than the research does.
"""

from __future__ import annotations

import json

from pipeline.migrations.add_gap_reason import BATCH_DIR, _detect_indent, normalise_path, walk_datums

# A gap only belongs in data_gaps if someone actually looked.
SEARCHED = {"searched_not_found", "source_unreachable", "not_public"}


def missing_paths(org: dict) -> list[str]:
    """Normalised paths that are searched gaps but are not declared in data_gaps."""
    declared = {normalise_path(gap) for gap in org.get("data_gaps", [])}
    missing = {
        normalise_path(path)
        for path, datum in walk_datums(org)
        if datum.get("value") is None and datum.get("gap_reason") in SEARCHED and normalise_path(path) not in declared
    }
    return sorted(missing)


def complete(org: dict) -> int:
    """Append the missing paths in place. Returns the number added."""
    missing = missing_paths(org)
    if not missing:
        return 0
    org.setdefault("data_gaps", []).extend(missing)
    return len(missing)


def main() -> None:
    total = 0
    for path in sorted(BATCH_DIR.glob("batch-*.json")):
        text = path.read_text(encoding="utf-8-sig")
        indent = _detect_indent(text)
        batch = json.loads(text)

        added = 0
        for org in batch:
            count = complete(org)
            if count:
                print(f"  {org['org_id']}: +{count} ({', '.join(missing_paths(org)) or 'done'})")
            added += count
        total += added

        if added:
            with path.open("w", encoding="utf-8", newline="\n") as handle:
                json.dump(batch, handle, ensure_ascii=False, indent=indent)
                handle.write("\n")
        print(f"{path.name}: {added} paths added")

    print(f"total: {total} paths added")
    if total == 0:
        print("nothing to do - data_gaps already agrees with the datums")


if __name__ == "__main__":
    main()
