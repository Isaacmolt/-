// SiteCraft quality gate: screenshots + axe + layout checks + emoji scan + Lighthouse
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const axeSource = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');

const SITES = path.resolve(__dirname, '..', 'sites');
const PORT = 8765;
const slugs = (process.argv[2] || 'demo-cafe,demo-hair,demo-pet').split(',');
const round = process.argv[3] || new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-');
const OUT = path.join(__dirname, 'shots', round);
fs.mkdirSync(OUT, { recursive: true });
const EMOJI = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{1F000}-\u{1F2FF}\u{FE0F}]/u;

(async () => {
  const server = spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1'], { cwd: SITES, stdio: 'ignore' });
  await new Promise(r => setTimeout(r, 800));
  const browser = await chromium.launch();
  const report = {};
  for (const slug of slugs) {
    const url = `http://127.0.0.1:${PORT}/${slug}/`;
    const r = { errors: [], overflow: {}, smallTargets: [], axe: [], emoji: false };
    r.heroFit = {};
    for (const [n, vp] of [['1366x768', {width:1366,height:768}], ['1440x900', {width:1440,height:900}], ['390x844', {width:390,height:844}]]) {
      const pg = await browser.newPage({ viewport: vp }); await pg.goto(url, { waitUntil: 'load' }); await pg.waitForTimeout(1200);
      r.heroFit[n] = await pg.evaluate(() => { const h = document.querySelector('.hero').getBoundingClientRect(); const bar = document.getElementById('demoBar'); const limit = innerHeight - (bar ? bar.getBoundingClientRect().height : 0); return Math.round(h.bottom) + '/' + Math.round(limit) + (h.bottom <= limit + 1 ? ' ok' : ' OVER'); });
      if (n === '1366x768') await pg.screenshot({ path: path.join(OUT, `${slug}-laptop-hero.png`) });
      await pg.close();
    }
    for (const [name, vp] of [['desktop', { width: 1440, height: 900 }], ['mobile', { width: 390, height: 844 }]]) {
      const page = await browser.newPage({ viewport: vp, deviceScaleFactor: 1, reducedMotion: 'no-preference' });
      page.on('pageerror', e => r.errors.push(name + ': ' + e.message));
      page.on('console', m => { if (m.type() === 'error' && !/fonts|maps|net::|favicon/i.test(m.text())) r.errors.push(name + ': ' + m.text()); });
      await page.goto(url, { waitUntil: 'load' });
      await page.evaluate(() => document.fonts.ready); await page.waitForTimeout(1500);
      await page.screenshot({ path: path.join(OUT, `${slug}-${name}-hero.png`) });
      await page.evaluate(() => document.querySelectorAll('[data-reveal]').forEach(el => el.classList.add('in')));
      await page.waitForTimeout(800);
      await page.screenshot({ path: path.join(OUT, `${slug}-${name}-full.png`), fullPage: true });
      r.overflow[name] = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      if (name === 'mobile') {
        r.smallTargets = await page.evaluate(() => [...document.querySelectorAll('a,button')].filter(el => {
          const b = el.getBoundingClientRect(); const cs = getComputedStyle(el);
          return cs.display !== 'none' && cs.visibility !== 'hidden' && b.width > 0 && (b.width < 40 || b.height < 40);
        }).map(el => `${el.tagName.toLowerCase()}.${el.className} "${(el.textContent||el.getAttribute('aria-label')||'').trim().slice(0,20)}" ${Math.round(el.getBoundingClientRect().width)}x${Math.round(el.getBoundingClientRect().height)}`));
        // functional: FAB hidden on first paint, menu opens/closes by tapping the button, gallery advances, service links focusable
        r.fn = {};
        r.fn.fabHiddenAtTop = await page.evaluate(() => { const f = document.querySelector('.fab'); return !f || getComputedStyle(f).opacity === '0'; });
        await page.click('#menuBtn'); await page.waitForTimeout(800);
        await page.screenshot({ path: path.join(OUT, `${slug}-mobile-menu.png`) });
        const bb = await page.locator('#menuBtn').boundingBox();
        r.fn.menuBtnOnTop = await page.evaluate(([x, y]) => document.elementFromPoint(x, y).closest('#menuBtn') !== null, [bb.x + bb.width / 2, bb.y + bb.height / 2]);
        await page.mouse.click(bb.x + bb.width / 2, bb.y + bb.height / 2); await page.waitForTimeout(900);
        r.fn.menuClosedByTap = await page.evaluate(() => !document.getElementById('overlay').classList.contains('open'));
        await page.evaluate(() => document.getElementById('gallery').scrollIntoView()); await page.waitForTimeout(300);
        await page.click('#nextTile'); await page.waitForTimeout(700); await page.click('#nextTile'); await page.waitForTimeout(700);
        r.fn.galleryCounterAfter2Next = await page.textContent('#tileNow');
        await page.click('#prevTile'); await page.waitForTimeout(700);
        r.fn.galleryCounterAfterPrev = await page.textContent('#tileNow');
        r.fn.serviceLinksFocusable = await page.evaluate(() => [...document.querySelectorAll('.svc li > a')].every(a => { a.focus(); return document.activeElement === a; }));
        r.fn.titleIndent = await page.evaluate(() => { const h = document.querySelector('h1'); const first = h.querySelector('.w'); const en = h.querySelector('.en .w'); return en ? Math.round(en.getBoundingClientRect().left - first.getBoundingClientRect().left) : 0; });
        // modal focus: after opening, focus is inside the overlay and Tab stays inside
        await page.click('#menuBtn'); await page.waitForTimeout(500);
        const inside1 = await page.evaluate(() => !!document.activeElement.closest('#overlay'));
        await page.keyboard.press('Tab'); await page.keyboard.press('Tab'); await page.keyboard.press('Tab'); await page.keyboard.press('Tab'); await page.keyboard.press('Tab');
        const inside2 = await page.evaluate(() => !!document.activeElement.closest('#overlay') || document.activeElement === document.getElementById('menuBtn'));
        await page.keyboard.press('Escape'); await page.waitForTimeout(300);
        r.fn.modalFocusTrapped = inside1 && inside2;
        r.fn.factClipped = await page.evaluate(() => [...document.querySelectorAll('.fact > span')].some(sp => sp.scrollWidth > sp.clientWidth + 1 && !sp.classList.contains('num')));
      }
      if (name === 'desktop') {
        r.computed = await page.evaluate(() => {
          const ff = el => getComputedStyle(el).fontFamily;
          const t = document.querySelector('.tile'), tall = document.querySelector('.tile.tall');
          const rb = t.getBoundingClientRect(), tb = tall.getBoundingClientRect();
          return { h1: ff(document.querySelector('h1')).split(',')[0], body: ff(document.body).split(',')[0], h1DiffersFromBody: ff(document.querySelector('h1')) !== ff(document.body),
                   tileRatio: +(rb.width / rb.height).toFixed(2), tallRatio: +(tb.width / tb.height).toFixed(2),
                   ogImage: !!document.querySelector('meta[property="og:image"]'), fontsLoaded: document.fonts.check('600 20px "Noto Serif TC"') || document.fonts.check('800 20px "Noto Sans TC"') };
        });
        await page.addStyleTag({ content: '*,*::before,*::after{transition:none!important;animation:none!important;opacity:1}' });
        await page.waitForTimeout(200);
        await page.addScriptTag({ content: axeSource });
        const res = await page.evaluate(async () => await axe.run(document, { runOnly: ['wcag2a', 'wcag2aa', 'best-practice'] }));
        r.axe = res.violations.map(v => ({ id: v.id, impact: v.impact, nodes: v.nodes.length, sample: v.nodes[0].target[0] }));
        r.emoji = EMOJI.test(await page.evaluate(() => document.documentElement.outerHTML));
        // dark mode contrast
        const dark = await browser.newPage({ viewport: vp, colorScheme: 'dark' });
        await dark.goto(url, { waitUntil: 'load' }); await dark.waitForTimeout(800);
        await dark.addStyleTag({ content: '*,*::before,*::after{transition:none!important;animation:none!important;opacity:1}' });
        await dark.evaluate(() => document.querySelectorAll('[data-reveal]').forEach(el => el.classList.add('in')));
        await dark.waitForTimeout(200);
        await dark.screenshot({ path: path.join(OUT, `${slug}-desktop-dark.png`), fullPage: true });
        await dark.addScriptTag({ content: axeSource });
        const dres = await dark.evaluate(async () => await axe.run(document, { runOnly: ['wcag2aa'] }));
        r.axeDark = dres.violations.map(v => ({ id: v.id, nodes: v.nodes.length, sample: v.nodes[0].target[0] }));
        await dark.close();
      }
      await page.close();
    }
    report[slug] = r;
  }
  await browser.close();
  // Lighthouse on the first slug (desktop)
  try {
    const lighthouse = (await import('lighthouse')).default;
    const chromeLauncher = await import('chrome-launcher');
    const chromePath = process.env.CHROME_PATH || chromium.executablePath();
    const chrome = await chromeLauncher.launch({ chromePath, chromeFlags: ['--headless=new', '--no-sandbox', '--disable-gpu'] });
    const lh = await lighthouse(`http://127.0.0.1:${PORT}/${slugs[0]}/`, { port: chrome.port, output: 'json', logLevel: 'error', formFactor: 'mobile', screenEmulation: { mobile: true, width: 390, height: 844, deviceScaleFactor: 2, disabled: false } });
    const c = lh.lhr.categories;
    report.lighthouse = Object.fromEntries(Object.keys(c).map(k => [k, Math.round(c[k].score * 100)]));
    report.lighthouseFails = Object.values(lh.lhr.audits).filter(a => a.score !== null && a.score < 0.9 && a.scoreDisplayMode !== 'informative').map(a => `${a.id} (${a.score}) ${a.displayValue||''}`).slice(0, 25);
    await chrome.kill();
  } catch (e) { report.lighthouse = 'failed: ' + e.message.split('\n')[0]; }
  server.kill();
  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));
  let allOk = true;
  for (const slug of slugs) {
    const v = report[slug], fn = v.fn || {}, c = v.computed || {};
    const ok = fn.fabHiddenAtTop && fn.menuBtnOnTop && fn.menuClosedByTap && fn.galleryCounterAfter2Next === '3' && fn.galleryCounterAfterPrev === '2'
      && fn.serviceLinksFocusable && fn.titleIndent === 0 && fn.modalFocusTrapped && !fn.factClipped && c.h1DiffersFromBody && c.ogImage
      && Math.abs(c.tileRatio - 1.33) < 0.05 && Math.abs(c.tallRatio - 0.75) < 0.05 && !v.errors.length && !v.smallTargets.length
      && !v.axe.length && !(v.axeDark || []).length && !v.emoji && Object.values(v.heroFit).every(x => x.includes('ok')) && Object.values(v.overflow).every(o => o === 0);
    allOk = allOk && ok;
    console.log(`${slug}: ${ok ? 'PASS' : 'FAIL'}`);
    if (!ok) console.log(JSON.stringify({ fn, computed: c, axe: v.axe, axeDark: v.axeDark, errors: v.errors, small: v.smallTargets, heroFit: v.heroFit, overflow: v.overflow, emoji: v.emoji }, null, 2));
  }
  const lh = report.lighthouse;
  const lhOk = lh && typeof lh === 'object' && ['performance', 'accessibility', 'best-practices', 'seo'].every(k => lh[k] >= 90);
  console.log('lighthouse:', JSON.stringify(lh), lhOk ? 'PASS' : 'FAIL');
  console.log(`\nALL GATES: ${allOk && lhOk ? 'PASS' : 'FAIL'}   (screenshots + report.json in ${OUT})`);
  process.exit(allOk && lhOk ? 0 : 1);
})();
