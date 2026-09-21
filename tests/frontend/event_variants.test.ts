import assert from "node:assert/strict";
import test from "node:test";
import { EVENT_VARIANTS } from "../../src/event_variants";

test("all mockup variants and original patterns are available per category", () => {
  assert.equal(EVENT_VARIANTS.notification.length, 6);
  assert.equal(EVENT_VARIANTS.achievement.length, 6);
  assert.equal(EVENT_VARIANTS.screenshot.length, 5);
  for (const [category, options] of Object.entries(EVENT_VARIANTS)) {
    assert.equal(new Set(options.map((option) => option.data)).size, options.length);
    assert.ok(options.every((option) => option.data.startsWith(`${category}-`)));
    assert.ok(options.every((option) => option.label && option.detail));
  }
});
