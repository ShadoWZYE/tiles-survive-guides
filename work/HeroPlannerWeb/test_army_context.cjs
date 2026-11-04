'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),{execFileSync}=require('node:child_process'),path=require('node:path');
const context=require('./army-context-model.js'),model=require('./estimate-model.js');
const data=require('../../outputs/hero-report/Hero-Army-Context.json'),upgrades=require('../../outputs/hero-report/TilesSurvive-Upgrade-Data.json'),estimates=require('../../outputs/hero-report/Hero-Estimate-Model.json');
test('exclusion, malformed profiles and comparison basis are explicit',()=>{
 assert.deepEqual(context.resolve('rosie',{signature:{rosie:1}},data).flat,[0,0,0]);
 assert.deepEqual(context.resolve('rosie',{enabled:true,signature:{rosie:1}},data,'reference').flat,[0,0,0]);
 assert.ok(context.resolve('rosie',{enabled:true,signature:{rosie:1}},data,'recorded').flat[0]>0);
 assert.deepEqual(context.resolve('rosie',{enabled:true,signature:{rosie:1},behemoth:[100,100,100]},data,'flat').flat,[0,0,0]);
 const clean=context.sanitize({enabled:true,research:{toString:1,bogus:1},signature:{rosie:999},behemoth:[-1,Infinity,'20']},data);
 assert.deepEqual(clean.research,{});assert.deepEqual(clean.signature,{});assert.deepEqual(clean.behemoth,[null,null,null]);
});
test('research applies current row once and respects recipient and encounter',()=>{
 const key='research_group_troop_attack_percent_1',row=data.research[key].levels.find(r=>r.level===2);
 const expected=row.effects.filter(e=>e.scene==='all'&&e.stat===0).reduce((s,e)=>s+e.value,0);
 assert.equal(context.resolve('rosie',{enabled:true,research:{[key]:2}},data).flat[0],expected);
 assert.equal(expected,13);
 for(const [key,node] of Object.entries(data.research))for(const row of node.levels.slice(0,1)){
  for(const [slug,hero] of Object.entries(data.heroes))for(const scene of ['all','pve','gve']){
   const expected=[0,0,0];for(const e of row.effects)if((e.scope==='all'||e.scope===hero.role||e.scope===hero.faction)&&(e.scene==='all'||e.scene===scene))expected[e.stat]+=e.value;
   assert.deepEqual(context.resolve(slug,{enabled:true,scene,research:{[key]:row.level}},data).flat,expected);
  }
 }
});
test('flat bonuses enter before passives and update faction/frontline contribution inputs',()=>{
 const base=model.evaluate('rosie',null,upgrades,estimates),atk=model.evaluate('rosie',null,upgrades,estimates,0,[3600,0,0]),hp=model.evaluate('rosie',null,upgrades,estimates,0,[0,0,240000]);
 assert.ok(atk.offense>base.offense);assert.equal(atk.durability,base.durability);
 assert.ok(hp.durability>base.durability);assert.ok(hp.healthContribution>base.healthContribution);assert.ok(hp.passiveContributions[2]>base.passiveContributions[2]);
 const huge=model.evaluate('rosie',null,upgrades,estimates,0,[1e8,0,0]);assert.ok(huge.score>atk.score);
 for(const slug of Object.keys(estimates.heroes))assert.deepEqual(model.evaluate(slug,null,upgrades,estimates),model.evaluate(slug,null,upgrades,estimates,0,[0,0,0]));
 assert.ok(context.resolve('rosie',{enabled:true,signature:{rosie:1}},data,'recorded').notes.some(n=>n.includes('linked skill excluded')));
});
test('native and browser context and adjusted estimates agree across all heroes',()=>{
 const root=path.resolve(__dirname,'../..');const cases=JSON.parse(execFileSync('dotnet',['run','--no-build','--project',path.join(root,'work/HeroPlanner.Tests'),'--','--army-context',path.join(root,'outputs/hero-report')],{encoding:'utf8',maxBuffer:8*1024*1024}));
 assert.equal(cases.length,696);
 for(const c of cases){const resolved=context.resolve(c.slug,c.settings,data,c.basis);assert.deepEqual(resolved,c.context);
  const result=model.evaluate(c.slug,null,upgrades,estimates,20,resolved.flat);
  for(const k of ['offense','durability','score','healthContribution'])assert.ok(Math.abs(result[k]-c.result[k])<1e-7,`${c.slug} ${k}`);
  result.passiveContributions.forEach((v,i)=>assert.ok(Math.abs(v-c.result.passiveContributions[i])<1e-7));
 }
});

test('configured Behemoth uses current level and exact star step, never the manual snapshot too',()=>{
 const raw={enabled:true,behemothSource:'configured',behemoth:[999,999,999],behemothBuilds:{caser:{level:1,star:1}}};
 assert.deepEqual(context.resolve('rosie',raw,data).flat,[1257,252,83784]);
 assert.deepEqual(context.resolve('rosie',{...raw,behemothSource:'manual'},data).flat,[999,999,999]);
 const current=data.behemoths.caser.levels.at(-1),expected=[0,0,0];for(const e of current.effects)expected[e.stat]+=e.value;
 assert.deepEqual(context.resolve('rosie',{...raw,behemothBuilds:{caser:{level:current.level,star:0}}},data).flat,expected);
 assert.deepEqual(context.sanitize({...raw,behemothBuilds:{caser:{level:99999,star:1},missing:{level:1,star:1}}},data).behemothBuilds,{caser:{level:0,star:1}});
});
