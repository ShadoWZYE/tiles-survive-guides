const test=require('node:test'),assert=require('node:assert/strict'),path=require('node:path'),{execFileSync}=require('node:child_process');
const model=require('./estimate-model.js'),upgrades=require('../../outputs/hero-report/TilesSurvive-Upgrade-Data.json'),estimates=require('../../outputs/hero-report/Hero-Estimate-Model.json');

test('raw healing evidence distinguishes property owners, scales levels, and disappears when locked',()=>{
  const reference=model.evaluate('ken',null,upgrades,estimates);
  assert.ok(reference.rawHealingPotential.some(x=>x.formula.includes('x caster HP')));
  assert.deepEqual(model.evaluate('ken',{skills:{survivor_ken_skill_1:0}},upgrades,estimates).rawHealingPotential,[]);
  const first=model.evaluate('ken',{skills:{survivor_ken_skill_1:1}},upgrades,estimates);
  assert.equal(first.rawHealingPotential[0].formula,'0.15 x caster HP');
  assert.ok(model.evaluate('maddie',null,upgrades,estimates).rawHealingPotential.some(x=>x.formula.includes('x recipient HP')&&x.execution.includes('conditional')));
  const stripped=structuredClone(estimates);
  for(const h of Object.values(stripped.heroes))for(const s of h.skills)for(const row of s.levels)delete row.healing_budgets;
  for(const slug of Object.keys(estimates.heroes))for(const window of [0,10,20,30]){
    const before=model.evaluate(slug,null,upgrades,stripped,window),after=model.evaluate(slug,null,upgrades,estimates,window);
    for(const key of ['offense','durability','score','low','high'])assert.equal(before[key],after[key],'raw amounts must not silently change ranking weights');
  }
});

test('finish-triggered damage honors source completion, passive cooldown and update boundary',()=>{
  const t={cooldown_seconds:5,delay_seconds:0};
  assert.deepEqual(model.finishTriggers(t,[2,4,8,10],10),[2,8]);
  assert.deepEqual(model.finishTriggers({...t,delay_seconds:2},[2,8],10),[4]);
  assert.deepEqual(model.finishTriggers(t,[2,4,8],10,3),[4]);
  for(const window of [0,10,20,30]){
    const parentLocked={skills:{survivor_ray_skill_1:0}},bothLocked={skills:{survivor_ray_skill_1:0,survivor_ray_skill_2:0}};
    assert.ok(Math.abs(model.evaluate('ray',parentLocked,upgrades,estimates,window).score-model.evaluate('ray',bothLocked,upgrades,estimates,window).score)<1e-9);
    assert.deepEqual(model.evaluate('ray',parentLocked,upgrades,estimates,window).activeSkillIds,model.evaluate('ray',bothLocked,upgrades,estimates,window).activeSkillIds,'inactive dependency cannot supply squad synergy');
    const original=estimates.heroes.ray.skills.find(s=>s.slot===2),copy=structuredClone(estimates);
    const passive=copy.heroes.ray.skills.find(s=>s.slot===2);passive.levels.forEach(r=>{r.utility=0;});
    if(window===10)copy.heroes.ray.skills.find(s=>s.slot===1).base_pre_cooldown_ms=10000;
    const on=model.evaluate('ray',null,upgrades,copy,window),off=model.evaluate('ray',{skills:{survivor_ray_skill_2:0}},upgrades,copy,window);
    if(window===10)assert.equal(on.offense,off.offense,'active has not finished before opening 10s');
    if(window===20||window===30)assert.ok(on.offense>off.offense,'completed active enables delayed damage');
    assert.equal(original.finish_trigger.source_skill_id,'survivor_ray_skill_1');
  }
});
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
test('fair comparator ignores personal stars and ownership; recorded and flat modes are explicit',()=>{
  const saved={stage:upgrades.heroes.rosie.stages[0].id,level:1,skills:{},gear:[],owned:true};
  const ref=model.evaluate('rosie',null,upgrades,estimates),flat={offense:100,durability:100,score:100};
  assert.deepEqual(model.compare('rosie',saved,upgrades,estimates,'reference',flat),ref);
  assert.deepEqual(model.compare('rosie',{...saved,owned:false,level:110},upgrades,estimates,'reference',flat),ref);
  assert.ok(model.compare('rosie',saved,upgrades,estimates,'recorded',flat).score<ref.score);
  assert.equal(model.compare('rosie',saved,upgrades,estimates,'flat',flat).score,100);
});
test('native/browser estimates agree for all heroes and incomplete, reference and locked builds',()=>{
  const root=path.resolve(__dirname,'../..'),cases=JSON.parse(execFileSync('dotnet',['run','--no-build','--project',path.join(root,'work/HeroPlanner.Tests'),'--','unused','--estimates',path.join(root,'outputs/hero-report')],{encoding:'utf8',maxBuffer:1024*1024}));
  assert.equal(cases.length,464);
  for(const c of cases){const r=model.evaluate(c.slug,c.saved,upgrades,estimates,c.battleSeconds);assert.equal(r.basis,c.result.basis);
    assert.deepEqual(r.activeSkillIds,c.result.activeSkillIds,`${c.slug}: active skill parity`);
    assert.deepEqual(r.openingCastCounts,c.result.openingCastCounts,`${c.slug}: shared cast counts`);
    assert.deepEqual(r.rawHealingPotential,c.result.rawHealingPotential,`${c.slug}: raw healing evidence parity`);
    for(const k of ['offense','durability','score','low','high','healthContribution'])assert.ok(Math.abs(r[k]-c.result[k])<1e-8,`${c.slug}: ${k}`);
    for(const k of ['selfPercent','teamPercent','passiveContributions'])r[k].forEach((v,i)=>assert.ok(Math.abs(v-c.result[k][i])<1e-8));}
});

