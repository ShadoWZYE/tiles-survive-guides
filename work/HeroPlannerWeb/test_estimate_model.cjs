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
  const ref=model.compare('rosie',null,upgrades,estimates,'reference'),flat={offense:100,durability:100,score:100};
  assert.deepEqual(model.compare('rosie',saved,upgrades,estimates,'reference',flat),ref);
  assert.deepEqual(model.compare('rosie',{...saved,owned:false,level:110},upgrades,estimates,'reference',flat),ref);
  assert.ok(model.compare('rosie',saved,upgrades,estimates,'recorded',flat).score<ref.score);
  const naked=model.compare('rosie',saved,upgrades,estimates,'flat',flat);
  assert.equal(naked.basis,'Max heroes, no gear');assert.ok(naked.score<ref.score);assert.ok(naked.activeSkillIds.length>0);
});
test('native/browser estimates agree for all heroes and incomplete, reference and locked builds',()=>{
  const root=path.resolve(__dirname,'../..'),cases=JSON.parse(execFileSync('dotnet',['run','--no-build','--project',path.join(root,'work/HeroPlanner.Tests'),'--','unused','--estimates',path.join(root,'outputs/hero-report')],{encoding:'utf8',maxBuffer:1024*1024}));
  assert.equal(cases.length,464);
  for(const c of cases){const r=model.evaluate(c.slug,c.saved,upgrades,estimates,c.battleSeconds);assert.equal(r.basis,c.result.basis);
    assert.deepEqual(r.activeSkillIds,c.result.activeSkillIds,`${c.slug}: active skill parity`);
    assert.deepEqual(r.openingCastCounts,c.result.openingCastCounts,`${c.slug}: shared cast counts`);
    assert.deepEqual(r.rawHealingPotential,c.result.rawHealingPotential,`${c.slug}: raw healing evidence parity`);
    for(const k of ['offense','durability','score','low','high','healthContribution'])assert.ok(Math.abs(r[k]-c.result[k])<1e-8,`${c.slug}: ${k}`);
    for(const k of ['selfPercent','teamPercent','passiveContributions','heroStats'])r[k].forEach((v,i)=>assert.ok(Math.abs(v-c.result[k][i])<1e-8));}
});

