"use client";

/**
 * What used to sit here was an inline SVG "Nepal outline" with six marks placed
 * "roughly" over the affected districts. It was invented: there is no district-polygon
 * data anywhere in this repo (data/raw/hapi/admin2_NPL.json carries codes and names
 * only) and no geojson to draw a real one from, so the shape and the mark positions
 * were both drawn from memory. On a product whose entire claim is that every value
 * carries its source and nothing is invented, a fabricated map in the most prominent
 * slot on the page was the one thing this product cannot do, however honest the
 * caption underneath it tried to be — a reader looks at the shape, not the caption.
 *
 * This replaces it with the same information in a form that is actually sourced: the
 * named districts and how many organisations reported a response in each, straight
 * from board.facets.districts, each name a link into the same one-district filter the
 * "6 Distrikte" number-line link already applies for all of them at once — this
 * spells the aggregate out into its individual destinations rather than adding a new
 * kind of link. No shape, no relative sizing, no bars — a sized bar would smuggle
 * back in exactly the same "looks like a chart of severity" problem in a different
 * medium, and this section carries no ranking of any kind.
 */
export function DistrictSummary({
  heading,
  districts,
  hrefFor,
  onSelect,
}: {
  heading: string;
  districts: { code: string; name: string; count: number }[];
  hrefFor: (code: string) => string;
  onSelect: (code: string) => void;
}) {
  return (
    // No max-width: this is a compact meta line in the register of the number line
    // above it (also unconstrained), not a reading-flow paragraph, so it is allowed
    // to use the full row rather than wrap early (review defect 1 fold budget).
    <p className="text-sm text-ink">
      <span className="text-muted">{heading}: </span>
      {districts.map((d, i) => (
        <span key={d.code}>
          {i > 0 && ", "}
          <a
            href={hrefFor(d.code)}
            onClick={(e) => {
              e.preventDefault();
              onSelect(d.code);
            }}
            className="text-accent underline underline-offset-2"
          >
            {d.name}
          </a>{" "}
          <span className="text-muted">({d.count})</span>
        </span>
      ))}
    </p>
  );
}
