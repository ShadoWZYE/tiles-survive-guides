/* Render the data-derived SVGs, then verify the offline map in a browser.
 * Set PLAYWRIGHT_MODULE and EDGE_BINARY if the bundled paths differ.
 */
const fs = require('fs');
const path = require('path');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE ||
  'C:/Users/Shadow/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');

(async () => {
  const output = path.resolve(__dirname, '../outputs/state-map');
  const browser = await chromium.launch({ headless: true, executablePath: process.env.EDGE_BINARY ||
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe' });
  try {
    const page = await browser.newPage({ viewport: { width: 3200, height: 2560 }, deviceScaleFactor: 1 });
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    for (const lang of ['EN', 'RU']) {
      const svg = fs.readFileSync(path.join(output, `State-1005-Capture-Map-${lang}.svg`), 'utf8');
      await page.setContent('<html><style>body{margin:0}</style>' + svg + '</html>');
      await page.screenshot({ path: path.join(output, `State-1005-Capture-Map-${lang}.png`) });
    }
    await page.setViewportSize({ width: 1500, height: 1000 });
    await page.goto('file:///' + path.join(output, 'State-1005-Interactive-Map.html').replaceAll('\\', '/'));
    assert.equal(await page.locator('.region').count(), 110);
    assert.equal(await page.locator('.city').count(), 110);
    assert.equal(await page.locator('#targets button').count(), 36);
    for (const [coords, plan] of [['828:588','VeD #1'], ['908:508','ALL'], ['1108:468','VeD #2'], ['408:528','TCE'], ['688:188','Unassigned'], ['908:768','VeD #3'],
      ['968:768', 'VeD #4'], ['968:488','VeD #5'], ['1048:528','VeD #6'],
      ['1108:568','Unassigned'], ['508:588', 'VAN'], ['328:188','VAN'], ['468:248','VAN'], ['248:348','TCE'], ['848:328', 'ALL'], ['948:188','ALL'], ['868:988','rus'], ['648:948','rus'], ['408:828','ECL'], ['328:748','ECL'], ['648:328','VAN'], ['308:468','TCE'], ['248:668','ECL'], ['168:628','ECL'], ['388:988','rus'], ['728:1068','rus'], ['968:1068','rus'], ['1008:1128','rus'], ['248:488','TCE'], ['168:348','TCE'], ['168:488','TCE'], ['248:848','ECL'], ['668:828','ECL']]) {
      await page.locator('#search').fill(coords);
      await page.locator('#search').press('Enter');
      assert.ok((await page.locator('#detail').innerText()).includes(plan));
      assert.ok((await page.locator('#detail').innerText()).includes(coords));
    }
    const van=await page.evaluate(()=>DATA.cities.find(c=>c.x===328&&c.y===188));
    assert.equal(van.confirmed_owner,'VAN');
    assert.equal(van.ownership_reported,'2026-10-29');
    assert.equal(await page.locator('#detail .pill').innerText(),'ECL');
    const state=await page.evaluate(()=>({contested:DATA.cities.filter(c=>c.contested),base:DATA.cities.find(c=>c.x===668&&c.y===828)}));
    assert.deepEqual(state.contested,[]);
    assert.deepEqual(state.base.claims,['ECL']);
    assert.equal(state.base.confirmed_owner,'ECL');
    assert.equal(await page.locator(`.region[data-area="${state.base.area_id}"]`).getAttribute('fill'),'#236b79');
    await page.locator('#level').selectOption('6');
    assert.equal(await page.locator('.region.dim').count(), 107);
    await page.locator('#level').selectOption('0');
    await page.locator('#locale').click();
    assert.ok((await page.locator('#detail h2').innerText()).includes('Военная база'));
    await page.locator('#locale').click();
    await page.locator('#fit').click();
    const initial = await page.locator('#stage svg').getAttribute('viewBox');
    await page.locator('#plus').click();
    assert.notEqual(await page.locator('#stage svg').getAttribute('viewBox'), initial);
    const beforePan = await page.locator('#stage svg').getAttribute('viewBox');
    await page.mouse.move(500, 450); await page.mouse.down();
    await page.mouse.move(560, 470); await page.mouse.up();
    assert.notEqual(await page.locator('#stage svg').getAttribute('viewBox'), beforePan);
    await page.locator('#fit').click();
    assert.equal(await page.locator('#stage svg').getAttribute('viewBox'), initial);
    // Exercise actual city-marker hit testing, separate from search and buttons.
    await page.locator('.city[data-area="40400094"]').click();
    assert.ok((await page.locator('#detail').innerText()).includes('VeD #1'));
    await page.locator('#search').fill('missing-city');
    await page.locator('#search').press('Enter');
    assert.ok((await page.locator('#error').innerText()).includes('No matching city'));
    assert.deepEqual(errors, []);
    console.log('PASS: PNGs rendered; 110 cities/regions, 36 claimed regions, no contested, EN/RU, search, filtering, zoom, pan and city clicks.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
