(function (root) {
  "use strict";
  // Investment policy, not a DPS simulation or a star-to-power multiplier.
  const compare = (a, b, metric) => (Number(b[metric]) || 0) - (Number(a[metric]) || 0)
    || (a.asset_slug < b.asset_slug ? -1 : a.asset_slug > b.asset_slug ? 1 : 0);
  function carries(squad) {
    const damage = squad.filter(h => h.role !== "Melee" && !(h.role === "Mid" && h.mechanics.has("Healing")));
    const pool = damage.length ? damage : squad.filter(h => h.role !== "Melee");
    return [...(pool.length ? pool : squad)].sort((a, b) => (Number(b.offense_index) || 0) - (Number(a.offense_index) || 0)
      || (a.role === "Range" ? 0 : 1) - (b.role === "Range" ? 0 : 1) || compare(a, b, "offense_index")).slice(0, 2);
  }
  function rank(squad, mode = "Balanced") {
    const remaining = new Map(squad.map(h => [h.asset_slug, h]));
    const unique = [...remaining.values()];
    const damage = carries(unique);
    const front = unique.filter(h => h.role === "Melee").sort((a, b) => compare(a, b, "durability_index"))[0];
    const result = [];
    const add = (hero, reason) => {
      if (hero && remaining.delete(hero.asset_slug)) result.push({hero, reason});
    };
    const addDamage = i => add(damage[i], i === 0
      ? "Primary damage-core investment. Keep the frontline functional; this is not a measured DPS ranking."
      : "Secondary damage-core investment after the core is functional.");
    const addFront = () => add(front, "Frontline anchor. Raise this first if the line dies before your damage heroes can work.");
    const utility = h => h.role === "Mid" && h.mechanics.has("Healing") ? 4
      : h.mechanics.has("Shield") || h.mechanics.has("Damage reduction") ? 3
      : h.mechanics.has("DEF reduction") ? 2
      : ["Healing", "Stun", "Slow", "ATK reduction"].some(m => h.mechanics.has(m)) ? 1 : 0;
    const addUtility = () => add([...remaining.values()].filter(h => utility(h) > 0)
      .sort((a, b) => utility(b) - utility(a) || compare(a, b, "durability_index"))[0],
      "Sustain / utility investment. Prioritize the useful skill; do not equalize every hero's spending.");
    if (mode === "Survival") { addFront(); addUtility(); addDamage(0); addDamage(1); }
    else if (mode === "Offense") { addDamage(0); addDamage(1); addFront(); addUtility(); }
    else { addDamage(0); addFront(); addDamage(1); addUtility(); }
    [...remaining.values()].sort((a, b) => compare(a, b, mode === "Survival" ? "durability_index" : "offense_index"))
      .forEach(h => add(h, "Maintain this member after the core priorities; upgrade a needed skill before spreading resources evenly."));
    return result;
  }
  function cleanStars(value) {
    return typeof value === "number" && Number.isInteger(value) && value >= 0 && value <= 99 ? value : null;
  }
  function sanitizeProgress(candidate, validSlugs) {
    const result = {};
    if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) return result;
    for (const slug of validSlugs) {
      const entry = candidate[slug];
      if (!entry || typeof entry !== "object") continue;
      const current = cleanStars(entry.current), target = cleanStars(entry.target);
      if (current !== null || target !== null) result[slug] = {current, target};
    }
    return result;
  }
  function starPlan(squad, mode, progress = {}) {
    return rank(squad, mode).map(item => {
      const current = cleanStars(progress[item.hero.asset_slug]?.current);
      const target = cleanStars(progress[item.hero.asset_slug]?.target);
      const status = current === null || target === null ? "unknown" : current >= target ? "reached" : "pending";
      return {...item, current, target, status};
    });
  }
  const api = {rank, carries, cleanStars, sanitizeProgress, starPlan};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.FormationPriority = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
