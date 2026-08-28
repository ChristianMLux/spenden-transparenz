"use client";

import { useId, type ReactNode } from "react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Mark, type MarkKey } from "./marks";

/**
 * The chip that opens the provenance. Everything visible is decided on the server and
 * arrives as props; this component exists only because a popover needs state.
 *
 * Accessibility:
 * - Radix follows the Dialog WAI-ARIA pattern, so the trigger gets aria-expanded and
 *   aria-controls, Escape closes and focus returns to the trigger.
 * - Radix does not name the content, so PopoverContent is labelled by the heading that
 *   DatumBody renders.
 * - The chip is 24px tall and its hit area is extended to 44px by an ::after that does
 *   not affect layout. Any row containing one is at least 44px tall, so the hit areas of
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
  const contentId = useId();

  return (
    <Popover>
      <PopoverTrigger
        type="button"
        aria-label={triggerLabel}
        className={`relative inline-flex min-h-6 items-center gap-1 px-1 py-0.5 text-xs ${toneClassName} after:absolute after:-inset-x-2 after:-inset-y-2.5 after:content-['']`}
      >
        <Mark mark={mark} />
        <span>{label}</span>
      </PopoverTrigger>
      <PopoverContent aria-labelledby={headingId} id={contentId}>
        {children}
      </PopoverContent>
    </Popover>
  );
}
