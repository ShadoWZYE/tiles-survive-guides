'use strict';
const {chromium}=require(process.env.PLANNER_PLAYWRIGHT||'playwright'),{pathToFileURL}=require('node:url'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.PLANNER_BROWSER});
 try{
  const page=await browser.newPage({viewport:{width:1920,height:1080}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(pathToFileURL(path.resolve(__dirname,'../../outputs/Tiles-Survive-Hero-Planner-Offline.html')).href);
  await page.locator('.hero-card[data-slug="rosie"]').click();await page.locator('[data-tab="talents"]').click();
  for(const [branch,total,levels] of [['163600001',39,[3,3,3]],['163600002',28,[3,2,3]],['163600003',26,[3,3,3]]]){
   await page.locator(`[data-talent-points="${branch}"]`).fill(String(total));
   for(let i=0;i<levels.length;i++){const key=branch+':'+(i+1);await page.locator(`[data-talent-node="${key}"]`).click();await page.locator(`[data-talent="${key}"] select`).selectOption(String(levels[i]));}
  }
  await page.locator('#save-talents').click();
  const mountain=page.locator('[data-talent-rec="163600001:4"]'),rover=page.locator('[data-talent-rec="163600002:2"]'),sky=page.locator('[data-talent-rec="163600003:4"]');
  assert.equal(await mountain.getAttribute('data-guidance-kind'),'progression');assert.equal(await sky.getAttribute('data-guidance-kind'),'progression');assert.equal(await rover.getAttribute('data-guidance-kind'),'save');
  assert.match(await mountain.innerText(),/Troop Attack Bonus \+0.5%/);assert.match(await rover.innerText(),/Save 2 more points for Armor Boost Lv 3.*costs 4, available 2.*Unlocks Firepower Burst/);
  assert.equal(await page.locator('.talent-node.is-next').count(),2);assert.equal(await page.locator('[data-talent-node="163600002:2"] .talent-next').innerText(),'SAVE +2');assert.doesNotMatch(await mountain.innerText(),/\+0[.,]00.*score/);
  await sky.click();assert.equal(await page.locator('[data-talent="163600003:4"]').isVisible(),true);
  if(process.env.PLANNER_SCREENSHOT_DIR)await page.screenshot({path:path.join(process.env.PLANNER_SCREENSHOT_DIR,'browser-talent-progression.png')});
  await page.locator('[data-talent="163600003:4"] [data-talent-quick="1"]').click();assert.equal(await page.locator('[data-talent-rec="163600003:4"]').getAttribute('data-guidance-kind'),'save');assert.match(await page.locator('[data-talent-rec="163600003:4"]').innerText(),/Save 3 more points.*Firepower Burst Lv 2/);
  await page.locator('[data-talent-points="163600002"]').fill('30');await page.locator('[data-talent-points="163600002"]').press('Tab');assert.equal(await rover.getAttribute('data-guidance-kind'),'scored');assert.equal(await page.locator('[data-talent-node="163600002:2"] .talent-next').innerText(),'NEXT');assert.deepEqual(errors,[]);
  console.log('PASS reported 39/28/26-point case: affordable troop progression, named saving target and shortfall, unlock reason, guidance navigation and updates after spending/earning.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
