const {test}=require('node:test'),assert=require('node:assert/strict'),path=require('node:path'),{execFileSync}=require('node:child_process');
const model=require('./formation-model.js');
function hero(id,role,d,o=100){return {asset_slug:id,name:id,role,durability_index:d,offense_index:o,healthContribution:0};}
test('a fragile second front hero cannot hide behind one strong tank',()=>{
  const weak=[hero('tank','Melee',180),hero('mid','Mid',20),...['a','b','c'].map(n=>hero(n,'Range',100))];
  const even=[hero('tank','Melee',100),hero('mid','Mid',100),...['a','b','c'].map(n=>hero(n,'Range',100))];
  assert.ok(model.evaluate(weak).adjustment<model.evaluate(even).adjustment);
  assert.equal(model.evaluate(even).adjustment,0);
  assert.ok(Math.abs(model.evaluate(weak,'Survival').adjustment)>Math.abs(model.evaluate(weak,'Offense').adjustment));
});
test('a durable mid can take the second front seat while ranged carries stay behind',()=>{
  const squad=[hero('weak','Melee',20),hero('strong','Melee',100),hero('mid','Mid',90),hero('carry','Range',200,180),hero('other','Range',100)];
  const before=JSON.stringify(squad),r=model.evaluate(squad);
  assert.deepEqual(r.heroes.slice(0,2).map(h=>h.asset_slug),['strong','mid']);
  assert.equal(r.heroes[2].asset_slug,'carry');assert.equal(JSON.stringify(squad),before);
  assert.deepEqual(model.evaluate([...squad].reverse()).heroes.map(h=>h.asset_slug),r.heroes.map(h=>h.asset_slug));
});
test('zero durability and incomplete or flat squads remain finite and unadjusted',()=>{
  const squad=['a','b','c','d','e'].map(n=>hero(n,'Range',0));
  assert.equal(model.evaluate(squad).adjustment,0);
  assert.equal(model.evaluate(squad.slice(0,4)).adjustment,0);
  assert.equal(model.evaluate(squad,'Balanced',true,.25).adjustment,0);
});
test('native/browser placement and fit agree across roles, zeros, flat stats and faction health',()=>{
  const cases=JSON.parse(execFileSync('dotnet',['run','--no-build','--project',path.resolve(__dirname,'../HeroPlanner.Tests'),'--','--formation-fit'],{encoding:'utf8',maxBuffer:16*1024*1024}));
  assert.equal(cases.length,1536);
  for(const c of cases){const r=model.evaluate(c.heroes.map(h=>({...h,asset_slug:h.asset_slug||h.assetSlug,durability_index:h.durability_index??h.durabilityIndex,offense_index:h.offense_index??h.offenseIndex})),c.mode,c.flat,c.health);
    assert.deepEqual(r.heroes.map(h=>h.asset_slug),c.order);
    assert.ok(Math.abs(r.adjustment-c.adjustment)<1e-9);assert.ok(Math.abs(r.frontDurability-c.frontDurability)<1e-9);
    assert.ok(Math.abs(model.passiveBonus(c.heroes,c.mode,c.flat)-c.passiveBonus)<1e-9);}
});

test('team buffs add only to other heroes, stack additively and vanish in flat mode',()=>{
  const provider={...hero('tara','Melee',100),estimate:{teamPercent:[0,.2,0],passiveContributions:[50,40,60]}};
  const ally={...hero('ally','Mid',100),estimate:{teamPercent:[0,0,0],passiveContributions:[50,40,60]}};
  assert.equal(model.passiveBonus([provider]),0);
  assert.ok(Math.abs(model.passiveBonus([provider,ally])-.35*8/2)<1e-10);
  const other={...provider,asset_slug:'tony'};
  assert.ok(Math.abs(model.passiveBonus([provider,other,ally])-.35*(8+8+16)/3)<1e-10);
  assert.equal(model.passiveBonus([provider,ally],'Balanced',true),0);
});
