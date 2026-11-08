'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),{execFileSync}=require('node:child_process'),path=require('node:path');
const context=require('./army-context-model.js'),estimate=require('./estimate-model.js');
const data=require('../../outputs/hero-report/Hero-Army-Context.json'),upgrades=require('../../outputs/hero-report/TilesSurvive-Upgrade-Data.json'),model=require('../../outputs/hero-report/Hero-Estimate-Model.json');
const branches=Object.keys(data.faction_talents),key=(b,n)=>b+':'+n;
function build(nodes,points=80,b=branches[0]){return {enabled:true,factionTalents:Object.fromEntries(nodes.map((n,i)=>[key(b,i+1),n])),factionPoints:{[b]:points}};}
test('exact current talent catalog, cumulative rows, separate point pools and global scope',()=>{
 assert.equal(branches.length,3);for(const b of branches){assert.equal(Object.keys(data.faction_talents[b].nodes).length,8);const s=build([3,3,3],30,b);assert.equal(context.talentSpent(b,s,data),b===branches[2]?24:30);assert.deepEqual(context.resolve('rosie',s,data,'recorded').flat,[2100,420,140000]);assert.deepEqual(context.resolve('becca',s,data,'reference').flat,[2100,420,140000]);}
 const both={enabled:true,factionTalents:{[key(branches[0],1)]:1,[key(branches[1],1)]:1}};assert.deepEqual(context.resolve('maddie',both,data).flat,[1400,0,0]);
});
test('locked, unrecorded, over-budget, invalid and disabled talents grant nothing',()=>{
 for(const s of [{enabled:true,factionPoints:{[branches[0]]:39}},build([0,1]),build([3],9),build([4]),{...build([1]),enabled:false}])assert.deepEqual(context.resolve('rosie',s,data,'recorded').flat,[0,0,0]);
 assert.deepEqual(context.resolve('rosie',build([3,3,3]),data,'flat').flat,[0,0,0]);
 assert.equal(context.talentErrors(build([3,3,3,0,1]),data,branches[0]).length,1);
 assert.deepEqual(context.resolve('rosie',build([3,3,3,3,3,3,3,3]),data).flat,[2100,420,140000]); // no terminal placeholder bonus
});
test('affordable legal next upgrades rank marginal gain per point and never spend another faction currency',()=>{
 const score=s=>context.resolve('rosie',{...s,enabled:true},data,'recorded').flat.reduce((a,b)=>a+b,0);
 assert.deepEqual(context.talentRecommendations(build([],2),data,score),[]);
 assert.deepEqual(context.talentRecommendations({enabled:true},data,score),[]);
 const rows=context.talentRecommendations(build([3],16),data,score);assert.equal(rows.length,2);assert.equal(rows[0].key,key(branches[0],3));assert.equal(rows[0].gainPerPoint,15000);
 assert.equal(context.talentRecommendations(build([3],10),data,score).length,0);
 const troop=context.talentRecommendations(build([3,3,3],33),data,score);assert.equal(troop.length,1);assert.equal(troop[0].modeled,false);assert.equal(troop[0].gain,0);
});
test('purchased bonuses change the real scoring inputs consistently in My builds and Equal builds',()=>{
 for(const slug of Object.keys(model.heroes)){
  const max=estimate.maximumBuild(slug,model,true),flat=context.resolve(slug,build([3,3,3]),data,'recorded').flat;
  const a=estimate.compare(slug,max,upgrades,model,'recorded',null,0,flat),b=estimate.compare(slug,max,upgrades,model,'reference',null,0,flat);
  assert.equal(a.score,b.score);assert.ok(b.score>estimate.compare(slug,max,upgrades,model,'reference').score);
 }
});
test('native/browser validation, costs, effects and recommendations agree',()=>{
 const cases=[build([3,3,3],39),build([3,2,3],28,branches[1]),build([3,3,3],26,branches[2]),build([3,3,3,3,3,3,3],100),build([3,3,3,3,3,3,3,3],100),{enabled:true,factionPoints:Object.fromEntries(branches.map(b=>[b,39]))},{...build([1]),factionPoints:{[branches[0]]:-1}}, {...build([1]),factionPoints:{[branches[0]]:100001}},build([]),build([1]),build([3],10),build([3],16),build([0,1]),build([3,3,3],30),build([3,3,3,3,3,3,3,3]),build([4]),{enabled:true,factionTalents:{[key(branches[0],1)]:1,[key(branches[1],1)]:1}}];
 const native=JSON.parse(execFileSync('dotnet',['run','--project','work/HeroPlanner.Tests','-c','Release','--no-build','--','--faction-talents',path.resolve('outputs/hero-report')],{input:JSON.stringify(cases),encoding:'utf8'}));
 for(let i=0;i<cases.length;i++){const s=cases[i],n=native[i];assert.deepEqual(n.guidance,context.talentGuidance(s,data,[]));assert.deepEqual(n.clean,context.sanitize(s,data));assert.deepEqual(n.flat,context.resolve('rosie',s,data,'recorded').flat);assert.deepEqual(n.errors,branches.flatMap(b=>context.talentErrors(s,data,b)));assert.deepEqual(n.choices,context.talentRecommendations(s,data,c=>context.resolve('rosie',{enabled:true,factionPoints:c.factionPoints,factionTalents:c.factionTalents},data,'recorded').flat.reduce((a,b)=>a+b,0)));}
});

test('after the flat stats, name affordable troop progression and exact saving targets without inventing score',()=>{
 const s={enabled:true,factionPoints:{[branches[0]]:39,[branches[1]]:28,[branches[2]]:26},factionTalents:{...build([3,3,3]).factionTalents,...build([3,2,3],28,branches[1]).factionTalents,...build([3,3,3],26,branches[2]).factionTalents}};
 const guides=context.talentGuidance(s,data,[]);assert.deepEqual(guides.map(g=>g.kind),['progression','save','progression']);assert.equal(guides[0].choice.key,key(branches[0],4));assert.equal(guides[0].choice.cost,3);assert.equal(guides[2].choice.cost,2);assert.equal(guides[1].shortfall,2);assert.match(guides[1].message,/Armor Boost Lv 3.*costs 4, available 2.*Unlocks Firepower Burst/);assert.match(guides[0].message,/Troop Attack Bonus \+0.5%/);assert.equal(guides[0].choice.gain,0);
 assert.equal(context.talentGuidance(build([3,3,3,3,3,3,3],100),data,[])[0].kind,'review');assert.equal(context.talentGuidance(build([3,3,3,3,3,3,3,3],100),data,[])[0].kind,'complete');
});
