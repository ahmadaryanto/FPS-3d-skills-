// Synthesised SFX + quiet music bed for the Ruined Hall clip. Usage: node audio.mjs events.json audio.wav
import fs from "fs";

const ev = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const OUT = process.argv[3] || "audio.wav";
const SR = 48000;
const N = Math.round(ev.duration * SR);
const L = new Float32Array(N);
const R = new Float32Array(N);

let seed = 12345;
const rnd = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296);
const noise = () => rnd() * 2 - 1;
const sstep = (u) => { u = Math.max(0, Math.min(1, u)); return u * u * (3 - 2 * u); };

// add a mono sound made by fn(tLocal) -> sample, at time t0 for dur seconds, with gain and pan (-1..1)
function add(t0, dur, gain, pan, fn) {
  const i0 = Math.round(t0 * SR);
  const n = Math.round(dur * SR);
  const gl = gain * Math.sqrt((1 - pan) / 2), gr = gain * Math.sqrt((1 + pan) / 2);
  for (let i = 0; i < n; i++) {
    const j = i0 + i;
    if (j < 0 || j >= N) continue;
    const v = fn(i / SR, i);
    L[j] += v * gl;
    R[j] += v * gr;
  }
}

// one-pole filters as closures
const lp = (fc) => { let y = 0; const a = 1 - Math.exp(-2 * Math.PI * fc / SR); return (x) => (y += a * (x - y)); };
const hp = (fc) => { const f = lp(fc); return (x) => x - f(x); };
const bp = (lo, hi) => { const a = hp(lo), b = lp(hi); return (x) => b(a(x)); };

// ---- wind (whole clip), louder up on the platform
{
  const f1 = lp(420), f2 = lp(900);
  add(0, ev.duration, 1, 0, (t) => {
    const up = 0.6 + 0.4 * sstep((t - 4.6) / 1.5);
    const gust = 0.6 + 0.4 * Math.sin(t * 0.7) * Math.sin(t * 0.23 + 1);
    return (f1(noise()) * 0.5 + f2(noise()) * 0.12) * 0.11 * up * gust;
  });
}

// ---- music bed: a low minor pad with a slow pulse, swelling for the close
{
  const notes = [55, 82.41, 110, 130.81, 164.81];
  const fl = lp(700), fr = lp(700);
  const top = [220, 261.63, 329.63, 392];
  for (let i = 0; i < N; i++) {
    const t = i / SR;
    let a = 0, b = 0;
    for (let k = 0; k < notes.length; k++) {
      const f = notes[k];
      a += Math.sin(2 * Math.PI * f * t) + 0.4 * Math.sin(2 * Math.PI * f * 2.003 * t) + 0.2 * Math.sin(2 * Math.PI * f * 3.001 * t);
      b += Math.sin(2 * Math.PI * f * 1.004 * t + 1) + 0.4 * Math.sin(2 * Math.PI * f * 1.997 * t) + 0.2 * Math.sin(2 * Math.PI * f * 3.006 * t);
    }
    const swell = 1 + 1.7 * sstep((t - 16.6) / 1.5);
    const env = sstep(t / 1.5) * (1 - sstep((t - 19.0) / 1.0)) * swell;
    const pulse = 0.75 + 0.25 * Math.sin(2 * Math.PI * 1.5 * t);
    // a slow arpeggio on top, only in the close
    const st = Math.floor(t * 3) % top.length;
    const ph = (t * 3) % 1;
    const arp = Math.sin(2 * Math.PI * top[st] * t) * Math.exp(-ph * 4) * 0.9 * sstep((t - 16.8) / 0.8);
    const g = 0.016 * env;
    L[i] += (fl(a) * pulse + arp) * g;
    R[i] += (fr(b) * pulse + arp) * g;
  }
}

// ---- footsteps on stone
ev.steps.forEach((t, k) => {
  const f = lp(260 + 80 * rnd()), c = bp(1500, 4000);
  add(t, 0.16, 0.5, k % 2 ? 0.2 : -0.2, (x) => f(noise()) * Math.exp(-x * 38) * 1.6 + c(noise()) * Math.exp(-x * 120) * 0.25);
});

