"use client";

import { Suspense, lazy, useState, type ReactNode } from "react";
import { Mark, type MarkKey } from "./marks";

// Radix Popover costs 30.6 KB gzipped and only the organisation page pulls it in, through
// this chip. A popover is by definition something a reader chooses to open, so none of it
// belongs in first load. Until someone activates a chip this renders a plain button; the
// Radix half arrives on activation and replays that activation against itself.
const DatumPopover = lazy(() => import("./datum-popover"));

/**
 * The chip that opens the provenance. Everything visible is decided on the server and
 * arrives as props; this component exists only because a popover needs state.
 *
 * Accessibility, and the reason the deferral does not cost any of it:
 * - Before activation the button carries its own aria-haspopup="dialog" and
 *   aria-expanded="false", so assistive technology describes it correctly with no
 *   JavaScript loaded beyond this component.
 * - After activation Radix takes over the same attributes and, because it follows the
 *   Dialog WAI-ARIA pattern, moves focus into the content, closes on Escape and returns
 *   focus to the trigger. That behaviour is asserted by the keyboard tests, so it keeps
 *   coming from Radix rather than being reimplemented.
 * - The Suspense fallback is the same button, so nothing moves or disappears while the
 *   chunk loads.
 * - The chip is 24px tall and its hit area is extended to 44px by an ::after that does not
 *   affect layout. Any row containing one is at least 44px tall, so the hit areas of
 *   neighbouring rows cannot overlap.
 */
export function DatumTrigger({
  mark,
  label,
  triggerLabel,
  headingId,
  toneClassName,
  children,
}: {
  mark: MarkKey;
  label: string;
  triggerLabel: string;
  headingId: string;
  toneClassName: string;
  children: ReactNode;
}) {
  const [activated, setActivated] = useState(false);

  const className = `relative inline-flex min-h-6 items-center gap-1 px-1 py-0.5 text-xs ${toneClassName} after:absolute after:-inset-x-2 after:-inset-y-2.5 after:content-['']`;

  const placeholder = (
    <button
      type="button"
      aria-haspopup="dialog"
      aria-expanded={false}
      aria-label={triggerLabel}
      className={className}
      onClick={() => setActivated(true)}
    >
      <Mark mark={mark} />
      <span>{label}</span>
    </button>
  );

  if (!activated) return placeholder;

  return (
    <Suspense fallback={placeholder}>
      <DatumPopover
        mark={mark}
        label={label}
        triggerLabel={triggerLabel}
        headingId={headingId}
        toneClassName={toneClassName}
      >
        {children}
      </DatumPopover>
    </Suspense>
  );
}
