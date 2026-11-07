'use strict';
const {openingSchedule,finishTriggers}=require('../HeroPlannerWeb/estimate-model.js');
// Raid coefficient potential only: no final damage, target/AI or death prediction.
function potential(skills,horizon,aliveUntil,persist=false){
 if(!Number.isFinite(horizon)||horizon<=0||!Number.isFinite(aliveUntil)||aliveUntil<0||aliveUntil>horizon)throw new Error('Invalid observation/lifetime window');
 const selected=skills.filter(s=>s.row?.level>0),queue=selected.filter(s=>s.queue_eligible&&s.row.cast_budget),schedule=openingSchedule(queue,aliveUntil,true);
 let coefficient=0;const cutoff=Math.min(horizon,aliveUntil),endsAt=persist?horizon:cutoff;
 for(const s of queue){const budget=s.row.cast_budget,duration=s.cast_duration_at_unit_speed_seconds;
  for(const end of schedule[s.id]||[]){const start=end-duration;if(start>=cutoff-1e-9)continue;
   if(budget.direct_events?.length){for(const e of budget.direct_events)if(start+e.offset_seconds<=cutoff+1e-9)coefficient+=e.coefficient;}
   else if(end<=cutoff+1e-9)coefficient+=budget.direct_coefficient;
   for(const tick of budget.periodic_ticks){const applied=start+(tick.application_offset_seconds??duration);
    if(applied>cutoff+1e-9)continue;
    coefficient+=Math.min(tick.nominal_ticks,Math.max(0,Math.floor((endsAt-applied)*1000/tick.interval_ms+1e-9)))*tick.coefficient_per_tick;
   }
  }
 }
 for(const s of selected.filter(s=>s.finish_trigger&&s.row.cast_budget)){
  const t=s.finish_trigger,parentEnds=(schedule[t.source_skill_id]||[]).filter(end=>end<=cutoff+1e-9);
  coefficient+=finishTriggers(t,parentEnds,cutoff,s.base_pre_cooldown_ms/1000).length*s.row.cast_budget.direct_coefficient;
 }
 return {coefficient,perObservationSecond:coefficient/horizon,completedCasts:Object.fromEntries(queue.map(s=>[s.id,(schedule[s.id]||[]).filter(end=>end<=cutoff+1e-9&&end-s.cast_duration_at_unit_speed_seconds<cutoff-1e-9).length]))};
}
function analyse(observation,upgrades,estimates){
 const friendly=observation.friendly,heroDamage=observation.heroes.reduce((sum,h)=>sum+h.damage,0),petDamage=friendly.behemoths.reduce((s,p)=>s+p.damage,0);
 let skillPower=0,gearPower=0;
 const checks=[],heroes=[];
 for(const h of observation.heroes){const model=estimates.heroes[h.planner_slug],data=upgrades.heroes[h.planner_slug];
  const skills=model.skills.map(s=>({...s,row:s.levels.find(r=>r.level===h.skill_levels_by_slot[s.slot])}));
  if(skills.some(s=>!s.row))throw new Error('Missing observed skill row');
  for(const s of data.skills){const level=h.skill_levels_by_slot[s.slot];if(level)skillPower+=s.levels.find(r=>r.level===level).power;}
  for(const g of h.gear)gearPower+=upgrades.gear[g.id].levels.find(r=>r.level===g.level).power;
  const active=model.skills.find(s=>s.slot===1),seconds=active.base_pre_cooldown_ms/1000;
  checks.push({hero:h.name,consistent:h.opening_countdown_display-1<seconds&&seconds<=h.opening_countdown_display,configured:seconds,display:h.opening_countdown_display});
  const timing=observation.timing_scenario,life=[(h.grey_wall_seconds[0]-timing.battle_start_wall_seconds[1])*timing.speed,(h.grey_wall_seconds[1]-timing.battle_start_wall_seconds[0])*timing.speed];
  heroes.push({hero:h.name,scenario_alive_seconds:life,damage_per_alive_second_scenario:[h.damage/life[1],h.damage/life[0]],
   lifetime_coefficient_potential:[potential(skills,30,life[0]).coefficient,potential(skills,30,life[1],true).coefficient],full_30s_coefficient_potential:potential(skills,30,30).coefficient});
 }
 return {schema:1,battle_id:observation.id,independent_battles:1,model_version:estimates.version,source_sha256:observation.source_sha256,
  opening_countdowns:checks,skill_power:{observed:friendly.skill_power,reconstructed:skillPower,consistent:skillPower===friendly.skill_power},gear_power:{observed:friendly.gear_power,reconstructed:gearPower,residual:friendly.gear_power-gearPower},
  damage:{hero:heroDamage,behemoth:petDamage,total:heroDamage+petDamage,behemoth_fraction:petDamage/(heroDamage+petDamage)},heroes,
  winner_prediction:null,damage_prediction:null,accuracy_percentage:null,
  scope:'Observed-lifetime sensitivity analysis at assumed 2x playback, not a live battle simulator. Coefficients omit targets, hit success, movement, interruption, attack speed, some conditional/summon effects and effective healing. No global weight fitting from this one fight.',unresolved:observation.unresolved};
}
if(require.main===module){const fs=require('fs'),path=require('path'),folder=path.resolve(__dirname,'../../outputs/hero-report'),read=n=>JSON.parse(fs.readFileSync(path.join(folder,n),'utf8'));
 const result=analyse(read('Replay-Observation-2026-11-07.json'),read('TilesSurvive-Upgrade-Data.json'),read('Hero-Estimate-Model.json'));
 fs.writeFileSync(path.join(folder,'Replay-Checks-2026-11-07.json'),JSON.stringify(result,null,2)+'\n');
 console.log(`One battle; countdowns ${result.opening_countdowns.filter(c=>c.consistent).length}/5; skill power reconciled: ${result.skill_power.consistent}; gear residual: ${result.gear_power.residual}. Predictive accuracy unmeasured.`);
}
module.exports={potential,analyse};
