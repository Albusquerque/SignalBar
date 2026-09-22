import test from "node:test";
import assert from "node:assert/strict";
import { setTimeout as delay } from "node:timers/promises";
import { ControllerMonitor, isSteamInputService } from "../../src/controller_monitor";
import type { ControllerTelemetry, SteamInputService } from "../../src/controller_monitor";
import type { ControllerBatteryUpdate } from "../../src/api";

const packet = (body: object) => ({ BSuccess: () => true, Body: () => ({ toObject: () => body }) });
const pad = (percent = 72, serial = "pad-one") => ({ controller_index: 0, controller_type: 2,
  name: "Steam Controller", serial_number: serial, battery_level: percent, is_wireless_steam_dongle: true, is_charging: false });
type Callback = (message: unknown) => number;

function rig() {
  const hooks = new Map<string, Callback>();
  let rows: object[] = [];
  let available = true;
  let uiRows: unknown;
  const register = (name: string) => (callback: Callback) => {
    hooks.set(name, callback);
    return { unregister: () => { hooks.delete(name); } };
  };
  const service: SteamInputService = {
    GetControllerListHandler: { name: "SteamInputManager.GetControllerList#1" },
    GetControllerList: async () => packet({ controllers: rows }),
    RegisterForNotifyControllerListChanged: register("list"),
    RegisterForNotifyControllerBatteryState: register("battery"),
    RegisterForNotifyControllerDisconnected: register("disconnect"),
  };
  const snapshots: ControllerBatteryUpdate[][] = [];
  const states: ControllerTelemetry[] = [];
  const monitor = new ControllerMonitor({
    discover: () => available ? service : undefined,
    readStore: () => uiRows,
    publish: async items => { snapshots.push(items); },
    diagnose: async state => { states.push(state); },
    pollMs: 10000, timeoutMs: 30,
  });
  return { service, snapshots, states, hooks, monitor,
    rows: (next: object[]) => { rows = next; },
    uiRows: (next: unknown) => { uiRows = next; },
    available: (next: boolean) => { available = next; },
    emit: (name: string, body: object = {}) => hooks.get(name)?.(packet(body)),
  };
}

test("discovers exact service, reads already-connected Steam Controller without opening settings", async () => {
  const r = rig();
  try {
    r.rows([pad()]); r.monitor.start(); await delay(3);
    assert.equal(isSteamInputService(r.service), true);
    assert.equal(isSteamInputService({ GetControllerList: () => {} }), false);
    assert.equal(r.snapshots.at(-1)?.[0].percent, 72);
    assert.equal(r.states.at(-1)?.phase, "ready");
    assert.equal(r.hooks.size, 3);
  } finally { await r.monitor.stop(); }
});

test("96/41 battery values survive repeated 96/100 roster snapshots and reordering", async () => {
  const r = rig();
  try {
    const first = pad(96);
    const second = { ...pad(100, "pad-two"), controller_index: 3 };
    r.rows([first, second]); r.monitor.start(); await delay(3);
    r.emit("battery", { controller_index: 3, battery_level: 41, charging: false }); await delay(3);
    r.uiRows([{ nControllerIndex: 3, strName: "Steam Controller", strSerialNumber: "pad-two",
      eControllerType: 2, ucBatteryLevel: 100, bWireless: true, bCharging: false }]);
    for (let i = 0; i < 3; i++) await r.monitor.refresh();
    assert.deepEqual(r.snapshots.at(-1)?.map(x => x.percent), [96, 41]);
    assert.equal(r.states.at(-1)?.devices?.[1].list_percent, 100);
    assert.equal(r.states.at(-1)?.devices?.[1].event_percent, 41);
    r.rows([second, first]); await r.monitor.refresh();
    assert.deepEqual(r.snapshots.at(-1)?.map(x => x.percent), [41, 96]);
    // Device identifiers, not array order or reusable index, carry telemetry.
    r.rows([first, { ...second, controller_index: 7 }]); await r.monitor.refresh();
    assert.deepEqual(r.snapshots.at(-1)?.map(x => x.percent), [96, 41]);
    r.rows([first]); await r.monitor.refresh();
    r.rows([first, second]); await r.monitor.refresh();
    assert.deepEqual(r.snapshots.at(-1)?.map(x => x.percent), [96, 100]);
  } finally { await r.monitor.stop(); }
});

