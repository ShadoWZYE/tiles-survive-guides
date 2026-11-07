const test=require('node:test'),assert=require('node:assert/strict'),R=require('./reconstruct-damage.cjs'),probe=require('./probe_survival_damage.cjs');
const folder='../../outputs/hero-report/',read=n=>require(folder+n),estimates=read('Hero-Estimate-Model.json');
const rows=R.features(read('Replay-Observation-2026-11-07.json'),read('Replay-Reconstruction-Inputs-2026-11-07.json'),read('TilesSurvive-Upgrade-Data.json'),estimates,read('Hero-Army-Context.json')).rows;
test('held owner labels cannot influence nested survival-damage prediction',()=>{
 for(const mode of ['coefficient','coefficient_plus_exposure'])for(let i=0;i<rows.length;i++){
  const train=rows.map((_,j)=>j).filter(j=>j!==i),before=probe.predict(rows,estimates,train,mode)[i];
  const changed=structuredClone(rows);changed[i].observed=1e12;changed[i].alive_seconds=1000;
  assert.equal(probe.predict(changed,estimates,train,mode)[i].predicted,before.predicted);
 }
});
