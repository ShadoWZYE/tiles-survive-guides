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
    if(process.env.PLANNER_SCREENSHOT_DIR) await page.screenshot({path:path.join(process.env.PLANNER_SCREENSHOT_DIR,"roster.png")});
    await page.locator('[data-tab="squad"]').click();
    for(const slug of slugs) await page.locator(`.hero-card[data-slug="${slug}"]`).click();
    const priorities=page.locator('.guide-card.resource li strong');
    assert.deepEqual(await priorities.allTextContents(),["1. Becca","2. Rosie","3. Ray","4. Layla","5. Maddie"]);
    const starCard=page.locator('.guide-card').filter({has:page.locator('h3',{hasText:'Star-upgrade queue'})});
    assert.match(await starCard.innerText(),/Planned order: Rosie 3★ → 4★; Ray/);
    assert.match(await starCard.innerText(),/Target reached: Becca/);
    await page.locator('#formation-mode').selectOption("Survival");
    assert.deepEqual(await priorities.allTextContents(),["1. Rosie","2. Layla","3. Becca","4. Ray","5. Maddie"]);
    await page.locator('#formation-mode').selectOption("Balanced");
    if(process.env.PLANNER_SCREENSHOT_DIR) await page.screenshot({path:path.join(process.env.PLANNER_SCREENSHOT_DIR,"formation.png")});
    await page.setViewportSize({width:390,height:844});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),"Mobile page overflows horizontally");
    await page.locator('[data-tab="roster"]').click();
    assert.ok(await page.locator('#current-stars').isVisible());
    if(process.env.PLANNER_SCREENSHOT_DIR) await page.screenshot({path:path.join(process.env.PLANNER_SCREENSHOT_DIR,"mobile.png"),fullPage:true});
    assert.deepEqual(errors,[]);
    console.log("Browser smoke passed: role priority, mode switching, saved star targets, ownership preservation, mobile layout.");
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
