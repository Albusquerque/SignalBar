import assert from "node:assert/strict";
import test from "node:test";

import { averageBand, LED_COUNT, scoreBand } from "../../src/artwork";
import type { RGB } from "../../src/types";

test("artwork band always produces exactly 17 RGB pixels", () => {
  const width = 170;
  const height = 20;
  const data = new Uint8ClampedArray(width * height * 4);
  for (let offset = 0; offset < data.length; offset += 4) {
    data[offset] = (offset / 4) % width;
    data[offset + 1] = 100;
    data[offset + 2] = 200;
    data[offset + 3] = 255;
  }
  const colors = averageBand(data, width, height, 0.5);
  assert.equal(colors.length, LED_COUNT);
  for (const color of colors) {
    assert.equal(color.length, 3);
    assert.ok(color.every((channel) => Number.isInteger(channel) && channel >= 0 && channel <= 255));
  }
});

test("auto scoring prefers a varied colourful band over black or uniform white", () => {
  const black = Array.from({ length: 17 }, () => [0, 0, 0] as RGB);
  const white = Array.from({ length: 17 }, () => [255, 255, 255] as RGB);
  const varied = Array.from({ length: 17 }, (_, index) => (
    index % 3 === 0 ? [240, 30, 40] : index % 3 === 1 ? [20, 210, 80] : [30, 70, 240]
  ) as RGB);
  assert.ok(scoreBand(varied) > scoreBand(black));
  assert.ok(scoreBand(varied) > scoreBand(white));
});

