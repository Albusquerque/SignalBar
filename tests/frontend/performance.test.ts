import assert from "node:assert/strict";
import test from "node:test";

import { hslStringToRgb, performancePreview, rgbToHsl, temperatureColor } from "../../src/performance";
import type { Status } from "../../src/types";

const status = {
  performance_metric: "mixed",
  mixed_direction: "mirrored",
  temperature_palette: "classic",
  temperature_custom_cool: [10, 20, 30],
  temperature_custom_middle: [70, 80, 90],
  temperature_custom_hot: [220, 230, 240],
  cool_temp_c: 50,
  hot_temp_c: 90,
  performance: {
    cpu_load: 25,
    cpu_temperature: 50,
    gpu_load: 50,
    gpu_temperature: 90,
  },
} as Status;

test("temperature colours use named thresholds and selected palette", () => {
  assert.deepEqual(temperatureColor(50, 50, 90, "classic"), [35, 205, 95]);
  assert.deepEqual(temperatureColor(90, 50, 90, "classic"), [235, 45, 55]);
});

test("custom temperature colours and Decky HSL picker round-trip", () => {
  assert.deepEqual(temperatureColor(50, 50, 90, "custom", [
    status.temperature_custom_cool,
    status.temperature_custom_middle,
    status.temperature_custom_hot,
  ]), [10, 20, 30]);
  const source = [30, 180, 230] as [number, number, number];
  const [h, s, l] = rgbToHsl(source);
  const restored = hslStringToRgb(`hsla(${h}, ${s}%, ${l}%, 1)`);
  assert.ok(restored);
  restored.forEach((channel, index) => assert.ok(Math.abs(channel - source[index]) <= 2));
});

test("mixed preview can use two left-to-right meters", () => {
  const frame = performancePreview({ ...status, mixed_direction: "same" });
  assert.ok(frame[9].some(Boolean));
  assert.deepEqual(frame[16], [0, 0, 0]);
});

test("mixed preview is CPU 8, black separator, GPU 8", () => {
  const frame = performancePreview(status);
  assert.equal(frame.length, 17);
  assert.deepEqual(frame[8], [0, 0, 0]);
  assert.equal(frame.slice(0, 8).filter((pixel) => pixel.some(Boolean)).length, 2);
  assert.equal(frame.slice(9).filter((pixel) => pixel.some(Boolean)).length, 4);
  assert.ok(frame[0].some(Boolean));
  assert.ok(frame[16].some(Boolean));
});
