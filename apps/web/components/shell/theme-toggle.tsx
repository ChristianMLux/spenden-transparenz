"use client";

import { useSyncExternalStore } from "react";

type Choice = "system" | "light" | "dark";

const STORAGE_KEY = "spenden-theme";
const CHOICES = ["system", "light", "dark"] as const;

// A tiny external store rather than useState plus useEffect: the setting lives in
// localStorage, which is an external system, and useSyncExternalStore is the API that
// reads one without a cascading render on mount.
//
// All labels arrive as props. No client component in this app calls useTranslations, so
// next-intl's client runtime and the message catalogue never cross the wire.
const listeners = new Set<() => void>();

function subscribe(listener: () => void) {
  listeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

function getSnapshot(): Choice {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return CHOICES.includes(stored as Choice) ? (stored as Choice) : "system";
  } catch {
    return "system";
  }
}

function getServerSnapshot(): Choice {
  return "system";
}

function apply(choice: Choice) {
  const root = document.documentElement;
  root.classList.remove("light", "dark");
  const dark =
    choice === "dark" ||
    (choice === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  root.classList.add(dark ? "dark" : "light");
}

function select(choice: Choice) {
  try {
    window.localStorage.setItem(STORAGE_KEY, choice);
  } catch {
    // A browser with site data blocked still gets a working toggle for this page view.
  }
  apply(choice);
  for (const listener of listeners) listener();
}

/**
 * Three real radio buttons rather than a cycling icon button, so the current setting can
 * be read without pressing anything. Without JavaScript nothing here changes and the
 * prefers-color-scheme block in globals.css still delivers a correct dark mode.
 */
export function ThemeToggle({
  legend,
  labels,
}: {
  legend: string;
  labels: Record<Choice, string>;
}) {
  const choice = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  return (
    <fieldset className="flex flex-wrap items-center gap-3 border-0 p-0 text-sm">
      <legend className="sr-only">{legend}</legend>
      {CHOICES.map((option) => (
        <label key={option} className="flex min-h-11 cursor-pointer items-center gap-1">
          <input
            type="radio"
            name="theme"
            value={option}
            checked={choice === option}
            onChange={() => select(option)}
            className="size-4 accent-[var(--accent)]"
          />
          <span>{labels[option]}</span>
        </label>
      ))}
    </fieldset>
  );
}
