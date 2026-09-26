import { getPongStatus, pingPongInput, pressPong, setPongInputState } from "./api";
import type { PongStatus } from "./types";

declare const SteamClient: {
  Input?: {
    RegisterForControllerInputMessages?: (
      callback: (controllerIndex: number, button: number, pressed: boolean) => void,
    ) => { unregister?: () => void } | undefined;
  };
} | undefined;

export interface PongGamepad { index: number; name: string; mapping: string; primaryPressed: boolean }
export interface SteamPongController { index: number; lastButton: number; pressed: boolean }
export interface PongInputDiagnostic {
  source: "steam" | "browser" | "touch" | "manual";
  index: number;
  lastButton: number;
  presses: number;
  lastAt: number;
  lastMs: number | null;
  averageMs: number | null;
  maximumMs: number | null;
  failures: number;
  lastError: string;
  request: "probe" | "game";
}

type DiagnosticRecord = PongInputDiagnostic & { samples: number[]; sequence: number; lastCompleted: number };
const diagnostics = new Map<string, DiagnosticRecord>();
let diagnosticObservers = 0;

export function observePongInputDiagnostics(): () => void {
  diagnosticObservers += 1;
  return () => { diagnosticObservers = Math.max(0, diagnosticObservers - 1); };
}

export function pongInputDiagnostics(): PongInputDiagnostic[] {
  return [...diagnostics.values()].map(({ samples: _samples, sequence: _sequence,
    lastCompleted: _lastCompleted, ...record }) => ({ ...record }))
    .sort((left, right) => left.source.localeCompare(right.source) || left.index - right.index);
}

export function resetPongInputDiagnostics() { diagnostics.clear(); }

function measureInput<T>(source: PongInputDiagnostic["source"], index: number, button: number,
                         request: "probe" | "game", call: () => Promise<T>): Promise<T> {
  const key = `${source}:${index}`;
  let record = diagnostics.get(key);
  if (!record) {
    record = { source, index, lastButton: button, presses: 0, lastAt: 0, lastMs: null,
      averageMs: null, maximumMs: null, failures: 0, lastError: "", request,
      samples: [], sequence: 0, lastCompleted: 0 };
    diagnostics.set(key, record);
  }
  record.presses += 1;
  record.lastAt = Date.now();
  record.lastButton = button;
  record.request = request;
  const sequence = ++record.sequence;
  const started = performance.now();
  return Promise.resolve().then(call).then((value) => {
    const elapsed = performance.now() - started;
    if (diagnostics.get(key) !== record) return value;
    record.samples.push(elapsed);
    if (record.samples.length > 20) record.samples.shift();
    record.averageMs = record.samples.reduce((sum, value) => sum + value, 0) / record.samples.length;
    record.maximumMs = Math.max(...record.samples);
    if (sequence >= record.lastCompleted) {
      record.lastCompleted = sequence;
      record.lastMs = elapsed;
      record.lastError = "";
    }
    return value;
  }, (error: unknown) => {
    if (diagnostics.get(key) === record) {
      record.failures += 1;
      if (sequence >= record.lastCompleted) {
        record.lastCompleted = sequence;
        record.lastError = error instanceof Error ? error.message : String(error);
      }
    }
    throw error;
  });
}

export function probePongBackend() {
  void measureInput("manual", -1, -1, "probe", pingPongInput).catch(() => undefined);
}

export function pressPongOnScreen(sessionId: number, player: number): Promise<PongStatus> {
  return measureInput("touch", player, -1, "game", () => pressPong(sessionId, player));
}

const steamControllers = new Map<number, { lastButton: number; pressed: boolean; seenAt: number }>();
let steamInputAvailable = false;

export function steamPongInputState(): { available: boolean; controllers: SteamPongController[] } {
  const now = Date.now();
  return {
    available: steamInputAvailable,
    controllers: [...steamControllers].filter(([, item]) => now - item.seenAt < 5 * 60_000)
      .map(([index, item]) => ({ index, lastButton: item.lastButton, pressed: item.pressed }))
      .sort((left, right) => left.index - right.index),
  };
}

export function connectedPongGamepads(): PongGamepad[] {
  try {
    if (typeof navigator.getGamepads !== "function") return [];
    return Array.from(navigator.getGamepads()).filter((pad): pad is Gamepad => Boolean(pad?.connected))
      .map((pad) => ({ index: pad.index, name: pad.id.slice(0, 80), mapping: pad.mapping,
        primaryPressed: Boolean(pad.buttons[0]?.pressed) }));
  } catch {
    return [];
  }
}

type HapticActuator = { playEffect?: (type: "dual-rumble", options: {
  duration: number; strongMagnitude: number; weakMagnitude: number;
}) => Promise<unknown> };

function buzz(index: number, kind: string) {
  try {
    const pad = navigator.getGamepads?.()[index];
    const actuator = (pad as Gamepad & { vibrationActuator?: HapticActuator } | null)?.vibrationActuator;
    if (!actuator?.playEffect) return;
    const duration = kind === "point" ? 110 : kind === "loss" ? 90 : kind === "level" ? 85 : kind === "perfect" ? 65 : 40;
    const strength = kind === "point" ? 0.45 : kind === "loss" ? 0.25 : kind === "level" ? 0.35 : kind === "perfect" ? 0.32 : 0.18;
    void actuator.playEffect("dual-rumble", {
      duration, strongMagnitude: strength, weakMagnitude: strength * 0.65,
    }).catch(() => undefined);
  } catch { /* Unsupported haptics never affect play. */ }
}

