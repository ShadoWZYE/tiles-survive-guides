'use strict';
const {chromium}=require(process.env.PLANNER_PLAYWRIGHT||'playwright'),{pathToFileURL}=require('node:url'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.PLANNER_BROWSER});try{
 const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(pathToFileURL(path.resolve(__dirname,'../../outputs/Tiles-Survive-Hero-Planner-Offline.html')).href);
 assert.equal(await page.locator('[data-army]').count(),5);
 await page.locator('.hero-card[data-slug="rosie"]').click();await page.locator('#mode').selectOption('Survival');
 await page.getByRole('button',{name:'Army 2',exact:true}).click();
 assert.equal(await page.locator('.squad-slots .slot:not(.empty)').count(),0);assert.equal(await page.locator('.hero-card[data-slug="rosie"]').isDisabled(),true);
 assert.equal(await page.locator('#mode').inputValue(),'Balanced');
 await page.locator('[data-tab="stats"]').click();assert.equal(await page.locator('.hero-card[data-slug="rosie"]').isDisabled(),false);await page.locator('.hero-card[data-slug="rosie"]').click();assert.match(await page.locator('#detail-content').innerText(),/Rosie/);
 await page.locator('[data-tab="squad"]').click();assert.equal(await page.locator('.hero-card[data-slug="rosie"]').isDisabled(),true);
 await page.locator('.hero-card[data-slug="becca"]').click();await page.locator('#mode').selectOption('Offense');
 const selected=await page.evaluate(()=>JSON.parse(localStorage.getItem('tiles-survive-hero-planner-profile-v1')));assert.deepEqual(selected.armies[0].heroes,['rosie']);assert.deepEqual(selected.armies[1].heroes,['becca']);
 await page.reload();assert.equal(await page.locator('[data-army="1"]').getAttribute('aria-pressed'),'true');assert.equal(await page.locator('#mode').inputValue(),'Offense');
 assert.match(await page.locator('.squad-slots').innerText(),/Becca/);
 await page.getByRole('button',{name:'Army 1',exact:true}).click();assert.equal(await page.locator('#mode').inputValue(),'Survival');assert.match(await page.locator('.squad-slots').innerText(),/Rosie/);assert.equal(await page.locator('.hero-card[data-slug="becca"]').isDisabled(),true);
 await page.locator('#clear-squad').click();await page.getByRole('button',{name:'Army 2',exact:true}).click();assert.equal(await page.locator('.hero-card[data-slug="rosie"]').isDisabled(),false);
 await page.getByRole('button',{name:'Army 5',exact:true}).click();assert.equal(await page.locator('.hero-card[data-slug="becca"]').isDisabled(),true);
 await page.locator('.result').first().click();const profile=await page.evaluate(()=>JSON.parse(localStorage.getItem('tiles-survive-hero-planner-profile-v1')));assert.equal(profile.armies[4].heroes.length,5);assert.equal(profile.armies[4].heroes.includes('becca'),false);
 await page.reload();assert.equal(await page.locator('[data-army="4"]').getAttribute('aria-pressed'),'true');
 if(process.env.PLANNER_SCREENSHOT_DIR)await page.screenshot({path:path.join(process.env.PLANNER_SCREENSHOT_DIR,'five-armies-desktop.png')});
 await page.setViewportSize({width:430,height:932});assert.equal(await page.locator('[data-army]').count(),5);
 if(process.env.PLANNER_SCREENSHOT_DIR)await page.screenshot({path:path.join(process.env.PLANNER_SCREENSHOT_DIR,'five-armies-mobile.png')});
 await page.setViewportSize({width:1440,height:1080});
 for(let i=0;i<5;i++){await page.locator(`[data-army="${i}"]`).click();await page.locator('#clear-squad').click();}
 for(let i=0;i<5;i++){await page.locator(`[data-army="${i}"]`).click();await page.locator('.result').first().click();}
 const full=await page.evaluate(()=>JSON.parse(localStorage.getItem('tiles-survive-hero-planner-profile-v1')));assert.ok(full.armies.every(a=>a.heroes.length===5));assert.equal(new Set(full.armies.flatMap(a=>a.heroes)).size,25);
 await page.reload();assert.equal(await page.locator('[data-army="4"]').getAttribute('aria-pressed'),'true');assert.equal(await page.locator('.squad-slots .slot:not(.empty)').count(),5);
 assert.deepEqual(errors,[]);console.log('PASS five army switching, per-army modes, persistence, reservations, recommendations, clear, reload and mobile controls.');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1)});
