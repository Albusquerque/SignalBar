import assert from "node:assert/strict";
import test from "node:test";

import { normalizeAppId } from "../../src/steam_app_id";

test("normalizes unsigned and signed Steam shortcut AppIDs", () => {
  assert.equal(normalizeAppId(42), 42);
  assert.equal(normalizeAppId(0xF1234567), 0xF1234567);
  assert.equal(normalizeAppId(0xF1234567 | 0), 0xF1234567);
  assert.equal(normalizeAppId(-1), 0);
  assert.equal(normalizeAppId(0), 0);
  assert.equal(normalizeAppId(Number.NaN), 0);
});
