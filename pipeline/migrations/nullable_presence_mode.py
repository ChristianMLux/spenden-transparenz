"""Schema v0.3: nepal_presence.mode can be a gap.

Run once:  python -m pipeline.migrations.nullable_presence_mode
           (as a module, not as a script: it imports from its sibling migration)
Idempotent: a second run changes nothing.

Found by WP-A when ingest_orgs hit ck_org_datum_provenance: seven organisations carry
`nepal_presence.mode = "unknown"` with no source_url. The database was right to refuse them - a
value with no source is not a value - but the data was not wrong either.

The schema was. `datum_presence_mode` is the only datum type in the contract whose value cannot be
null; every other one has a `_nullable` variant. So a researcher who could not determine how an
organisation works in Nepal had exactly one way to say so: the enum member "unknown". All seven
also listed `nepal_presence.mode` in their `data_gaps`, and four wrote a note explaining what they
could not access. They were recording a gap in the only vocabulary the schema gave them.

This migration gives the schema the word it was missing, and converts those seven records to a
real gap. "unknown" stays a legal enum value: a source that explicitly says the mode is unclear is
a different, sourced claim, and that one should still be expressible.
"""

from __future__ import annotations

import json

from pipeline.migrations.add_gap_reason import (
    BATCH_DIR,
    GENERATED_NOTE,
    _detect_indent,
    normalise_path,
)

PATH = "nepal_presence.mode"


def is_unsourced_unknown(datum: dict) -> bool:
    """A mode of "unknown" with nothing behind it. A sourced "unknown" is left alone."""
    return datum.get("value") == "unknown" and not datum.get("source_url")


def convert(org: dict) -> int:
    """Turn an unsourced "unknown" mode into a gap. Returns the number of changes."""
    datum = org.get("nepal_presence", {}).get("mode")
    if datum is None or not is_unsourced_unknown(datum):
        return 0

    declared = {normalise_path(gap) for gap in org.get("data_gaps", [])}
    # Every one of the seven declared this path in data_gaps, so they searched. The fallback
    # exists only so the rule is complete, not because the data needs it.
    reason = "searched_not_found" if PATH in declared else "not_searched"

    changes = 0
    datum["value"] = None
    changes += 1
    if datum.get("gap_reason") != reason:
        datum["gap_reason"] = reason
        changes += 1
    if not (datum.get("note") or "").strip():
        datum["note"] = GENERATED_NOTE[reason]
        changes += 1
    return changes


def main() -> None:
    total = 0
    for path in sorted(BATCH_DIR.glob("batch-*.json")):
        text = path.read_text(encoding="utf-8-sig")
        indent = _detect_indent(text)
        batch = json.loads(text)

        changes = sum(convert(org) for org in batch)
        total += changes

        if changes:
            with path.open("w", encoding="utf-8", newline="\n") as handle:
                json.dump(batch, handle, ensure_ascii=False, indent=indent)
                handle.write("\n")
        print(f"{path.name}: {changes} changes")

    print(f"total: {total} changes")
    if total == 0:
        print("nothing to do - already migrated")


if __name__ == "__main__":
    main()
