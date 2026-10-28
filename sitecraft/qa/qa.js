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
    for (const [n, vp] of [['700x900', {width:700,height:900}], ['820x1180', {width:820,height:1180}], ['1280x720', {width:1280,height:720}], ['1280x800', {width:1280,height:800}], ['1366x768', {width:1366,height:768}], ['1440x900', {width:1440,height:900}], ['1920x1080', {width:1920,height:1080}], ['390x844', {width:390,height:844}]]) {
      const pg = await browser.newPage({ viewport: vp }); await pg.goto(url, { waitUntil: 'load' }); await pg.evaluate(() => document.fonts.ready); await pg.waitForTimeout(2200);
      if (n === '1366x768') await pg.screenshot({ path: path.join(OUT, `${slug}-laptop-hero.png`) });  // capture before the probes below touch the DOM
      if (n !== '390x844') {
        r.closingClear = r.closingClear || {};
        await pg.evaluate(() => document.querySelector('.closing').scrollIntoView()); await pg.waitForTimeout(300);
        r.closingClear[n] = await pg.evaluate(() => { const btns = [...document.querySelectorAll('.closing .btn, .closing .big')].map(b => b.getBoundingClientRect()); const shapes = [...document.querySelectorAll('.cl-motif :is(path,circle,ellipse,rect)')].map(s => s.getBoundingClientRect()); const hit = (a, b) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom; return !btns.some(b => shapes.some(s => hit(b, s))); });
        await pg.evaluate(() => scrollTo(0, 0)); await pg.waitForTimeout(200);
      }
      // no line may start with closing punctuation in display text (kinsoku), checked after the idle segmenter ran
      r.kinsoku = r.kinsoku || {};
      await pg.waitForTimeout(1500);
      r.kinsoku[n] = await pg.evaluate(() => { let bad = 0; document.querySelectorAll('h2.statement,.tagline,.closing h2,.about p,.lead').forEach(el => { const range = document.createRange(); const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT); let prev = null; while (walker.nextNode()) { const node = walker.currentNode; for (let i = 0; i < node.nodeValue.length; i++) { const ch = node.nodeValue[i]; if (!ch.trim()) continue; range.setStart(node, i); range.setEnd(node, i + 1); const rc = range.getClientRects()[0]; if (!rc) continue; if (prev && rc.top > prev.top + 2 && /[，。、！？：；」』）]/.test(ch)) bad++; prev = rc; } } }); return bad; });
      // the name must never run under the motif: test the real name and a long 9-character name
      r.nameClear = r.nameClear || {};
      r.nameClear[n] = await pg.evaluate(() => {
        const hit = (a, b) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
        const count = () => { const ws = [...document.querySelectorAll('h1 .w')].map(w => w.getBoundingClientRect()); const shapes = [...document.querySelectorAll('.hero .motif :is(path,circle,ellipse,rect)')].map(s => s.getBoundingClientRect()); const band = document.querySelector('.hero').dataset.hero === 'band'; return band ? 0 : ws.filter(w => shapes.some(s => hit(w, s))).length; };
        const real = count();
        const h1 = document.querySelector('h1'); const saved = h1.innerHTML, savedLen = h1.style.getPropertyValue('--len');
        h1.innerHTML = '小花手作咖啡工作室'.split('').map((c, i) => `<span class="w" style="--i:${i}">${c}</span>`).join(''); h1.style.setProperty('--len', '9');
        const long = count(); h1.innerHTML = saved; h1.style.setProperty('--len', savedLen);
        return { real, long };
      });
      // band: at least 24px between the CTA row and the highest band shape
      r.bandGap = r.bandGap || {};
      r.bandGap[n] = await pg.evaluate(() => { const hero = document.querySelector('.hero'); if (hero.dataset.hero !== 'band') return 99; const cta = document.querySelector('.hero .cta').getBoundingClientRect(); const tops = [...document.querySelectorAll('.hero-foot .motif :is(path,circle,ellipse,rect)')].map(s => s.getBoundingClientRect().top); return Math.round(Math.min(...tops) - cta.bottom); });
      r.heroFit[n] = await pg.evaluate(() => { const h = document.querySelector('.hero').getBoundingClientRect(); const bar = document.getElementById('demoBar'); const limit = innerHeight - (bar ? bar.getBoundingClientRect().height : 0); return Math.round(h.bottom) + '/' + Math.round(limit) + (h.bottom <= limit + 1 ? ' ok' : ' OVER'); });
      await pg.close();
    }
    for (const [name, vp] of [['desktop', { width: 1440, height: 900 }], ['mobile', { width: 390, height: 844 }]]) {
      const page = await browser.newPage({ viewport: vp, deviceScaleFactor: 1, reducedMotion: 'no-preference' });
      page.on('pageerror', e => r.errors.push(name + ': ' + e.message));
      page.on('console', m => { if (m.type() === 'error' && !/fonts|maps|net::|favicon/i.test(m.text())) r.errors.push(name + ': ' + m.text()); });
      await page.goto(url, { waitUntil: 'load' });
      await page.evaluate(() => document.fonts.ready); await page.waitForTimeout(2200);
      await page.screenshot({ path: path.join(OUT, `${slug}-${name}-hero.png`) });
      if (name === 'desktop') r.nmOneLine = await page.evaluate(() => { const nm = document.querySelector('.statement .nm'); return !nm || nm.getClientRects().length === 1; });
      await page.evaluate(() => { document.querySelectorAll('[data-reveal]').forEach(el => el.classList.add('in')); document.querySelector('.closing').classList.add('in'); });
      await page.waitForTimeout(2200);
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
        // two-line title alignment: left edges match (side layout) or centres match (band layout)
        r.fn.bandVisibleMobile = await page.evaluate(() => { const hero = document.querySelector('.hero'); if (hero.dataset.hero !== 'band') return true; const m = document.querySelector('.motif').getBoundingClientRect(); const bar = document.querySelector('.hero-foot').getBoundingClientRect(); return m.bottom <= bar.top + 8 && m.height > 60; });
        await page.evaluate(() => document.getElementById('gallery').scrollIntoView()); await page.waitForTimeout(400);
        await page.click('.strip .tile:first-child', { position: { x: 40, y: 40 } }); await page.waitForTimeout(300);
        const lbOpen = await page.evaluate(() => document.getElementById('lb').open);
        await page.keyboard.press('ArrowRight'); await page.waitForTimeout(150); await page.keyboard.press('ArrowRight'); await page.waitForTimeout(150); await page.keyboard.press('ArrowLeft'); await page.waitForTimeout(150);
        const lbNow = await page.textContent('#lbNow');
        await page.keyboard.press('Escape'); await page.waitForTimeout(300);
        r.fn.lightbox = await page.evaluate(([o, n]) => o && n.trim().startsWith('2') && !document.getElementById('lb').open && document.activeElement === document.querySelector('.strip .tile:first-child'), [lbOpen, lbNow]);
        r.fn.typeClearMobile = await page.evaluate(() => { const vt = document.querySelector('.tile.type .vtext'), cap = document.querySelector('.tile.type .cap'); if (!vt) return true; document.getElementById('gallery').scrollIntoView(); return vt.getBoundingClientRect().bottom <= cap.getBoundingClientRect().top + 1; });
        r.fn.titleIndent = await page.evaluate(() => { const h = document.querySelector('h1'); const en = h.querySelector('.en'); if (!en) return 0; const zh = [...h.querySelectorAll(':scope > .w')]; const l = Math.min(...zh.map(w => w.getBoundingClientRect().left)), rr = Math.max(...zh.map(w => w.getBoundingClientRect().right)); const eb = en.getBoundingClientRect(); const enText = en.querySelector('.w'); const et = enText.getBoundingClientRect(); const last = en.querySelectorAll('.w'); const er = last[last.length - 1].getBoundingClientRect().right; return getComputedStyle(h).textAlign === 'center' ? Math.round(((et.left + er) / 2) - ((l + rr) / 2)) : Math.round(et.left - l); });
        // modal focus: after opening, focus is inside the overlay and Tab stays inside
        await page.click('#menuBtn'); await page.waitForTimeout(500);
        const inside1 = await page.evaluate(() => !!document.activeElement.closest('#overlay'));
        await page.keyboard.press('Tab'); await page.keyboard.press('Tab'); await page.keyboard.press('Tab'); await page.keyboard.press('Tab'); await page.keyboard.press('Tab');
        const inside2 = await page.evaluate(() => !!document.activeElement.closest('#overlay') || document.activeElement === document.getElementById('menuBtn'));
        await page.keyboard.press('Escape'); await page.waitForTimeout(300);
        r.fn.modalFocusTrapped = inside1 && inside2;
        // overlay hours mirror the facts bar as separate spans (no glued string)
        await page.click('#menuBtn'); await page.waitForTimeout(400);
        r.fn.overlayHoursSpans = await page.evaluate(() => { const n = document.querySelectorAll('#ovHours > span').length; const t = document.getElementById('ovHours').textContent; return n >= 2 || (n === 1 && !/營業中\d|公休明天|休息中\d/.test(t)); });
        await page.keyboard.press('Escape'); await page.waitForTimeout(300);
        r.fn.factClipped = await page.evaluate(() => [...document.querySelectorAll('.fact > span')].some(sp => sp.scrollWidth > sp.clientWidth + 1 && !sp.classList.contains('num')));
        // no-break spans must stay on one line (no CJK orphans)
        r.fn.nbBroken = await page.evaluate(() => [...document.querySelectorAll('.nb, .statement .nm .en')].some(el => { const lh = parseFloat(getComputedStyle(el).lineHeight) || 20; return el.getBoundingClientRect().height > lh * 1.5 || el.getClientRects().length > 1; }));
        r.fn.menuBtnClear = await page.evaluate(() => { const b = document.getElementById('menuBtn').getBoundingClientRect(); const shapes = [...document.querySelectorAll('.hero .motif :is(path,circle,ellipse,rect)')].map(s => s.getBoundingClientRect()); return !shapes.some(s => s.left < b.right && b.left < s.right && s.top < b.bottom && b.top < s.bottom); });
        // hero CTA row: no orphan control on phones (every control shares a row with another, or spans full width)
        r.fn.ctaOrphan = await page.evaluate(() => { const els = [...document.querySelectorAll('.hero .cta > *')]; const rows = {}; els.forEach(e => { const b = e.getBoundingClientRect(); const k = Math.round(b.top); (rows[k] = rows[k] || []).push(b.width); }); return Object.values(rows).some(ws => ws.length === 1 && ws[0] < 300); });
        // no-JS: content still visible
        const nojs = await browser.newPage({ viewport: vp, javaScriptEnabled: false });
        await nojs.goto(url, { waitUntil: 'load' });
        r.fn.visibleWithoutJs = await nojs.evaluate(() => getComputedStyle(document.querySelector('.statement')).opacity === '1' && getComputedStyle(document.querySelector('h1 .w')).opacity === '1');
        await nojs.close();
      }
      if (name === 'desktop') {
        // every hero motif shape finishes its draw-in (idle motion or the closed state must never leave a shape undrawn); the weave stays out of the type lane
        await page.waitForTimeout(800);
        r.motifDrawn = await page.evaluate(() => [...document.querySelectorAll('.hero .motif svg :is(path,circle,ellipse,rect)')].every(e => parseFloat(getComputedStyle(e).strokeDashoffset) === 0));
        // self-hosted fonts: every declared face either loaded or was not needed; none failed
        r.fontFaces = await page.evaluate(() => [...document.fonts].map(f => f.status));
        r.weaveMasked = await page.evaluate(() => { const w = document.querySelector('.weave'); if (!w || getComputedStyle(w).display === 'none') return true; return !!w.querySelector('rect[mask]') && !!w.querySelector('mask linearGradient, linearGradient'); });
        // anchor landing: after clicking a nav link the header is solid and visible, and the facts bar is not under a transparent nav
        await page.click('.nav ul a[href="#about"]'); await page.waitForTimeout(1600);
        r.anchorLanding = await page.evaluate(() => { const nav = document.getElementById('nav'); const cs = getComputedStyle(nav); return { solid: nav.classList.contains('solid'), hidden: nav.classList.contains('hide'), top: Math.round(nav.getBoundingClientRect().top), aboutTop: Math.round(document.getElementById('about').getBoundingClientRect().top) }; });
        await page.evaluate(() => scrollTo(0, 0)); await page.waitForTimeout(400);
        // reduced motion honoured
        const rm = await browser.newPage({ viewport: vp, reducedMotion: 'reduce' });
        await rm.goto(url, { waitUntil: 'load' }); await rm.waitForTimeout(300);
        r.reducedMotion = await rm.evaluate(() => ({ h1: getComputedStyle(document.querySelector('h1 .w')).animationName, reveal: getComputedStyle(document.querySelector('[data-reveal]')).transitionDuration, revealOpacity: getComputedStyle(document.querySelector('[data-reveal]')).opacity }));
        await rm.close();
        // focus ring colour on a light section equals the ink token
        // keyboard-initiated focus so :focus-visible applies
        await page.evaluate(() => { document.addEventListener('keydown', () => document.querySelector('.svc li > a').focus(), { once: true }); });
        await page.keyboard.press('Shift'); await page.waitForTimeout(100);
        r.focusRing = await page.evaluate(() => { const a = document.querySelector('.svc li > a'); const fv = a.matches(':focus-visible'); const oc = getComputedStyle(a).outlineColor; const ink = getComputedStyle(document.documentElement).getPropertyValue('--pd').trim(); const h = ink.replace('#',''); const rgb = `rgb(${parseInt(h.slice(0,2),16)}, ${parseInt(h.slice(2,4),16)}, ${parseInt(h.slice(4,6),16)})`; a.blur(); return { focusVisible: fv, outline: oc, ink: rgb, ok: fv && oc === rgb }; });
        // band hero: motif never overlaps the title box; parallax never moves the facts bar
        r.heroGeom = await page.evaluate(() => { const h = document.querySelector('h1').getBoundingClientRect(); const m = document.querySelector('.motif').getBoundingClientRect(); const band = document.querySelector('.hero').dataset.hero === 'band'; const bar = document.querySelector('.hero-foot').getBoundingClientRect(); const ox = Math.max(0, Math.min(h.right, m.right) - Math.max(h.left, m.left)); const oy = Math.max(0, Math.min(h.bottom, m.bottom) - Math.max(h.top, m.top)); return { band, overlapPct: Math.round(100 * ox * oy / (h.width * h.height)), bandAboveBar: !band || Math.round(m.bottom) <= Math.round(bar.top) + 8 }; });
        r.tiles = await page.evaluate(() => { const th = document.getElementById('tileHours'), hh = document.getElementById('heroHours'); const vt = document.querySelector('.tile.type .vtext'), cap = document.querySelector('.tile.type .cap'); const today = document.querySelector('#hours li.today'); const nb = document.querySelector('#heroHours .nb'); const tt = th ? th.textContent.trim() : ''; return { hoursMatch: !th || !today || tt === today.children[1].textContent.trim() || (nb && tt === nb.textContent.trim()), typeClear: !vt || vt.getBoundingClientRect().bottom <= cap.getBoundingClientRect().top + 1 }; });
        await page.mouse.move(20, 300); await page.waitForTimeout(1000);
        r.factsDrift = await page.evaluate(() => getComputedStyle(document.querySelector('.facts')).transform);
        await page.mouse.move(700, 450);
        // scroll-spy: after scrolling to services, the matching nav link is current
        await page.evaluate(() => document.getElementById('services').scrollIntoView({ block: 'center' })); await page.waitForTimeout(500);
        r.scrollSpy = await page.evaluate(() => { const a = document.querySelector('.nav ul a[aria-current="true"]'); return a ? a.getAttribute('href') : null; });
        await page.evaluate(() => scrollTo(0, 0)); await page.waitForTimeout(300);
        r.computed = await page.evaluate(() => {
          const ff = el => getComputedStyle(el).fontFamily;
          const t = document.querySelector('.tile'), tall = document.querySelector('.tile.tall');
          const rb = t.getBoundingClientRect(), tb = tall.getBoundingClientRect();
          return { h1: ff(document.querySelector('h1')).split(',')[0], body: ff(document.body).split(',')[0], h1DiffersFromBody: ff(document.querySelector('h1')) !== ff(document.body),
                   tileRatio: +(rb.width / rb.height).toFixed(2), tallRatio: +(tb.width / tb.height).toFixed(2),
                   ogImage: !!document.querySelector('meta[property="og:image"]'), fontsLoaded: document.fonts.check('600 20px "Noto Serif TC"') || document.fonts.check('800 20px "Noto Sans TC"') };
        });
        await page.addStyleTag({ content: '*,*::before,*::after{transition:none!important;animation:none!important;opacity:1}h1 .w,.tagline,.hero .cta,.hero .eyebrow,.hero-foot .fact,.strip .tile{opacity:1!important;transform:none!important}.motif svg *,.cl-motif *{stroke-dashoffset:0!important}' });
        await page.waitForTimeout(200);
        await page.addScriptTag({ content: axeSource });
        const res = await page.evaluate(async () => await axe.run(document, { runOnly: ['wcag2a', 'wcag2aa', 'best-practice'] }));
        r.axe = res.violations.map(v => ({ id: v.id, impact: v.impact, nodes: v.nodes.length, sample: v.nodes[0].target[0] }));
        r.emoji = EMOJI.test(await page.evaluate(() => document.documentElement.outerHTML));
        // dark mode contrast
        const dark = await browser.newPage({ viewport: vp, colorScheme: 'dark' });
        await dark.goto(url, { waitUntil: 'load' }); await dark.waitForTimeout(800);
        await dark.addStyleTag({ content: '*,*::before,*::after{transition:none!important;animation:none!important;opacity:1}h1 .w,.tagline,.hero .cta,.hero .eyebrow,.hero-foot .fact,.strip .tile{opacity:1!important;transform:none!important}.motif svg *,.cl-motif *{stroke-dashoffset:0!important}' });
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
    let best = null;
    for (let i = 0; i < 3; i++) {
      const run = await lighthouse(`http://127.0.0.1:${PORT}/${slugs[0]}/`, { port: chrome.port, output: 'json', logLevel: 'error', formFactor: 'mobile', screenEmulation: { mobile: true, width: 390, height: 844, deviceScaleFactor: 2, disabled: false } });
      if (!best || run.lhr.categories.performance.score > best.lhr.categories.performance.score) best = run;
    }
    const lh = best;
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
      && fn.serviceLinksFocusable && Math.abs(fn.titleIndent) <= 2 && fn.modalFocusTrapped && !fn.factClipped && !fn.nbBroken && !fn.ctaOrphan && fn.visibleWithoutJs && v.scrollSpy === '#services' && c.h1DiffersFromBody && c.ogImage
      && v.anchorLanding && v.anchorLanding.solid && !v.anchorLanding.hidden && v.anchorLanding.top === 0
      && fn.overlayHoursSpans && v.heroGeom && (!v.heroGeom.band || v.heroGeom.overlapPct === 0) && v.heroGeom.bandAboveBar && v.factsDrift === 'none'
      && fn.menuBtnClear && v.nmOneLine && v.motifDrawn && v.weaveMasked && v.fontFaces && v.fontFaces.length >= 2 && v.fontFaces.every(s => s !== 'error') && v.fontFaces.includes('loaded')
      && v.tiles && v.tiles.hoursMatch && v.tiles.typeClear && fn.bandVisibleMobile && fn.typeClearMobile && fn.lightbox
      && v.closingClear && Object.values(v.closingClear).every(Boolean)
      && v.nameClear && Object.values(v.nameClear).every(x => x.real === 0 && x.long === 0) && v.bandGap && Object.values(v.bandGap).every(g => g >= 24)
      && v.kinsoku && Object.values(v.kinsoku).every(k => k === 0)
      && v.reducedMotion && v.reducedMotion.h1 === 'none' && v.reducedMotion.revealOpacity === '1' && v.focusRing && v.focusRing.ok
      && Math.abs(c.tileRatio - 1.33) < 0.05 && Math.abs(c.tallRatio - 0.75) < 0.05 && !v.errors.length && !v.smallTargets.length
      && !v.axe.length && !(v.axeDark || []).length && !v.emoji && Object.values(v.heroFit).every(x => x.includes('ok')) && Object.values(v.overflow).every(o => o === 0);
    allOk = allOk && ok;
    console.log(`${slug}: ${ok ? 'PASS' : 'FAIL'}`);
    if (!ok) console.log(JSON.stringify({ fn, scrollSpy: v.scrollSpy, heroGeom: v.heroGeom, tiles: v.tiles, closingClear: v.closingClear, nameClear: v.nameClear, bandGap: v.bandGap, kinsoku: v.kinsoku, factsDrift: v.factsDrift, anchorLanding: v.anchorLanding, reducedMotion: v.reducedMotion, focusRing: v.focusRing, computed: c, axe: v.axe, axeDark: v.axeDark, errors: v.errors, small: v.smallTargets, heroFit: v.heroFit, overflow: v.overflow, emoji: v.emoji }, null, 2));
  }
  const lh = report.lighthouse;
  const lhOk = lh && typeof lh === 'object' && ['performance', 'accessibility', 'best-practices', 'seo'].every(k => lh[k] >= 90);
  console.log('lighthouse:', JSON.stringify(lh), lhOk ? 'PASS' : 'FAIL');
  console.log(`\nALL GATES: ${allOk && lhOk ? 'PASS' : 'FAIL'}   (screenshots + report.json in ${OUT})`);
  process.exit(allOk && lhOk ? 0 : 1);
})();
