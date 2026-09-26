import { useEffect, useRef } from "react";
import type { PongStatus, RGB } from "../types";

const COLUMNS = 40;
const ROWS = 18;
const CELL = 12;
const AMBER = "#ffb44d";
const CYAN = "#4ddbef";
const PINK = "#ff679f";
const WHITE = "#fff2d6";
const STAGES = ["#56d8d1", "#649eff", "#bd79f5", "#ffa64c", "#ff6759"];

const SMALL: Record<string, string[]> = {
  A: ["010", "101", "111", "101", "101"], B: ["110", "101", "110", "101", "110"],
  C: ["011", "100", "100", "100", "011"], D: ["110", "101", "101", "101", "110"],
  E: ["111", "100", "110", "100", "111"], F: ["111", "100", "110", "100", "100"],
  G: ["011", "100", "101", "101", "011"], H: ["101", "101", "111", "101", "101"],
  I: ["111", "010", "010", "010", "111"], J: ["001", "001", "001", "101", "010"],
  K: ["101", "101", "110", "101", "101"], L: ["100", "100", "100", "100", "111"],
  M: ["101", "111", "111", "101", "101"], N: ["101", "111", "111", "111", "101"],
  O: ["010", "101", "101", "101", "010"], P: ["110", "101", "110", "100", "100"],
  Q: ["010", "101", "101", "011", "001"], R: ["110", "101", "110", "101", "101"],
  S: ["011", "100", "010", "001", "110"], T: ["111", "010", "010", "010", "010"],
  U: ["101", "101", "101", "101", "111"], V: ["101", "101", "101", "101", "010"],
  W: ["101", "101", "111", "111", "101"], X: ["101", "101", "010", "101", "101"],
  Y: ["101", "101", "010", "010", "010"], Z: ["111", "001", "010", "100", "111"],
  "0": ["111", "101", "101", "101", "111"], "1": ["010", "110", "010", "010", "111"],
  "2": ["110", "001", "010", "100", "111"], "3": ["110", "001", "010", "001", "110"],
  "4": ["101", "101", "111", "001", "001"], "5": ["111", "100", "110", "001", "110"],
  "6": ["011", "100", "110", "101", "010"], "7": ["111", "001", "010", "010", "010"],
  "8": ["010", "101", "010", "101", "010"], "9": ["010", "101", "011", "001", "110"],
  "!": ["010", "010", "010", "000", "010"], " ": ["000", "000", "000", "000", "000"],
};

const DIGITS = [
  ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
  ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
  ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
  ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
  ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
  ["11111", "10000", "10000", "11110", "00001", "00001", "11110"],
  ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
  ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
  ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
  ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
];

type Cue = "ready" | "hit" | "perfect" | "level" | "point" | "loss" | "finished" | "idle";
interface VisualState { session: number; feedback: number; phase: string; cue: Cue; started: number }

function dot(ctx: CanvasRenderingContext2D, x: number, y: number, colour: string, alpha = 1) {
  if (x < 0 || x >= COLUMNS || y < 0 || y >= ROWS) return;
  ctx.globalAlpha = alpha;
  ctx.fillStyle = colour;
  ctx.beginPath();
  ctx.arc((x + .5) * CELL, (y + .5) * CELL, CELL * .36, 0, Math.PI * 2);
  ctx.fill();
  ctx.globalAlpha = 1;
}

function smallTextAt(ctx: CanvasRenderingContext2D, value: string, x0: number, y: number, colour: string) {
  const text = value.toUpperCase();
  for (let i = 0; i < text.length; i++) {
    const rows = SMALL[text[i]] ?? SMALL[" "];
    for (let row = 0; row < 5; row++) {
      for (let column = 0; column < 3; column++) {
        if (rows[row][column] === "1") dot(ctx, x0 + i * 4 + column, y + row, colour);
      }
    }
  }
}

function smallText(ctx: CanvasRenderingContext2D, value: string, y: number, colour: string) {
  smallTextAt(ctx, value, Math.floor((COLUMNS - (value.length * 4 - 1)) / 2), y, colour);
}

function largeDigit(ctx: CanvasRenderingContext2D, value: number, x: number, colour: string, alpha = 1) {
  for (let row = 0; row < 7; row++) {
    for (let column = 0; column < 5; column++) {
      if (DIGITS[value][row][column] === "1") dot(ctx, x + column, row + 7, colour, alpha);
    }
  }
}

function perimeter(position: number): [number, number] {
  const length = 2 * COLUMNS + 2 * ROWS - 4;
  let step = ((position % length) + length) % length;
  if (step < COLUMNS) return [step, 0];
  step -= COLUMNS;
  if (step < ROWS - 1) return [COLUMNS - 1, step + 1];
  step -= ROWS - 1;
  if (step < COLUMNS - 1) return [COLUMNS - 2 - step, ROWS - 1];
  step -= COLUMNS - 1;
  return [0, ROWS - 2 - step];
}

