(function(root){
  "use strict";
  const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[c]);
  const fmt=v=>Number(v).toLocaleString("en-US",{maximumFractionDigits:4});
  const data=()=>root.__UPGRADE_DATA__;
  const input=(id,value,max)=>`<input id="${id}" type="number" min="0" max="${max}" step="1" placeholder="Unknown" value="${value??''}">`;
  function editor(slug,profile){
    const h=data().heroes[slug],b=profile.heroProgress?.[slug]?.build||{};
    if(!h)return "";
    return `<details class="notice" open><summary><strong>My build · ${esc(h.name)}</strong></summary><p>Enter the exact configured rank/step, not whole stars. Unknown is never assumed maximum. Rank numbers are client identifiers; confirm the matching step and skill caps in-game.</p>
      <div class="control-strip"><label>Rank / step<select id="build-stage"><option value="">Unknown</option>${h.stages.map(s=>`<option value="${esc(s.id)}"${s.id===b.stage?' selected':''}>${s.rank} / ${s.step} · skill caps ${s.skill_caps.join('/')} · max level ${s.level_max}</option>`).join('')}</select></label><label>Hero level${input('build-level',b.level,1000)}</label></div>
      <div class="control-strip">${h.skills.map((s,i)=>`<label>${esc(s.name)}${input('build-skill-'+i,b.skills?.[s.id],1000)}</label>`).join('')}</div>
      <p>Skill level 0 means locked; blank means unknown. Gear is optional. Only universal gear types are supported; profession and exclusive effects are not modeled.</p>
      <label>Gear recording<select id="build-gear-mode"><option value="unknown"${b.gear==null?' selected':''}>Unknown / excluded</option><option value="recorded"${Array.isArray(b.gear)?' selected':''}>Recorded (empty slots mean no gear)</option></select></label>
      <div class="control-strip">${[1,2,3].map(slot=>{const g=b.gear?.find(x=>data().gear[x.id]?.slot===slot);return `<label>Gear slot ${slot}<select id="build-gear-${slot}"><option value="">None</option>${Object.entries(data().gear).filter(([,t])=>t.slot===slot).map(([id,t])=>`<option value="${esc(id)}"${g?.id===id?' selected':''}>${esc(t.name)} · quality ${t.quality}</option>`).join('')}</select>${input('build-gear-level-'+slot,g?.level,1000)}</label>`}).join('')}</div>
      <button class="button" id="save-build">Save build</button><p id="build-error" role="status"></p></details>`;
  }
  function bindEditor(slug,profile,save,render){
    const $=id=>document.getElementById(id),h=data().heroes[slug];
    if(!$('save-build'))return;
    $('save-build').onclick=()=>{
      const fields=[...document.querySelectorAll('[id^="build-"][type="number"]')];
      if(fields.some(x=>!x.reportValidity()))return;
      const num=id=>$(id).value===''?null:Number($(id).value),skills={};
      h.skills.forEach((s,i)=>{const n=num('build-skill-'+i);if(n!==null)skills[s.id]=n;});
      const gear=$('build-gear-mode').value==='recorded'?[1,2,3].filter(s=>$('build-gear-'+s).value).map(s=>({id:$('build-gear-'+s).value,level:num('build-gear-level-'+s)})):null;
      const b={stage:$('build-stage').value||null,level:num('build-level'),skills,gear};
      const clean=UpgradeModel.sanitizeBuild(b,h);
      if(!clean){$('build-error').textContent='Selected gear needs a valid level.';return;}
      if(clean.stage&&clean.level!==null){const check=UpgradeModel.state(slug,clean,data(),30);if(check.error){$('build-error').textContent=check.error;return;}}
      profile.heroProgress[slug]={...profile.heroProgress[slug],build:clean};save();render();
    };
  }
  const labels={power:'Configured power contribution',attack:'Hero ATK total',health:'Hero HP total',defense:'Hero DEF total',direct:'Experimental direct-output potential'};
  function panel(slugs,profile){
    const s=UpgradeModel.sanitizeSettings(profile.upgradeSettings),builds=Object.fromEntries(slugs.map(id=>[id,profile.heroProgress?.[id]?.build]));
    const owned=slugs.filter(id=>profile.ownedHeroes?.includes(id));
    const r=slugs.length===5?UpgradeModel.evaluate(owned,builds,data(),s):null;
    const materials=[...new Set(slugs.flatMap(id=>{const h=data().heroes[id];return h?h.stages.flatMap(x=>Object.keys(x.cost)).concat(h.skills.flatMap(x=>x.levels.flatMap(l=>Object.keys(l.cost)))):[];})), 'hero-xp','gear-xp'];
    let content='<p>Select five heroes in Your squad before comparing upgrades.</p>';
    if(r){
      if(!owned.length)content='<p>Mark the heroes you own before prioritising resources. Comparator assumptions are never used here.</p>';
      else if(r.missing.length)content=`<p>Record these owned builds in My roster first:</p><ul>${r.missing.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`;
      else{
        let group='';content=r.candidates.map(c=>{
          const heading=c.group!==group?`<h4>${esc(data().items[c.group]||c.group||'Multiple / unlisted costs')} · resource ${esc(c.group||'unranked')}</h4>`:'';group=c.group;
          return `${heading}<div class="notice"><strong>${esc(c.label)}</strong><br>${c.blocked?esc(c.blocked):c.gain===null?'Return not modeled':`${fmt(c.gain)}% formation gain · ${c.efficiency===null?'not comparable':fmt(c.efficiency)+'% gain per 100 resource units'}`}<br>Cost: ${Object.entries(c.cost).map(([k,v])=>`${fmt(v)} ${esc(data().items[k]||k)} [${esc(k)}]`).join(' + ')||'Not listed; not assumed free'} · ${esc(c.affordability)}${c.delta?`<br>Stat change: ATK ${fmt(c.delta[0])}, DEF ${fmt(c.delta[1])}, HP ${fmt(c.delta[2])}`:''}<details><summary>Evidence / gates</summary>${esc(c.detail)}</details></div>`;
        }).join('')||'<p>No next upgrades match this filter.</p>';
        content+=`<p>${r.notes.map(esc).join('; ')}</p>`;
      }
    }
    return `<section class="guide-card resource" style="grid-column:1/-1"><h3>Data-driven next upgrades</h3><p>Client ${esc(data().client_build)}. Adjacent upgrades, ranked by gain per cost within each exact material. No fixed hero order. These are stat/contribution comparisons, not a complete battle simulation.</p>
      <div class="control-strip"><label>Return metric<select id="upgrade-goal">${UpgradeModel.goals.filter(g=>g!=="direct").map(g=>`<option value="${g}"${g===s.goal?' selected':''}>${labels[g]}</option>`).join('')}</select></label><label><input id="upgrade-affordable" type="checkbox"${s.onlyAffordable?' checked':''}> Only affordable</label></div>
      <p>Offline native audit invalidated the experimental direct-output ranking: display parameters are not runtime damage coefficients. Complete effects, cast timing and dynamic patches remain unverified. Power is the sum of recorded config contributions, not measured team power. ATK/HP/DEF totals are not damage/survival predictions. Rank unlocks do not grant free skill levels.</p>
      <details><summary>Resource balances (blank = unknown)</summary><div class="control-strip">${materials.map((id,i)=>`<label>${esc(data().items[id]||id)} [${esc(id)}]<input data-material="${esc(id)}" id="budget-${i}" type="number" min="0" max="1000000000000" step="1" placeholder="Unknown" value="${s.inventory[id]??''}"></label>`).join('')}</div></details>
      <button class="button secondary" id="save-upgrade-settings">Apply metric / balances</button><p>Building gates must be checked in-game. XP costs assume zero progress toward the next level. Shard conversions and multi-resource efficiencies are not assumed. Equal returns are ties; alphabetical display order is not an advantage.</p>${content}</section>`;
  }
  function bindPanel(profile,save,render){
    const button=document.getElementById('save-upgrade-settings');if(!button)return;
    button.onclick=()=>{
      const fields=[...document.querySelectorAll('[data-material]')];
      if(fields.some(x=>!x.reportValidity()))return;
      const inventory={...profile.upgradeSettings?.inventory};
      document.querySelectorAll('[data-material]').forEach(x=>{if(x.value==='')delete inventory[x.dataset.material];else inventory[x.dataset.material]=Number(x.value);});
      profile.upgradeSettings=UpgradeModel.sanitizeSettings({goal:document.getElementById('upgrade-goal').value,seconds:profile.upgradeSettings?.seconds,onlyAffordable:document.getElementById('upgrade-affordable').checked,inventory});save();render();
    };
  }
  root.UpgradeUI={editor,bindEditor,panel,bindPanel};
})(globalThis);
