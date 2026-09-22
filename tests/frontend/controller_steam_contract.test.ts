import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { setTimeout as delay } from "node:timers/promises";
import { ControllerMonitor, isSteamInputService } from "../../src/controller_monitor";
import type { ControllerBatteryUpdate } from "../../src/api";

// Optional, read-only contract check against the user's installed Steam code.
// No Valve bundle is copied into the repo. Transport is simulated: this is NOT
// a hardware test. The service wrapper and protobuf metadata are Valve's real
// loaded module, so method/signature tests do not merely echo our own fixtures.
test("installed Steam service namespace, protobuf fields and notification registrations", {
  skip: !process.env.SIGNALBAR_STEAM_UI_BUNDLE,
}, async () => {
  const factories: Record<string, Function> = {};
  const steam = { webpackChunksteamui: { push: (chunk: unknown[]) => Object.assign(factories, chunk[1]) } };
  vm.runInNewContext(fs.readFileSync(process.env.SIGNALBAR_STEAM_UI_BUNDLE!, "utf8"), { self: steam }, { timeout: 5000 });
  const factory = Object.values(factories).find(fn => fn.toString().includes('GetControllerListHandler={name:"SteamInputManager.GetControllerList#1"'));
  assert.ok(factory, "current Steam bundle must contain the service");
  const handlers = new Map<string, (message: unknown) => number>();
  const packet = (body: object) => ({ BSuccess: () => true, Body: () => ({ toObject: () => body }) });
  let queryName = "";
  const transport = { SendMsg: async (name: string, _request: unknown, responseClass: any) => {
    queryName = name;
    const raw = responseClass.M().fields.controllers.c.M().fields;
    for (const field of ["controller_index", "name", "serial_number", "battery_level", "is_charging", "is_bluetooth"])
      assert.ok(field in raw, `actual protobuf must include ${field}`);
    return packet({ controllers: [{ controller_index: 0, name: "Steam Controller", controller_type: 2,
      battery_level: 72, is_wireless_steam_dongle: true, is_charging: false }] });
  } };
  const registry = { RegisterServiceNotificationHandler: (description: any, handler: (message: unknown) => number) => {
    if (description.name.includes("BatteryState")) {
      const fields = description.request.M().fields;
      assert.deepEqual(Object.keys(fields).sort(), ["battery_level", "charging", "controller_index"]);
    }
    handlers.set(description.name, handler);
    return { unregister: () => handlers.delete(description.name) };
  } };
  // The generated wrapper only needs these ports at module-initialisation /
  // schema-inspection time. We deliberately never create an input-feed object.
  const ports = { Message: class {}, qM: {}, gp: {}, I8: (_type: unknown, value: unknown) => value,
    OI: () => ({ GetDefaultTransport: () => transport, GetDefaultHandlerRegistry: () => registry }) };
  const require = Object.assign(() => ports, {
    d: (target: object, getters: Record<string, () => unknown>) => {
      for (const [key, get] of Object.entries(getters)) Object.defineProperty(target, key, { get, enumerable: true });
    },
    r: () => {}, n: (value: unknown) => () => value,
  });
  const exports = {};
  factory({}, exports, require);
  const service = Object.values(exports).find(isSteamInputService);
  assert.ok(service, "semantic Decky lookup must find Valve's actual export");
  const snapshots: ControllerBatteryUpdate[][] = [];
  const monitor = new ControllerMonitor({ discover: () => service, publish: async rows => { snapshots.push(rows); },
    diagnose: async () => {}, pollMs: 10000 });
  try {
    monitor.start(); await delay(5);
    assert.equal(queryName, "SteamInputManager.GetControllerList#1");
    assert.equal(snapshots.at(-1)?.[0].percent, 72);
    assert.equal(handlers.size, 3);
    assert.equal(handlers.get("SteamInputManager.NotifyControllerBatteryState#1")!(packet({ controller_index: 0, battery_level: 13, charging: true })), 1);
    await delay(3);
    assert.equal(snapshots.at(-1)?.[0].percent, 13);
    assert.equal(snapshots.at(-1)?.[0].charging, true);
  } finally { await monitor.stop(); }
  assert.equal(handlers.size, 0);
});
