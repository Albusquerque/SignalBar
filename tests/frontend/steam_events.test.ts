import assert from "node:assert/strict";
import test from "node:test";

import { classifySteamNotification, screenshotWasCaptured } from "../../src/steam_events";

test("every valid Steam notification type maps to a light signal", () => {
  assert.equal(classifySteamNotification(5), "achievement");
  assert.equal(classifySteamNotification(14), "screenshot");
  assert.equal(classifySteamNotification(55), "record-start");
  assert.equal(classifySteamNotification(56), "record-stop");
  assert.equal(classifySteamNotification(8), "notification");
  assert.equal(classifySteamNotification(31), "notification");
  assert.equal(classifySteamNotification(27), "notification"); // Community comment
  assert.equal(classifySteamNotification(45), "notification"); // parental warning
  assert.equal(classifySteamNotification(1), "notification"); // download completion
  assert.equal(classifySteamNotification(99), "notification"); // future Steam type
  for (let type = 1; type <= 58; type++) {
    assert.notEqual(classifySteamNotification(type), null, `Steam type ${type}`);
  }
  assert.equal(classifySteamNotification(0), null);
  assert.equal(classifySteamNotification(NaN), null);
});

test("a deleted screenshot never plays the capture signal", () => {
  assert.equal(screenshotWasCaptured({ strOperation: "written" }), true);
  assert.equal(screenshotWasCaptured({ strOperation: "deleted" }), false);
  assert.equal(screenshotWasCaptured(null), false);
});
