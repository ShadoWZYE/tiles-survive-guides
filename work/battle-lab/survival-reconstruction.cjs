'use strict';
const {project}=require('../HeroPlannerWeb/survival-model.js'),R=require('./reconstruct-damage.cjs');
const SHARES=[0,.05,.1,.15,.2,.3,.4,.5,.6,.7];
function calibrate(rows,trainingIndices){
 if(trainingIndices.length<2)throw new Error('Insufficient survival training rows');let best;
 for(const share of SHARES){
  const unit=project(rows.map(r=>r.known_flat_hp),1,share,Number.MAX_VALUE).deathTimes;
  const fit=R.nonnegativeFit(trainingIndices.map(i=>[unit[i]]),trainingIndices.map(i=>rows[i].alive_seconds));
  if(!(fit.coefficients[0]>0))continue;
  if(!best||fit.sse<best.sse-1e-9)best={back_share:share,pressure:1/fit.coefficients[0],sse:fit.sse};
 }if(!best)throw new Error('No valid survival calibration');return best;
}
function evaluate(rows){
 const indices=rows.map((_,i)=>i),all=calibrate(rows,indices),full=project(rows.map(r=>r.known_flat_hp),all.pressure,all.back_share,30),folds=[];
 const output=(training,calibration,source)=>{
  const lives=project(rows.map(r=>r.known_flat_hp),calibration.pressure,calibration.back_share,30).aliveSeconds;
  const scale=R.nonnegativeFit(training.map(i=>[rows[i][source]*lives[i]]),training.map(i=>rows[i].observed)).coefficients[0];
  return rows.map((r,i)=>r[source]*lives[i]*scale);
 };
 for(const i of indices){const train=indices.filter(j=>i!==j),cal=calibrate(rows,train),lives=project(rows.map(r=>r.known_flat_hp),cal.pressure,cal.back_share,30).aliveSeconds;
  folds.push({hero:rows[i].hero,observed:rows[i].alive_seconds,predicted:lives[i],training_owners:train.map(j=>rows[j].hero),calibration:cal,attack_damage:output(train,cal,'attack')[i],offense_damage:output(train,cal,'offense_index')[i]});}
 const positionControl=indices.map(i=>{const group=indices.filter(j=>j!==i&&(j<2)===(i<2));return {hero:rows[i].hero,observed:rows[i].alive_seconds,predicted:group.reduce((v,j)=>v+rows[j].alive_seconds,0)/group.length};});
 return {calibration:all,controls:{position_only_held_owner:R.errors(positionControl)},survival:{fitted:R.errors(rows.map((r,i)=>({hero:r.hero,observed:r.alive_seconds,predicted:full.aliveSeconds[i]}))),internal_held_owner:R.errors(folds),held_owner_predictions_inside_observed_interval:folds.filter((r,i)=>r.predicted>=rows[i].alive_seconds_bounds[0]&&r.predicted<=rows[i].alive_seconds_bounds[1]).length},damage:Object.fromEntries(['attack','offense_index'].map(source=>[source,{fitted:R.errors(rows.map((r,i)=>({hero:r.hero,observed:r.observed,predicted:output(indices,all,source)[i],display_quantum:10000}))),internal_held_owner:R.errors(rows.map((r,i)=>({hero:r.hero,observed:r.observed,predicted:folds[i][source==='attack'?'attack_damage':'offense_damage'],display_quantum:10000})))}])),folds};
}
if(require.main===module){const fs=require('fs'),path=require('path'),crypto=require('crypto'),folder=path.resolve(__dirname,'../../outputs/hero-report'),read=n=>JSON.parse(fs.readFileSync(path.join(folder,n),'utf8'));
 const o=read('Replay-Observation-2026-11-07.json'),rows=R.features(o,read('Replay-Reconstruction-Inputs-2026-11-07.json'),read('TilesSurvive-Upgrade-Data.json'),read('Hero-Estimate-Model.json'),read('Hero-Army-Context.json')).rows;
 if(rows.slice(0,2).map(r=>r.hero).join(',')!=='rosie,freja')throw new Error('Recheck the pre-fight front pair before calibrating');
 const report={schema:1,battle_id:o.id,independent_battles:1,independent_battle_accuracy:null,model:'Shared HP-pressure budget; two front positions shield three back positions; pressure redirects after deaths',pre_fight_front_pair:['rosie','freja'],fitted_survival_parameters:2,fitted_survival_and_damage_parameters:3,scope:'Same-battle calibration, not an independent validation. Held-owner folds exclude that owner death time AND damage from every fitted parameter. Only known pre-fight HP and positions are used when predicting.',limits:['Pressure is an inferred HP-drain benchmark, not recovered enemy ATK or a transferable server formula.','Troop health, shield, effective healing, control and target-specific mitigation are not supplied or invented.','Presentation death intervals remain an uncertain proxy for original combat time.','The optional optimiser adjustment discounts personal offense exposure only; survival and utility score weights remain unchanged.','A position-only control performs similarly on this small sample; the HP mechanism is not established as superior by independent battles.'],...evaluate(rows)};
 report.presentation_time_sensitivity=['earliest','latest'].map(position=>{const r=R.features(o,read('Replay-Reconstruction-Inputs-2026-11-07.json'),read('TilesSurvive-Upgrade-Data.json'),read('Hero-Estimate-Model.json'),read('Hero-Army-Context.json'),position).rows,result=evaluate(r);return {position,calibration:result.calibration,survival_held_owner_wape:result.survival.internal_held_owner.wape,offense_damage_held_owner_wape:result.damage.offense_index.internal_held_owner.wape};});
 report.source_hashes=Object.fromEntries(['Replay-Observation-2026-11-07.json','Replay-Reconstruction-Inputs-2026-11-07.json','Hero-Estimate-Model.json','Hero-Army-Context.json'].map(n=>[n,crypto.createHash('sha256').update(fs.readFileSync(path.join(folder,n))).digest('hex')]));
 fs.writeFileSync(path.join(folder,'Survival-Reconstruction.json'),JSON.stringify(report,null,2)+'\n');
 fs.writeFileSync(path.join(folder,'Survival-Benchmark.json'),JSON.stringify({version:1,pressure:report.calibration.pressure,back_share:report.calibration.back_share,horizon:30,label:'Recorded-pressure HP benchmark (experimental)',source_battle:o.id,training_battles:1,scope:report.scope,limits:report.limits},null,2)+'\n');
 console.log(JSON.stringify({survival_fit:report.survival.fitted.wape,survival_held_owner:report.survival.internal_held_owner.wape,damage:report.damage,calibration:report.calibration},null,2));
}
module.exports={calibrate,evaluate};
