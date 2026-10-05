(function(root) {
  "use strict";
  const goals = ["power","attack","health","defense","direct"];
  const integer = (v,max=1000000) => typeof v==="number" && Number.isInteger(v) && v>=0 && v<=max ? v : null;
  const row = (rows,level) => rows.find(r=>r.level===level);
  function sanitizeBuild(value,data) {
    if(!value || typeof value!=="object") return null;
    const skills={};
    for(const skill of data.skills) {
      const n=integer(value.skills?.[skill.id],1000);
      if(n!==null) skills[skill.id]=n;
    }
    if(Array.isArray(value.gear)&&value.gear.some(g=>!g||typeof g.id!=="string"||integer(g.level,1000)===null))return null;
    const gear=Array.isArray(value.gear) ? value.gear.map(g=>({id:g.id,level:g.level})) : null;
    return {stage:data.stages.some(s=>s.id===value.stage)?value.stage:null,level:integer(value.level,1000),skills,gear};
  }
  function sanitizeSettings(value={}) {
    const inventory={};
    if(value?.inventory && typeof value.inventory==="object")for(const [key,n] of Object.entries(value.inventory))
      if(typeof n==="number"&&Number.isFinite(n)&&n>=0&&n<=1e12)inventory[key]=n;
    return {goal:goals.includes(value?.goal)?value.goal:"power",seconds:integer(value?.seconds,300)||30,inventory,onlyAffordable:value?.onlyAffordable===true};
  }
  function state(slug,build,data,seconds) {
    const h=data.heroes[slug], b=sanitizeBuild(build,h), missing=[];
    if(!b)return {error:"build not recorded"};
    const stage=h.stages.find(s=>s.id===b.stage), level=row(h.levels,b.level);
    if(!stage||!level)return {error:"exact rank step / hero level missing"};
    if(level.level>stage.level_max)return {error:"hero level exceeds this rank's cap"};
    const stats=stage.stats.map((v,i)=>v+level.stats[i]);
    let power=stage.power+level.power;
    const slots=new Set();
    if(b.gear===null)missing.push("gear not recorded (excluded)");
    if(h.skills.some(skill=>b.skills[skill.id]===undefined))missing.push("unrecorded skill power excluded from baseline");
    for(const g of b.gear||[]) {
      const type=data.gear[g.id], entry=type&&row(type.levels,g.level);
      if(!entry||slots.has(type.slot)||type.hero_level_required>b.level)return {error:"invalid, duplicate-slot or level-gated gear"};
      slots.add(type.slot);stats.forEach((_,i)=>stats[i]+=entry.stats[i]);power+=entry.power;
    }
    let direct=0, directKnown=true;
    for(const skill of h.skills) {
      const n=b.skills[skill.id], cap=stage.skill_caps[skill.slot]??0;
      if(n!==undefined && (n>cap || (n>0&&!row(skill.levels,n))))return {error:`${skill.name}: level exceeds cap or is absent from data`};
      if(skill.effect_type!==1 || !skill.damage_params.length || skill.conditional || skill.cooldown<=0)continue;
      if(n===undefined){directKnown=false;continue;}
      if(n===0)continue;
      const coeff=skill.damage_ratio*(skill.damage_params[0]+(skill.damage_params[1]||0)*(n-1));
      const window=seconds*1000;
      const casts=window>skill.first_cast?Math.ceil((window-skill.first_cast)/skill.cooldown):0;
      direct+=stats[0]*coeff*casts;
    }
    for(const skill of h.skills) {
      const n=b.skills[skill.id];
      if(n>0)power+=row(skill.levels,n)?.power||0;
    }
    return {build:b,stage,level,stats,power,direct:directKnown?direct:null,missing};
  }
  function evaluate(slugs,builds,data,settings={}) {
    settings=sanitizeSettings(settings);
    const unique=[...new Set(slugs)].filter(s=>data.heroes[s]);
    const states=new Map(unique.map(s=>[s,state(s,builds[s],data,settings.seconds)]));
    const missing=[...states].filter(([,s])=>s.error).map(([slug,s])=>`${data.heroes[slug].name}: ${s.error}`);
    const result={candidates:[],missing,notes:[],baseline:null,goal:settings.goal};
    if(missing.length||!unique.length)return result;
    const statTotals=[0,0,0];let totalPower=0,totalDirect=0,directKnown=true;
    for(const s of states.values()){statTotals.forEach((_,i)=>statTotals[i]+=s.stats[i]);totalPower+=s.power;if(s.direct===null)directKnown=false;else totalDirect+=s.direct;}
    result.baseline={stats:statTotals,power:totalPower,direct:directKnown?totalDirect:null};
    result.notes=[...new Set([...states.values()].flatMap(s=>s.missing))];
    const metric=s=>settings.goal==="power"?s.power:settings.goal==="direct"?s.direct:s.stats[{attack:0,defense:1,health:2}[settings.goal]];
    const base=settings.goal==="power"?totalPower:settings.goal==="direct"?(directKnown?totalDirect:null):statTotals[{attack:0,defense:1,health:2}[settings.goal]];
    const add=(slug,label,kind,after,cost,detail,blocked=null,unsupported=false)=>{
      const before=states.get(slug), next=state(slug,after,data,settings.seconds);
      let gain=null;
      if(!next.error&&base!==null&&base>0&&!unsupported&&metric(next)!==null&&metric(before)!==null)gain=(metric(next)-metric(before))/base*100;
      const positive=Object.entries(cost||{}).filter(([,v])=>Number.isFinite(v)&&v>0);
      const known=positive.length>0&&positive.every(([key])=>settings.inventory[key]!==undefined);
      const affordability=known?(positive.every(([key,n])=>settings.inventory[key]>=n)?"affordable":"insufficient"):"unknown";
      const group=positive.length===1?positive[0][0]:null;
      const efficiency=gain!==null&&group&&!blocked&&!next.error?gain/positive[0][1]*100:null;
      result.candidates.push({slug,label,kind,cost:Object.fromEntries(positive),group,gain,efficiency,affordability,
        detail,blocked:blocked||next.error||null,unsupported,delta:!next.error?next.stats.map((n,i)=>n-before.stats[i]):null});
    };
    for(const [slug,s] of states){
      const h=data.heroes[slug], nextStage=h.stages[h.stages.findIndex(x=>x.id===s.stage.id)+1];
      if(nextStage)add(slug,`${h.name}: rank ${s.stage.rank}/${s.stage.step} → ${nextStage.rank}/${nextStage.step}`,"rank",
        {...s.build,stage:nextStage.id},nextStage.cost,`Skill caps: ${nextStage.skill_caps.join("/")}. Unlocks: ${nextStage.unlocks||"none listed"}. Building requirement: ${nextStage.building_required} (check in-game).`,
        s.build.level<nextStage.level_required?`Requires hero level ${nextStage.level_required}`:null);
      const nextLevel=row(h.levels,s.build.level+1);
      if(nextLevel){const xp=nextLevel.xp_total!==null&&s.level.xp_total!==null?nextLevel.xp_total-s.level.xp_total:null;
        add(slug,`${h.name}: level ${s.build.level} → ${nextLevel.level}`,"level",{...s.build,level:nextLevel.level},xp>0?{"hero-xp":xp}:{},
          `Building gate ID ${nextLevel.building_gate}; check in-game. Cost assumes zero XP toward the next level.`,nextLevel.level>s.stage.level_max?"Rank level cap reached":null);}
      for(const skill of h.skills){
        const n=s.build.skills[skill.id], cap=s.stage.skill_caps[skill.slot]??0;
        if(n===undefined){result.notes.push(`${h.name}: ${skill.name} level missing`);continue;}
        const next=row(skill.levels,n+1);
        if(!next)continue;
        const supported=skill.effect_type===1&&skill.damage_params.length>0&&!skill.conditional&&skill.cooldown>0;
        // Utility/conditional skills retain their cost and changed parameters, not an invented zero payoff.
        add(slug,`${h.name}: ${skill.name} ${n} → ${n+1}`,"skill",{...s.build,skills:{...s.build.skills,[skill.id]:n+1}},next.cost,
          `SlgItemReq material cost. ${supported?"Affine direct-output estimate; ignores animation hit counts, movement and mitigation.":"Runtime utility / conditional effect not simulated."} ${next.params.join("; ")}`,
          n+1>cap?`Needs a higher rank (current skill cap ${cap})`:null,settings.goal==="direct"&&!supported);
      }
      for(const g of s.build.gear||[]){const type=data.gear[g.id], current=row(type.levels,g.level), next=row(type.levels,g.level+1);
        if(next)add(slug,`${h.name}: ${type.name} ${g.level} → ${g.level+1}`,"gear",{...s.build,gear:s.build.gear.map(x=>x.id===g.id?{...x,level:x.level+1}:x)},
          current.xp_next>0?{"gear-xp":current.xp_next}:{},"Gear level only; enhancement / refinement / exclusive-gear effects excluded. Cost assumes zero XP toward next level.");}
    }
    result.candidates.sort((a,b)=>(a.group||"~").localeCompare(b.group||"~")||(b.efficiency??-Infinity)-(a.efficiency??-Infinity)||a.label.localeCompare(b.label));
    result.notes=[...new Set(result.notes)];
    if(settings.onlyAffordable)result.candidates=result.candidates.filter(c=>c.affordability==="affordable"&&!c.blocked);
    return result;
  }
  const api={sanitizeBuild,sanitizeSettings,state,evaluate,goals};
  if(typeof module!=="undefined"&&module.exports)module.exports=api;else root.UpgradeModel=api;
})(typeof globalThis!=="undefined"?globalThis:this);
