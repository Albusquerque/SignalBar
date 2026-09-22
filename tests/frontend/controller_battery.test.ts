import test from "node:test";
import assert from "node:assert/strict";
import {
  batteryChange,
  batteryCharging,
  batteryLevelList,
  batteryPercent,
  controllerList,
  mergeOrderedBatteryLevels,
} from "../../src/controller_battery";

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
  assert.equal(batteryPercent({ ucBatteryLevel: 64 }), 64);
  assert.equal(batteryCharging({ bCharging: false }), false);
});

test("SteamUI battery arrays preserve controller-list order", () => {
  assert.deepEqual(batteryLevelList([76, 19, 255]), [76, 19, null]);
  assert.deepEqual(batteryLevelList([{ ucBatteryLevel: 42 }]), [42]);
  assert.equal(batteryLevelList({ 0: 76 }), null);
  assert.deepEqual(mergeOrderedBatteryLevels([
    { id: "steam:2", name: "First", percent: null, level: 3, charging: null },
    { id: "steam:7", name: "Second", percent: 80, level: null, charging: false },
  ], [76, 19]), [
    { id: "steam:2", name: "First", percent: 76, level: null, charging: null },
    { id: "steam:7", name: "Second", percent: 19, level: null, charging: false },
  ]);
});

test("coarse or invalid battery values are not presented as exact percentages", () => {
  assert.equal(batteryPercent({ sBatteryLevel: 3 }), null);
  assert.equal(batteryPercent({ sBatteryLevel: 65535 }), null);
  assert.equal(batteryPercent({ nBatteryPercent: 150 }), null);
  assert.deepEqual(batteryChange([1, 2]), { index: 1, percent: null, level: 2, charging: null });
});
