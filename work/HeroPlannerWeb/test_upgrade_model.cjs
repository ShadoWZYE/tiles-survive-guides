const test=require('node:test'),assert=require('node:assert/strict'),model=require('./upgrade-model.js');
const real=require('../../outputs/hero-report/TilesSurvive-Upgrade-Data.json');
const make=(name,gain,cost)=>({name,stages:[{id:'r0',rank:0,step:0,stats:[100,20,500],power:100,skill_caps:[],level_max:5},{id:'r1',rank:0,step:1,stats:[100+gain,20,500],power:100+gain,cost:{shared:cost},skill_caps:[],level_max:5,level_required:1}],levels:[{level:1,stats:[0,0,0],power:0,xp_total:0},{level:2,stats:[10,0,0],power:10,xp_total:100}],skills:[]});
const fixture={heroes:{a:make('A',20,10),b:make('B',30,100)},gear:{}};
const builds={a:{stage:'r0',level:1,skills:{},gear:[]},b:{stage:'r0',level:1,skills:{},gear:[]}};
test('cost and gain determine order, not hero identity or selection order',()=>{
  const ranked=d=>model.evaluate(['b','a'],builds,d,{goal:'attack'}).candidates.filter(c=>c.kind==='rank');
  assert.equal(ranked(fixture)[0].slug,'a');
  const changed=structuredClone(fixture);changed.heroes.b.stages[1].cost.shared=1;
  assert.equal(ranked(changed)[0].slug,'b');
  assert.equal(ranked(fixture)[0].gain,10);assert.equal(ranked(fixture)[0].efficiency,100);
});
test('unknown builds, gear and skill levels are never guessed',()=>{
  assert.ok(model.evaluate(['a','b'],{a:builds.a},fixture).missing.length);
  assert.equal(model.sanitizeBuild({...builds.a,gear:[{id:'bad',level:null}]},fixture.heroes.a),null);
  const h=real.heroes.rosie,b={stage:h.stages[0].id,level:1,skills:{},gear:null};
  const s=model.state('rosie',b,real,30);assert.equal(s.direct,null);assert.ok(s.missing.length);
});
test('affordability requires every balance and separates resource currencies',()=>{
  let r=model.evaluate(['a','b'],builds,fixture,{inventory:{shared:20},onlyAffordable:true});
  assert.deepEqual(r.candidates.map(c=>c.slug),['a']);
  r=model.evaluate(['a','b'],builds,fixture,{onlyAffordable:true});assert.equal(r.candidates.length,0);
  const changed=structuredClone(fixture);changed.heroes.b.stages[1].cost={other:1};
  const ranks=model.evaluate(['a','b'],builds,changed).candidates.filter(c=>c.kind==='rank');
  assert.notEqual(ranks[0].group,ranks[1].group);
});
test('rank unlocks change caps but do not grant free skill levels',()=>{
  const h=real.heroes.rosie,stage=h.stages[0],b={stage:stage.id,level:1,skills:Object.fromEntries(h.skills.map(s=>[s.id,stage.skill_caps[s.slot]>0?1:0])),gear:[]};
  const r=model.evaluate(['rosie'],{rosie:b},real,{goal:'attack'});
  const rank=r.candidates.find(c=>c.kind==='rank');assert.ok(rank);assert.ok(rank.delta[0]>0);
  const next=real.heroes.rosie.stages[1];
  const state=model.state('rosie',{...b,stage:next.id},real,30);assert.deepEqual(state.build.skills,b.skills);
  const invalid=structuredClone(b);invalid.skills[h.skills[0].id]=999;assert.match(model.state('rosie',invalid,real,30).error,/cap/);
});
test('all exported heroes have usable initial builds and bounded candidate returns',()=>{
  for(const [slug,h] of Object.entries(real.heroes)){
    const stage=h.stages[0],b={stage:stage.id,level:1,skills:Object.fromEntries(h.skills.map(s=>[s.id,stage.skill_caps[s.slot]>0?1:0])),gear:[]};
    const r=model.evaluate([slug],{[slug]:b},real);assert.deepEqual(r.missing,[],slug);
    assert.ok(r.candidates.length>0,slug);assert.ok(r.candidates.every(c=>c.gain===null||Number.isFinite(c.gain)),slug);
  }
});
test('direct-output estimates respond to skill level and retain unsupported utility as unknown',()=>{
  const d=structuredClone(fixture),h=d.heroes.a;
  h.stages.forEach(s=>s.skill_caps=[2,2]);
  h.skills=[{id:'hit',name:'Hit',slot:0,effect_type:1,damage_ratio:1,damage_params:[1,1],cooldown:1000,first_cast:0,conditional:false,levels:[{level:1,power:0,cost:{book:1},params:[]},{level:2,power:0,cost:{book:2},params:[]}]},
    {id:'utility',name:'Utility',slot:1,effect_type:3,damage_ratio:0,damage_params:[],cooldown:1000,first_cast:0,conditional:true,levels:[{level:1,power:0,cost:{book:1},params:[]},{level:2,power:0,cost:{book:2},params:[]}]}];
  const b={...builds.a,skills:{hit:1,utility:1}};
  assert.equal(model.state('a',b,d,30).direct,3000);
  const r=model.evaluate(['a'],{a:b},d,{goal:'direct'});
  const hit=r.candidates.find(c=>c.label.includes('Hit'));assert.equal(hit.gain,100);assert.equal(hit.efficiency,5000);
  const utility=r.candidates.find(c=>c.label.includes('Utility'));assert.equal(utility.gain,null);assert.ok(utility.unsupported);
  const unknown={...b,skills:{utility:1}};assert.equal(model.evaluate(['a'],{a:unknown},d,{goal:'direct'}).baseline.direct,null);
});
test('duplicate gear slots and level gates are blocked instead of counted twice',()=>{
  const d=structuredClone(fixture);d.gear={helmet:{slot:1,hero_level_required:1,levels:[{level:1,stats:[1,2,3],power:5}]},other:{slot:1,hero_level_required:1,levels:[{level:1,stats:[1,2,3],power:5}]}};
  assert.match(model.state('a',{...builds.a,gear:[{id:'helmet',level:1},{id:'other',level:1}]},d,30).error,/duplicate-slot/);
  d.gear.helmet.hero_level_required=2;
  assert.match(model.state('a',{...builds.a,gear:[{id:'helmet',level:1}]},d,30).error,/level-gated/);
});
