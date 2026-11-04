"use strict";
const {chromium}=require(process.env.PLANNER_PLAYWRIGHT||"playwright");
const {pathToFileURL}=require("node:url"),path=require("node:path"),assert=require("node:assert/strict");
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.PLANNER_BROWSER?{executablePath:process.env.PLANNER_BROWSER}:{})});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(pathToFileURL(path.resolve(__dirname,'../../outputs/Tiles-Survive-Hero-Planner-Offline.html')).href);
  await page.locator('[data-tab="stats"]').click();await page.locator('.hero-card[data-slug="rosie"]').click();
  await page.locator('#hero-signature-level').selectOption('2');await page.locator('#hero-signature-enabled').check();await page.locator('#save-signature').click();
  assert.equal(await page.locator('#hero-signature-level').inputValue(),'2');
  assert.ok(await page.locator('.signature-card .context-icon').evaluate(e=>e.complete&&e.naturalWidth>0));
  assert.ok(await page.locator('.signature-card .context-skill-icon').evaluate(e=>e.complete&&e.naturalWidth>0));
  await page.locator('[data-tab="roster"]').click();assert.equal(await page.locator('#hero-signature-level').inputValue(),'2');
  await page.locator('[data-tab="behemoths"]').click();
  assert.equal(await page.locator('#roster-pane').isVisible(),false);
  await page.locator('#beast-source').selectOption('configured');
  await page.locator('[data-beast-tab="caser"][data-part="level"]').selectOption('2');
  await page.locator('[data-beast-tab="caser"][data-part="star"]').selectOption('1');
  assert.ok(await page.locator('#beast-manual-0').isDisabled());
  await page.locator('#save-behemoths').click();await page.reload();await page.locator('[data-tab="behemoths"]').click();
  assert.equal(await page.locator('#beast-source').inputValue(),'configured');
  assert.equal(await page.locator('[data-beast-tab="caser"][data-part="level"]').inputValue(),'2');
  assert.equal(await page.locator('[data-beast-tab="caser"][data-part="star"]').inputValue(),'1');
  assert.ok(await page.locator('.behemoth-icon').evaluateAll(es=>es.length>0&&es.every(e=>e.complete&&e.naturalWidth>0)));
  if(process.env.PLANNER_SCREENSHOT_DIR)await page.screenshot({path:path.join(process.env.PLANNER_SCREENSHOT_DIR,'behemoths-desktop.png')});
  await page.locator('[data-tab="stats"]').click();await page.locator('.hero-card[data-slug="rosie"]').click();
  assert.ok(await page.locator('#roster-pane').isVisible());assert.equal(await page.locator('#hero-signature-level').inputValue(),'2');
  await page.locator('.hero-card[data-slug="layla"]').click();assert.equal(await page.locator('#hero-signature-level').inputValue(),'0');
  await page.locator('#hero-signature-level').selectOption('1');await page.locator('#save-signature').click();
  await page.locator('.hero-card[data-slug="rosie"]').click();assert.equal(await page.locator('#hero-signature-level').inputValue(),'2');
  if(process.env.PLANNER_SCREENSHOT_DIR)await page.screenshot({path:path.join(process.env.PLANNER_SCREENSHOT_DIR,'signature-desktop.png')});
  await page.setViewportSize({width:390,height:844});
  for(const tab of ['stats','roster','behemoths']){
   await page.locator(`[data-tab="${tab}"]`).click();
   const size=await page.evaluate(()=>({w:innerWidth,scroll:document.documentElement.scrollWidth}));
   assert.ok(size.scroll<=size.w+2,`${tab} mobile overflow: ${JSON.stringify(size)}`);
  }
  if(process.env.PLANNER_SCREENSHOT_DIR)await page.screenshot({path:path.join(process.env.PLANNER_SCREENSHOT_DIR,'behemoths-mobile.png'),fullPage:true});
  assert.deepEqual(errors,[]);console.log('PASS hero-local Signature Gear and icons, separate Behemoth tab, source isolation, persistence, hero isolation and mobile layout.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
