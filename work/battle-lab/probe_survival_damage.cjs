'use strict';
// Laboratory only. Every held owner's damage and lifetime are excluded from all fits.
const R=require('./reconstruct-damage.cjs'),S=require('./survival-reconstruction.cjs'),P=require('../HeroPlannerWeb/survival-model.js'),D=require('./analyse-replay.cjs');
function predict(rows,estimates,train,mode){
 const calibration=S.calibrate(rows,train);
 const times=P.project(rows.map(r=>r.known_flat_hp),calibration.pressure,calibration.back_share,30).aliveSeconds;
 const features=rows.map((r,i)=>{
  const skills=estimates.heroes[r.hero].skills.map(s=>({...s,row:s.levels.find(v=>v.level===r.build.skills[s.id])}));
  const damage=D.potential(skills,30,times[i]);
  return mode==='coefficient'?[r.attack*damage.coefficient]:[r.attack*damage.coefficient,times[i]];
 });
 const fitted=R.nonnegativeFit(train.map(i=>features[i]),train.map(i=>rows[i].observed));
 return rows.map((r,i)=>({hero:r.hero,observed:r.observed,predicted:features[i].reduce((sum,v,j)=>sum+v*fitted.coefficients[j],0)}));
}
function evaluate(rows,estimates){
 const all=rows.map((_,i)=>i);
 return ['coefficient','coefficient_plus_exposure'].map(mode=>({mode,fitted_parameter_count:mode==='coefficient'?3:4,
  fitted:R.errors(predict(rows,estimates,all,mode)),
  internal_held_owner:R.errors(rows.map((r,i)=>predict(rows,estimates,all.filter(j=>j!==i),mode)[i]))}));
}
if(require.main===module){
 const fs=require('fs'),path=require('path'),crypto=require('crypto'),folder=path.resolve(__dirname,'../../outputs/hero-report');
 const read=n=>JSON.parse(fs.readFileSync(path.join(folder,n),'utf8'));
 const names=['Replay-Observation-2026-11-07.json','Replay-Reconstruction-Inputs-2026-11-07.json','TilesSurvive-Upgrade-Data.json','Hero-Estimate-Model.json','Hero-Army-Context.json'];
 const [observation,inputs,upgrades,estimates,context]=names.map(read),rows=R.features(observation,inputs,upgrades,estimates,context).rows;
 const report={schema:1,battle_id:observation.id,training_battles:1,independent_battle_accuracy:null,promoted_to_optimizer:false,
  scope:'Negative/control experiment: shared pressure fitted without held owner; integrate configured coefficients only up to predicted survival. No per-hero corrections.',
  models:evaluate(rows,estimates),
  limits:['The coefficient-only model performs worse than the simpler HP-times-ATK control on held owners.','Adding an exposure term has no identified soldier attribution; four fitted parameters on five owners is underconstrained.','Replay presentation time is not verified original combat time.','No independent battle validation; these diagnostics do not change ranking or confidence.'],
  source_sha256:Object.fromEntries(names.map(n=>[n,crypto.createHash('sha256').update(fs.readFileSync(path.join(folder,n))).digest('hex')]))};
 fs.writeFileSync(path.join(folder,'Survival-Damage-Probes.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify(report.models.map(m=>({mode:m.mode,fit:m.fitted.wape,held_owner:m.internal_held_owner.wape}))));
}
module.exports={predict,evaluate};