// ---- ladder rungs: wooden knock
ev.rungs.forEach((t, k) => {
  const f0 = 240 + 60 * rnd();
  const c = bp(700, 2600);
  add(t, 0.2, 0.42, k % 2 ? 0.25 : -0.25, (x) =>
    Math.sin(2 * Math.PI * f0 * x) * Math.exp(-x * 45) + Math.sin(2 * Math.PI * f0 * 2.7 * x) * Math.exp(-x * 70) * 0.5 + c(noise()) * Math.exp(-x * 90) * 0.6);
});
// breathing on the climb
for (const t of [4.75, 5.2]) {
  const c = bp(500, 1800);
  add(t, 0.38, 0.1, 0, (x) => c(noise()) * Math.sin(Math.PI * x / 0.38) ** 2);
}

// ---- jumps: whoosh then landing thud
function whoosh(t, dur, gain) {
  let y = 0, y2 = 0;
  add(t, dur, gain, 0, (x) => {
    const u = x / dur;
    const fc = 300 + 2600 * Math.sin(Math.PI * u);
    const a = 1 - Math.exp(-2 * Math.PI * fc / SR);
    y += a * (noise() - y);
    y2 += 0.02 * (y - y2);
    return (y - y2) * Math.sin(Math.PI * u) ** 1.5;
  });
}
function thud(t, gain) {
  const f = lp(500);
  add(t, 0.45, gain, 0, (x) => Math.sin(2 * Math.PI * (48 + 60 * Math.exp(-x * 30)) * x) * Math.exp(-x * 11) + f(noise()) * Math.exp(-x * 30) * 0.8);
}
whoosh(ev.jump1 - 0.05, 0.5, 0.3);
thud(ev.land1, 0.75);
whoosh(ev.jump2 - 0.05, 0.75, 0.42);
thud(ev.land2, 1.0);

// ---- aim in / out: cloth + a soft click
for (const t of [...ev.ads, ...ev.unads]) {
  const c = bp(900, 3500);
  add(t, 0.25, 0.14, 0.1, (x) => c(noise()) * Math.sin(Math.PI * x / 0.25) ** 2);
  add(t + 0.2, 0.04, 0.16, 0.1, (x) => Math.sin(2 * Math.PI * 2300 * x) * Math.exp(-x * 160));
}

// ---- gunshots (fast, snappy) + casings
ev.shots.forEach((t, k) => {
  const crack = hp(1200), body = lp(1700), tail = lp(900);
  const det = 1 + 0.06 * (rnd() - 0.5);
  add(t, 0.42, 0.95, 0.06, (x) =>
    crack(noise()) * Math.exp(-x * 190) * 0.9
    + body(noise()) * Math.exp(-x * 48) * 1.5
    + Math.sin(2 * Math.PI * (70 + 190 * Math.exp(-x * 60)) * det * x) * Math.exp(-x * 30) * 1.1
    + tail(noise()) * Math.exp(-x * 9) * 0.16);
  if (k % 2 === 0) {
    const f0 = 3800 + 1800 * rnd();
    for (const [dt, g] of [[0.32, 1], [0.41, 0.5]]) {
      add(t + dt + 0.05 * rnd(), 0.12, 0.05 * g, 0.5, (x) => (Math.sin(2 * Math.PI * f0 * x) + 0.5 * Math.sin(2 * Math.PI * f0 * 1.52 * x)) * Math.exp(-x * 55));
    }
  }
});

// ---- bullet hits on metal
ev.hits.forEach((t) => {
  const f0 = 1500 + 1500 * rnd();
  const c = hp(2500);
  add(t, 0.14, 0.12, -0.15 + 0.3 * rnd(), (x) => Math.sin(2 * Math.PI * f0 * x) * Math.exp(-x * 60) + c(noise()) * Math.exp(-x * 150) * 0.7);
});