test("startup reads SteamUI's already-updated 41% without waiting for another battery event", async () => {
  const r = rig();
  try {
    r.rows([pad(96), { ...pad(100, "pad-two"), controller_index: 1 }]);
    r.uiRows([{ nControllerIndex: 1, strName: "Steam Controller", strSerialNumber: "pad-two",
      eControllerType: 2, ucBatteryLevel: 41, bWireless: true, bCharging: false }]);
    r.monitor.start(); await delay(3);
    assert.deepEqual(r.snapshots.at(-1)?.map(x => x.percent), [96, 41]);
    assert.equal(r.states.at(-1)?.devices?.[1].source, "SteamUI controller state");
    assert.equal(r.states.at(-1)?.devices?.[1].store_percent, 41);
    r.uiRows([{ nControllerIndex: 1, strSerialNumber: "someone-else", ucBatteryLevel: 2 }]);
    await r.monitor.refresh();
    assert.equal(r.snapshots.at(-1)?.[1].percent, 100);
  } finally { await r.monitor.stop(); }
});

test("empty baseline then connect/battery/charging/disconnect, no game/UI lifecycle dependency", async () => {
  const r = rig();
  try {
    r.monitor.start(); await delay(3);
    assert.deepEqual(r.snapshots[0], []);
    r.rows([pad()]); assert.equal(r.emit("list"), 1); await delay(3);
    assert.equal(r.snapshots.at(-1)?.[0].percent, 72);
    r.emit("battery", { controller_index: 0, battery_level: 19, charging: false }); await delay(3);
    assert.equal(r.snapshots.at(-1)?.[0].percent, 19);
    r.emit("battery", { controller_index: 0, battery_level: 20, charging: true }); await delay(3);
    assert.equal(r.snapshots.at(-1)?.[0].charging, true);
    r.rows([]); r.emit("disconnect", { controller_index: 0 }); await delay(3);
    assert.deepEqual(r.snapshots.at(-1), []);
  } finally { await r.monitor.stop(); }
  assert.equal(r.hooks.size, 0);
});

test("retries service discovery and reads snapshots even if notification registry is unavailable", async () => {
  const r = rig();
  try {
    r.available(false); r.monitor.start(); await delay(3);
    assert.equal(r.states.at(-1)?.phase, "unavailable");
    assert.equal(r.snapshots.length, 0);
    r.available(true);
    r.service.RegisterForNotifyControllerListChanged = () => null;
    r.service.RegisterForNotifyControllerBatteryState = () => null;
    r.service.RegisterForNotifyControllerDisconnected = () => null;
    r.rows([pad()]); await r.monitor.refresh();
    assert.equal(r.states.at(-1)?.hooks, 0);
    assert.equal(r.snapshots.at(-1)?.[0].percent, 72);
    r.rows([pad(15)]); await r.monitor.refresh();
    assert.equal(r.snapshots.at(-1)?.[0].percent, 15);
  } finally { await r.monitor.stop(); }
});

test("late query cannot overwrite a newer battery notification", async () => {
  const r = rig();
  try {
    r.rows([pad()]); r.monitor.start(); await delay(3);
    let resolve!: (value: ReturnType<typeof packet>) => void;
    r.service.GetControllerList = () => new Promise(done => { resolve = done; });
    const query = r.monitor.refresh();
    await Promise.resolve();
    r.emit("battery", { controller_index: 0, battery_level: 12, charging: false });
    resolve(packet({ controllers: [pad(72)] })); await query;
    assert.equal(r.snapshots.at(-1)?.[0].percent, 12);
  } finally { await r.monitor.stop(); }
});

