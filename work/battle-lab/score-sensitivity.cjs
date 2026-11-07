'use strict';
const model=require('../HeroPlannerWeb/estimate-model.js');
function ranking(heroes,weights){return heroes.map(h=>({...h,value:weights[0]*h.offense+weights[1]*h.durability+weights[2]*h.utility})).sort((a,b)=>b.value-a.value||a.slug.localeCompare(b.slug));}
function summarize(base,runs){
 const baseline=new Map(base.map((h,i)=>[h.slug,i+1]));
 return {scenarios:runs.length,heroes:base.map(h=>{const ranks=runs.map(r=>r.findIndex(x=>x.slug===h.slug)+1);return {hero:h.slug,baseline_rank:baseline.get(h.slug),best_rank:Math.min(...ranks),worst_rank:Math.max(...ranks),top_five_scenarios:ranks.filter(r=>r<=5).length};}),runs:runs.map(r=>({top_five:r.slice(0,5).map(h=>h.slug)}))};
}
function analyse(upgrades,estimates){
 const vectors=seconds=>Object.keys(estimates.heroes).sort().map(slug=>{const r=model.compare(slug,null,upgrades,estimates,'reference',null,seconds);return {slug,offense:r.offense,durability:r.durability,utility:(r.score-.55*r.offense-.35*r.durability)/.1};});
 const weights=[];for(const o of [.45,.55,.65])for(const u of [.05,.10,.15])weights.push([o,1-o-u,u]);
 const baseline=ranking(vectors(0),[.55,.35,.10]),sensitivity=summarize(baseline,weights.map(w=>ranking(vectors(0),w)));
 sensitivity.runs.forEach((r,i)=>r.weights=weights[i]);
 const windows=[0,10,20,30],timing=summarize(baseline,windows.map(w=>ranking(vectors(w),[.55,.35,.10])));timing.runs.forEach((r,i)=>r.game_seconds=windows[i]||'sustained');
 return {schema:1,model_version:estimates.version,scope:'Global individual hero index sensitivity. Full-access equal maximum T5 builds, no account context or enemy. Not squad rankings: faction composition, team synergy and front-pair placement are excluded. No observed outcome is used to fit weights.',baseline_weights:[.55,.35,.10],weight_sensitivity:sensitivity,timing_sensitivity:timing,ranking_accuracy:null,note:'Rank robustness measures dependence on modeling choices, not combat prediction accuracy. The 9 weight settings are deliberately selected scenarios, not a probability distribution.'};
}
if(require.main===module){const fs=require('fs'),path=require('path'),folder=path.resolve(__dirname,'../../outputs/hero-report'),read=n=>JSON.parse(fs.readFileSync(path.join(folder,n),'utf8'));const result=analyse(read('TilesSurvive-Upgrade-Data.json'),read('Hero-Estimate-Model.json'));fs.writeFileSync(path.join(folder,'Global-Score-Sensitivity.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({weight_scenarios:result.weight_sensitivity.scenarios,baseline:result.weight_sensitivity.runs[4].top_five,top5_in_all_weight_scenarios:result.weight_sensitivity.heroes.filter(h=>h.top_five_scenarios===9).map(h=>h.hero),timing_top5:result.timing_sensitivity.runs}));}
module.exports={analyse,ranking,summarize};
