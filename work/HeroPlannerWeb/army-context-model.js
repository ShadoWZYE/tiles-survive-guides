(function(root){
'use strict';
function sanitize(raw={},data={}){
 const selected=(values,catalog)=>Object.fromEntries(Object.entries(values&&typeof values==='object'?values:{}).filter(([k,v])=>Number.isInteger(v)&&Object.hasOwn(catalog||{},k)&&catalog[k].levels.some(r=>r.level===v)));
 const behemothBuilds={};for(const [key,value] of Object.entries(raw?.behemothBuilds||{})){
  if(!Object.hasOwn(data.behemoths||{},key)||!value||typeof value!=='object')continue;
  const entry=data.behemoths[key],level=Number.isInteger(value.level)&&entry.levels.some(r=>r.level===value.level)?value.level:0,
   star=Number.isInteger(value.star)&&entry.stars.some(r=>r.level===value.star)?value.star:0;
  if(level||star)behemothBuilds[key]={level,star};
 }
 return {enabled:raw?.enabled===true,scene:['pve','gve'].includes(raw?.scene)?raw.scene:'all',
  behemothSource:raw?.behemothSource==='configured'?'configured':'manual',behemothBuilds,
  research:selected(raw?.research,data.research),signature:selected(raw?.signature,data.signature),
  behemoth:[0,1,2].map(i=>{const v=raw?.behemoth?.[i];return typeof v==='number'&&Number.isFinite(v)&&v>=0&&v<=1e12?v:null;})};
}
function resolve(slug,raw,data,basis='reference'){
 const s=sanitize(raw,data),flat=[0,0,0],notes=[];
 if(!s.enabled||basis==='flat')return {flat,notes,active:false};
 const hero=data.heroes?.[slug]||{};
 function apply(row,label){
  for(const e of row.effects)if((e.scope==='all'||e.scope===hero.role||e.scope===hero.faction)&&(e.scene==='all'||e.scene===s.scene))flat[e.stat]+=e.value;
  if(row.linked_skill)notes.push(label+': linked skill excluded');
  if(row.unmodeled.length)notes.push(label+': additional effects excluded');
 }
 if(s.behemothSource==='manual')for(let i=0;i<3;i++)flat[i]+=s.behemoth[i]??0;
 else for(const [key,build] of Object.entries(s.behemothBuilds)){
  const entry=data.behemoths[key];for(const row of [entry.levels.find(r=>r.level===build.level),entry.stars.find(r=>r.level===build.star)])if(row)apply(row,entry.name);
  notes.push(entry.name+': level/star stats only; skill, talent and full-skill bonuses excluded');
 }
 for(const [key,n] of Object.entries(s.research))apply(data.research[key].levels.find(r=>r.level===n),data.research[key].name);
 if(basis==='recorded'&&s.signature[slug])apply(data.signature[slug].levels.find(r=>r.level===s.signature[slug]),'Signature Gear');
 return {flat,notes,active:true};
}
const colors=['Green','Blue','Purple','Gold','Red','Red+','Orange','Orange+','Platinum','Platinum+','Rainbow','Rainbow+'];
function starView(count,tiers=12){
 const tier=Math.min(Math.floor(count/30)+1,tiers),full=Math.floor(count/30)+1>tiers;let n=count%30;
 const slots=Array.from({length:5},()=>{const steps=full?6:Math.min(6,n);n=Math.max(0,n-6);return {base:tier-1,overlay:tier,steps};});
 const phase=count>0?Math.floor((count-1)/30)+1:0,star=count>0?Math.floor(((count-1)%30)/6)+1:1,step=count>0?(count-1)%6+1:1;
 return {slots,phase,star,step,label:count===0?'Stars unknown':`${colors[phase-1]||'Advanced phase '+phase} · star ${star} · step ${step}/6`};
}
const api={sanitize,resolve,starView,colors};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ArmyContextModel=api;
})(globalThis);
