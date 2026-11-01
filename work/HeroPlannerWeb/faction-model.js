(function(root){
  'use strict';
  const cache=new Map();
  function normalize(faction){return ({mountain:'Mountain',stalwart:'Mountain',wasteland:'Wasteland',rover:'Wasteland',sky:'Sky',aeronaut:'Sky',sea:'Sea',mariner:'Sea'})[String(faction||'').trim().toLowerCase()]||'Unknown';}
  function compose(factions){
    if(factions.length>5)throw new Error('A formation has at most five heroes.');
    const counts=[0,0,0];let mariners=0;
    for(const f of factions){const n=normalize(f),i=['Mountain','Wasteland','Sky'].indexOf(n);if(i>=0)counts[i]++;else if(n==='Sea')mariners++;}
    const key=[...counts,mariners].join(',');if(cache.has(key))return cache.get(key);
    let best={pattern:'mixed',healthBonus:0,counterBonus:0,mariners};
    for(let a=0;a<=mariners;a++)for(let b=0;b<=mariners-a;b++){
      const c=[counts[0]+a,counts[1]+b,counts[2]+mariners-a-b].sort((x,y)=>y-x);
      const tier=c[0]===5?['5',.25,.05]:c[0]===4?['4',.18,.05]:c[0]===3&&c[1]===2?['3+2',.12,.05]:c[0]===3?['3',.08,0]:c[0]===2&&c[1]===2?['2+2',.04,0]:c[0]===2?['2',.02,0]:['mixed',0,0];
      if(tier[1]>best.healthBonus)best={pattern:tier[0],healthBonus:tier[1],counterBonus:tier[2],mariners};
    }
    Object.freeze(best);cache.set(key,best);return best;
  }
  function counters(attacker,target){return ({Wasteland:'Mountain',Mountain:'Sky',Sky:'Wasteland'})[normalize(attacker)]===normalize(target);}
  function summary(effect){return `Faction ${effect.pattern}: Final Health +${Math.round(effect.healthBonus*100)}%`+(effect.mariners?` (${effect.mariners} Mariner wildcard${effect.mariners===1?'':'s'})`:'')+(effect.counterBonus?`; counter damage +${Math.round(effect.counterBonus*100)}% when applicable`:'');}
  function scoreBonus(heroes,mode,flat=false,enemyFaction='Unknown'){
    if(!heroes.length)return 0;
    const effect=compose(heroes.map(h=>h.faction));
    const hp=heroes.reduce((s,h)=>s+h.healthContribution,0)/heroes.length*effect.healthBonus;
    const offense=heroes.reduce((s,h)=>s+(counters(h.faction,enemyFaction)?h.offense_index*(.20+effect.counterBonus):0),0)/heroes.length;
    const dw=flat?.25:.35,ow=flat?.35:.55;
    if(mode==='Offense')return flat?offense:.75*offense+.25*(ow*offense+dw*hp);
    if(mode==='Survival')return flat?hp:.75*hp+.25*(ow*offense+dw*hp);
    if(mode==='PvE farming'&&!flat)return .45*offense+.30*hp+.25*(ow*offense+dw*hp);
    return ow*offense+dw*hp;
  }
  const api={normalize,compose,counters,summary,scoreBonus};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.FactionModel=api;
})(globalThis);
