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
  localStorage: {getItem: () => null}, FormationPriority: policy, UpgradeModel:require('./upgrade-model.js'), FactionModel:require('./faction-model.js'), FormationModel:require('./formation-model.js')});
context.__UPGRADE_DATA__=JSON.parse(fs.readFileSync(path.join(root,'outputs/hero-report/TilesSurvive-Upgrade-Data.json'),'utf8'));
context.window.__UPGRADE_DATA__=context.__UPGRADE_DATA__;
context.ArmyContextModel=require('./army-context-model.js');
context.ArmyRoster=require('./army-roster.js');
context.window.__ARMY_CONTEXT_DATA__=require('../../outputs/hero-report/Hero-Army-Context.json');
vm.runInContext(fs.readFileSync(path.join(__dirname,'upgrade-ui.js'),'utf8'),context);
// Use the production parser and recommendation functions without mounting the browser shell.
const source = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");
assert.ok(source.includes("wireShell(); renderAll(); registerWebMcp();"));
vm.runInContext(source.replace("wireShell(); renderAll(); registerWebMcp();",
  "globalThis.hooks={heroes,profile,sanitizeProfile,mechanicsFor,bestOwnedAndTargets,renderFormationGuide,starQueue,findTopSquads,clearOptimizerCache:()=>optimizerCache.clear()};"), context);
const {heroes, profile} = context.hooks;
heroes.forEach(h=>h.healthContribution=0); // This parser-only fixture does not run renderAll's estimate refresh.
const example = ["Rosie","Layla","Becca","Ray","Maddie"].map(name => heroes.find(h => h.name === name));
const names = (squad, mode) => policy.rank(squad, mode).map(x=>x.hero.name);