test("late query cannot resurrect a disconnected device or give its battery to a replacement", async () => {
  const r = rig();
  try {
    r.rows([pad()]); r.monitor.start(); await delay(3);
    let resolve!: (value: ReturnType<typeof packet>) => void;
    r.service.GetControllerList = () => new Promise(done => { resolve = done; });
    const query = r.monitor.refresh();
    await Promise.resolve();
    r.emit("disconnect", { controller_index: 0 });
    r.service.GetControllerList = async () => packet({ controllers: [{ ...pad(255, "replacement") }] });
    resolve(packet({ controllers: [pad(72)] })); await query; await delay(3);
    assert.equal(r.snapshots.at(-1)?.[0].percent, null);
    assert.notEqual(r.snapshots[0][0].id, r.snapshots.at(-1)?.[0].id);
    assert.ok(r.snapshots.some(items => items.length === 0));
  } finally { await r.monitor.stop(); }
});

test("query failure/timeout is not a successful empty roster, recovery retries; late stop is safe", async () => {
  const r = rig();
  try {
    r.service.GetControllerList = async () => ({ ...packet({}), BSuccess: () => false });
    r.monitor.start(); await delay(3);
    assert.equal(r.states.at(-1)?.phase, "error");
    assert.equal(r.snapshots.length, 0);
    r.service.GetControllerList = () => new Promise(() => {});
    await r.monitor.refresh();
    assert.match(r.states.at(-1)?.error ?? "", /timed out/);
    r.service.GetControllerList = async () => packet({ controllers: [pad(1)] });
    await r.monitor.refresh();
    assert.equal(r.states.at(-1)?.phase, "ready");
    assert.equal(r.snapshots.at(-1)?.[0].percent, 1);
    let resolve!: (value: ReturnType<typeof packet>) => void;
    r.service.GetControllerList = () => new Promise(done => { resolve = done; });
    const query = r.monitor.refresh();
    await Promise.resolve();
    await r.monitor.stop();
    const count = r.snapshots.length;
    resolve(packet({ controllers: [] })); await query;
    assert.equal(r.snapshots.length, count);
  } finally { await r.monitor.stop(); }
});

test("backend unavailable at startup is retried, not silently dropped", async () => {
  let accept = false;
  const snapshots: unknown[] = [];
  const r = rig();
  const monitor = new ControllerMonitor({ discover: () => r.service, pollMs: 10000,
    publish: async items => { if (!accept) throw new Error("backend starting"); snapshots.push(items); },
    diagnose: async () => {},
  });
  try {
    monitor.start(); await delay(3);
    assert.equal(snapshots.length, 0);
    accept = true; await monitor.refresh();
    assert.deepEqual(snapshots, [[]]);
  } finally { await monitor.stop(); }
});

test("background interval renews snapshots without callbacks or an open panel", async () => {
  const r = rig();
  r.rows([pad()]);
  const snapshots: ControllerBatteryUpdate[][] = [];
  delete r.service.RegisterForNotifyControllerListChanged;
  delete r.service.RegisterForNotifyControllerBatteryState;
  delete r.service.RegisterForNotifyControllerDisconnected;
  const monitor = new ControllerMonitor({ discover: () => r.service, pollMs: 10,
    publish: async items => { snapshots.push(items); }, diagnose: async () => {} });
  try {
    monitor.start(); await delay(5);
    r.rows([pad(18)]);
    await delay(30);
    assert.ok(snapshots.length >= 2);
    assert.equal(snapshots.at(-1)?.[0].percent, 18);
    await monitor.stop();
    const count = snapshots.length;
    await delay(20);
    assert.equal(snapshots.length, count);
  } finally { await monitor.stop(); }
});
