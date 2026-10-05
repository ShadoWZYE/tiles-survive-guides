(function(root){
  'use strict';
  function evaluate(slug,saved,upgrades,estimates){
    const model=estimates.heroes[slug],data=upgrades.heroes[slug];
    const stage=data.stages.find(s=>s.id===saved?.stage)||data.stages.find(s=>s.id===model.reference_stage);
    const levelNumber=Math.min(Number.isInteger(saved?.level)&&data.levels.some(l=>l.level===saved.level)?saved.level:model.reference_level,stage.level_max);
    const level=data.levels.find(l=>l.level===levelNumber),stats=stage.stats.map((v,i)=>v+level.stats[i]);
    let known=(saved?.stage===stage.id?1:0)+(saved?.level===levelNumber?1:0),damage=0,utility=0;
    const slots=new Set();let gearKnown=Array.isArray(saved?.gear);
    for(const gear of Array.isArray(saved?.gear)?saved.gear:[]){const type=upgrades.gear[gear?.id],row=type?.levels.find(l=>l.level===gear?.level);
      if(row&&type.hero_level_required<=levelNumber&&!slots.has(type.slot)){slots.add(type.slot);stats.forEach((_,i)=>stats[i]+=row.stats[i]);}else gearKnown=false;}
    if(gearKnown)known++;
    for(const skill of model.skills){const cap=stage.skill_caps[skill.slot]||0;let n=Math.min(skill.reference_level,cap),recorded=saved?.skills?.[skill.id];
      if(Number.isInteger(recorded)&&recorded>=0&&recorded<=cap&&skill.levels.some(l=>l.level===recorded)){n=recorded;known++;}
      const row=skill.levels.find(l=>l.level===n)||skill.levels[0];damage+=row.damage;utility+=row.utility;}
    function calculate(df,uf){const offense=100*stats[0]*(1+.5*Math.log1p(damage*df))/estimates.scales[0],
      durability=100*(.7*stats[2]+30*stats[1])*(1+.08*utility*uf)/estimates.scales[1],u=100*(1+utility*uf)/estimates.scales[2];
      return {offense,durability,score:.55*offense+.35*durability+.1*u};}
    return {...calculate(1,1),low:calculate(.5,.5).score,high:calculate(2.5,1.5).score,
      basis:known===0?'Reference build':known===model.skills.length+3?'Recorded build':'Recorded + assumed'};
  }
  function compare(slug,saved,upgrades,estimates,basis,flat){
    return basis==='flat'?{...flat,low:flat.score,high:flat.score,basis:'Flat max stats'}:
      evaluate(slug,basis==='recorded'?saved:null,upgrades,estimates);
  }
  const api={evaluate,compare};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.EstimateModel=api;
})(globalThis);
