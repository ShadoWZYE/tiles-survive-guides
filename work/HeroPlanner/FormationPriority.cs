using System.Text.Json.Serialization;

namespace TilesSurviveHeroPlanner;

public sealed record HeroInvestment(Hero Hero, string Reason);
public sealed class HeroProgress
{
    [JsonPropertyName("current")] public int? Current { get; set; }
    [JsonPropertyName("target")] public int? Target { get; set; }
    public static int? Clean(int? value) => value is >= 0 and <= 99 ? value : null;
    [JsonIgnore] public string Status => Clean(Current) is not int current || Clean(Target) is not int target
        ? "unknown" : current >= target ? "reached" : "pending";
}

// Role-based investment guide. Stars do not invent a damage or power multiplier.
public static class FormationPriority
{
    public static List<Hero> Carries(IEnumerable<Hero> squad)
    {
        var heroes = squad.ToList();
        var pool = heroes.Where(h => h.Role != "Melee" && !(h.Role == "Mid" && h.HasMechanic("Healing"))).ToList();
        if (pool.Count == 0) pool = heroes.Where(h => h.Role != "Melee").ToList();
        if (pool.Count == 0) pool = heroes;
        return pool.OrderByDescending(h => h.OffenseIndex).ThenBy(h => h.Role == "Range" ? 0 : 1)
            .ThenBy(h => h.AssetSlug, StringComparer.Ordinal).Take(2).ToList();
    }

    public static List<HeroInvestment> Rank(IEnumerable<Hero> squad, PlannerMode mode)
    {
        var remaining = squad.DistinctBy(h => h.AssetSlug).ToDictionary(h => h.AssetSlug);
        var damage = Carries(remaining.Values);
        var front = remaining.Values.Where(h => h.Role == "Melee").OrderByDescending(h => h.DurabilityIndex)
            .ThenBy(h => h.AssetSlug, StringComparer.Ordinal).FirstOrDefault();
        var result = new List<HeroInvestment>();
        void Add(Hero? hero, string reason)
        {
            if (hero is not null && remaining.Remove(hero.AssetSlug)) result.Add(new(hero, reason));
        }
        void AddDamage(int i) => Add(damage.ElementAtOrDefault(i), i == 0
            ? "Primary damage-core investment. Keep the frontline functional; this is not a measured DPS ranking."
            : "Secondary damage-core investment after the core is functional.");
        void AddFront() => Add(front, "Frontline anchor. Raise this first if the line dies before your damage heroes can work.");
        int Utility(Hero h) => h.Role == "Mid" && h.HasMechanic("Healing") ? 4
            : h.HasMechanic("Shield") || h.HasMechanic("Damage reduction") ? 3
            : h.HasMechanic("DEF reduction") ? 2
            : new[] { "Healing", "Stun", "Slow", "ATK reduction" }.Any(h.HasMechanic) ? 1 : 0;
        void AddUtility() => Add(remaining.Values.Where(h => Utility(h) > 0).OrderByDescending(Utility)
            .ThenByDescending(h => h.DurabilityIndex).ThenBy(h => h.AssetSlug, StringComparer.Ordinal).FirstOrDefault(),
            "Sustain / utility investment. Prioritize the useful skill; do not equalize every hero's spending.");
        if (mode == PlannerMode.Survival) { AddFront(); AddUtility(); AddDamage(0); AddDamage(1); }
        else if (mode == PlannerMode.Offense) { AddDamage(0); AddDamage(1); AddFront(); AddUtility(); }
        else { AddDamage(0); AddFront(); AddDamage(1); AddUtility(); }
        foreach (var hero in remaining.Values.OrderByDescending(h => mode == PlannerMode.Survival ? h.DurabilityIndex : h.OffenseIndex)
                     .ThenBy(h => h.AssetSlug, StringComparer.Ordinal).ToList())
            Add(hero, "Maintain this member after the core priorities; upgrade a needed skill before spreading resources evenly.");
        return result;
    }
}
