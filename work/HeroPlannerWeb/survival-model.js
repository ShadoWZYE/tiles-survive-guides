(function(root){'use strict';
// Reference HP-pressure scenario. No observed death times or damage rows are inputs.
function project(hp,pressure,backShare,horizon=30){
 if(!Array.isArray(hp)||hp.length!==5||hp.some(x=>!Number.isFinite(x)||x<0)||!Number.isFinite(pressure)||pressure<=0||!Number.isFinite(backShare)||backShare<0||backShare>1||!Number.isFinite(horizon)||horizon<=0)throw new Error('Invalid survival scenario');
 const remaining=[...hp],dead=hp.map(x=>x===0),death=hp.map(()=>0);let time=0;
 for(let event=0;event<5&&dead.some(x=>!x);event++){
  const front=(+!dead[0])+(+!dead[1]),back=(+!dead[2])+(+!dead[3])+(+!dead[4]);
  const rates=hp.map((_,i)=>dead[i]?0:i<2?pressure*(back?1-backShare:1)/front:pressure*(front?backShare:1)/back);
  let dt=Infinity;for(let i=0;i<5;i++)if(!dead[i]&&rates[i]>0)dt=Math.min(dt,remaining[i]/rates[i]);
  if(!Number.isFinite(dt))throw new Error('Scenario has no reachable target');time+=dt;
  for(let i=0;i<5;i++)if(!dead[i]){remaining[i]=Math.max(0,remaining[i]-rates[i]*dt);if(remaining[i]<=1e-9*Math.max(1,hp[i])){dead[i]=true;death[i]=time;}}
 }
 return {deathTimes:death,aliveSeconds:death.map(t=>Math.min(t,horizon)),censored:death.map(t=>t>=horizon),horizon};
}
function evaluate(heroes,mode,data,horizon=30){
 if(heroes.length!==5||!data?.pressure)return {available:false,adjustment:0};
 const total=heroes.reduce((v,h)=>v+(h.estimate?.teamPercent?.[2]||0),0);
 const hp=heroes.map(h=>{const e=h.estimate,s=e?.heroStats?.[2];return s*(1+(total-(e?.teamPercent?.[2]||0))/(1+(e?.selfPercent?.[2]||0)+(e?.teamPercent?.[2]||0)));});
 if(hp.some(v=>!Number.isFinite(v)||v<=0))return {available:false,adjustment:0};
 const result=project(hp,data.pressure,data.back_share,horizon),weight=mode==='Offense'?.8875:mode==='Survival'?.1375:mode==='PvE farming'?.5875:.55;
 return {...result,available:true,adjustment:weight*heroes.reduce((v,h,i)=>v+Math.max(0,h.offense_index)*(result.aliveSeconds[i]/horizon-1),0)/5};
}
const api={project,evaluate};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.SurvivalModel=api;
})(globalThis);
