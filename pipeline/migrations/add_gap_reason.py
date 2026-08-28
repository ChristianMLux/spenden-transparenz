"""Backfill gap_reason (schema v0.2) into the pilot records.

Run once:  python pipeline/migrations/add_gap_reason.py
Idempotent: a second run over already-migrated files changes nothing.

The classification is derived, never invented. In order, first match wins:

  1. the note says the source did not answer          -> source_unreachable
  2. the note says the source does not publish it     -> not_public
  3. the note describes a search, or the path is
     listed in the record's data_gaps                 -> searched_not_found
  4. otherwise                                        -> not_searched

Order matters between 1 and 2: an unreachable source cannot tell us what it publishes, so recording
it as not_public would be a claim we cannot support.

Where a gap carries no note at all, a minimal factual one is written so that the invariant
"a gap has a note and a reason" holds. That note states only what the record already implies
through data_gaps; it never asserts anything about the organisation.

Measured on the dataset before the migration: 420 datums, 263 of them gaps, 117 with a note and
146 without, 238 listed in data_gaps and 25 not.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BATCH_DIR = REPO / "data" / "orgs"

DATUM_KEYS = {"value", "source_url", "retrieved_at", "verification"}

UNREACHABLE = re.compile(
    r"unreachable|http\s*40\d|\b40[13]\b|blocked|could not be (?:read|opened|fetched|retrieved)"
    r"|did not (?:respond|answer)|timed out|timeout|not (?:reachable|accessible)"
    r"|returned (?:an )?error",
    re.IGNORECASE,
)
NOT_PUBLIC = re.compile(
    # (?:ö|oe): the notes use both the umlaut and its transliteration. A character class would
    # match the o of "oe" and then fail on the e.
    r"not publish|does not publish|do not publish|nicht ver(?:ö|oe)ffentlicht"
    r"|not public(?:ly)?|no public (?:split|breakdown|figure)|not disclosed|does not disclose",
    re.IGNORECASE,
)

GENERATED_NOTE = {
    "searched_not_found": "Searched in the 2026-08-28 research pass; not found.",
    "not_searched": "Not searched in this research pass.",
    "source_unreachable": "Source did not answer during the 2026-08-28 research pass.",
    "not_public": "Source states this is not published.",
}

# A note we wrote ourselves is bookkeeping, not evidence. Reading one back as "a researcher looked
# into this" flipped every not_searched gap to searched_not_found on the second run - which is
# exactly the distinction the field exists to keep.
GENERATED_NOTES = frozenset(GENERATED_NOTE.values())


def _is_researcher_note(note: str) -> bool:
    stripped = note.strip()
    return bool(stripped) and stripped not in GENERATED_NOTES


INDEX = re.compile(r"\[\d+\]")


def normalise_path(path: str) -> str:
    """registrations[2].identifier -> registrations[].identifier"""
    return INDEX.sub("[]", path)


def walk_datums(obj: object, path: str = "") -> Iterator[tuple[str, dict]]:
    """Yield (path, datum) for every node that carries provenance.

    Same traversal as pipeline/probes/validate_orgs.py, duplicated here on purpose: the probes are
    frozen research artefacts and this migration must not depend on their import path staying
    script-relative.
    """
    if isinstance(obj, dict):
        if DATUM_KEYS <= obj.keys():
            yield path, obj
        for key, value in obj.items():
            yield from walk_datums(value, f"{path}.{key}" if path else key)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from walk_datums(value, f"{path}[{index}]")


def derive_gap_reason(datum: dict, path: str, data_gaps: set[str]) -> str | None:
    """None when the datum carries a value. Otherwise the reason the value is missing."""
    if datum.get("value") is not None:
        return None
    note = datum.get("note") or ""
    if UNREACHABLE.search(note):
        return "source_unreachable"
    if NOT_PUBLIC.search(note):
        return "not_public"
    if _is_researcher_note(note) or normalise_path(path) in data_gaps:
        return "searched_not_found"
    return "not_searched"


def derive_registration_gap_reason(registration: dict) -> str | None:
    """A register row with a null identifier stays in the record and says why.

    That row is often the most honest line on an organisation page: "the register did not answer"
    is a statement about the register, not about the organisation.
    """
    if registration.get("identifier") is not None:
        return None
    note = registration.get("note") or ""
    if UNREACHABLE.search(note):
        return "source_unreachable"
    if NOT_PUBLIC.search(note):
        return "not_public"
    if _is_researcher_note(note):
        return "searched_not_found"
    return "not_searched"


def _detect_indent(text: str) -> int:
    """Match the file's existing indent so the diff stays as small as the content change allows."""
    for line in text.splitlines()[1:]:
        stripped = line.lstrip(" ")
        if stripped and stripped != line:
            return len(line) - len(stripped)
    return 1


def migrate_org(org: dict) -> int:
    """Add gap_reason (and a minimal note where missing) in place. Returns the number of changes."""
    changed = 0
    data_gaps = {normalise_path(g) for g in org.get("data_gaps", [])}

    for path, datum in walk_datums(org):
        reason = derive_gap_reason(datum, path, data_gaps)
        if datum.get("gap_reason") != reason:
            datum["gap_reason"] = reason
            changed += 1
        if reason is not None and not (datum.get("note") or "").strip():
            datum["note"] = GENERATED_NOTE[reason]
            changed += 1

    for registration in org.get("registrations", []):
        reason = derive_registration_gap_reason(registration)
        if registration.get("gap_reason") != reason:
            registration["gap_reason"] = reason
            changed += 1
        if reason is not None and not (registration.get("note") or "").strip():
            registration["note"] = GENERATED_NOTE[reason]
            changed += 1

    return changed


def load_orgs() -> list[dict]:
    """The 44 organisations, deduplicated the same way validate_orgs.load_batches does.

    caritas-nepal appears in both batch-2 and batch-3; the first occurrence wins, which is what
    the validator, the dataset and the API all see. The migration itself still writes every record
    in every file, so the files stay internally consistent - only this read view dedupes.
    """
    orgs: list[dict] = []
    seen: set[str] = set()
    for path in sorted(BATCH_DIR.glob("batch-*.json")):
        for org in json.loads(path.read_text(encoding="utf-8-sig")):
            org_id = org.get("org_id")
            if org_id in seen:
                continue
            seen.add(org_id)
            orgs.append(org)
    return orgs


def main() -> None:
    total_changes = 0
    for path in sorted(BATCH_DIR.glob("batch-*.json")):
        text = path.read_text(encoding="utf-8-sig")
        indent = _detect_indent(text)
        batch = json.loads(text)

        changes = sum(migrate_org(org) for org in batch)
        total_changes += changes

        if changes:
            with path.open("w", encoding="utf-8", newline="\n") as handle:
                json.dump(batch, handle, ensure_ascii=False, indent=indent)
                handle.write("\n")
        print(f"{path.name}: {changes} changes (indent {indent})")

    print(f"total: {total_changes} changes")
    if total_changes == 0:
        print("nothing to do - already migrated")


if __name__ == "__main__":
    main()
