const test=require('node:test'),assert=require('node:assert/strict'),R=require('./reconstruct-damage.cjs'),{potential}=require('./analyse-replay.cjs');
test('nonnegative fitting handles different units, singular columns and zero features',()=>{
 const r=R.nonnegativeFit([[1e6,1],[2e6,0],[0,2],[3e6,1]],[5,4,6,9]);
 assert.ok(Math.abs(r.coefficients[0]-2e-6)<1e-12);assert.ok(Math.abs(r.coefficients[1]-3)<1e-9);assert.ok(r.sse<1e-15);
 const duplicate=R.nonnegativeFit([[1,1],[2,2]],[2,4]);assert.ok(duplicate.sse<1e-15);assert.ok(duplicate.coefficients.every(v=>v>=0));
 assert.deepEqual(R.nonnegativeFit([[0],[0]],[1,2]).coefficients,[0]);assert.throws(()=>R.nonnegativeFit([[NaN]],[1]));
});
test('an excluded owner outcome cannot choose its own coefficient or defence-grid candidate',()=>{
 const rows=[1,2,3,4,5].map((v,i)=>({hero:String(i),observed:v*v+1,x:v}));
 const spec={id:'probe',parameter_count:2,labels:[],candidates:[{parameters:{shape:'linear'},features:r=>[r.x]},{parameters:{shape:'quadratic'},features:r=>[r.x*r.x]}]};
 const before=R.evaluateModel(rows,spec),changed=structuredClone(rows);changed[2].observed=100000;
 const after=R.evaluateModel(changed,spec);assert.equal(before.leave_one_owner_out.rows[2].predicted,after.leave_one_owner_out.rows[2].predicted);assert.deepEqual(before.leave_one_owner_out.rows[2].parameters,after.leave_one_owner_out.rows[2].parameters);
 assert.equal(after.leave_one_owner_out.rows[2].trained_on.includes('2'),false);
});
test('report display precision prevents claiming an uncertain damage ordering',()=>{
 const r=R.errors([{hero:'a',observed:9220000,predicted:1,display_quantum:10000},{hero:'b',observed:9230000,predicted:2,display_quantum:10000}]);assert.equal(r.rounding_separated_rank_pairs,0);
});
test('recorded reconstruction reconciles build power and exposes fitted error without modifying inputs',()=>{
 const root='../../outputs/hero-report/',o=require(root+'Replay-Observation-2026-11-07.json'),i=require(root+'Replay-Reconstruction-Inputs-2026-11-07.json'),u=require(root+'TilesSurvive-Upgrade-Data.json'),e=require(root+'Hero-Estimate-Model.json'),a=require(root+'Hero-Army-Context.json'),before=JSON.stringify([o,i,u,e,a]);
 const r=R.reconstruct(o,i,u,e,a);assert.equal(JSON.stringify([o,i,u,e,a]),before);assert.equal(r.build_power_check.reconstructed,6562465);assert.equal(r.independent_battles,1);assert.equal(r.independent_battle_accuracy,null);assert.equal(r.models.length,9);assert.equal(r.damage_taken_models.length,2);assert.ok(r.damage_taken_models[1].in_sample.max_owner_relative_error<.03);
 const baseline=r.models.find(m=>m.id==='planner_offense'),control=r.models.find(m=>m.id==='lifetime_only_control');assert.ok(baseline.in_sample.wape>.20);assert.ok(control.in_sample.max_owner_relative_error>.30,'a small mean fit must not hide a bad hero row');
 const exposure=r.models.find(m=>m.id==='attack_times_observed_lifetime');assert.equal(exposure.fitted_parameter_count,1);assert.ok(exposure.in_sample.wape<.17&&exposure.leave_one_owner_out.wape<.23&&exposure.in_sample.max_owner_relative_error<.29);assert.ok(exposure.leave_one_owner_out.wape<baseline.leave_one_owner_out.wape);
 for(const m of r.models){assert.equal(m.in_sample.rows.length,5);assert.equal(m.leave_one_owner_out.rows.length,5);assert.ok(m.fitted_parameters.coefficients.every(v=>v>=0));}
 const h=o.heroes.find(h=>h.planner_slug==='ray'),s=e.heroes.ray.skills.map(k=>({...k,row:k.levels.find(v=>v.level===h.skill_levels_by_slot[k.slot])})),budget=potential(s,30,21.5);
 assert.ok(Math.abs(Object.values(budget.perSkillCoefficient).reduce((x,y)=>x+y,0)-budget.coefficient)<1e-9);
 const bad=structuredClone(i);bad.candidate_stages.rosie='survivor_rosie_rank_1_0';assert.throws(()=>R.features(o,bad,u,e,a));
});