test('opening windows change timing while preserving locks, flat stats and defaults',()=>{
  const sustained=model.evaluate('nikola',null,upgrades,estimates);
  const opening=model.evaluate('nikola',null,upgrades,estimates,10);
  assert.ok(opening.selfPercent[0]<sustained.selfPercent[0]);
  assert.deepEqual(model.evaluate('nikola',null,upgrades,estimates,999),sustained);
  const flat={offense:100,durability:100,score:100};
  assert.notEqual(model.compare('nikola',null,upgrades,estimates,'flat',flat,10).score,model.compare('nikola',null,upgrades,estimates,'flat',flat,0).score);
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

test('My builds keeps partial heroes eligible without borrowing reference strength; native parity',()=>{
 const root=path.resolve(__dirname,'../..'),cases=JSON.parse(execFileSync('dotnet',['run','--no-build','--project',path.join(root,'work/HeroPlanner.Tests'),'--','--recorded-scores',path.join(root,'outputs/hero-report')],{encoding:'utf8',maxBuffer:4*1024*1024}));
 assert.equal(cases.length,145);for(const c of cases){const r=model.evaluate(c.slug,c.saved,upgrades,estimates,0,null,true);assert.equal(r.comparable,true);assert.equal(c.result.comparable,true);assert.deepEqual(r.missingFields||[],c.result.missingFields||[]);assert.ok(Math.abs(r.score-c.result.score)<1e-7);assert.equal(r.staminaReductionPercent,c.result.staminaReductionPercent);}
 const partial=model.compare('rosie',{level:1},upgrades,estimates,'recorded',{});assert.equal(partial.comparable,true);assert.ok(partial.missingFields.length);
});
test('all missing progress uses base rank, level one and no skill or gear bonuses without changing the saved build',()=>{
 for(const [slug,h] of Object.entries(upgrades.heroes)){
  const first=[...h.stages].sort((a,b)=>a.rank-b.rank||a.step-b.step)[0];
  const base={stage:first.id,level:1,gear:[],skills:Object.fromEntries(h.skills.map(s=>[s.id,0]))};
  const incomplete={skills:{},gear:null};const snapshot=JSON.stringify(incomplete);
  for(const seconds of [0,10,20,30]){
   const blank=model.evaluate(slug,incomplete,upgrades,estimates,seconds,null,true),explicit=model.evaluate(slug,base,upgrades,estimates,seconds,null,true);
   for(const field of ['offense','durability','score'])assert.equal(blank[field],explicit[field],`${slug} ${field}`);
   assert.deepEqual(blank.activeSkillIds,[]);assert.deepEqual(blank.teamPercent,[0,0,0]);
  }assert.equal(JSON.stringify(incomplete),snapshot);
 }
});
test('Freja remains eligible when Shadow Guard is unrecorded; missing or locked damaging skills add no benefit',()=>{
 const h=upgrades.heroes.freja,stage=h.stages.find(s=>s.id==='survivor_freja_rank_9_2'),skills=Object.fromEntries(h.skills.map(s=>[s.id,Math.min(10,stage.skill_caps[s.slot])])) ;delete skills.survivor_freja_skill_3;
 const saved={stage:stage.id,level:120,gear:[],skills},before=JSON.stringify(saved);
 const result=model.evaluate('freja',saved,upgrades,estimates,0,null,true);
 assert.equal(result.comparable,true);assert.ok(result.score>0);assert.ok(!result.activeSkillIds.includes('survivor_freja_skill_3'));assert.equal(JSON.stringify(saved),before);
 const empty=model.evaluate('freja',{...saved,skills:{}},upgrades,estimates,0,null,true),locked=model.evaluate('freja',{...saved,skills:Object.fromEntries(h.skills.map(s=>[s.id,0]))},upgrades,estimates,0,null,true);
 assert.equal(empty.score,locked.score);assert.ok(result.offense>empty.offense);
});
test('missing level is one even on a developed rank; invalid or rank-locked skills and gated gear add no bonus',()=>{
 const h=upgrades.heroes.freja,stage=h.stages.at(-1),saved={stage:stage.id,skills:{survivor_freja_attack:999},gear:[{id:'missing-item',level:99}]};
 const blank=model.evaluate('freja',saved,upgrades,estimates,0,null,true),explicit=model.evaluate('freja',{stage:stage.id,level:1,skills:{},gear:[]},upgrades,estimates,0,null,true);
 assert.equal(blank.score,explicit.score);assert.deepEqual(blank.activeSkillIds,[]);
 const first=h.stages[0],locked=Object.fromEntries(h.skills.map(s=>[s.id,first.skill_caps[s.slot]?0:10]));
 const ignored=model.evaluate('freja',{stage:first.id,level:1,skills:locked,gear:[]},upgrades,estimates,0,null,true),none=model.evaluate('freja',null,upgrades,estimates,0,null,true);
 assert.equal(ignored.score,none.score);
});
test('utility receives a single score channel and cannot inflate physical durability',()=>{
 const altered=structuredClone(estimates);for(const skill of altered.heroes.rosie.skills)for(const row of skill.levels)row.utility*=10;
 const a=model.evaluate('rosie',null,upgrades,estimates),b=model.evaluate('rosie',null,upgrades,altered);assert.equal(a.durability,b.durability);assert.equal(a.offense,b.offense);assert.ok(b.score>a.score);
});
test('Lucky farming savings use the selected skill level; missing and locked Wild Hunt give zero',()=>{
 const h=upgrades.heroes.lucky,stage=h.stages.at(-1),saved={stage:stage.id,level:120,gear:[],skills:{survivor_lucky_skill_2:11}};
 const result=model.evaluate('lucky',saved,upgrades,estimates,0,null,true);
 assert.ok(Math.abs(result.staminaReductionPercent-13)<1e-9);
 for(const skills of [{},{survivor_lucky_skill_2:0}])assert.equal(model.evaluate('lucky',{...saved,skills},upgrades,estimates,0,null,true).staminaReductionPercent,0);
});


test('maximum modes use max level, rank, skills and standard T5 gear with native parity',()=>{
 const root=path.resolve(__dirname,'../..'),cases=JSON.parse(execFileSync('dotnet',['run','--no-build','--project',path.join(root,'work/HeroPlanner.Tests'),'--','--max-comparisons',path.join(root,'outputs/hero-report')],{encoding:'utf8',maxBuffer:4*1024*1024}));
 assert.equal(cases.length,464);
 for(const c of cases){
  const build=model.maximumBuild(c.slug,estimates,c.basis!=='flat'),hero=upgrades.heroes[c.slug],stage=[...hero.stages].sort((a,b)=>b.rank-a.rank||b.step-a.step)[0];
  assert.deepEqual(build,c.build);assert.equal(build.stage,stage.id);assert.equal(build.level,Math.max(...hero.levels.filter(r=>r.level<=stage.level_max).map(r=>r.level)));
  for(const s of hero.skills)assert.equal(build.skills[s.id],Math.min(stage.skill_caps[s.slot],Math.max(...s.levels.map(r=>r.level))));
  if(c.basis==='flat')assert.deepEqual(build.gear,[]);else{assert.equal(build.gear.length,3);for(const g of build.gear){assert.equal(upgrades.gear[g.id].quality,5);assert.equal(g.level,Math.max(...upgrades.gear[g.id].levels.map(r=>r.level)));}}
  const result=model.compare(c.slug,{level:1},upgrades,estimates,c.basis,null,c.seconds,c.context);assert.equal(result.basis,c.result.basis);
  for(const k of ['score','offense','durability','staminaReductionPercent'])assert.ok(Math.abs(result[k]-c.result[k])<1e-7);
  if(c.basis==='flat')assert.equal(result.score,model.compare(c.slug,null,upgrades,estimates,'flat',null,c.seconds,[0,0,0]).score);
 }
});

test('recorded fourth skills add their verified flat stats once, before permanent percentages',()=>{
 const upgrade=require('./upgrade-model.js');
 for(const [slug,expected] of [['freja',[5378,1075,358560]],['maddie',[6480,1296,432000]]]){
  const h=upgrades.heroes[slug],s=h.skills.find(s=>s.slot===3),stage=h.stages.at(-1);
  assert.deepEqual(s.levels.find(r=>r.level===1).flat_stats,expected);
  const base={stage:stage.id,level:120,gear:[],skills:Object.fromEntries(h.skills.map(s=>[s.id,0]))},on=structuredClone(base);on.skills[s.id]=1;
  const before=upgrade.state(slug,base,upgrades,30),after=upgrade.state(slug,on,upgrades,30);
  assert.deepEqual(after.stats.map((v,i)=>v-before.stats[i]),expected);
  assert.equal(after.power-before.power,s.levels.find(r=>r.level===1).power,'power already includes skill power');
  const a=model.evaluate(slug,base,upgrades,estimates,0,null,true),b=model.evaluate(slug,on,upgrades,estimates,0,null,true);
  assert.ok(Math.abs(b.offense-a.offense-1000*expected[0]/estimates.scales[0])<1e-8);
  assert.ok(Math.abs(b.durability-a.durability-1000*(.7*expected[2]+30*expected[1])/estimates.scales[1])<1e-8);
  const unknown=structuredClone(on);delete unknown.skills[s.id];
  assert.equal(model.evaluate(slug,unknown,upgrades,estimates,0,null,true).score,a.score);
  const low={...on,stage:h.stages[0].id,level:1};assert.equal(model.evaluate(slug,low,upgrades,estimates,0,null,true).activeSkillIds.includes(s.id),false);
 }
});


test('1000-point normalization changes actual score components and preserves physical stats and percentage effects',()=>{
 assert.equal(estimates.score_scale,1000);
 const legacy={...estimates,score_scale:100};
 for(const slug of Object.keys(estimates.heroes))for(const basis of ['reference','flat','recorded']){
  const build={level:1,skills:{}};
  const old=model.compare(slug,build,upgrades,legacy,basis),current=model.compare(slug,build,upgrades,estimates,basis);
  for(const key of ['offense','durability','score','low','high','healthContribution'])assert.ok(Math.abs(current[key]-10*old[key])<1e-8,slug+' '+key);
  for(let i=0;i<3;i++)assert.ok(Math.abs(current.passiveContributions[i]-10*old.passiveContributions[i])<1e-8);
  for(const key of ['heroStats','teamPercent','selfPercent','staminaReductionPercent'])assert.deepEqual(current[key],old[key]);
 }
});


test('comparison basis changes inputs only: identical max builds produce identical combat estimates',()=>{
 for(const slug of Object.keys(estimates.heroes))for(const seconds of [0,10,20,30]){
  const build=model.maximumBuild(slug,estimates,true),snapshot=JSON.stringify(build);
  const a=model.compare(slug,build,upgrades,estimates,'reference',null,seconds,[100,20,2000]);
  const b=model.compare(slug,build,upgrades,estimates,'recorded',null,seconds,[100,20,2000]);
  for(const key of ['offense','durability','score','low','high','healthContribution','passiveContributions','teamPercent','selfPercent','heroStats','activeSkillIds','openingCastCounts','rawHealingPotential','staminaReductionPercent'])assert.deepEqual(a[key],b[key],slug+' '+key);
  const naked=model.maximumBuild(slug,estimates,false),flat=model.compare(slug,null,upgrades,estimates,'flat',null,seconds),recorded=model.compare(slug,naked,upgrades,estimates,'recorded',null,seconds);
  for(const key of ['offense','durability','score','heroStats','activeSkillIds','openingCastCounts'])assert.deepEqual(flat[key],recorded[key],slug+' no-gear '+key);
  assert.equal(JSON.stringify(build),snapshot);
 }
});

test('recorded projectile bursts scale each linked effect and vanish when the skill is locked',()=>{
 for(const [slug,slot,count] of [['tony',0,6],['dave',1,3],['sarge',0,3],['eva',1,8]]){
  const skill=estimates.heroes[slug].skills.find(s=>s.slot===slot);assert.equal(Object.values(skill.direct_hit_counts).reduce((a,b)=>a+b,0),count);
  const on=model.compare(slug,null,upgrades,estimates,'reference'),build=model.maximumBuild(slug,estimates,true);build.skills[skill.id]=0;
  const off=model.compare(slug,build,upgrades,estimates,'recorded');assert.ok(off.offense<on.offense);assert.ok(!off.activeSkillIds.includes(skill.id));
  assert.deepEqual(skill.levels[1].cast_budget.direct_events,[],'Launch time was presented as an impact time');
 }
});
