'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),{execFileSync}=require('node:child_process'),path=require('node:path');
const S=require('../HeroPlannerWeb/survival-model.js'),lab=require('./survival-reconstruction.cjs'),R=require('./reconstruct-damage.cjs');
test('pressure redirects through the front and back groups and conserves the supplied HP budget',()=>{
 assert.deepEqual(S.project([100,100,100,100,100],100,0).deathTimes,[2,2,5,5,5]);
 assert.deepEqual(S.project([100,100,100,100,100],100,1).deathTimes,[5,5,3,3,3]);
 const hp=[100,200,300,400,500],before=[...hp],p=S.project(hp,100,.3,4);
 assert.deepEqual(hp,before);assert.ok(Math.abs(Math.max(...p.deathTimes)-15)<1e-9);assert.equal(p.aliveSeconds.every(t=>t<=4),true);
 assert.ok(p.censored.some(Boolean));assert.deepEqual(S.project(hp.map(v=>v*2),200,.3,4),p);
 assert.deepEqual(S.project([0,0,0,0,0],100,0).deathTimes,[0,0,0,0,0]);
});
test('invalid pressure and missing stat inputs never become invented survival benefits',()=>{
 for(const pressure of [0,-1,NaN,Infinity])assert.throws(()=>S.project([1,1,1,1,1],pressure,.3));
 assert.throws(()=>S.project([1,1,1,1,NaN],100,.3));assert.throws(()=>S.project([1,1,1,1,1],100,-.1));
 assert.equal(S.evaluate(Array.from({length:5},()=>({offense_index:100,estimate:{}})),'Balanced',{pressure:100,back_share:.3}).adjustment,0);
 const heroes=Array.from({length:5},()=>({offense_index:100,estimate:{heroStats:[1,1,100],teamPercent:[0,0,0],selfPercent:[0,0,0]}}));
 const projected=S.evaluate(heroes,'Balanced',{pressure:100,back_share:.3});assert.ok(projected.available&&projected.adjustment<0);
});
test('native and browser pressure predictions agree across finite horizons, ties and zero-HP actors',()=>{
 let seed=1234567;const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
 const cases=Array.from({length:80},(_,i)=>[...Array.from({length:5},()=>i%10===0?0:1+random()*1e7),1+random()*1e6,[0,.05,.3,.7,1][i%5],[10,20,30][i%3]]);
 const root=path.resolve(__dirname,'../..'),native=JSON.parse(execFileSync('dotnet',['run','--no-build','--project',path.join(root,'work/HeroPlanner.Tests'),'--','--survival'],{input:JSON.stringify(cases),encoding:'utf8'}));
 cases.forEach((r,i)=>{const browser=S.project(r.slice(0,5),r[5],r[6],r[7]);for(const k of ['deathTimes','aliveSeconds'])browser[k].forEach((v,j)=>assert.ok(Math.abs(v-native[i][k][j])<1e-9*Math.max(1,v)));assert.deepEqual(browser.censored,native[i].censored);});
});
test('held-owner survival and damage labels cannot fit that owners benchmark prediction',()=>{
 const root='../../outputs/hero-report/',rows=R.features(require(root+'Replay-Observation-2026-11-07.json'),require(root+'Replay-Reconstruction-Inputs-2026-11-07.json'),require(root+'TilesSurvive-Upgrade-Data.json'),require(root+'Hero-Estimate-Model.json'),require(root+'Hero-Army-Context.json')).rows;
 const first=lab.evaluate(rows);assert.ok(first.survival.internal_held_owner.wape<.12);
 for(let i=0;i<rows.length;i++){
  const changed=structuredClone(rows);changed[i].alive_seconds=1000;changed[i].observed=1e12;
  const next=lab.evaluate(changed).folds[i],original=first.folds[i];
  assert.equal(next.predicted,original.predicted);assert.equal(next.attack_damage,original.attack_damage);assert.equal(next.offense_damage,original.offense_damage);assert.deepEqual(next.calibration,original.calibration);
 }
 assert.equal(require(root+'Survival-Reconstruction.json').independent_battle_accuracy,null);
});
