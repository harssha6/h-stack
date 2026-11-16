// Usage: node qa_viewer.cjs /abs/viewer.html /tmp/outdir   (PLAYWRIGHT=/path/to/node_modules/playwright, CHROME=/path/to/chrome)
const fs = require('fs');
const { pathToFileURL } = require('url');
const pw = process.env.PLAYWRIGHT || 'playwright'; const { chromium } = require(pw);
(async () => {
  const file = process.argv[2], out = (process.argv[3] || '/tmp/svm-qa').replace(/\/$/, ''); require('fs').mkdirSync(out, { recursive: true });
  const installed = ['/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'].find(p => fs.existsSync(p));
  const b = await chromium.launch({ executablePath: process.env.CHROME || installed });
  try { const p = await b.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  const errs = []; p.on('pageerror', e => errs.push(String(e))); p.on('console', m => m.type() === 'error' && errs.push(m.text()));
  await p.goto(pathToFileURL(require('path').resolve(file)).href); await p.waitForTimeout(600);
  await p.getByRole('button', { name: '2 columns', exact: true }).click();
  await p.screenshot({ path: out + '/1_grid.png', fullPage: true });
  await p.click('.toolbar .pop-wrap .btn'); await p.waitForTimeout(250);
  await p.screenshot({ path: out + '/2_menu.png', clip: { x: 0, y: 0, width: 1440, height: 560 } });
  await p.click('.pop.open .opt:nth-of-type(2)'); await p.waitForTimeout(300);
  await p.locator('main .shot').nth(1).click(); await p.waitForTimeout(350);
  await p.screenshot({ path: out + '/3_focus.png' });
  await p.keyboard.press('Escape'); await p.waitForTimeout(250);
  await p.click('.tab:nth-of-type(2)'); await p.waitForTimeout(300);
  await p.click('.toolbar .seg:last-of-type button:nth-of-type(2)'); await p.waitForTimeout(300);
  const box = await p.$('.swipe'); const bb = await box.boundingBox();
  await p.mouse.move(bb.x + bb.width * .3, bb.y + 100); await p.mouse.down(); await p.mouse.move(bb.x + bb.width * .62, bb.y + 100, { steps: 5 }); await p.mouse.up();
  await p.screenshot({ path: out + '/4_swipe.png' });
  await p.click('.tab:nth-of-type(3)'); await p.waitForTimeout(300); await p.screenshot({ path: out + '/5_scores.png' });
  // pointer cursor audit
  await p.click('.tab:nth-of-type(1)'); await p.waitForTimeout(300);
  const bad = await p.$$eval('button, [role=button], select, a', els => els.filter(e => getComputedStyle(e).cursor !== 'pointer' && !e.classList.contains('shot')).map(e => e.className || e.tagName));
  console.log('non-pointer clickables:', JSON.stringify(bad));
  await p.setViewportSize({ width: 390, height: 844 }); await p.waitForTimeout(300); await p.screenshot({ path: out + '/6_mobile.png' });
  const broken = await p.locator('main img').evaluateAll(els => els.filter(e => !e.complete || !e.naturalWidth).map(e => e.alt));
  console.log('errors:', JSON.stringify(errs));
  if (errs.length || bad.length || broken.length) throw new Error('Viewer QA failed: console, cursor or image errors');
  console.log('PASS: coverage, focus, swipe, scores and mobile');
  } finally { await b.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
