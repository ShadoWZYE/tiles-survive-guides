"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const {execFileSync} = require("node:child_process");
const policy = require("./formation-priority.js");
const root = path.resolve(__dirname, "../..");
const dataPath = path.join(root, "outputs/hero-report/TilesSurvive-Hero-Data.json");
const context = vm.createContext({window: {__HERO_DATA__: JSON.parse(fs.readFileSync(dataPath, "utf8"))},
  localStorage: {getItem: () => null}, FormationPriority: policy});
// Use the production parser and recommendation functions without mounting the browser shell.
const source = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");
assert.ok(source.includes("wireShell(); renderAll(); registerWebMcp();"));
vm.runInContext(source.replace("wireShell(); renderAll(); registerWebMcp();",
  "globalThis.hooks={heroes,profile,sanitizeProfile,mechanicsFor,bestOwnedAndTargets,renderFormationGuide,starQueue};"), context);
const {heroes, profile} = context.hooks;
const example = ["Rosie","Layla","Becca","Ray","Maddie"].map(name => heroes.find(h => h.name === name));
const names = (squad, mode) => policy.rank(squad, mode).map(x=>x.hero.name);

test("example priority depends on formation job, not composite hero score", () => {
  assert.deepEqual(names(example,"Balanced"), ["Becca","Rosie","Ray","Layla","Maddie"]);
  assert.deepEqual(names(example,"Offense"), ["Becca","Ray","Rosie","Layla","Maddie"]);
  assert.deepEqual(names(example,"Survival"), ["Rosie","Layla","Becca","Ray","Maddie"]);
  assert.deepEqual(names(example,"PvE farming"), names(example,"Balanced"));
  assert.ok(example.find(h=>h.name==="Becca").mechanics.has("DEF reduction"));
});
test("order is stable, deduplicated and independent of selection order", () => {
  assert.deepEqual(names(example.slice().reverse()),names(example));
  assert.deepEqual(names([...example,...example]),names(example));
  assert.deepEqual(names([]),[]);
  const dave=heroes.find(h=>h.name==="Dave");
  assert.equal(names([dave,...example.slice(0,4)])[0],"Dave","A higher-offense midline damage hero must not be ignored for a ranged hero");
});
test("star targets alter only the star queue; unknown is not zero", () => {
  const progress = Object.fromEntries(example.map(h=>[h.asset_slug,{current:3,target:4}]));
  progress[example.find(h=>h.name==="Becca").asset_slug]={current:4,target:4};
  const plan=policy.starPlan(example,"Balanced",progress);
  assert.deepEqual(plan.filter(x=>x.status==="pending").map(x=>x.hero.name),["Rosie","Ray","Layla","Maddie"]);
  assert.equal(plan[0].status,"reached");
  assert.ok(policy.starPlan(example,"Balanced").every(x=>x.status==="unknown"));
  assert.deepEqual(names(example),["Becca","Rosie","Ray","Layla","Maddie"]);
});
test("old and malformed profiles sanitize safely; zero stars survives roundtrip", () => {
  const old=context.hooks.sanitizeProfile({ownedHeroes:example.map(h=>h.asset_slug)});
  assert.equal(Object.keys(old.heroProgress).length,0);
  const slug=example[0].asset_slug;
  const progress=policy.sanitizeProgress({[slug]:{current:0,target:5},bogus:{current:1,target:5}},heroes.map(h=>h.asset_slug));
  assert.deepEqual(JSON.parse(JSON.stringify(progress)),{[slug]:{current:0,target:5}});
  for(const value of [-1,100,3.5,"4",Infinity,NaN]) assert.equal(policy.cleanStars(value),null);
  assert.equal(policy.sanitizeProgress({[slug]:{current:-1,target:"5"}},[slug])[slug],undefined);
});
test("formation guide and owned-roster resource recommendation share the policy", () => {
  profile.ownedHeroes=example.map(h=>h.asset_slug);profile.mode="Balanced";
  profile.heroProgress={};
  const guide=context.hooks.renderFormationGuide(example);
  const resources=context.hooks.bestOwnedAndTargets().resources;
  assert.match(guide,/1\. Becca/);assert.match(guide,/2\. Rosie/);assert.match(guide,/3\. Ray/);
  assert.match(resources,/Becca → Rosie → Ray → Layla → Maddie/);
  assert.match(guide,/Star-upgrade queue/);assert.match(guide,/not upgrade ROI/);
});
test("desktop and browser investment rules agree across modes and edge cases", () => {
  const output=JSON.parse(execFileSync("dotnet",["run","--no-build","--project",path.join(root,"work/HeroPlanner.Tests"),"--",dataPath],{encoding:"utf8"}));
  // Match the source JSON order used by the desktop test, not the browser's roster sorting.
  const bySlug=new Map(heroes.map(h=>[h.asset_slug,h]));
  const sourceHeroes=JSON.parse(fs.readFileSync(dataPath,"utf8")).map(h=>bySlug.get(h.asset_slug));
  const cases={example,reversed:example.slice().reverse(),duplicates:[...example,...example],empty:[],
    frontOnly:sourceHeroes.filter(h=>h.role==="Melee").slice(0,5),noFront:sourceHeroes.filter(h=>h.role!=="Melee").slice(0,5),
    partial:example.slice(0,2),tied:sourceHeroes.filter(h=>h.offense_index===74.09).slice(0,5)};
  for(const [name,squad] of Object.entries(cases))for(const mode of ["Balanced","Offense","Survival","Pve"])
    assert.deepEqual(policy.rank(squad,mode==="Pve"?"PvE farming":mode).map(x=>({slug:x.hero.asset_slug,reason:x.reason})),output[`${name}/${mode}`]);
});
