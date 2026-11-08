'use strict';
const {chromium}=require(process.env.PLANNER_PLAYWRIGHT||'playwright'),{pathToFileURL}=require('node:url'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const folder=fs.mkdtempSync(path.join(os.tmpdir(),'planner-restart-')),url=pathToFileURL(path.resolve(__dirname,'../../outputs/Tiles-Survive-Hero-Planner-Offline.html')).href;
 const options={headless:true,executablePath:process.env.PLANNER_BROWSER,viewport:{width:1440,height:1080}};
 let browser=await chromium.launchPersistentContext(folder,options);
 try{
  let page=await browser.newPage();await page.goto(url);
  await page.locator('#comparison-basis').selectOption('recorded');
  await page.locator('.hero-card[data-slug="rosie"]').click();
  await page.locator('.squad-data-notice summary').click();assert.match(await page.locator('.squad-data-notice').innerText(),/exact rank|hero level|gear/);
  await page.locator('[data-complete-build="rosie"]').click();assert.equal(await page.locator('#build-level').count(),1);
  await page.locator('[data-tab="squad"]').click();await page.locator('[data-army="1"]').click();await page.locator('.hero-card[data-slug="becca"]').click();await page.locator('#mode').selectOption('Survival');
  await browser.close();browser=await chromium.launchPersistentContext(folder,options);page=await browser.newPage();await page.goto(url);
  assert.equal(await page.locator('#comparison-basis').inputValue(),'recorded');assert.equal(await page.locator('[data-army="1"]').getAttribute('aria-pressed'),'true');assert.equal(await page.locator('#mode').inputValue(),'Survival');assert.match(await page.locator('.squad-slots').innerText(),/Becca/);assert.equal(await page.locator('.hero-card[data-slug="rosie"]').isDisabled(),true);
  assert.match(await page.locator('#hero-grid').innerText(),/below leader/);assert.doesNotMatch(await page.locator('#hero-grid').innerText(),/model gap/);
  assert.match(await page.locator('.hero-card[data-slug="rosie"] .build-defaults').innerText(),/Defaults/);
  if(process.env.PLANNER_SCREENSHOT_DIR)await page.screenshot({path:path.join(process.env.PLANNER_SCREENSHOT_DIR,'default-build-cards.png')});
  await page.locator('[data-tab="research"]').click();let labels=await page.locator('#research-tree').innerText();assert.doesNotMatch(labels,/legacy|Stalwart|Rover|Aeronaut|Ocean/i);
  await page.locator('#research-tree').selectOption('all');assert.equal(await page.locator('[data-research="research_group_troop_attack_percent_1"]').count(),0);
  await page.locator('#research-gated').check();labels=await page.locator('#research-tree').innerText();assert.match(labels,/Stalwart Power.*gated/);assert.doesNotMatch(labels,/legacy/i);
  await page.locator('[data-tab="behemoths"]').click();assert.equal(await page.locator('[data-beast-card]').count(),2);assert.doesNotMatch(await page.locator('#detail-content').innerText(),/griffon_eagle|Blazing Reaper/);
  await page.locator('#beast-source').selectOption('configured');const card=page.locator('[data-beast-card="caser"]');await card.locator('.beast-color').selectOption('3');await card.locator('.beast-slot').selectOption('4');await card.locator('.beast-step').selectOption('4');
  assert.match(await card.locator('.beast-star-preview span').nth(3).locator('img').nth(1).getAttribute('style'),/from 90deg/);
  if(process.env.PLANNER_SCREENSHOT_DIR)await page.screenshot({path:path.join(process.env.PLANNER_SCREENSHOT_DIR,'behemoth-corrected.png')});
  console.log('PASS real browser restart, comparison basis, saved armies, missing-data labels, score comparisons, hidden legacy/gated research, two live Behemoths and right-origin star fill.');
 }finally{await browser.close();fs.rmSync(folder,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exit(1)});