// ---- drone hum for each wave, dropping out as they die
function hum(t0, t1, pan, f0) {
  const f = lp(1100);
  add(t0, t1 - t0 + 0.2, 0.05, pan, (x) => {
    const env = sstep(x / 1.2) * (1 - sstep((x - (t1 - t0)) / 0.2));
    const ph = f0 * x + 0.4 * Math.sin(2 * Math.PI * 0.6 * x);
    const saw = 2 * (ph % 1) - 1;
    return f(saw + 0.5 * Math.sin(2 * Math.PI * ph * 2.01)) * (0.65 + 0.35 * Math.sin(2 * Math.PI * 31 * x)) * env;
  });
}
hum(ev.drones1[0], ev.deaths[0], -0.3, 132);
hum(ev.drones1[0] + 0.3, ev.deaths[1], 0.0, 147);
hum(ev.drones1[0] + 0.6, ev.deaths[2], 0.35, 124);
hum(ev.drones2[0], ev.deaths[3], -0.6, 139);
hum(ev.drones2[0] + 0.35, ev.deaths[4], -0.3, 128);

// ---- drone break-ups
ev.deaths.forEach((t, k) => {
  const a = lp(900), b = lp(180), c = hp(1800);
  const pan = [-0.3, 0, 0.35, -0.5, -0.2][k];
  add(t, 1.7, 0.85, pan, (x) =>
    a(noise()) * Math.exp(-x * 5) * 1.3 + b(noise()) * Math.exp(-x * 2.6) * 2.4
    + Math.sin(2 * Math.PI * (38 + 50 * Math.exp(-x * 12)) * x) * Math.exp(-x * 5) * 0.9
    + c(noise()) * Math.exp(-x * 40) * 0.5);
  // debris crackle
  for (let j = 0; j < 9; j++) {
    const f0 = 900 + 2600 * rnd();
    add(t + 0.15 + 1.1 * rnd(), 0.08, 0.07, pan + 0.4 * (rnd() - 0.5), (x) => Math.sin(2 * Math.PI * f0 * x) * Math.exp(-x * 80) + noise() * Math.exp(-x * 200) * 0.4);
  }
});

// ---- reload: mag out, mag in, charging handle
function click(t, gain, f0, decay) {
  const c = bp(800, 5000);
  add(t, 0.12, gain, 0.15, (x) => c(noise()) * Math.exp(-x * decay) + Math.sin(2 * Math.PI * f0 * x) * Math.exp(-x * decay * 0.7) * 0.6);
}
click(ev.reload.magOut, 0.3, 900, 70);
{
  const c = bp(600, 2400);
  add(ev.reload.magOut + 0.05, 0.3, 0.12, 0.15, (x) => c(noise()) * Math.sin(Math.PI * x / 0.3) ** 2);   // slide out
}
click(ev.reload.magIn, 0.45, 620, 50);
click(ev.reload.magIn + 0.05, 0.3, 1400, 90);
click(ev.reload.handle, 0.32, 1100, 75);
click(ev.reload.handle + 0.11, 0.4, 780, 60);

// ---- soft limiter + WAV
let peak = 0;
for (let i = 0; i < N; i++) {
  L[i] = Math.tanh(L[i] * 1.15);
  R[i] = Math.tanh(R[i] * 1.15);
  peak = Math.max(peak, Math.abs(L[i]), Math.abs(R[i]));
}
const g = 0.92 / peak;
const buf = Buffer.alloc(44 + N * 4);
buf.write("RIFF", 0); buf.writeUInt32LE(36 + N * 4, 4); buf.write("WAVEfmt ", 8);
buf.writeUInt32LE(16, 16); buf.writeUInt16LE(1, 20); buf.writeUInt16LE(2, 22);
buf.writeUInt32LE(SR, 24); buf.writeUInt32LE(SR * 4, 28); buf.writeUInt16LE(4, 32); buf.writeUInt16LE(16, 34);
buf.write("data", 36); buf.writeUInt32LE(N * 4, 40);
for (let i = 0; i < N; i++) {
  buf.writeInt16LE(Math.round(L[i] * g * 32767), 44 + i * 4);
  buf.writeInt16LE(Math.round(R[i] * g * 32767), 46 + i * 4);
}
fs.writeFileSync(OUT, buf);
console.log("wrote", OUT, "peak", peak.toFixed(3));
