const test=require('node:test'),assert=require('node:assert/strict'),path=require('node:path'),{execFileSync}=require('node:child_process');
const model=require('./estimate-model.js'),upgrades=require('../../outputs/hero-report/TilesSurvive-Upgrade-Data.json'),estimates=require('../../outputs/hero-report/Hero-Estimate-Model.json');
test('every hero gets a bounded reference estimate with no personal data; SSR are not all identical',()=>{
  assert.deepEqual(Object.keys(estimates.heroes).sort(),Object.keys(upgrades.heroes).sort());
  const scores=[];
  for(const slug of Object.keys(upgrades.heroes)){const r=model.evaluate(slug,null,upgrades,estimates);
    assert.equal(r.basis,'Reference build');assert.ok(r.low<=r.score&&r.high>=r.score);assert.ok(Number.isFinite(r.score)&&r.score>0);scores.push(r.score);}
  assert.ok(new Set(scores.map(n=>n.toFixed(3))).size>10);
});
test('recorded fields override defaults without mutating the build; unknowns remain assumed',()=>{
  const slug='rosie',ref=model.evaluate(slug,null,upgrades,estimates),saved={level:1};const snapshot=JSON.stringify(saved);
  const partial=model.evaluate(slug,saved,upgrades,estimates);assert.equal(partial.basis,'Recorded + assumed');assert.ok(partial.score<ref.score);assert.equal(JSON.stringify(saved),snapshot);
  assert.equal(model.evaluate(slug,{level:999},upgrades,estimates).basis,'Reference build');
});
test('native/browser estimates agree for all heroes and incomplete, reference and locked builds',()=>{
  const root=path.resolve(__dirname,'../..'),cases=JSON.parse(execFileSync('dotnet',['run','--no-build','--project',path.join(root,'work/HeroPlanner.Tests'),'--','unused','--estimates',path.join(root,'outputs/hero-report')],{encoding:'utf8',maxBuffer:1024*1024}));
  assert.equal(cases.length,116);
  for(const c of cases){const r=model.evaluate(c.slug,c.saved,upgrades,estimates);assert.equal(r.basis,c.result.basis);
    for(const k of ['offense','durability','score','low','high'])assert.ok(Math.abs(r[k]-c.result[k])<1e-8,`${c.slug}: ${k}`);}
});
