(() => {
  "use strict";

  const STORAGE_KEY = "tiles-survive-hero-planner-profile-v1";
  const DEFAULT_PROFILE = {
    version: 1,
    comparisonBasis: "reference",
    ownedHeroes: [],
    heroProgress: {},
    upgradeSettings: {},
    serverOpenDate: "2026-09-02",
    mode: "Balanced",
    access: "All access",
    requireRoleCoverage: true,
    leftWidth: 58
  };
  const $ = selector => document.querySelector(selector);
  const $$ = selector => [...document.querySelectorAll(selector)];
  const esc = value => String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[char]);
  const number = value => Number(value || 0).toLocaleString("en-US", {maximumFractionDigits: 1});
  const heroes = window.__HERO_DATA__.map(normalizeHero)
    .sort((a, b) => b.composite_index - a.composite_index || a.name.localeCompare(b.name));
  const bySlug = new Map(heroes.map(hero => [hero.asset_slug, hero]));
  const flatIndices = new Map(heroes.map(h=>[h.asset_slug,{offense:h.offense_index,durability:h.durability_index,score:h.composite_index}]));
  let profile = loadProfile();
  let state = {
    tab: "squad",
    active: heroes[0].asset_slug,
    squad: (window.__INITIAL_SQUAD__||[]).filter(slug=>bySlug.has(slug)).slice(0,5),
    faction: "All factions",
    role: "All roles",
    rarity: "All rarities",
    releaseActive: null
  };
  let optimizerCache = new Map();
  let suppressCardClickUntil = 0;

  const activeHero = () => bySlug.get(state.active) || heroes[0];
  const owned = hero => profile.ownedHeroes.includes(hero.asset_slug);

  function normalizeHero(hero) {
    hero.skills = (hero.skills || []).map(skill => ({...skill, mechanics: mechanicsFor(skill), payoff: payoffFor(skill)}));
    hero.mechanics = new Set(hero.skills.flatMap(skill => skill.mechanics));
    hero.staminaReduction = Math.max(0, ...hero.skills.flatMap(skill => skill.max_level_overall_benefits || [])
      .filter(item => item.name === "prop_intel_stamina_reduce_percent").map(item => Math.abs(item.value) * 100));
    return hero;
  }

  function mechanicsFor(skill) {
    const source = `${(skill.raid_level_parameters || []).join("|")}|${skill.squad_parameter_map || ""}|${skill.game_description || ""}`.toLowerCase();
    const tests = [
      ["summon", "Summon"], ["heal", "Healing"], ["shield", "Shield"], ["stun", "Stun"],
      ["speeddown", "Slow"], ["weaken_team_atk", "ATK reduction"], ["weaken_team_def", "DEF reduction"],
      ["weaken_enemy_def", "DEF reduction"],
      ["weaken_enemy_atk", "ATK reduction"],
      ["dmg_dec", "Damage reduction"], ["inc_dmg", "Damage boost"], ["crit", "Critical effect"],
      ["stamina", "Stamina reduction"], ["hpmax", "Maximum health"]
    ];
    const result = [...new Set(tests.filter(([needle]) => source.includes(needle)).map(([, label]) => label))];
    if (!result.length && (skill.normal_attack || source.includes("damage"))) result.push("Damage");
    return result.length ? result : ["Mechanic not yet classified"];
  }

  function payoffFor(skill) {
    const mechanics = mechanicsFor(skill);
    if (skill.normal_attack) return "Reliable basic damage; mostly a baseline rather than a reason to build the hero.";
    if (mechanics.includes("Healing") && mechanics.includes("Shield")) return "Strong sustain package: restores health and prevents follow-up damage.";
    if (mechanics.includes("Healing")) return "Sustain value rises in longer fights and when the squad survives long enough for repeated casts.";
    if (mechanics.includes("Shield") || mechanics.includes("Damage reduction")) return "Protective value is highest for keeping fragile damage dealers active.";
    if (mechanics.includes("Stun") || mechanics.includes("Slow")) return "Control creates safer damage windows and reduces incoming pressure; payoff depends on effect uptime.";
    if (mechanics.includes("ATK reduction") || mechanics.includes("DEF reduction")) return "Team utility: weakens enemies so the whole squad either takes less damage or deals more.";
    if (mechanics.includes("Stamina reduction")) {
      const reduction = Math.max(0, ...(skill.max_level_overall_benefits || []).filter(item => item.name === "prop_intel_stamina_reduce_percent").map(item => Math.abs(item.value) * 100));
      return reduction ? `Global PvE economy: the extracted maximum benefit reduces Stamina consumption by ${number(reduction)}%, allowing more farming from the same daily resource.` : "Global PvE economy: lowers Stamina spent per action.";
    }
    if (mechanics.includes("Summon")) return "Adds another battlefield source of pressure; practical value depends on summon uptime and survivability.";
    return "The client exposes this effect, but its practical payoff needs a fuller battle-effect simulation.";
  }

  function loadProfile() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
      if (parsed && typeof parsed === "object") return sanitizeProfile(parsed);
    } catch (_) {}
    return {...DEFAULT_PROFILE};
  }

  function sanitizeProfile(candidate) {
    const ownedHeroes = Array.isArray(candidate.ownedHeroes) ? candidate.ownedHeroes.filter(slug => bySlug.has(slug)) : [];
    const allowedModes = ["Balanced", "Offense", "Survival", "PvE farming"];
    const allowedAccess = ["All access", "F2P confirmed", "F2P + events", "IAP-linked", "Owned only"];
    const heroProgress=FormationPriority.sanitizeProgress(candidate.heroProgress, bySlug.keys());
    for(const [slug,h] of Object.entries(window.__UPGRADE_DATA__?.heroes||{})) {
      const build=UpgradeModel.sanitizeBuild(candidate.heroProgress?.[slug]?.build,h);
      if(build)heroProgress[slug]={...heroProgress[slug],build};
    }
    return {
      version: 1,
      comparisonBasis: ["flat","recorded"].includes(candidate.comparisonBasis)?candidate.comparisonBasis:"reference",
      ownedHeroes: [...new Set(ownedHeroes)],
      heroProgress,
      upgradeSettings: UpgradeModel.sanitizeSettings(candidate.upgradeSettings),
      serverOpenDate: /^\d{4}-\d{2}-\d{2}$/.test(candidate.serverOpenDate || "") ? candidate.serverOpenDate : DEFAULT_PROFILE.serverOpenDate,
      mode: allowedModes.includes(candidate.mode) ? candidate.mode : DEFAULT_PROFILE.mode,
      access: allowedAccess.includes(candidate.access) ? candidate.access : DEFAULT_PROFILE.access,
      requireRoleCoverage: candidate.requireRoleCoverage !== false,
      leftWidth: Math.min(72, Math.max(38, Number(candidate.leftWidth) || DEFAULT_PROFILE.leftWidth))
    };
  }

  function saveProfile() {
    profile = sanitizeProfile(profile);
    document.documentElement.style.setProperty("--left", `${profile.leftWidth}%`);
    const status = $("#save-status");
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
      status.textContent = "Saved in this browser";
      status.style.color = "var(--good)";
    } catch (_) {
      status.textContent = "Browser save unavailable — export profile";
      status.style.color = "var(--danger)";
    }
  }

  function setProfile(next) {
    profile = sanitizeProfile(next);
    optimizerCache.clear();
    saveProfile();
    renderAll();
  }

  function exportProfile() {
    const blob = new Blob([JSON.stringify(profile, null, 2)], {type: "application/json"});
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "Tiles-Survive-Hero-Planner-Profile.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function importProfile(file) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(String(reader.result));
        if (!parsed || typeof parsed !== "object" || !Array.isArray(parsed.ownedHeroes)) throw new Error("Not a planner profile");
        setProfile(parsed);
        alert("Profile imported.");
      } catch (error) {
        alert(`That file is not a valid Hero Planner profile.\n\n${error.message}`);
      }
    };
    reader.readAsText(file);
  }

  function matchesFilters(hero) {
    return (state.faction === "All factions" || hero.faction === state.faction)
      && (state.role === "All roles" || hero.role === state.role)
      && (state.rarity === "All rarities" || hero.rarity === state.rarity);
  }

  function matchesAccess(hero, access = profile.access) {
    if (access === "Owned only") return owned(hero);
    if (access === "F2P confirmed") return hero.acquisition_class === "f2p_confirmed";
    if (access === "F2P + events") return ["f2p_confirmed", "event_mixed"].includes(hero.acquisition_class);
    if (access === "IAP-linked") return Boolean(hero.iap_linked);
    return true;
  }

  function renderCards() {
    const visible = heroes.filter(matchesFilters);
    $("#hero-grid").innerHTML = visible.map(hero => {
      const selected = state.squad.includes(hero.asset_slug);
      const own = owned(hero);
      return `<button class="hero-card${selected ? " selected" : ""}" data-slug="${esc(hero.asset_slug)}" data-rarity="${esc(hero.rarity)}" aria-label="${esc(hero.name)}${own ? ", owned" : ""}">
        <img src="${hero.portrait_data}" alt="${esc(hero.name)}" draggable="false">
        <span class="rarity">${esc(hero.rarity)}</span>${hero.has_ascension ? '<span class="asc">ASC</span>' : ''}${own ? '<span class="owned-badge" title="Owned">✓</span>' : ''}
        <span class="card-copy"><strong>${esc(hero.name)}</strong><small>${esc(hero.faction)} · ${esc(hero.role)}</small><small class="index" title="${esc(hero.estimate?.basis)}">${profile.comparisonBasis==='flat'?'Stats':'Est.'} ${number(hero.composite_index)}</small></span>
      </button>`;
    }).join("") || '<div class="empty-state">No heroes match these filters.</div>';
    $$(".hero-card").forEach(card => card.addEventListener("click", () => {
      if (performance.now() < suppressCardClickUntil) return;
      const hero = bySlug.get(card.dataset.slug);
      if (state.tab === "release") state.releaseActive = hero.asset_slug;
      else state.active = hero.asset_slug;
      if (state.tab === "release") {}
      else if (state.tab === "roster") {} // Select for editing; the explicit owned button changes ownership.
      else if (state.tab === "squad") toggleSquad(hero);
      renderCards();
      renderDetail();
    }));
  }

  function toggleSquad(hero) {
    const found = state.squad.indexOf(hero.asset_slug);
    if (found >= 0) state.squad.splice(found, 1);
    else if (state.squad.length < 5) state.squad.push(hero.asset_slug);
    state.squad = orderFormation(state.squad.map(slug => bySlug.get(slug)), profile.mode).map(item => item.asset_slug);
  }

  function toggleOwned(hero) {
    profile.ownedHeroes = owned(hero) ? profile.ownedHeroes.filter(slug => slug !== hero.asset_slug) : [...profile.ownedHeroes, hero.asset_slug];
    optimizerCache.clear();
    saveProfile();
  }

  function scoreHero(hero, mode = profile.mode) {
    if(profile.comparisonBasis==='flat')return mode==='Offense'?hero.offense_index:mode==='Survival'?hero.durability_index:hero.composite_index;
    if (mode === "Offense") return hero.offense_index * .75 + hero.composite_index * .25;
    if (mode === "Survival") return hero.durability_index * .75 + hero.composite_index * .25;
    if (mode === "PvE farming") return hero.offense_index * .45 + hero.durability_index * .30 + hero.composite_index * .25 + Math.min(40, hero.staminaReduction * 1.3);
    return hero.composite_index;
  }

  function orderFormation(items, mode = profile.mode) {
    const roleOrder = {Melee: 0, Mid: 1, Range: 2};
    return [...items].sort((a, b) => {
      const band = (roleOrder[a.role] ?? 3) - (roleOrder[b.role] ?? 3);
      if (band) return band;
      const av = a.role === "Melee" ? a.durability_index : a.role === "Range" ? a.offense_index : scoreHero(a, mode);
      const bv = b.role === "Melee" ? b.durability_index : b.role === "Range" ? b.offense_index : scoreHero(b, mode);
      return bv - av || a.name.localeCompare(b.name);
    });
  }

  function evaluateSynergy(squad, includeSummary = true) {
    if(profile.comparisonBasis==='flat')return {bonus:0,summary:'Flat stats: skill synergy excluded'};
    const has = mechanic => squad.some(hero => hero.mechanics.has(mechanic));
    const providers = mechanic => squad.filter(hero => hero.mechanics.has(mechanic)).slice(0, 2).map(hero => hero.name).join("/");
    const carries = () => [...squad].sort((a, b) => b.offense_index - a.offense_index).slice(0, 2).map(hero => hero.name).join("/");
    const interactions = [];
    let bonus = 0;
    if (has("DEF reduction")) { bonus += ({Offense:1.2,Survival:.8,"PvE farming":1.1}[profile.mode] ?? 1); interactions.push(`${providers("DEF reduction")} DEF break → ${carries()}`); }
    const sustain = has("Healing") || has("Shield") || has("Damage reduction");
    if (has("ATK reduction") && sustain) { bonus += ({Survival:1.2,Offense:.7,"PvE farming":1}[profile.mode] ?? .9); interactions.push(`${providers("ATK reduction")} ATK down + sustain`); }
    if (has("Healing") && (has("Shield") || has("Damage reduction"))) { bonus += ({Survival:1.5,Offense:.8,"PvE farming":1.2}[profile.mode] ?? 1.1); interactions.push(`${providers("Healing")} healing + ${providers(has("Shield") ? "Shield" : "Damage reduction")} protection`); }
    const control = has("Stun") || has("Slow");
    if (control) {
      const count = squad.filter(hero => hero.mechanics.has("Stun") || hero.mechanics.has("Slow")).length;
      bonus += ({Offense:.8,Survival:.8,"PvE farming":.6}[profile.mode] ?? .7) + Math.min(.3, Math.max(0, count - 1) * .15);
      interactions.push(`${squad.filter(hero => hero.mechanics.has("Stun") || hero.mechanics.has("Slow")).slice(0,2).map(hero => hero.name).join("/")} control → ${carries()} damage window`);
    }
    if (has("Damage boost") || has("Critical effect")) {
      const supporters = squad.filter(hero => hero.mechanics.has("Damage boost") || hero.mechanics.has("Critical effect"));
      bonus += ({Offense:1.2,Survival:.6,"PvE farming":1}[profile.mode] ?? .9) + Math.min(.3, Math.max(0, supporters.length - 1) * .15);
      interactions.push(`${supporters.slice(0,2).map(hero => hero.name).join("/")} offense support → ${carries()}`);
    }
    if (has("Summon") && (control || has("DEF reduction") || has("Damage boost") || has("Critical effect"))) { bonus += .35; interactions.push(`${providers("Summon")} summon + team utility`); }
    if (profile.mode === "PvE farming") {
      const stamina = [...squad].sort((a,b) => b.staminaReduction - a.staminaReduction)[0];
      if (stamina?.staminaReduction) interactions.unshift(`${stamina.name} −${number(stamina.staminaReduction)}% Stamina cost`);
    }
    bonus = Math.min(6, bonus);
    return {bonus, summary: !includeSummary ? "" : interactions.length ? interactions.slice(0,3).join(" · ") + (interactions.length > 3 ? ` · +${interactions.length - 3} more` : "") : "No modeled cross-skill pairing"};
  }

  function findTopSquads(pool, limit = 20, roleCoverage = profile.requireRoleCoverage) {
    const key = `${pool.map(hero => hero.asset_slug).join(",")}|${profile.mode}|${roleCoverage}|${limit}`;
    if (optimizerCache.has(key)) return optimizerCache.get(key);
    const best = [];
    for (let a=0;a<pool.length-4;a++) for(let b=a+1;b<pool.length-3;b++) for(let c=b+1;c<pool.length-2;c++) for(let d=c+1;d<pool.length-1;d++) for(let e=d+1;e<pool.length;e++) {
      const squad = [pool[a],pool[b],pool[c],pool[d],pool[e]];
      if (roleCoverage && new Set(squad.map(hero => hero.role)).size < 3) continue;
      const base = squad.reduce((sum, hero) => sum + scoreHero(hero), 0) / 5;
      const synergy = evaluateSynergy(squad, false).bonus;
      const item = {heroes: orderFormation(squad), base, synergy, score: base + synergy};
      if (best.length < limit || item.score > best[best.length-1].score) {
        best.push(item); best.sort((x,y) => y.score - x.score || x.heroes.map(h=>h.name).join().localeCompare(y.heroes.map(h=>h.name).join()));
        if (best.length > limit) best.pop();
      }
    }
    best.forEach(item => item.summary = evaluateSynergy(item.heroes).summary);
    optimizerCache.set(key, best);
    return best;
  }

  function heroHeader(hero) {
    const details=profile.comparisonBasis==='flat'?'Flat maximum configuration stats only. Saved stars, levels, skills, gear and ownership are ignored. Identical stats legitimately tie. Skill and synergy weights are excluded.':`${esc(hero.estimate?.basis)} · low confidence · scenario range ${number(hero.estimate?.low)}–${number(hero.estimate?.high)}. Equal builds uses level 110, rank 3 step 6, capped skills and no gear for everyone. ONLY My builds uses your saved progression; unknown fields then use reference defaults. Equal development is not equal resource cost. Representative effects and inferred utility form a planning proxy, not a combat simulation. Scenario factors: damage 0.5–2.5×, utility 0.5–1.5×; not statistical confidence intervals. Fixed reference anchors allow scores above 100. Server overrides remain unverified.`;
    return `<div class="section-head"><div><h2>${esc(hero.name)}</h2><p>${esc(hero.rarity)} · ${esc(hero.faction)} · ${esc(hero.role)} · ${esc(hero.has_ascension ? "Ascension available" : "Base form")}</p></div></div><details><summary>Estimate details</summary><p>${details}</p><p>Resource priorities independently use actual recorded builds of owned heroes.</p></details>`;
  }

  function renderDetail() {
    $$(".top-nav [data-tab]").forEach(button => button.classList.toggle("active", button.dataset.tab === state.tab));
    const titles = {squad:["Hero roster","Click heroes to build a five-hero formation."],stats:["Choose a hero","Click a card to inspect extracted maximum stats."],skills:["Choose a hero","Click a card to inspect skills, icons, and modeled payoff."],roster:["My roster","Select a hero to record its build; use its owned button to change ownership."],release:["Release roster","Click a hero for its release and access evidence."]};
    $("#roster-title").textContent = titles[state.tab][0]; $("#roster-hint").textContent = titles[state.tab][1];
    if (state.tab === "squad") renderSquad();
    else if (state.tab === "stats") renderStats();
    else if (state.tab === "skills") renderSkills();
    else if (state.tab === "roster") renderRoster();
    else renderRelease();
  }

  function renderSquad() {
    const selected = state.squad.map(slug => bySlug.get(slug));
    const complete = selected.length === 5;
    const results = complete ? [] : findTopSquads(heroes.filter(hero => matchesAccess(hero)));
    const planning = complete ? renderFormationGuide(selected) : `<div class="control-strip"><label>Battle focus<select id="mode"><option>Balanced</option><option>Offense</option><option>Survival</option><option>PvE farming</option></select></label><label>Hero access<select id="access"><option>All access</option><option>F2P confirmed</option><option>F2P + events</option><option>IAP-linked</option><option>Owned only</option></select></label><label class="check-label"><input id="role-coverage" type="checkbox"> All 3 roles</label></div>
      <h3>Top configurations</h3><p class="evidence">${results.length ? `${results.length} highest-scoring squads · click one to load it` : "No valid five-hero squad for this access filter."}</p>
      <div class="result-list">${results.map((result,i) => `<button class="result" data-index="${i}"><span class="result-line"><span class="rank">#${i+1}</span><span>${result.heroes.map(h=>esc(h.name)).join(" · ")}</span><span class="score">${number(result.score)}</span></span><span class="synergy">+${number(result.synergy)} synergy · ${esc(result.summary)}</span></button>`).join("")}</div>`;
    $("#detail-content").innerHTML = `<div class="section-head"><div><h2>Your squad</h2><p>${selected.length} / 5 selected · formation shown front-to-back</p></div><button class="button secondary" id="clear-squad">Clear</button></div>
      <div class="squad-slots">${[0,1,2,3,4].map(i => selected[i] ? `<div class="slot"><img src="${selected[i].portrait_data}" alt=""><b>${esc(selected[i].name)}</b><small>${esc(selected[i].role)} · position ${i+1}</small></div>` : '<div class="slot empty">Empty</div>').join("")}</div>
      ${planning}`;
    $("#clear-squad").onclick = () => {state.squad=[];renderCards();renderDetail()};
    UpgradeUI.bindPanel(profile,saveProfile,renderDetail);
    if (complete) $("#formation-mode").onchange = event => {profile.mode=event.target.value;optimizerCache.clear();saveProfile();renderDetail()};
    if (!complete) {
      $("#mode").value = profile.mode; $("#access").value = profile.access; $("#role-coverage").checked = profile.requireRoleCoverage;
      $("#mode").onchange = event => {profile.mode=event.target.value; optimizerCache.clear(); state.squad=orderFormation(selected).map(h=>h.asset_slug); saveProfile();renderDetail()};
      $("#access").onchange = event => {profile.access=event.target.value; optimizerCache.clear();saveProfile();renderDetail()};
      $("#role-coverage").onchange = event => {profile.requireRoleCoverage=event.target.checked;optimizerCache.clear();saveProfile();renderDetail()};
      $$(".result").forEach(button => button.onclick = () => {state.squad=results[Number(button.dataset.index)].heroes.map(h=>h.asset_slug);renderCards();renderDetail()});
    }
  }

  function renderFormationGuide(squad) {
    const base = squad.reduce((sum, hero) => sum + scoreHero(hero), 0) / 5;
    const synergy = evaluateSynergy(squad);
    const carries = FormationPriority.carries(squad);
    const sustain = squad.filter(hero => ["Healing","Shield","Damage reduction"].some(mechanic => hero.mechanics.has(mechanic)));
    const control = squad.filter(hero => hero.mechanics.has("Stun") || hero.mechanics.has("Slow"));
    const debuff = squad.filter(hero => hero.mechanics.has("ATK reduction") || hero.mechanics.has("DEF reduction"));
    const positions = squad.map((hero,index) => `<li><strong>${index+1}. ${esc(hero.name)}</strong><span>${esc(hero.role)} · ${esc(positionJob(hero,carries))}</span></li>`).join("");
    const functionParts = [`Modeled damage core: ${carries.map(hero=>hero.name).join(" and ")}. This is not a measured DPS ranking.`];
    if (debuff.length) functionParts.push(`${debuff.slice(0,2).map(hero=>hero.name).join("/")} weakens targets before the main damage window.`);
    if (control.length) functionParts.push(`${control.slice(0,2).map(hero=>hero.name).join("/")} creates control windows.`);
    if (sustain.length) functionParts.push(`${sustain.slice(0,2).map(hero=>hero.name).join("/")} keeps the formation active through longer exchanges.`);
    const battle = [];
    if (debuff.length) battle.push("Open on one priority target so every follow-up hit benefits from the debuffs");
    if (control.length) battle.push("commit burst while control is active instead of splitting damage");
    if (sustain.length) battle.push("keep the frontline together so protection covers the carries");
    if (profile.mode === "PvE farming" && squad.some(hero=>hero.staminaReduction)) battle.push("use this formation for repeated PvE actions to exploit its Stamina reduction");
    const gaps=[];
    ["Melee","Mid","Range"].forEach(role=>{if(!squad.some(hero=>hero.role===role))gaps.push(`no ${role.toLowerCase()} hero`)});
    if(!sustain.length)gaps.push("no extracted healing, shield, or damage-reduction layer");
    if(!control.length)gaps.push("no extracted stun or slow");
    if(!squad.some(hero=>hero.mechanics.has("DEF reduction")))gaps.push("no extracted defense break for burst damage");
    if(profile.mode==="PvE farming"&&!squad.some(hero=>hero.staminaReduction))gaps.push("no extracted Stamina economy effect");
    return `<section class="formation-guide"><div class="formation-banner"><span>Formation ready</span><strong>${esc(profile.mode)} formation</strong><small>Modeled score ${number(base+synergy.bonus)} · ${number(base)} base + ${number(synergy.bonus)} synergy</small><em>Click a selected hero on the left to revise the squad.</em></div>
      <div class="control-strip"><label>Formation goal<select id="formation-mode">${["Balanced","Offense","Survival","PvE farming"].map(m=>`<option${m===profile.mode?' selected':''}>${m}</option>`).join("")}</select></label></div>
      <div class="guide-grid"><article class="guide-card"><h3>Placement · front to back</h3><ol>${positions}</ol></article><article class="guide-card"><h3>How it functions</h3><p>${esc(functionParts.join(" "))}</p><small>${esc(synergy.summary)}</small></article><article class="guide-card"><h3>Battle guide</h3><p>${esc(battle.length ? `${battle.join("; then ")}.` : "Focus one target at a time and protect your damage core.")}</p></article>${UpgradeUI.panel(squad.map(h=>h.asset_slug),profile)}<article class="guide-card watch"><h3>Watch for</h3><p>${esc(gaps.length ? `Main modeled gaps: ${gaps.slice(0,3).join("; ")}.` : "No obvious structural gap in the extracted roles and mechanics. Exact cooldowns, targeting, gear, and live balance can still change performance.")}</p></article></div></section>`;
  }

  function positionJob(hero,carries) {
    if(hero.role==="Melee")return hero.mechanics.has("Shield")||hero.mechanics.has("Damage reduction")?"absorb pressure and protect the line":"hold the frontline";
    if(carries.includes(hero))return "priority damage carry";
    if(hero.mechanics.has("Healing"))return "sustain the squad";
    if(hero.mechanics.has("Stun")||hero.mechanics.has("Slow"))return "set up the damage window";
    if(hero.mechanics.has("ATK reduction")||hero.mechanics.has("DEF reduction"))return "apply team-wide enemy pressure";
    return "support the core rotation";
  }

  function starQueue(squad) {
    const plan = FormationPriority.starPlan(squad, profile.mode, profile.heroProgress);
    const pending = plan.filter(x=>x.status==="pending").map(x=>`${x.hero.name} ${x.current}★ → ${x.target}★`);
    const unknown = plan.filter(x=>x.status==="unknown").map(x=>x.hero.name);
    const reached = plan.filter(x=>x.status==="reached").map(x=>x.hero.name);
    return [pending.length ? `Planned order: ${pending.join("; ")}.` : "No pending star targets recorded.",
      unknown.length ? `Not assessed (missing stars/target): ${unknown.join(", ")}.` : "",
      reached.length ? `Target reached: ${reached.join(", ")}.` : "",
      "Check the next skill unlock and shard cost in-game; stars do not rescale the modeled squad score."].filter(Boolean).join(" ");
  }

  function renderStats() {
    const hero = activeHero();
    $("#detail-content").innerHTML = `${heroHeader(hero)}<div class="hero-detail"><img class="portrait-large" src="${hero.portrait_data}" alt="${esc(hero.name)}"><div><div class="stat-grid"><div class="stat wide"><small>Max-level battle power</small><strong>${number(hero.max_level_battle_power)}</strong></div><div class="stat"><small>Attack</small><strong>${number(hero.max_level_attack)}</strong></div><div class="stat"><small>Defense</small><strong>${number(hero.max_level_defense)}</strong></div><div class="stat"><small>Health</small><strong>${number(hero.max_level_health)}</strong></div><div class="stat"><small>March capacity</small><strong>${number(hero.max_level_march_capacity)}</strong></div><div class="stat"><small>Estimated offense</small><strong>${number(hero.offense_index)}</strong></div><div class="stat"><small>Estimated durability</small><strong>${number(hero.durability_index)}</strong></div></div><p class="evidence">ATK/DEF/HP and power above are maximum configuration values. Estimated components use recorded builds plus reference assumptions.</p></div></div>`;
  }

  function renderSkills() {
    const hero = activeHero();
    $("#detail-content").innerHTML = `${heroHeader(hero)}<div class="skill-list">${hero.skills.map(skill => `<article class="skill-card">${skill.icon_data ? `<img src="${skill.icon_data}" alt="">` : '<div></div>'}<div><h3>${esc(skill.display_name || (skill.normal_attack ? "Basic attack" : `Skill ${skill.slot}`))}</h3><span class="tags">${esc(skill.mechanics.join(" · "))} · ${skill.configured_max_level ? `Level ${skill.configured_max_level}` : "Level data unavailable"}</span><p>${esc((skill.game_description || "The English client has no squad description for this skill.").replace(/\{(\d+)\}/g,"[runtime value $1]"))}</p><p class="payoff"><strong>Expected payoff:</strong> ${esc(skill.payoff)}</p><p class="evidence">Runtime damage not simulated. Skill-level parameters are modifiers, not multiples of ATK.</p></div></article>`).join("")}</div>`;
  }

  function bestOwnedAndTargets() {
    const ownedHeroes = heroes.filter(owned);
    const unowned = heroes.filter(hero => !owned(hero) && matchesAccess(hero, profile.access === "Owned only" ? "All access" : profile.access));
    if (ownedHeroes.length < 5) return {unlock:`Mark your remaining heroes. Strongest current candidates: ${unowned.sort((a,b)=>scoreHero(b)-scoreHero(a)).slice(0,Math.max(3,5-ownedHeroes.length)).map(h=>h.name).join(", ") || "none"}.`};
    const current = findTopSquads(ownedHeroes,1)[0] || findTopSquads(ownedHeroes,1,false)[0];
    const upgrades = unowned.map(candidate => {
      const next = findTopSquads([...ownedHeroes,candidate],1)[0] || findTopSquads([...ownedHeroes,candidate],1,false)[0];
      return {candidate,next,gain:next.score-current.score};
    }).sort((a,b)=>b.gain-a.gain||b.next.score-a.next.score).slice(0,3);
    return {unlock:upgrades.length ? `Best modeled next targets: ${upgrades.map(x=>`${x.candidate.name} (${x.gain>=0?"+":""}${number(x.gain)} squad points)`).join("; ")}.` : "You own the complete extracted roster."};
  }

  function renderRoster() {
    const hero=activeHero(), recommendation=bestOwnedAndTargets(), progress=profile.heroProgress[hero.asset_slug] || {};
    $("#detail-content").innerHTML = `<div class="section-head"><div><h2>My roster</h2><p>${profile.ownedHeroes.length} / ${heroes.length} marked as owned</p></div><div class="roster-actions"><button class="button secondary" id="all-owned">Mark all</button><button class="button danger" id="none-owned">Clear</button></div></div>
      <div class="release-hero"><img src="${hero.portrait_data}" alt=""><div><h3>${esc(hero.name)} ${owned(hero)?'<span style="color:var(--good)">✓ Owned</span>':''}</h3><p>${esc(hero.rarity)} · ${esc(hero.faction)} · ${esc(hero.role)}</p><button class="button" id="toggle-owned">${owned(hero)?"Remove owned check":"Mark as owned"}</button></div></div>
      <div class="control-strip"><label>${esc(hero.name)} current stars<input id="current-stars" type="number" min="0" max="99" step="1" placeholder="Unknown" value="${progress.current ?? ''}"></label><label>Your star target<input id="target-stars" type="number" min="0" max="99" step="1" placeholder="Not set" value="${progress.target ?? ''}"></label><button class="button secondary" id="save-stars">Save stars</button></div><p class="evidence">Legacy whole-star notes only. Leave blank if unknown. They do not drive upgrade comparisons; record the exact rank step below. No guessed star-to-power scaling.</p>
      ${UpgradeUI.editor(hero.asset_slug,profile)}<div class="recommendations"><div class="notice"><strong>What to unlock next (max-configuration heuristic)</strong><br>${esc(recommendation.unlock)}</div></div>${UpgradeUI.panel(state.squad,profile)}`;
    UpgradeUI.bindEditor(hero.asset_slug,profile,saveProfile,renderAll);
    UpgradeUI.bindPanel(profile,saveProfile,renderAll);
    $("#save-stars").onclick=()=>{
      const inputs=[$("#current-stars"),$("#target-stars")];
      if(inputs.some(input=>!input.reportValidity()))return;
      const [current,target]=inputs.map(input=>input.value===""?null:FormationPriority.cleanStars(Number(input.value)));
      profile.heroProgress[hero.asset_slug]={...progress,current,target};saveProfile();renderDetail();
    };
    $("#toggle-owned").onclick=()=>{toggleOwned(hero);renderCards();renderDetail()};
    $("#all-owned").onclick=()=>setProfile({...profile,ownedHeroes:heroes.map(h=>h.asset_slug)});
    $("#none-owned").onclick=()=>setProfile({...profile,ownedHeroes:[]});
  }

  function releaseWindow(hero) {
    if (hero.release_week_min == null) return null;
    const open = new Date(`${profile.serverOpenDate}T00:00:00`);
    if (Number.isNaN(open.valueOf())) return null;
    const start = new Date(open); start.setDate(start.getDate() + (hero.release_week_min - 1) * 7);
    const end = new Date(open); end.setDate(end.getDate() + (hero.release_week_max || hero.release_week_min) * 7 - 1);
    return {hero,start,end,min:hero.release_week_min,max:hero.release_week_max || hero.release_week_min};
  }
  const dateText = date => date.toLocaleDateString(undefined,{day:"numeric",month:"short",year:"numeric"});

  function renderRelease() {
    const hero=state.releaseActive ? bySlug.get(state.releaseActive) : null, window=hero ? releaseWindow(hero) : null, today=new Date(); today.setHours(0,0,0,0);
    const schedule=heroes.map(releaseWindow).filter(Boolean).sort((a,b)=>a.start-b.start);
    const upcoming=schedule.filter(item=>item.end>=today);
    const current=upcoming.find(item=>item.start<=today&&item.end>=today), next=upcoming.find(item=>item.start>today), headline=next||current;
    const nextCopy=headline ? `<strong>${next?"NEXT":"FINAL CONFIGURED WINDOW"}: ${esc(headline.hero.name)}</strong><br>${dateText(headline.start)} – ${dateText(headline.end)} · server weeks ${headline.min}–${headline.max}<br><small>${next?`Starts in ${Math.ceil((headline.start-today)/86400000)} days.${current?` Current window: ${current.hero.name} through ${dateText(current.end)}.`:""}`:`Active now; ends in ${Math.max(0,Math.ceil((headline.end-today)/86400000))} days. No later client window is configured.`}</small>` : '<strong>No later configured releases</strong><br>All extracted server-age windows are in the past.';
    const heroEvidence = hero ? `<div class="release-hero" style="margin-top:12px"><img src="${hero.portrait_data}" alt=""><div><h3>${esc(hero.name)}</h3><p><strong>${window?`${dateText(window.start)} – ${dateText(window.end)} (weeks ${window.min}–${window.max})`:"Core roster — no server-age release rule"}</strong></p><p>${esc(hero.acquisition_label || "Acquisition route unknown")} · ${esc(hero.acquisition_confidence || "low")} confidence</p><p class="evidence">${hero.iap_linked?"IAP-linked evidence": "No IAP link extracted"} · ${hero.recruit_pool?"Recruit pool":"Not in extracted recruit pool"} · ${hero.turntable_event?"Turntable event":"No turntable event flag"}</p></div></div>` : '<div class="notice release-prompt">Click a hero card on the left to inspect that hero’s release window and acquisition evidence.</div>';
    $("#detail-content").innerHTML = `<div class="section-head"><div><h2>Release &amp; access</h2><p>Estimates use your server opening date and extracted client rules.</p></div></div>
      <div class="control-strip"><label>Server opening date<input id="server-date" type="date" value="${esc(profile.serverOpenDate)}"></label></div>
      <div class="notice">${nextCopy}</div>
      ${heroEvidence}
      <div class="timeline">${upcoming.slice(0,12).map(item=>{const marker=item===current?"NOW":item===next?"NEXT":`W${item.min}`;return `<div class="timeline-row"><span class="marker">${marker}</span><span><strong>${esc(item.hero.name)}</strong><br><small>Weeks ${item.min}–${item.max} · ${dateText(item.start)} – ${dateText(item.end)}</small></span><small>${item.start<=today?"Active configured window":`In ${Math.ceil((item.start-today)/86400000)} days`}</small></div>`}).join("")}</div>`;
    $("#server-date").onchange=event=>{profile.serverOpenDate=event.target.value;saveProfile();renderDetail()};
  }

  let lastEstimateBuilds=null;
  function renderAll() {
    const snapshot=profile.comparisonBasis+(profile.comparisonBasis==='recorded'?JSON.stringify(heroes.map(h=>profile.heroProgress?.[h.asset_slug]?.build||null)):'');
    if(snapshot!==lastEstimateBuilds){
      for(const hero of heroes){const result=EstimateModel.compare(hero.asset_slug,profile.heroProgress?.[hero.asset_slug]?.build,window.__UPGRADE_DATA__,window.__ESTIMATE_DATA__,profile.comparisonBasis,flatIndices.get(hero.asset_slug));
        hero.estimate=result;hero.offense_index=result.offense;hero.durability_index=result.durability;hero.composite_index=result.score;}
      heroes.sort((a,b)=>b.composite_index-a.composite_index||a.name.localeCompare(b.name));optimizerCache.clear();
      lastEstimateBuilds=profile.comparisonBasis+(profile.comparisonBasis==='recorded'?JSON.stringify(heroes.map(h=>profile.heroProgress?.[h.asset_slug]?.build||null)):'');
    }
    document.documentElement.style.setProperty("--left", `${profile.leftWidth}%`);
    $('#comparison-basis').value=profile.comparisonBasis;
    renderCards(); renderDetail(); saveProfile();
  }

  function wireShell() {
    $('#comparison-basis').onchange=event=>{profile.comparisonBasis=event.target.value;renderAll();};
    $$(".top-nav [data-tab]").forEach(button => button.onclick=()=>{state.tab=button.dataset.tab;if(state.tab==="release")state.releaseActive=null;renderDetail()});
    [["#faction-filter","faction"],["#role-filter","role"],["#rarity-filter","rarity"]].forEach(([selector,key]) => $(selector).onchange=event=>{state[key]=event.target.value;renderCards()});
    $("#export-profile").onclick=exportProfile;
    $("#import-profile").onclick=()=>$("#profile-file").click();
    $("#profile-file").onchange=event=>{if(event.target.files[0])importProfile(event.target.files[0]);event.target.value=""};

    const scroll=$("#hero-scroll"); let pending=false,dragging=false,startY=0,startScroll=0;
    scroll.addEventListener("pointerdown", event=>{if(event.button!==0)return;pending=true;dragging=false;startY=event.clientY;startScroll=scroll.scrollTop});
    scroll.addEventListener("pointermove", event=>{if(!pending)return;const delta=event.clientY-startY;if(!dragging&&Math.abs(delta)>6){dragging=true;scroll.classList.add("dragging");scroll.setPointerCapture(event.pointerId)}if(dragging){scroll.scrollTop=startScroll-delta;event.preventDefault()}});
    const endDrag=()=>{if(dragging)suppressCardClickUntil=performance.now()+120;pending=false;dragging=false;scroll.classList.remove("dragging")};
    scroll.addEventListener("pointerup",endDrag);scroll.addEventListener("pointercancel",endDrag);scroll.addEventListener("lostpointercapture",endDrag);

    const splitter=$("#splitter"),workspace=$("#workspace");let resizing=false;
    splitter.addEventListener("pointerdown",event=>{resizing=true;splitter.setPointerCapture(event.pointerId);event.preventDefault()});
    splitter.addEventListener("pointermove",event=>{if(!resizing)return;const rect=workspace.getBoundingClientRect();profile.leftWidth=Math.min(72,Math.max(38,(event.clientX-rect.left)/rect.width*100));document.documentElement.style.setProperty("--left",`${profile.leftWidth}%`)});
    splitter.addEventListener("pointerup",()=>{if(resizing){resizing=false;saveProfile()}});
    splitter.addEventListener("keydown",event=>{if(!["ArrowLeft","ArrowRight"].includes(event.key))return;profile.leftWidth+=event.key==="ArrowLeft"?-2:2;saveProfile();event.preventDefault()});
  }

  function registerWebMcp() {
    const context=document.modelContext;if(!context?.registerTool)return;
    try {
      context.registerTool({name:"set_owned_heroes",title:"Set owned heroes",description:"Replace the planner's owned-hero list using hero names.",inputSchema:{type:"object",properties:{names:{type:"array",items:{type:"string"}}},required:["names"],additionalProperties:false},annotations:{readOnlyHint:false,untrustedContentHint:false},execute({names}){if(!Array.isArray(names))throw new Error("names must be an array");const wanted=new Set(names.map(name=>String(name).toLowerCase()));setProfile({...profile,ownedHeroes:heroes.filter(hero=>wanted.has(hero.name.toLowerCase())).map(hero=>hero.asset_slug)});return{owned:profile.ownedHeroes.map(slug=>bySlug.get(slug).name)}}});
      context.registerTool({name:"get_best_squads",title:"Get best squads",description:"Return the best modeled five-hero squads for the current planner settings.",inputSchema:{type:"object",properties:{limit:{type:"integer",minimum:1,maximum:20}},additionalProperties:false},annotations:{readOnlyHint:true,untrustedContentHint:false},execute({limit=5}={}){return findTopSquads(heroes.filter(hero=>matchesAccess(hero)),limit).map(item=>({heroes:item.heroes.map(hero=>hero.name),score:Number(item.score.toFixed(1)),synergy:item.summary}))}});
    } catch (_) {}
  }

  wireShell(); renderAll(); registerWebMcp();
})();
