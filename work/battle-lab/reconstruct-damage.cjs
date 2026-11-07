'use strict';
const estimate=require('../HeroPlannerWeb/estimate-model.js');
const upgrade=require('../HeroPlannerWeb/upgrade-model.js');
const context=require('../HeroPlannerWeb/army-context-model.js');
const {potential}=require('./analyse-replay.cjs');
function solve(matrix,rhs){
 const a=matrix.map((row,i)=>[...row,rhs[i]]),n=rhs.length;
 for(let j=0;j<n;j++){
  let pivot=j;for(let i=j+1;i<n;i++)if(Math.abs(a[i][j])>Math.abs(a[pivot][j]))pivot=i;
  if(Math.abs(a[pivot][j])<1e-10)return null;
  [a[j],a[pivot]]=[a[pivot],a[j]];const d=a[j][j];for(let k=j;k<=n;k++)a[j][k]/=d;
  for(let i=0;i<n;i++)if(i!==j){const f=a[i][j];for(let k=j;k<=n;k++)a[i][k]-=f*a[j][k];}
 }return a.map(row=>row[n]);
}
// Small exact active-set NNLS. Column scaling prevents ATK and seconds units dominating conditioning.
function nonnegativeFit(x,y){
 if(!x.length||x.length!==y.length||!x[0].length||x[0].length>3||x.some(r=>r.length!==x[0].length||r.some(v=>!Number.isFinite(v)||v<0))||y.some(v=>!Number.isFinite(v)||v<0))throw new Error('Invalid nonnegative fit inputs');
 const m=x[0].length,scales=Array.from({length:m},(_,j)=>Math.sqrt(x.reduce((s,r)=>s+r[j]**2,0)/x.length)||1),z=x.map(r=>r.map((v,j)=>v/scales[j]));
 let best={coefficients:Array(m).fill(0),sse:y.reduce((s,v)=>s+v*v,0),active:0};
 for(let mask=1;mask<1<<m;mask++){
  const active=Array.from({length:m},(_,j)=>j).filter(j=>mask&(1<<j));
  const gram=active.map(j=>active.map(k=>z.reduce((s,r)=>s+r[j]*r[k],0))),rhs=active.map(j=>z.reduce((s,r,i)=>s+r[j]*y[i],0)),beta=solve(gram,rhs);
  if(!beta||beta.some(v=>v< -1e-8))continue;
  const coefficients=Array(m).fill(0);active.forEach((j,k)=>coefficients[j]=Math.max(0,beta[k])/scales[j]);
  const sse=x.reduce((s,r,i)=>s+(r.reduce((v,f,j)=>v+f*coefficients[j],0)-y[i])**2,0);
  if(sse<best.sse-1e-6)best={coefficients,sse,active:active.length};
 }return best;
}
const dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);
function errors(rows){
 const total=rows.reduce((s,r)=>s+r.observed,0),absolute=rows.reduce((s,r)=>s+Math.abs(r.predicted-r.observed),0),positive=rows.filter(r=>r.observed>0);
 let comparable=0,agree=0;
 for(let i=0;i<rows.length;i++)for(let j=i+1;j<rows.length;j++){
  const a=rows[i],b=rows[j];if(Math.abs(a.observed-b.observed)<=(a.display_quantum||0)+(b.display_quantum||0))continue;
  comparable++;if((a.predicted-b.predicted)*(a.observed-b.observed)>0)agree++;
 }
 return {wape:total?absolute/total:null,mae:rows.length?absolute/rows.length:null,max_owner_relative_error:positive.length?Math.max(...positive.map(r=>Math.abs(r.predicted-r.observed)/r.observed)):null,
  observed_total:total,predicted_total:rows.reduce((s,r)=>s+r.predicted,0),rounding_separated_rank_pairs:comparable,rank_pairs_agree:agree,rows:rows.map(r=>({...r,relative_error:r.observed?r.predicted/r.observed-1:null}))};
}
function fitModel(rows,spec){
 let best=null;
 for(const candidate of spec.candidates){
  const fit=nonnegativeFit(rows.map(r=>candidate.features(r)),rows.map(r=>r.observed));
  if(!best||fit.sse<best.sse-1e-6)best={...fit,candidate,parameters:{...candidate.parameters,coefficients:fit.coefficients}};
 }return best;
}
function evaluateModel(rows,spec){
 const fit=fitModel(rows,spec),prediction=r=>dot(fit.candidate.features(r),fit.coefficients),folds=[];
 const fitted=errors(rows.map(r=>({hero:r.hero,observed:r.observed,predicted:prediction(r),display_quantum:10000})));
 for(let i=0;i<rows.length;i++){
  const held=rows[i],trained=fitModel(rows.filter((_,j)=>j!==i),spec);
  folds.push({hero:held.hero,observed:held.observed,predicted:dot(trained.candidate.features(held),trained.coefficients),display_quantum:10000,trained_on:rows.filter((_,j)=>j!==i).map(r=>r.hero),parameters:trained.parameters});
 }
 return {id:spec.id,fitted_parameter_count:spec.parameter_count,features:spec.labels,fitted_parameters:fit.parameters,in_sample:fitted,leave_one_owner_out:errors(folds),scope:'Conditional retrospective reconstruction. Leave-one-owner-out re-fits on the other four owners in this same battle, including any defence-grid selection. Neither is independent battle validation.'};
}
function features(observation,inputs,upgrades,estimates,army,position='midpoint',accountSource='video_only'){
 if(inputs.battle_id!==observation.id)throw new Error('Mismatched reconstruction case');
 let reconstructed=inputs.signature_power;const result=[];
 for(const h of observation.heroes){
  const slug=h.planner_slug,hero=upgrades.heroes[slug],build={stage:inputs.candidate_stages[slug],level:h.level,gear:h.gear,skills:Object.fromEntries(hero.skills.map(s=>[s.id,h.skill_levels_by_slot[s.slot]]))};
  if(!hero.stages.some(s=>s.id===build.stage))throw new Error('Missing candidate rank');
  const state=upgrade.state(slug,build,upgrades,30);if(state.error)throw new Error(state.error);reconstructed+=state.power;
  const settings=accountSource==='saved_context_candidate'?inputs.candidate_army_context:{enabled:true,signature:inputs.signature};
  if(!settings)throw new Error('Missing candidate account context');
  const known=context.resolve(slug,settings,army,'recorded');
  const skills=estimates.heroes[slug].skills.map(s=>({...s,row:s.levels.find(r=>r.level===build.skills[s.id])}));
  if(skills.some(s=>!s.row))throw new Error('Unknown recorded skill');
  const t=observation.timing_scenario,lifeBounds=[t.speed*(h.grey_wall_seconds[0]-t.battle_start_wall_seconds[1]),t.speed*(h.grey_wall_seconds[1]-t.battle_start_wall_seconds[0])],life=position==='earliest'?lifeBounds[0]:position==='latest'?lifeBounds[1]:(lifeBounds[0]+lifeBounds[1])/2;
  const budget=potential(skills,30,life,false),full=potential(skills,30,30,false),basic=skills.find(s=>s.slot===0),baseAttack=state.stats[0]+known.flat[0];
  const score=estimate.evaluate(slug,build,upgrades,estimates,0,known.flat,true);
  result.push({hero:slug,observed:h.damage,observed_damage_taken:h.damage_taken,known_flat_hp:state.stats[2]+known.flat[2],build,known_base_stats:state.stats,known_context_flat:known.flat,known_signature_flat:context.resolve(slug,{enabled:true,signature:inputs.signature},army,'recorded').flat,base_attack:baseAttack,known_attack_factor:1+skills.reduce((s,k)=>s+(k.row.cast_budget?.permanent_self_percent?.[0]||0)+(k.row.team_percent?.[0]||0),0),
   offense_index:score.offense,offense_per_additional_team_attack_percent:score.passiveContributions[0],team_attack_percent:score.teamPercent[0],
   alive_seconds:life,alive_seconds_bounds:lifeBounds,coefficient:budget.coefficient,basic_coefficient:budget.perSkillCoefficient[basic.id]||0,other_coefficient:budget.coefficient-(budget.perSkillCoefficient[basic.id]||0),full_coefficient:full.coefficient});
 }
 if(reconstructed!==observation.friendly.hero_power)throw new Error('Candidate build power no longer reconciles the report');
 for(const r of result){const others=result.filter(s=>s!==r).reduce((s,h)=>s+h.team_attack_percent,0);r.offense_index+=others*r.offense_per_additional_team_attack_percent;r.known_attack_factor+=others;r.attack=r.base_attack*r.known_attack_factor;}
 return {reconstructed_hero_power:reconstructed,rows:result};
}
function specifications(rows){
 const meanAttack=rows.reduce((s,r)=>s+r.attack,0)/rows.length;
 const one=(id,label,fn)=>({id,parameter_count:1,labels:[label],candidates:[{parameters:{},features:r=>[fn(r)]}]});
 return [one('planner_offense','current production offense index',r=>r.offense_index),one('full_30s_coefficient','known ATK times 30-second coefficient',r=>r.attack*r.full_coefficient),
  one('observed_lifetime_coefficient','known ATK times observed-lifetime coefficient',r=>r.attack*r.coefficient),
  {id:'native_base_defence_grid',parameter_count:2,labels:['native ATK^2/(ATK+2.5*shared_DEF) times observed-lifetime coefficient'],candidates:[0,.25,.5,1,2].map(ratio=>({parameters:{defence_to_mean_known_attack:ratio,shared_defence:ratio*meanAttack},features:r=>[r.attack*r.attack/(r.attack+2.5*ratio*meanAttack)*r.coefficient]}))},
  one('lifetime_only_control','observed survival seconds, with no skill/build information',r=>r.alive_seconds),
  {id:'coefficient_plus_owned_exposure',parameter_count:2,labels:['known ATK times observed-lifetime coefficient','observed survival seconds (unassigned owned-output term, not identified soldier damage)'],candidates:[{parameters:{},features:r=>[r.attack*r.coefficient,r.alive_seconds]}]},
  {id:'basic_other_plus_exposure',parameter_count:3,labels:['known ATK times basic coefficient','known ATK times other coefficient','observed survival seconds (unassigned)'],candidates:[{parameters:{},features:r=>[r.attack*r.basic_coefficient,r.attack*r.other_coefficient,r.alive_seconds]}]}];
}
function reconstruct(observation,inputs,upgrades,estimates,army){
 const fixed=features(observation,inputs,upgrades,estimates,army),models=specifications(fixed.rows).map(s=>evaluateModel(fixed.rows,s));
 const incomingRows=fixed.rows.map(r=>({...r,observed:r.observed_damage_taken}));
 const incomingSpecifications=[
  {id:'known_flat_hp_scaled',parameter_count:1,labels:['known flat hero HP'],candidates:[{parameters:{},features:r=>[r.known_flat_hp]}]},
  {id:'shared_effective_incoming_budget',parameter_count:2,labels:['known flat hero HP','shared effective incoming-budget offset (not identified base HP)'],candidates:[{parameters:{},features:r=>[r.known_flat_hp,1]}]}
 ];const damage_taken_models=incomingSpecifications.map(s=>evaluateModel(incomingRows,s));
 const candidate=features(observation,inputs,upgrades,estimates,army,'midpoint','saved_context_candidate');
 const summary=m=>({id:m.id,in_sample_wape:m.in_sample.wape,max_owner_relative_error:m.in_sample.max_owner_relative_error,leave_one_owner_out_wape:m.leave_one_owner_out.wape});
 const context_sensitivity={source:'saved_context_candidate',provenance:inputs.candidate_context_provenance,known_stats:candidate.rows.map(r=>({hero:r.hero,flat_context:r.known_context_flat})),models:specifications(candidate.rows).map(s=>summary(evaluateModel(candidate.rows,s))),damage_taken_models:incomingSpecifications.map(s=>summary(evaluateModel(candidate.rows.map(r=>({...r,observed:r.observed_damage_taken})),s)))};
 const timing_sensitivity=['earliest','latest'].map(position=>{const f=features(observation,inputs,upgrades,estimates,army,position);return {position,models:specifications(f.rows).map(s=>{const r=evaluateModel(f.rows,s);return {id:r.id,in_sample_wape:r.in_sample.wape,leave_one_owner_out_wape:r.leave_one_owner_out.wape};})};});
 return {schema:1,battle_id:observation.id,evaluation_role:'retrospective_calibration',independent_battles:1,model_version:estimates.version,source_sha256:observation.source_sha256,
  damage_definition:observation.damage_definition,build_power_check:{reconstructed:fixed.reconstructed_hero_power,observed:observation.friendly.hero_power},
  observed_hero_damage_total:fixed.rows.reduce((s,r)=>s+r.observed,0),observed_behemoth_damage_excluded_from_fit:observation.friendly.behemoths.reduce((s,p)=>s+p.damage,0),
  conditioned_on:['Recorded gear, hero levels, skill levels and Signature flat stats','Candidate exact rank steps (combined power matches)','Observed presentation survival intervals at assumed 2x playback; original combat clock unverified'],
  unknown_inputs:inputs.unknown_context,features:fixed.rows,models,damage_taken_models,timing_sensitivity,context_sensitivity,
  limits:['Static replay paths load stored rounds, initialize replay hero ATK to 0 / HP to 100, and import report statistics. Animation-derived time is not established as authoritative original fight time.',
  'Shared scaling and nuisance coefficients are fitted from these outcomes; no per-hero multiplier is fitted.','Survival is supplied from the replay rather than predicted. Targeting, movement, hit success, criticals and shielding are not recreated.','Hero rows include eligible owned actors; an exposure term is not a measured soldier or summon damage fraction.','The defence grid is a nuisance-shape probe; fitted DEF is not recovered enemy defence. Its grid boundary can hide missing mechanisms.','Leave-one-owner-out is an internal same-battle stress test; all five owners share the encounter and observations.','The shared incoming-budget offset is an empirical fit to reported damage taken, not recovered troop HP, Research, Behemoth stats or an effective-healing allocation.',
  'Balanced global scoring includes survival and utility and cannot be calibrated against damage columns alone. No production weight is changed.'],
  independent_battle_accuracy:null};
}
if(require.main===module){const fs=require('fs'),path=require('path'),folder=path.resolve(__dirname,'../../outputs/hero-report'),read=n=>JSON.parse(fs.readFileSync(path.join(folder,n),'utf8'));const r=reconstruct(read('Replay-Observation-2026-11-07.json'),read('Replay-Reconstruction-Inputs-2026-11-07.json'),read('TilesSurvive-Upgrade-Data.json'),read('Hero-Estimate-Model.json'),read('Hero-Army-Context.json'));
 const crypto=require('crypto');r.source_hashes=Object.fromEntries(['Replay-Observation-2026-11-07.json','Replay-Reconstruction-Inputs-2026-11-07.json','Hero-Estimate-Model.json','TilesSurvive-Upgrade-Data.json','Hero-Army-Context.json','Replay-Authority-Audit.json'].map(n=>[n,crypto.createHash('sha256').update(fs.readFileSync(path.join(folder,n))).digest('hex')]));
 r.code_hashes=Object.fromEntries(['reconstruct-damage.cjs','analyse-replay.cjs','../HeroPlannerWeb/estimate-model.js','../HeroPlannerWeb/upgrade-model.js','../HeroPlannerWeb/army-context-model.js'].map(n=>[n,crypto.createHash('sha256').update(fs.readFileSync(path.resolve(__dirname,n))).digest('hex')]));
 fs.writeFileSync(path.join(folder,'Retrospective-Damage-Reconstruction.json'),JSON.stringify(r,null,2)+'\n');console.log(JSON.stringify([...r.models,...r.damage_taken_models].map(m=>({model:m.id,fit_wape:m.in_sample.wape,max_owner_error:m.in_sample.max_owner_relative_error,leave_one_owner_out_wape:m.leave_one_owner_out.wape,parameters:m.fitted_parameters})),null,2));}
module.exports={solve,nonnegativeFit,errors,fitModel,evaluateModel,features,specifications,reconstruct};
