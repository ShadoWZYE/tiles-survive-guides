const test=require('node:test'),assert=require('node:assert/strict'),{potential,analyse}=require('./analyse-replay.cjs');
const skill={id:'a',slot:0,priority:1,queue_eligible:true,base_pre_cooldown_ms:0,cadence_assumed_seconds:2,cast_duration_at_unit_speed_seconds:1,row:{level:1,cast_budget:{direct_coefficient:2,direct_events:[{offset_seconds:.2,coefficient:2}],periodic_ticks:[]}}};
test('death cuts off future casts and damage dispatch while preserving the observation denominator',()=>{
 assert.equal(potential([skill],10,0).coefficient,0);assert.equal(potential([skill],10,.1).coefficient,0);
 assert.equal(potential([skill],10,.5).coefficient,2);assert.equal(potential([skill],10,.5).perObservationSecond,.2);
 assert.equal(potential([skill],10,2).coefficient,2,'no new cast at death');assert.equal(potential([skill],10,10).coefficient,10);
 assert.throws(()=>potential([skill],10,11));assert.equal(potential([{...skill,row:{...skill.row,level:0}}],10,10).coefficient,0);
});
test('already dispatched periodic effects have separate cancel and persist scenarios',()=>{
 const s=structuredClone(skill);s.row.cast_budget.periodic_ticks=[{application_offset_seconds:.2,nominal_ticks:5,interval_ms:1000,coefficient_per_tick:1}];
 assert.equal(potential([s],10,.5,false).coefficient,2);assert.equal(potential([s],10,.5,true).coefficient,7);
 assert.equal(potential([s],10,.1,true).coefficient,0);
});
test('report/replay form one observation; independent power and countdown checks remain honest',()=>{
 const base='../../outputs/hero-report/',r=analyse(require(base+'Replay-Observation-2026-11-07.json'),require(base+'TilesSurvive-Upgrade-Data.json'),require(base+'Hero-Estimate-Model.json'));
 assert.equal(r.independent_battles,1);assert.ok(r.opening_countdowns.every(c=>c.consistent));assert.equal(r.skill_power.reconstructed,1165764);assert.equal(r.skill_power.consistent,true);
 assert.equal(r.gear_power.residual,169260);assert.equal(r.damage.total,37910000);assert.equal(r.accuracy_percentage,null);
 for(const h of r.heroes){assert.ok(h.lifetime_coefficient_potential[0]<=h.lifetime_coefficient_potential[1]);assert.ok(h.lifetime_coefficient_potential[1]<=h.full_30s_coefficient_potential+1e-8);}
});
