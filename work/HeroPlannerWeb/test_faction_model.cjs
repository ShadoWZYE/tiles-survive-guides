const test=require('node:test'),assert=require('node:assert/strict'),path=require('node:path'),{execFileSync}=require('node:child_process');
const model=require('./faction-model.js');
const M='Mountain',W='Wasteland',S='Sky',O='Sea';
test('screenshot health tiers, including five matching heroes',()=>{
  for(const [factions,hp,pattern] of [
    [[M,W,S],0,'mixed'],[[M,M,W,S],.02,'2'],[[M,M,W,W,S],.04,'2+2'],
    [[M,M,M,W,S],.08,'3'],[[M,M,M,W,W],.12,'3+2'],[[M,M,M,M,W],.18,'4'],[[M,M,M,M,M],.25,'5']]){
    const e=model.compose(factions);assert.equal(e.healthBonus,hp);assert.equal(e.pattern,pattern);
  }
});
test('Mariners fill a single slot each, selecting the best valid composition',()=>{
  for(const [factions,hp,pattern] of [
    [[M,M,W,S,O],.08,'3'], // One wildcard cannot simultaneously create 3+2.
    [[M,M,W,W,O],.12,'3+2'],[[M,M,M,W,O],.18,'4'],[[M,M,M,O,O],.25,'5'],
    [[O,O,O,O,O],.25,'5'],[[M,W,S,O,O],.08,'3']]){
    const e=model.compose(factions);assert.equal(e.healthBonus,hp);assert.equal(e.pattern,pattern);
    assert.deepEqual(model.compose([...factions].reverse()),e);
  }
});
test('counter direction, neutral Mariners and unknown enemies',()=>{
  assert.ok(model.counters(W,M));assert.ok(model.counters(M,S));assert.ok(model.counters(S,W));
  for(const f of [M,W,S,O,'Unknown']){assert.equal(model.counters(O,f),false);assert.equal(model.counters(f,O),false);assert.equal(model.counters(f,'Unknown'),false);assert.equal(model.counters(f,f),false);}
});
test('health changes only the HP contribution; counter damage stays conditional',()=>{
  const squad=[M,M,W,W,S].map(faction=>({faction,offense_index:100,healthContribution:80}));
  assert.ok(Math.abs(model.scoreBonus(squad,'Balanced')-.35*80*.04)<1e-10);
  assert.equal(model.scoreBonus(squad,'Offense',true),0);
  assert.ok(Math.abs(model.scoreBonus(squad,'Survival',true)-80*.04)<1e-10);
  assert.ok(model.scoreBonus(squad,'Offense',false,M)>model.scoreBonus(squad,'Offense',false,'Unknown'));
  const changed=squad.map(h=>({...h,offense_index:1000}));
  assert.equal(model.scoreBonus(changed,'Survival',true),model.scoreBonus(squad,'Survival',true));
});
test('native/browser parity over every five-slot faction combination, mode, basis and target',()=>{
  const root=path.resolve(__dirname,'../..');
  const cases=JSON.parse(execFileSync('dotnet',['run','--no-build','--project',path.join(root,'work/HeroPlanner.Tests'),'--','--factions'],{encoding:'utf8',maxBuffer:4*1024*1024}));
  assert.equal(cases.length,1024);
  for(const c of cases){
    const {summary,...effect}=c.effect;assert.deepEqual(model.compose(c.factions),effect);
    assert.equal(model.summary(effect),summary);
    const heroes=c.factions.map((faction,i)=>({faction,healthContribution:80+i,offense_index:100+i}));let n=0;
    for(const flat of [false,true])for(const mode of ['Balanced','Offense','Survival','PvE farming'])for(const enemy of ['Unknown',M,W,S,O])
      assert.ok(Math.abs(model.scoreBonus(heroes,mode,flat,enemy)-c.scores[n++])<1e-10,`${c.factions}/${mode}/${enemy}`);
  }
});
