import test from "node:test";
import assert from "node:assert/strict";
import { batteryPercent, controllerItem, messageBody, isSteamControllerStore, storeControllerItem } from "../../src/controller_battery";

test("current SteamInputManager schema: percentages include 0 and 1, not coarse levels", () => {
  for (const value of [0, 1, 2, 4, 50, 100]) assert.equal(batteryPercent(value), value);
  for (const value of [undefined, null, 255, -1, NaN, "50", true]) assert.equal(batteryPercent(value), null);
  const item = controllerItem({ controller_index: 0, name: "Steam Controller", serial_number: "private",
    controller_type: 2, battery_level: 72, is_wireless_steam_dongle: true, is_charging: false })!;
  assert.equal(item.percent, 72);
  assert.equal(item.name, "Steam Controller");
  assert.equal(item.level, null);
  assert.equal(item.charging, false);
  assert.ok(!item.id.includes("private"));
});

test("unknown battery is not an empty battery; identity does not follow reused controller slot", () => {
  const raw = { controller_index: 0, name: "Steam Controller" };
  assert.equal(controllerItem(raw)?.percent, null);
  assert.equal(controllerItem({ ...raw, battery_level: 0, is_bluetooth: false, is_wireless_steam_dongle: false })?.percent, null);
  assert.equal(controllerItem({ ...raw, battery_level: 0, is_bluetooth: true })?.percent, 0);
  assert.notEqual(controllerItem({ ...raw, serial_number: "a" })?.id, controllerItem({ ...raw, serial_number: "b" })?.id);
  assert.equal(controllerItem({ ...raw, serial_number: "a" })?.id, controllerItem({ ...raw, serial_number: "a", controller_index: 3 })?.id);
  assert.equal(controllerItem({ controller_index: -1 }), null);
  assert.equal(controllerItem({ controller_index: 0xffffffff }), null);
});

test("ignore built-in/virtual devices, retain old and new Steam Controllers", () => {
  for (const type of [4, 21, 100, 101, 102, 120, 130, 400, 800])
    assert.equal(controllerItem({ controller_index: 0, controller_type: type }), null);
  for (const type of [2, 3, 10, 30, 34])
    assert.ok(controllerItem({ controller_index: 0, controller_type: type }));
  assert.equal(controllerItem({ controller_index: 0, is_remote_device: true }), null);
  assert.throws(() => messageBody([65]), /unreadable/);
});

test("SteamUI store discovery only accepts the controller store and maps its actual fields", () => {
  assert.equal(isSteamControllerStore({ GetController() {}, GetControllers() {} }), false);
  assert.equal(isSteamControllerStore({ GetController() {}, GetControllers() {}, fnOnControllerBatteryState() {} }), true);
  assert.equal(storeControllerItem({ nControllerIndex: 1, strName: "Steam Controller", ucBatteryLevel: 41,
    bWireless: true, bCharging: false })?.item.percent, 41);
  assert.equal(storeControllerItem({ ucBatteryLevel: 100 }), null);
});