/** Runs at plugin load, independently of the Decky settings panel. */
export class PongInputRuntime {
  private alive = false;
  private pollTimer: number | undefined;
  private statusTimer: number | undefined;
  private statusPending = false;
  private status: PongStatus | undefined;
  private held = new Map<number, boolean>();
  private feedbackSeq = 0;
  private sessionId = -1;
  private steamRegistration: { unregister?: () => void } | undefined;
  private steamHookActive = false;
  private steamHeld = new Set<string>();

  start() {
    if (this.alive) return;
    this.alive = true;
    this.ensureSteamHook();
    void this.refresh();
  }

  stop() {
    this.alive = false;
    window.clearInterval(this.pollTimer);
    window.clearTimeout(this.statusTimer);
    this.pollTimer = undefined;
    this.statusTimer = undefined;
    this.held.clear();
    this.steamHeld.clear();
    try { this.steamRegistration?.unregister?.(); } catch { /* Steam may be shutting down. */ }
    this.steamRegistration = undefined;
    this.steamHookActive = false;
    steamInputAvailable = false;
    steamControllers.clear();
  }

  private ensureSteamHook() {
    if (!this.alive || this.steamHookActive) return;
    try {
      const input = typeof SteamClient === "undefined" ? undefined : SteamClient?.Input;
      const register = input?.RegisterForControllerInputMessages;
      if (typeof register !== "function") return;
      this.steamRegistration = register.call(input, (index, button, pressed) => this.onSteamButton(index, button, pressed));
      this.steamHookActive = true;
      steamInputAvailable = true;
    } catch { /* Retry after SteamUI finishes loading. */ }
  }

  private onSteamButton(index: number, button: number, pressed: boolean) {
    if (!this.alive || !Number.isInteger(index) || index < 0 || index >= 0xffffffff
        || !Number.isInteger(button) || button < 0 || button > 50 || typeof pressed !== "boolean") return;
    steamControllers.set(index, { lastButton: button, pressed, seenAt: Date.now() });
    const key = `${index}:${button}`;
    const wasHeld = this.steamHeld.has(key);
    if (pressed) this.steamHeld.add(key);
    else this.steamHeld.delete(key);
    const status = this.status;
    if (!pressed || wasHeld) return;
    const player = status?.gamepad_indices.indexOf(index) ?? -1;
    if (status?.active && !status.paused && status.input_source === "steam"
        && button === status.action_button && player >= 0) {
      void measureInput("steam", index, button, "game", () => pressPong(status.session_id, player))
        .catch(() => undefined);
    } else if (diagnosticObservers > 0) {
      void measureInput("steam", index, button, "probe", pingPongInput).catch(() => undefined);
    }
  }

  private async refresh() {
    if (!this.alive || this.statusPending) return;
    this.statusPending = true;
    try {
      this.ensureSteamHook();
      const status = await getPongStatus();
      if (!this.alive) return;
      if (status.session_id !== this.sessionId) {
        this.sessionId = status.session_id;
        this.held.clear();
        this.feedbackSeq = status.feedback_seq;
      } else if (status.feedback_seq !== this.feedbackSeq) {
        this.feedbackSeq = status.feedback_seq;
        if (status.vibration_enabled && status.input_source === "browser" && status.feedback_player >= 0) {
          const index = status.gamepad_indices[status.feedback_player];
          if (index !== undefined) buzz(index, status.feedback_kind);
        }
      }
      this.status = status;
      if (status.active && status.input_source === "browser" && this.pollTimer === undefined) {
        this.pollTimer = window.setInterval(() => this.readButtons(), 16);
      } else if ((!status.active || status.input_source !== "browser") && this.pollTimer !== undefined) {
        window.clearInterval(this.pollTimer);
        this.pollTimer = undefined;
        this.held.clear();
      }
      if (status.active && status.gamepad_indices.length > 0) {
        let connected = false;
        if (status.input_source === "steam") {
          connected = this.steamHookActive && status.gamepad_indices.every((index) => steamControllers.has(index));
        } else if (status.input_source === "browser") {
          const pads = navigator.getGamepads?.() ?? [];
          connected = status.gamepad_indices.every((index) => Boolean(pads[index]?.connected));
        }
        await setPongInputState(status.session_id, connected);
      }
    } catch { /* Retry when Decky/backend is ready. */ }
    finally {
      this.statusPending = false;
      if (this.alive) this.statusTimer = window.setTimeout(() => void this.refresh(), this.status?.active ? 350 : 1000);
    }
  }

  private readButtons() {
    const status = this.status;
    if (!this.alive || !status?.active || status.input_source !== "browser") return;
    let pads: (Gamepad | null)[];
    try { pads = Array.from(navigator.getGamepads?.() ?? []); }
    catch { return; }
    status.gamepad_indices.forEach((index, player) => {
      const pressed = Boolean(pads[index]?.connected && pads[index]?.buttons[0]?.pressed);
      const wasHeld = this.held.get(index) ?? pressed;
      this.held.set(index, pressed);
      if (pressed && !wasHeld) {
        if (!status.paused) {
          void measureInput("browser", index, 0, "game", () => pressPong(status.session_id, player))
            .catch(() => undefined);
        } else {
          void measureInput("browser", index, 0, "probe", pingPongInput).catch(() => undefined);
        }
      }
    });
  }
}
