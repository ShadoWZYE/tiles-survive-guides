(function(root){
  'use strict';
  // Conservative planning prior, not a fitted targeting probability.
  const frontWeight=.75;
  function key(h){return h.asset_slug||h.name||'';}
  function weight(mode){return mode==='Survival'?.8375:mode==='Offense'?.0875:mode==='PvE farming'?.3875:.35;}
  function teamTotal(heroes){
    const total=[0,0,0];for(const x of heroes)for(let i=0;i<3;i++)total[i]+=x.estimate?.teamPercent?.[i]||0;return total;
  }
  function delta(total,h,i){
    return (total[i]-(h.estimate?.teamPercent?.[i]||0))*(h.estimate?.passiveContributions?.[i]||0);
  }
  function passiveBonus(heroes,mode='Balanced',flat=false){
    if(flat||!heroes.length)return 0;
    const total=teamTotal(heroes);if(total.every(v=>v===0))return 0;
    const offense=mode==='Survival'?.1375:mode==='Offense'?.8875:mode==='PvE farming'?.5875:.55;
    return heroes.reduce((sum,h)=>sum+offense*delta(total,h,0)+weight(mode)*(delta(total,h,1)+delta(total,h,2)),0)/heroes.length;
  }
  function evaluate(heroes,mode='Balanced',flat=false,healthBonus=0,exposure=frontWeight){
    if(!heroes.length)return {heroes:[],adjustment:0,frontDurability:0};
    const role={Melee:0,Mid:1,Range:2};
    const legacy=[...heroes].sort((a,b)=>(role[a.role]??3)-(role[b.role]??3)||
      (a.role==='Melee'?b.durability_index-a.durability_index:b.offense_index-a.offense_index)||key(a).localeCompare(key(b)));
    if(flat||heroes.length!==5)return {heroes:legacy,adjustment:0,frontDurability:0};
    const total=teamTotal(heroes);
    const durability=h=>Math.max(0,h.durability_index+(h.healthContribution||0)*healthBonus+delta(total,h,1)+delta(total,h,2));
    // Keep ranged carries protected when two non-ranged candidates are available.
    const candidates=heroes.filter(h=>h.role==='Melee'||h.role==='Mid');
    const pool=candidates.length>=2?candidates:heroes;
    const front=[...pool].sort((a,b)=>durability(b)-durability(a)||a.offense_index-b.offense_index||key(a).localeCompare(key(b))).slice(0,2);
    const back=heroes.filter(h=>!front.includes(h)).sort((a,b)=>b.offense_index-a.offense_index||key(a).localeCompare(key(b)));
    const a=durability(front[0]),b=durability(front[1]);
    const frontDurability=a+b>0?2*a*b/(a+b):0;
    const mean=heroes.reduce((s,h)=>s+durability(h),0)/5;
    const rear=back.reduce((s,h)=>s+durability(h),0)/3;
    return {heroes:[...front,...back],frontDurability,
      adjustment:weight(mode)*(exposure*frontDurability+(1-exposure)*rear-mean)};
  }
  const api={evaluate,frontWeight,passiveBonus};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.FormationModel=api;
})(globalThis);
