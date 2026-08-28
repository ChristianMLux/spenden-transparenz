// One timestamp for the whole build.
//
// Nothing in the render path may call Date.now(): it makes static output
// non-reproducible, makes "retrieved 2 days ago" drift between the prerendered HTML and
// the hydrated DOM, and makes screenshot tests flaky. Pass this value down instead.
export const NOW = new Date(process.env.BUILD_NOW ?? "2026-08-28T14:57:00Z");
