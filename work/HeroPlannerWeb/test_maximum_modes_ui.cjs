'use strict';
const {chromium}=require(process.env.PLANNER_PLAYWRIGHT||'playwright');
const {pathToFileURL}=require('node:url'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.PLANNER_BROWSER?{executablePath:process.env.PLANNER_BROWSER}:{})});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(pathToFileURL(path.resolve(__dirname,'../../outputs/Tiles-Survive-Hero-Planner-Offline.html')).href);
  const basis=page.locator('#comparison-basis');
  assert.match(await basis.innerText(),/Equal builds · max T5/);assert.match(await basis.innerText(),/Max heroes · no gear/);
  const expected=await page.evaluate(()=>{
   const u=window.__UPGRADE_DATA__,e=window.__ESTIMATE_DATA__;
   const number=v=>v.toFixed(2);
   return Object.fromEntries(['reference','flat'].map(b=>[b,number(window.EstimateModel.compare('rosie',null,u,e,b).score)]));
  });
  const card=page.locator('.hero-card[data-slug="rosie"] .index');
  assert.equal(await card.innerText(),'Est. '+expected.reference);
  assert.equal(await card.getAttribute('title'),'Equal max T5 build');
  await basis.selectOption('flat');
  assert.equal(await card.innerText(),'Est. '+expected.flat);
  assert.equal(await card.getAttribute('title'),'Max heroes, no gear');
  assert.notEqual(expected.reference,expected.flat);
  assert.ok(await page.locator('.hero-card .index').evaluateAll(es=>new Set(es.map(e=>e.textContent)).size>5),'Skill-aware no-gear scores collapsed into maximum-stat ties');
  const nikola=page.locator('.hero-card[data-slug="nikola"] .index'),sustained=await nikola.innerText();
  await page.locator('#battle-window').selectOption('10');
  assert.notEqual(await nikola.innerText(),sustained,'No-gear mode still ignored the skill window');
  await page.reload();assert.equal(await basis.inputValue(),'flat');
  await page.locator('[data-tab="skills"]').click();await page.locator('.hero-card[data-slug="rosie"]').click();
  await page.getByText('Estimate details',{exact:true}).click();
  assert.match(await page.locator('#detail-content').innerText(),/Maximum hero level, rank and capped skills/);
  if(process.env.PLANNER_SCREENSHOT_DIR)await page.screenshot({path:path.join(process.env.PLANNER_SCREENSHOT_DIR,'maximum-no-gear.png'),fullPage:true});
  assert.deepEqual(errors,[]);
  console.log('PASS maximum T5/no-gear build scores, skill separation, timing, labels, details and persistence.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
