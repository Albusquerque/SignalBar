import test from "node:test";
import assert from "node:assert/strict";
import { batteryChange, batteryCharging, batteryPercent, controllerList } from "../../src/controller_battery";

test("controller list keeps stable Steam indices and does not invent a charge", () => {
  assert.deepEqual(controllerList([{ nControllerIndex: 1, strName: "DualSense", bWireless: true }]), [
    { id: "steam:1", name: "DualSense", percent: null, level: null, charging: null },
  ]);
  assert.equal(controllerList({ nControllerIndex: 1 }), null);
});

test("battery callback and state values accept explicit percentages", () => {
  assert.deepEqual(batteryChange([{ unControllerIndex: 2, nBatteryPercentage: 76, bCharging: true }]),
    { index: 2, percent: 76, level: null, charging: true });
  assert.deepEqual(batteryChange([2, 64, false]), { index: 2, percent: 64, level: null, charging: false });
  assert.equal(batteryPercent({ sBatteryLevel: 91 }), 91);
  assert.equal(batteryCharging({ bCharging: false }), false);
});

test("coarse or invalid battery values are not presented as exact percentages", () => {
  assert.equal(batteryPercent({ sBatteryLevel: 3 }), null);
  assert.equal(batteryPercent({ sBatteryLevel: 65535 }), null);
  assert.equal(batteryPercent({ nBatteryPercent: 150 }), null);
  assert.deepEqual(batteryChange([1, 2]), { index: 1, percent: null, level: 2, charging: null });
});
