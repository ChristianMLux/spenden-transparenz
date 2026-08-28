"""Schema v0.4: every researched response states its own classification.

Run once:  python -m pipeline.migrations.explicit_classification
Idempotent: a second run changes nothing.

The loader used to derive `activity_type` and `amount_basis` from keywords in the activity
sentence. The PO read all 44 researched responses against that derivation and found 14 wrong -
roughly a third - and several of them not merely imprecise but false:

  malteser-international  "activities in project regions temporarily paused" -> appeal_launched
  plan-international      a public statement                                 -> amount_basis disbursed
  wfp-nepal               food rations dispatched                            -> amount_basis released
  the-rising-youth-club   "the club would deploy"                            -> amount_basis pledged
  drk                     "NRCS teams dispatched, tarpaulins, water"         -> appeal_launched
  mercy-corps             "coordinating with authorities"                    -> medical
  world-vision            "preparing emergency assistance"                   -> wash

Three of those invent a financial claim out of a sentence containing no money at all. On the board
`amount_basis` is rendered next to the figure, so "disbursed" on a statement with no amount is the
product asserting a payment nobody reported. That is the single most damaging thing this product
could get wrong, and no keyword table is worth that risk.

So the classification is data now, not inference. A person read each sentence; the value is written
into the record beside the sentence it came from; and the loader uses what it finds or falls back
to `other` / `reported`, which claim nothing. It never guesses.

The 14 corrections below are the PO's readings. The other 30 keep the labels the derivation
produced, which the PO also read and confirmed - they are written out explicitly all the same, so
that no value on the board depends on a keyword matching next time the sentences change.
"""

from __future__ import annotations

import json

from pipeline.migrations.add_gap_reason import BATCH_DIR, _detect_indent

# (org_id, index in current_response) -> (activity_type, amount_basis)
#
# amount_basis is only pledged/appeal/raised/released/disbursed where the sentence says so. With no
# amount it stays "reported" unless the sentence is explicitly an appeal.
CLASSIFICATION: dict[tuple[str, int], tuple[str, str]] = {
    # --- the PO's 14 corrections ---------------------------------------------------------------
    ("malteser-international", 0): ("presence_declared", "reported"),
    ("plan-international-nepal", 0): ("presence_declared", "reported"),
    ("wfp-nepal", 0): ("relief_distribution", "reported"),
    ("the-rising-youth-club", 0): ("presence_declared", "reported"),
    ("drk-generalsekretariat", 0): ("relief_distribution", "reported"),
    ("mercy-corps", 0): ("coordination", "reported"),
    ("world-vision-nepal", 0): ("presence_declared", "reported"),
    ("caritas-international", 0): ("funding_pledged", "released"),
    ("diakonie-katastrophenhilfe", 0): ("assessment", "reported"),
    ("community-self-reliance-centre", 0): ("coordination", "reported"),
    ("hindu-swayamsevak-sangh-nepal", 0): ("relief_distribution", "reported"),
    ("mountain-heart-nepal", 0): ("medical", "reported"),
    ("direct-relief", 1): ("funding_pledged", "reported"),
    ("helvetas", 0): ("funding_pledged", "released"),
    # --- the other 30, read and confirmed, written out so nothing depends on a keyword ----------
    ("nepal-red-cross-society", 0): ("funding_pledged", "released"),
    ("nepal-red-cross-society", 1): ("relief_distribution", "reported"),
    ("nepal-red-cross-society", 2): ("assessment", "reported"),
    ("ifrc", 0): ("appeal_launched", "appeal"),
    ("ifrc", 1): ("funding_pledged", "released"),
    ("unicef-nepal", 0): ("relief_distribution", "reported"),
    ("unicef-nepal", 1): ("assessment", "reported"),
    ("save-the-children-international", 0): ("relief_distribution", "reported"),
    ("msf-international", 0): ("assessment", "reported"),
    ("msf-international", 1): ("assessment", "reported"),
    ("oxfam-in-nepal", 0): ("appeal_launched", "appeal"),
    ("care-nepal", 0): ("assessment", "reported"),
    ("people-in-need-nepal", 0): ("appeal_launched", "appeal"),
    ("project-hope", 0): ("assessment", "reported"),
    ("habitat-humanity-nepal", 0): ("assessment", "reported"),
    ("direct-relief", 0): ("medical", "reported"),
    ("direct-relief", 2): ("medical", "reported"),
    ("dhulikhel-hospital", 0): ("medical", "reported"),
    ("globalgiving", 0): ("appeal_launched", "raised"),
    ("non-resident-nepali-association", 0): ("funding_pledged", "pledged"),
    ("non-resident-nepali-association", 1): ("relief_distribution", "reported"),
    ("hindu-swayamsevak-sangh-nepal", 1): ("search_and_rescue", "reported"),
    ("vishwa-hindu-parishad-nepal", 0): ("search_and_rescue", "reported"),
    ("nepal-lions-md325", 0): ("appeal_launched", "appeal"),
    ("worec-nepal", 0): ("appeal_launched", "appeal"),
    ("kiwanis-club-rupandehi-lumbini", 0): ("funding_pledged", "pledged"),
    ("welthungerhilfe", 0): ("funding_pledged", "released"),
    ("aktion-deutschland-hilft", 0): ("appeal_launched", "reported"),
    ("govinda-entwicklungshilfe", 0): ("presence_declared", "reported"),
    ("back-to-life", 0): ("medical", "reported"),
}


def classify(org_id: str, index: int) -> tuple[str, str] | None:
    return CLASSIFICATION.get((org_id, index))


def apply(org: dict) -> int:
    """Write the explicit classification onto each current_response entry. Returns changes made."""
    changed = 0
    for index, response in enumerate(org.get("current_response", [])):
        decided = classify(org["org_id"], index)
        if decided is None:
            continue
        activity_type, amount_basis = decided
        if response.get("activity_type") != activity_type:
            response["activity_type"] = activity_type
            changed += 1
        if response.get("amount_basis") != amount_basis:
            response["amount_basis"] = amount_basis
            changed += 1
    return changed


def main() -> None:
    total = 0
    seen = 0
    for path in sorted(BATCH_DIR.glob("batch-*.json")):
        text = path.read_text(encoding="utf-8-sig")
        indent = _detect_indent(text)
        batch = json.loads(text)

        changes = sum(apply(org) for org in batch)
        seen += sum(len(org.get("current_response", [])) for org in batch)
        total += changes

        if changes:
            with path.open("w", encoding="utf-8", newline="\n") as handle:
                json.dump(batch, handle, ensure_ascii=False, indent=indent)
                handle.write("\n")
        print(f"{path.name}: {changes} field writes")

    print(f"total: {total} field writes over {seen} responses")
    if total == 0:
        print("nothing to do - every response already states its classification")


if __name__ == "__main__":
    main()
