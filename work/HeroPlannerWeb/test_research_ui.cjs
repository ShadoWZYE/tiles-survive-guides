"use strict";
const {chromium}=require(process.env.PLANNER_PLAYWRIGHT||"playwright");
const {pathToFileURL}=require("node:url"),path=require("node:path"),assert=require("node:assert/strict");
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.PLANNER_BROWSER?{executablePath:process.env.PLANNER_BROWSER}:{})});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(pathToFileURL(path.resolve(__dirname,'../../outputs/Tiles-Survive-Hero-Planner-Offline.html')).href);
  await page.locator('#army-context').click();await page.locator('#setup-enabled').check();await page.locator('#setup-scene').selectOption('pve');await page.locator('[data-setup-tab="research"]').click();
  assert.equal(await page.locator('#roster-pane').isVisible(),false);assert.equal(await page.locator('#research-tree').inputValue(),'4300006');
  assert.ok(await page.locator('.research-card img').evaluateAll(es=>es.length>0&&es.every(e=>e.complete&&e.naturalWidth>0)));
  await page.locator('#research-tree').selectOption('4300002');await page.locator('#research-search').fill('research_group_troop_attack_percent_1');
  const card=page.locator('[data-research="research_group_troop_attack_percent_1"]');
  await card.locator('select').selectOption('2');assert.match(await card.innerText(),/ATK \+13/);assert.match(await page.locator('#research-progress').innerText(),/1 unsaved edits/);
  await page.locator('[data-tab="behemoths"]').click();await page.locator('[data-tab="research"]').click();
  assert.equal(await card.locator('select').inputValue(),'2');await page.locator('#save-research').click();
  await page.reload();await page.locator('[data-tab="research"]').click();await page.locator('#research-tree').selectOption('4300002');await page.locator('#research-search').fill('research_group_troop_attack_percent_1');
  assert.equal(await card.locator('select').inputValue(),'2');
  await card.locator('[data-step="1"]').click();assert.equal(await card.locator('select').inputValue(),'3');await page.locator('#discard-research').click();assert.equal(await card.locator('select').inputValue(),'2');
  await card.locator('select').selectOption('0');await page.locator('#save-research').click();assert.equal(await card.locator('select').inputValue(),'0');
  const saved=await page.evaluate(()=>JSON.parse(localStorage.getItem('tiles-survive-hero-planner-profile-v1')));assert.equal(saved.armyContext.enabled,true);assert.equal(saved.armyContext.scene,'pve');assert.equal(saved.armyContext.research.research_group_troop_attack_percent_1,undefined);
  await page.locator('#research-search').fill('');await page.locator('#research-tree').selectOption('4300006');
  if(process.env.PLANNER_SCREENSHOT_DIR)await page.screenshot({path:path.join(process.env.PLANNER_SCREENSHOT_DIR,'research-desktop.png')});
  await page.locator('#army-context').click();if(process.env.PLANNER_SCREENSHOT_DIR)await page.screenshot({path:path.join(process.env.PLANNER_SCREENSHOT_DIR,'army-setup.png')});await page.locator('#setup-close').click();
  await page.setViewportSize({width:390,height:844});const size=await page.evaluate(()=>({w:innerWidth,s:document.documentElement.scrollWidth}));assert.ok(size.s<=size.w+2);
  if(process.env.PLANNER_SCREENSHOT_DIR)await page.screenshot({path:path.join(process.env.PLANNER_SCREENSHOT_DIR,'research-mobile.png'),fullPage:true});
  await page.locator('#research-recorded').check();assert.match(await page.locator('#research-cards').innerText(),/No matching research/);
  assert.deepEqual(errors,[]);console.log('PASS Research icons, branches, previews, draft retention, save/discard/removal, persistence, Army Setup and mobile layout.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