function pattern(ctx: CanvasRenderingContext2D, status: PongStatus, visual: VisualState, now: number,
                 accent: string) {
  const elapsed = Math.max(0, now - visual.started);
  const side = status.feedback_player === 1 ? 34 : 5;
  if (visual.cue === "hit" && elapsed < 480) {
    const reach = Math.floor(elapsed / 55);
    for (let i = 0; i < 8; i++) {
      const x = side + (side < 20 ? i : -i);
      dot(ctx, x, 6 + (i % 2) * 8, WHITE, Math.max(.15, 1 - Math.abs(i - reach) * .25));
    }
  } else if (visual.cue === "perfect" && elapsed < 1050) {
    const radius = 1 + Math.floor(elapsed / 140);
    for (let ray = 0; ray < 12; ray++) {
      const angle = ray * Math.PI / 6;
      dot(ctx, Math.round(side + Math.cos(angle) * radius * 1.4),
        Math.round(10 + Math.sin(angle) * radius), WHITE, .85);
    }
  } else if (visual.cue === "level" && elapsed < 1400) {
    const sweep = Math.floor(elapsed / 24);
    for (let x = 1; x < COLUMNS - 1; x++) {
      if (x > sweep) continue;
      const y = 7 + Math.abs((x % 8) - 4);
      dot(ctx, x, y, accent, x > sweep - 6 ? 1 : .42);
      dot(ctx, x, ROWS - 1 - y, accent, x > sweep - 6 ? 1 : .42);
    }
  } else if ((visual.cue === "point" || visual.cue === "loss") && elapsed < 1050) {
    const radius = 1 + Math.floor(elapsed / 100);
    const centre = status.feedback_player === 1 ? 30 : 9;
    for (let angle = 0; angle < 16; angle++) {
      const radians = angle * Math.PI / 8;
      dot(ctx, Math.round(centre + Math.cos(radians) * radius * 1.5),
        Math.round(10 + Math.sin(radians) * radius * .7),
        visual.cue === "loss" ? PINK : AMBER, Math.max(.25, 1 - elapsed / 1500));
    }
  } else if (visual.cue === "finished" && elapsed < 3400) {
    for (let burst = 0; burst < 3; burst++) {
      const age = (elapsed + burst * 400) % 1150;
      const radius = 1 + Math.floor(age / 170);
      const cx = [9, 30, 20][burst];
      const cy = [9, 10, 8][burst];
      for (let ray = 0; ray < 10; ray++) {
        const angle = ray * Math.PI / 5 + burst;
        dot(ctx, Math.round(cx + Math.cos(angle) * radius * 1.5),
          Math.round(cy + Math.sin(angle) * radius), burst === 1 ? PINK : accent, .9);
      }
    }
  } else if (visual.cue === "ready" && status.phase === "ready") {
    const countdown = 3 - Math.min(2, Math.floor(elapsed / 500));
    largeDigit(ctx, countdown, 2, accent, .5);
    largeDigit(ctx, countdown, 33, accent, .5);
  }
}

function draw(ctx: CanvasRenderingContext2D, status: PongStatus, visual: VisualState, now: number) {
  const width = COLUMNS * CELL;
  const height = ROWS * CELL;
  ctx.fillStyle = "#080b10";
  ctx.fillRect(0, 0, width, height);
  for (let y = 0; y < ROWS; y++) {
    for (let x = 0; x < COLUMNS; x++) dot(ctx, x, y, "#342821", .4);
  }
  const accent = STAGES[Math.max(0, Math.min(4, status.level - 1))];
  const chase = Math.floor(now / 72);
  for (let i = 0; i < 4; i++) {
    const [x, y] = perimeter(chase + i * 28);
    dot(ctx, x, y, accent, i === 0 ? 1 : .42);
  }
  pattern(ctx, status, visual, now, accent);

  const elapsed = Math.max(0, now - visual.started);
  let banner = status.mode === "solo" ? "SCORE" : status.mode === "duel" ? "DUEL" : "PONGBAR";
  let bannerColour = AMBER;
  if (status.paused) { banner = "PAUSED"; bannerColour = PINK; }
  else if (visual.cue === "finished" && elapsed < 3400) {
    banner = status.mode === "solo" && status.winner === 1 ? "GAME OVER" : "WINNER";
    bannerColour = status.winner === 1 ? PINK : accent;
  } else if (visual.cue === "level" && elapsed < 1400) { banner = "JACKPOT"; bannerColour = accent; }
  else if (visual.cue === "perfect" && elapsed < 1050) { banner = "PERFECT"; bannerColour = WHITE; }
  else if (visual.cue === "point" && elapsed < 1050) { banner = "POINT"; bannerColour = AMBER; }
  else if (visual.cue === "loss" && elapsed < 1050) { banner = "MISS"; bannerColour = PINK; }
  else if (visual.cue === "hit" && elapsed < 480) { banner = "RETURN"; bannerColour = CYAN; }
  else if (status.phase === "ready") { banner = "GET READY"; bannerColour = accent; }
  smallText(ctx, banner, 1, bannerColour);

  if (status.mode === "duel") {
    smallTextAt(ctx, "P1", 2, 8, CYAN);
    smallTextAt(ctx, "P2", 31, 8, PINK);
    const left = Math.min(9, Math.max(0, status.scores[0] ?? 0));
    const right = Math.min(9, Math.max(0, status.scores[1] ?? 0));
    largeDigit(ctx, left, 12, CYAN);
    largeDigit(ctx, right, 23, PINK);
    dot(ctx, 19, 9, AMBER); dot(ctx, 19, 12, AMBER);
    dot(ctx, 20, 9, AMBER); dot(ctx, 20, 12, AMBER);
  } else {
    const score = Math.min(999, Math.max(0, status.returns));
    String(score).padStart(3, "0").split("").forEach((digit, index) => {
      largeDigit(ctx, Number(digit), 11 + index * 6, AMBER);
    });
  }

  for (let i = 0; i < 17; i++) {
    const colour: RGB = status.colors?.[i] ?? [0, 0, 0];
    const [r, g, b] = colour;
    dot(ctx, 11 + i, 16, r + g + b > 0 ? `rgb(${r},${g},${b})` : "#46392c",
      r + g + b > 0 ? 1 : .45);
  }
  dot(ctx, 3, 16, CYAN, .8);
  dot(ctx, 36, 16, PINK, .8);
}

