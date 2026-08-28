import { vi } from "vitest";

// `use cache` functions call cacheTag() and cacheLife() from next/cache. Outside a real
// Next build or server, which is exactly what a Vitest run is, there is no work-unit
// store for them to attach to and the real implementations throw.
//
// Mocking them once here rather than per file: WP1's filter.test.ts imported getBoard
// without knowing it had become a cached function in WP3's branch, and the failure only
// appeared when the two branches met. A shared setup removes the trap instead of
// patching one instance of it.
vi.mock("next/cache", () => ({
  cacheTag: vi.fn(),
  cacheLife: vi.fn(),
  revalidateTag: vi.fn(),
  updateTag: vi.fn(),
  revalidatePath: vi.fn(),
}));
