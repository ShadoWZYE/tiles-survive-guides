"use strict";
// Optional UI regression test: install Playwright and set PLANNER_BROWSER if needed.
const {chromium} = require(process.env.PLANNER_PLAYWRIGHT || "playwright");
const {pathToFileURL} = require("node:url");
const path = require("node:path");
const assert = require("node:assert/strict");
(async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.PLANNER_BROWSER ? {executablePath:process.env.PLANNER_BROWSER} : {})});
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1080}});
    const errors=[];page.on("pageerror",error=>errors.push(error.message));
    await page.goto(pathToFileURL(path.resolve(__dirname,"../../outputs/Tiles-Survive-Hero-Planner-Offline.html")).href);
    const names=["Rosie","Layla","Becca","Ray","Maddie"];
    const slugs=await page.evaluate(names=>names.map(n=>window.__HERO_DATA__.find(h=>h.name===n).asset_slug),names);
    await page.locator('[data-tab="roster"]').click();
    await page.locator('#none-owned').click();
    for(const slug of slugs) {
      await page.locator(`.hero-card[data-slug="${slug}"]`).click();
      await page.locator('#toggle-owned').click();
      await page.locator('#current-stars').fill("3");
      await page.locator('#target-stars').fill("4");
      await page.locator('#save-stars').click();
      const stage=await page.evaluate(slug=>window.__UPGRADE_DATA__.heroes[slug].stages[0],slug);
      await page.locator('#build-stage').selectOption(stage.id);
      await page.locator('#build-level').fill('1');
      const skills=await page.evaluate(slug=>window.__UPGRADE_DATA__.heroes[slug].skills,slug);
      for(let i=0;i<skills.length;i++)await page.locator('#build-skill-'+i).fill(stage.skill_caps[skills[i].slot]>0?'1':'0');
      await page.locator('#build-gear-mode').selectOption('recorded');
      await page.locator('#save-build').click();
    }
    const becca=slugs[2];
    await page.locator(`.hero-card[data-slug="${becca}"]`).click();
    assert.equal(await page.locator('#toggle-owned').innerText(),"Remove owned check","Selecting an owned hero must not unmark it");
    await page.locator('#current-stars').fill("4");await page.locator('#save-stars').click();
    await page.reload();
    await page.locator('[data-tab="roster"]').click();
    await page.locator(`.hero-card[data-slug="${becca}"]`).click();
    assert.equal(await page.locator('#current-stars').inputValue(),"4");
    assert.equal(await page.locator('#target-stars').inputValue(),"4");
    assert.equal(await page.locator('#toggle-owned').innerText(),"Remove owned check");
    assert.equal(await page.locator('#build-level').inputValue(),'1','Build must survive reload and star updates');
    if(process.env.PLANNER_SCREENSHOT_DIR) await page.screenshot({path:path.join(process.env.PLANNER_SCREENSHOT_DIR,"roster.png")});
    await page.locator('[data-tab="squad"]').click();
    for(const slug of slugs) await page.locator(`.hero-card[data-slug="${slug}"]`).click();
    const priorities=page.locator('.guide-card.resource');
    assert.match(await priorities.innerText(),/Data-driven next upgrades/i);
    assert.match(await priorities.innerText(),/gain per 100 resource units/);
    assert.doesNotMatch(await priorities.innerText(),/Record these builds/);
    await page.locator('#upgrade-goal').selectOption('attack');
    await page.locator('#save-upgrade-settings').click();
    assert.equal(await page.locator('#upgrade-goal').inputValue(),'attack');
    const before=await priorities.innerText();
    await page.locator('#formation-mode').selectOption("Survival");
    assert.equal(await priorities.innerText(),before,'Role mode must not override upgrade returns');
    await page.locator('#formation-mode').selectOption("Balanced");
    if(process.env.PLANNER_SCREENSHOT_DIR) await page.screenshot({path:path.join(process.env.PLANNER_SCREENSHOT_DIR,"formation.png")});
    await page.setViewportSize({width:390,height:844});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),"Mobile page overflows horizontally");
    await page.locator('[data-tab="roster"]').click();
    assert.ok(await page.locator('#current-stars').isVisible());
    if(process.env.PLANNER_SCREENSHOT_DIR) await page.screenshot({path:path.join(process.env.PLANNER_SCREENSHOT_DIR,"mobile.png"),fullPage:true});
    assert.deepEqual(errors,[]);
    console.log("Browser smoke passed: actual builds, data-driven returns, metric switching, saved profile, ownership preservation, mobile layout.");
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