export function PongMatrixDisplay({ status }: { status: PongStatus }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const statusRef = useRef(status);
  const visualRef = useRef<VisualState>({ session: status.session_id, feedback: status.feedback_seq,
    phase: status.phase, cue: status.phase === "finished" ? "finished" : status.phase === "level" ? "level" :
      status.phase === "ready" ? "ready" : "idle", started: performance.now() });

  useEffect(() => {
    const visual = visualRef.current;
    const now = performance.now();
    if (visual.session !== status.session_id) {
      visual.session = status.session_id;
      visual.feedback = status.feedback_seq;
      visual.phase = status.phase;
      visual.cue = status.phase === "finished" ? "finished" : status.phase === "level" ? "level" :
        status.phase === "ready" ? "ready" : "idle";
      visual.started = now;
    } else if (status.phase === "finished" && visual.phase !== "finished") {
      visual.cue = "finished";
      visual.started = now;
    } else if (visual.feedback !== status.feedback_seq) {
      const kind = status.feedback_kind;
      visual.cue = kind === "perfect" || kind === "hit" || kind === "level" ||
        kind === "point" || kind === "loss" ? kind : "idle";
      visual.started = now;
    } else if (status.phase === "ready" && visual.phase !== "ready") {
      visual.cue = "ready";
      visual.started = now;
    }
    visual.feedback = status.feedback_seq;
    visual.phase = status.phase;
    statusRef.current = status;
  }, [status]);

  useEffect(() => {
    const ctx = canvasRef.current?.getContext("2d");
    if (!ctx) return;
    const render = () => draw(ctx, statusRef.current, visualRef.current, performance.now());
    render();
    const timer = window.setInterval(render, 60);
    return () => window.clearInterval(timer);
  }, []);

  const label = status.mode === "duel"
    ? `PongBar pixel matrix. Player 1 ${status.scores[0]}, player 2 ${status.scores[1]}. Level ${status.level}.`
    : `PongBar pixel matrix. Score ${status.returns} returns, best streak ${status.best_streak}, ${status.lives} lives. Level ${status.level}.`;
  return <div style={{ width: "100%", boxSizing: "border-box", padding: 10, borderRadius: 10,
    background: "linear-gradient(145deg, #292e35, #0b0e12 65%)", border: "1px solid #53585c",
    boxShadow: "inset 0 1px 0 #697078, 0 6px 18px rgba(0,0,0,.35)" }}>
    <div style={{ display: "flex", justifyContent: "space-between", color: "#f7bd69",
      fontSize: ".7em", letterSpacing: ".16em", marginBottom: 6 }}>
      <span>PONGBAR · DOT MATRIX</span><span>LEVEL {status.level}</span>
    </div>
    <canvas ref={canvasRef} width={COLUMNS * CELL} height={ROWS * CELL} role="img" aria-label={label}
      style={{ display: "block", width: "100%", height: "auto", background: "#080b10",
        borderRadius: 4, border: "1px solid #744923", imageRendering: "pixelated",
        boxShadow: "inset 0 0 12px #000, 0 0 8px rgba(255,171,64,.16)" }} />
    <div style={{ display: "flex", justifyContent: "space-between", gap: 8, color: "#c9c2b7",
      fontSize: ".72em", marginTop: 7 }}>
      <span>{status.mode === "duel" ? `P1 ${status.scores[0]}  ·  P2 ${status.scores[1]}` :
        `SCORE ${status.returns}  ·  BEST ${status.best_streak}`}</span>
      <span>{status.mode === "duel" ? "FIRST TO 5" : `${status.lives} LIVES`}</span>
    </div>
  </div>;
}