test('opening windows change timing while preserving locks, flat stats and defaults',()=>{
  const sustained=model.evaluate('nikola',null,upgrades,estimates);
  const opening=model.evaluate('nikola',null,upgrades,estimates,10);
  assert.ok(opening.selfPercent[0]<sustained.selfPercent[0]);
  assert.deepEqual(model.evaluate('nikola',null,upgrades,estimates,999),sustained);
  const flat={offense:100,durability:100,score:100};
  assert.deepEqual(model.compare('nikola',null,upgrades,estimates,'flat',flat,10),model.compare('nikola',null,upgrades,estimates,'flat',flat,0));
  const saved={skills:{survivor_nikola_skill_1:0}};
  assert.deepEqual(model.evaluate('nikola',saved,upgrades,estimates,10).selfPercent,[0,0,0]);
});

test('one casting slot respects readiness, priority, idle time and full completion',()=>{
  const skill=(id,slot,priority,delay,cast,cadence)=>({id,slot,priority,base_pre_cooldown_ms:delay*1000,cast_duration_at_unit_speed_seconds:cast,cadence_assumed_seconds:cadence,queue_eligible:true});
  const basic=skill('basic',0,0,0,2,2),active=skill('active',1,3,1,3,6);
  assert.deepEqual(model.openingSchedule([basic,active],8),{basic:[2,7],active:[5]});
  assert.deepEqual(model.openingSchedule([basic],8),{basic:[2,4,6,8]});
  assert.deepEqual(model.openingSchedule([skill('wait',1,3,5,2,4)],10),{wait:[7]});
  assert.equal(model.coveredTime([2,4,8],4,10),8,'overlapping buff time counted once');
  assert.equal(model.coveredTime([12],4,10),0,'buff after horizon cannot contribute');
});

test('locking an active skill frees basic attacks and removes its queue entry',()=>{
  for(const slug of Object.keys(estimates.heroes)){
    const active=estimates.heroes[slug].skills.find(s=>s.slot===1),basic=estimates.heroes[slug].skills.find(s=>s.slot===0);
    const all=model.evaluate(slug,null,upgrades,estimates,20),locked=model.evaluate(slug,{skills:{[active.id]:0}},upgrades,estimates,20);
    assert.ok((locked.openingCastCounts[basic.id]||0)>=(all.openingCastCounts[basic.id]||0),slug);
    assert.ok(!Object.hasOwn(locked.openingCastCounts,active.id),slug);
  }
});

test('in-flight immediate damage and known buff applications are credited at dispatch',()=>{
  const skill={id:'basic',slot:0,priority:0,base_pre_cooldown_ms:0,cast_duration_at_unit_speed_seconds:2,cadence_assumed_seconds:2,queue_eligible:true};
  assert.deepEqual(model.openingSchedule([skill],1),{basic:[]});
  assert.deepEqual(model.openingSchedule([skill],1,true),{basic:[2]});
  const budget={direct_coefficient:6,direct_events:[{offset_seconds:.5,coefficient:2},{offset_seconds:1.5,coefficient:4}],periodic_ticks:[]};
  assert.equal(model.openingDamage(budget,[2],2,1),2,'early hit survives a partial cast');
  assert.equal(model.openingDamage({...budget,direct_events:[]},[2],2,1),0,'unresolved impact stays completion-based');
  const periodic={direct_coefficient:0,direct_events:[],periodic_ticks:[{interval_ms:500,nominal_ticks:3,coefficient_per_tick:1,application_offset_seconds:.25}]};
  assert.equal(model.openingDamage(periodic,[2],2,1),1);
  const nikola=model.evaluate('nikola',null,upgrades,estimates,10);
  assert.ok(Math.abs(nikola.selfPercent[0]-.08)<1e-8,'ATK starts at the linked 0.5s dispatch');
});

test('active skill selection respects rank caps, explicit locks and missing defaults',()=>{
  for(const slug of Object.keys(estimates.heroes)){
    const data=upgrades.heroes[slug],lowest=data.stages[0];
    const capped=model.evaluate(slug,{stage:lowest.id},upgrades,estimates);
    for(const s of estimates.heroes[slug].skills)assert.equal(capped.activeSkillIds.includes(s.id),Math.min(s.reference_level,lowest.skill_caps[s.slot])>0);
    const locked=model.evaluate(slug,{skills:Object.fromEntries(data.skills.map(s=>[s.id,0]))},upgrades,estimates);
    assert.deepEqual(locked.activeSkillIds,[]);
    assert.ok(model.evaluate(slug,null,upgrades,estimates).activeSkillIds.length>0);
  }
});

test('recorded passive levels affect stats; explicit zero removes its benefit',()=>{
  const low=model.evaluate('layla',{skills:{survivor_layla_skill_2:1}},upgrades,estimates);
  const cap=estimates.heroes.layla.skills.find(s=>s.id==='survivor_layla_skill_2').reference_level;
  const high=model.evaluate('layla',{skills:{survivor_layla_skill_2:cap}},upgrades,estimates);
  const locked=model.evaluate('layla',{skills:{survivor_layla_skill_2:0}},upgrades,estimates);
  assert.ok(high.durability>low.durability&&low.durability>locked.durability);
  assert.equal(high.offense,low.offense);assert.deepEqual(locked.selfPercent,[0,0,0]);
  const tara=model.evaluate('tara',{skills:{survivor_tara_skill_2:0}},upgrades,estimates);
  assert.deepEqual(tara.teamPercent,[0,0,0]);
});
