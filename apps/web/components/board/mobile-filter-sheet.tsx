"use client";

import { useEffect, useRef, type ReactNode } from "react";

/**
 * The mobile filter sheet, built on the native <dialog> element rather than a Radix
 * Dialog wrapped in a shadcn "sheet" component. Two reasons: components/ui/ is lead-only
 * (WP0 has not added a sheet primitive there, and this worker does not touch that
 * directory), and <dialog>.showModal() already gives a correct focus trap, Escape-to-
 * close and top-layer rendering in every evergreen browser, so nothing here has to
 * reimplement what the platform provides for free.
 */
export function MobileFilterSheet({
  open,
  onOpenChange,
  title,
  closeLabel,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  closeLabel: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      onClose={() => onOpenChange(false)}
      onClick={(e) => {
        // A click landing on the <dialog> element itself (not on any of its children)
        // is a click on the backdrop: native <dialog> has no light-dismiss of its own.
        if (e.target === e.currentTarget) onOpenChange(false);
      }}
      aria-labelledby="mobile-filter-title"
      className="fixed inset-x-0 bottom-0 top-auto m-0 max-h-[85dvh] w-full max-w-full border-t border-rule bg-surface p-4 [&::backdrop]:bg-ink/40"
    >
      <div className="flex items-center justify-between gap-4 border-b border-rule pb-3">
        <p id="mobile-filter-title" className="text-lg">
          {title}
        </p>
        <button
          type="button"
          onClick={() => onOpenChange(false)}
          className="min-h-11 min-w-11 px-2 text-sm text-ink"
        >
          {closeLabel}
        </button>
      </div>
      <div className="mt-3 max-h-[calc(85dvh-5rem)] overflow-y-auto overscroll-contain">
        {children}
      </div>
    </dialog>
  );
}
