(function(root){'use strict';
 const modes=['Balanced','Offense','Survival','PvE farming'];
 function clean(input,known){const available=new Set(known),used=new Set();return Array.from({length:5},(_,i)=>{const raw=Array.isArray(input)?input[i]:null,heroes=[];for(const slug of Array.isArray(raw?.heroes)?raw.heroes:[]){if(typeof slug==='string'&&available.has(slug)&&!used.has(slug)&&heroes.length<5){heroes.push(slug);used.add(slug);}}return {heroes,mode:modes.includes(raw?.mode)?raw.mode:'Balanced'};});}
 function blocked(armies,active){return new Set(armies.flatMap((a,i)=>i===active?[]:a.heroes));}
 function owner(armies,slug){return armies.findIndex(a=>a.heroes.includes(slug));}
 function index(value){return Number.isInteger(value)&&value>=0&&value<5?value:0;}
 const api={clean,blocked,owner,index};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ArmyRoster=api;
})(globalThis);