test("example priority depends on formation job, not composite hero score", () => {
  const carries=policy.carries(example).map(h=>h.name);
  assert.equal(names(example,"Balanced")[0],carries[0]);
  assert.equal(names(example,"Balanced")[1],"Rosie");
  assert.deepEqual(names(example,"Offense").slice(0,2),carries);
  assert.equal(names(example,"Survival")[0],"Rosie");
  assert.deepEqual(names(example,"PvE farming"), names(example,"Balanced"));
  assert.ok(example.find(h=>h.name==="Becca").mechanics.has("DEF reduction"));
});
test("order is stable, deduplicated and independent of selection order", () => {
  assert.deepEqual(names(example.slice().reverse()),names(example));
  assert.deepEqual(names([...example,...example]),names(example));
  assert.deepEqual(names([]),[]);
  const dave={...heroes.find(h=>h.name==="Dave"),offense_index:Math.max(...heroes.map(h=>h.offense_index))+1};
  assert.equal(names([dave,...example.slice(0,4)])[0],"Dave","A higher-offense midline damage hero must not be ignored for a ranged hero");
});
test("star targets alter only the star queue; unknown is not zero", () => {
  const progress = Object.fromEntries(example.map(h=>[h.asset_slug,{current:3,target:4}]));
  progress[example.find(h=>h.name==="Becca").asset_slug]={current:4,target:4};
  const plan=policy.starPlan(example,"Balanced",progress);
  assert.deepEqual(plan.filter(x=>x.status==="pending").map(x=>x.hero.name),names(example,"Balanced").filter(n=>n!=="Becca"));
  assert.equal(plan[0].status,"reached");
  assert.ok(policy.starPlan(example,"Balanced").every(x=>x.status==="unknown"));
  assert.equal(names(example)[0],policy.carries(example)[0].name);
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
test("formation investment view requires actual builds instead of imposing a role order", () => {
  profile.ownedHeroes=example.map(h=>h.asset_slug);profile.mode="Balanced";
  profile.heroProgress={};
  const guide=context.hooks.renderFormationGuide(example);
  assert.match(guide,/Data-driven next upgrades/);
  assert.match(guide,/Record these owned builds/);
  assert.match(guide,/build not recorded/);
  assert.doesNotMatch(guide,/Role-based guide, not upgrade ROI/);
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


test("PvE farming sorts known stamina saving before combat without increasing combat scores",()=>{
 const squad=example.map((h,i)=>({...h,asset_slug:'farm-'+i,name:'Farm '+i,staminaReduction:0,estimate:{comparable:true},offense_index:100,durability_index:100,composite_index:100}));
 const lucky={...squad[2],asset_slug:'farm-lucky',name:'Farm Lucky',staminaReduction:16,offense_index:1,durability_index:1,composite_index:1};
 profile.mode='PvE farming';
 const first=context.hooks.findTopSquads([...squad,lucky],1,true)[0];
 assert.ok(first.heroes.some(h=>h.asset_slug==='farm-lucky'));assert.equal(first.stamina,16);
 // Use a distinct cache key to represent the normal estimate-refresh invalidation.
 lucky.staminaReduction=0;lucky.asset_slug='farm-locked';
 const locked=context.hooks.findTopSquads([...squad,lucky],1,true)[0];
 assert.ok(!locked.heroes.some(h=>h.asset_slug==='farm-locked'));assert.ok(locked.score>first.score);
});


test('survival benchmark changes the selected five rather than only the displayed score',()=>{
 const oldBasis=profile.comparisonBasis,oldMode=profile.mode,oldFlag=profile.survivalBenchmark;
 const h=(slug,role,offense,durability,hp)=>({asset_slug:slug,name:slug,role,faction:'Mountain',skills:[],mechanics:new Set(),composite_index:.55*offense+.35*durability,offense_index:offense,durability_index:durability,healthContribution:0,estimate:{basis:'Recorded build',comparable:true,heroStats:[100,100,hp],selfPercent:[0,0,0],teamPercent:[0,0,0]}});
 const candidates=[h('core-a','Melee',100,100,1000),h('core-b','Melee',100,100,1000),h('core-c','Mid',100,100,1000),h('core-d','Range',100,100,1000),h('fragile','Range',250,10,10),h('sturdy','Range',100,100,1000)];
 context.SurvivalModel=require('./survival-model.js');context.window.__SURVIVAL_DATA__={pressure:1000,back_share:.3};
 try{profile.comparisonBasis='recorded';profile.mode='Balanced';profile.survivalBenchmark=false;
 const before=context.hooks.findTopSquads(candidates,1)[0];assert.ok(before.heroes.some(h=>h.asset_slug==='fragile'));
 profile.survivalBenchmark=true;const after=context.hooks.findTopSquads(candidates,1)[0];assert.ok(after.heroes.some(h=>h.asset_slug==='sturdy'));assert.ok(!after.heroes.some(h=>h.asset_slug==='fragile'));
 }finally{profile.comparisonBasis=oldBasis;profile.mode=oldMode;profile.survivalBenchmark=oldFlag;}
});


test('entire formation scores and every contribution use the actual 1000-point scale',()=>{
 const model=require('./estimate-model.js'),u=require('../../outputs/hero-report/TilesSurvive-Upgrade-Data.json'),e=require('../../outputs/hero-report/Hero-Estimate-Model.json');
 const prior={...e,score_scale:100},saved={mode:profile.mode,basis:profile.comparisonBasis,flag:profile.survivalBenchmark};
 const pool=data=>['rosie','freja','becca','maddie','ray','layla'].map(slug=>{const h=heroes.find(h=>h.asset_slug===slug),r=model.compare(slug,null,u,data,'reference');return {...h,estimate:r,offense_index:r.offense,durability_index:r.durability,composite_index:r.score,healthContribution:r.healthContribution};});
 try{profile.mode='Balanced';profile.comparisonBasis='reference';profile.survivalBenchmark=false;context.hooks.clearOptimizerCache();const before=context.hooks.findTopSquads(pool(prior),3);context.hooks.clearOptimizerCache();const after=context.hooks.findTopSquads(pool(e),3);
 for(let i=0;i<after.length;i++){assert.deepEqual(after[i].heroes.map(h=>h.asset_slug),before[i].heroes.map(h=>h.asset_slug));for(const key of ['score','synergy','faction','frontline','exposure'])assert.ok(Math.abs(after[i][key]-10*before[i][key])<1e-7,key);}
 }finally{profile.mode=saved.mode;profile.comparisonBasis=saved.basis;profile.survivalBenchmark=saved.flag;context.hooks.clearOptimizerCache();}
});
