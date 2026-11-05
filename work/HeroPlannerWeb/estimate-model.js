(function(root){
  'use strict';
  function healingFormula(budget){const number=v=>Number(v.toFixed(7)).toString(),terms=[];
    if(budget.attack_coefficient>0)terms.push(`${number(budget.attack_coefficient)} x caster ATK`);
    if(budget.flat_amount>0)terms.push(number(budget.flat_amount));
    for(const t of budget.property_terms)if(t.coefficient>0)terms.push(`${number(t.coefficient)} x ${t.owner} ${t.property}`);
    return terms.join(' + ');}
  // Non-preemptive scenario: one clipped cast per hero, configured priority.
  function openingSchedule(source,window,includeInFlight=false){
    const skills=source.filter(s=>s.queue_eligible&&s.cast_duration_at_unit_speed_seconds>0&&s.cadence_assumed_seconds>0);
    const completed=Object.fromEntries(skills.map(s=>[s.id,[]])),ready=Object.fromEntries(skills.map(s=>[s.id,s.base_pre_cooldown_ms/1000]));
    let time=0;
    for(let guard=0;skills.length&&time<=window&&guard<10000;guard++){
      const next=skills.filter(s=>ready[s.id]<=time+1e-9).sort((a,b)=>b.priority-a.priority||a.slot-b.slot||(a.id<b.id?-1:a.id>b.id?1:0))[0];
      if(!next){time=Math.min(...Object.values(ready));continue;}
      const end=time+next.cast_duration_at_unit_speed_seconds;if(end>window+1e-9){if(includeInFlight)completed[next.id].push(end);break;}
      completed[next.id].push(end);ready[next.id]=time+next.cadence_assumed_seconds;time=end;
    }
    return completed;
  }
  function openingDamage(budget,ends,duration,window){let total=0;
    for(const end of ends){const start=end-duration;
      if(budget.direct_events?.length)total+=budget.direct_events.filter(e=>start+e.offset_seconds<=window+1e-9).reduce((sum,e)=>sum+e.coefficient,0);
      else if(end<=window+1e-9)total+=budget.direct_coefficient;
      for(const tick of budget.periodic_ticks){const applied=start+(tick.application_offset_seconds??duration);
        total+=Math.min(tick.nominal_ticks,Math.max(0,Math.floor((window-applied)*1000/tick.interval_ms+1e-9)))*tick.coefficient_per_tick;}
    }return total/window;}
  function coveredTime(completions,duration,window){let end=0,covered=0;
    for(const start of completions){const stop=Math.min(window,start+duration);covered+=Math.max(0,stop-Math.max(start,end));end=Math.max(end,stop);}return covered;}
  function finishTriggers(trigger,ends,window,initialDelay=0){let ready=initialDelay;const result=[];
    for(const end of ends){if(end<ready-1e-9||end+trigger.delay_seconds>=window-1e-9)continue;
      result.push(end+trigger.delay_seconds);ready=end+trigger.cooldown_seconds;}return result;}
  function missingBuild(slug,saved,data){
    const h=data.heroes[slug],stage=h.stages.find(s=>s.id===saved?.stage),level=h.levels.find(l=>l.level===saved?.level),missing=[];
    if(!stage)missing.push('exact rank / step');if(!level||stage&&level.level>stage.level_max)missing.push('valid hero level');
    if(!Array.isArray(saved?.gear))missing.push('gear (record equipped items or explicitly none)');else{const slots=new Set();for(const g of saved.gear){const type=data.gear[g?.id];if(!type||!type.levels.some(r=>r.level===g.level)||!level||type.hero_level_required>level.level||slots.has(type.slot)){missing.push('valid gear slots / levels');break;}slots.add(type.slot);}}
    if(stage)for(const skill of h.skills){const cap=stage.skill_caps[skill.slot]||0;if(!cap)continue;const n=saved?.skills?.[skill.id];if(!Number.isInteger(n)||n<0||n>cap||n>0&&!skill.levels.some(r=>r.level===n))missing.push(skill.name+' level');}
    return missing;
  }
  function evaluate(slug,saved,upgrades,estimates,battleSeconds=0,externalFlat=null,requireRecorded=false){
    if(requireRecorded){const missing=missingBuild(slug,saved,upgrades);if(missing.length)return {offense:0,durability:0,score:0,low:0,high:0,basis:"Incomplete build",comparable:false,missingFields:missing,healthContribution:0,activeSkillIds:[]};saved=structuredClone(saved);const stage=upgrades.heroes[slug].stages.find(s=>s.id===saved.stage);saved.skills??={};for(const skill of upgrades.heroes[slug].skills)if(!stage.skill_caps[skill.slot])saved.skills[skill.id]=0;}
    const model=estimates.heroes[slug],data=upgrades.heroes[slug];
    const stage=data.stages.find(s=>s.id===saved?.stage)||data.stages.find(s=>s.id===model.reference_stage);
    const levelNumber=Math.min(Number.isInteger(saved?.level)&&data.levels.some(l=>l.level===saved.level)?saved.level:model.reference_level,stage.level_max);
    const level=data.levels.find(l=>l.level===levelNumber),stats=stage.stats.map((v,i)=>v+level.stats[i]);
    let known=(saved?.stage===stage.id?1:0)+(saved?.level===levelNumber?1:0),damage=0,utility=0;
    const selfPercent=[0,0,0],teamPercent=[0,0,0];
    const activeSkillIds=[];
    const selected=[];
    const slots=new Set();let gearKnown=Array.isArray(saved?.gear);
    for(const gear of Array.isArray(saved?.gear)?saved.gear:[]){const type=upgrades.gear[gear?.id],row=type?.levels.find(l=>l.level===gear?.level);
      if(row&&type.hero_level_required<=levelNumber&&!slots.has(type.slot)){slots.add(type.slot);stats.forEach((_,i)=>stats[i]+=row.stats[i]);}else gearKnown=false;}
    if(gearKnown)known++;
    for(const skill of model.skills){const cap=stage.skill_caps[skill.slot]||0;let n=Math.min(skill.reference_level,cap),recorded=saved?.skills?.[skill.id];
      if(Number.isInteger(recorded)&&recorded>=0&&recorded<=cap&&skill.levels.some(l=>l.level===recorded)){n=recorded;known++;}
      const row=skill.levels.find(l=>l.level===n)||skill.levels[0],opening=[10,20,30].includes(battleSeconds)?row.opening_windows?.[battleSeconds]:null;damage+=opening?.damage??row.damage;utility+=row.utility;
      if(row.level>0)activeSkillIds.push(skill.id);
      if(row.level>0)selected.push({skill,row});
      for(let i=0;i<3;i++){selfPercent[i]+=(opening?.self_percent??row.self_percent)?.[i]||0;teamPercent[i]+=row.team_percent?.[i]||0;}}
    const schedule=[10,20,30].includes(battleSeconds)?openingSchedule(selected.filter(x=>x.row.cast_budget).map(x=>x.skill),battleSeconds,true):{};
    for(const {skill,row} of selected.filter(x=>Object.hasOwn(schedule,x.skill.id))){
      const completions=schedule[skill.id],budget=row.cast_budget,duration=skill.cast_duration_at_unit_speed_seconds;
      const independent=row.opening_windows?.[battleSeconds];damage+=openingDamage(budget,completions,duration,battleSeconds)-(independent?.damage??row.damage);
      const scheduledSelf=[...budget.permanent_self_percent];
      for(const buff of budget.temporary_buffs)for(let i=0;i<3;i++)scheduledSelf[i]+=buff.percent[i]*coveredTime(completions.map(end=>end-duration+(buff.application_offset_seconds??duration)),buff.duration_seconds,battleSeconds)/battleSeconds;
      for(let i=0;i<3;i++)selfPercent[i]+=scheduledSelf[i]-(independent?.self_percent??row.self_percent)[i];
    }
    for(const {skill,row} of selected.filter(x=>x.skill.finish_trigger)){
      const trigger=skill.finish_trigger,parent=selected.find(x=>x.skill.id===trigger.source_skill_id);
      const finite=[10,20,30].includes(battleSeconds),old=finite?(row.opening_windows?.[battleSeconds]?.damage??row.damage):row.damage;
      const rate=!parent?0:finite?finishTriggers(trigger,schedule[parent.skill.id]??[],battleSeconds,skill.base_pre_cooldown_ms/1000).length*row.cast_budget.direct_coefficient/battleSeconds:row.damage;
      damage+=rate-old;if(!parent){utility-=row.utility;activeSkillIds.splice(activeSkillIds.indexOf(skill.id),1);}
    }
    for(let i=0;i<3;i++){const v=externalFlat?.[i];if(Number.isFinite(v)&&v>=0)stats[i]+=v;}
    const baseStats=[...stats],factors=stats.map((_,i)=>1+selfPercent[i]+teamPercent[i]);
    stats.forEach((_,i)=>stats[i]*=factors[i]);
    function calculate(df,uf){const offense=100*stats[0]*(1+.5*Math.log1p(damage*df))/estimates.scales[0],
      durability=100*(.7*stats[2]+30*stats[1])/estimates.scales[1],u=100*(1+utility*uf)/estimates.scales[2];
      return {offense,durability,score:.55*offense+.35*durability+.1*u};}
    return {...calculate(1,1),low:calculate(.5,.5).score,high:calculate(2.5,1.5).score,
      healthContribution:calculate(1,1).durability*(.7*stats[2])/(.7*stats[2]+30*stats[1]),
      passiveContributions:[calculate(1,1).offense/factors[0],calculate(1,1).durability*30*baseStats[1]/(.7*stats[2]+30*stats[1]),calculate(1,1).durability*.7*baseStats[2]/(.7*stats[2]+30*stats[1])],
      teamPercent,selfPercent,activeSkillIds,openingCastCounts:Object.fromEntries(Object.entries(schedule).map(([id,ends])=>[id,ends.filter(end=>end<=battleSeconds+1e-9).length])),
      rawHealingPotential:selected.filter(x=>activeSkillIds.includes(x.skill.id)).flatMap(({skill,row})=>(row.healing_budgets??[]).map(b=>({skillId:skill.id,formula:healingFormula(b),execution:b.execution}))),
      basis:known===0?'Reference build':known===model.skills.length+3?'Recorded build':'Recorded + assumed'};
  }
  function compare(slug,saved,upgrades,estimates,basis,flat,battleSeconds=0,externalFlat=null){
    return basis==='flat'?{...flat,low:flat.score,high:flat.score,basis:'Flat max stats'}:
      evaluate(slug,basis==='recorded'?saved:null,upgrades,estimates,battleSeconds,externalFlat,basis==='recorded');
  }
  const api={evaluate,compare,missingBuild,openingSchedule,openingDamage,coveredTime,finishTriggers,healingFormula};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.EstimateModel=api;
})(globalThis);
