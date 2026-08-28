"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Mark, type MarkKey } from "./marks";

/**
 * The Radix half of the provenance chip, in its own module so it can be loaded on demand.
 *
 * Radix Popover costs 30.6 KB gzipped and organisation pages were the only route pulling
 * it in. A popover is by definition something a reader chooses to open, so none of that
 * belongs in first load. datum-trigger.tsx renders a plain button until someone activates
 * a chip, then imports this.
 *
 * On mount it clicks its own trigger once. That looks odd, and the obvious alternative,
 * rendering with `open` already true, is what was tried first: Radix then never observes a
 * closed-to-open transition, so it does not run its focus management and focus is left on
 * a button that has just been unmounted. A Playwright test caught it. Driving the real
 * trigger instead means Radix does everything it normally does, including moving focus
 * into the content and returning it to this trigger on Escape.
 */
export default function DatumPopover({
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
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    // Drives an external widget rather than setting React state: this is the activation
    // the reader already performed, replayed against the component that has just arrived.
    triggerRef.current?.click();
  }, []);

  return (
    <Popover>
      <PopoverTrigger
        ref={triggerRef}
        type="button"
        aria-label={triggerLabel}
        className={`relative inline-flex min-h-6 items-center gap-1 px-1 py-0.5 text-xs ${toneClassName} after:absolute after:-inset-x-2 after:-inset-y-2.5 after:content-['']`}
      >
        <Mark mark={mark} />
        <span>{label}</span>
      </PopoverTrigger>
      <PopoverContent aria-labelledby={headingId}>{children}</PopoverContent>
    </Popover>
  );
}
