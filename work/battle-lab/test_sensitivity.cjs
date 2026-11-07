const test=require('node:test'),assert=require('node:assert/strict'),{analyse,ranking}=require('./score-sensitivity.cjs');
test('weight sensitivity is a separate diagnostic and does not mutate production inputs',()=>{
 const u=require('../../outputs/hero-report/TilesSurvive-Upgrade-Data.json'),e=require('../../outputs/hero-report/Hero-Estimate-Model.json'),before=JSON.stringify(e),r=analyse(u,e);
 assert.equal(JSON.stringify(e),before);assert.equal(r.weight_sensitivity.scenarios,9);assert.equal(r.timing_sensitivity.scenarios,4);assert.equal(r.ranking_accuracy,null);
 for(const s of r.weight_sensitivity.runs){assert.ok(Math.abs(s.weights.reduce((a,b)=>a+b,0)-1)<1e-10);assert.equal(new Set(s.top_five).size,5);}
 assert.equal(r.weight_sensitivity.heroes.length,29);
 const v=[{slug:'a',offense:100,durability:1,utility:0},{slug:'b',offense:1,durability:100,utility:0}];
 assert.equal(ranking(v,[1,0,0])[0].slug,'a');assert.equal(ranking(v,[0,1,0])[0].slug,'b');
});
