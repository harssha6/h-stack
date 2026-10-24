// Frame-perfect capture of an animated web flow. The page runs on a virtual clock that advances
// exactly 1/FPS per screenshot, so every frame lands and nothing stutters however slow the machine is.
//
//   node capture.mjs            (needs playwright-core; uses system Chrome, set CHROME_PATH to override)
//   FPS=60 DURATION=26 OUT=frames URL=http://localhost:3000/ node capture.mjs
//   ffmpeg -framerate 60 -i frames/f%05d.jpg -c:v libx264 -crf 12 -pix_fmt yuv420p take.mp4
//
// Edit the CHOREOGRAPHY block for each flow. Everything else is reusable.
import { chromium } from 'playwright-core';
import fs from 'node:fs';

const FPS = Number(process.env.FPS || 60);
const DURATION = Number(process.env.DURATION || 26);
const OUT = process.env.OUT || 'frames';
const URL = process.env.URL || 'http://localhost:3000/';
fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });

// Virtual time: performance.now, Date.now, timers and rAF only move when the loop advances them.
// CSS and WAAPI animations are paused and seeked to the same clock every frame.
const clock = () => {
  let vt = 0;
  const realSetTimeout = window.setTimeout.bind(window);
  const base = Date.now();
  window.__realSetTimeout = realSetTimeout;
  performance.now = () => vt;
  Date.now = () => base + vt;
  let id = 1;
  const timers = new Map();
  const rafs = new Map();
  window.setTimeout = (fn, ms = 0, ...a) => { const i = id++; timers.set(i, { t: vt + Math.max(0, Number(ms) || 0), fn, a }); return i; };
  window.setInterval = (fn, ms = 0, ...a) => { const every = Math.max(1, Number(ms) || 0); const i = id++; timers.set(i, { t: vt + every, fn, a, every }); return i; };
  window.clearTimeout = window.clearInterval = (i) => { timers.delete(i); };
  window.requestAnimationFrame = (fn) => { const i = id++; rafs.set(i, fn); return i; };
  window.cancelAnimationFrame = (i) => { rafs.delete(i); };
  const seen = new WeakMap();
  window.__sync = () => {
    for (const an of document.getAnimations()) {
      let s = seen.get(an);
      if (!s) { s = { at: vt, ct: Number(an.currentTime) || 0 }; seen.set(an, s); }
      if (an.playState !== 'paused') an.pause();
      an.currentTime = s.ct + (vt - s.at) * (an.playbackRate || 1);
    }
  };
  window.__advance = (ms) => {
    const end = vt + ms;
    for (;;) {
      let next = null;
      for (const entry of timers) if (entry[1].t <= end && (!next || entry[1].t < next[1].t)) next = entry;
      if (!next) break;
      const [i, t] = next;
      vt = Math.max(vt, t.t);
      if (t.every) t.t += t.every; else timers.delete(i);
      try { typeof t.fn === 'function' && t.fn(...t.a); } catch (e) { console.error(e); }
    }
    vt = end;
    const cbs = [...rafs.values()];
    rafs.clear();
    for (const cb of cbs) { try { cb(vt); } catch (e) { console.error(e); } }
  };
};

const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
const context = await browser.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 2, ignoreHTTPSErrors: true, reducedMotion: 'no-preference' });
await context.route(/umami|posthog|segment|analytics/, (route) => route.abort()); // keep the take out of product analytics
const page = await context.newPage();
page.on('pageerror', (e) => console.error('pageerror', e.message));
await page.addInitScript(clock);
await page.goto(URL, { waitUntil: 'load' });
await page.evaluate(() => document.fonts.ready);
const settle = () => page.evaluate(() => new Promise((r) => window.__realSetTimeout(() => window.__realSetTimeout(r, 0), 0)));
for (let i = 0; i < 60; i++) { await page.evaluate(() => window.__advance(1000 / 60)); await settle(); }

// Hide dev chrome and draw a visible cursor; headless screenshots have none.
await page.addStyleTag({ content: `nextjs-portal{display:none!important}
  #demo-cursor{position:fixed;left:0;top:0;width:20px;height:28px;z-index:2147483647;pointer-events:none;transform:translate(-100px,-100px)}` });
await page.evaluate(() => {
  const c = document.createElement('div');
  c.id = 'demo-cursor';
  c.innerHTML = '<svg width="20" height="28" viewBox="0 0 16 24"><path d="M1.5 1.5 L1.5 19 L6 14.8 L9.3 22 L12.4 20.6 L9.2 13.6 L15 13.6 Z" fill="#fff" stroke="#14120f" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  document.body.appendChild(c);
});

const rect = (selector) => page.evaluate((s) => { const r = document.querySelector(s)?.getBoundingClientRect(); return r && { x: r.left, y: r.top, w: r.width, h: r.height }; }, selector);
const center = async (selector, fx = 0.5, fy = 0.5) => { const r = await rect(selector); return { x: r.x + r.w * fx, y: r.y + r.h * fy }; };

// ---- CHOREOGRAPHY (seconds). Targets resolve when a move starts, so they follow the live layout.
// Arrive on a target about 0.5s before clicking it, and leave about 1.5s of stillness after each beat.
// Example selectors; replace them with ones from your own page.
const OPEN = 'button[aria-label="Open menu"]';
const ACTION = 'button[aria-label="Run action"]';
const CARD = '[data-demo="result-card"]';
const moves = [
  { from: 0.4, to: 1.6, target: () => center(OPEN, 0.5, 0.5) },
  { from: 3.0, to: 4.0, target: () => center(ACTION) },
  { from: 8.6, to: 9.4, target: async () => ({ x: 1120, y: 470 }) },
  { from: 11.2, to: 12.2, target: () => center(CARD, 0.35, 0.35) },
  { from: 12.3, to: 13.1, target: () => center(CARD, 0.85, 0.75) },
];
const clicks = [1.9, 4.4, 13.4];
let pos = { x: 1180, y: 640 };
// ---- end CHOREOGRAPHY

const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
let active = null;
const frames = Math.round(DURATION * FPS);
for (let f = 0; f < frames; f++) {
  const t = f / FPS;
  const m = moves.find((k) => t >= k.from && t <= k.to + 1 / FPS);
  if (m) {
    if (active !== m) { active = m; m.start = { ...pos }; m.end = await m.target(); }
    const p = ease(Math.min(1, (t - m.from) / (m.to - m.from)));
    pos = { x: m.start.x + (m.end.x - m.start.x) * p, y: m.start.y + (m.end.y - m.start.y) * p };
  }
  await page.mouse.move(pos.x, pos.y);
  await page.evaluate(({ x, y }) => { document.getElementById('demo-cursor').style.transform = `translate(${x - 2}px, ${y - 2}px)`; }, pos);
  // Compare frame indexes, not float times, or a click can fire twice.
  for (const c of clicks) if (Math.round(c * FPS) === f) { await page.mouse.down(); await page.mouse.up(); }
  await settle();
  await page.evaluate((ms) => window.__advance(ms), 1000 / FPS);
  await settle();
  await page.evaluate(() => window.__sync());
  await page.screenshot({ path: `${OUT}/f${String(f).padStart(5, '0')}.jpg`, type: 'jpeg', quality: 94 });
  if (f % 60 === 0) console.log(`frame ${f}/${frames}`);
}
await browser.close();
console.log('done', frames);
